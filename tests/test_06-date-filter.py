"""Tests for Step 6: Date Filter (see .claude/specs/06-date-filter.md).

Scope: GET /profile's optional `start` / `end` query-string filter on the
"Recent transactions" list. Assertions are derived from the spec's "Routes",
"Rules for implementation", and "Definition of done" sections only — not from
reading app.py's / database/queries.py's actual filtering logic.

DB isolation note
------------------
`database/db.py` points at a fixed on-disk file (`expense_tracker.db`) and
`app.py` calls `init_db()` / `seed_db()` once at import time — there is no
per-test in-memory DB to swap in. To keep tests deterministic and avoid
touching (or depending on) the shared seed data — whose expense dates are
relative to "today" and could collide with other test runs or developers'
manual testing — every test registers its own uniquely-emailed user via the
real `/register` route and inserts its own expense rows directly through
`database.db.get_db()` (parameterised SQL only). Each test tears down exactly
the rows it created (expenses first, then the user, respecting the
`expenses.user_id -> users.id` foreign key) so the shared database is left as
it was found.
"""

import uuid

import pytest
from flask import url_for

from app import app as flask_app
from database.db import get_db, get_user_by_email


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def client():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app.test_client()


@pytest.fixture
def urls():
    """Route paths resolved via url_for(), never hardcoded."""
    with flask_app.test_request_context():
        return {
            "register": url_for("register"),
            "login": url_for("login"),
            "profile": url_for("profile"),
        }


