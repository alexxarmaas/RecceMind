from typing import List

def generate_pacenotes(classified_curves: List[dict]) -> List[dict]:
    """
    Transforms a list of classified curves into a text draft of pacenotes.
    Example output format:
    100
    Derecha 4
    60
    Izquierda 3 larga
    """
    notes = []
    
    for i, curve in enumerate(classified_curves):
        # Calculate distance to next curve or from start
        if i == 0:
            distance = curve["start_distance"]
        else:
            prev_curve = classified_curves[i-1]
            distance = curve["start_distance"] - prev_curve["end_distance"]
            
        distance = round(distance)
        if distance > 10: # Only print distances if they are meaningful
            notes.append({"type": "distance", "text": str(distance), "curve_index": None})
            
        # Create the note for the curve
        direction = curve["direction"]
        classification = curve["classification"]
        
        # Add modifiers based on telemetry if present
        prefix = ""
        suffix = ""
        
        if "max_braking" in curve and curve["max_braking"] is not None:
            if curve["max_braking"] > 0.5: # 50% brake threshold
                prefix = "Frena "
                
        if "max_speed" in curve and curve["max_speed"] is not None:
            # simple check: if speed > 100kmh (27m/s) entering a 1,2 or 3 corner
            if curve["max_speed"] > 27.0 and classification <= 3:
                prefix = "Ojo " + prefix
                
        if "min_gear" in curve and curve["min_gear"] is not None:
            suffix = f" en {curve['min_gear']}ª"
            
        note_str = f"{prefix}{direction} {classification}"
        
        if classification == 1:
            note_str = f"{prefix}Horquilla {direction.lower()}"
            
        if curve["length"] > 40:
            note_str += " larga"
            
        # Add se abre / se cierra
        if "modifier" in curve and curve["modifier"]:
            note_str += curve["modifier"]
            
        note_str += suffix
            
        notes.append({"type": "note", "text": note_str, "curve_index": i})
        
    return notes
