# Spec: Registration

## Overview

Wire up the existing `register.html` form so that submitting it actually
creates a user row in the `users` table. Today `/register` is GET-only and the
form POSTs into a route that does not accept POST, so the page 405s on submit.
This step adds POST handling, server-side validation, `werkzeug` password
hashing, and two thin data-access helpers in `database/db.py`. It is the first
feature that writes user data, and it is what Step 3 (login/logout) will
authenticate against.

Registration does **not** log the user in. Sessions, `flash()`, and
`app.secret_key` are Step 3 territory and are explicitly out of scope here — on
success we redirect to `/login` with a success banner.

## Depends on

- **Step 1 — Database setup** (complete). `get_db()`, `init_db()`, and the
  `users` table with its `UNIQUE` email constraint already exist in
  `database/db.py`.

## Routes

- `GET /register` — renders the registration form — public *(already exists;
  gains `methods=["GET", "POST"]`)*
- `POST /register` — validates input, creates the user, redirects to
  `/login?registered=1` on success; re-renders `register.html` with `error` on
  failure — public
- `GET /login` — unchanged behaviour, but now reads the `registered` query
  parameter to show a one-line success banner — public

No other new routes. The `"... coming in Step N"` placeholders in `app.py` stay
exactly as they are.

## Database changes

**No database changes.** The `users` table created in Step 1 already has every
column this feature needs (`name`, `email` UNIQUE, `password_hash`,
`created_at` defaulted). No migration, no new table, no new column.

Two new **functions** are added to `database/db.py` (not schema changes):

- `get_user_by_email(email)` — returns a `sqlite3.Row` or `None`
- `create_user(name, email, password)` — hashes the password with
  `generate_password_hash`, inserts the row, returns the new `id`

## Templates

**Create:**

- None.

**Modify:**

- `templates/register.html`
  - Repopulate `name` and `email` on a failed submit via
    `value="{{ name or '' }}"` / `value="{{ email or '' }}"` so the user does
    not retype them. Never repopulate the password field.
  - Add `minlength="8"` to the password input to match the server rule.
  - Keep the existing `{% if error %}<div class="auth-error">` block as-is; the
    route already passes `error` in the shape it expects.
- `templates/login.html`
  - Add a `{% if success %}<div class="auth-success">{{ success }}</div>{% endif %}`
    block directly above the existing `{% if error %}` block inside
    `.auth-card`.

## Files to change

- `app.py` — import `redirect`, `url_for`, `request` from `flask`; import
  `create_user`, `get_user_by_email` from `database.db`; replace the `register`
  route with a GET/POST handler; pass `success` into the `login` route.
- `database/db.py` — add `get_user_by_email()` and `create_user()`.
- `templates/register.html` — see above.
- `templates/login.html` — see above.
- `static/css/style.css` — add an `.auth-success` rule mirroring `.auth-error`,
  using `--accent-light` / `--accent` / `--radius-sm`.

## Files to create

- None.

## New dependencies

**No new dependencies.** `flask`, `werkzeug`, `sqlite3` (stdlib) and
`re` (stdlib, for the email check) cover everything.

## Validation rules

Validate on the server in this order, returning the **first** failure as
`error` with HTTP 200 and the form re-rendered:

| Field | Rule | Error message |
| --- | --- | --- |
| all | strip whitespace, all three required | `"Please fill in every field."` |
| name | at least 2 characters after stripping | `"Please enter your full name."` |
| email | matches a simple `^[^@\s]+@[^@\s]+\.[^@\s]+$` check | `"Please enter a valid email address."` |
| password | at least 8 characters | `"Password must be at least 8 characters."` |
| email | not already in `users` | `"An account with that email already exists."` |

Store the email lowercased and stripped. Wrap the insert in a
`try/except sqlite3.IntegrityError` as a second line of defence against the
duplicate-email race, returning the same "already exists" error.

## Rules for implementation

- No SQLAlchemy or ORMs — `sqlite3` only.
- Parameterised queries only. Never f-strings or `%` formatting in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash`. The plain
  password is never stored, logged, or echoed back into the template.
- All SQL lives in `database/db.py`. `app.py` never opens a connection or
  writes a query itself.
- Every connection is closed in a `finally:` block, matching the existing
  `get_db()` usage pattern in `db.py`.
- Use CSS variables — never hardcode hex values. `.auth-success` must reuse the
  existing `:root` tokens.
- All templates extend `base.html`. No new stylesheet file; `.auth-success`
  goes in the auth section of `static/css/style.css` beside `.auth-error`.
- Vanilla JS only — this feature needs **no** JavaScript at all. Do not add a
  `{% block scripts %}` to either auth template.
- Do not add `app.secret_key`, `session`, or `flash()`. Do not touch the
  placeholder routes. Do not build login authentication.

## Definition of done

Run `python app.py` and check each of these against `http://localhost:5001`:

- [ ] `GET /register` renders the form exactly as it does today — no visual change.
- [ ] Submitting a valid new name/email/password redirects to `/login` and shows
      a green success banner reading "Account created — please sign in."
- [ ] `sqlite3 expense_tracker.db "SELECT name, email, password_hash FROM users"`
      shows the new row, with a `password_hash` starting `scrypt:` or `pbkdf2:` —
      never the plain password.
- [ ] Submitting the same email a second time re-renders `/register` with
      "An account with that email already exists." and creates no second row.
- [ ] Registering with `DEMO@spendly.com` is rejected as a duplicate of the
      seeded `demo@spendly.com` (case-insensitive match).
- [ ] A 7-character password is rejected with
      "Password must be at least 8 characters." and no row is created.
- [ ] `notanemail` is rejected with "Please enter a valid email address."
- [ ] After any failed submit, the name and email fields are still filled in and
      the password field is empty.
- [ ] The error banner uses `.auth-error` and the success banner `.auth-success`;
      both read correctly against the `--paper` background.
- [ ] `GET /login` with no query parameter shows no banner.
- [ ] The app starts with no errors and `/`, `/login`, `/terms` are unaffected.