def _unique_email():
    return f"dftest-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def new_user(client, urls):
    """Register a fresh, uniquely-emailed user via the real /register route.

    Yields a dict with id/email/password/name, then deletes everything this
    test wrote (its expenses, then the user row) so the shared
    expense_tracker.db is left untouched for other tests / developers.
    """
    email = _unique_email()
    password = "testpass123"
    name = "Date Filter Test User"

    resp = client.post(
        urls["register"],
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 302, "Successful registration should redirect to /login"

    user_row = get_user_by_email(email)
    assert user_row is not None, "Registered user should be findable via get_user_by_email"

    yield {"id": user_row["id"], "email": email, "password": password, "name": name}

    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_row["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (user_row["id"],))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def auth_client(client, urls, new_user):
    """A test client logged in as `new_user`."""
    resp = client.post(
        urls["login"],
        data={"email": new_user["email"], "password": new_user["password"]},
        follow_redirects=False,
    )
    assert resp.status_code == 302, "Successful login should redirect"
    return client


def _add_expense(user_id, amount, category, txn_date, description=None):
    """Insert one expense row directly (no /expenses/add route exists yet —
    it's still a Step-7 placeholder per app.py), using parameterised SQL that
    matches the `expenses` schema in database/db.py.
    """
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, txn_date, description),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def user_with_expenses(new_user):
    """`new_user` with three expenses spread across a known date range.

    Cleaned up by new_user's own teardown (DELETE FROM expenses WHERE
    user_id = ?), so no separate teardown is needed here.
    """
    _add_expense(new_user["id"], 100.50, "Food", "2026-01-05", "Groceries A")
    _add_expense(new_user["id"], 200.25, "Bills", "2026-01-15", "Rent B")
    _add_expense(new_user["id"], 300.00, "Entertainment", "2026-01-25", "Movie C")
    return new_user


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestProfileAuthGuard:
    def test_signed_out_profile_redirects_to_login(self, client, urls):
        resp = client.get(urls["profile"])
        assert resp.status_code == 302, "Signed-out /profile should redirect, not render"
        assert urls["login"] in resp.headers["Location"], "Should redirect to /login"

    def test_signed_out_profile_with_filter_params_still_redirects_to_login(self, client, urls):
        """Filter query params must not bypass the existing session check."""
        resp = client.get(f"{urls['profile']}?start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 302, "Filter params must not let a signed-out request through"
        assert urls["login"] in resp.headers["Location"], "Should still redirect to /login"


# ------------------------------------------------------------------ #
# Empty states                                                        #
# ------------------------------------------------------------------ #

class TestEmptyStates:
    def test_brand_new_user_unfiltered_sees_no_transactions_yet(self, auth_client, new_user, urls):
        resp = auth_client.get(urls["profile"])
        assert resp.status_code == 200
        assert b"No transactions yet." in resp.data, (
            "A user with zero expenses and no filter should see the "
            "'no transactions yet' empty state, not a broken/empty table"
        )
        assert b"<table" not in resp.data, "Empty state should not render an empty table"

    def test_brand_new_user_with_filter_params_sees_no_transactions_in_range(
        self, auth_client, new_user, urls
    ):
        """Same user, but with a filter active — wording should reflect the
        active filter rather than the generic 'no transactions yet' message.
        """
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-01&end=2026-01-31")
        assert resp.status_code == 200
        assert b"No transactions in this range." in resp.data

    def test_inverted_range_shows_empty_state_not_error(
        self, auth_client, user_with_expenses, urls
    ):
        """start after end must return no rows (not swap the bounds, not 500)."""
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-25&end=2026-01-05")
        assert resp.status_code == 200, "Inverted range must not raise a 500"
        assert b"No transactions in this range." in resp.data
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description not in resp.data, (
                "Inverted range must match nothing, not silently swap start/end"
            )


# ------------------------------------------------------------------ #
# Unfiltered list                                                     #
# ------------------------------------------------------------------ #

class TestUnfilteredTransactionList:
    def test_unfiltered_profile_shows_all_transactions(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(urls["profile"])
        assert resp.status_code == 200
        assert b"Recent transactions" in resp.data
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description in resp.data, f"{description!r} should appear when unfiltered"

    def test_unfiltered_profile_has_no_clear_filter_link(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(urls["profile"])
        assert b"Clear filter" not in resp.data, (
            "Clear filter link must only appear when a filter is active"
        )


# ------------------------------------------------------------------ #
# Date-range filtering                                                #
# ------------------------------------------------------------------ #

class TestDateRangeFiltering:
    def test_filter_range_returns_only_matching_transactions(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-10&end=2026-01-20")
        assert resp.status_code == 200
        assert b"Rent B" in resp.data, "Expense dated within the range should be shown"
        assert b"Groceries A" not in resp.data, "Expense before the range should be excluded"
        assert b"Movie C" not in resp.data, "Expense after the range should be excluded"

    def test_range_boundaries_are_inclusive(self, auth_client, user_with_expenses, urls):
        """start/end exactly matching an expense's date should include it."""
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-05&end=2026-01-05")
        assert resp.status_code == 200
        assert b"Groceries A" in resp.data, "start == end == an expense's date should include it"
        assert b"Rent B" not in resp.data
        assert b"Movie C" not in resp.data

    def test_visiting_filtered_url_directly_shows_same_filtered_result(
        self, auth_client, user_with_expenses, urls
    ):
        """DoD: visiting /profile?start=...&end=... directly (a plain query
        string, not a form POST) must show the same filtered result as
        submitting the GET form — there is no server-side difference between
        the two since both arrive as a GET with query params.
        """
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-01&end=2026-01-20")
        assert resp.status_code == 200
        assert b"Groceries A" in resp.data
        assert b"Rent B" in resp.data
        assert b"Movie C" not in resp.data

    def test_start_only_filter_includes_everything_from_start_onward(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-15")
        assert resp.status_code == 200
        assert b"Rent B" in resp.data
        assert b"Movie C" in resp.data
        assert b"Groceries A" not in resp.data

    def test_end_only_filter_includes_everything_up_to_end(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?end=2026-01-15")
        assert resp.status_code == 200
        assert b"Groceries A" in resp.data
        assert b"Rent B" in resp.data
        assert b"Movie C" not in resp.data


# ------------------------------------------------------------------ #
# Validation / malformed input edge cases                             #
# ------------------------------------------------------------------ #

class TestMalformedDateHandling:
    def test_malformed_start_does_not_500_and_behaves_as_unfiltered(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=not-a-date")
        assert resp.status_code == 200, "A malformed start must not raise a 500"
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description in resp.data, "Malformed start should be treated as unset"

    def test_malformed_end_does_not_500_and_behaves_as_unfiltered(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?end=banana")
        assert resp.status_code == 200, "A malformed end must not raise a 500"
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description in resp.data, "Malformed end should be treated as unset"

    def test_malformed_start_with_valid_end_only_applies_the_valid_bound(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=99-99-9999&end=2026-01-15")
        assert resp.status_code == 200
        assert b"Groceries A" in resp.data
        assert b"Rent B" in resp.data
        assert b"Movie C" not in resp.data, "Valid end bound should still be applied"

    def test_empty_string_params_treated_as_unset(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=&end=")
        assert resp.status_code == 200
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description in resp.data


# ------------------------------------------------------------------ #
# Filter form / Clear filter link                                     #
# ------------------------------------------------------------------ #

class TestFilterForm:
    def test_filter_form_present_with_expected_fields(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(urls["profile"])
        assert b'name="start"' in resp.data
        assert b'name="end"' in resp.data
        assert b"Filter" in resp.data

    def test_clear_filter_link_appears_when_filter_active(
        self, auth_client, user_with_expenses, urls
    ):
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-10")
        assert b"Clear filter" in resp.data, "Clear filter link should show once a filter is set"

    def test_clear_filter_link_returns_to_unfiltered_list(
        self, auth_client, user_with_expenses, urls
    ):
        # Follow the same path a user clicking "Clear filter" would take:
        # a plain GET to /profile with no query params.
        resp = auth_client.get(urls["profile"])
        assert resp.status_code == 200
        for description in (b"Groceries A", b"Rent B", b"Movie C"):
            assert description in resp.data, "Clearing the filter should restore the full list"
        assert b"Clear filter" not in resp.data


# ------------------------------------------------------------------ #
# Currency formatting                                                 #
# ------------------------------------------------------------------ #

class TestCurrencyFormatting:
    def test_amounts_display_rupee_symbol(self, auth_client, user_with_expenses, urls):
        resp = auth_client.get(urls["profile"])
        assert resp.status_code == 200
        # The rupee sign is emitted as the literal HTML entity `&#8377;` in
        # profile.html; it must appear once per shown transaction row.
        assert resp.data.count(b"&#8377;") == 3, "Every displayed amount should show the rupee sign"
        assert b"$" not in resp.data, "Currency must never render as dollars"
        assert b"\xc2\xa3" not in resp.data, "Currency must never render as pound sterling"

    def test_filtered_amounts_display_rupee_symbol(self, auth_client, user_with_expenses, urls):
        resp = auth_client.get(f"{urls['profile']}?start=2026-01-10&end=2026-01-20")
        assert resp.status_code == 200
        assert resp.data.count(b"&#8377;") == 1, "Only the single matching row's amount is shown"
