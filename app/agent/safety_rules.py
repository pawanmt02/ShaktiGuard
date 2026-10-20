from typing import List, Dict, Any, Tuple
from app.models import UrgencyLevel, IncidentType, LocationData

SAFETY_CHECKLISTS: Dict[IncidentType, List[str]] = {
    IncidentType.STALKING_HARASSMENT: [
        "Head immediately toward brightly lit areas, open stores, or groups of people.",
        "Do not make direct eye contact or confront the individual; maintain brisk, confident pace.",
        "Keep your phone accessible in your hand with screen brightness dimmed.",
        "If pursued closely, enter the nearest commercial establishment (store, restaurant, hotel) and alert the staff.",
        "Do not head toward isolated alleyways, parking lots, or your private residence entrance while being followed."
    ],
    IncidentType.MEDICAL_EMERGENCY: [
        "Sit or lie down in a safe, flat position immediately to prevent injury from falling.",
        "Loosen tight clothing around your neck, chest, and waist to ease breathing.",
        "If experiencing chest pressure or severe pain, rest quietly and avoid sudden physical exertion.",
        "Keep your phone near you on speakerphone mode.",
        "Unlock your front door if indoors so arriving emergency responders can enter without delay."
    ],
    IncidentType.SUSPICIOUS_ROUTE_TRANSIT: [
        "Quietly share your live trip tracking link with your emergency contacts.",
        "Firmly ask the driver: 'You seem to have taken a wrong turn, please return to the main route now.'",
        "Keep your hand on the door handle lock and roll down the window slightly to attract public attention if needed.",
        "Make a fake or real phone call speaking loudly: 'Yes, I am sharing my live GPS with you right now, I will be there in 5 minutes.'",
        "If vehicle slows down in an unsafe isolated spot, prepare to exit immediately toward public spaces."
    ],
    IncidentType.ACCIDENT_COLLISION: [
        "Check yourself and immediate companions for bleeding, broken limbs, or spinal pain.",
        "If you are on an active roadway and can safely move, get off the road to avoid secondary collisions.",
        "Do not remove helmets or sharply move anyone with potential neck or spine trauma unless facing fire hazard.",
        "Turn on phone flashlight or vehicle hazard lights to signal other vehicles.",
        "Apply firm, direct pressure with clean cloth over any heavily bleeding wounds."
    ],
    IncidentType.PHYSICAL_ASSAULT: [
        "Scream loudly: 'FIRE!' or 'HELP!' to draw maximum bystander attention.",
        "Target vulnerable points (eyes, throat, groin) only if physical struggle is unavoidable to create escape window.",
        "Break free and run toward illumination, traffic, or crowded buildings immediately.",
        "Discard heavy bags or personal belongings if they slow down your escape.",
        "Activate ShaktiGuard panic siren if in an area where noise will deter the assailant."
    ],
    IncidentType.FIRE_HAZARD: [
        "Stay low to the floor beneath the smoke layer while moving toward exits.",
        "Feel door handles with the back of your hand before opening; if hot, do not open.",
        "Never use elevators during a fire; use marked stairwells only.",
        "Cover your mouth and nose with a damp cloth or your clothing.",
        "Once outside, stay out; do not re-enter the building under any circumstances."
    ],
    IncidentType.GENERAL_DISTRESS: [
        "Remain calm, breathe steadily, and take in your immediate surroundings.",
        "Identify at least two potential exit routes or safe shelters nearby.",
        "Keep ShaktiGuard open; your location and status are broadcasting to your trusted contacts.",
        "Stay in well-lit, visible positions and avoid isolated areas.",
        "Prepare to speak to approaching responders or phone dispatchers."
    ]
}

