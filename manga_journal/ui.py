"""The library list, review panel, and add/edit form."""

import sqlite3
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

from .library import MangaLibrary, STATUSES
from .theme import PANEL_PADDING, READING_PADDING, THEME_NAME, apply_styles, attach_scrollbar, register_theme, text_options


SORT_OPTIONS = {
    "Title (A–Z)": "title",
    "Rating: low to high": "rating_asc",
    "Rating: high to low": "rating_desc",
}


class MangaJournalApp(ttk.App):
    def __init__(self, library: MangaLibrary) -> None:
        register_theme()
        super().__init__(title="Manga Library", theme=THEME_NAME)
        apply_styles(self)
        self.library = library
        self.selected_id: int | None = None
        self.selected_ids: tuple[int, ...] = ()
        self.editing_id: int | None = None
        self._mode = "view"
        self._form_baseline: dict[str, str] = {}
        self.geometry("1120x760")
        self.minsize(960, 640)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.title_input = tk.StringVar()
        self.status_input = tk.StringVar(value="Automatic")
        self.rating_input = tk.StringVar()
        self.chapter_input = tk.StringVar(value="0")
        self.status_hint = tk.StringVar()
        self.search_input = tk.StringVar()
        self.status_filter = tk.StringVar(value="All")
        self.sort_input = tk.StringVar(value="Title (A–Z)")
        self._restoring_filters = False
        self._active_filters = self._filter_values()
        self.review_caption = tk.StringVar(value="YOUR REVIEW")
        self.form_title = tk.StringVar(value="New manga")
        self.review_title = tk.StringVar(value="Select a manga")
        self.feedback = tk.StringVar(value="Select a manga to read your review, or add a new one.")
        self.count = tk.StringVar(value="0 manga")
        self._build_widgets()
        self.refresh_manga()
        for variable in (self.search_input, self.status_filter, self.sort_input):
            variable.trace_add("write", self._on_filters_changed)
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        self.manga_list.focus_set()

    def _build_widgets(self) -> None:
        content = ttk.Frame(self, style="Main.TFrame")
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1, minsize=440, uniform="panels")
        content.columnconfigure(1, weight=0, minsize=1)
        content.columnconfigure(2, weight=1, minsize=380, uniform="panels")
        content.rowconfigure(0, weight=1)

        listing = ttk.Frame(
            content, padding=(PANEL_PADDING, 24, PANEL_PADDING, 16), style="Sidebar.TFrame"
        )
        listing.grid(row=0, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(3, weight=1)
        header = ttk.Frame(listing, style="Sidebar.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 24))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="READING JOURNAL", style="Accent.Sidebar.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(header, text="Manga Library", style="Title.Sidebar.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Button(header, text="New manga", command=self.start_new, bootstyle="primary").grid(
            row=0, column=1, rowspan=2, sticky="e", padx=(16, 0)
        )

        self._build_list_controls(listing)
        selection_bar = ttk.Frame(listing, style="Sidebar.TFrame")
        selection_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        selection_bar.columnconfigure(0, weight=1)
        ttk.Label(selection_bar, textvariable=self.count, style="Muted.Sidebar.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.select_all_button = ttk.Button(
            selection_bar, text="Select all", command=self.select_all, bootstyle="secondary outline"
        )
        self.select_all_button.grid(row=0, column=1, sticky="e")
        self.manga_list = ttk.Treeview(
            listing, columns=("title", "status", "rating", "chapter"),
            show="headings", selectmode="extended", style="Library.Treeview",
        )
        for name, heading, width in (
            ("title", "Title", 220), ("status", "Status", 108),
            ("rating", "Rating", 70), ("chapter", "Chapter", 70),
        ):
            anchor = "w" if name in ("title", "status") else "center"
            self.manga_list.heading(name, text=heading, anchor=anchor)
            self.manga_list.column(
                name, width=width, minwidth=70, stretch=(name == "title"), anchor=anchor
            )
        self.manga_list.grid(row=3, column=0, sticky="nsew")
        self.manga_list.bind("<<TreeviewSelect>>", self._on_manga_selected)
        self.manga_list.bind("<Control-a>", self.select_all)
        self.manga_list.bind("<Control-A>", self.select_all)
        for event in ("<Button-1>", "<Double-Button-1>", "<Motion>"):
            self.manga_list.bind(event, self._prevent_column_resize)
        scrollbar = ttk.Scrollbar(
            listing, orient="vertical", command=self.manga_list.yview, bootstyle="secondary"
        )
        scrollbar.grid(row=3, column=1, sticky="ns")
        attach_scrollbar(self.manga_list, scrollbar)
        ttk.Label(
            listing, text="Ctrl+click: select multiple   ·   Ctrl+A: select all",
            style="Muted.Sidebar.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Frame(content, width=1, style="Divider.TFrame").grid(row=0, column=1, sticky="ns")
        self.panel = ttk.Frame(
            content, padding=(READING_PADDING, 28, READING_PADDING, 24), style="Main.TFrame"
        )
        self.panel.grid(row=0, column=2, sticky="nsew")
        self.panel.columnconfigure(0, weight=1)
        self.panel.rowconfigure(0, weight=1)
        self._build_review_panel()
        self._build_form_panel()
        self.form.grid_remove()
        self.panel.bind("<Configure>", self._resize_panel_text)

        footer = ttk.Frame(self, padding=(PANEL_PADDING, 10), style="Sidebar.TFrame")
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.feedback_label = ttk.Label(
            footer, textvariable=self.feedback, style="Muted.Sidebar.TLabel", wraplength=1000
        )
        self.feedback_label.grid(row=0, column=0, sticky="w")
        footer.bind("<Configure>", self._resize_feedback)

    def _prevent_column_resize(self, event: tk.Event) -> str | None:
        """Keep column dividers fixed while allowing normal row selection."""
        if self.manga_list.identify_region(event.x, event.y) == "separator":
            self.manga_list.configure(cursor="")
            return "break"
        return None

    def _resize_panel_text(self, event: tk.Event) -> None:
        width = max(180, event.width - 2 * READING_PADDING)
        self.review_heading.configure(wraplength=width)
        self.status_hint_label.configure(wraplength=width)

    def _resize_feedback(self, event: tk.Event) -> None:
        self.feedback_label.configure(wraplength=max(240, event.width - 2 * PANEL_PADDING))

    def _build_list_controls(self, listing: ttk.Frame) -> None:
        controls = ttk.Frame(listing, style="Sidebar.TFrame")
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        controls.columnconfigure((0, 1), weight=1)
        ttk.Label(controls, text="Search title", style="Caption.Sidebar.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        search = ttk.Frame(controls, style="Sidebar.TFrame")
        search.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 16))
        search.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(
            search, textvariable=self.search_input, style="Sidebar.TEntry"
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(search, text="Reset", command=self.reset_filters, bootstyle="secondary outline").grid(
            row=0, column=1, padx=(10, 0)
        )
        ttk.Label(controls, text="Status", style="Caption.Sidebar.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Label(controls, text="Sort by", style="Caption.Sidebar.TLabel").grid(
            row=2, column=1, sticky="w", padx=(12, 0)
        )
        ttk.Combobox(
            controls, textvariable=self.status_filter, values=("All", *STATUSES),
            state="readonly", width=15, style="Sidebar.TCombobox",
        ).grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Combobox(
            controls, textvariable=self.sort_input, values=tuple(SORT_OPTIONS),
            state="readonly", width=20, style="Sidebar.TCombobox",
        ).grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(6, 0))

    def _filter_values(self) -> tuple[str, str, str]:
        return self.search_input.get(), self.status_filter.get(), self.sort_input.get()

    def _set_filter_values(self, values: tuple[str, str, str]) -> None:
        # Restore or reset all controls together, without refreshing three times.
        self._restoring_filters = True
        try:
            self.search_input.set(values[0])
            self.status_filter.set(values[1])
            self.sort_input.set(values[2])
        finally:
            self._restoring_filters = False

    def _on_filters_changed(self, *args: str, select_first: bool = False) -> None:
        if self._restoring_filters:
            return
        requested = self._filter_values()
        if requested == self._active_filters and not select_first:
            return
        if not self._confirm_discard():
            self._set_filter_values(self._active_filters)
            return
        if self.refresh_manga(select_first=select_first):
            self._active_filters = requested
            self.feedback.set("")
        else:
            self._set_filter_values(self._active_filters)

    def reset_filters(self) -> None:
        self._set_filter_values(("", "All", "Title (A–Z)"))
        self._on_filters_changed(select_first=True)

    def _has_filters(self) -> bool:
        return bool(self.search_input.get().strip() or self.status_filter.get() != "All")

    def _build_review_panel(self) -> None:
        self.review_panel = ttk.Frame(self.panel, style="Main.TFrame")
        self.review_panel.grid(row=0, column=0, sticky="nsew")
        self.review_panel.columnconfigure(0, weight=1)
        self.review_panel.rowconfigure(3, weight=1)
        ttk.Label(
            self.review_panel, textvariable=self.review_caption, style="Caption.Main.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.review_heading = ttk.Label(
            self.review_panel, textvariable=self.review_title,
            style="Heading.Main.TLabel", wraplength=400,
        )
        self.review_heading.grid(row=1, column=0, sticky="w", pady=(0, 24))
        ttk.Frame(self.review_panel, height=1, style="Divider.TFrame").grid(
            row=2, column=0, sticky="ew", pady=(0, 24)
        )

        review_area = ttk.Frame(self.review_panel, style="Main.TFrame")
        review_area.grid(row=3, column=0, sticky="nsew")
        review_area.columnconfigure(0, weight=1)
        review_area.rowconfigure(0, weight=1)
        self.review_display = tk.Text(
            review_area, height=10, width=28, wrap="word",
            state="disabled", **text_options(),
        )
        self.review_display.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            review_area, orient="vertical", command=self.review_display.yview, bootstyle="secondary"
        )
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(12, 0))
        attach_scrollbar(self.review_display, scrollbar)

        actions = ttk.Frame(self.review_panel, style="Main.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(24, 0))
        actions.columnconfigure(0, weight=1)
        self.edit_button = ttk.Button(
            actions, text="Edit", command=self.start_edit,
            state="disabled", bootstyle="secondary outline",
        )
        self.edit_button.grid(row=0, column=0, sticky="w")
        self.delete_button = ttk.Button(
            actions, text="Delete selected", command=self.delete_manga,
            state="disabled", bootstyle="danger outline",
        )
        self.delete_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

    def _build_form_panel(self) -> None:
        self.form = ttk.Frame(self.panel, style="Main.TFrame")
        self.form.grid(row=0, column=0, sticky="nsew")
        self.form.columnconfigure(0, weight=1)
        self.form.rowconfigure(8, weight=1)
        ttk.Label(self.form, textvariable=self.form_title, style="Heading.Main.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 24)
        )
        ttk.Label(self.form, text="Title (required)", style="Caption.Main.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        self.title_entry = ttk.Entry(
            self.form, textvariable=self.title_input, style="Editor.TEntry"
        )
        self.title_entry.grid(row=2, column=0, sticky="ew", pady=(6, 16))
        ttk.Label(self.form, text="Status", style="Caption.Main.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        self.status_dropdown = ttk.Combobox(
            self.form, textvariable=self.status_input, values=("Automatic", *STATUSES),
            state="readonly", style="Editor.TCombobox",
        )
        self.status_dropdown.grid(row=4, column=0, sticky="ew", pady=(6, 6))
        self.status_hint_label = ttk.Label(
            self.form, textvariable=self.status_hint, style="Muted.Main.TLabel", wraplength=380
        )
        self.status_hint_label.grid(row=5, column=0, sticky="w", pady=(0, 16))

        numbers = ttk.Frame(self.form, style="Main.TFrame")
        numbers.grid(row=6, column=0, sticky="ew", pady=(0, 16))
        numbers.columnconfigure((0, 1), weight=1)
        ttk.Label(numbers, text="Rating (0–100, optional)", style="Caption.Main.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(numbers, text="Current chapter", style="Caption.Main.TLabel").grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Entry(numbers, textvariable=self.rating_input, width=12, style="Editor.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(6, 0)
        )
        ttk.Entry(numbers, textvariable=self.chapter_input, width=12, style="Editor.TEntry").grid(
            row=1, column=1, sticky="ew", padx=(16, 0), pady=(6, 0)
        )
        ttk.Label(self.form, text="Thoughts / review", style="Caption.Main.TLabel").grid(
            row=7, column=0, sticky="w"
        )
        edit_area = ttk.Frame(self.form, style="Main.TFrame")
        edit_area.grid(row=8, column=0, sticky="nsew", pady=(6, 20))
        edit_area.columnconfigure(0, weight=1)
        edit_area.rowconfigure(0, weight=1)
        self.review_input = tk.Text(
            edit_area, height=5, width=28, wrap="word", **text_options(editable=True)
        )
        self.review_input.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            edit_area, orient="vertical", command=self.review_input.yview, bootstyle="secondary"
        )
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        attach_scrollbar(self.review_input, scrollbar)
        actions = ttk.Frame(self.form, style="Main.TFrame")
        actions.grid(row=9, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        self.save_button = ttk.Button(
            actions, text="Save", command=self.save_manga, bootstyle="primary"
        )
        self.save_button.grid(row=0, column=0, sticky="w")
        self.cancel_button = ttk.Button(
            actions, text="Cancel", command=self.cancel_form, bootstyle="secondary outline"
        )
        self.cancel_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

    def refresh_manga(
        self, preferred_id: int | None = None, *, select_first: bool = False
    ) -> bool:
        try:
            manga = self.library.list_manga(
                search=self.search_input.get(),
                status="" if self.status_filter.get() == "All" else self.status_filter.get(),
                sort=SORT_OPTIONS.get(self.sort_input.get(), ""),
            )
        except (ValueError, sqlite3.Error) as error:
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
        suffix = "matching manga" if self._has_filters() else "manga"
        self.count.set(f"{len(manga)} {suffix}")
        entries = {entry["id"]: entry for entry in manga}
        if select_first:
            selection = ()
        elif preferred_id is not None and preferred_id in entries:
            selection = (preferred_id,)
        else:
            selection = tuple(entry["id"] for entry in manga if entry["id"] in self.selected_ids)
        if not selection and manga:
            selection = (manga[0]["id"],)
        if len(selection) > 1:
            self._show_multiple_selection(selection)
        else:
            self._show_review(entries[selection[0]] if selection else None)
        self.select_all_button.configure(state="normal" if manga else "disabled")
        if selection:
            self.manga_list.selection_set(tuple(str(manga_id) for manga_id in selection))
            self.manga_list.focus(str(selection[0]))
            self.manga_list.see(str(selection[0]))
        return True

    def _show_review(self, entry: sqlite3.Row | None) -> None:
        self._mode = "view"
        self.editing_id = None
        self._form_baseline = {}
        self.selected_id = entry["id"] if entry is not None else None
        self.selected_ids = (self.selected_id,) if self.selected_id is not None else ()
        self.review_caption.set("YOUR REVIEW")
        if entry is None:
            if self.manga_list.get_children():
                self.review_title.set("Select a manga")
                text = "Select a manga from the list to read your review."
            elif self._has_filters():
                self.review_title.set("No matching manga")
                text = "Try another search or status, or use Reset to show the whole library."
            else:
                self.review_title.set("Select a manga")
                text = "Use New manga to add your first entry."
        else:
            self.review_title.set(entry["title"])
            text = entry["review"] or "No review yet."
        self._set_review_text(text)
        self.form.grid_remove()
        self.review_panel.grid()
        state = "normal" if entry is not None else "disabled"
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)

    def _set_review_text(self, text: str) -> None:
        self.review_display.configure(state="normal")
        self.review_display.delete("1.0", "end")
        self.review_display.insert("1.0", text)
        self.review_display.configure(state="disabled")

    def _show_multiple_selection(self, manga_ids: tuple[int, ...]) -> None:
        self._mode = "view"
        self.editing_id = None
        self._form_baseline = {}
        self.selected_id = None
        self.selected_ids = manga_ids
        self.review_caption.set("SELECTION")
        self.review_title.set(f"{len(manga_ids)} manga selected")
        self._set_review_text(
            "Use Delete selected to remove these manga and their reviews.\n\n"
            "Select one manga to read or edit its review."
        )
        self.form.grid_remove()
        self.review_panel.grid()
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="normal")

    def select_all(self, event: tk.Event | None = None) -> str:
        self.manga_list.selection_set(self.manga_list.get_children())
        self.manga_list.focus_set()
        return "break"

    def _restore_selection(self) -> None:
        previous = tuple(
            str(manga_id) for manga_id in self.selected_ids if self.manga_list.exists(str(manga_id))
        )
        self.manga_list.selection_set(previous)

    def _on_manga_selected(self, event: tk.Event | None = None) -> None:
        selection = tuple(int(item) for item in self.manga_list.selection())
        if set(selection) == set(self.selected_ids):
            return
        if not self._confirm_discard():
            self._restore_selection()
            return
        if not selection:
            self._show_review(None)
            self.feedback.set("")
            return
        if len(selection) > 1:
            self._show_multiple_selection(selection)
            self.feedback.set("")
            return
        try:
            entry = self.library.get_manga(selection[0])
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot load manga", str(error), parent=self)
            self._restore_selection()
            return
        self._show_review(entry)
        self.feedback.set("")

    def _form_values(self) -> dict[str, str]:
        return {
            "title": self.title_input.get(),
            "status": "" if self.status_input.get() == "Automatic" else self.status_input.get(),
            "rating": self.rating_input.get(),
            "current_chapter": self.chapter_input.get(),
            "review": self.review_input.get("1.0", "end-1c"),
        }

    def _confirm_discard(self) -> bool:
        if self._mode == "view" or self._form_values() == self._form_baseline:
            return True
        return messagebox.askyesno(
            "Discard unsaved changes?",
            "You have unsaved changes. Discard them and continue?",
            parent=self,
        )

    def _show_form(self, entry: sqlite3.Row | None) -> None:
        self.editing_id = entry["id"] if entry is not None else None
        self._mode = "edit" if entry is not None else "new"
        self.form_title.set("Edit manga" if entry is not None else "New manga")
        self.title_input.set(entry["title"] if entry is not None else "")
        self.status_input.set(entry["status"] if entry is not None else "Automatic")
        self.rating_input.set(
            str(entry["rating"]) if entry is not None and entry["rating"] is not None else ""
        )
        self.chapter_input.set(str(entry["current_chapter"]) if entry is not None else "0")
        self.review_input.delete("1.0", "end")
        if entry is not None:
            self.review_input.insert("1.0", entry["review"])
        self.status_dropdown.configure(values=STATUSES if entry is not None else ("Automatic", *STATUSES))
        self.status_hint.set(
            "Status stays as selected when the chapter changes."
            if entry is not None
            else "Automatic: Not Started at chapter 0; Reading above 0."
        )
        self._form_baseline = self._form_values()
        self.review_panel.grid_remove()
        self.form.grid()
        self.title_entry.focus_set()

    def start_new(self) -> None:
        if self._confirm_discard():
            self._show_form(None)
            self.feedback.set("Enter a new manga, then Save.")

    def start_edit(self) -> None:
        if self.selected_id is None or not self._confirm_discard():
            return
        try:
            entry = self.library.get_manga(self.selected_id)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot edit manga", str(error), parent=self)
            return
        self._show_form(entry)
        self.feedback.set("Edit the fields, then Save or Cancel.")

    def cancel_form(self) -> None:
        if self.refresh_manga(self.selected_id):
            self.feedback.set("Changes cancelled.")
            self.manga_list.focus_set()

    def save_manga(self) -> None:
        if self._mode == "view":
            return
        values = self._form_values()
        try:
            if self.editing_id is None:
                manga_id = self.library.add_manga(**values)
                action = "Added"
            else:
                manga_id = self.editing_id
                self.library.update_manga(manga_id, **values)
                action = "Saved"
        except ValueError as error:
            messagebox.showerror("Check your entry", str(error), parent=self)
            return
        except sqlite3.Error as error:
            messagebox.showerror("Cannot save manga", f"Your manga could not be saved.\n\n{error}", parent=self)
            return

        # Saving has succeeded; the draft must not be submitted a second time.
        self._show_review(None)
        self.feedback.set(f'{action} "{values["title"].strip()}".')
        if self.refresh_manga(manga_id) and self.selected_id != manga_id:
            self.feedback.set(
                f'{action} "{values["title"].strip()}". Hidden by the current search or status filter.'
            )
        self.manga_list.focus_set()

    def delete_manga(self) -> None:
        if not self.selected_ids or self._mode != "view":
            return
        manga_ids = list(self.selected_ids)
        try:
            if len(manga_ids) == 1:
                entry = self.library.get_manga(manga_ids[0])
                prompt = f'Delete "{entry["title"]}"?'
            else:
                prompt = f"Delete {len(manga_ids)} manga?"
            if not messagebox.askyesno("Delete selected manga?", prompt, parent=self):
                return
            deleted = self.library.delete_manga_many(manga_ids)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot delete manga", str(error), parent=self)
            return
        self.feedback.set(f"Deleted {deleted} manga.")
        self.refresh_manga()
        self.manga_list.focus_set()

    def _close_window(self) -> None:
        if self._confirm_discard():
            self.destroy()
