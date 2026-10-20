import pytest
from app.agent.engine import AgentEngine
from app.models import (
    EmergencyTriggerRequest,
    LocationData,
    UrgencyLevel,
    IncidentType
)

@pytest.mark.asyncio
async def test_agent_stalking_detection():
    engine = AgentEngine()
    req = EmergencyTriggerRequest(
        trigger_source="VOICE",
        input_text="A strange man is following me near the bus stop in the dark, I am frightened.",
        location=LocationData(latitude=12.9716, longitude=77.5946, address="Indiranagar"),
        battery_level=60,
        is_covert=False
    )
    understanding, plan = await engine.process_distress_signal(req)
    
    assert understanding.urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
    assert understanding.incident_type == IncidentType.STALKING_HARASSMENT
    assert len(plan.guidance_steps) >= 3
    assert "bus stop" in understanding.extracted_entities.get("location_named", "").lower()
    assert plan.workflow_id.startswith("WF-SG")

@pytest.mark.asyncio
async def test_agent_medical_emergency_detection():
    engine = AgentEngine()
    req = EmergencyTriggerRequest(
        trigger_source="TEXT",
        input_text="Severe chest pain and difficulty breathing, feel like fainting.",
        location=LocationData(latitude=12.9352, longitude=77.6245),
        battery_level=80,
        is_covert=False
    )
    understanding, plan = await engine.process_distress_signal(req)
    
    assert understanding.urgency == UrgencyLevel.CRITICAL
    assert understanding.incident_type == IncidentType.MEDICAL_EMERGENCY
    assert any("sit" in step.lower() or "lie" in step.lower() for step in plan.guidance_steps)

@pytest.mark.asyncio
async def test_agent_silent_covert_trigger():
    engine = AgentEngine()
    req = EmergencyTriggerRequest(
        trigger_source="SOS_BUTTON",
        input_text="",
        battery_level=45,
        is_covert=True
    )
    understanding, plan = await engine.process_distress_signal(req)
    
    assert understanding.urgency == UrgencyLevel.HIGH
    assert plan.silent_mode_recommended is True
