from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _curve_structure(curve: dict) -> dict[str, Any]:
    classification = int(curve["classification"])
    direction = "right" if str(curve["direction"]).lower() == "derecha" else "left"
    modifiers: list[str] = []
    modifier_text = str(curve.get("modifier") or "").strip().lower()
    if "cierra" in modifier_text:
        modifiers.append("tightens")
    if "abre" in modifier_text:
        modifiers.append("opens")

    entry_classification = int(curve.get("entry_classification", classification))
    exit_classification = int(curve.get("exit_classification", classification))
    severity = classification
    target_severity: int | None = None

    if "tightens" in modifiers and exit_classification < entry_classification:
        severity = entry_classification
        target_severity = exit_classification
    elif "opens" in modifiers and exit_classification > entry_classification:
        severity = entry_classification
        target_severity = exit_classification

    warnings: list[str] = []
    max_braking = curve.get("max_braking")
    if max_braking is not None and float(max_braking) > 0.5:
        warnings.append("brake")

    max_speed = curve.get("max_speed")
    if max_speed is not None and float(max_speed) > 27.0 and classification <= 3:
        warnings.insert(0, "caution")

    structured: dict[str, Any] = {
        "kind": "curve",
        "direction": direction,
        "severity": severity,
        "length": "long" if float(curve["length"]) > 40 else "standard",
        "modifiers": modifiers,
        "warnings": warnings,
    }
    if target_severity is not None:
        structured["target_severity"] = target_severity

    min_gear = curve.get("min_gear")
    if min_gear is not None:
        structured["gear"] = int(min_gear)
    return structured


def _event_structure(text: str) -> dict[str, Any]:
    normalized = text.strip().lower()
    if normalized == "rasante":
        return {"kind": "crest"}
    if normalized == "salto":
        return {"kind": "jump"}
    return {"kind": "custom", "label": text}


def render_pacenote(structured: dict[str, Any]) -> str:
    """Render canonical Spanish display text from structured pacenote data."""
    kind = structured.get("kind")
    if kind == "distance":
        return str(int(round(float(structured["meters"]))))
    if kind == "crest":
        return "Rasante"
    if kind == "jump":
        return "Salto"
    if kind == "custom":
        return str(structured.get("label", ""))

    if kind != "curve":
        return ""

    warnings = set(structured.get("warnings") or [])
    prefix_parts: list[str] = []
    if "caution" in warnings:
        prefix_parts.append("Ojo")
    if "brake" in warnings:
        prefix_parts.append("Frena")

    severity = int(structured["severity"])
    direction = "Derecha" if structured["direction"] == "right" else "Izquierda"
    if severity == 1:
        body = f"Horquilla {direction.lower()}"
    else:
        body = f"{direction} {severity}"

    if structured.get("length") == "long":
        body += " larga"

    target_severity = structured.get("target_severity")
    modifiers = set(structured.get("modifiers") or [])
    if "tightens" in modifiers:
        body += " se cierra"
        if target_severity is not None:
            body += f" a {int(target_severity)}"
    if "opens" in modifiers:
        body += " se abre"
        if target_severity is not None:
            body += f" a {int(target_severity)}"

    gear = structured.get("gear")
    if gear is not None:
        body += f" en {int(gear)}ª"

    return " ".join(prefix_parts + [body])


def generate_pacenotes(
    classified_curves: list[dict],
    extra_events: Iterable[dict] | None = None,
) -> list[dict]:
    events: list[dict] = []
    curve_ends: dict[int, float] = {}

    for index, curve in enumerate(classified_curves):
        position = float(curve["start_distance"])
        curve_ends[index] = float(curve["end_distance"])
        structured = _curve_structure(curve)
        events.append(
            {
                "type": "note",
                "text": render_pacenote(structured),
                "curve_index": index,
                "distance": round(position, 2),
                "structured": structured,
            }
        )

    for event in extra_events or []:
        if "distance" not in event:
            continue
        text = str(event["text"])
        structured = _event_structure(text)
        events.append(
            {
                "type": "note",
                "text": render_pacenote(structured),
                "curve_index": event.get("curve_index"),
                "distance": round(float(event["distance"]), 2),
                "structured": structured,
            }
        )

    events.sort(key=lambda event: (event["distance"], event["curve_index"] is None))

    notes: list[dict] = []
    previous_end = 0.0
    for event in events:
        gap = max(0.0, float(event["distance"]) - previous_end)
        if gap > 10:
            structured_distance = {"kind": "distance", "meters": round(gap)}
            notes.append(
                {
                    "type": "distance",
                    "text": render_pacenote(structured_distance),
                    "curve_index": None,
                    "distance": round(float(event["distance"]), 2),
                    "structured": structured_distance,
                }
            )
        notes.append(event)

        curve_index = event.get("curve_index")
        if curve_index is not None and curve_index in curve_ends:
            previous_end = max(previous_end, curve_ends[curve_index])
        else:
            previous_end = max(previous_end, float(event["distance"]))

    return notes
