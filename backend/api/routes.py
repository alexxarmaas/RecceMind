from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from secrets import compare_digest
from typing import Annotated

import polyline
import speech_recognition as sr
from defusedxml import ElementTree as ET
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import TypeAdapter, ValidationError
from pydub import AudioSegment
from sqlalchemy.orm import Session

from api.schemas import CoordsRequest, FeedbackRequest, GpxRequest, PolylineRequest, RouteRequest
from config import settings
from database import models
from database.database import SessionLocal
from geometry import (
    analyze_polyline,
    calculate_speed_profile,
    classify_curves,
    extract_crests,
    generate_pacenotes,
    parse_telemetry_csv,
)
from geometry.classification_engine import train_model
from services import MapsService, MapsServiceError

logger = logging.getLogger(__name__)
_threshold_adapter = TypeAdapter(dict[int, float])


def require_service_token(
    x_reccemind_token: Annotated[str | None, Header(alias="X-RecceMind-Token")] = None,
) -> None:
    expected_token = settings.service_token
    if not expected_token:
        return
    if not x_reccemind_token or not compare_digest(x_reccemind_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid RecceMind service token",
        )


router = APIRouter(
    prefix="/api",
    tags=["geometry"],
    dependencies=[Depends(require_service_token)],
)


def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


async def _read_limited(upload: UploadFile) -> bytes:
    content = await upload.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte upload limit",
        )
    return content


def _parse_form_thresholds(thresholds: str | None, label: str) -> dict[int, float] | None:
    if not thresholds:
        return None
    try:
        return _threshold_adapter.validate_python(json.loads(thresholds))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {label} thresholds") from exc


