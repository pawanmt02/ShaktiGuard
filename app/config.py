import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseModel):
    app_name: str = "ShaktiGuard: AI Emergency Response Assistant"
    version: str = "1.0.0"
    debug: bool = True
    
    # Database
    db_path: str = str(DATA_DIR / "shaktiguard.db")
    
    # AI Engine
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = "gemini-2.5-flash"
    
    # Escalation Timers
    grace_period_seconds: int = 5
    tier1_escalation_seconds: int = 45
    tier2_escalation_seconds: int = 90
    
    # Emergency Helplines
    emergency_police: str = "112"
    emergency_ambulance: str = "108"
    emergency_women_helpline: str = "1091"

settings = Settings()
