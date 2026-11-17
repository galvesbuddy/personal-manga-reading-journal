"""Start the manga journal desktop application."""

from manga_journal.ui import MangaJournalApp


def main() -> None:
    app = MangaJournalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
