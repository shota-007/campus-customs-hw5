"""Database access for the Campus Customs MCP server.

All tools go through this module so there is exactly one place that decides
which SQLite file is used: the working copy data/campus_customs_new.db.
The original data/campus_customs.db is never opened here.
"""

import calendar
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"
DB_PATH = (PROJECT_ROOT / os.environ.get("CAMPUS_CUSTOMS_DB", DEFAULT_DB_PATH)).resolve()

# Work tables the agents write to. They live only in the working copy and are
# created on server start, so a reset (copying the original over the working
# copy) wipes them along with every payment and stock change.
WORK_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('invoice', 'rent', 'purchase_order')),
    ref_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payee TEXT NOT NULL,
    account TEXT NOT NULL,
    ticket_id INTEGER,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'rejected', 'refused')),
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER REFERENCES payments(id)
);
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    sku TEXT NOT NULL,
    size TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_cost REAL NOT NULL,
    total REAL NOT NULL,
    ticket_id INTEGER,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'ordered', 'cancelled')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expected_arrival TEXT
);
CREATE TABLE IF NOT EXISTS stock_holds (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    size TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    status TEXT NOT NULL DEFAULT 'held' CHECK (status IN ('held', 'released')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_log (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    agent TEXT NOT NULL,
    entry TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _open(mode: str) -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Working database not found at {DB_PATH}. "
            "Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect(readonly: bool = True) -> sqlite3.Connection:
    """Open the working database. Read-only by default so lookups can never write.

    A reset copies the original over the working copy, which drops the work
    tables. They are recreated here on the next connection, so a reset never
    breaks a running server.
    """
    conn = _open("ro" if readonly else "rw")
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ticket_log'").fetchone() is None:
        conn.close()
        ensure_schema()
        conn = _open("ro" if readonly else "rw")
    return conn


def ensure_schema() -> None:
    conn = _open("rw")
    try:
        conn.executescript(WORK_SCHEMA)
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def shop_today(conn: sqlite3.Connection) -> date:
    """The shop's 'today' comes from desk.date_today, never the real clock."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("desk table has no date_today row")
    return date.fromisoformat(row["date_today"])


def now_iso() -> str:
    """Wall-clock timestamp for audit columns (when an agent acted)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_one_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))
