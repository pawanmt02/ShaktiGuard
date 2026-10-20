import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "ShaktiGuard" in data["app_name"]
    assert "helplines" in data

def test_contacts_crud():
    # 1. List contacts
    res = client.get("/api/contacts")
    assert res.status_code == 200
    contacts = res.json()
    assert len(contacts) > 0
    
    # 2. Add new contact
    new_c = {
        "name": "Dr. Aarav Patel",
        "phone": "+91 99887 76655",
        "email": "aarav@example.com",
        "relationship": "Physician",
        "tier": 2,
        "notify_sms": True,
        "notify_email": True,
        "notify_call": False
    }
    create_res = client.post("/api/contacts", json=new_c)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["name"] == "Dr. Aarav Patel"
    c_id = created["id"]
    
    # 3. Delete contact
    del_res = client.delete(f"/api/contacts/{c_id}")
    assert del_res.status_code == 200

def test_trigger_and_cancel_safeguard():
    # Test triggering with grace period
    payload = {
        "trigger_source": "SOS_BUTTON",
        "input_text": "Accidental tap test",
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "battery_level": 90,
        "is_covert": False
    }
    trigger_res = client.post("/api/emergency/trigger?immediate=false", json=payload)
    assert trigger_res.status_code == 200
    session = trigger_res.json()
    assert session["status"] == "TRIGGERED_GRACE"
    s_id = session["id"]
    
    # Cancel within grace period (safeguard)
    cancel_res = client.post(f"/api/emergency/{s_id}/cancel?reason=Pocket+accidental+press")
    assert cancel_res.status_code == 200
    cancelled = cancel_res.json()
    assert cancelled["status"] == "CANCELLED_FALSE_ALARM"

def test_immediate_emergency_and_acknowledge():
    payload = {
        "trigger_source": "VOICE",
        "input_text": "I feel unsafe near the bus stop, someone is following me.",
        "location": {"latitude": 12.9784, "longitude": 77.6408},
        "battery_level": 55,
        "is_covert": False
    }
    trigger_res = client.post("/api/emergency/trigger?immediate=true", json=payload)
    assert trigger_res.status_code == 200
    session = trigger_res.json()
    assert session["status"] == "ACTIVE"
    assert session["understanding"] is not None
    assert session["plan"] is not None
    s_id = session["id"]

    # Responder acknowledgment
    contacts_res = client.get("/api/contacts")
    contacts = contacts_res.json()
    first_c = contacts[0]
    
    ack_payload = {
        "contact_id": first_c["id"],
        "responder_name": first_c["name"],
        "status": "EN_ROUTE",
        "note": "Calling you right now and driving to your location."
    }
    ack_res = client.post(f"/api/responder/acknowledge?session_id={s_id}", json=ack_payload)
    assert ack_res.status_code == 200
    
    # Resolve
    resolve_res = client.post(f"/api/emergency/{s_id}/resolve?notes=User+safely+reunited+with+brother")
    assert resolve_res.status_code == 200
    resolved = resolve_res.json()
    assert resolved["status"] == "RESOLVED"

def test_simulation_scenario_run():
    sim_res = client.post("/api/simulate/run/scenario-stalking?auto_acknowledge=true")
    assert sim_res.status_code == 200
    data = sim_res.json()
    assert data["performance"]["workflow_completed"] is True
    assert data["session"]["understanding"]["incident_type"] == "STALKING_HARASSMENT"

def test_simulation_metrics():
    metrics_res = client.get("/api/simulate/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert "workflow_completion_pct" in metrics
    assert "alert_delivery_time_avg_ms" in metrics
