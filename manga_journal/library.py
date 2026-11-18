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

        return self.database.add_manga(
            title=title,
            status=status,
            rating=parsed_rating,
            current_chapter=parsed_chapter,
            review=review,
        )

    def list_manga(self) -> list[sqlite3.Row]:
        return self.database.list_manga()
