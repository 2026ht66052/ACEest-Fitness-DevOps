"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture
def app(tmp_path):
    """A Flask app bound to a throwaway SQLite file."""
    database = tmp_path / "test.db"
    application = create_app(TestConfig, DATABASE=str(database))
    yield application


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_client(client):
    """Create and return one persisted client."""
    payload = {
        "name": "Arun",
        "age": 29,
        "height": 175,
        "weight": 80,
        "program": "Muscle Gain (MG) - PPL",
        "target_weight": 85,
        "target_adherence": 90,
    }
    response = client.post("/api/v1/clients", json=payload)
    assert response.status_code == 201
    return response.get_json()
