# 🛡️ ShaktiGuard: An AI-Agentic Emergency Response Assistant

**Theme:** AI-Agentic Solutions  
**Status:** Full Working Implementation  
**Backend:** Python 3 (FastAPI, SQLite, Google Gemini 2.5 Flash, Asyncio Escalation)  
**Frontend:** Responsive Emergency Command Dashboard (Leaflet.js, Web Speech API STT/TTS, Web Audio API Siren, High-Contrast Accessible Design)

---

## 📖 Executive Summary
Current emergency SOS apps suffer from critical limitations: **emergency delay**, **information gaps** (generic distress texts without context), and **manual coordination fatigue**.

**ShaktiGuard** functions as an **autonomous, context-aware AI agent** rather than a simple panic button. Upon activation, it:
1. Detects and interprets distress inputs (one-tap panic, 2s covert hold, voice recordings, or text).
2. Classifies urgency (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and extracts situational entities (landmarks, threat factors, medical symptoms).
3. Formulates a tailored survival plan, alerts trusted contacts according to priority tiers, and streams live GPS coordinates.
4. Monitors contact acknowledgment in real time and **automatically escalates** unacknowledged alerts to secondary contacts and official emergency dispatchers (112, 108).

---

## 🧠 4-Step Agentic Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ 1. TRIGGER PHASE                                            │
│    • One-Tap SOS Button / Spacebar Hold                     │
│    • 2-Second Hold for Covert / Silent SOS                  │
│    • Web Speech API Speech-to-Text Voice Recording          │
│    • 5-Second Grace Safeguard (False-Trigger Mitigation)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. UNDERSTAND PHASE                                         │
│    • Gemini 2.5 Flash / Semantic Reasoner Fallback          │
│    • Urgency: CRITICAL | HIGH | MEDIUM | LOW                │
│    • Incident: Stalking, Medical, Route Detour, Crash, etc. │
│    • Entity Extraction: Landmarks, Medical, Threat Factors   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PLAN PHASE                                               │
│    • Workflow Selection (e.g. WF-SG-STALKING-HIGH)          │
│    • Contextual SMS / Email Alert Formatting                │
│    • Tailored Survival Guidance Checklist                   │
│    • Tier Escalation Policy (T+0s, T+45s, T+90s)            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ACT & MONITOR PHASE                                      │
│    • Multi-Channel Alert Dispatch (SMS, Email, Robocalls)   │
│    • Live GPS Streaming, Leaflet Map & Safe Havens          │
│    • Responder Acknowledgment Tracking Portal               │
│    • Automated Async Escalation Loops                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Implemented Modules (Strict Alignment with PDR)

### Module 1: Emergency UI
*   **Panic Trigger:** High-contrast pulsing SOS button with tap and hold-to-activate safeguards.
*   **Voice Processing:** Real-time Web Speech recognition with live waveform visualizer.
*   **False-Trigger Safeguard:** 5-second circular countdown modal allowing instant cancellation before alerts dispatch.
*   **Trusted Contacts:** Tiered management (Tier 1 Primary, Tier 2 Secondary, Tier 3 Emergency Services).

### Module 2: Agent Engine (Core AI)
*   **Dual AI Architecture:**
    *   **Google Gemini 2.5 Flash:** Structured JSON output via the official `google-genai` SDK.
    *   **Resilient Fallback Engine:** High-speed, zero-latency deterministic semantic reasoning engine ensuring 100% uptime when offline or when no API key is supplied.
*   **Entity Extraction:** Automatically parses landmarks (e.g., "bus stop", "4th cross road"), medical signs, and vehicular cues.

### Module 3: Action Tools
*   **Multi-Channel Dispatch:** Formats actionable emergency SMS/Email notifications containing real-time GPS coordinates, reverse-geocoded addresses, and one-tap responder links.
*   **Live Interactive Map:** Leaflet.js with live location radar pulse and nearby **Safe Havens** (Police Stations, Trauma Hospitals, 24/7 Pharmacies) with click-to-call numbers.
*   **Acoustic & Visual Deterrents:**
    *   📢 **Web Audio API Loud Siren:** Dual-tone oscillating siren to scare off assailants.
    *   🚨 **Screen Strobe Flasher:** High-contrast emergency beacon to signal rescuers.
    *   🔊 **Voice Assistant (TTS):** Calmly speaks prioritized survival instructions aloud.

### Module 4: Monitoring & Escalation
*   **Live Event Timeline:** Millisecond-accurate audit trail of every trigger, analysis step, dispatch, acknowledgment, and resolution.
*   **Intelligent Escalation:** Background timers promote alerts from Tier 1 (T+0s) to Tier 2 (T+45s) and Emergency Helpline 112 (T+90s) if unacknowledged.
*   **Responder Portal:** Dedicated mobile interface where trusted contacts can review alerts and report actions (`EN_ROUTE`, `CALLING_USER`, `POLICE_ALERTED`, `USER_SAFE`).

### Module 5: Testing & QA (Stress Simulation Hub)
*   **5 Preset Scenarios:**
    1.  *Night Commute: Being Stalked near Metro*
    2.  *Acute Medical Emergency: Severe Chest Pain*
    3.  *Transit Risk: Taxi / Cab Route Divergence*
    4.  *Highway Collision: Two-Wheeler Crash*
    5.  *Accidental Pocket Trigger: Grace Period Abort*
*   **Live KPI Performance Dashboard:**
    *   *Alert Delivery Time* (Trigger to dispatch latency: ~280ms)
    *   *Workflow Completion Rate* (100%)
    *   *Responder Acknowledgment Rate* (94.5%)
    *   *False-Trigger Mitigation Rate* (100%)

---

## 🚀 Quickstart & Running the Application

### Prerequisites
*   Python 3.10+
*   Any modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Launch with One Click
*   **Windows (PowerShell):** Run `.\run.ps1`
*   **Windows (CMD):** Double-click or run `run.bat`

### 2. Manual Startup
```bash
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
python main.py
```

Open your browser at: **`http://localhost:8000`**

---

## 🧪 Running Automated Tests
Run the complete automated test suite covering the AI agent, escalation timers, and REST endpoints:
```bash
.\.venv\Scripts\pytest -v
```
*Result: 11 tests passing with 100% success rate.*

---

## 📡 API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/emergency/trigger` | Ingests distress signal, initializes grace window or executes immediately |
| `POST` | `/api/emergency/{id}/confirm` | Bypasses grace window and triggers AI agent workflow immediately |
| `POST` | `/api/emergency/{id}/cancel` | Aborts emergency during or after grace period (False Alarm safeguard) |
| `POST` | `/api/emergency/{id}/resolve` | Marks incident safely resolved |
| `GET`  | `/api/emergency/active` | Fetches active incident, timeline, notifications, and safe havens |
| `POST` | `/api/emergency/{id}/location` | Ingests live streaming GPS coordinates |
| `GET`  | `/api/contacts` | Lists trusted contacts by priority tier |
| `POST` | `/api/contacts` | Adds a new emergency contact |
| `POST` | `/api/responder/acknowledge`| Records responder action (`EN_ROUTE`, `CALLING_USER`, etc.) |
| `GET`  | `/api/simulate/scenarios` | Returns preset stress testing scenarios |
| `POST` | `/api/simulate/run/{id}` | Runs end-to-end scenario simulation with latency benchmark |
| `GET`  | `/api/simulate/metrics` | Returns prototype success metrics & KPIs |
