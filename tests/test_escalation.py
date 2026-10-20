import pytest
import asyncio
from datetime import datetime
from app.models import (
    EmergencySession,
    SessionStatus,
    LocationData,
    Contact
)
from app.database import (
    init_db,
    save_session,
    get_session,
    get_all_contacts,
    get_notifications
)
from app.services.escalation import escalation_manager
from app.services.notification import dispatcher

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

@pytest.mark.asyncio
async def test_escalation_manager_timer_lifecycle():
    session = EmergencySession(
        status=SessionStatus.ACTIVE,
        trigger_source="SOS_BUTTON",
        active_tier=1
    )
    save_session(session)
    
    # Start monitor
    escalation_manager.start_escalation_monitor(session)
    assert session.id in escalation_manager.active_tasks
    
    # Cancel monitor
    escalation_manager.cancel_monitor(session.id)
    assert session.id not in escalation_manager.active_tasks

def test_notification_dispatcher_tier_alert():
    session = EmergencySession(
        status=SessionStatus.ACTIVE,
        trigger_source="SOS_BUTTON",
        location=LocationData(latitude=12.9716, longitude=77.5946, address="MG Road"),
        battery_level=75
    )
    save_session(session)
    
    contacts = [
        Contact(name="Test Contact 1", phone="9999999999", tier=1, notify_sms=True),
        Contact(name="Test Contact 2", phone="8888888888", tier=2, notify_sms=True)
    ]
    
    dispatched = dispatcher.dispatch_tier_alert(session, contacts, tier=1)
    assert len(dispatched) >= 1
    assert dispatched[0].recipient_name == "Test Contact 1"
    assert "SHAKTIGUARD" in dispatched[0].message
