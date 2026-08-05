import pytest
from geometry.geometry_engine import Curve
from geometry.classification_engine import classify_curve, classify_curves
from geometry.pacenote_generator import generate_pacenotes

def test_classify_curve():
    assert classify_curve(160) == 6
    assert classify_curve(120) == 5
    assert classify_curve(80) == 4
    assert classify_curve(40) == 3
    assert classify_curve(30) == 2
    assert classify_curve(10) == 1

def test_classify_curves():
    c1 = Curve(0, 10, 0, 50, 50, 160, 10, "Derecha")
    c2 = Curve(15, 20, 100, 120, 20, 15, 45, "Izquierda")
    
    classified = classify_curves([c1, c2])
    
    assert len(classified) == 2
    assert classified[0]["classification"] == 6
    assert classified[1]["classification"] == 1
    
def test_generate_pacenotes():
    classified_curves = [
        {
            "start_distance": 100,
            "end_distance": 150,
            "length": 50,
            "direction": "Derecha",
            "classification": 4
        },
        {
            "start_distance": 210, # dist between = 210 - 150 = 60
            "end_distance": 290,
            "length": 80,
            "direction": "Izquierda",
            "classification": 3
        }
    ]
    
    notes = generate_pacenotes(classified_curves)
    
    # 100, Derecha 4 larga, 60, Izquierda 3 larga
    assert notes == ["100", "Derecha 4 larga", "60", "Izquierda 3 larga"]

def test_generate_pacenotes_horquilla():
    classified_curves = [
        {
            "start_distance": 50,
            "end_distance": 70,
            "length": 20,
            "direction": "Derecha",
            "classification": 1
        }
    ]
    notes = generate_pacenotes(classified_curves)
    assert notes == ["50", "Horquilla derecha"]
