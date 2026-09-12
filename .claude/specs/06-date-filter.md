# Spec: Date Filter

## Overview
Step 6 adds a date-range filter to the profile page's transaction history.
`database/queries.py` and the `/profile` route (Step 5) already compute
`recent_transactions`, `summary_stats`, and `category_breakdown` from real
expense data, but `templates/profile.html` (Step 4) only ever rendered the
account-details card — the transaction list itself has never been shown to a
user. This step renders that transaction list for the first time and lets a
signed-in user narrow it to a date range via two `GET` query parameters, so
the filter is bookmarkable and shareable. Summary stats and category
breakdown remain out of scope — this step touches only the transaction list.

## Depends on
- Step 1: Database setup (`expenses.date` stored as `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]` gates `/profile`)
- Step 4: Profile page design (`profile.html` account card, `.profile-*` CSS)
- Step 5: Backend routes for profile page (`get_recent_transactions()` and the
  `/profile` route already fetch and pass `recent_transactions`)

## Routes
- `GET /profile` — modified — logged-in only (unchanged access level).
  Accepts optional `start` and `end` query-string parameters
  (`YYYY-MM-DD`), e.g. `/profile?start=2026-09-01&end=2026-09-30`. Each is
  validated with `datetime.strptime(value, "%Y-%m-%d")`; a missing or
  unparsable value is treated as "not set" rather than raising an error. When
  neither is set, the transaction list is unfiltered (existing behaviour).

## Database changes
No database changes. `expenses.date` is already a `TEXT` column storing
`YYYY-MM-DD`, which supports lexicographic range comparison directly in SQL.

## Templates
- **Modify:** `templates/profile.html`
  - Add a "Recent transactions" section below the existing account card.
  - Add a filter form: `method="get"` `action="{{ url_for('profile') }}"`,
    two `<input type="date">` fields (`name="start"`, `name="end"`)
    pre-filled from the current `start` / `end` values, a submit button
    ("Filter"), and — only when a filter is active — a "Clear filter" link
    back to plain `{{ url_for('profile') }}`.
  - Render `recent_transactions` as a list/table of date, description,
    category, and amount (₹). When the list is empty, show a plain message
    ("No transactions in this range." / "No transactions yet.") instead of an
    empty table.
  - No `{% block scripts %}` — plain GET form submission, no JavaScript
    needed.

## Files to change
- `app.py` — in `profile()`: read `start` / `end` from `request.args`,
  validate each as `YYYY-MM-DD` (discard silently if invalid or absent), pass
  the validated values to `get_recent_transactions()`, and pass the raw
  `start` / `end` strings back to the template so the form can be pre-filled.
- `database/queries.py` — extend `get_recent_transactions(user_id, start=None, end=None, limit=10)`
  to add `AND date >= ?` / `AND date <= ?` clauses only when `start` / `end`
  are provided, still parameterised.
- `templates/profile.html` — add the filter form and the transaction list
  markup described above.
- `static/css/style.css` — add rules for the filter form and transaction list
  under a new `/* Date filter */` section (or extend the existing `/* Profile
  page */` section), reusing existing tokens and `.form-group` /
  `.btn-primary` patterns — no new hardcoded values.

## Files to create
No new files.

## New dependencies
No new dependencies. Date parsing uses the stdlib `datetime` module.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — `start` / `end` are bound as `?` params, never
  string-formatted into SQL.
- Passwords hashed with `werkzeug` (unaffected by this step).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- No inline styles; no page-scoped `<style>` block.
- Vanilla JS only, and this feature needs none — filtering happens via a
  plain `GET` form, not `fetch`/JS.
- Currency must always display as ₹ — never £ or $.
- An invalid or malformed `start`/`end` must never raise a 500 — treat it as
  unset and fall back to the unfiltered list.
- If `start` is after `end`, treat the range as empty (return no rows) rather
  than silently swapping them or erroring.
- `get_recent_transactions()` must still close its connection in a `finally`
  block, matching the existing pattern in `database/queries.py`.

## Definition of done
- [ ] Visiting `/profile` while signed out still redirects to `/login`
      (filter params do not bypass the existing session check).
- [ ] Signing in as the seed user (`demo@spendly.com` / `demo123`) and
      visiting `/profile` now shows a "Recent transactions" list with the
      8 seed expenses, alongside the existing account card.
- [ ] Submitting the filter form with a `start`/`end` range that covers only
      some seed expenses shows only the expenses whose `date` falls within
      that inclusive range.
- [ ] Visiting `/profile?start=2026-09-01&end=2026-09-30` directly (no form
      submission) shows the same filtered result — the filter is a plain
      query string.
- [ ] Setting `end` earlier than `start` shows the empty-state message, not
      an error.
- [ ] Passing a malformed date (e.g. `/profile?start=not-a-date`) does not
      throw a 500 — it behaves as if no filter were applied.
- [ ] The "Clear filter" link appears only when a filter is active and
      returns to the full, unfiltered transaction list.
- [ ] All amounts in the transaction list display the ₹ symbol.
- [ ] A brand-new user with no expenses sees the empty-state message instead
      of a broken/empty table.
- [ ] `grep -E '#[0-9a-fA-F]{3,6}'` over the new CSS rules finds nothing.
