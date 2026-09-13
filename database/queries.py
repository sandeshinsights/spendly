"""Pure query helpers for the profile page. No Flask imports.

Each function opens its own connection via get_db() and closes it before
returning, matching the pattern in database/db.py.
"""

from datetime import datetime

from database.db import get_db


def _format_month_year(raw):
    """Render a stored 'YYYY-MM-DD HH:MM:SS' timestamp as e.g. 'January 2026'."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
        except (TypeError, ValueError):
            continue
        return parsed.strftime("%B %Y")
    return raw or "—"


def get_user_by_id(user_id):
    """Return {'name', 'email', 'member_since'} for a user, or None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": _format_month_year(row["created_at"]),
    }


def get_summary_stats(user_id):
    """Return {'total_spent', 'transaction_count', 'top_category'} for a user."""
    conn = get_db()
    try:
        totals_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_spent,
                   COUNT(*) AS transaction_count
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        top_row = conn.execute(
            """
            SELECT category
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY SUM(amount) DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": totals_row["total_spent"],
        "transaction_count": totals_row["transaction_count"],
        "top_category": top_row["category"] if top_row is not None else "—",
    }


def get_recent_transactions(user_id, start=None, end=None, limit=10):
    """Return the user's most recent expenses, newest-first, as a list of dicts.

    start/end are optional 'YYYY-MM-DD' strings that narrow the result to
    expenses with date >= start and/or date <= end (inclusive). An inverted
    range (start after end) simply matches no rows, since both bounds are
    ANDed together.
    """
    conn = get_db()
    try:
        clauses = ["user_id = ?"]
        params = [user_id]

        if start:
            clauses.append("date >= ?")
            params.append(start)
        if end:
            clauses.append("date <= ?")
            params.append(end)

        params.append(limit)

        # clauses only ever contains fixed strings from this function — never
        # user-supplied text — so f-string-joining them here is safe. Values
        # still flow through parameterised `?` placeholders below.
        rows = conn.execute(
            f"""
            SELECT date, description, category, amount
            FROM expenses
            WHERE {' AND '.join(clauses)}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def create_expense(user_id, amount, category, date, description):
    """Insert a new expense row, return its id."""
    conn = get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_category_breakdown(user_id):
    """Return per-category totals and percentages (summing to 100) for a user."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY SUM(amount) DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    if grand_total == 0:
        return []

    result = [
        {
            "name": row["category"],
            "amount": row["total"],
            "pct": round(row["total"] / grand_total * 100),
        }
        for row in rows
    ]

    remainder = 100 - sum(item["pct"] for item in result)
    result[0]["pct"] += remainder

    return result
