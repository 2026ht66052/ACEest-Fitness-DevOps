"""Tests for the persistence layer."""

from __future__ import annotations

from app import db


def test_schema_contains_every_table(app):
    with app.app_context():
        rows = db.query("SELECT name FROM sqlite_master WHERE type = 'table'")
        names = {row["name"] for row in rows}
    assert {"clients", "progress", "workouts", "exercises", "metrics"} <= names


def test_init_db_is_idempotent(app):
    with app.app_context():
        db.init_db()
        db.init_db()
        assert db.query("SELECT COUNT(*) AS n FROM clients", one=True)["n"] == 0


def test_execute_returns_lastrowid_and_query_one(app):
    with app.app_context():
        row_id = db.execute(
            "INSERT INTO clients (name, program, weight) VALUES (?, ?, ?)",
            ("Nisha", "Beginner (BG)", 55.0),
        )
        assert row_id == 1
        row = db.query("SELECT * FROM clients WHERE id = ?", (row_id,), one=True)
        assert row["name"] == "Nisha"


def test_query_one_returns_none_when_empty(app):
    with app.app_context():
        assert db.query("SELECT * FROM clients WHERE name = ?", ("Nope",), one=True) is None


def test_unique_client_name_constraint(app):
    with app.app_context():
        db.execute(
            "INSERT INTO clients (name, program, weight) VALUES (?, ?, ?)",
            ("Dup", "Beginner (BG)", 60.0),
        )
        try:
            db.execute(
                "INSERT INTO clients (name, program, weight) VALUES (?, ?, ?)",
                ("Dup", "Beginner (BG)", 61.0),
            )
        except Exception as exc:
            assert "UNIQUE" in str(exc).upper()
        else:  # pragma: no cover - would indicate a schema regression
            raise AssertionError("expected a UNIQUE constraint violation")


def test_exercises_cascade_with_workout(app):
    with app.app_context():
        workout_id = db.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min) "
            "VALUES (?, ?, ?, ?)",
            ("Arun", "2026-01-01", "Strength", 60),
        )
        db.execute(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
            (workout_id, "Deadlift", 3, 5, 150.0),
        )
        db.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        assert db.query("SELECT * FROM exercises WHERE workout_id = ?", (workout_id,)) == []
