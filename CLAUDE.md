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
- **`database/db.py`** — intended single source of DB access. SQLite file is
  `expense_tracker.db` at repo root (gitignored). Connections should set
  `row_factory` and enable foreign keys (`PRAGMA foreign_keys = ON`).
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
