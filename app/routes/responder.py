from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from app.models import AcknowledgeRequest, TimelineEvent
from app.database import (
    get_session,
    get_contact_by_id,
    get_notifications,
    add_notification,
    add_timeline_event,
    get_timeline_events
)
from app.services.escalation import escalation_manager

router = APIRouter(prefix="/api/responder", tags=["Responder"])

@router.get("/session/{session_id}")
async def get_responder_session_view(session_id: str, contact_id: str = None):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
        
    contact = get_contact_by_id(contact_id) if contact_id else None
    notifications = get_notifications(session_id)
    timeline = get_timeline_events(session_id)
    
    return {
        "session": session,
        "contact": contact,
        "notifications": notifications,
        "timeline": timeline
    }

@router.post("/acknowledge")
async def acknowledge_emergency(req: AcknowledgeRequest, session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    contact = get_contact_by_id(req.contact_id)
    responder_name = req.responder_name or (contact.name if contact else "Trusted Contact")
    
    # Update corresponding notification record
    notifs = get_notifications(session_id)
    updated_records = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    for n in notifs:
        if n.recipient_id == req.contact_id:
            n.status = "ACKNOWLEDGED"
            n.acknowledged_at = now_iso
            n.response_note = f"[{req.status}] {req.note}"
            add_notification(n)
            updated_records.append(n)
            
    rel_sec = escalation_manager.get_relative_seconds(session_id)
    add_timeline_event(TimelineEvent(
        session_id=session_id,
        relative_seconds=rel_sec,
        event_type="ACKNOWLEDGE",
        title=f"Responder Acknowledged: {responder_name}",
        details=f"Status: {req.status.replace('_', ' ').title()} - '{req.note}'",
        metadata={"responder_name": responder_name, "status": req.status, "note": req.note}
    ))
    
    return {
        "status": "success",
        "message": f"Acknowledgment recorded for {responder_name}",
        "acknowledged_at": now_iso
    }
