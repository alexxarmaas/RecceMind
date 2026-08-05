from typing import List
from .geometry_engine import Curve
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Global models dictionary
ml_models = {}

DEFAULT_THRESHOLDS = {
    6: 150,
    5: 100,
    4: 60,
    3: 35,
    2: 20
}

def classify_curve(radius: float, thresholds: dict = None) -> int:
    """
    Classifies a curve based on its radius using a configurable scale (1 to 6).
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
        
    if radius > thresholds.get(6, 150):
        return 6
    elif radius > thresholds.get(5, 100):
        return 5
    elif radius > thresholds.get(4, 60):
        return 4
    elif radius > thresholds.get(3, 35):
        return 3
    elif radius > thresholds.get(2, 20):
        return 2
    else:
        return 1

def train_model(feedbacks, driver_id="default"):
    """Trains a Random Forest classifier based on user feedback for a specific driver."""
    global ml_models
    if not feedbacks or len(feedbacks) < 5:
        # Not enough data to train reliably
        return False
        
    X = []
    y = []
    for fb in feedbacks:
        X.append([fb.radius, abs(fb.heading_change), fb.length])
        y.append(fb.user_classification)
        
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X, y)
    ml_models[driver_id] = clf
    return True

def classify_curve_ml(curve: Curve, thresholds: dict = None, driver_id="default") -> int:
    """Classifies using ML if available for the driver, otherwise falls back to static thresholds."""
    if driver_id in ml_models:
        try:
            X = np.array([[curve.radius, abs(curve.heading_change), curve.length]])
            prediction = ml_models[driver_id].predict(X)[0]
            return int(prediction)
        except:
            pass
            
    return classify_curve(curve.radius, thresholds)

def classify_curves(curves: List[Curve], thresholds: dict = None, driver_id="default") -> List[dict]:
    """Adds a classification to a list of Curve objects."""
    classified_curves = []
    for curve in curves:
        curve_dict = curve.to_dict()
        curve_dict["classification"] = classify_curve_ml(curve, thresholds, driver_id)
        classified_curves.append(curve_dict)
    
    return classified_curves
