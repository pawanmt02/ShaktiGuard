from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class UrgencyLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class IncidentType(str, Enum):
    STALKING_HARASSMENT = "STALKING_HARASSMENT"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    SUSPICIOUS_ROUTE_TRANSIT = "SUSPICIOUS_ROUTE_TRANSIT"
    ACCIDENT_COLLISION = "ACCIDENT_COLLISION"
    PHYSICAL_ASSAULT = "PHYSICAL_ASSAULT"
    FIRE_HAZARD = "FIRE_HAZARD"
    GENERAL_DISTRESS = "GENERAL_DISTRESS"

class SessionStatus(str, Enum):
    TRIGGERED_GRACE = "TRIGGERED_GRACE"
    ANALYZING = "ANALYZING"
    ACTIVE = "ACTIVE"
    ESCALATED_TIER_2 = "ESCALATED_TIER_2"
    ESCALATED_EMERGENCY = "ESCALATED_EMERGENCY"
    RESOLVED = "RESOLVED"
    CANCELLED_FALSE_ALARM = "CANCELLED_FALSE_ALARM"

class LocationData(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = 10.0
    altitude: Optional[float] = None
    speed: Optional[float] = None
    address: Optional[str] = "Current GPS Location"
    landmark: Optional[str] = None
    timestamp: Optional[str] = None

class Contact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    email: Optional[str] = None
    relationship: str = "Family"
    tier: int = 1  # 1: Primary, 2: Secondary, 3: Helplines
    notify_sms: bool = True
    notify_email: bool = True
    notify_call: bool = False
    created_at: str = Field(default_factory=utc_now_iso)

class EmergencyTriggerRequest(BaseModel):
    trigger_source: str = "SOS_BUTTON"  # SOS_BUTTON, VOICE, TEXT, SIMULATION
    input_text: Optional[str] = ""
    audio_transcript: Optional[str] = ""
    location: Optional[LocationData] = None
    battery_level: Optional[int] = 85
    is_covert: bool = False

class AgentUnderstanding(BaseModel):
    urgency: UrgencyLevel = UrgencyLevel.HIGH
    confidence: float = 0.95
    incident_type: IncidentType = IncidentType.GENERAL_DISTRESS
    situational_summary: str
    extracted_entities: Dict[str, Any] = {}
    threat_assessment: str
    reasoning: str

class AgentPlan(BaseModel):
    workflow_id: str
    workflow_name: str
    priority_action: str
    target_contacts: List[str] = []
    notification_message: str
    guidance_steps: List[str] = []
    escalation_policy: Dict[str, Any] = {}
    silent_mode_recommended: bool = False
    siren_recommended: bool = False

class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    relative_seconds: float = 0.0
    event_type: str  # TRIGGER, UNDERSTAND, PLAN, DISPATCH, ACKNOWLEDGE, ESCALATE, LOCATION_UPDATE, CANCEL, RESOLVE
    title: str
    details: str
    metadata: Dict[str, Any] = {}

class NotificationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    recipient_id: str
    recipient_name: str
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    channel: str = "SMS"  # SMS, EMAIL, PUSH, WHATSAPP, HELPLINE
    message: str
    sent_at: str = Field(default_factory=utc_now_iso)
    status: str = "DELIVERED"  # SENT, DELIVERED, ACKNOWLEDGED, FAILED
    acknowledged_at: Optional[str] = None
    response_note: Optional[str] = None

class EmergencySession(BaseModel):
    id: str = Field(default_factory=lambda: f"SG-{uuid.uuid4().hex[:8].upper()}")
    status: SessionStatus = SessionStatus.TRIGGERED_GRACE
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    trigger_source: str = "SOS_BUTTON"
    raw_input: str = ""
    location: Optional[LocationData] = None
    understanding: Optional[AgentUnderstanding] = None
    plan: Optional[AgentPlan] = None
    battery_level: Optional[int] = 85
    is_covert: bool = False
    active_tier: int = 1
    cancellation_reason: Optional[str] = None
    resolution_notes: Optional[str] = None

class AcknowledgeRequest(BaseModel):
    contact_id: str
    responder_name: Optional[str] = None
    status: str = "EN_ROUTE"  # EN_ROUTE, CALLING_USER, POLICE_ALERTED, USER_SAFE, STAND_DOWN
    note: Optional[str] = "Responding immediately."

class ApiSettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    grace_period_seconds: Optional[int] = None
    tier1_escalation_seconds: Optional[int] = None
    tier2_escalation_seconds: Optional[int] = None
