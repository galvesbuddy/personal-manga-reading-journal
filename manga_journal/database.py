"""SQLite storage for the manga library."""

from contextlib import closing
import os
from pathlib import Path
import sqlite3


def default_database_path() -> Path:
    """Keep saved data separate from the source code and executable."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "MangaLibrary" / "library.sqlite3"


class MangaDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS manga (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                    status TEXT NOT NULL DEFAULT 'Not Started'
                        CHECK (status IN ('Not Started', 'Reading', 'Completed', 'Dropped')),
                    rating INTEGER CHECK (
                        rating IS NULL OR
                        (typeof(rating) = 'integer' AND rating BETWEEN 0 AND 100)
                    ),
                    current_chapter REAL NOT NULL DEFAULT 0 CHECK (current_chapter >= 0),
                    review TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def add_manga(
        self,
        *,
        title: str,
        status: str,
        rating: int | None,
        current_chapter: float,
        review: str,
    ) -> int:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO manga (title, status, rating, current_chapter, review)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, status, rating, current_chapter, review),
            )
            return cursor.lastrowid

    def list_manga(self) -> list[sqlite3.Row]:
        with closing(self._connect()) as connection:
            return connection.execute(
                """
                SELECT id, title, status, rating, current_chapter, review
                FROM manga
                ORDER BY title COLLATE NOCASE, id
                """
            ).fetchall()

    def get_manga(self, manga_id: int) -> sqlite3.Row | None:
        with closing(self._connect()) as connection:
            return connection.execute(
                """
                SELECT id, title, status, rating, current_chapter, review
                FROM manga WHERE id = ?
                """,
                (manga_id,),
            ).fetchone()

    def update_manga(
        self,
        manga_id: int,
        *,
        title: str,
        status: str,
        rating: int | None,
        current_chapter: float,
        review: str,
    ) -> bool:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE manga
                SET title = ?, status = ?, rating = ?, current_chapter = ?, review = ?
                WHERE id = ?
                """,
                (title, status, rating, current_chapter, review, manga_id),
            )
            return cursor.rowcount == 1

    def delete_manga_many(self, manga_ids: list[int]) -> int:
        manga_ids = list(dict.fromkeys(manga_ids))
        if not manga_ids:
            return 0
        with closing(self._connect()) as connection, connection:
            cursor = connection.executemany(
                "DELETE FROM manga WHERE id = ?", [(manga_id,) for manga_id in manga_ids]
            )
            if cursor.rowcount != len(manga_ids):
                # Raising inside the transaction rolls back every deletion in this batch.
                raise ValueError("Some selected manga no longer exist. No manga were deleted.")
            return cursor.rowcount
