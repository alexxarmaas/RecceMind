import numpy as np
import polyline
from typing import List, Dict, Any

class Curve:
    def __init__(self, start_idx: int, end_idx: int, start_distance: float, end_distance: float, 
                 length: float, radius: float, heading_change: float, direction: str, modifier: str = "",
                 max_speed: float = None, min_gear: int = None, max_braking: float = None):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.start_distance = start_distance
        self.end_distance = end_distance
        self.length = length
        self.radius = radius
        self.heading_change = heading_change
        self.direction = direction
        self.modifier = modifier
        self.max_speed = max_speed
        self.min_gear = min_gear
        self.max_braking = max_braking

    def to_dict(self):
        d = {
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "start_distance": round(self.start_distance, 2),
            "end_distance": round(self.end_distance, 2),
            "length": round(self.length, 2),
            "radius": round(self.radius, 2),
            "heading_change": round(self.heading_change, 2),
            "direction": self.direction,
            "modifier": self.modifier
        }
        if self.max_speed is not None:
            d["max_speed"] = round(self.max_speed, 2)
        if self.min_gear is not None:
            d["min_gear"] = self.min_gear
        if self.max_braking is not None:
            d["max_braking"] = round(self.max_braking, 2)
        return d

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters."""
    R = 6371000 # Earth radius in meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def initial_bearing(lat1, lon1, lat2, lon2):
    """Calculate initial bearing between two coordinates in degrees."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - (np.sin(lat1) * np.cos(lat2) * np.cos(dlon))
    initial_bearing = np.arctan2(x, y)
    return (np.degrees(initial_bearing) + 360) % 360

def calculate_curvature(p1, p2, p3):
    """Approximate radius of curvature given 3 points using Menger curvature or circumcircle."""
    # Convert lat/lon to local cartesian coordinates roughly
    # 1 deg lat = 111320m, 1 deg lon = 111320m * cos(lat)
    lat_mid = np.radians((p1[0] + p2[0] + p3[0])/3)
    
    def to_cartesian(p):
        return np.array([(p[1] - p2[1]) * 111320 * np.cos(lat_mid), (p[0] - p2[0]) * 111320])

    c1 = to_cartesian(p1)
    c2 = to_cartesian(p2) # Origin
    c3 = to_cartesian(p3)

    # Triangle sides
    a = np.linalg.norm(c1 - c2)
    b = np.linalg.norm(c2 - c3)
    c = np.linalg.norm(c3 - c1)

    # Area using Heron's formula
    s = (a + b + c) / 2
    area_sq = s * (s - a) * (s - b) * (s - c)
    if area_sq <= 0:
        return float('inf')
    area = np.sqrt(area_sq)
    
    if area == 0:
        return float('inf')

    radius = (a * b * c) / (4 * area)
    return radius

