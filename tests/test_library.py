"""Check user-facing rules against real, temporary SQLite databases."""

from contextlib import closing
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from manga_journal.database import MangaDatabase, default_database_path
from manga_journal.library import MangaLibrary


class MangaLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nested" / "library.sqlite3"
        self.library = MangaLibrary(MangaDatabase(self.path))

    def test_entry_survives_reopening_database(self) -> None:
        manga_id = self.library.add_manga(
            title="  葬送のフリーレン  ", current_chapter="10.5", rating="92",
            review="A thoughtful story.\nWorth revisiting.",
        )
        reopened = MangaLibrary(MangaDatabase(self.path))
        entry, = reopened.list_manga()
        self.assertEqual(dict(entry), {
            "id": manga_id, "title": "葬送のフリーレン", "status": "Reading",
            "rating": 92, "current_chapter": 10.5,
            "review": "A thoughtful story.\nWorth revisiting.",
        })

    def test_default_fields_for_unread_manga(self) -> None:
        self.library.add_manga(title="Unread")
        entry, = self.library.list_manga()
        self.assertEqual(entry["status"], "Not Started")
        self.assertEqual(entry["current_chapter"], 0)
        self.assertIsNone(entry["rating"])
        self.assertEqual(entry["review"], "")

    def test_zero_rating_is_distinct_from_unrated(self) -> None:
        self.library.add_manga(title="Rated", rating="0")
        self.library.add_manga(title="Unrated")
        entries = {entry["title"]: entry for entry in self.library.list_manga()}
        self.assertEqual(entries["Rated"]["rating"], 0)
        self.assertIsNone(entries["Unrated"]["rating"])

    def test_explicit_status_wins_over_chapter_default(self) -> None:
        for status in ("Not Started", "Reading", "Completed", "Dropped"):
            with self.subTest(status=status):
                self.library.add_manga(title=status, status=status, current_chapter="25.5")
        for entry in self.library.list_manga():
            self.assertEqual(entry["title"], entry["status"])

    def test_invalid_input_does_not_create_entries(self) -> None:
        cases = (
            {"title": " \t\n"},
            {"rating": "-1"}, {"rating": "101"}, {"rating": "80.5"}, {"rating": "abc"},
            {"current_chapter": "-0.5"}, {"current_chapter": "abc"},
            {"current_chapter": "nan"}, {"current_chapter": "inf"},
            {"current_chapter": "1e999"}, {"status": "Unknown"},
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.library.add_manga(**{"title": "Example", **values})
        self.assertEqual(self.library.list_manga(), [])

    def test_rating_endpoints_are_valid(self) -> None:
        self.library.add_manga(title="Zero", rating="0")
        self.library.add_manga(title="Hundred", rating="100")
        self.assertEqual({entry["rating"] for entry in self.library.list_manga()}, {0, 100})

    def test_titles_and_reviews_are_stored_as_data(self) -> None:
        title = "Reader's manga'); DROP TABLE manga; --"
        self.library.add_manga(title=title, review="Quotes: ' and \"")
        self.library.add_manga(title="Another entry")
        entries = self.library.list_manga()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["title"], title)

    def test_database_constraints_reject_invalid_rows(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for title, status, rating, chapter in (
                ("", "Reading", None, 0),
                ("Title", "Invalid", None, 0),
                ("Title", "Reading", 101, 0),
                ("Title", "Reading", 80.5, 0),
                ("Title", "Reading", None, -1),
            ):
                with self.subTest(values=(title, status, rating, chapter)):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(
                            "INSERT INTO manga (title, status, rating, current_chapter) VALUES (?, ?, ?, ?)",
                            (title, status, rating, chapter),
                        )
        self.assertEqual(self.library.list_manga(), [])

    def test_default_location_uses_windows_environment(self) -> None:
        with patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name}):
            self.assertEqual(
                default_database_path(), Path(self.temp.name) / "MangaLibrary" / "library.sqlite3"
            )


if __name__ == "__main__":
    unittest.main()
