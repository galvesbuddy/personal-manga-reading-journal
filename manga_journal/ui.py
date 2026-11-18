"""A basic form and saved-manga list for the first application workflow."""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from .library import MangaLibrary, STATUSES


class MangaJournalApp(tk.Tk):
    def __init__(self, library: MangaLibrary) -> None:
        super().__init__()
        self.library = library
        self.title("Manga Library")
        self.geometry("1000x650")
        self.minsize(820, 520)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.title_input = tk.StringVar()
        self.status_input = tk.StringVar(value="Automatic")
        self.rating_input = tk.StringVar()
        self.chapter_input = tk.StringVar(value="0")
        self.feedback = tk.StringVar(value="Add a manga to start your library.")
        self.count = tk.StringVar(value="0 manga")
        self._build_widgets()
        self.refresh_manga()
        self.title_entry.focus_set()

    def _build_widgets(self) -> None:
        content = ttk.Frame(self, padding=16)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(1, weight=1)
        ttk.Label(content, text="Manga Library", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 16)
        )

        listing = ttk.Frame(content)
        listing.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(1, weight=1)
        ttk.Label(listing, textvariable=self.count).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.manga_list = ttk.Treeview(
            listing, columns=("title", "status", "rating", "chapter"), show="headings", selectmode="browse"
        )
        for name, heading, width in (
            ("title", "Title", 220),
            ("status", "Status", 105),
            ("rating", "Rating", 65),
            ("chapter", "Chapter", 70),
        ):
            self.manga_list.heading(name, text=heading)
            self.manga_list.column(name, width=width, minwidth=60, stretch=(name == "title"))
        self.manga_list.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(listing, orient="vertical", command=self.manga_list.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.manga_list.configure(yscrollcommand=scrollbar.set)

        form = ttk.LabelFrame(content, text="Add manga", padding=12)
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(0, weight=1)
        form.rowconfigure(7, weight=1)

        ttk.Label(form, text="Title (required)").grid(row=0, column=0, sticky="w")
        self.title_entry = ttk.Entry(form, textvariable=self.title_input)
        self.title_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        ttk.Label(form, text="Status (optional)").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            form, textvariable=self.status_input, values=("Automatic", *STATUSES), state="readonly"
        ).grid(row=3, column=0, sticky="ew", pady=(4, 4))
        ttk.Label(
            form, text="Automatic: Not Started at chapter 0; Reading above 0.", wraplength=260
        ).grid(row=4, column=0, sticky="w", pady=(0, 12))

        numbers = ttk.Frame(form)
        numbers.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        numbers.columnconfigure((0, 1), weight=1)
        ttk.Label(numbers, text="Rating (0–100, optional)").grid(row=0, column=0, sticky="w")
        ttk.Label(numbers, text="Current chapter").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Entry(numbers, textvariable=self.rating_input, width=12).grid(
            row=1, column=0, sticky="ew", pady=(4, 0)
        )
        ttk.Entry(numbers, textvariable=self.chapter_input, width=12).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 0)
        )
        ttk.Label(form, text="Thoughts / review (optional)").grid(row=6, column=0, sticky="w")
        self.review_input = tk.Text(form, height=7, width=28, wrap="word", font=("Segoe UI", 10))
        self.review_input.grid(row=7, column=0, sticky="nsew", pady=(4, 12))
        ttk.Button(form, text="Add manga", command=self.add_manga).grid(row=8, column=0, sticky="ew")
        ttk.Label(content, textvariable=self.feedback, wraplength=760).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

    def refresh_manga(self) -> bool:
        try:
            manga = self.library.list_manga()
        except sqlite3.Error as error:
            messagebox.showerror("Cannot load library", f"Could not load your manga.\n\n{error}", parent=self)
            return False
        children = self.manga_list.get_children()
        if children:
            self.manga_list.delete(*children)
        for entry in manga:
            self.manga_list.insert(
                "", "end", iid=str(entry["id"]), values=(
                    entry["title"], entry["status"],
                    "Unrated" if entry["rating"] is None else entry["rating"],
                    format(entry["current_chapter"], ".15g"),
                )
            )
        self.count.set(f"{len(manga)} manga")
        return True

    def add_manga(self) -> None:
        title = self.title_input.get()
        try:
            manga_id = self.library.add_manga(
                title=title,
                status="" if self.status_input.get() == "Automatic" else self.status_input.get(),
                rating=self.rating_input.get(),
                current_chapter=self.chapter_input.get(),
                review=self.review_input.get("1.0", "end-1c"),
            )
        except ValueError as error:
            messagebox.showerror("Check your entry", str(error), parent=self)
            return
        except sqlite3.Error as error:
            messagebox.showerror("Cannot save manga", f"Your manga could not be saved.\n\n{error}", parent=self)
            return

        self.title_input.set("")
        self.status_input.set("Automatic")
        self.rating_input.set("")
        self.chapter_input.set("0")
        self.review_input.delete("1.0", "end")
        self.feedback.set(f'Added "{title.strip()}".')
        if self.refresh_manga():
            self.manga_list.selection_set(str(manga_id))
            self.manga_list.see(str(manga_id))
        self.title_entry.focus_set()
