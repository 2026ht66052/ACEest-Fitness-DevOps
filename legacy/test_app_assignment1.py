import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "test_aceest_fitness.db"
    application = create_app({
        "TESTING": True,
        "DATABASE": str(database),
    })
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["application"] == "ACEest Fitness & Gym"
    assert data["status"] == "running"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_programs(client):
    response = client.get("/programs")
    assert response.status_code == 200
    data = response.get_json()

    assert "Fat Loss" in data
    assert "Muscle Gain" in data
    assert "Beginner" in data


def test_create_client(client):
    response = client.post("/clients", json={
        "name": "Test User",
        "age": 25,
        "height": 175,
        "weight": 70,
        "program": "Beginner",
    })

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Client created successfully"
    assert data["client"]["name"] == "Test User"
    assert data["client"]["calories"] == 1820


def test_create_client_requires_name(client):
    response = client.post("/clients", json={
        "age": 25,
        "height": 175,
        "weight": 70,
        "program": "Beginner",
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Name is required"


def test_create_client_requires_valid_program(client):
    response = client.post("/clients", json={
        "name": "Test User",
        "age": 25,
        "height": 175,
        "weight": 70,
        "program": "Invalid Program",
    })

    assert response.status_code == 400
    assert "Invalid program" in response.get_json()["error"]


def test_create_client_requires_positive_weight(client):
    response = client.post("/clients", json={
        "name": "Test User",
        "age": 25,
        "height": 175,
        "weight": 0,
        "program": "Beginner",
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Weight must be greater than zero"


def test_get_client(client):
    create_response = client.post("/clients", json={
        "name": "John",
        "age": 30,
        "height": 180,
        "weight": 80,
        "program": "Muscle Gain",
    })

    client_id = create_response.get_json()["client"]["id"]

    response = client.get(f"/clients/{client_id}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["name"] == "John"
    assert data["program"] == "Muscle Gain"
    assert data["calories"] == 2800


def test_get_nonexistent_client(client):
    response = client.get("/clients/9999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Client not found"


def test_add_progress(client):
    create_response = client.post("/clients", json={
        "name": "Progress User",
        "age": 28,
        "height": 170,
        "weight": 65,
        "program": "Fat Loss",
    })

    client_id = create_response.get_json()["client"]["id"]

    response = client.post(
        f"/clients/{client_id}/progress",
        json={
            "week": "Week 1",
            "adherence": 90,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Progress saved successfully"
    assert data["progress"]["adherence"] == 90


def test_progress_must_be_between_zero_and_hundred(client):
    create_response = client.post("/clients", json={
        "name": "Progress User",
        "age": 28,
        "height": 170,
        "weight": 65,
        "program": "Fat Loss",
    })

    client_id = create_response.get_json()["client"]["id"]

    response = client.post(
        f"/clients/{client_id}/progress",
        json={
            "week": "Week 1",
            "adherence": 120,
        },
    )

    assert response.status_code == 400
    assert (
        response.get_json()["error"]
        == "Adherence must be between 0 and 100"
    )


def test_get_progress(client):
    create_response = client.post("/clients", json={
        "name": "Progress User",
        "age": 28,
        "height": 170,
        "weight": 65,
        "program": "Fat Loss",
    })

    client_id = create_response.get_json()["client"]["id"]

    client.post(
        f"/clients/{client_id}/progress",
        json={
            "week": "Week 1",
            "adherence": 90,
        },
    )

    response = client.get(f"/clients/{client_id}/progress")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["week"] == "Week 1"
    assert data[0]["adherence"] == 90


def test_add_workout(client):
    create_response = client.post("/clients", json={
        "name": "Workout User",
        "age": 32,
        "height": 178,
        "weight": 75,
        "program": "Muscle Gain",
    })

    client_id = create_response.get_json()["client"]["id"]

    response = client.post(
        f"/clients/{client_id}/workouts",
        json={
            "date": "2026-10-08",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Upper body workout",
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Workout saved successfully"
    assert data["workout"]["workout_type"] == "Strength"
    assert data["workout"]["duration_min"] == 60


def test_get_workouts(client):
    create_response = client.post("/clients", json={
        "name": "Workout User",
        "age": 32,
        "height": 178,
        "weight": 75,
        "program": "Muscle Gain",
    })

    client_id = create_response.get_json()["client"]["id"]

    client.post(
        f"/clients/{client_id}/workouts",
        json={
            "date": "2026-10-08",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Upper body workout",
        },
    )

    response = client.get(f"/clients/{client_id}/workouts")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["workout_type"] == "Strength"
