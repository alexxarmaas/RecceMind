from __future__ import annotations

from collections.abc import Iterable
from threading import RLock

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .geometry_engine import Curve

DEFAULT_THRESHOLDS: dict[int, float] = {
    6: 150.0,
    5: 100.0,
    4: 60.0,
    3: 35.0,
    2: 20.0,
}

_MIN_TRAINING_SAMPLES = 12
_ml_models: dict[str, RandomForestClassifier] = {}
_model_lock = RLock()


def normalize_thresholds(thresholds: dict | None) -> dict[int, float]:
    normalized = DEFAULT_THRESHOLDS.copy()
    if thresholds:
        normalized.update({int(level): float(radius) for level, radius in thresholds.items()})
    return normalized


def classify_curve(radius: float, thresholds: dict | None = None) -> int:
    current = normalize_thresholds(thresholds)
    if radius > current[6]:
        return 6
    if radius > current[5]:
        return 5
    if radius > current[4]:
        return 4
    if radius > current[3]:
        return 3
    if radius > current[2]:
        return 2
    return 1


def rule_confidence(radius: float, thresholds: dict | None = None) -> float:
    """Estimate confidence for threshold-based classification.

    Confidence is intentionally lowest close to a severity boundary and rises
    towards the middle of a band. Extreme classes use their nearest boundary
    and the adjacent band width as a scale. This is not a calibrated
    probability; it is a review-priority signal until enough driver feedback
    exists to use the ML classifier probability directly.
    """

    current = normalize_thresholds(thresholds)
    classification = classify_curve(radius, current)

    if classification == 6:
        boundary = current[6]
        scale = max(abs(current[6] - current[5]), 10.0)
        normalized_margin = max(0.0, min(1.0, (radius - boundary) / scale))
    elif classification == 1:
        boundary = current[2]
        scale = max(abs(current[3] - current[2]), 10.0)
        normalized_margin = max(0.0, min(1.0, (boundary - radius) / scale))
    else:
        lower = current[classification]
        upper = current[classification + 1]
        width = upper - lower
        if width <= 0:
            return 0.55
        margin = min(radius - lower, upper - radius)
        normalized_margin = max(0.0, min(1.0, margin / (width / 2)))

    return round(0.55 + 0.40 * normalized_margin, 3)


def train_model(feedbacks: Iterable, driver_id: str = "default") -> bool:
    feedback_list = list(feedbacks)
    labels = {feedback.user_classification for feedback in feedback_list}
    if len(feedback_list) < _MIN_TRAINING_SAMPLES or len(labels) < 2:
        return False

    features = np.array(
        [
            [feedback.radius, abs(feedback.heading_change), feedback.length]
            for feedback in feedback_list
        ],
        dtype=float,
    )
    targets = np.array(
        [feedback.user_classification for feedback in feedback_list],
        dtype=int,
    )

    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=1,
    )
    classifier.fit(features, targets)
    with _model_lock:
        _ml_models[driver_id] = classifier
    return True


def classify_curve_with_confidence(
    curve: Curve,
    thresholds: dict | None = None,
    driver_id: str = "default",
) -> tuple[int, float, str]:
    with _model_lock:
        classifier = _ml_models.get(driver_id)

    if classifier is not None:
        try:
            features = np.array(
                [[curve.radius, abs(curve.heading_change), curve.length]],
                dtype=float,
            )
            prediction = int(classifier.predict(features)[0])
            probabilities = classifier.predict_proba(features)[0]
            confidence = float(np.max(probabilities))
            return prediction, round(max(0.0, min(1.0, confidence)), 3), "ml"
        except (AttributeError, TypeError, ValueError):
            pass

    classification = classify_curve(curve.radius, thresholds)
    return classification, rule_confidence(curve.radius, thresholds), "rule"


def classify_curve_ml(
    curve: Curve,
    thresholds: dict | None = None,
    driver_id: str = "default",
) -> int:
    classification, _, _ = classify_curve_with_confidence(curve, thresholds, driver_id)
    return classification


def classify_curves(
    curves: list[Curve],
    thresholds: dict | None = None,
    driver_id: str = "default",
) -> list[dict]:
    result: list[dict] = []
    for curve in curves:
        classification, confidence, source = classify_curve_with_confidence(
            curve,
            thresholds,
            driver_id,
        )
        curve_data = curve.to_dict()
        curve_data["classification"] = classification
        curve_data["classification_confidence"] = confidence
        curve_data["classification_source"] = source

        if curve.entry_radius is not None:
            curve_data["entry_classification"] = classify_curve(curve.entry_radius, thresholds)
            curve_data["entry_confidence"] = rule_confidence(curve.entry_radius, thresholds)
        else:
            curve_data["entry_classification"] = classification
            curve_data["entry_confidence"] = confidence

        if curve.exit_radius is not None:
            curve_data["exit_classification"] = classify_curve(curve.exit_radius, thresholds)
            curve_data["exit_confidence"] = rule_confidence(curve.exit_radius, thresholds)
        else:
            curve_data["exit_classification"] = classification
            curve_data["exit_confidence"] = confidence

        result.append(curve_data)
    return result
