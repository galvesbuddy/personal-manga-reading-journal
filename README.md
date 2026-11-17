# Personal Manga Reading Journal

A local desktop manga journal built with Python and Tkinter. The current
version opens a minimal, resizable window. SQLite storage and manga management
are the next steps.

## Setup (Git Bash on Windows)

All commands and relative paths in this README assume your current directory
is the project root, `personal-manga-reading-journal/`. Use Git Bash to run
the commands below.

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

A window titled **Manga Library** opens. It is intentionally empty for this
first step; close it with the window's normal close button.

## Build a Windows executable

From the project root, with the virtual environment active:

```bash
python -m PyInstaller --onedir --name MangaLibrary --specpath build main.py
./dist/MangaLibrary/MangaLibrary.exe
```

This initial build keeps a console available for debugging. Distribute the
entire `dist/MangaLibrary/` folder, including its supporting files (make a dir for debugging ease). Generated
build files, including the packaging specification, go under `build/`.

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
requirements/
    requirements.txt          # Third-party dependency list
```

Each Python package directory includes an `__init__.py` file.

## Leave the virtual environment

When finished:

```bash
deactivate
```

