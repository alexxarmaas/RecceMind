from __future__ import annotations

from typing import Iterable


def _curve_text(curve: dict) -> str:
    classification = int(curve["classification"])
    direction = str(curve["direction"])
    prefix = ""
    suffix = ""

    max_braking = curve.get("max_braking")
    if max_braking is not None and max_braking > 0.5:
        prefix = "Frena "

    max_speed = curve.get("max_speed")
    if max_speed is not None and max_speed > 27.0 and classification <= 3:
        prefix = "Ojo " + prefix

    min_gear = curve.get("min_gear")
    if min_gear is not None:
        suffix = f" en {int(min_gear)}ª"

    if classification == 1:
        text = f"{prefix}Horquilla {direction.lower()}"
    else:
        text = f"{prefix}{direction} {classification}"

    if float(curve["length"]) > 40:
        text += " larga"
    if curve.get("modifier"):
        text += str(curve["modifier"])
    return text + suffix


def generate_pacenotes(
    classified_curves: list[dict], extra_events: Iterable[dict] | None = None
) -> list[dict]:
    events: list[dict] = []
    curve_ends: dict[int, float] = {}

    for index, curve in enumerate(classified_curves):
        position = float(curve["start_distance"])
        curve_ends[index] = float(curve["end_distance"])
        events.append(
            {
                "type": "note",
                "text": _curve_text(curve),
                "curve_index": index,
                "distance": round(position, 2),
            }
        )

    for event in extra_events or []:
        if "distance" not in event:
            continue
        events.append(
            {
                "type": "note",
                "text": str(event["text"]),
                "curve_index": event.get("curve_index"),
                "distance": round(float(event["distance"]), 2),
            }
        )

    events.sort(key=lambda event: (event["distance"], event["curve_index"] is None))

    notes: list[dict] = []
    previous_end = 0.0
    for event in events:
        gap = max(0.0, float(event["distance"]) - previous_end)
        if gap > 10:
            notes.append(
                {
                    "type": "distance",
                    "text": str(round(gap)),
                    "curve_index": None,
                    "distance": round(float(event["distance"]), 2),
                }
            )
        notes.append(event)

        curve_index = event.get("curve_index")
        if curve_index is not None and curve_index in curve_ends:
            previous_end = max(previous_end, curve_ends[curve_index])
        else:
            previous_end = max(previous_end, float(event["distance"]))

    return notes
