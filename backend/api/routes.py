from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import re
import polyline
import xml.etree.ElementTree as ET
import speech_recognition as sr
from sqlalchemy.orm import Session
from fastapi import Depends, UploadFile, File

from geometry import analyze_polyline, classify_curves, generate_pacenotes, extract_crests, calculate_speed_profile, parse_telemetry_csv
from geometry.classification_engine import train_model
from database.database import SessionLocal
from database import models
from services import MapsService

router = APIRouter(prefix="/api", tags=["geometry"])
# Dummy comment to trigger uvicorn reload

class RouteRequest(BaseModel):
    origin: str
    destination: str
    thresholds: Optional[dict] = None
    driver_id: Optional[str] = "default"

class PolylineRequest(BaseModel):
    polyline: str
    thresholds: Optional[dict] = None
    driver_id: Optional[str] = "default"

class GpxRequest(BaseModel):
    gpx_content: str
    thresholds: Optional[dict] = None
    driver_id: Optional[str] = "default"

class CoordsRequest(BaseModel):
    coordinates: List[List[float]]
    thresholds: Optional[dict] = None
    driver_id: Optional[str] = "default"

class FeedbackRequest(BaseModel):
    radius: float
    heading_change: float
    length: float
    original_classification: int
    user_classification: int
    driver_id: Optional[str] = "default"

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/analyze-route")
def analyze_route(request: RouteRequest):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API Key not configured")
        
    maps_service = MapsService(api_key=api_key)
    route_data = maps_service.get_route(request.origin, request.destination)
    
    if not route_data or 'routes' not in route_data or len(route_data['routes']) == 0:
        raise HTTPException(status_code=404, detail="Route not found")
        
    polyline_str = route_data['routes'][0]['polyline']['encodedPolyline']
    
    curves = analyze_polyline(polyline_str)
    classified_curves = classify_curves(curves, request.thresholds, request.driver_id)
    pacenotes = generate_pacenotes(classified_curves)
    points = polyline.decode(polyline_str)
    speed_profile = calculate_speed_profile(points)
    
    return {
        "polyline": polyline_str,
        "distanceMeters": route_data['routes'][0].get('distanceMeters', 0),
        "duration": route_data['routes'][0].get('duration', "0s"),
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": speed_profile
    }

@router.post("/process-polyline")
def process_polyline(request: PolylineRequest):
    # Process the polyline using the geometry engine
    curves = analyze_polyline(request.polyline)
    classified_curves = classify_curves(curves, request.thresholds, request.driver_id)
    pacenotes = generate_pacenotes(classified_curves)
    points = polyline.decode(request.polyline)
    speed_profile = calculate_speed_profile(points)
    
    return {
        "polyline": request.polyline,
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": speed_profile
    }

@router.post("/process-gpx")
def process_gpx(request: GpxRequest):
    points = []
    elevations = []
    
    try:
        root = ET.fromstring(request.gpx_content)
        # Handle namespaces if any by removing them or using wildcard
        # For simplicity, we just find all elements regardless of namespace
        namespace = ''
        if '}' in root.tag:
            namespace = root.tag.split('}')[0] + '}'
            
        for trkpt in root.iter(f'{namespace}trkpt'):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            ele_elem = trkpt.find(f'{namespace}ele')
            
            ele = float(ele_elem.text) if ele_elem is not None else 0.0
            
            points.append((lat, lon))
            elevations.append(ele)
    except Exception as e:
        # Fallback to regex if XML parsing fails
        pattern = re.compile(r'<trkpt\s+lat="([^"]+)"\s+lon="([^"]+)">')
        matches = pattern.findall(request.gpx_content)
        if not matches:
            raise HTTPException(status_code=400, detail="No track points found in GPX")
        points = [(float(lat), float(lon)) for lat, lon in matches]
        elevations = [0.0] * len(points)
        
    if not points:
        raise HTTPException(status_code=400, detail="No track points found in GPX")
        
    encoded_polyline = polyline.encode(points)
    
    curves = analyze_polyline(encoded_polyline)
    classified_curves = classify_curves(curves, request.thresholds, request.driver_id)
    pacenotes = generate_pacenotes(classified_curves)
    
    # Extract crests and merge
    crests = extract_crests(points, elevations)
    if crests:
        # We need to approximate distance of pacenotes from start to sort them.
        # generate_pacenotes uses distances between curves, let's keep it simple
        # and just append them for now. A proper sort requires absolute distance.
        pacenotes.extend(crests)
    
    speed_profile = calculate_speed_profile(points)
    
    return {
        "polyline": encoded_polyline,
        "distanceMeters": 0,
        "duration": "0s",
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": speed_profile
    }

@router.post("/process-telemetry")
async def process_telemetry(file: UploadFile = File(...), thresholds: Optional[str] = None, driver_id: Optional[str] = "default"):
    import json
    parsed_thresholds = None
    if thresholds:
        try:
            parsed_thresholds = json.loads(thresholds)
        except json.JSONDecodeError:
            pass

    content = await file.read()
    content_str = content.decode('utf-8')
    
    points, telemetry = parse_telemetry_csv(content_str)
    if not points:
        raise HTTPException(status_code=400, detail="No valid coordinates found in telemetry file")
        
    encoded_polyline = polyline.encode(points)
    
    curves = analyze_polyline(encoded_polyline, telemetry=telemetry)
    classified_curves = classify_curves(curves, parsed_thresholds, driver_id)
    pacenotes = generate_pacenotes(classified_curves)
    
    # We could calculate a theoretical speed profile, or return the actual speeds from telemetry.
    # For now, let's just return theoretical for consistency, or a blend.
    speed_profile = calculate_speed_profile(points)
    
    return {
        "polyline": encoded_polyline,
        "distanceMeters": 0,
        "duration": "0s",
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": speed_profile
    }

@router.post("/process-coords")
def process_coords(request: CoordsRequest):
    encoded_polyline = polyline.encode(request.coordinates)
    
    curves = analyze_polyline(encoded_polyline)
    classified_curves = classify_curves(curves, request.thresholds, request.driver_id)
    pacenotes = generate_pacenotes(classified_curves)
    
    points = [(c[0], c[1]) for c in request.coordinates]
    speed_profile = calculate_speed_profile(points)
    
    return {
        "polyline": encoded_polyline,
        "curves": classified_curves,
        "pacenotes": pacenotes,
        "speed_profile": speed_profile
    }

@router.post("/feedback")
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    feedback_entry = models.PacenoteFeedback(
        radius=request.radius,
        heading_change=request.heading_change,
        length=request.length,
        original_classification=request.original_classification,
        user_classification=request.user_classification,
        driver_id=request.driver_id
    )
    db.add(feedback_entry)
    db.commit()
    
    # Re-train model with all feedbacks for this driver
    feedbacks = db.query(models.PacenoteFeedback).filter_by(driver_id=request.driver_id).all()
    success = train_model(feedbacks, request.driver_id)
    
    return {"message": "Feedback saved", "ml_trained": success, "total_feedbacks": len(feedbacks)}

@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    recognizer = sr.Recognizer()
    
    # Save uploaded file temporarily
    temp_audio_path = f"temp_{audio.filename}"
    try:
        with open(temp_audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)
            
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="es-ES")
            return {"text": text}
    except sr.UnknownValueError:
        return {"text": "", "error": "No se entendió el audio"}
    except sr.RequestError as e:
        return {"text": "", "error": f"Error del servicio: {e}"}
    except Exception as e:
        return {"text": "", "error": f"Error procesando audio: {e}"}
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
