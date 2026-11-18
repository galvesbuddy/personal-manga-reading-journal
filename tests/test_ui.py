"""Exercise review viewing and edit/delete workflows with temporary storage."""

from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import tkinter as tk
import unittest
from unittest.mock import patch

from manga_journal.database import MangaDatabase
from manga_journal.library import MangaLibrary
from manga_journal.ui import MangaJournalApp


class MangaUITests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.library = MangaLibrary(MangaDatabase(Path(temporary.name) / "library.sqlite3"))
        self.first_id = self.library.add_manga(
            title="First", status="Dropped", rating="0", current_chapter="10.5",
            review="First review.\nSecond line.",
        )
        self.second_id = self.library.add_manga(title="Second")
        try:
            self.app = MangaJournalApp(self.library)
        except tk.TclError as error:
            if "no display name" in str(error) or "couldn't connect to display" in str(error):
                self.skipTest(f"Tkinter display unavailable: {error}")
            raise
        self.addCleanup(self.app.destroy)
        self.app.withdraw()
        self.app.update()
        errors = patch("manga_journal.ui.messagebox.showerror")
        self.error = errors.start()
        self.addCleanup(errors.stop)
        confirmations = patch("manga_journal.ui.messagebox.askyesno", return_value=False)
        self.confirm = confirmations.start()
        self.addCleanup(confirmations.stop)

    def select(self, manga_id: int) -> None:
        self.app.manga_list.selection_set(str(manga_id))
        self.app.update()

    def displayed_review(self) -> str:
        return self.app.review_display.get("1.0", "end-1c")

    def test_selection_shows_read_only_review_and_empty_placeholder(self) -> None:
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.assertEqual(str(self.app.review_display.cget("state")), "disabled")
        self.select(self.second_id)
        self.assertEqual(self.app.review_title.get(), "Second")
        self.assertEqual(self.displayed_review(), "No review yet.")
        self.error.assert_not_called()

    def test_edit_loads_fields_and_saves_same_entry(self) -> None:
        self.app.start_edit()
        self.assertEqual(self.app.title_input.get(), "First")
        self.assertEqual(self.app.rating_input.get(), "0")
        self.assertEqual(self.app.review_input.get("1.0", "end-1c"), "First review.\nSecond line.")
        self.app.title_input.set("Renamed")
        self.app.chapter_input.set("15.5")
        self.app.review_input.delete("1.0", "end")
        self.app.review_input.insert("1.0", "Updated review")
        self.app.save_manga()
        self.app.update()
        self.assertEqual(len(self.library.list_manga()), 2)
        entry = self.library.get_manga(self.first_id)
        self.assertEqual(entry["title"], "Renamed")
        self.assertEqual(entry["status"], "Dropped")
        self.assertEqual(entry["current_chapter"], 15.5)
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.displayed_review(), "Updated review")
        self.assertEqual(self.app._mode, "view")
        self.error.assert_not_called()

    def test_new_creates_another_entry_and_cancel_does_not_save(self) -> None:
        self.app.start_new()
        self.app.title_input.set("Cancelled entry")
        self.app.cancel_form()
        self.assertEqual(len(self.library.list_manga()), 2)
        self.assertEqual(self.app.selected_id, self.first_id)
        self.app.start_new()
        self.assertEqual(self.app.title_input.get(), "")
        self.app.title_input.set("New entry")
        self.app.chapter_input.set("2.5")
        self.app.review_input.insert("1.0", "New review")
        self.app.save_manga()
        self.app.update()
        self.assertEqual(len(self.library.list_manga()), 3)
        self.assertNotEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.displayed_review(), "New review")
        self.assertEqual(self.library.get_manga(self.app.selected_id)["status"], "Reading")
        self.assertEqual(self.library.get_manga(self.first_id)["title"], "First")
        self.error.assert_not_called()

    def test_cancel_edit_restores_review_without_saving(self) -> None:
        self.app.start_edit()
        self.app.title_input.set("Unsaved title")
        self.app.review_input.insert("end", " Unsaved review")
        self.app.cancel_form()
        self.assertEqual(self.library.get_manga(self.first_id)["title"], "First")
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.assertEqual(self.app._mode, "view")
        self.error.assert_not_called()

    def test_invalid_edit_keeps_form_and_saved_values(self) -> None:
        self.app.start_edit()
        self.app.rating_input.set("101")
        self.app.save_manga()
        self.error.assert_called_once()
        self.assertEqual(self.app._mode, "edit")
        self.assertEqual(self.app.rating_input.get(), "101")
        self.assertEqual(self.library.get_manga(self.first_id)["rating"], 0)

    def test_navigation_preserves_draft_unless_discard_is_confirmed(self) -> None:
        self.app.start_edit()
        self.app.review_input.insert("end", " Draft")
        self.select(self.second_id)
        self.confirm.assert_called_once()
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.app.manga_list.selection(), (str(self.first_id),))
        self.assertTrue(self.app.review_input.get("1.0", "end-1c").endswith(" Draft"))
        self.confirm.return_value = True
        self.select(self.second_id)
        self.assertEqual(self.app.selected_id, self.second_id)
        self.assertEqual(self.app._mode, "view")
        self.assertEqual(self.library.get_manga(self.first_id)["review"], "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_delete_requires_confirmation_and_handles_empty_library(self) -> None:
        self.app.delete_manga()
        self.assertEqual(self.confirm.call_args.args[1], 'Delete "First"?')
        self.assertEqual(len(self.library.list_manga()), 2)
        self.confirm.return_value = True
        self.app.delete_manga()
        self.app.update()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.assertEqual(self.displayed_review(), "No review yet.")
        self.app.delete_manga()
        self.app.update()
        self.assertEqual(self.library.list_manga(), [])
        self.assertEqual(self.app.manga_list.get_children(), ())
        self.assertIsNone(self.app.selected_id)
        self.assertTrue(self.app.edit_button.instate(["disabled"]))
        self.assertTrue(self.app.delete_button.instate(["disabled"]))
        self.error.assert_not_called()

    def test_editing_does_not_round_unchanged_chapter(self) -> None:
        self.library.update_manga(self.first_id, title="First", current_chapter="10.123456789012345")
        before = self.library.get_manga(self.first_id)["current_chapter"]
        self.app.start_edit()
        self.app.save_manga()
        self.assertEqual(self.library.get_manga(self.first_id)["current_chapter"], before)
        self.error.assert_not_called()

    def test_search_updates_selection_and_reset_restores_library(self) -> None:
        self.app.search_input.set("fIR")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), (str(self.first_id),))
        self.assertEqual(self.app.selected_id, self.first_id)
        self.app.search_input.set("second")
        self.app.update()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.assertEqual(self.app.review_title.get(), "Second")
        self.app.search_input.set("no such title")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), ())
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(self.app.review_title.get(), "No matching manga")
        self.assertEqual(self.app.count.get(), "0 matching manga")
        self.assertTrue(self.app.edit_button.instate(["disabled"]))
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(len(self.app.manga_list.get_children()), 2)
        self.assertEqual(self.app.count.get(), "2 manga")
        self.assertEqual(len(self.library.list_manga()), 2)
        self.error.assert_not_called()

    def test_combined_controls_and_sort_preserve_matching_selection(self) -> None:
        high_id = self.library.add_manga(title="First high", status="Dropped", rating="95")
        self.app.search_input.set("first")
        self.app.status_filter.set("Dropped")
        self.app.sort_input.set("Rating: high to low")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), (str(high_id), str(self.first_id)))
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.app.status_filter.set("Not Started")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), ())
        self.app.reset_filters()
        self.assertEqual(len(self.app.manga_list.get_children()), 3)
        self.error.assert_not_called()

    def test_sort_keeps_unrated_selection_and_unrated_rows_last(self) -> None:
        high_id = self.library.add_manga(title="High", rating="100")
        self.app.refresh_manga()
        self.select(self.second_id)
        self.app.sort_input.set("Rating: high to low")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), (str(high_id), str(self.first_id), str(self.second_id)))
        self.assertEqual(self.app.selected_id, self.second_id)
        self.app.sort_input.set("Rating: low to high")
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), (str(self.first_id), str(high_id), str(self.second_id)))
        self.assertEqual(self.app.selected_id, self.second_id)
        self.error.assert_not_called()

    def test_filter_change_can_be_cancelled_without_losing_draft(self) -> None:
        self.app.start_edit()
        self.app.review_input.insert("end", " Draft")
        self.app.search_input.set("second")
        self.app.update()
        self.confirm.assert_called_once()
        self.assertEqual(self.app.search_input.get(), "")
        self.assertEqual(self.app._mode, "edit")
        self.assertTrue(self.app.review_input.get("1.0", "end-1c").endswith(" Draft"))
        self.assertEqual(self.app.selected_id, self.first_id)
        self.confirm.return_value = True
        self.app.search_input.set("second")
        self.app.update()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.assertEqual(self.app._mode, "view")
        self.assertEqual(self.library.get_manga(self.first_id)["review"], "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_reset_restores_all_controls_if_discard_is_declined(self) -> None:
        self.app.search_input.set("first")
        self.app.status_filter.set("Dropped")
        self.app.sort_input.set("Rating: high to low")
        self.app.start_edit()
        self.app.title_input.set("Unsaved title")
        self.app.reset_filters()
        self.app.update()
        self.confirm.assert_called_once()
        self.assertEqual(self.app.search_input.get(), "first")
        self.assertEqual(self.app.status_filter.get(), "Dropped")
        self.assertEqual(self.app.sort_input.get(), "Rating: high to low")
        self.assertEqual(self.app.title_input.get(), "Unsaved title")
        self.assertEqual(self.app._mode, "edit")
        self.error.assert_not_called()

    def test_reset_selects_first_manga_when_controls_are_already_default(self) -> None:
        self.select(self.second_id)
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.app.manga_list.selection(), (str(self.first_id),))
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.confirm.assert_not_called()
        self.error.assert_not_called()

    def test_reset_selects_first_manga_after_filtering(self) -> None:
        self.app.search_input.set("second")
        self.app.update()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.app.manga_list.get_children()[0], str(self.first_id))
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_reset_at_defaults_still_protects_unsaved_changes(self) -> None:
        self.select(self.second_id)
        self.app.start_edit()
        self.app.title_input.set("Unsaved title")
        self.app.reset_filters()
        self.app.update()
        self.confirm.assert_called_once()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.assertEqual(self.app.title_input.get(), "Unsaved title")
        self.assertEqual(self.app._mode, "edit")
        self.confirm.return_value = True
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.app.selected_id, self.first_id)
        self.assertEqual(self.app._mode, "view")
        self.assertEqual(self.library.get_manga(self.second_id)["title"], "Second")
        self.error.assert_not_called()

    def test_save_excluded_by_filter_is_saved_and_explained(self) -> None:
        self.app.status_filter.set("Dropped")
        self.app.start_edit()
        self.app.status_input.set("Completed")
        self.app.save_manga()
        self.app.update()
        self.assertEqual(self.library.get_manga(self.first_id)["status"], "Completed")
        self.assertEqual(self.app.manga_list.get_children(), ())
        self.assertIn("Hidden by the current search or status filter", self.app.feedback.get())
        self.assertEqual(self.app.review_title.get(), "No matching manga")
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(len(self.app.manga_list.get_children()), 2)
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_deleting_last_match_preserves_other_saved_manga(self) -> None:
        self.app.status_filter.set("Dropped")
        self.confirm.return_value = True
        self.app.delete_manga()
        self.app.update()
        self.assertEqual(self.app.manga_list.get_children(), ())
        self.assertEqual(self.app.review_title.get(), "No matching manga")
        self.assertEqual(len(self.library.list_manga()), 1)
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.app.selected_id, self.second_id)
        self.error.assert_not_called()

    def test_failed_filter_query_restores_controls_and_previous_list(self) -> None:
        before = self.app.manga_list.get_children()
        with patch.object(self.library, "list_manga", side_effect=sqlite3.OperationalError("Test read failure")):
            self.app.search_input.set("second")
        self.app.update()
        self.error.assert_called_once()
        self.assertEqual(self.app.search_input.get(), "")
        self.assertEqual(self.app.manga_list.get_children(), before)
        self.assertEqual(self.app.selected_id, self.first_id)

    def select_many(self, *manga_ids: int) -> None:
        self.app.manga_list.selection_set(tuple(str(manga_id) for manga_id in manga_ids))
        self.app.update()

    def test_multiple_selection_shows_count_and_disables_edit(self) -> None:
        self.select_many(self.first_id, self.second_id)
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(set(self.app.selected_ids), {self.first_id, self.second_id})
        self.assertEqual(self.app.review_title.get(), "2 manga selected")
        self.assertTrue(self.app.edit_button.instate(["disabled"]))
        self.assertFalse(self.app.delete_button.instate(["disabled"]))
        self.app.start_edit()
        self.assertEqual(self.app._mode, "view")
        self.error.assert_not_called()

    def test_select_all_and_bulk_delete_only_affect_displayed_matches(self) -> None:
        third = self.library.add_manga(title="Third", review="Third review")
        self.app.status_filter.set("Not Started")
        self.app.select_all()
        self.app.update()
        self.assertEqual(set(self.app.selected_ids), {self.second_id, third})
        self.confirm.return_value = True
        self.app.delete_manga()
        self.app.update()
        self.confirm.assert_called_once()
        self.assertEqual(self.confirm.call_args.args[1], "Delete 2 manga?")
        self.assertEqual([entry["id"] for entry in self.library.list_manga()], [self.first_id])
        self.assertEqual(self.app.review_title.get(), "No matching manga")
        self.assertTrue(self.app.select_all_button.instate(["disabled"]))
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_cancelling_bulk_delete_keeps_entries_and_selection(self) -> None:
        self.app.select_all()
        self.app.update()
        before = [dict(entry) for entry in self.library.list_manga()]
        self.app.delete_manga()
        self.confirm.assert_called_once()
        self.assertEqual([dict(entry) for entry in self.library.list_manga()], before)
        self.assertEqual(set(self.app.selected_ids), {self.first_id, self.second_id})
        self.error.assert_not_called()

    def test_bulk_delete_entire_library_clears_selection_and_allows_new_entries(self) -> None:
        self.app.select_all()
        self.app.update()
        self.confirm.return_value = True
        self.app.delete_manga()
        self.app.update()
        self.assertEqual(self.library.list_manga(), [])
        self.assertEqual(self.app.selected_ids, ())
        self.assertIsNone(self.app.selected_id)
        self.assertTrue(self.app.edit_button.instate(["disabled"]))
        self.assertTrue(self.app.delete_button.instate(["disabled"]))
        self.assertTrue(self.app.select_all_button.instate(["disabled"]))
        self.app.start_new()
        self.app.title_input.set("After clearing")
        self.app.save_manga()
        self.app.update()
        self.assertEqual(len(self.library.list_manga()), 1)
        self.assertEqual(self.app.review_title.get(), "After clearing")
        self.assertFalse(self.app.select_all_button.instate(["disabled"]))
        self.error.assert_not_called()

    def test_select_all_preserves_draft_if_discard_is_declined(self) -> None:
        self.app.start_edit()
        self.app.review_input.insert("end", " Draft")
        self.app.select_all()
        self.app.update()
        self.confirm.assert_called_once()
        self.assertEqual(self.app.selected_ids, (self.first_id,))
        self.assertEqual(self.app.manga_list.selection(), (str(self.first_id),))
        self.assertEqual(self.app._mode, "edit")
        self.assertTrue(self.app.review_input.get("1.0", "end-1c").endswith(" Draft"))
        self.confirm.return_value = True
        self.app.select_all()
        self.app.update()
        self.assertEqual(self.app.review_title.get(), "2 manga selected")
        self.assertEqual(self.app._mode, "view")
        self.assertEqual(self.library.get_manga(self.first_id)["review"], "First review.\nSecond line.")
        self.error.assert_not_called()

    def test_sort_preserves_multiple_selection_and_filter_drops_hidden_ids(self) -> None:
        self.select_many(self.first_id, self.second_id)
        self.app.sort_input.set("Rating: high to low")
        self.app.update()
        self.assertEqual(set(self.app.selected_ids), {self.first_id, self.second_id})
        self.app.status_filter.set("Dropped")
        self.app.update()
        self.assertEqual(self.app.selected_ids, (self.first_id,))
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")
        self.assertFalse(self.app.edit_button.instate(["disabled"]))
        self.app.reset_filters()
        self.app.select_all()
        self.app.update()
        self.app.reset_filters()
        self.app.update()
        self.assertEqual(self.app.selected_ids, (self.first_id,))
        self.error.assert_not_called()

    def test_cancel_new_restores_multiple_selection(self) -> None:
        self.select_many(self.first_id, self.second_id)
        self.app.start_new()
        self.app.title_input.set("Cancelled")
        self.app.cancel_form()
        self.app.update()
        self.assertEqual(set(self.app.selected_ids), {self.first_id, self.second_id})
        self.assertEqual(self.app.review_title.get(), "2 manga selected")
        self.assertEqual(len(self.library.list_manga()), 2)
        self.error.assert_not_called()

    def test_deselecting_all_shows_selection_prompt_and_disables_delete(self) -> None:
        self.app.manga_list.selection_remove(*self.app.manga_list.selection())
        self.app.update()
        self.assertEqual(self.app.selected_ids, ())
        self.assertTrue(self.app.edit_button.instate(["disabled"]))
        self.assertTrue(self.app.delete_button.instate(["disabled"]))
        self.assertIn("Select a manga from the list", self.displayed_review())
        self.assertFalse(self.app.select_all_button.instate(["disabled"]))
        self.error.assert_not_called()

    def test_failed_selection_read_restores_previous_selection(self) -> None:
        with patch.object(self.library, "get_manga", side_effect=sqlite3.OperationalError("Test read failure")):
            self.select(self.second_id)
        self.error.assert_called_once()
        self.assertEqual(self.app.selected_ids, (self.first_id,))
        self.assertEqual(self.app.manga_list.selection(), (str(self.first_id),))
        self.assertEqual(self.displayed_review(), "First review.\nSecond line.")


if __name__ == "__main__":
    unittest.main()
