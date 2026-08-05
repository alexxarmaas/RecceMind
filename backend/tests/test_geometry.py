from geometry.classification_engine import classify_curve
from geometry.geometry_engine import Curve, calculate_speed_profile, parse_telemetry_csv
from geometry.pacenote_generator import generate_pacenotes


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
    assert notes[1]["text"] == "Derecha 4 larga"
    assert notes[1]["curve_index"] == 0
    assert notes[2]["text"] == "60"
    assert notes[3]["text"] == "Izquierda 3 larga se cierra"


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