def smooth_points(points: List[tuple], window: int = 3) -> List[tuple]:
    """Applies a simple moving average filter to reduce GPS noise."""
    if len(points) < window:
        return points
    
    smoothed = []
    for i in range(len(points)):
        start = max(0, i - window // 2)
        end = min(len(points), i + window // 2 + 1)
        slice_pts = points[start:end]
        avg_lat = sum(p[0] for p in slice_pts) / len(slice_pts)
        avg_lon = sum(p[1] for p in slice_pts) / len(slice_pts)
        smoothed.append((avg_lat, avg_lon))
    return smoothed

def analyze_polyline(encoded_polyline: str, telemetry: List[dict] = None) -> List[Curve]:
    raw_points = polyline.decode(encoded_polyline)
    if len(raw_points) < 3:
        return []
        
    points = smooth_points(raw_points, window=3)
    
    # Calculate distances and bearings
    distances = [0.0]
    bearings = []
    
    for i in range(len(points) - 1):
        dist = haversine_distance(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
        distances.append(distances[-1] + dist)
        bearings.append(initial_bearing(points[i][0], points[i][1], points[i+1][0], points[i+1][1]))
        
    curves = []
    current_curve = None
    
    # Simple curve detection logic (placeholder for more advanced segmentation)
    for i in range(1, len(points) - 1):
        heading_change = bearings[i] - bearings[i-1]
        
        # Normalize heading change to [-180, 180]
        heading_change = (heading_change + 180) % 360 - 180
        
        radius = calculate_curvature(points[i-1], points[i], points[i+1])
        
        # If radius is relatively small (e.g. < 200m), we are in a curve
        if radius < 200 and abs(heading_change) > 5:
            direction = "Derecha" if heading_change > 0 else "Izquierda"
            
            if current_curve is None or current_curve['direction'] != direction:
                if current_curve is not None:
                    curves.append(current_curve)
                
                current_curve = {
                    "start_idx": i - 1,
                    "end_idx": i + 1,
                    "start_distance": distances[i-1],
                    "end_distance": distances[i+1],
                    "radius": radius,
                    "heading_change": heading_change,
                    "direction": direction,
                    "radii": [radius]
                }
            else:
                current_curve['end_idx'] = i + 1
                current_curve['end_distance'] = distances[i+1]
                current_curve['heading_change'] += heading_change
                current_curve['radius'] = min(current_curve['radius'], radius)
                current_curve['radii'].append(radius)
        else:
            if current_curve is not None:
                curves.append(current_curve)
                current_curve = None
                
    if current_curve is not None:
        curves.append(current_curve)
        
    # Convert to Curve objects
    curve_objects = []
    for c in curves:
        length = c['end_distance'] - c['start_distance']
        if length > 0:
            radii = c['radii']
            modifier = ""
            if len(radii) >= 4:
                half = len(radii) // 2
                r_start = sum(radii[:half]) / half
                r_end = sum(radii[half:]) / (len(radii) - half)
                if r_start > 1.5 * r_end:
                    modifier = " se cierra"
                elif r_end > 1.5 * r_start:
                    modifier = " se abre"
                    
        # Assign telemetry if provided
        max_speed = None
        min_gear = None
        max_braking = None
        
        if telemetry:
            # Telemetry is a list of dicts mapped to points
            # Analyze telemetry for this curve and its entry zone (e.g. 5 points before)
            start_t = max(0, c['start_idx'] - 5)
            end_t = min(len(telemetry), c['end_idx'] + 1)
            curve_telemetry = telemetry[start_t:end_t]
            
            speeds = [t.get('speed') for t in curve_telemetry if t.get('speed') is not None]
            if speeds:
                max_speed = max(speeds)
                
            gears = [t.get('gear') for t in curve_telemetry if t.get('gear') is not None]
            if gears:
                min_gear = min(gears)
                
            # Braking is usually higher values if percentage, or boolean 1/0
            brakes = [t.get('brake') for t in curve_telemetry if t.get('brake') is not None]
            if brakes:
                max_braking = max(brakes)

        curve_objects.append(Curve(
            start_idx=c['start_idx'],
            end_idx=c['end_idx'],
            start_distance=c['start_distance'],
            end_distance=c['end_distance'],
            length=length,
            radius=c['radius'],
            heading_change=c['heading_change'],
            direction=c['direction'],
            modifier=modifier,
            max_speed=max_speed,
            min_gear=min_gear,
            max_braking=max_braking
        ))
            
    return curve_objects

import csv
import io

def parse_telemetry_csv(content: str) -> tuple[List[tuple], List[dict]]:
    """
    Parses a CSV string containing telemetry data.
    Expected columns: lat, lon, speed (optional), brake (optional), gear (optional)
    Returns: points (List[(lat, lon)]), telemetry (List[dict])
    """
    points = []
    telemetry = []
    
    reader = csv.DictReader(io.StringIO(content.strip()))
    for row in reader:
        # Standardize keys by lowercasing and stripping
        clean_row = {k.strip().lower(): v for k, v in row.items() if k}
        
        try:
            lat = float(clean_row['lat'])
            lon = float(clean_row['lon'])
        except (KeyError, ValueError):
            continue # Skip invalid rows
            
        points.append((lat, lon))
        
        t_data = {}
        if 'speed' in clean_row:
            try: t_data['speed'] = float(clean_row['speed'])
            except ValueError: pass
        if 'brake' in clean_row:
            try: t_data['brake'] = float(clean_row['brake'])
            except ValueError: pass
        if 'gear' in clean_row:
            try: t_data['gear'] = int(float(clean_row['gear']))
            except ValueError: pass
            
        telemetry.append(t_data)
        
    return points, telemetry

def extract_crests(points: List[tuple], elevations: List[float]) -> List[dict]:
    """Detect crests (rasantes) from elevation data."""
    if not elevations or len(elevations) != len(points):
        return []
        
    distances = [0.0]
    for i in range(len(points) - 1):
        dist = haversine_distance(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
        distances.append(distances[-1] + dist)
        
    crests = []
    # simple local maxima detection
    for i in range(5, len(elevations) - 5):
        # check if it's a local maximum within a window
        window = elevations[i-5:i+6]
        if elevations[i] == max(window):
            # calculate prominence (height difference from surrounding local minima)
            left_min = min(elevations[i-5:i])
            right_min = min(elevations[i+1:i+6])
            
            prominence = min(elevations[i] - left_min, elevations[i] - right_min)
            
            if prominence > 2.0: # threshold for a "Rasante"
                crests.append({
                    "type": "note",
                    "text": "Rasante" if prominence < 5.0 else "Salto",
                    "distance": distances[i],
                    "curve_index": None
                })
                
    # remove crests that are too close to each other
    filtered_crests = []
    last_dist = -100
    for crest in crests:
        if crest["distance"] - last_dist > 50:
            filtered_crests.append(crest)
            last_dist = crest["distance"]
            
    return filtered_crests

def calculate_speed_profile(points: List[tuple]) -> List[float]:
    """Calculate a theoretical speed profile for the points (m/s)."""
    speeds = []
    # Very crude approximation
    for i in range(len(points)):
        if i == 0 or i == len(points) - 1:
            speeds.append(20.0)
            continue
            
        r = calculate_curvature(points[i-1], points[i], points[i+1])
        if r == float('inf'):
            v = 40.0 # max speed ~ 144 km/h
        else:
            # v = sqrt(10 * r), capped at 40
            v = min(40.0, np.sqrt(10 * r))
            
        speeds.append(v)
        
    # Smooth the speeds (cars can't accelerate/decelerate instantly)
    smoothed = speeds.copy()
    for _ in range(3):
        for i in range(1, len(smoothed) - 1):
            smoothed[i] = (smoothed[i-1] + smoothed[i] + smoothed[i+1]) / 3
            
    return smoothed
