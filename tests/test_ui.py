"""Exercise review viewing and edit/delete workflows with temporary storage."""

from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
