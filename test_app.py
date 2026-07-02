"""Tests for the CI/CD Pipeline Lab API."""

import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_returns_200(client):
    """Health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json(client):
    """Health endpoint returns valid JSON with status and version."""
    response = client.get("/health")
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_info_returns_200(client):
    """Info endpoint returns 200 OK."""
    response = client.get("/api/info")
    assert response.status_code == 200


def test_info_contains_name(client):
    """Info endpoint includes application name."""
    response = client.get("/api/info")
    data = response.get_json()
    assert data["name"] == "Pipeline API"


def test_index_returns_200(client):
    """Root endpoint returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200


def test_nonexistent_route_returns_404(client):
    """Non-existent route returns 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
