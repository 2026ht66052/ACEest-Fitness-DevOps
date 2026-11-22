"""API-level tests driving the Flask application through its HTTP interface."""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# Operational endpoints
# --------------------------------------------------------------------------- #
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ready"


def test_version_endpoint_exposes_version_and_track(client):
    body = client.get("/version").get_json()
    assert body["app"] == "aceest-fitness"
    assert "version" in body and "track" in body


def test_version_headers_added_to_every_response(client):
    response = client.get("/health")
    assert response.headers["X-App-Version"]
    assert response.headers["X-App-Track"]


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "not found"


# --------------------------------------------------------------------------- #
# Programs
# --------------------------------------------------------------------------- #
def test_list_programs(client):
    body = client.get("/api/v1/programs").get_json()
    assert body["count"] == 4
    assert {p["name"] for p in body["programs"]}


def test_generate_program_endpoint(client):
    response = client.post(
        "/api/v1/programs/generate",
        json={"program": "Beginner (BG)", "experience": "beginner", "seed": 5},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 9
    assert body["plan"][0]["day"] == "Monday"


def test_generate_program_endpoint_validates_input(client):
    response = client.post(
        "/api/v1/programs/generate", json={"program": "Beginner (BG)", "experience": "pro"}
    )
    assert response.status_code == 400
    assert "details" in response.get_json()


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
def test_create_client(client):
    response = client.post(
        "/api/v1/clients",
        json={"name": "Meera", "weight": 58, "height": 160, "program": "Beginner (BG)"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Meera"
    assert body["calories"] == 1508


def test_create_client_rejects_missing_fields(client):
    response = client.post("/api/v1/clients", json={"name": "NoProgram"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation failed"


def test_create_client_is_idempotent_on_name(client, sample_client):
    response = client.post(
        "/api/v1/clients",
        json={"name": "Arun", "weight": 82, "height": 175, "program": "Beginner (BG)"},
    )
    assert response.status_code == 201
    listing = client.get("/api/v1/clients").get_json()
    assert listing["count"] == 1
    assert listing["clients"][0]["program"] == "Beginner (BG)"


def test_list_clients_empty(client):
    body = client.get("/api/v1/clients").get_json()
    assert body == {"count": 0, "clients": []}


def test_get_client_includes_derived_fields(client, sample_client):
    body = client.get("/api/v1/clients/Arun").get_json()
    assert body["bmi"] == 26.1
    assert body["bmi_category"] == "Overweight"
    assert body["progress_summary"]["weeks_logged"] == 0


def test_get_unknown_client_returns_404(client):
    assert client.get("/api/v1/clients/Nobody").status_code == 404


def test_delete_client_removes_record(client, sample_client):
    assert client.delete("/api/v1/clients/Arun").status_code == 204
    assert client.get("/api/v1/clients/Arun").status_code == 404


def test_delete_unknown_client_returns_404(client):
    assert client.delete("/api/v1/clients/Ghost").status_code == 404


# --------------------------------------------------------------------------- #
# Progress
# --------------------------------------------------------------------------- #
def test_log_and_read_progress(client, sample_client):
    for week, value in (("Week 01 - 2026", 60), ("Week 02 - 2026", 85)):
        response = client.post(
            "/api/v1/clients/Arun/progress", json={"week": week, "adherence": value}
        )
        assert response.status_code == 201

    body = client.get("/api/v1/clients/Arun/progress").get_json()
    assert len(body["entries"]) == 2
    assert body["summary"]["average_adherence"] == 72.5
    assert body["summary"]["trend"] == "improving"


def test_log_progress_defaults_week_label(client, sample_client):
    body = client.post("/api/v1/clients/Arun/progress", json={"adherence": 70}).get_json()
    assert body["week"].startswith("Week ")


def test_log_progress_rejects_out_of_range(client, sample_client):
    response = client.post("/api/v1/clients/Arun/progress", json={"adherence": 140})
    assert response.status_code == 400


def test_log_progress_for_unknown_client(client):
    assert client.post("/api/v1/clients/Ghost/progress", json={"adherence": 50}).status_code == 404


# --------------------------------------------------------------------------- #
# Workouts
# --------------------------------------------------------------------------- #
def test_log_workout_with_exercises(client, sample_client):
    response = client.post(
        "/api/v1/clients/Arun/workouts",
        json={
            "date": "2026-02-01",
            "workout_type": "Strength",
            "duration_min": 75,
            "notes": "Heavy squats",
            "exercises": [{"name": "Back Squat", "sets": 5, "reps": 5, "weight": 120}],
        },
    )
    assert response.status_code == 201

    body = client.get("/api/v1/clients/Arun/workouts").get_json()
    assert body["count"] == 1
    assert body["workouts"][0]["exercises"][0]["name"] == "Back Squat"


def test_log_workout_rejects_unknown_type(client, sample_client):
    response = client.post(
        "/api/v1/clients/Arun/workouts", json={"workout_type": "Yoga Flow"}
    )
    assert response.status_code == 400


def test_log_workout_rejects_bad_duration(client, sample_client):
    response = client.post(
        "/api/v1/clients/Arun/workouts",
        json={"workout_type": "Mobility", "duration_min": -5},
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def test_log_metrics_updates_client_weight(client, sample_client):
    response = client.post(
        "/api/v1/clients/Arun/metrics",
        json={"date": "2026-03-01", "weight": 78.4, "waist": 84, "bodyfat": 17.5},
    )
    assert response.status_code == 201
    client_body = client.get("/api/v1/clients/Arun").get_json()
    assert client_body["weight"] == 78.4
    assert client_body["last_metrics"]["waist"] == 84


def test_log_metrics_rejects_zero_weight(client, sample_client):
    assert (
        client.post("/api/v1/clients/Arun/metrics", json={"weight": 0}).status_code == 400
    )


def test_list_metrics(client, sample_client):
    client.post("/api/v1/clients/Arun/metrics", json={"weight": 80, "date": "2026-01-01"})
    body = client.get("/api/v1/clients/Arun/metrics").get_json()
    assert body["count"] == 1


# --------------------------------------------------------------------------- #
# Calculators
# --------------------------------------------------------------------------- #
def test_bmi_endpoint(client):
    body = client.post("/api/v1/bmi", json={"height": 175, "weight": 80}).get_json()
    assert body["bmi"] == 26.1
    assert body["category"] == "Overweight"


def test_bmi_endpoint_validates(client):
    assert client.post("/api/v1/bmi", json={"height": 0, "weight": 80}).status_code == 400


def test_calories_endpoint(client):
    body = client.post(
        "/api/v1/calories", json={"weight": 70, "program": "Fat Loss (FL) - 3 day"}
    ).get_json()
    assert body["calories"] == 1540


def test_calories_endpoint_validates_program(client):
    assert (
        client.post("/api/v1/calories", json={"weight": 70, "program": "Nope"}).status_code
        == 400
    )


def test_api_version_endpoint(client):
    assert client.get("/api/v1/version").get_json()["app"] == "aceest-fitness"
