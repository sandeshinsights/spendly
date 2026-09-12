import os
import re
import sqlite3
from datetime import datetime

from flask import (Flask, redirect, render_template, request, session,
                   url_for)

from database.db import (create_user, get_db, get_user_by_email,
                         init_db, seed_db, verify_credentials)
from database.queries import (get_category_breakdown, get_recent_transactions,
                              get_summary_stats, get_user_by_id)

app = Flask(__name__)

# Dev-only fallback; set SECRET_KEY in the environment for anything real.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Deliberately permissive — catches obvious typos, not every RFC 5322 edge case.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_date(value):
    """Return value if it's a 'YYYY-MM-DD' string, else None."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")   # never stripped

    error = None
    if not name or not email or not password:
        error = "Please fill in every field."
    elif len(name) < 2:
        error = "Please enter your full name."
    elif not EMAIL_RE.match(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif get_user_by_email(email):
        error = "An account with that email already exists."

    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "An account with that email already exists."
        else:
            return redirect(url_for("login", registered=1))

    return render_template("register.html", error=error, name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        success = None
        if request.args.get("registered"):
            success = "Account created — please sign in."
        return render_template("login.html", success=success)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    user = None
    if not email or not password:
        error = "Please enter your email and password."
    else:
        user = verify_credentials(email, password)
        if user is None:
            error = "Incorrect email or password."

    if error:
        return render_template("login.html", error=error, email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        # Stale cookie — the referenced user no longer exists.
        session.clear()
        return redirect(url_for("login"))

    start = _valid_date(request.args.get("start"))
    end = _valid_date(request.args.get("end"))

    # --- Transaction history (Subagent 1) ---
    recent_transactions = get_recent_transactions(session["user_id"], start=start, end=end)

    # --- Summary stats (Subagent 2) ---
    summary_stats = get_summary_stats(session["user_id"])

    # --- Category breakdown (Subagent 3) ---
    category_breakdown = get_category_breakdown(session["user_id"])

    return render_template(
        "profile.html",
        user=user,
        member_since=user["member_since"],
        recent_transactions=recent_transactions,
        summary_stats=summary_stats,
        category_breakdown=category_breakdown,
        start=start,
        end=end,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
