# Spec: Login and Logout

## Overview

Turn `/login` from a form that goes nowhere into real authentication, and make
the `/logout` placeholder actually end a session. Today `login.html` POSTs to
`/login`, but the route is GET-only, so submitting 405s; `/logout` returns the
string `"Logout — coming in Step 3"`. This step adds POST handling to `/login`,
verifies the submitted email/password against the `password_hash` written by
Step 2 (Registration), and — on success — records the user in a Flask
`session`. `/logout` clears that session. This is the first feature to use
`session` and therefore the first to require `app.secret_key`. It authenticates
against the exact rows Step 2 creates and the seeded `demo@spendly.com` user.

Scope is deliberately narrow: log a real user in, keep them logged in across
requests, log them out. It does **not** build `/profile`, does **not** protect
the expense routes, and does **not** add "remember me", password reset, or
rate limiting. The navbar gains a logged-in state only so there is a visible
way to reach logout.

## Depends on

- **Step 1 — Database setup** (complete). `get_db()` and the `users` table
  exist.
- **Step 2 — Registration** (complete). `get_user_by_email()` and
  `create_user()` exist in `database/db.py`; real users with `werkzeug`
  password hashes can be created; `login.html` already renders `success` and
  `error` banners and POSTs to `/login`.

## Routes

- `GET /login` — renders the sign-in form; shows the `registered=1` success
  banner as today. If the user is already logged in, redirect to `/` — public
  *(already exists; gains `methods=["GET", "POST"]`)*
- `POST /login` — validates the form, verifies credentials, sets
  `session["user_id"]` and `session["user_name"]` on success and redirects to
  `/`; on failure re-renders `login.html` with a generic `error` and HTTP 200 —
  public
- `GET /logout` — clears the session and redirects to `/login` — replaces the
  current placeholder; behaves the same whether or not anyone was logged in —
  public

No other route changes. The `/profile`, `/expenses/*` placeholders keep their
exact `"... coming in Step N"` strings.

## Database changes

**No database changes.** No new table, column, constraint, or index. The
`users` table already has `email` (UNIQUE) and `password_hash`.

One new **function** is added to `database/db.py` (not a schema change):

- `verify_credentials(email, password)` — looks up the user by normalised
  email via the same query shape as `get_user_by_email`, checks the supplied
  password with `werkzeug.security.check_password_hash`, and returns the
  `sqlite3.Row` on a match or `None` on any failure (unknown email or wrong
  password). It must not reveal which of the two failed.

## Templates

**Create:**

- None.

**Modify:**

- `templates/login.html`
  - No structural change. The existing `{% if success %}` / `{% if error %}`
    blocks and the `POST /login` form already match what the route will pass.
    Add `autocomplete="email"` / `autocomplete="current-password"` to the two
    inputs while here (optional polish, no behaviour change).
- `templates/base.html`
  - Make the `.nav-links` block session-aware. When `session.user_id` is set,
    show the user's first name (or `session.user_name`) and a
    `Log out` link to `{{ url_for('logout') }}` in place of the
    "Sign in" / "Get started" links. When it is not set, render exactly what
    is there today.
  - Use `session` directly in the template (Flask puts it in the Jinja
    context); do not require every route to pass a `user` variable.

## Files to change

- `app.py`
  - Set `app.secret_key` from `os.environ.get("SECRET_KEY", "<dev-only
    fallback>")` near the `Flask(__name__)` line, with a comment that the
    fallback is for local dev only.
  - Import `session` from `flask`; import `verify_credentials` from
    `database.db`.
  - Replace the `login` route with a GET/POST handler as described in Routes.
  - Replace the `logout` placeholder body with `session.clear()` +
    `redirect(url_for("login"))`.
- `database/db.py` — add `verify_credentials()` beside `get_user_by_email()`.
- `templates/login.html` — optional input `autocomplete` attributes only.
- `templates/base.html` — session-aware `.nav-links`.
- `static/css/style.css` — only if the logged-in navbar needs a new rule
  (e.g. a `.nav-user` label). Reuse existing `:root` tokens and the
  `.nav-links` / `.nav-cta` patterns; no new file.

## Files to create

- None.

## New dependencies

**No new dependencies.** `flask` (ships `session`, signed cookies),
`werkzeug.security.check_password_hash`, and `os` (stdlib) cover everything.

## Validation rules

Server-side, on `POST /login`, return the **first** failure as `error` with
HTTP 200 and the form re-rendered:

| Field | Rule | Error message |
| --- | --- | --- |
| email, password | both present after `.strip()` on email (password never stripped) | `"Please enter your email and password."` |
| credentials | `verify_credentials(email, password)` returns a row | `"Incorrect email or password."` |

- The credentials error is intentionally generic — never say "no such account"
  vs "wrong password", and never echo the password back into the template.
- Normalise email with `.strip().lower()` before lookup, matching Step 2.
- On success, set `session["user_id"]` and `session["user_name"]`, then
  `redirect(url_for("landing"))`.

## Rules for implementation

- No SQLAlchemy or ORMs — `sqlite3` only.
- Parameterised queries only. Never f-strings or `%` formatting in SQL.
- Passwords are verified with `werkzeug.security.check_password_hash`. The
  plain password is never stored, logged, or written back into the template.
- All SQL lives in `database/db.py`; `app.py` never opens a connection or
  writes a query itself. Every connection is closed in a `finally:` block,
  matching the existing `get_db()` pattern.
- `app.secret_key` comes from the environment with a clearly-commented
  dev-only fallback. Do not commit a real secret.
- Use CSS variables — never hardcode hex values. Any navbar rule reuses
  existing `:root` tokens.
- All templates extend `base.html`.
- Vanilla JS only. This feature needs **no** JavaScript — do not add a
  `{% block scripts %}`.
- Do not add `flash()` (keep the existing `error` / `success` variable
  pattern), do not add login-required protection to any route, do not build
  `/profile` or touch any other placeholder route.

## Definition of done

Run `python app.py` and check each against `http://localhost:5001`:

- [ ] `GET /login` renders exactly as it does today; `GET /login?registered=1`
      still shows the green "Account created — please sign in." banner.
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/` and the
      navbar now shows the user's name and a "Log out" link instead of
      "Sign in" / "Get started".
- [ ] `DEMO@spendly.com` / `demo123` also signs in (case-insensitive email).
- [ ] A wrong password for `demo@spendly.com` re-renders `/login` with
      "Incorrect email or password." and no session is set (navbar unchanged).
- [ ] An unknown email shows the same "Incorrect email or password." message —
      not a different one.
- [ ] Submitting with an empty email or empty password shows
      "Please enter your email and password."
- [ ] After signing in, visiting `/` in the same browser still shows the
      logged-in navbar (session persists across requests).
- [ ] Clicking "Log out" redirects to `/login`, and the navbar returns to
      "Sign in" / "Get started"; visiting `/` confirms the session is gone.
- [ ] `GET /logout` when not logged in still redirects to `/login` without
      error.
- [ ] Registering a brand-new account (Step 2 flow) and then signing in with
      those credentials works end to end.
- [ ] The password is never present in the page source after a failed login.
- [ ] App starts with no errors; `/`, `/register`, and `/terms` are
      unaffected.