def analyze_heuristic_distress(
    raw_input: str,
    location: LocationData = None,
    is_covert: bool = False
) -> Tuple[UrgencyLevel, IncidentType, str, Dict[str, Any], str, List[str]]:
    text = (raw_input or "").lower().strip()
    
    # Defaults
    urgency = UrgencyLevel.HIGH if is_covert else UrgencyLevel.MEDIUM
    incident_type = IncidentType.GENERAL_DISTRESS
    extracted_entities: Dict[str, Any] = {
        "location_named": location.address if location else "Live GPS",
        "threat_factors": []
    }
    
    # Keyword & pattern matching
    stalking_keywords = ["follow", "stalk", "behind me", "creepy", "watching me", "shadow", "tailing", "chasing", "unsafe", "bus stop"]
    medical_keywords = ["chest pain", "heart", "breath", "dizzy", "faint", "bleeding", "unconscious", "collapse", "seizure", "stroke", "allergic"]
    transit_keywords = ["cab", "taxi", "uber", "driver", "route", "wrong turn", "bypass", "auto", "detour", "refuses to stop"]
    accident_keywords = ["accident", "crash", "collision", "hit-and-run", "fracture", "run over", "injured on road"]
    assault_keywords = ["attack", "hitting", "assault", "grab", "threat", "weapon", "knife", "gun", "cornered", "harass", "beating"]
    fire_keywords = ["fire", "smoke", "burning", "trapped", "explosion", "blaze"]
    
    if any(k in text for k in assault_keywords):
        urgency = UrgencyLevel.CRITICAL
        incident_type = IncidentType.PHYSICAL_ASSAULT
        extracted_entities["threat_factors"].append("Physical assault or violence risk")
    elif any(k in text for k in fire_keywords):
        urgency = UrgencyLevel.CRITICAL
        incident_type = IncidentType.FIRE_HAZARD
        extracted_entities["threat_factors"].append("Active fire or structural threat")
    elif any(k in text for k in medical_keywords):
        urgency = UrgencyLevel.CRITICAL if ("chest" in text or "unconscious" in text or "faint" in text) else UrgencyLevel.HIGH
        incident_type = IncidentType.MEDICAL_EMERGENCY
        extracted_entities["threat_factors"].append("Acute physiological emergency")
    elif any(k in text for k in transit_keywords):
        urgency = UrgencyLevel.HIGH
        incident_type = IncidentType.SUSPICIOUS_ROUTE_TRANSIT
        extracted_entities["threat_factors"].append("Uncontrolled transit deviation")
    elif any(k in text for k in accident_keywords):
        urgency = UrgencyLevel.HIGH
        incident_type = IncidentType.ACCIDENT_COLLISION
        extracted_entities["threat_factors"].append("Traffic collision impact")
    elif any(k in text for k in stalking_keywords):
        urgency = UrgencyLevel.HIGH
        incident_type = IncidentType.STALKING_HARASSMENT
        extracted_entities["threat_factors"].append("Potential predatory stalking")
    else:
        if is_covert:
            urgency = UrgencyLevel.HIGH
            extracted_entities["threat_factors"].append("Covert silent distress signal")
        elif not text:
            urgency = UrgencyLevel.HIGH
            extracted_entities["threat_factors"].append("Instant one-tap panic button trigger")
            
    # Extract landmarks if mentioned
    for landmark_cue in ["near", "at", "outside", "in front of", "by", "road", "cross", "metro", "station", "stop"]:
        if landmark_cue in text:
            parts = text.split(landmark_cue)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                extracted_entities["location_named"] = f"{landmark_cue.capitalize()} {parts[1].strip()[:35]}"
                break
                
    summary = f"Emergency situation detected ({incident_type.value.replace('_', ' ').title()}) requiring immediate response."
    if text:
        summary = f"{incident_type.value.replace('_', ' ').title()}: '{raw_input[:100]}...'"
        
    threat_assessment = f"Detected {urgency.value} urgency involving {incident_type.value}. Response protocol initialized."
    guidance = SAFETY_CHECKLISTS.get(incident_type, SAFETY_CHECKLISTS[IncidentType.GENERAL_DISTRESS])
    
    return urgency, incident_type, summary, extracted_entities, threat_assessment, guidance
