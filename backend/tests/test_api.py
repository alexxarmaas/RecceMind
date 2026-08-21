import io
import zipfile

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


def test_route_request_accepts_map_coordinates_before_calling_google():
    original_key = settings.google_maps_api_key
    object.__setattr__(settings, "google_maps_api_key", "")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/analyze-route",
                json={
                    "origin_coords": [28.10, -15.50],
                    "destination_coords": [28.12, -15.47],
                },
            )
    finally:
        object.__setattr__(settings, "google_maps_api_key", original_key)

    assert response.status_code == 503
    assert response.status_code != 422


def test_process_kmz_uses_longest_linestring():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>Short helper</name><LineString><coordinates>
        -15.50,28.10,0 -15.499,28.101,0 -15.498,28.102,0
      </coordinates></LineString></Placemark>
      <Placemark><name>TC Demo</name><LineString><coordinates>
        -15.50,28.10,0 -15.499,28.101,0 -15.497,28.102,0 -15.495,28.1025,0 -15.493,28.104,0
      </coordinates></LineString></Placemark>
    </Document></kml>"""
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", kml)

    with TestClient(app) as client:
        response = client.post(
            "/api/process-kmz",
            files={"file": ("vmrm-demo.kmz", archive_buffer.getvalue(), "application/vnd.google-earth.kmz")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sourceName"] == "TC Demo"
    assert payload["kmzTrackCount"] == 2
    assert payload["polyline"]
