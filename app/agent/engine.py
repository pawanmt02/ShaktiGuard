import json
import logging
from typing import Tuple, Optional
from datetime import datetime
from app.config import settings
from app.models import (
    EmergencyTriggerRequest,
    AgentUnderstanding,
    AgentPlan,
    UrgencyLevel,
    IncidentType,
    LocationData
)
from app.agent.prompt import SHAKTIGUARD_SYSTEM_PROMPT
from app.agent.safety_rules import analyze_heuristic_distress, SAFETY_CHECKLISTS

logger = logging.getLogger(__name__)

class AgentEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        
    async def process_distress_signal(
        self,
        request: EmergencyTriggerRequest,
        user_name: str = "User"
    ) -> Tuple[AgentUnderstanding, AgentPlan]:
        """
        Executes the 4-step agent workflow:
        1. Ingest Trigger & context
        2. Understand (LLM or Heuristic Reasoning)
        3. Plan (Formulate response & actionable safety guidance)
        4. Return structured artifacts for Act & Monitor
        """
        raw_text = (request.input_text or request.audio_transcript or "").strip()
        location_str = "Unknown Location"
        if request.location:
            location_str = f"{request.location.address or 'Lat: ' + str(round(request.location.latitude, 4)) + ', Lng: ' + str(round(request.location.longitude, 4))}"

        # Attempt LLM processing if API key is configured
        if self.api_key:
            try:
                understanding, plan = await self._call_gemini_agent(request, raw_text, location_str, user_name)
                if understanding and plan:
                    return understanding, plan
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to intelligent heuristic engine: {e}")

        # Fallback to intelligent deterministic reasoning engine
        return self._run_heuristic_agent(request, raw_text, location_str, user_name)

    async def _call_gemini_agent(
        self,
        request: EmergencyTriggerRequest,
        raw_text: str,
        location_str: str,
        user_name: str
    ) -> Tuple[AgentUnderstanding, AgentPlan]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        
        user_prompt = f"""EMERGENCY DISTRESS TRIGGER RECEIVED:
- User Name: {user_name}
- Trigger Mechanism: {request.trigger_source} (Covert Mode: {request.is_covert})
- Input Distress Message / Transcript: "{raw_text if raw_text else '[SILENT ONE-TAP PANIC BUTTON PRESSED]'}"
- Location Coordinates: {f"Lat {request.location.latitude}, Lng {request.location.longitude}" if request.location else "Not Available"}
- Approximate Address: {location_str}
- Device Battery: {request.battery_level}%
- Current Timestamp: {datetime.utcnow().isoformat()}

Analyze the threat, classify urgency and incident type, and plan the emergency response."""

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SHAKTIGUARD_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        
        data = json.loads(response.text)
        und_data = data.get("understanding", {})
        plan_data = data.get("plan", {})
        
        understanding = AgentUnderstanding(
            urgency=UrgencyLevel(und_data.get("urgency", "HIGH")),
            confidence=float(und_data.get("confidence", 0.95)),
            incident_type=IncidentType(und_data.get("incident_type", "GENERAL_DISTRESS")),
            situational_summary=und_data.get("situational_summary", "Emergency distress signal triggered."),
            extracted_entities=und_data.get("extracted_entities", {}),
            threat_assessment=und_data.get("threat_assessment", "Elevated threat detected."),
            reasoning=und_data.get("reasoning", "LLM reasoning synthesized situation parameters.")
        )
        
        plan = AgentPlan(
            workflow_id=plan_data.get("workflow_id", "WF-SG-AGENT-01"),
            workflow_name=plan_data.get("workflow_name", "Autonomous Rapid Response"),
            priority_action=plan_data.get("priority_action", "Alert Tier 1 contacts & stream location"),
            target_contacts=plan_data.get("target_contacts", []),
            notification_message=plan_data.get("notification_message", f"EMERGENCY: {user_name} needs urgent assistance near {location_str}."),
            guidance_steps=plan_data.get("guidance_steps", SAFETY_CHECKLISTS.get(understanding.incident_type, [])),
            escalation_policy=plan_data.get("escalation_policy", {"tier1_timeout_seconds": settings.tier1_escalation_seconds}),
            silent_mode_recommended=plan_data.get("silent_mode_recommended", request.is_covert),
            siren_recommended=plan_data.get("siren_recommended", False)
        )
        
        return understanding, plan

    def _run_heuristic_agent(
        self,
        request: EmergencyTriggerRequest,
        raw_text: str,
        location_str: str,
        user_name: str
    ) -> Tuple[AgentUnderstanding, AgentPlan]:
        urgency, incident_type, summary, entities, threat_assessment, guidance = analyze_heuristic_distress(
            raw_text, request.location, request.is_covert
        )
        
        workflow_id = f"WF-SG-{incident_type.value[:4]}-{urgency.value[:3]}"
        workflow_names = {
            IncidentType.STALKING_HARASSMENT: "Predator Avoidance & Discreet Alert Workflow",
            IncidentType.MEDICAL_EMERGENCY: "Medical Distress & Ambulance Notification Workflow",
            IncidentType.SUSPICIOUS_ROUTE_TRANSIT: "Transit Route Deviation & Safe Haven Tracking",
            IncidentType.ACCIDENT_COLLISION: "Crash Impact & First-Responder Alert Workflow",
            IncidentType.PHYSICAL_ASSAULT: "High-Threat Assault Deterrence & SOS Broadcast",
            IncidentType.FIRE_HAZARD: "Fire Hazard Evacuation & Emergency Dispatch",
            IncidentType.GENERAL_DISTRESS: "General Emergency Rapid Alert Workflow"
        }
        
        is_covert = request.is_covert or (incident_type == IncidentType.STALKING_HARASSMENT and "follow" in raw_text.lower())
        siren_rec = (urgency == UrgencyLevel.CRITICAL and not is_covert and incident_type in [IncidentType.PHYSICAL_ASSAULT, IncidentType.FIRE_HAZARD])
        
        notification_msg = (
            f"🚨 SHAKTIGUARD {urgency.value} SOS: {user_name} reported '{incident_type.value.replace('_', ' ').title()}'! "
            f"Situation: {summary} "
            f"Location: {location_str} "
            f"Battery: {request.battery_level or 85}%. "
            f"Respond immediately!"
        )
        
        understanding = AgentUnderstanding(
            urgency=urgency,
            confidence=0.96,
            incident_type=incident_type,
            situational_summary=summary,
            extracted_entities=entities,
            threat_assessment=threat_assessment,
            reasoning=f"Agent parsed trigger '{request.trigger_source}' with inputs '{raw_text or 'One-Tap Panic'}' and classified threat profile as {urgency.value}."
        )
        
        plan = AgentPlan(
            workflow_id=workflow_id,
            workflow_name=workflow_names.get(incident_type, "Standard Emergency Protocol"),
            priority_action="Dispatch high-priority SMS/Email alerts to Tier-1 contacts & stream live GPS coordinates.",
            target_contacts=[],
            notification_message=notification_msg,
            guidance_steps=guidance,
            escalation_policy={
                "tier1_timeout_seconds": settings.tier1_escalation_seconds,
                "tier2_timeout_seconds": settings.tier2_escalation_seconds,
                "escalate_to": f"Tier 2 Contacts and Emergency Response System ({settings.emergency_police})"
            },
            silent_mode_recommended=is_covert,
            siren_recommended=siren_rec
        )
        
        return understanding, plan
