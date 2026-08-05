from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class DriverScopedRequest(BaseModel):
    thresholds: dict[int, float] | None = None
    driver_id: str = Field(default="default", min_length=1, max_length=100, pattern=r"^[\w .-]+$")

    @field_validator("thresholds")
    @classmethod
    def validate_thresholds(cls, value: dict[int, float] | None) -> dict[int, float] | None:
        if value is None:
            return None

        normalized = {int(level): float(radius) for level, radius in value.items()}
        invalid_levels = set(normalized) - {2, 3, 4, 5, 6}
        if invalid_levels:
            raise ValueError(f"Unsupported curve levels: {sorted(invalid_levels)}")
        if any(radius <= 0 for radius in normalized.values()):
            raise ValueError("Curve thresholds must be positive")

        ordered = [normalized[level] for level in (2, 3, 4, 5, 6) if level in normalized]
        if ordered != sorted(ordered):
            raise ValueError("Thresholds must increase from curve level 2 to level 6")
        return normalized


class RouteRequest(DriverScopedRequest):
    origin: str = Field(min_length=2, max_length=300)
    destination: str = Field(min_length=2, max_length=300)


class PolylineRequest(DriverScopedRequest):
    polyline: str = Field(min_length=3, max_length=2_000_000)


class GpxRequest(DriverScopedRequest):
    gpx_content: str = Field(min_length=10, max_length=10_000_000)


class CoordsRequest(DriverScopedRequest):
    coordinates: list[list[float]] = Field(min_length=3, max_length=250_000)

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, coordinates: list[list[float]]) -> list[list[float]]:
        for index, coordinate in enumerate(coordinates):
            if len(coordinate) != 2:
                raise ValueError(f"Coordinate {index} must contain [latitude, longitude]")
            latitude, longitude = coordinate
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(f"Coordinate {index} is outside valid latitude/longitude bounds")
        return coordinates


class FeedbackRequest(BaseModel):
    radius: float = Field(gt=0)
    heading_change: float
    length: float = Field(gt=0)
    original_classification: int = Field(ge=1, le=6)
    user_classification: int = Field(ge=1, le=6)
    driver_id: str = Field(default="default", min_length=1, max_length=100, pattern=r"^[\w .-]+$")


class ErrorResponse(BaseModel):
    detail: str
    context: dict[str, Any] | None = None
