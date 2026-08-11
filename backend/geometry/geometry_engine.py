from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from math import sqrt
from typing import Any

import numpy as np
import polyline
from scipy.interpolate import CubicSpline

EARTH_RADIUS_M = 6_371_000.0


@dataclass
class Curve:
    start_idx: int
    end_idx: int
    start_distance: float
    end_distance: float
    length: float
    radius: float
    heading_change: float
    direction: str
    modifier: str = ""
    entry_radius: float | None = None
    exit_radius: float | None = None
    max_speed: float | None = None
    min_gear: int | None = None
    max_braking: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "start_distance": round(self.start_distance, 2),
            "end_distance": round(self.end_distance, 2),
            "length": round(self.length, 2),
            "radius": round(self.radius, 2),
            "heading_change": round(self.heading_change, 2),
            "direction": self.direction,
            "modifier": self.modifier,
        }
        if self.entry_radius is not None:
            data["entry_radius"] = round(self.entry_radius, 2)
        if self.exit_radius is not None:
            data["exit_radius"] = round(self.exit_radius, 2)
        if self.max_speed is not None:
            data["max_speed"] = round(self.max_speed, 2)
        if self.min_gear is not None:
            data["min_gear"] = self.min_gear
        if self.max_braking is not None:
            data["max_braking"] = round(self.max_braking, 2)
        return data


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    value = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
    )
    return float(EARTH_RADIUS_M * 2 * np.arctan2(np.sqrt(value), np.sqrt(1 - value)))


def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lon1_r, lat2_r, lon2_r = map(np.radians, [lat1, lon1, lat2, lon2])
    delta_lon = lon2_r - lon1_r
    x = np.sin(delta_lon) * np.cos(lat2_r)
    y = np.cos(lat1_r) * np.sin(lat2_r) - (
        np.sin(lat1_r) * np.cos(lat2_r) * np.cos(delta_lon)
    )
    return float((np.degrees(np.arctan2(x, y)) + 360) % 360)


def normalize_heading_change(value: float) -> float:
    return float((value + 180) % 360 - 180)


def _to_local_xy(points: list[tuple[float, float]]) -> np.ndarray:
    if not points:
        return np.empty((0, 2), dtype=float)
    origin_lat = np.radians(points[0][0])
    origin_lon = np.radians(points[0][1])
    coordinates = []
    for latitude, longitude in points:
        latitude_r = np.radians(latitude)
        longitude_r = np.radians(longitude)
        x = (longitude_r - origin_lon) * EARTH_RADIUS_M * np.cos(origin_lat)
        y = (latitude_r - origin_lat) * EARTH_RADIUS_M
        coordinates.append((x, y))
    return np.asarray(coordinates, dtype=float)


def _from_local_xy(
    coordinates: np.ndarray,
    origin: tuple[float, float],
) -> list[tuple[float, float]]:
    origin_lat = np.radians(origin[0])
    origin_lon = np.radians(origin[1])
    points: list[tuple[float, float]] = []
    for x, y in coordinates:
        latitude_r = origin_lat + float(y) / EARTH_RADIUS_M
        longitude_r = origin_lon + float(x) / (EARTH_RADIUS_M * np.cos(origin_lat))
        points.append((float(np.degrees(latitude_r)), float(np.degrees(longitude_r))))
    return points


