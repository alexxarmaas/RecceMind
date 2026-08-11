import math

import polyline

from geometry.classification_engine import classify_curve
from geometry.geometry_engine import (
    EARTH_RADIUS_M,
    Curve,
    analyze_polyline,
    calculate_speed_profile,
    haversine_distance,
    parse_telemetry_csv,
    resample_points,
)
from geometry.pacenote_generator import generate_pacenotes, render_pacenote


def test_classify_curve_accepts_json_string_keys():
    thresholds = {"6": 180, "5": 120, "4": 75, "3": 45, "2": 25}
    assert classify_curve(181, thresholds) == 6
    assert classify_curve(121, thresholds) == 5
    assert classify_curve(76, thresholds) == 4
    assert classify_curve(46, thresholds) == 3
    assert classify_curve(26, thresholds) == 2
    assert classify_curve(10, thresholds) == 1


def test_generate_pacenotes_returns_frontend_contract():
    curves = [
        {
            "start_distance": 100,
            "end_distance": 150,
            "length": 50,
            "direction": "Derecha",
            "classification": 4,
            "modifier": "",
        },
        {
            "start_distance": 210,
            "end_distance": 290,
            "length": 80,
            "direction": "Izquierda",
            "classification": 3,
            "modifier": " se cierra",
        },
    ]

    notes = generate_pacenotes(curves)

    assert notes[0]["type"] == "distance"
    assert notes[0]["text"] == "100"
    assert notes[0]["structured"] == {"kind": "distance", "meters": 100}
    assert notes[1]["text"] == "Derecha 4 larga"
    assert notes[1]["curve_index"] == 0
    assert notes[1]["structured"] == {
        "kind": "curve",
        "direction": "right",
        "severity": 4,
        "length": "long",
        "modifiers": [],
        "warnings": [],
    }
    assert notes[2]["text"] == "60"
    assert notes[3]["text"] == "Izquierda 3 larga se cierra"
    assert notes[3]["structured"]["modifiers"] == ["tightens"]


def test_structured_pacenote_renders_telemetry_warnings():
    structured = {
        "kind": "curve",
        "direction": "left",
        "severity": 2,
        "length": "standard",
        "modifiers": ["opens"],
        "warnings": ["caution", "brake"],
        "gear": 2,
    }

    assert render_pacenote(structured) == "Ojo Frena Izquierda 2 se abre en 2ª"


def test_extra_events_are_inserted_by_absolute_distance():
    curves = [
        {
            "start_distance": 100,
            "end_distance": 140,
            "length": 40,
            "direction": "Derecha",
            "classification": 4,
            "modifier": "",
        }
    ]
    events = [{"type": "note", "text": "Rasante", "distance": 50, "curve_index": None}]

    notes = generate_pacenotes(curves, events)

    assert [note["text"] for note in notes] == ["50", "Rasante", "50", "Derecha 4"]
    assert notes[1]["structured"] == {"kind": "crest"}


def test_resample_points_uses_metric_spacing_and_keeps_endpoints():
    points = [(28.0, -15.0), (28.0, -14.999)]
    sampled = resample_points(points, spacing_m=10)

    assert sampled[0] == points[0]
    assert sampled[-1] == points[-1]
    assert len(sampled) > 5

    segments = [
        haversine_distance(first[0], first[1], second[0], second[1])
        for first, second in zip(sampled, sampled[1:])
    ]
    assert max(segments) <= 10.1
    assert all(segment > 0 for segment in segments)


def _quarter_circle(samples: int, radius_m: float = 80.0) -> list[tuple[float, float]]:
    center_latitude = 28.0
    center_longitude = -15.0
    points: list[tuple[float, float]] = []
    for angle in [index * (math.pi / 2) / (samples - 1) for index in range(samples)]:
        x = radius_m * math.cos(angle)
        y = radius_m * math.sin(angle)
        latitude = center_latitude + math.degrees(y / EARTH_RADIUS_M)
        longitude = center_longitude + math.degrees(
            x / (EARTH_RADIUS_M * math.cos(math.radians(center_latitude)))
        )
        points.append((latitude, longitude))
    return points


def test_curve_detection_is_stable_across_source_sampling_density():
    sparse = analyze_polyline(polyline.encode(_quarter_circle(12)))
    dense = analyze_polyline(polyline.encode(_quarter_circle(40)))

    assert len(sparse) == 1
    assert len(dense) == 1
    assert sparse[0].direction == dense[0].direction
    assert abs(sparse[0].radius - dense[0].radius) < 15
    assert abs(sparse[0].length - dense[0].length) < 20
    assert 60 <= abs(sparse[0].heading_change) <= 110
    assert 60 <= abs(dense[0].heading_change) <= 110


def test_telemetry_parser_skips_invalid_rows():
    points, telemetry = parse_telemetry_csv(
        "lat,lon,speed,brake,gear\n28.1,-15.4,30,0.4,3\ninvalid,-15.5,20,0,2\n"
    )
    assert points == [(28.1, -15.4)]
    assert telemetry == [{"speed": 30.0, "brake": 0.4, "gear": 3}]


def test_speed_profile_respects_requested_cap():
    points = [(28.0, -15.0), (28.0001, -15.0), (28.0002, -15.0)]
    speeds = calculate_speed_profile(points, max_speed_mps=30)
    assert len(speeds) == len(points)
    assert max(speeds) <= 30


def test_curve_serialization_keeps_optional_telemetry():
    curve = Curve(0, 4, 0, 30, 30, 45, 60, "Derecha", max_speed=20, min_gear=2)
    payload = curve.to_dict()
    assert payload["max_speed"] == 20
    assert payload["min_gear"] == 2
