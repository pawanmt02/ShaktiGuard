from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone
from app.models import (
    EmergencyTriggerRequest,
    EmergencySession,
    SessionStatus,
    TimelineEvent,
    LocationData
)
from app.database import (
    save_session,
    get_session,
    get_all_sessions,
    get_all_contacts,
    add_timeline_event,
    get_timeline_events,
    get_notifications
)
from app.agent.engine import AgentEngine
from app.services.location import reverse_geocode, get_nearby_safe_havens
from app.services.notification import dispatcher
from app.services.escalation import escalation_manager
from app.config import settings

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])

@router.post("/trigger", response_model=EmergencySession)
async def trigger_emergency(request: EmergencyTriggerRequest, immediate: bool = False):
    """
    Triggers an emergency distress signal.
    If immediate=True, bypasses grace period and executes agent loop instantly.
    """
    # Create new session
    session = EmergencySession(
        status=SessionStatus.ACTIVE if immediate else SessionStatus.TRIGGERED_GRACE,
        trigger_source=request.trigger_source,
        raw_input=(request.input_text or request.audio_transcript or ""),
        location=request.location,
        battery_level=request.battery_level,
        is_covert=request.is_covert,
        active_tier=1
    )
    
    # Reverse geocode if coordinates provided and address is default
    if session.location and (not session.location.address or session.location.address == "Current GPS Location"):
        address = await reverse_geocode(session.location.latitude, session.location.longitude)
        session.location.address = address

    save_session(session)
    escalation_manager.session_start_times[session.id] = datetime.fromisoformat(session.created_at)

    # Log initial trigger event
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=0.0,
        event_type="TRIGGER",
        title=f"Distress Triggered via {session.trigger_source}",
        details=f"Raw distress input: '{session.raw_input or '[One-Tap Panic]'}' (Covert: {session.is_covert})",
        metadata={"trigger_source": session.trigger_source, "covert": session.is_covert}
    ))

    if immediate:
        # Run agent understanding & planning immediately
        await execute_agent_pipeline(session.id)
        session = get_session(session.id)

    return session

@router.post("/{session_id}/confirm", response_model=EmergencySession)
async def confirm_trigger(session_id: str):
    """Confirms the distress signal, ending grace period and triggering AI agent pipeline."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
        
    if session.status == SessionStatus.TRIGGERED_GRACE:
        await execute_agent_pipeline(session_id)
        session = get_session(session_id)
        
    return session

async def execute_agent_pipeline(session_id: str):
    session = get_session(session_id)
    if not session or session.status in [SessionStatus.RESOLVED, SessionStatus.CANCELLED_FALSE_ALARM]:
        return

    session.status = SessionStatus.ANALYZING
    session.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    # 1. AI Understanding & Planning
    engine = AgentEngine()
    trigger_req = EmergencyTriggerRequest(
        trigger_source=session.trigger_source,
        input_text=session.raw_input,
        location=session.location,
        battery_level=session.battery_level,
        is_covert=session.is_covert
    )
    
    understanding, plan = await engine.process_distress_signal(trigger_req)
    session.understanding = understanding
    session.plan = plan
    session.status = SessionStatus.ACTIVE
    session.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    rel_sec = escalation_manager.get_relative_seconds(session.id)
    
    # 2. Log Understanding event
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec,
        event_type="UNDERSTAND",
        title=f"AI Agent: Classified as {understanding.urgency.value} Priority",
        details=f"{understanding.situational_summary} | Incident: {understanding.incident_type.value}",
        metadata=understanding.model_dump()
    ))

    # 3. Log Plan event
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec + 0.1,
        event_type="PLAN",
        title=f"AI Agent: Activated Workflow {plan.workflow_id}",
        details=f"Selected '{plan.workflow_name}'. Action: {plan.priority_action}",
        metadata=plan.model_dump()
    ))

    # 4. Dispatch Tier 1 notifications
    contacts = get_all_contacts()
    dispatched = dispatcher.dispatch_tier_alert(session, contacts, tier=1)
    
    # Log Dispatch event
    recipient_names = ", ".join([d.recipient_name for d in dispatched if d.channel == "SMS"]) or "Primary Contacts"
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec + 0.2,
        event_type="DISPATCH",
        title=f"Multi-Channel Alert Dispatched (Tier 1)",
        details=f"Sent emergency SMS/Email with live GPS link to: {recipient_names}",
        metadata={"count": len(dispatched), "recipients": recipient_names}
    ))

    # 5. Start background escalation monitor
    escalation_manager.start_escalation_monitor(session)

@router.post("/{session_id}/cancel", response_model=EmergencySession)
async def cancel_emergency(session_id: str, reason: Optional[str] = "False alarm / User cancelled"):
    """Cancels the emergency, stops escalation, and sends all-clear if alerts were dispatched."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")

    escalation_manager.cancel_monitor(session_id)
    prev_status = session.status
    session.status = SessionStatus.CANCELLED_FALSE_ALARM
    session.cancellation_reason = reason
    session.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    rel_sec = escalation_manager.get_relative_seconds(session_id)
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec,
        event_type="CANCEL",
        title="Emergency Cancelled / False Alarm Safeguard",
        details=f"User aborted distress session: {reason}",
        metadata={"reason": reason, "previous_status": str(prev_status)}
    ))

    # If alerts had already been dispatched, send an All Clear update
    if prev_status in [SessionStatus.ACTIVE, SessionStatus.ESCALATED_TIER_2, SessionStatus.ESCALATED_EMERGENCY]:
        contacts = get_all_contacts()
        dispatcher.dispatch_cancellation(session, contacts, reason)

    return session

