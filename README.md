# Personal Manga Reading Journal

A local desktop manga journal, planned with Python, Tkinter/ttk, and SQLite.

## Setup (Git Bash on Windows)

All commands and relative paths in this README assume your current directory
is the project root, `personal-manga-reading-journal/`. Use Git Bash to run
the commands below. For example, `requirements/requirements.txt` refers to
the file inside this project's `requirements/` folder.

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

When finished, leave the virtual environment with:

```bash
deactivate
```

Application implementation and executable packaging are the next steps.
