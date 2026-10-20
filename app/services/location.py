import httpx
import logging
from typing import Optional, List, Dict, Any
from app.models import LocationData

logger = logging.getLogger(__name__)

# Sample Safe Havens (Police Stations, Hospitals) for demo & map visualization
KNOWN_SAFE_HAVENS = [
    {
        "name": "Central Police Station & Cyber Cell",
        "type": "POLICE",
        "phone": "112 / +91-80-22942222",
        "lat_offset": 0.0035,
        "lng_offset": 0.0028,
        "address": "MG Road / Police HQ"
    },
    {
        "name": "City Care Multi-Speciality Hospital (24/7 Trauma)",
        "type": "HOSPITAL",
        "phone": "108 / +91-80-25553333",
        "lat_offset": -0.0042,
        "lng_offset": 0.0031,
        "address": "Hospital Road, Emergency Bay"
    },
    {
        "name": "Metro Transit Security Outpost",
        "type": "TRANSIT_SECURITY",
        "phone": "+91-80-22941111",
        "lat_offset": 0.0018,
        "lng_offset": -0.0040,
        "address": "Station Concourse, Gate 2"
    },
    {
        "name": "Apollo 24/7 Emergency Pharmacy & Clinic",
        "type": "PHARMACY",
        "phone": "1860-500-0101",
        "lat_offset": -0.0025,
        "lng_offset": -0.0022,
        "address": "Main Commercial Street"
    }
]

async def reverse_geocode(lat: float, lng: float) -> str:
    """Reverse geocode latitude and longitude using OpenStreetMap Nominatim with fallback."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
        headers = {"User-Agent": "ShaktiGuard-Emergency-Response-Agent/1.0"}
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                display_name = data.get("display_name")
                if display_name:
                    # Shorten to first 3 segments
                    parts = display_name.split(",")
                    short_addr = ", ".join(parts[:3]).strip()
                    return short_addr
    except Exception as e:
        logger.debug(f"Reverse geocode lookup timeout/error: {e}")
        
    return f"GPS Location (Lat: {round(lat, 4)}, Lng: {round(lng, 4)})"

def get_nearby_safe_havens(base_lat: float, base_lng: float) -> List[Dict[str, Any]]:
    """Returns calculated safe havens relative to the user's current GPS position."""
    havens = []
    for h in KNOWN_SAFE_HAVENS:
        haven_lat = round(base_lat + h["lat_offset"], 6)
        haven_lng = round(base_lng + h["lng_offset"], 6)
        havens.append({
            "name": h["name"],
            "type": h["type"],
            "phone": h["phone"],
            "latitude": haven_lat,
            "longitude": haven_lng,
            "address": h["address"],
            "estimated_distance_meters": int(abs(h["lat_offset"] * 111000) + abs(h["lng_offset"] * 111000))
        })
    havens.sort(key=lambda x: x["estimated_distance_meters"])
    return havens