@router.post("/{session_id}/resolve", response_model=EmergencySession)
async def resolve_emergency(session_id: str, notes: Optional[str] = "Emergency resolved safely."):
    """Marks the emergency as safely resolved."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")

    escalation_manager.cancel_monitor(session_id)
    session.status = SessionStatus.RESOLVED
    session.resolution_notes = notes
    session.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    rel_sec = escalation_manager.get_relative_seconds(session_id)
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec,
        event_type="RESOLVE",
        title="Incident Marked Resolved",
        details=f"Resolution note: {notes}",
        metadata={"notes": notes}
    ))

    return session

@router.post("/{session_id}/location", response_model=EmergencySession)
async def update_location(session_id: str, location: LocationData):
    """Receives live GPS updates while session is active."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")

    if not location.address or location.address == "Current GPS Location":
        location.address = await reverse_geocode(location.latitude, location.longitude)

    session.location = location
    session.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    rel_sec = escalation_manager.get_relative_seconds(session_id)
    add_timeline_event(TimelineEvent(
        session_id=session.id,
        relative_seconds=rel_sec,
        event_type="LOCATION_UPDATE",
        title="Live Location Streamed",
        details=f"Updated GPS: {location.address} (Accuracy: {location.accuracy}m)",
        metadata={"lat": location.latitude, "lng": location.longitude, "accuracy": location.accuracy}
    ))

    return session

@router.get("/active")
async def get_active_session():
    """Returns the most recent active or latest emergency session."""
    sessions = get_all_sessions(limit=5)
    for s in sessions:
        if s.status in [SessionStatus.TRIGGERED_GRACE, SessionStatus.ANALYZING, SessionStatus.ACTIVE, SessionStatus.ESCALATED_TIER_2, SessionStatus.ESCALATED_EMERGENCY]:
            timeline = get_timeline_events(s.id)
            notifs = get_notifications(s.id)
            safe_havens = []
            if s.location:
                safe_havens = get_nearby_safe_havens(s.location.latitude, s.location.longitude)
            return {
                "session": s,
                "timeline": timeline,
                "notifications": notifs,
                "safe_havens": safe_havens
            }
            
    # If none active, return the most recent session if available
    if sessions:
        s = sessions[0]
        return {
            "session": s,
            "timeline": get_timeline_events(s.id),
            "notifications": get_notifications(s.id),
            "safe_havens": get_nearby_safe_havens(s.location.latitude, s.location.longitude) if s.location else []
        }
    return {"session": None, "timeline": [], "notifications": [], "safe_havens": []}

@router.get("/history", response_model=List[EmergencySession])
async def list_emergency_history(limit: int = 50):
    return get_all_sessions(limit=limit)

@router.get("/{session_id}")
async def get_emergency_detail(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    timeline = get_timeline_events(session_id)
    notifications = get_notifications(session_id)
    safe_havens = []
    if session.location:
        safe_havens = get_nearby_safe_havens(session.location.latitude, session.location.longitude)
        
    return {
        "session": session,
        "timeline": timeline,
        "notifications": notifications,
        "safe_havens": safe_havens
    }
