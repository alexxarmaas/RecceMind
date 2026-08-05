import requests
from typing import Optional, Dict, Any

class MapsService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def get_route(self, origin: str, destination: str) -> Optional[Dict[Any, Any]]:
        """
        Gets route from Google Routes API.
        """
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.polyline,routes.distanceMeters,routes.duration"
        }
        
        payload = {
            "origin": {
                "address": origin
            },
            "destination": {
                "address": destination
            },
            "travelMode": "DRIVE"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
