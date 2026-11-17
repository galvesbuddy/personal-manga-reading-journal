"""The application's Tkinter window."""

import tkinter as tk


class MangaJournalApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Manga Library")
        self.geometry("1000x650")
        self.minsize(720, 480)
