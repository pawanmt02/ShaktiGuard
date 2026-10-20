import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from app.config import settings
from app.models import (
    EmergencySession,
    SessionStatus,
    TimelineEvent,
    UrgencyLevel
)
from app.database import (
    get_session,
    save_session,
    get_all_contacts,
    add_timeline_event,
    get_notifications
)
from app.services.notification import dispatcher

logger = logging.getLogger(__name__)

class EscalationManager:
    def __init__(self):
        # Maps session_id to active asyncio background task
        self.active_tasks: Dict[str, asyncio.Task] = {}
        # Stores session start timestamps for relative seconds calculation
        self.session_start_times: Dict[str, datetime] = {}

    def get_relative_seconds(self, session_id: str) -> float:
        start = self.session_start_times.get(session_id)
        if not start:
            return 0.0
        # Ensure start is timezone-aware if needed
        now = datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return round((now - start).total_seconds(), 1)

    def start_escalation_monitor(self, session: EmergencySession):
        """Starts asynchronous escalation loop for an active emergency session."""
        self.cancel_monitor(session.id)
        self.session_start_times[session.id] = datetime.fromisoformat(session.created_at)
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_escalation_loop(session.id))
            self.active_tasks[session.id] = task
        except RuntimeError:
            logger.debug(f"No running event loop available to spawn escalation task for {session.id}.")

    def cancel_monitor(self, session_id: str):
        """Cancels any running escalation timer for this session."""
        task = self.active_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

    async def _run_escalation_loop(self, session_id: str):
        try:
            # 1. Wait for Tier 1 Escalation Timeout
            tier1_wait = settings.tier1_escalation_seconds
            logger.info(f"Escalation monitor started for session {session_id}. Waiting {tier1_wait}s for Tier-1 ack.")
            await asyncio.sleep(tier1_wait)

            session = get_session(session_id)
            if not session or session.status in [SessionStatus.RESOLVED, SessionStatus.CANCELLED_FALSE_ALARM]:
                return

            # Check if any contact acknowledged
            notifs = get_notifications(session_id)
            has_ack = any(n.status == "ACKNOWLEDGED" for n in notifs)
            if has_ack:
                logger.info(f"Session {session_id} acknowledged by a responder. Pausing escalation.")
                return

            # Escalate to Tier 2
            contacts = get_all_contacts()
            session.active_tier = 2
            session.status = SessionStatus.ESCALATED_TIER_2
            session.updated_at = datetime.now(timezone.utc).isoformat()
            save_session(session)

            rel_sec = self.get_relative_seconds(session_id)
            add_timeline_event(TimelineEvent(
                session_id=session.id,
                relative_seconds=rel_sec,
                event_type="ESCALATE",
                title="Tier 1 Timeout: Escalating to Tier 2",
                details=f"No acknowledgment received within {tier1_wait}s. Alerting secondary trusted contacts.",
                metadata={"new_tier": 2}
            ))

            dispatcher.dispatch_tier_alert(session, contacts, tier=2)
            logger.warning(f"Session {session_id} escalated to Tier-2 contacts.")

            # 2. Wait for Tier 2 Escalation Timeout
            tier2_wait = settings.tier2_escalation_seconds - settings.tier1_escalation_seconds
            if tier2_wait > 0:
                await asyncio.sleep(tier2_wait)

            session = get_session(session_id)
            if not session or session.status in [SessionStatus.RESOLVED, SessionStatus.CANCELLED_FALSE_ALARM]:
                return

            notifs = get_notifications(session_id)
            has_ack = any(n.status == "ACKNOWLEDGED" for n in notifs)
            if has_ack:
                logger.info(f"Session {session_id} acknowledged before Tier 3 escalation.")
                return

            # Escalate to Tier 3 (Emergency Helplines / 112)
            session.active_tier = 3
            session.status = SessionStatus.ESCALATED_EMERGENCY
            session.updated_at = datetime.now(timezone.utc).isoformat()
            save_session(session)

            rel_sec = self.get_relative_seconds(session_id)
            add_timeline_event(TimelineEvent(
                session_id=session.id,
                relative_seconds=rel_sec,
                event_type="ESCALATE",
                title="Critical Escalation: Alerting Emergency Dispatch (112)",
                details="Primary and Secondary tiers did not respond. Transmitting automated priority dispatch to Emergency Services.",
                metadata={"new_tier": 3, "helpline": settings.emergency_police}
            ))

            dispatcher.dispatch_tier_alert(session, contacts, tier=3)
            logger.critical(f"Session {session_id} reached CRITICAL Tier-3 Emergency Helpline escalation!")

        except asyncio.CancelledError:
            logger.info(f"Escalation monitor task cancelled for session {session_id}.")
        except Exception as e:
            logger.error(f"Error in escalation loop for {session_id}: {e}")

escalation_manager = EscalationManager()
