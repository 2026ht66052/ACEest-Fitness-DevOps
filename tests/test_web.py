"""Tests for the server-rendered UI."""

from __future__ import annotations


def test_dashboard_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Gym dashboard" in response.data


def test_dashboard_lists_created_client(client):
    client.post(
        "/clients",
        data={"name": "Kavya", "weight": "55", "height": "158", "program": "Beginner (BG)"},
        follow_redirects=True,
    )
    assert b"Kavya" in client.get("/").data


def test_programs_page_lists_all_programs(client):
    response = client.get("/programs")
    assert response.status_code == 200
    assert b"Muscle Gain" in response.data


def test_new_client_form_renders(client):
    assert b"Client intake" in client.get("/clients/new").data


def test_create_client_via_form_redirects_to_detail(client):
    response = client.post(
        "/clients",
        data={"name": "Rahul", "weight": "72", "height": "170", "program": "Beginner (BG)"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Rahul" in response.data
    assert b"Client" in response.data


def test_create_client_via_form_shows_validation_errors(client):
    response = client.post("/clients", data={"name": "", "program": ""})
    assert response.status_code == 400
    assert b"Name is required" in response.data


def test_client_detail_unknown_name_returns_404_page(client):
    response = client.get("/clients/Unknown")
    assert response.status_code == 404
    assert b"Client not found" in response.data


def test_log_progress_from_detail_page(client):
    client.post(
        "/clients",
        data={"name": "Divya", "weight": "60", "height": "162", "program": "Beginner (BG)"},
        follow_redirects=True,
    )
    response = client.post(
        "/clients/Divya/progress", data={"adherence": "80"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"80" in response.data


def test_log_progress_rejects_invalid_value(client):
    client.post(
        "/clients",
        data={"name": "Sam", "weight": "60", "height": "162", "program": "Beginner (BG)"},
        follow_redirects=True,
    )
    response = client.post(
        "/clients/Sam/progress", data={"adherence": "999"}, follow_redirects=True
    )
    assert b"between 0 and 100" in response.data
