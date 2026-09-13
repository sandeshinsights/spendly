# Spec: Add Expense

## Overview
Step 7 replaces the `/expenses/add` placeholder with a real feature that lets a
logged-in user record a new expense. It introduces a form page for entering an
amount, category, date, and optional description, and wires it to an insert
against the existing `expenses` table. Once submitted, the new expense should
immediately be reflected on the profile page's transaction list, summary
stats, and category breakdown, since those already read live from the
database (Step 5).

## Depends on
- Step 1: Database setup (`expenses` table and `get_db()` exist)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile page (profile reads live expense data,
  so a new expense is visible immediately after redirect)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate input and insert the expense — logged-in only

Both methods live on the existing `/expenses/add` route (replacing the
placeholder), following the same GET/POST-on-one-route pattern already used by
`/register` and `/login`. An unauthenticated request to either method
redirects to `/login`, matching the guard already used on `/profile`.

## Database changes
No database changes. The `expenses` table already has all required columns
(`user_id`, `amount`, `category`, `date`, `description`, `created_at`).

## Templates
- **Create:** `templates/add_expense.html` — form with fields for amount,
  category (select, populated from `CATEGORIES` in `database/db.py`), date
  (defaulting to today), and description (optional). Follows the
  `auth-card` / `form-group` / `form-input` markup pattern used in
  `register.html`, and renders `{{ error }}` in a block the same way auth
  pages do.
- **Modify:** `templates/profile.html` — add an "Add expense" link/button
  (e.g. near the transaction list heading) pointing at
  `{{ url_for('add_expense') }}`. No other structural changes.

## Files to change
- `app.py` — replace the placeholder `add_expense` route with real
  `GET`/`POST` handling: auth guard, form validation, insert, redirect
- `templates/profile.html` — add a link to the add-expense page
- `database/queries.py` — add a `create_expense` helper

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (n/a to this feature, but keep as a standing
  rule — do not touch auth code)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Foreign keys PRAGMA must be enabled on every connection (already done in
  `get_db()`)
- Currency must always display as ₹ — never £ or $
- `category` must be validated server-side against `CATEGORIES` in
  `database/db.py` — never trust the submitted value blindly, even though the
  form renders a `<select>`
- `amount` must be validated server-side as a positive number (reject zero,
  negative, and non-numeric input)
- `date` must be validated with the same `YYYY-MM-DD` format check already
  used in `app.py` (`_valid_date`); reject invalid or missing dates
- `description` is optional — omitting it must not raise an error and should
  store `NULL`/empty, matching the existing seed data (`Other` category has a
  `None` description)
- On success, redirect to `/profile` (redirect-after-POST — do not re-render
  the form on the same POST)
- On validation failure, re-render `add_expense.html` with the entered values
  preserved and an `{{ error }}` message, matching the pattern in
  `register()`/`login()`
- `create_expense` in `database/queries.py` must call `get_db()` internally
  and close the connection before returning, matching the existing helpers in
  that file

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount,
      category (7 options), date (defaulting to today), and description
- [ ] Submitting a valid expense inserts a row and redirects to `/profile`
- [ ] The new expense appears in the profile page's transaction list,
      updates the total spent, and updates the category breakdown
- [ ] Submitting a zero or negative amount shows a validation error and
      inserts no row
- [ ] Submitting a non-numeric amount shows a validation error and inserts
      no row
- [ ] Submitting an invalid or malformed date shows a validation error and
      inserts no row
- [ ] Submitting with an empty description succeeds
- [ ] All amounts on the add-expense flow and profile page display the ₹
      symbol
- [ ] A link to `/expenses/add` is reachable from the profile page