def _analyze_encoded_polyline(
    encoded_polyline: str,
    thresholds: dict[int, float] | None,
    driver_id: str,
    telemetry: list[dict] | None = None,
    extra_events: list[dict] | None = None,
) -> dict:
    try:
        points = polyline.decode(encoded_polyline)
    except (IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid encoded polyline") from exc

    curves = analyze_polyline(encoded_polyline, telemetry=telemetry)
    classified_curves = classify_curves(curves, thresholds, driver_id)
    pacenotes = generate_pacenotes(classified_curves, extra_events)
    return {
        "polyline": encoded_polyline,
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": calculate_speed_profile(points),
    }


def _parse_kml_coordinate_text(text: str | None) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if not text:
        return points
    for raw_coordinate in text.replace("\n", " ").replace("\t", " ").split():
        parts = raw_coordinate.split(",")
        if len(parts) < 2:
            continue
        try:
            longitude = float(parts[0])
            latitude = float(parts[1])
        except ValueError:
            continue
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            points.append((latitude, longitude))
    return points


def _extract_kmz_tracks(content: bytes) -> list[dict]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid KMZ archive") from exc

    max_uncompressed = settings.max_upload_bytes * 4
    kml_members = [member for member in archive.infolist() if member.filename.lower().endswith(".kml")]
    if not kml_members:
        raise HTTPException(status_code=400, detail="KMZ does not contain a KML document")
    if sum(member.file_size for member in kml_members) > max_uncompressed:
        raise HTTPException(status_code=413, detail="KMZ expands beyond the allowed size")

    tracks: list[dict] = []
    for member in kml_members:
        try:
            root = ET.fromstring(archive.read(member))
        except ET.ParseError:
            continue

        for placemark in root.iter():
            if not str(placemark.tag).endswith("Placemark"):
                continue
            name = ""
            for child in placemark:
                if str(child.tag).endswith("name") and child.text:
                    name = child.text.strip()
                    break
            for line_string in placemark.iter():
                if not str(line_string.tag).endswith("LineString"):
                    continue
                coordinate_text = None
                for node in line_string.iter():
                    if str(node.tag).endswith("coordinates"):
                        coordinate_text = node.text
                        break
                points = _parse_kml_coordinate_text(coordinate_text)
                if len(points) >= 3:
                    tracks.append({"name": name or Path(member.filename).stem, "points": points})

    if not tracks:
        raise HTTPException(status_code=400, detail="KMZ does not contain a valid LineString stage")
    return tracks


def _kmz_track_summaries(tracks: list[dict]) -> list[dict]:
    return [
        {
            "index": index,
            "name": track["name"],
            "pointCount": len(track["points"]),
        }
        for index, track in enumerate(tracks)
    ]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze-route")
def analyze_route(request: RouteRequest):
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail="Google Maps API key is not configured")

    maps_service = MapsService(
        api_key=settings.google_maps_api_key,
        timeout_seconds=settings.external_request_timeout_seconds,
    )
    try:
        route_data = maps_service.get_route(
            request.origin,
            request.destination,
            request.origin_coords,
            request.destination_coords,
        )
    except MapsServiceError as exc:
        logger.warning("Google Routes failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    route = route_data["routes"][0]
    encoded_polyline = route["polyline"]["encodedPolyline"]
    result = _analyze_encoded_polyline(
        encoded_polyline,
        request.thresholds,
        request.driver_id,
    )
    result.update(
        {
            "distanceMeters": route.get("distanceMeters", 0),
            "duration": route.get("duration", "0s"),
        }
    )
    return result


@router.post("/process-polyline")
def process_polyline(request: PolylineRequest):
    return _analyze_encoded_polyline(request.polyline, request.thresholds, request.driver_id)


@router.post("/process-gpx")
def process_gpx(request: GpxRequest):
    try:
        root = ET.fromstring(request.gpx_content)
    except ET.ParseError as exc:
        raise HTTPException(status_code=400, detail="Invalid GPX XML") from exc

    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    points: list[tuple[float, float]] = []
    elevations: list[float] = []
    for track_point in root.iter(f"{namespace}trkpt"):
        try:
            latitude = float(track_point.attrib["lat"])
            longitude = float(track_point.attrib["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            continue
        elevation_element = track_point.find(f"{namespace}ele")
        try:
            elevation = float(elevation_element.text) if elevation_element is not None else 0.0
        except (TypeError, ValueError):
            elevation = 0.0
        points.append((latitude, longitude))
        elevations.append(elevation)

    if len(points) < 3:
        raise HTTPException(status_code=400, detail="GPX must contain at least three valid track points")

    encoded_polyline = polyline.encode(points)
    crests = extract_crests(points, elevations)
    result = _analyze_encoded_polyline(
        encoded_polyline,
        request.thresholds,
        request.driver_id,
        extra_events=crests,
    )
    result.update({"distanceMeters": 0, "duration": "0s"})
    return result


@router.post("/inspect-kmz")
async def inspect_kmz(file: Annotated[UploadFile, File(...)]):
    content = await _read_limited(file)
    tracks = _extract_kmz_tracks(content)
    default_index = max(range(len(tracks)), key=lambda index: len(tracks[index]["points"]))
    return {
        "tracks": _kmz_track_summaries(tracks),
        "defaultTrackIndex": default_index,
    }


@router.post("/process-kmz")
async def process_kmz(
    file: Annotated[UploadFile, File(...)],
    thresholds: Annotated[str | None, Form()] = None,
    driver_id: Annotated[str, Form(min_length=1, max_length=100)] = "default",
    track_index: Annotated[int | None, Form(ge=0)] = None,
):
    parsed_thresholds = _parse_form_thresholds(thresholds, "KMZ")
    content = await _read_limited(file)
    tracks = _extract_kmz_tracks(content)

    if track_index is None:
        selected_index = max(range(len(tracks)), key=lambda index: len(tracks[index]["points"]))
    elif track_index >= len(tracks):
        raise HTTPException(status_code=422, detail="KMZ track index is outside the available range")
    else:
        selected_index = track_index

    selected = tracks[selected_index]
    result = _analyze_encoded_polyline(
        polyline.encode(selected["points"]),
        parsed_thresholds,
        driver_id,
    )
    result.update(
        {
            "distanceMeters": 0,
            "duration": "0s",
            "sourceName": selected["name"],
            "kmzTrackCount": len(tracks),
            "selectedTrackIndex": selected_index,
        }
    )
    return result


@router.post("/process-telemetry")
async def process_telemetry(
    file: Annotated[UploadFile, File(...)],
    thresholds: Annotated[str | None, Form()] = None,
    driver_id: Annotated[str, Form(min_length=1, max_length=100)] = "default",
):
    parsed_thresholds = _parse_form_thresholds(thresholds, "telemetry")
    content = await _read_limited(file)
    try:
        content_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Telemetry CSV must use UTF-8 encoding") from exc

    points, telemetry = parse_telemetry_csv(content_text)
    if len(points) < 3:
        raise HTTPException(status_code=400, detail="Telemetry must contain at least three valid coordinates")

    encoded_polyline = polyline.encode(points)
    result = _analyze_encoded_polyline(
        encoded_polyline,
        parsed_thresholds,
        driver_id,
        telemetry=telemetry,
    )
    result.update({"distanceMeters": 0, "duration": "0s"})
    return result


@router.post("/process-coords")
def process_coords(request: CoordsRequest):
    points = [(coordinate[0], coordinate[1]) for coordinate in request.coordinates]
    return _analyze_encoded_polyline(
        polyline.encode(points),
        request.thresholds,
        request.driver_id,
    )


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest, database: Session = Depends(get_db)):
    feedback_entry = models.PacenoteFeedback(
        radius=request.radius,
        heading_change=request.heading_change,
        length=request.length,
        original_classification=request.original_classification,
        user_classification=request.user_classification,
        driver_id=request.driver_id,
    )
    database.add(feedback_entry)
    database.commit()

    feedbacks = (
        database.query(models.PacenoteFeedback)
        .filter_by(driver_id=request.driver_id)
        .order_by(models.PacenoteFeedback.timestamp.asc())
        .all()
    )
    trained = train_model(feedbacks, request.driver_id)
    return {
        "message": "Feedback saved",
        "ml_trained": trained,
        "total_feedbacks": len(feedbacks),
    }


@router.post("/speech-to-text")
async def speech_to_text(audio: Annotated[UploadFile, File(...)]):
    content = await _read_limited(audio)
    source_suffix = Path(audio.filename or "audio.m4a").suffix.lower() or ".m4a"
    source_path = ""
    wav_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=source_suffix) as source_file:
            source_file.write(content)
            source_path = source_file.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
            wav_path = wav_file.name

        AudioSegment.from_file(source_path).export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        return {"text": recognizer.recognize_google(audio_data, language="es-ES")}
    except sr.UnknownValueError:
        return {"text": "", "error": "No se entendió el audio"}
    except sr.RequestError as exc:
        logger.warning("Speech recognition service failed: %s", exc)
        raise HTTPException(status_code=502, detail="Speech recognition service failed") from exc
    except Exception as exc:
        logger.exception("Audio processing failed")
        raise HTTPException(
            status_code=422,
            detail="Audio could not be decoded. Ensure FFmpeg is installed on the backend.",
        ) from exc
    finally:
        for temporary_path in (source_path, wav_path):
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)
