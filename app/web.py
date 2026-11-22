"""Server-rendered UI blueprint — the browser-facing replacement for the
original Tkinter window.
"""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from . import core, db

bp = Blueprint("web", __name__)


@bp.get("/")
def dashboard():
    """Gym dashboard: client roster and headline numbers."""
    clients = db.query("SELECT * FROM clients ORDER BY name")
    totals = db.query(
        "SELECT COUNT(*) AS clients, COALESCE(AVG(calories), 0) AS avg_calories FROM clients",
        one=True,
    )
    adherence = db.query("SELECT COALESCE(AVG(adherence), 0) AS avg FROM progress", one=True)
    return render_template(
        "dashboard.html",
        clients=clients,
        totals=totals,
        avg_adherence=round(adherence["avg"], 1),
        programs=core.PROGRAMS,
        version=current_app.config["APP_VERSION"],
        track=current_app.config["APP_TRACK"],
    )


@bp.get("/clients/new")
def new_client_form():
    """Render the client intake form."""
    return render_template("client_form.html", programs=core.program_names(), client=None)


@bp.post("/clients")
def create_client():
    """Handle the client intake form submission."""
    try:
        data = core.validate_client(request.form.to_dict())
    except core.ValidationError as exc:
        for message in exc.errors:
            flash(message, "error")
        return (
            render_template(
                "client_form.html",
                programs=core.program_names(),
                client=request.form.to_dict(),
            ),
            400,
        )

    db.execute(
        """
        INSERT INTO clients
            (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (:name, :age, :height, :weight, :program, :calories, :target_weight,
                :target_adherence)
        ON CONFLICT(name) DO UPDATE SET
            age = excluded.age, height = excluded.height, weight = excluded.weight,
            program = excluded.program, calories = excluded.calories,
            target_weight = excluded.target_weight,
            target_adherence = excluded.target_adherence
        """,
        data,
    )
    flash(f"Client {data['name']} saved", "success")
    return redirect(url_for("web.client_detail", name=data["name"]))


@bp.get("/clients/<name>")
def client_detail(name: str):
    """Show a single client's profile, plan and progress."""
    client = db.query("SELECT * FROM clients WHERE name = ?", (name,), one=True)
    if not client:
        return render_template("not_found.html", name=name), 404

    progress = db.query(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id", (name,)
    )
    workouts = db.query(
        "SELECT * FROM workouts WHERE client_name = ? ORDER BY date DESC LIMIT 10", (name,)
    )
    bmi = None
    if client.get("height") and client.get("weight"):
        bmi = core.calculate_bmi(client["height"], client["weight"])

    return render_template(
        "client_detail.html",
        client=client,
        program=core.PROGRAMS.get(client["program"], {}),
        progress=progress,
        summary=core.summarise_progress(progress),
        workouts=workouts,
        bmi=bmi,
        bmi_category=core.bmi_category(bmi) if bmi else None,
        bmi_note=core.bmi_risk_note(bmi) if bmi else None,
    )


@bp.post("/clients/<name>/progress")
def log_progress(name: str):
    """Log weekly adherence from the client detail page."""
    try:
        adherence = core.validate_adherence(request.form.get("adherence"))
    except core.ValidationError as exc:
        for message in exc.errors:
            flash(message, "error")
        return redirect(url_for("web.client_detail", name=name))

    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (name, request.form.get("week") or core.week_label(), adherence),
    )
    flash("Weekly progress logged", "success")
    return redirect(url_for("web.client_detail", name=name))


@bp.get("/programs")
def programs():
    """Public program catalogue with workout and nutrition guidance."""
    return render_template("programs.html", programs=core.PROGRAMS)
