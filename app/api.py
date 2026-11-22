"""JSON API blueprint.

Every route returns JSON so that the CI pipeline can run contract/smoke tests
against a running container without needing a browser.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from . import core, db

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _error(message, status: int = 400, errors=None):
    payload = {"error": message}
    if errors:
        payload["details"] = errors
    return jsonify(payload), status


@bp.errorhandler(core.ValidationError)
def _handle_validation(exc: core.ValidationError):  # pragma: no cover - wired below
    return _error("validation failed", 400, exc.errors)


# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
@bp.get("/programs")
def list_programs():
    """Return the catalogue of training programs."""
    return jsonify(
        {
            "count": len(core.PROGRAMS),
            "programs": [
                {
                    "name": name,
                    "calorie_factor": meta["factor"],
                    "focus": meta["focus"],
                    "description": meta["desc"],
                    "diet": meta["diet"],
                }
                for name, meta in core.PROGRAMS.items()
            ],
        }
    )


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
@bp.get("/clients")
def list_clients():
    """List every client, newest first."""
    rows = db.query("SELECT * FROM clients ORDER BY name")
    return jsonify({"count": len(rows), "clients": rows})


@bp.post("/clients")
def create_client():
    """Create or replace a client record."""
    payload = request.get_json(silent=True) or {}
    try:
        data = core.validate_client(payload)
    except core.ValidationError as exc:
        return _error("validation failed", 400, exc.errors)

    db.execute(
        """
        INSERT INTO clients
            (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (:name, :age, :height, :weight, :program, :calories, :target_weight,
                :target_adherence)
        ON CONFLICT(name) DO UPDATE SET
            age = excluded.age,
            height = excluded.height,
            weight = excluded.weight,
            program = excluded.program,
            calories = excluded.calories,
            target_weight = excluded.target_weight,
            target_adherence = excluded.target_adherence
        """,
        data,
    )
    row = db.query("SELECT * FROM clients WHERE name = ?", (data["name"],), one=True)
    return jsonify(row), 201


@bp.get("/clients/<name>")
def get_client(name: str):
    """Return a single client with derived metrics and progress summary."""
    row = db.query("SELECT * FROM clients WHERE name = ?", (name,), one=True)
    if not row:
        return _error("client not found", 404)

    progress = db.query(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id", (name,)
    )
    row["progress_summary"] = core.summarise_progress(progress)

    if row.get("height") and row.get("weight"):
        bmi = core.calculate_bmi(row["height"], row["weight"])
        row["bmi"] = bmi
        row["bmi_category"] = core.bmi_category(bmi)
        row["bmi_risk_note"] = core.bmi_risk_note(bmi)

    row["last_metrics"] = db.query(
        "SELECT date, weight, waist, bodyfat FROM metrics "
        "WHERE client_name = ? ORDER BY date DESC LIMIT 1",
        (name,),
        one=True,
    )
    return jsonify(row)


@bp.delete("/clients/<name>")
def delete_client(name: str):
    """Delete a client and everything belonging to them."""
    row = db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True)
    if not row:
        return _error("client not found", 404)
    for table in ("progress", "workouts", "metrics"):
        db.execute(f"DELETE FROM {table} WHERE client_name = ?", (name,))
    db.execute("DELETE FROM clients WHERE name = ?", (name,))
    return "", 204


# --------------------------------------------------------------------------- #
# Weekly adherence / progress
# --------------------------------------------------------------------------- #
@bp.post("/clients/<name>/progress")
def log_progress(name: str):
    """Log a weekly adherence percentage for a client."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)

    payload = request.get_json(silent=True) or {}
    try:
        adherence = core.validate_adherence(payload.get("adherence"))
    except core.ValidationError as exc:
        return _error("validation failed", 400, exc.errors)

    week = payload.get("week") or core.week_label()
    row_id = db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (name, week, adherence),
    )
    return jsonify({"id": row_id, "client_name": name, "week": week, "adherence": adherence}), 201


