"""Input validation and application rules for the manga journal."""

import math
import sqlite3

from .database import MangaDatabase


STATUSES = ("Not Started", "Reading", "Completed", "Dropped")


class MangaLibrary:
    def __init__(self, database: MangaDatabase) -> None:
        self.database = database

    def add_manga(
        self,
        *,
        title: str,
        status: str = "",
        rating: str = "",
        current_chapter: str = "",
        review: str = "",
    ) -> int:
        title, status, parsed_rating, parsed_chapter = self._validate_fields(
            title=title, status=status, rating=rating, current_chapter=current_chapter
        )
        return self.database.add_manga(
            title=title,
            status=status,
            rating=parsed_rating,
            current_chapter=parsed_chapter,
            review=review,
        )

    def list_manga(
        self, *, search: str = "", status: str = "", sort: str = "title"
    ) -> list[sqlite3.Row]:
        status = status.strip()
        if status and status not in STATUSES:
            raise ValueError("Choose one of the listed status filters.")
        if sort not in ("title", "rating_asc", "rating_desc"):
            raise ValueError("Choose one of the listed sort orders.")

        query = search.strip().casefold()
        manga = [
            entry for entry in self.database.list_manga()
            if query in entry["title"].casefold() and (not status or entry["status"] == status)
        ]
        # Sort by title first so equal ratings retain alphabetical order.
        manga.sort(key=lambda entry: (entry["title"].casefold(), entry["id"]))
        if sort == "title":
            return manga

        rated = [entry for entry in manga if entry["rating"] is not None]
        unrated = [entry for entry in manga if entry["rating"] is None]
        rated.sort(key=lambda entry: entry["rating"], reverse=(sort == "rating_desc"))
        return rated + unrated

    def get_manga(self, manga_id: int) -> sqlite3.Row:
        entry = self.database.get_manga(manga_id)
        if entry is None:
            raise ValueError("This manga is no longer in your library.")
        return entry

    def update_manga(
        self,
        manga_id: int,
        *,
        title: str,
        status: str = "",
        rating: str = "",
        current_chapter: str = "",
        review: str = "",
    ) -> None:
        existing = self.get_manga(manga_id)
        # An omitted edit status preserves the saved choice, including Dropped/Completed.
        status = status.strip() or existing["status"]
        title, status, parsed_rating, parsed_chapter = self._validate_fields(
            title=title, status=status, rating=rating, current_chapter=current_chapter
        )
        updated = self.database.update_manga(
            manga_id,
            title=title,
            status=status,
            rating=parsed_rating,
            current_chapter=parsed_chapter,
            review=review,
        )
        if not updated:
            raise ValueError("This manga is no longer in your library.")

    def delete_manga(self, manga_id: int) -> None:
        if not self.database.delete_manga(manga_id):
            raise ValueError("This manga is no longer in your library.")

    def _validate_fields(
        self,
        *,
        title: str,
        status: str,
        rating: str,
        current_chapter: str,
    ) -> tuple[str, str, int | None, float]:
        title = title.strip()
        if not title:
            raise ValueError("Enter a manga title.")

        rating_text = rating.strip()
        parsed_rating = None
        if rating_text:
            try:
                parsed_rating = int(rating_text)
            except ValueError:
                raise ValueError("Rating must be a whole number from 0 to 100.") from None
            if not 0 <= parsed_rating <= 100:
                raise ValueError("Rating must be a whole number from 0 to 100.")

        try:
            parsed_chapter = float(current_chapter.strip() or "0")
        except ValueError:
            raise ValueError("Chapter must be a number greater than or equal to 0.") from None
        if not math.isfinite(parsed_chapter) or parsed_chapter < 0:
            raise ValueError("Chapter must be a finite number greater than or equal to 0.")

        status = status.strip()
        if not status:
            status = "Reading" if parsed_chapter > 0 else "Not Started"
        if status not in STATUSES:
            raise ValueError("Choose one of the listed statuses.")

        return title, status, parsed_rating, parsed_chapter
