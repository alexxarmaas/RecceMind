from fastapi.testclient import TestClient

from main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
