# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Spendly" — a personal expense tracker built with Flask + server-rendered Jinja
templates + SQLite. It is a **staged teaching scaffold**: `app.py` ships real
routes for the pages that exist (`/`, `/register`, `/login`, `/terms`) and
placeholder routes that return `"... coming in Step N"` strings for features not
yet built (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`,
`/expenses/<id>/delete`). `database/db.py` is a stub describing the
`get_db()` / `init_db()` / `seed_db()` functions to be written.

Implication: do not build out future "Step N" functionality unless the current
task explicitly asks for it. Most tasks here are small, single-page changes
(see `file.txt` for the running log of prompts given so far).

## Working from specs

Steps are specified one at a time in `.claude/specs/NN-<name>.md` (e.g.
`.claude/specs/01-database-setup.md`). When a task refers to a step or a spec,
read the matching file first — it carries the exact schema, function contracts,
fixed value lists, and definition-of-done for that step. Implement only what the
spec for the current step covers.

## Commands

Windows / PowerShell, virtualenv lives in `venv/`:

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py                       # serves on http://localhost:5001 (debug=True)
```

Tests: `pytest` and `pytest-flask` are declared in `requirements.txt` but no
test suite exists yet. When adding tests, run all with `pytest` and a single
test with `pytest path/to/test_file.py::test_name`.

## Architecture

- **`app.py`** — the entire application: `Flask(__name__)` at module level, all
  routes inline, `app.run(debug=True, port=5001)`. No blueprints, no app factory,
  no config module.
- **`database/`** — a package (`database/__init__.py` is empty); import as
  `from database.db import get_db, init_db, seed_db`. `db.py` is the intended
  single source of DB access. SQLite file lives at repo root (gitignored;
  `expense_tracker.db`).
- **`templates/`** — every page `{% extends "base.html" %}`. `base.html` provides
  the navbar, footer, and loads `style.css` then `main.js`. Pages inject
  page-scoped CSS via `{% block head %}` and page-scoped JS via
  `{% block scripts %}` (see `landing.html` for the pattern).
- **`static/css/style.css`** — one global stylesheet. All colors, fonts, radii,
  and widths are CSS custom properties defined in `:root` (`--ink`, `--paper`,
  `--accent`, `--radius-md`, `--font-display`, etc.). Use these tokens rather
  than hardcoded values; match existing class-naming (`hero-*`, `auth-*`,
  `feature-*`, `form-*`).
- **`static/js/main.js`** — currently just a placeholder comment. **Vanilla JS
  only** — this project deliberately uses no JS framework or third-party
  libraries. Page-specific scripts go in that page's `{% block scripts %}` as an
  IIFE.

## Conventions

- Auth forms (`login.html`, `register.html`) already `POST` to `/login` and
  `/register`; those routes currently only handle `GET`. Wiring them up is a
  later step.
- Templates render an `{{ error }}` variable in an `.auth-error` block when
  passed one.
- Currency throughout the UI is the Indian rupee (`&#8377;` / ₹).
- Commit messages use a lowercase area prefix, e.g.
  `landing: add privacy policy page and route`.

### Data layer (when implementing `database/db.py`)

- No ORM (no SQLAlchemy) — use the stdlib `sqlite3` only.
- Parameterized queries only; never string-format values into SQL.
- Every connection sets `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`.
- Store money in an `amount` REAL column; dates as `YYYY-MM-DD` text.
- Hash passwords with `werkzeug.security.generate_password_hash`.
- `init_db()` uses `CREATE TABLE IF NOT EXISTS` and `seed_db()` is idempotent
  (bail out if data already exists) — both safe to run on every startup.
