"""SQLite persistence layer.

The schema mirrors the tables that were created inline by the Tkinter versions
(``clients``, ``progress``, ``workouts``, ``exercises``, ``metrics``) so that an
existing ``aceest_fitness.db`` file remains usable.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT UNIQUE NOT NULL,
    age              INTEGER,
    height           REAL,
    weight           REAL,
    program          TEXT NOT NULL,
    calories         INTEGER,
    target_weight    REAL,
    target_adherence INTEGER,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week        TEXT NOT NULL,
    adherence   INTEGER NOT NULL,
    logged_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name  TEXT NOT NULL,
    date         TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    name       TEXT NOT NULL,
    sets       INTEGER,
    reps       INTEGER,
    weight     REAL,
    FOREIGN KEY (workout_id) REFERENCES workouts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date        TEXT NOT NULL,
    weight      REAL,
    waist       REAL,
    bodyfat     REAL
);

CREATE INDEX IF NOT EXISTS idx_progress_client ON progress (client_name);
CREATE INDEX IF NOT EXISTS idx_workouts_client ON workouts (client_name);
CREATE INDEX IF NOT EXISTS idx_metrics_client  ON metrics (client_name);
"""


def get_db() -> sqlite3.Connection:
    """Return the request-scoped SQLite connection, opening it if needed."""
    if "db" not in g:
        path = current_app.config["DATABASE"]
        if path != ":memory:":
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    """Close the connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create the schema if it does not already exist."""
    get_db().executescript(SCHEMA)
    get_db().commit()


def query(sql: str, args: tuple = (), one: bool = False) -> Any:
    """Run a SELECT and return ``dict`` rows (or a single row with ``one``)."""
    cursor = get_db().execute(sql, args)
    rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql: str, args: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return ``lastrowid``."""
    db = get_db()
    cursor = db.execute(sql, args)
    db.commit()
    row_id = cursor.lastrowid
    cursor.close()
    return row_id


def init_app(app) -> None:
    """Register database lifecycle hooks and the ``init-db`` CLI command."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:  # pragma: no cover - CLI glue
        init_db()
        print(f"Initialised database at {app.config['DATABASE']}")
