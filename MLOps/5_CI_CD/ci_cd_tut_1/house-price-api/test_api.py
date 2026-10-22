
import pytest
from fastapi.testclient import TestClient

from main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_prediction_endpoint(client):
    response = client.post(
        "/predict",
        json={"area": 1500, "bedrooms": 3}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["area_sqft"] == 1500
    assert data["bedrooms"] == 3
    assert data["predicted_price_lakhs"] > 0


def test_invalid_area(client):
    response = client.post(
        "/predict",
        json={"area": -100, "bedrooms": 3}
    )

    assert response.status_code == 422


def test_invalid_bedrooms(client):
    response = client.post(
        "/predict",
        json={"area": 1500, "bedrooms": 0}
    )

    assert response.status_code == 422
