"""SQLite data layer for Spendly.

Exposes three functions:
  get_db()   — open a connection with dict-like rows and FK enforcement on
  init_db()  — create tables (idempotent)
  seed_db()  — insert a demo user + sample expenses once
"""

import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

# Fixed category list — keep in sync with the spec.
CATEGORIES = ["Food", "Transport", "Bills", "Health",
              "Entertainment", "Shopping", "Other"]


def get_db():
    """Return a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables if they do not exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert the demo user and 8 sample expenses — only on an empty database."""
    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        month = date.today().strftime("%Y-%m")
        expenses = [
            (user_id, 240.0, "Food", f"{month}-03", "Groceries for the week"),
            (user_id, 90.0, "Food", f"{month}-17", "Lunch with a friend"),
            (user_id, 60.0, "Transport", f"{month}-05", "Metro card top-up"),
            (user_id, 1800.0, "Bills", f"{month}-08", "Electricity bill"),
            (user_id, 450.0, "Health", f"{month}-11", "Pharmacy"),
            (user_id, 300.0, "Entertainment", f"{month}-14", "Movie tickets"),
            (user_id, 1250.0, "Shopping", f"{month}-20", "New running shoes"),
            (user_id, 150.0, "Other", f"{month}-24", None),
        ]
        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
