"""The app's Paperback-inspired palette, typography, and ttk styles."""

import tkinter as tk

import ttkbootstrap as ttk


THEME_NAME = "manga-dark"
PANEL_PADDING = 24
READING_PADDING = 32

COLORS = {
    "sidebar": "#151516",
    "main": "#1B1B1F",
    "input": "#25252B",
    "text": "#E8E8ED",
    "muted": "#A2A2AD",
    "border": "#33333C",
    "accent": "#F2646D",
    "primary": "#C93643",
    "selection": "#4A252C",
    "disabled": "#666671",
}

FONTS = {
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "caption": ("Segoe UI", 9, "bold"),
    "title": ("Segoe UI", 21, "bold"),
    "heading": ("Segoe UI", 23, "bold"),
    "review": ("Segoe UI", 12),
}

def register_theme() -> None:
    """Register before each root is created, including fresh roots in UI tests."""
    ttk.Theme(
        name="manga",
        primary=COLORS["primary"],
        secondary="#858590",
        success="#598C76",
        info="#8D9DBD",
        warning="#C7A16A",
        danger=COLORS["primary"],
        neutral="#858590",
        dark={"background": COLORS["main"], "foreground": COLORS["text"]},
    ).register()


def apply_styles(app: ttk.App) -> None:
    """Style existing ttk controls; classic Text widgets are colored in ui.py."""
    style = app.style
    app.configure(background=COLORS["main"])
    app.option_add("*TCombobox*Listbox.background", COLORS["input"])
    app.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    app.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    app.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])

    for name, color in (("Sidebar", "sidebar"), ("Main", "main"), ("Input", "input")):
        style.configure(f"{name}.TFrame", background=COLORS[color])
        style.configure(
            f"{name}.TLabel", background=COLORS[color], foreground=COLORS["text"], font=FONTS["body"]
        )
        style.configure(
            f"Muted.{name}.TLabel", background=COLORS[color], foreground=COLORS["muted"], font=FONTS["small"]
        )
        style.configure(
            f"Caption.{name}.TLabel", background=COLORS[color], foreground=COLORS["muted"], font=FONTS["caption"]
        )

    style.configure("Divider.TFrame", background=COLORS["border"])
    style.configure("Title.Sidebar.TLabel", font=FONTS["title"])
    style.configure("Heading.Main.TLabel", font=FONTS["heading"])
    style.configure("Accent.Sidebar.TLabel", foreground=COLORS["accent"], font=FONTS["caption"])

    for prefix in ("Sidebar", "Editor"):
        for kind in ("TEntry", "TCombobox"):
            name = f"{prefix}.{kind}"
            style.configure(
                name, fieldbackground=COLORS["input"], background=COLORS["input"],
                foreground=COLORS["text"], bordercolor=COLORS["border"],
                lightcolor=COLORS["border"], darkcolor=COLORS["border"],
                insertcolor=COLORS["text"], padding=(10, 8), font=FONTS["body"],
            )
            style.map(
                name,
                fieldbackground=[("readonly", COLORS["input"])],
                foreground=[("disabled", COLORS["disabled"]), ("readonly", COLORS["text"])],
                bordercolor=[("focus", COLORS["accent"])],
            )

    style.configure(
        "Library.Treeview", background=COLORS["sidebar"], fieldbackground=COLORS["sidebar"],
        foreground=COLORS["text"], bordercolor=COLORS["sidebar"], borderwidth=0,
        rowheight=34, font=FONTS["body"], relief="flat",
    )
    style.map(
        "Library.Treeview", background=[("selected", COLORS["selection"])],
        foreground=[("selected", COLORS["text"])], bordercolor=[("focus", COLORS["sidebar"])],
    )
    style.configure(
        "Library.Treeview.Heading", background=COLORS["sidebar"], foreground=COLORS["muted"],
        bordercolor=COLORS["sidebar"], font=FONTS["caption"], padding=(8, 10), relief="flat",
    )
    style.map("Library.Treeview.Heading", background=[("active", COLORS["input"])])
    style.configure("TButton", padding=(12, 8), font=FONTS["body"])


def text_options(*, editable: bool = False) -> dict:
    """Classic Tk text areas need explicit colors and selection styling."""
    return {
        "background": COLORS["input"] if editable else COLORS["main"],
        "foreground": COLORS["text"],
        "insertbackground": COLORS["accent"],
        "selectbackground": COLORS["selection"],
        "selectforeground": COLORS["text"],
        "highlightthickness": 1 if editable else 0,
        "highlightbackground": COLORS["border"],
        "highlightcolor": COLORS["accent"],
        "borderwidth": 0,
        "relief": "flat",
        "font": FONTS["body"] if editable else FONTS["review"],
        "padx": 12 if editable else 0,
        "pady": 10 if editable else 0,
        "spacing1": 0,
        "spacing2": 4,
        "spacing3": 8,
    }


def attach_scrollbar(widget: tk.Text | ttk.Treeview, scrollbar: ttk.Scrollbar) -> None:
    """Keep the reading area clear when all of its content already fits."""
    def update(first: str, last: str) -> None:
        scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            scrollbar.grid_remove()
        else:
            scrollbar.grid()

    widget.configure(yscrollcommand=update)