def calculate_curvature(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> float:
    xy = _to_local_xy([p1, p2, p3])
    side_a = float(np.linalg.norm(xy[1] - xy[2]))
    side_b = float(np.linalg.norm(xy[0] - xy[2]))
    side_c = float(np.linalg.norm(xy[0] - xy[1]))
    semiperimeter = (side_a + side_b + side_c) / 2
    area_sq = (
        semiperimeter
        * (semiperimeter - side_a)
        * (semiperimeter - side_b)
        * (semiperimeter - side_c)
    )
    if area_sq <= 1e-8:
        return float("inf")
    area = sqrt(area_sq)
    return (side_a * side_b * side_c) / (4 * area)


def smooth_points(
    points: list[tuple[float, float]],
    window: int = 5,
) -> list[tuple[float, float]]:
    if len(points) < 3 or window <= 1:
        return points
    window = max(3, window if window % 2 else window + 1)
    radius = window // 2
    smoothed: list[tuple[float, float]] = []
    for index in range(len(points)):
        start = max(0, index - radius)
        end = min(len(points), index + radius + 1)
        sample = points[start:end]
        weights = np.arange(1, len(sample) + 1, dtype=float)
        center = len(sample) // 2
        weights = np.minimum(weights, weights[::-1])
        if center == 0:
            weights = np.ones(len(sample), dtype=float)
        total = float(weights.sum())
        latitude = sum(point[0] * weight for point, weight in zip(sample, weights)) / total
        longitude = sum(point[1] * weight for point, weight in zip(sample, weights)) / total
        smoothed.append((latitude, longitude))
    smoothed[0] = points[0]
    smoothed[-1] = points[-1]
    return smoothed


def _cumulative_distances(points: list[tuple[float, float]]) -> list[float]:
    distances = [0.0]
    for first, second in zip(points, points[1:]):
        distances.append(
            distances[-1]
            + haversine_distance(first[0], first[1], second[0], second[1])
        )
    return distances


def _deduplicate_points(
    points: list[tuple[float, float]],
    minimum_distance_m: float = 0.05,
) -> list[tuple[float, float]]:
    if not points:
        return []
    deduplicated = [points[0]]
    for point in points[1:]:
        previous = deduplicated[-1]
        if (
            haversine_distance(previous[0], previous[1], point[0], point[1])
            > minimum_distance_m
        ):
            deduplicated.append(point)
    return deduplicated


def resample_points(
    points: list[tuple[float, float]],
    spacing_m: float = 2.0,
) -> list[tuple[float, float]]:
    """Return a smooth path sampled at approximately fixed metric intervals."""
    if spacing_m <= 0:
        raise ValueError("spacing_m must be positive")

    clean_points = _deduplicate_points(points)
    if len(clean_points) < 2:
        return clean_points

    local_xy = _to_local_xy(clean_points)
    source_distances = [0.0]
    for first, second in zip(local_xy, local_xy[1:]):
        source_distances.append(
            source_distances[-1] + float(np.linalg.norm(second - first))
        )

    total_distance = source_distances[-1]
    if total_distance <= spacing_m:
        return [clean_points[0], clean_points[-1]]

    targets = np.arange(0.0, total_distance, spacing_m, dtype=float)
    if targets.size == 0 or total_distance - float(targets[-1]) > 1e-6:
        targets = np.append(targets, total_distance)

    source = np.asarray(source_distances, dtype=float)
    if len(clean_points) >= 4:
        x_spline = CubicSpline(source, local_xy[:, 0], bc_type="natural")
        y_spline = CubicSpline(source, local_xy[:, 1], bc_type="natural")
        sampled_xy = np.column_stack((x_spline(targets), y_spline(targets)))
    else:
        sampled_xy = np.column_stack(
            (
                np.interp(targets, source, local_xy[:, 0]),
                np.interp(targets, source, local_xy[:, 1]),
            )
        )

    sampled = _from_local_xy(sampled_xy, clean_points[0])
    sampled[0] = clean_points[0]
    sampled[-1] = clean_points[-1]
    return sampled


def _nearest_distance_index(distances: list[float], target: float) -> int:
    if not distances:
        return 0
    position = int(np.searchsorted(distances, target, side="left"))
    if position <= 0:
        return 0
    if position >= len(distances):
        return len(distances) - 1
    before = position - 1
    return (
        before
        if abs(distances[before] - target) <= abs(distances[position] - target)
        else position
    )


def _signed_heading_change(
    points: list[tuple[float, float]],
    start_idx: int,
    end_idx: int,
) -> float:
    if end_idx - start_idx < 2:
        return 0.0

    bearings = [
        initial_bearing(*points[index], *points[index + 1])
        for index in range(start_idx, end_idx)
    ]
    return float(
        sum(
            normalize_heading_change(second - first)
            for first, second in zip(bearings, bearings[1:])
        )
    )


def summarize_radius_profile(
    radii: list[float],
    *,
    transition_ratio: float = 1.35,
) -> tuple[float | None, float | None, str]:
    """Summarize how curve radius evolves from entry to exit.

    Medians over the first and last thirds make the transition estimate resistant to
    one noisy curvature sample. A modifier is emitted only when the radius changes by
    at least ``transition_ratio`` in a consistent direction.
    """
    finite = [float(radius) for radius in radii if np.isfinite(radius) and radius > 0]
    if not finite:
        return None, None, ""

    if len(finite) < 4:
        representative = float(np.median(finite))
        return representative, representative, ""

    phase_size = max(2, len(finite) // 3)
    entry_radius = float(np.median(finite[:phase_size]))
    exit_radius = float(np.median(finite[-phase_size:]))

    if entry_radius > transition_ratio * exit_radius:
        modifier = " se cierra"
    elif exit_radius > transition_ratio * entry_radius:
        modifier = " se abre"
    else:
        modifier = ""
    return entry_radius, exit_radius, modifier


def analyze_polyline(
    encoded_polyline: str,
    telemetry: list[dict] | None = None,
    *,
    max_curve_radius: float = 250.0,
    min_local_heading_change: float = 2.0,
    min_total_heading_change: float = 6.0,
    min_curve_length: float = 10.0,
    resample_spacing_m: float = 2.0,
    analysis_window_m: float = 8.0,
    gap_tolerance_m: float = 8.0,
) -> list[Curve]:
    raw_points = polyline.decode(encoded_polyline)
    if len(raw_points) < 3:
        return []

    raw_distances = _cumulative_distances(raw_points)
    sampled_points = resample_points(raw_points, spacing_m=resample_spacing_m)
    points = smooth_points(sampled_points, window=5)

    analysis_window = max(2, int(round(analysis_window_m / resample_spacing_m)))
    if len(points) < 2 * analysis_window + 1:
        return []

    gap_tolerance = max(1, int(round(gap_tolerance_m / resample_spacing_m)))
    distances = _cumulative_distances(points)
    current: dict[str, Any] | None = None
    curves: list[dict[str, Any]] = []
    gap_count = 0

    def close_current() -> None:
        nonlocal current, gap_count
        if current is None:
            return

        start_idx = int(current["start_idx"])
        end_idx = int(current["end_idx"])
        length = distances[end_idx] - distances[start_idx]
        heading_change = _signed_heading_change(points, start_idx, end_idx)
        if length >= min_curve_length and abs(heading_change) >= min_total_heading_change:
            current["start_distance"] = distances[start_idx]
            current["end_distance"] = distances[end_idx]
            current["heading_change"] = heading_change
            curves.append(current)
        current = None
        gap_count = 0

    for index in range(analysis_window, len(points) - analysis_window):
        left = index - analysis_window
        right = index + analysis_window
        incoming = initial_bearing(*points[left], *points[index])
        outgoing = initial_bearing(*points[index], *points[right])
        local_heading_change = normalize_heading_change(outgoing - incoming)
        radius = calculate_curvature(points[left], points[index], points[right])
        candidate = (
            np.isfinite(radius)
            and radius <= max_curve_radius
            and abs(local_heading_change) >= min_local_heading_change
        )

        if not candidate:
            if current is not None:
                gap_count += 1
                if gap_count > gap_tolerance:
                    close_current()
            continue

        direction = "Derecha" if local_heading_change > 0 else "Izquierda"
        if current is None or current["direction"] != direction:
            close_current()
            current = {
                "start_idx": left,
                "end_idx": right,
                "direction": direction,
                "radii": [radius],
            }
        else:
            current["end_idx"] = right
            current["radii"].append(radius)
        gap_count = 0

    close_current()

    curve_objects: list[Curve] = []
    for curve in curves:
        start_distance = float(curve["start_distance"])
        end_distance = float(curve["end_distance"])
        source_start_idx = _nearest_distance_index(raw_distances, start_distance)
        source_end_idx = _nearest_distance_index(raw_distances, end_distance)
        finite_radii = [radius for radius in curve["radii"] if np.isfinite(radius)]
        representative_radius = (
            float(np.percentile(finite_radii, 30))
            if finite_radii
            else max_curve_radius
        )
        entry_radius, exit_radius, modifier = summarize_radius_profile(curve["radii"])
        max_speed = None
        min_gear = None
        max_braking = None

        if telemetry:
            start_telemetry = max(0, source_start_idx - 5)
            end_telemetry = min(len(telemetry), source_end_idx + 1)
            sample = telemetry[start_telemetry:end_telemetry]
            speeds = [
                item.get("speed") for item in sample if item.get("speed") is not None
            ]
            gears = [
                item.get("gear") for item in sample if item.get("gear") is not None
            ]
            brakes = [
                item.get("brake") for item in sample if item.get("brake") is not None
            ]
            max_speed = max(speeds) if speeds else None
            min_gear = min(gears) if gears else None
            max_braking = max(brakes) if brakes else None

        curve_objects.append(
            Curve(
                start_idx=source_start_idx,
                end_idx=source_end_idx,
                start_distance=start_distance,
                end_distance=end_distance,
                length=end_distance - start_distance,
                radius=representative_radius,
                heading_change=float(curve["heading_change"]),
                direction=str(curve["direction"]),
                modifier=modifier,
                entry_radius=entry_radius,
                exit_radius=exit_radius,
                max_speed=max_speed,
                min_gear=min_gear,
                max_braking=max_braking,
            )
        )
    return curve_objects


def parse_telemetry_csv(content: str) -> tuple[list[tuple[float, float]], list[dict]]:
    points: list[tuple[float, float]] = []
    telemetry: list[dict] = []
    reader = csv.DictReader(io.StringIO(content.strip()))
    for row in reader:
        clean_row = {key.strip().lower(): value for key, value in row.items() if key}
        try:
            latitude = float(clean_row["lat"])
            longitude = float(clean_row["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            continue
        points.append((latitude, longitude))
        sample: dict[str, float | int] = {}
        for key in ("speed", "brake"):
            try:
                if clean_row.get(key) not in (None, ""):
                    sample[key] = float(clean_row[key])
            except ValueError:
                pass
        try:
            if clean_row.get("gear") not in (None, ""):
                sample["gear"] = int(float(clean_row["gear"]))
        except ValueError:
            pass
        telemetry.append(sample)
    return points, telemetry


def extract_crests(
    points: list[tuple[float, float]],
    elevations: list[float],
) -> list[dict]:
    if len(points) < 11 or len(elevations) != len(points):
        return []
    distances = _cumulative_distances(points)
    crests: list[dict] = []
    for index in range(5, len(elevations) - 5):
        window = elevations[index - 5 : index + 6]
        if elevations[index] < max(window):
            continue
        left_min = min(elevations[index - 5 : index])
        right_min = min(elevations[index + 1 : index + 6])
        prominence = min(
            elevations[index] - left_min,
            elevations[index] - right_min,
        )
        if prominence >= 2.0:
            crests.append(
                {
                    "type": "note",
                    "text": "Salto" if prominence >= 5.0 else "Rasante",
                    "distance": distances[index],
                    "curve_index": None,
                }
            )

    filtered: list[dict] = []
    last_distance = -100.0
    for crest in crests:
        if crest["distance"] - last_distance >= 50:
            filtered.append(crest)
            last_distance = crest["distance"]
    return filtered


def calculate_speed_profile(
    points: list[tuple[float, float]],
    *,
    max_speed_mps: float = 40.0,
    lateral_acceleration_mps2: float = 6.0,
    acceleration_mps2: float = 2.5,
    braking_mps2: float = 6.0,
) -> list[float]:
    if not points:
        return []
    if len(points) < 3:
        return [min(20.0, max_speed_mps)] * len(points)

    distances = _cumulative_distances(points)
    speeds = [max_speed_mps] * len(points)
    for index in range(1, len(points) - 1):
        radius = calculate_curvature(
            points[index - 1],
            points[index],
            points[index + 1],
        )
        if np.isfinite(radius):
            speeds[index] = min(
                max_speed_mps,
                sqrt(max(0.0, lateral_acceleration_mps2 * radius)),
            )

    for index in range(len(points) - 2, -1, -1):
        segment = max(0.01, distances[index + 1] - distances[index])
        braking_limit = sqrt(
            max(0.0, speeds[index + 1] ** 2 + 2 * braking_mps2 * segment)
        )
        speeds[index] = min(speeds[index], braking_limit)

    for index in range(1, len(points)):
        segment = max(0.01, distances[index] - distances[index - 1])
        acceleration_limit = sqrt(
            max(0.0, speeds[index - 1] ** 2 + 2 * acceleration_mps2 * segment)
        )
        speeds[index] = min(speeds[index], acceleration_limit)

    return [round(speed, 3) for speed in speeds]
