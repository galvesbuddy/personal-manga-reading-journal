"""Start the manga journal desktop application."""

import sqlite3
from tkinter import messagebox

from manga_journal.database import MangaDatabase
from manga_journal.library import MangaLibrary
from manga_journal.ui import MangaJournalApp


def main() -> None:
    try:
        library = MangaLibrary(MangaDatabase())
    except (OSError, sqlite3.Error) as error:
        messagebox.showerror("Cannot open library", f"Could not open your manga library.\n\n{error}")
        return

    app = MangaJournalApp(library)
    app.mainloop()


if __name__ == "__main__":
    main()
