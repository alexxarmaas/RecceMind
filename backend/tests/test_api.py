from fastapi.testclient import TestClient

from config import settings
from main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_token_protects_api_when_configured():
    original_token = settings.service_token
    object.__setattr__(settings, "service_token", "test-service-token")
    try:
        with TestClient(app) as client:
            unauthorized = client.get("/api/health")
            authorized = client.get(
                "/api/health",
                headers={"X-RecceMind-Token": "test-service-token"},
            )
    finally:
        object.__setattr__(settings, "service_token", original_token)

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json() == {"status": "ok"}


def test_thresholds_are_coerced_from_json_keys():
    payload = {
        "polyline": "???",
        "thresholds": {"6": 180, "5": 120, "4": 75, "3": 45, "2": 25},
    }
    with TestClient(app) as client:
        response = client.post("/api/process-polyline", json=payload)
    assert response.status_code in {200, 400}
    assert response.status_code != 422


def test_invalid_coordinates_are_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/process-coords",
            json={"coordinates": [[95, 0], [28, -15], [28.1, -15.1]]},
        )
    assert response.status_code == 422