@bp.get("/clients/<name>/progress")
def get_progress(name: str):
    """Return every logged week plus aggregate statistics."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)
    rows = db.query(
        "SELECT id, week, adherence, logged_at FROM progress "
        "WHERE client_name = ? ORDER BY id",
        (name,),
    )
    return jsonify({"client_name": name, "entries": rows, "summary": core.summarise_progress(rows)})


# --------------------------------------------------------------------------- #
# Workouts and exercises
# --------------------------------------------------------------------------- #
@bp.post("/clients/<name>/workouts")
def log_workout(name: str):
    """Log a training session and, optionally, its exercises."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)

    payload = request.get_json(silent=True) or {}
    workout_type = str(payload.get("workout_type") or "").strip()
    if workout_type not in core.WORKOUT_TYPES:
        return _error(
            "validation failed",
            400,
            ["workout_type must be one of: " + ", ".join(core.WORKOUT_TYPES)],
        )

    workout_date = str(payload.get("date") or date.today().isoformat())
    try:
        duration = int(payload.get("duration_min") or 60)
    except (TypeError, ValueError):
        return _error("validation failed", 400, ["duration_min must be an integer"])
    if duration <= 0:
        return _error("validation failed", 400, ["duration_min must be greater than zero"])

    workout_id = db.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, workout_date, workout_type, duration, payload.get("notes") or ""),
    )

    for exercise in payload.get("exercises") or []:
        if not exercise.get("name"):
            continue
        db.execute(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
            (
                workout_id,
                exercise["name"],
                exercise.get("sets"),
                exercise.get("reps"),
                exercise.get("weight"),
            ),
        )

    return jsonify({"id": workout_id, "client_name": name, "date": workout_date}), 201


@bp.get("/clients/<name>/workouts")
def list_workouts(name: str):
    """Return workout history with nested exercises."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)
    workouts = db.query(
        "SELECT * FROM workouts WHERE client_name = ? ORDER BY date DESC, id DESC", (name,)
    )
    for workout in workouts:
        workout["exercises"] = db.query(
            "SELECT name, sets, reps, weight FROM exercises WHERE workout_id = ?",
            (workout["id"],),
        )
    return jsonify({"client_name": name, "count": len(workouts), "workouts": workouts})


# --------------------------------------------------------------------------- #
# Body metrics
# --------------------------------------------------------------------------- #
@bp.post("/clients/<name>/metrics")
def log_metrics(name: str):
    """Log body metrics (weight / waist / bodyfat)."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)

    payload = request.get_json(silent=True) or {}
    try:
        weight = float(payload.get("weight") or 0)
    except (TypeError, ValueError):
        return _error("validation failed", 400, ["weight must be a number"])
    if weight <= 0:
        return _error("validation failed", 400, ["weight must be greater than zero"])

    metric_date = str(payload.get("date") or date.today().isoformat())
    row_id = db.execute(
        "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)",
        (name, metric_date, weight, payload.get("waist"), payload.get("bodyfat")),
    )
    db.execute("UPDATE clients SET weight = ? WHERE name = ?", (weight, name))
    return jsonify({"id": row_id, "client_name": name, "date": metric_date, "weight": weight}), 201


@bp.get("/clients/<name>/metrics")
def list_metrics(name: str):
    """Return the body-metric history for a client."""
    if not db.query("SELECT id FROM clients WHERE name = ?", (name,), one=True):
        return _error("client not found", 404)
    rows = db.query(
        "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name = ? ORDER BY date",
        (name,),
    )
    return jsonify({"client_name": name, "count": len(rows), "metrics": rows})


# --------------------------------------------------------------------------- #
# Derived calculators
# --------------------------------------------------------------------------- #
@bp.post("/bmi")
def bmi():
    """Calculate BMI for an arbitrary height/weight pair."""
    payload = request.get_json(silent=True) or {}
    try:
        value = core.calculate_bmi(payload.get("height"), payload.get("weight"))
    except (core.ValidationError, TypeError, ValueError) as exc:
        errors = getattr(exc, "errors", ["height and weight must be numbers"])
        return _error("validation failed", 400, errors)
    return jsonify(
        {"bmi": value, "category": core.bmi_category(value), "note": core.bmi_risk_note(value)}
    )


@bp.post("/calories")
def calories():
    """Estimate a daily calorie target."""
    payload = request.get_json(silent=True) or {}
    try:
        value = core.calculate_calories(payload.get("weight"), payload.get("program", ""))
    except (core.ValidationError, TypeError, ValueError) as exc:
        errors = getattr(exc, "errors", ["weight and program are required"])
        return _error("validation failed", 400, errors)
    return jsonify({"calories": value, "program": payload.get("program")})


@bp.post("/programs/generate")
def generate():
    """Generate a weekly training plan for a program and experience level."""
    payload = request.get_json(silent=True) or {}
    try:
        plan = core.generate_program(
            payload.get("program", ""),
            payload.get("experience", ""),
            seed=payload.get("seed"),
        )
    except core.ValidationError as exc:
        return _error("validation failed", 400, exc.errors)
    return jsonify({"count": len(plan), "plan": plan})


# --------------------------------------------------------------------------- #
# Operational endpoints (used by Kubernetes probes and the CI smoke tests)
# --------------------------------------------------------------------------- #
@bp.get("/version")
def version():
    """Return the running version and deployment track."""
    return jsonify(
        {
            "app": "aceest-fitness",
            "version": current_app.config["APP_VERSION"],
            "track": current_app.config["APP_TRACK"],
            "instance": current_app.config["INSTANCE"],
        }
    )
