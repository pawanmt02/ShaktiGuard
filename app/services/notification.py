import logging
from typing import List, Optional
from datetime import datetime, timezone
from app.models import Contact, EmergencySession, NotificationRecord
from app.database import add_notification, get_notifications, get_recent_notifications

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    def __init__(self):
        pass

    def dispatch_tier_alert(
        self,
        session: EmergencySession,
        contacts: List[Contact],
        tier: int,
        base_url: str = "http://localhost:8000"
    ) -> List[NotificationRecord]:
        """
        Dispatches emergency alerts to all contacts belonging to the specified tier.
        """
        records: List[NotificationRecord] = []
        loc = session.location
        maps_link = f"https://maps.google.com/?q={loc.latitude},{loc.longitude}" if loc else "Unavailable"
        responder_link = f"{base_url}/#responder?session={session.id}"
        
        urgency_str = session.understanding.urgency.value if session.understanding else "HIGH"
        incident_str = session.understanding.incident_type.value.replace("_", " ").title() if session.understanding else "Emergency"
        summary = session.understanding.situational_summary if session.understanding else "Distress triggered."
        
        tier_contacts = [c for c in contacts if c.tier == tier]
        
        for contact in tier_contacts:
            contact_responder_link = f"{responder_link}&contact={contact.id}"
            
            # Format high-urgency SMS message
            sms_body = (
                f"🚨 SHAKTIGUARD {urgency_str} SOS 🚨\n"
                f"User reported: {incident_str}\n"
                f"Context: {summary}\n"
                f"Location: {loc.address if loc else 'GPS'} ({maps_link})\n"
                f"Battery: {session.battery_level}%\n"
                f"Tap to ACKNOWLEDGE & RESPOND: {contact_responder_link}"
            )
            
            # 1. SMS Channel
            if contact.notify_sms:
                sms_record = NotificationRecord(
                    session_id=session.id,
                    recipient_id=contact.id,
                    recipient_name=contact.name,
                    recipient_phone=contact.phone,
                    recipient_email=contact.email,
                    channel="SMS",
                    message=sms_body,
                    sent_at=datetime.now(timezone.utc).isoformat(),
                    status="DELIVERED"
                )
                add_notification(sms_record)
                records.append(sms_record)
                logger.info(f"[DISPATCH SMS] To {contact.name} ({contact.phone}): {sms_body[:80]}...")

            # 2. Email Channel
            if contact.notify_email and contact.email:
                email_body = (
                    f"URGENT EMERGENCY ALERT: {session.id}\n\n"
                    f"A distress alert was triggered for {contact.name}'s contact.\n\n"
                    f"Incident: {incident_str} ({urgency_str} Priority)\n"
                    f"Summary: {summary}\n"
                    f"Location: {loc.address if loc else 'GPS'}\n"
                    f"Google Maps: {maps_link}\n"
                    f"Device Battery: {session.battery_level}%\n\n"
                    f"Please coordinate assistance immediately at: {contact_responder_link}"
                )
                email_record = NotificationRecord(
                    session_id=session.id,
                    recipient_id=contact.id,
                    recipient_name=contact.name,
                    recipient_phone=contact.phone,
                    recipient_email=contact.email,
                    channel="EMAIL",
                    message=email_body,
                    sent_at=datetime.now(timezone.utc).isoformat(),
                    status="DELIVERED"
                )
                add_notification(email_record)
                records.append(email_record)
                logger.info(f"[DISPATCH EMAIL] To {contact.name} ({contact.email})")

            # 3. Automated Voice Call Alert simulation if enabled
            if contact.notify_call:
                call_record = NotificationRecord(
                    session_id=session.id,
                    recipient_id=contact.id,
                    recipient_name=contact.name,
                    recipient_phone=contact.phone,
                    recipient_email=contact.email,
                    channel="AUTOMATED_CALL",
                    message=f"[PRIORITY ROBOCALL] ShaktiGuard Emergency triggered by your contact. Urgency: {urgency_str}. Acknowledge via SMS link.",
                    sent_at=datetime.now(timezone.utc).isoformat(),
                    status="DELIVERED"
                )
                add_notification(call_record)
                records.append(call_record)

        return records

    def dispatch_cancellation(
        self,
        session: EmergencySession,
        contacts: List[Contact],
        reason: str = "False alarm - user confirmed safety."
    ) -> List[NotificationRecord]:
        """Dispatches an 'All Clear / Safe' notification to previously alerted contacts."""
        records = []
        # Find all contacts who received an alert for this session
        notified = get_notifications(session.id)
        contact_ids = set(n.recipient_id for n in notified)
        alerted_contacts = [c for c in contacts if c.id in contact_ids]
        
        for contact in alerted_contacts:
            msg = (
                f"✅ SHAKTIGUARD UPDATE: SOS Cancelled. "
                f"The user has confirmed they are safe ({reason}). "
                f"Stand down from emergency response."
            )
            rec = NotificationRecord(
                session_id=session.id,
                recipient_id=contact.id,
                recipient_name=contact.name,
                recipient_phone=contact.phone,
                recipient_email=contact.email,
                channel="SMS",
                message=msg,
                sent_at=datetime.utcnow().isoformat(),
                status="DELIVERED"
            )
            add_notification(rec)
            records.append(rec)
            
        return records

dispatcher = NotificationDispatcher()
