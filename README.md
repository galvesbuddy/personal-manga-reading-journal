# Personal Manga Reading Journal

A local desktop manga journal built with Python, Tkinter, and SQLite. The
current version lets you add manga and displays your saved library across
application restarts. The interface is a basic functional version; visual
styling, editing, deletion, search, filtering, and sorting are future steps.

## Setup (Git Bash on Windows)

All commands and relative paths in this README assume your current directory
is the project root, `personal-manga-reading-journal/`. Use a Unix-based terminal to run the commands below.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements/requirements.txt
```

Windows virtual environments use `Scripts/`, even in Git Bash. In each new
terminal session, run `source .venv/Scripts/activate` before using the project.

The requirements file lists third-party packages; pip installs them into
`.venv`. Currently, PyInstaller is the only third-party dependency, used to
package the app as an executable. Its own dependencies are installed by pip.

Tkinter/ttk and `sqlite3` are standard-library modules normally included with
Windows Python installations. Do not install packages named `tkinter` or
`sqlite3` with pip. If either module is missing, modify or reinstall Python
with the corresponding support enabled.

Verify Tkinter by opening its demonstration window:

```bash
python -m tkinter
```

In VS Code, use **Python: Select Interpreter** to select
`.venv/Scripts/python.exe`.

## Run the application

With the virtual environment active, run:

```bash
python main.py
```

A window titled **Manga Library** opens with a saved-manga list and an entry
form. Enter a title and click **Add manga**. Titles are trimmed and cannot be
blank. Other fields are optional:

- **Status:** Automatic saves Not Started at chapter 0, or Reading above 0.
  An explicit selection always takes priority.
- **Rating:** a whole number from 0 to 100. Leaving it blank means Unrated;
  a rating of 0 is a valid score.
- **Current chapter:** a finite, nonnegative number, including decimals such
  as 10.5. Leaving it blank means 0.
- **Thoughts / review:** optional free-form text saved with the entry.

Successful additions clear the form and select the saved entry in the list.
The list currently displays titles alphabetically. Selecting a row does not
yet open an editor or review viewer.

## Local storage

On Windows, the app creates and reuses:

```text
%LOCALAPPDATA%/MangaLibrary/library.sqlite3
```

This is usually under `C:/Users/<username>/AppData/Local/`. The location is
resolved in `default_database_path()` in `manga_journal/database.py`, so the
app does not hardcode a drive letter. Data stays separate from the executable
and source code. Rebuilding or moving the executable does not move the library.

The single `manga` table contains `id`, `title`, `status`, `rating`,
`current_chapter`, and `review`. SQL constraints back up input validation, and
parameterized queries keep user text separate from SQL instructions.

## Verify the first workflow

Add a manga with chapter 10.5 and no explicit status. Confirm the list shows
Reading, then close and reopen the app to confirm the entry remains. Add one
manga with a rating of 0 and another with the rating blank; they should display
0 and Unrated respectively. Invalid entries should show an explanation and
leave the form intact.

Run the automated storage and validation checks with:

```bash
python -m unittest discover -v
```

Tests use temporary databases and do not modify your personal library.

## Build a Windows executable

From the project root, with the virtual environment active:

```bash
python -m PyInstaller --onedir --name MangaLibrary --specpath build main.py
./dist/MangaLibrary/MangaLibrary.exe
```

This initial build keeps a console available for debugging. Distribute the
entire `dist/MangaLibrary/` folder, including its supporting files (make a dir for debugging ease). Generated
build files and the packaging specification go under `build/`; the finished
application goes under `dist/`. On a repeat folder build, PyInstaller may ask
to replace the previous output. Add `--noconfirm` to skip that prompt.

For a single executable with no console window:

```bash
python -m PyInstaller --onefile --windowed --name MangaLibrary --specpath build main.py
./dist/MangaLibrary.exe
```

Build on Windows to produce a Windows executable. The packaged application
includes its Python runtime, so the recipient does not need Python installed.

## Code layout

```text
main.py                       # Entry point: starts the app's event loop
manga_journal/
    __init__.py               # Marks the directory as a Python package
    ui.py                     # Defines the Tkinter window
    library.py                # Validates inputs and applies status defaults
    database.py               # Resolves storage location and runs SQLite queries
requirements/
    requirements.txt          # Third-party dependency list
tests/
    __init__.py
    test_library.py            # Validation, persistence, and database constraints
```

Each Python package directory includes an `__init__.py` file.

## Leave the virtual environment

When finished:

```bash
deactivate
```

