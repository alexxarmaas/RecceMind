from __future__ import annotations

from typing import Any

import requests


class MapsServiceError(RuntimeError):
    """Raised when Google Routes cannot provide a usable route."""


class MapsService:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def get_route(self, origin: str, destination: str) -> dict[str, Any]:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.polyline,routes.distanceMeters,routes.duration",
        }
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "DRIVE",
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MapsServiceError("Google Routes request failed") from exc

        route_data = response.json()
        if not route_data.get("routes"):
            raise MapsServiceError("Google Routes returned no routes")
        return route_data
