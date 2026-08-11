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


def classify_curve_ml(
    curve: Curve,
    thresholds: dict | None = None,
    driver_id: str = "default",
) -> int:
    with _model_lock:
        classifier = _ml_models.get(driver_id)

    if classifier is not None:
        try:
            features = np.array(
                [[curve.radius, abs(curve.heading_change), curve.length]],
                dtype=float,
            )
            return int(classifier.predict(features)[0])
        except (TypeError, ValueError):
            pass
    return classify_curve(curve.radius, thresholds)


def classify_curves(
    curves: list[Curve],
    thresholds: dict | None = None,
    driver_id: str = "default",
) -> list[dict]:
    result: list[dict] = []
    for curve in curves:
        classification = classify_curve_ml(curve, thresholds, driver_id)
        curve_data = curve.to_dict()
        curve_data["classification"] = classification
        curve_data["entry_classification"] = (
            classify_curve(curve.entry_radius, thresholds)
            if curve.entry_radius is not None
            else classification
        )
        curve_data["exit_classification"] = (
            classify_curve(curve.exit_radius, thresholds)
            if curve.exit_radius is not None
            else classification
        )
        result.append(curve_data)
    return result
