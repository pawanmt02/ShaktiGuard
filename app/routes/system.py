from fastapi import APIRouter
from app.config import settings
from app.models import ApiSettingsUpdate

router = APIRouter(prefix="/api/system", tags=["System & Settings"])

@router.get("/status")
async def get_system_status():
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "has_gemini_key": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "grace_period_seconds": settings.grace_period_seconds,
        "tier1_escalation_seconds": settings.tier1_escalation_seconds,
        "tier2_escalation_seconds": settings.tier2_escalation_seconds,
        "helplines": {
            "police": settings.emergency_police,
            "ambulance": settings.emergency_ambulance,
            "women_helpline": settings.emergency_women_helpline
        }
    }

@router.post("/settings")
async def update_settings(update: ApiSettingsUpdate):
    if update.gemini_api_key is not None:
        settings.gemini_api_key = update.gemini_api_key.strip()
    if update.grace_period_seconds is not None:
        settings.grace_period_seconds = update.grace_period_seconds
    if update.tier1_escalation_seconds is not None:
        settings.tier1_escalation_seconds = update.tier1_escalation_seconds
    if update.tier2_escalation_seconds is not None:
        settings.tier2_escalation_seconds = update.tier2_escalation_seconds
        
    return {
        "status": "success",
        "has_gemini_key": bool(settings.gemini_api_key),
        "grace_period_seconds": settings.grace_period_seconds,
        "tier1_escalation_seconds": settings.tier1_escalation_seconds
    }
