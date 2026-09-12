# Spec: Profile Page Design

## Overview

Turn `/profile` from the placeholder string `"Profile page — coming in Step 4"`
into a real, styled account page. After Step 3 a user can sign in and the navbar
shows their first name, but there is nowhere to go that confirms *whose* account
is open. This step adds a read-only profile page that renders the signed-in
user's details — name, email, and the date they joined — in a card that matches
Spendly's existing paper/ink visual language (the same tokens and card patterns
as the auth and legal pages). It is the first route that requires a logged-in
session: visiting `/profile` while signed out redirects to `/login`.

Scope is deliberately narrow. This is a **display-only** page. It does **not**
let the user edit their name, change their email, change their password, upload
an avatar, or delete their account — those are later steps. It does **not** show
any spending totals, charts, or expense history (the expense feature does not
exist yet — Steps 7+). It does **not** add a reusable `@login_required`
decorator; `/profile` does its own one-line session check and every other
placeholder route keeps its exact `"... coming in Step N"` string.

## Depends on

- **Step 1 — Database setup** (complete). `get_db()` and the `users` table
  exist; `users` has `name`, `email`, and `created_at`.
- **Step 3 — Login and Logout** (complete). `session["user_id"]` /
  `session["user_name"]` are set on sign-in and cleared on logout;
  `app.secret_key` is configured; `base.html` already renders a session-aware
  `.nav-links` block with a `.nav-user` label.

## Routes

- `GET /profile` — renders `profile.html` with the current user's row. If
  `session.get("user_id")` is missing, redirect to `url_for("login")` before
  any DB access. If the session holds an id that no longer exists in `users`
  (stale cookie), clear the session and redirect to `login`. — logged-in only
  *(replaces the current placeholder route)*

No other route changes. `/expenses/add`, `/expenses/<id>/edit`,
`/expenses/<id>/delete` keep their exact placeholder strings.

## Database changes

**No database changes.** No new table, column, constraint, or index. The
`users` table already has everything the page reads (`name`, `email`,
`created_at`).

One new **function** is added to `database/db.py` (not a schema change):

- `get_user_by_id(user_id)` — parameterised
  `SELECT * FROM users WHERE id = ?`, returns the `sqlite3.Row` or `None`.
  Placed beside `get_user_by_email()`, same connection/`finally: conn.close()`
  shape.

## Templates

**Create:**

- `templates/profile.html` — `{% extends "base.html" %}`. A `profile-section`
  wrapper containing:
  - A header with a circular monogram (the user's first initial, CSS-drawn —
    no image), the user's full name as an `<h1>`, and the email as a subtitle.
  - A details card (reusing the `.auth-card` / `.legal-body` card look) listing
    labelled rows: **Full name**, **Email address**, **Member since**
    (the `created_at` date, formatted like the legal pages, e.g.
    "3 September 2026").
  - A footer line with a "Log out" link to `{{ url_for('logout') }}`.
  - No `{% block scripts %}` — this page needs no JavaScript.

**Modify:**

- `templates/base.html` — wrap the existing `.nav-user` name in a link to
  `{{ url_for('profile') }}` so the navbar name is the way in. Keep the
  `.nav-user` class on the element (or move it to the anchor) so the existing
  style still applies; the logged-out branch is unchanged.

## Files to change

- `app.py`
  - Import `get_user_by_id` from `database.db` (alongside the existing imports).
  - Replace the `profile()` placeholder body: session check → redirect to
    `login` if signed out; `get_user_by_id(session["user_id"])`; if `None`,
    `session.clear()` + redirect to `login`; otherwise
    `render_template("profile.html", user=user)`.
- `database/db.py` — add `get_user_by_id()` next to `get_user_by_email()`.
- `templates/base.html` — link the `.nav-user` label to `/profile`.
- `static/css/style.css` — add a `/* Profile page */` section with `.profile-*`
  rules, following the existing `.auth-*` / `.legal-*` sections. Reuse `:root`
  tokens (`--ink`, `--ink-muted`, `--paper-card`, `--border`, `--accent`,
  `--accent-light`, `--radius-md`, `--font-display`, `--max-width`) — no new
  file, no page-scoped `<style>` block, no hardcoded colors.

## Files to create

- `templates/profile.html`

## New dependencies

**No new dependencies.** Flask's `session` / `render_template` / `redirect` /
`url_for` and `sqlite3` cover everything. Date formatting uses the stdlib
`datetime` module (or a Jinja expression in the template).

## Rules for implementation

- No SQLAlchemy or ORMs — `sqlite3` only.
- Parameterised queries only — never f-strings or `%` formatting in SQL.
- Passwords hashed with `werkzeug` (unchanged here — the page never reads,
  renders, or logs `password_hash`).
- All SQL lives in `database/db.py`; `app.py` never opens a connection or writes
  a query itself. Every connection is closed in a `finally:` block, matching the
  existing `get_db()` pattern.
- Use CSS variables — never hardcode hex values. All new rules reuse existing
  `:root` tokens.
- All templates extend `base.html`.
- Vanilla JS only — and this feature needs none. Do not add a
  `{% block scripts %}` or touch `static/js/main.js`.
- Currency is not shown on this page; if any amount ever appears, it is the
  Indian rupee (`&#8377;` / ₹).
- Do not add a reusable auth decorator, do not protect any route other than
  `/profile`, do not build or alter any other `"coming in Step N"` placeholder.
- Do not add edit/delete/avatar-upload functionality or any spending summary.
- Commit message prefix: `profile:` (e.g.
  `profile: add read-only account page and route`).

## Definition of done

Run `python app.py` and check each against `http://localhost:5001`:

- [ ] Visiting `/profile` while signed out redirects to `/login`.
- [ ] Signing in as `demo@spendly.com` / `demo123`, then visiting `/profile`
      (or clicking the name in the navbar) shows a page with the heading
      "Demo User", the email `demo@spendly.com`, and a "Member since" date.
- [ ] The navbar name is a link that lands on `/profile`.
- [ ] The monogram shows the user's first initial ("D") and is drawn in CSS
      (no `<img>` request in the network tab).
- [ ] "Member since" reads as a human date (e.g. "3 September 2026"), not a raw
      `2026-09-03 12:34:56` timestamp.
- [ ] The page visually matches Spendly — paper background, white card with
      `--border`, serif display heading — with no hardcoded hex values in the
      new CSS (`grep -E '#[0-9a-fA-F]{3,6}'` over the added `.profile-*` block
      finds nothing).
- [ ] The "Log out" link on the page ends the session and returns to `/login`;
      `/profile` then redirects to `/login` again.
- [ ] Registering a brand-new account, signing in, and opening `/profile` shows
      that new user's name and email.
- [ ] `password_hash` never appears in the page source.
- [ ] App starts with no errors; `/`, `/register`, `/login`, `/logout`,
      `/terms`, and the `/expenses/*` placeholders are unaffected.
