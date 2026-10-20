/**
 * ShaktiGuard Main Application Controller
 */

class ShaktiApp {
  constructor() {
    this.activeSession = null;
    this.currentLocation = {
      latitude: 12.9716,
      longitude: 77.5946,
      accuracy: 10,
      address: "MG Road, Bengaluru"
    };
    this.batteryLevel = 85;
    this.graceCountdownInterval = null;
    this.elapsedTimerInterval = null;
    this.pollInterval = null;
    this.holdTimer = null;
    this.isHolding = false;

    this.init();
  }

  async init() {
    this.initTabs();
    this.initGeolocation();
    this.initBattery();
    this.initSOSButtons();
    this.initVoiceAndChips();
    this.initCommandControls();
    this.initContactsManager();
    this.initSettings();

    // Initialize Map on first render
    window.emergencyMap.initMap();

    // Check for existing active session & contacts
    await this.loadContacts();
    await this.refreshActiveSession();

    // Start background sync poll
    this.pollInterval = setInterval(() => {
      this.refreshActiveSession();
    }, 3000);
  }

  // ================= 1. TAB ROUTING =================
  initTabs() {
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        const tabId = tab.getAttribute("data-tab");
        this.switchTab(tabId);
      });
    });
  }

  switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

    const targetTab = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
    const targetPanel = document.getElementById(tabId);

    if (targetTab && targetPanel) {
      targetTab.classList.add("active");
      targetPanel.classList.add("active");

      // Invalidate Leaflet map size on tab show
      if (tabId === "tab-command") {
        setTimeout(() => {
          if (window.emergencyMap.map) {
            window.emergencyMap.map.invalidateSize();
            window.emergencyMap.recenter();
          }
        }, 150);
      }
    }
  }

  // ================= 2. GEOLOCATION & BATTERY =================
  initGeolocation() {
    const locPreview = document.getElementById("current-location-preview");
    if (!navigator.geolocation) {
      if (locPreview) locPreview.innerText = "GPS: Bangalore Center (Default)";
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.currentLocation.latitude = pos.coords.latitude;
        this.currentLocation.longitude = pos.coords.longitude;
        this.currentLocation.accuracy = pos.coords.accuracy || 10;
        
        window.emergencyMap.updateUserPosition(
          pos.coords.latitude,
          pos.coords.longitude,
          pos.coords.accuracy || 10
        );

        if (locPreview) {
          locPreview.innerText = `GPS: Lat ${pos.coords.latitude.toFixed(4)}, Lng ${pos.coords.longitude.toFixed(4)} (±${Math.round(pos.coords.accuracy || 10)}m)`;
        }
      },
      (err) => {
        console.warn("Geolocation warning/permission denied:", err.message);
        if (locPreview) locPreview.innerText = "GPS: Indiranagar, Bengaluru (Demo Anchor)";
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  }

  async initBattery() {
    try {
      if ('getBattery' in navigator) {
        const battery = await navigator.getBattery();
        this.batteryLevel = Math.round(battery.level * 100);
        const display = document.getElementById("battery-level-display");
        if (display) display.innerText = `Battery: ${this.batteryLevel}%`;

        battery.addEventListener('levelchange', () => {
          this.batteryLevel = Math.round(battery.level * 100);
          if (display) display.innerText = `Battery: ${this.batteryLevel}%`;
        });
      }
    } catch (e) {
      console.debug("Battery API not accessible:", e);
    }
  }

  // ================= 3. SOS BUTTON & SAFEGUARD FLOW =================
  initSOSButtons() {
    const btnSOS = document.getElementById("btn-sos-trigger");
    if (!btnSOS) return;

    // Click / Tap -> Standard SOS with 5-sec grace window
    btnSOS.addEventListener("click", () => {
      if (!this.isHolding) {
        this.triggerDistressFlow(false);
      }
    });

    // Hold 2 Seconds -> Covert / Silent SOS
    const startHold = () => {
      this.isHolding = false;
      this.holdTimer = setTimeout(() => {
        this.isHolding = true;
        btnSOS.style.transform = "scale(0.92)";
        this.triggerDistressFlow(true); // Covert mode
      }, 1800);
    };

    const clearHold = () => {
      clearTimeout(this.holdTimer);
      btnSOS.style.transform = "";
      setTimeout(() => { this.isHolding = false; }, 200);
    };

    btnSOS.addEventListener("mousedown", startHold);
    btnSOS.addEventListener("touchstart", startHold);
    btnSOS.addEventListener("mouseup", clearHold);
    btnSOS.addEventListener("mouseleave", clearHold);
    btnSOS.addEventListener("touchend", clearHold);

    // Keyboard Spacebar listener
    window.addEventListener("keydown", (e) => {
      if (e.code === "Space" && e.target.tagName !== "INPUT" && !this.graceCountdownInterval) {
        e.preventDefault();
        this.triggerDistressFlow(false);
      }
    });

    // Safeguard Modal Action Buttons
    document.getElementById("btn-cancel-safeguard").addEventListener("click", () => {
      this.cancelSafeguard();
    });

    document.getElementById("btn-instant-confirm-safeguard").addEventListener("click", () => {
      this.confirmEmergencyImmediately();
    });

    document.getElementById("btn-send-context-sos").addEventListener("click", () => {
      this.triggerDistressFlow(false);
    });
  }

  async triggerDistressFlow(isCovert = false) {
    const inputVal = document.getElementById("input-distress-text").value.trim();
    const covertCheckbox = document.getElementById("covert-mode-checkbox");
    const covertFinal = isCovert || (covertCheckbox && covertCheckbox.checked);

    const payload = {
      trigger_source: covertFinal ? "COVERT_HOLD" : (inputVal ? "TEXT_CONTEXT" : "SOS_BUTTON"),
      input_text: inputVal,
      location: this.currentLocation,
      battery_level: this.batteryLevel,
      is_covert: covertFinal
    };

    try {
      // Create session in grace period
      const res = await fetch("/api/emergency/trigger?immediate=false", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        this.activeSession = await res.json();
        this.openSafeguardModal(5);
      }
    } catch (e) {
      console.error("SOS Trigger Error:", e);
      alert("Error initiating SOS: " + e.message);
    }
  }

  openSafeguardModal(seconds = 5) {
    const modal = document.getElementById("modal-grace-safeguard");
    const numDisplay = document.getElementById("grace-seconds-count");
    const labelDisplay = document.getElementById("grace-time-label");
    const circleBar = document.getElementById("grace-circle-bar");

    if (!modal) return;
    modal.style.display = "flex";

    let remaining = seconds;
    const totalCircumference = 283;

    if (numDisplay) numDisplay.innerText = remaining;
    if (labelDisplay) labelDisplay.innerText = remaining;
    if (circleBar) circleBar.style.strokeDashoffset = 0;

    clearInterval(this.graceCountdownInterval);
    this.graceCountdownInterval = setInterval(() => {
      remaining -= 1;
      if (numDisplay) numDisplay.innerText = remaining;
      if (labelDisplay) labelDisplay.innerText = remaining;

      if (circleBar) {
        const offset = totalCircumference - (remaining / seconds) * totalCircumference;
        circleBar.style.strokeDashoffset = offset;
      }

      if (remaining <= 0) {
        clearInterval(this.graceCountdownInterval);
        this.graceCountdownInterval = null;
        this.confirmEmergencyImmediately();
      }
    }, 1000);
  }

  async cancelSafeguard() {
    clearInterval(this.graceCountdownInterval);
    this.graceCountdownInterval = null;

    const modal = document.getElementById("modal-grace-safeguard");
    if (modal) modal.style.display = "none";

    if (this.activeSession) {
      try {
        await fetch(`/api/emergency/${this.activeSession.id}/cancel?reason=Accidental+trigger+aborted+by+user`, {
          method: "POST"
        });
        alert("Distress signal cancelled. Contacts have not been alerted.");
      } catch (e) {
        console.error("Cancel error:", e);
      }
    }
    await this.refreshActiveSession();
  }

  async confirmEmergencyImmediately() {
    clearInterval(this.graceCountdownInterval);
    this.graceCountdownInterval = null;

    const modal = document.getElementById("modal-grace-safeguard");
    if (modal) modal.style.display = "none";

    if (!this.activeSession) return;

    try {
      const res = await fetch(`/api/emergency/${this.activeSession.id}/confirm`, {
        method: "POST"
      });
      if (res.ok) {
        this.activeSession = await res.json();
        this.switchTab("tab-command");
        await this.refreshActiveSession();
      }
    } catch (e) {
      console.error("Confirm error:", e);
    }
  }

  // ================= 4. VOICE & CHIPS =================
  initVoiceAndChips() {
    const micBtn = document.getElementById("btn-voice-toggle");
    const wave = document.getElementById("audio-wave");
    const input = document.getElementById("input-distress-text");

    if (micBtn) {
      micBtn.addEventListener("click", () => {
        if (window.agentAudio.isRecording) {
          window.agentAudio.stopListening();
          micBtn.classList.remove("recording");
          if (wave) wave.style.display = "none";
        } else {
          micBtn.classList.add("recording");
          if (wave) wave.style.display = "flex";
          window.agentAudio.startListening(
            (transcript) => {
              if (input) input.value = transcript;
            },
            () => {
              micBtn.classList.remove("recording");
              if (wave) wave.style.display = "none";
            }
          );
        }
      });
    }

    // Quick chips
    document.querySelectorAll(".chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const text = chip.getAttribute("data-text");
        if (input) input.value = text;
      });
    });
  }

  // ================= 5. INCIDENT COMMAND CONTROLS =================
  initCommandControls() {
    // Siren
    const btnSiren = document.getElementById("btn-sound-siren");
    const sirenLabel = document.getElementById("siren-state-text");
    if (btnSiren) {
      btnSiren.addEventListener("click", () => {
        window.agentAudio.toggleSiren(sirenLabel);
      });
    }

    // Strobe
    const btnStrobe = document.getElementById("btn-screen-strobe");
    const strobeLabel = document.getElementById("strobe-state-text");
    const strobeOverlay = document.getElementById("screen-strobe-overlay");
    if (btnStrobe) {
      btnStrobe.addEventListener("click", () => {
        window.agentAudio.toggleStrobe(strobeOverlay, strobeLabel);
      });
    }

    // Voice guide (TTS)
    const btnTTS = document.getElementById("btn-tts-guide");
    const ttsLabel = document.getElementById("tts-state-text");
    if (btnTTS) {
      btnTTS.addEventListener("click", () => {
        const steps = this.activeSession && this.activeSession.plan ? this.activeSession.plan.guidance_steps : [];
        window.agentAudio.speakGuidance(steps, ttsLabel);
      });
    }

    // Mark safe & resolve
    const btnResolve = document.getElementById("btn-resolve-incident");
    if (btnResolve) {
      btnResolve.addEventListener("click", async () => {
        if (!this.activeSession) {
          alert("No active incident to resolve.");
          return;
        }
        if (confirm("Confirm that you are safe and want to resolve this emergency incident?")) {
          try {
            await fetch(`/api/emergency/${this.activeSession.id}/resolve?notes=User+marked+safe+from+dashboard`, {
              method: "POST"
            });
            window.agentAudio.stopSiren();
            if (sirenLabel) sirenLabel.innerText = "OFF";
            alert("Incident marked resolved. Response teams stand down.");
            await this.refreshActiveSession();
          } catch (e) {
            console.error("Resolve error:", e);
          }
        }
      });
    }

    // Map controls
    const btnRecenter = document.getElementById("btn-recenter-map");
    if (btnRecenter) btnRecenter.addEventListener("click", () => window.emergencyMap.recenter());

    const btnBreadcrumb = document.getElementById("btn-toggle-breadcrumbs");
    if (btnBreadcrumb) btnBreadcrumb.addEventListener("click", () => window.emergencyMap.toggleBreadcrumbs());

    const btnRefreshTimeline = document.getElementById("btn-refresh-timeline");
    if (btnRefreshTimeline) btnRefreshTimeline.addEventListener("click", () => this.refreshActiveSession());
  }

  // ================= 6. ACTIVE SESSION SYNC & RENDER =================
  async refreshActiveSession() {
    try {
      const res = await fetch("/api/emergency/active");
      if (res.ok) {
        const data = await res.json();
        this.activeSession = data.session;
        this.renderActiveSession(data.session, data.timeline, data.notifications, data.safe_havens);
      }
    } catch (e) {
      console.debug("Active session fetch error:", e);
    }
  }

  renderActiveSession(session, timeline, notifications, safeHavens) {
    const badgeIncident = document.getElementById("badge-incident");
    const cmdId = document.getElementById("cmd-incident-id");
    const cmdStatus = document.getElementById("cmd-incident-status");
    const cmdType = document.getElementById("cmd-incident-type");
    const cmdConfidence = document.getElementById("cmd-confidence");
    const cmdWorkflow = document.getElementById("cmd-workflow-name");
    const cmdSummary = document.getElementById("cmd-summary-text");
    const cmdThreat = document.getElementById("cmd-threat-text");
    const cmdUrgencyPill = document.getElementById("cmd-urgency-pill");
    const cmdSafetySteps = document.getElementById("cmd-safety-steps");
    const cmdTierBadge = document.getElementById("cmd-active-tier");
    const cmdEscalationTimer = document.getElementById("cmd-escalation-timer");
    const cmdMapAddress = document.getElementById("cmd-map-address");

    if (!session) {
      if (badgeIncident) badgeIncident.style.display = "none";
      if (cmdId) cmdId.innerText = "No Active Incident";
      if (cmdStatus) {
        cmdStatus.className = "incident-status-badge status-idle";
        cmdStatus.innerText = "IDLE";
      }
      return;
    }

    // Top Bar
    const isActive = session.status === "ACTIVE" || session.status.startsWith("ESCALATED");
    if (badgeIncident) badgeIncident.style.display = isActive ? "inline" : "none";
    if (cmdId) cmdId.innerText = session.id;

    if (cmdStatus) {
      cmdStatus.className = `incident-status-badge status-${session.status.toLowerCase()}`;
      cmdStatus.innerText = session.status.replace(/_/g, " ");
    }

    // Elapsed Timer
    this.updateElapsedTimer(session.created_at);

    // AI Understanding
    if (session.understanding) {
      const und = session.understanding;
      if (cmdType) cmdType.innerText = und.incident_type.replace(/_/g, " ");
      if (cmdConfidence) cmdConfidence.innerText = `${(und.confidence * 100).toFixed(0)}%`;
      if (cmdSummary) cmdSummary.innerText = und.situational_summary;
      if (cmdThreat) cmdThreat.innerText = und.threat_assessment;

      if (cmdUrgencyPill) {
        cmdUrgencyPill.innerText = und.urgency;
        cmdUrgencyPill.className = `urgency-pill pill-${und.urgency.toLowerCase()}`;
      }
    }

    // Plan & Guidance
    if (session.plan) {
      const plan = session.plan;
      if (cmdWorkflow) cmdWorkflow.innerText = plan.workflow_name;

      if (cmdSafetySteps && plan.guidance_steps) {
        cmdSafetySteps.innerHTML = plan.guidance_steps.map(step => `<li>${step}</li>`).join("");
      }
    }

    // Active Tier & Escalation
    if (cmdTierBadge) {
      cmdTierBadge.innerText = `Tier ${session.active_tier}: ${session.active_tier === 1 ? 'Primary' : session.active_tier === 2 ? 'Secondary' : 'Emergency Services'}`;
    }

    // Map & Safe Havens
    if (session.location) {
      if (cmdMapAddress) cmdMapAddress.innerText = session.location.address || "Live GPS Location";
      window.emergencyMap.updateUserPosition(
        session.location.latitude,
        session.location.longitude,
        session.location.accuracy || 10,
        false
      );
    }

    if (safeHavens) {
      this.renderSafeHavensList(safeHavens);
      window.emergencyMap.renderSafeHavens(safeHavens);
    }

    // Timeline
    this.renderTimeline(timeline);

    // Sync Responder Portal view
    window.responderPortal.setSession(session, notifications);
  }

  updateElapsedTimer(startTimeIso) {
    if (!startTimeIso) return;
    const start = new Date(startTimeIso).getTime();
    const timerEl = document.getElementById("cmd-elapsed-timer");
    if (!timerEl) return;

    const update = () => {
      const diffSec = Math.floor((Date.now() - start) / 1000);
      const mins = String(Math.floor(diffSec / 60)).padStart(2, "0");
      const secs = String(diffSec % 60).padStart(2, "0");
      timerEl.innerText = `⏱️ ${mins}:${secs}`;
    };

    update();
    clearInterval(this.elapsedTimerInterval);
    this.elapsedTimerInterval = setInterval(update, 1000);
  }

  renderSafeHavensList(havens) {
    const list = document.getElementById("cmd-safe-havens-list");
    if (!list) return;

    if (!havens || havens.length === 0) {
      list.innerHTML = `<div style="font-size:11px; color:#64748b;">No safe havens nearby.</div>`;
      return;
    }

    list.innerHTML = havens.slice(0, 3).map(h => `
      <div class="haven-item">
        <div>
          <span class="haven-name">${h.name}</span>
          <div style="font-size:10px; color:#94a3b8;">${h.address}</div>
        </div>
        <span class="haven-dist">~${h.estimated_distance_meters}m</span>
      </div>
    `).join("");
  }

  renderTimeline(timeline) {
    const feed = document.getElementById("cmd-timeline-feed");
    if (!feed) return;

    if (!timeline || timeline.length === 0) {
      feed.innerHTML = `<div class="timeline-empty">Standby. No events recorded yet.</div>`;
      return;
    }

    feed.innerHTML = timeline.map(e => {
      const relSec = e.relative_seconds ? `+${e.relative_seconds}s` : "0.0s";
      return `
        <div class="timeline-item t-${e.event_type.toLowerCase()}">
          <div class="t-time">${relSec}</div>
          <div class="t-content">
            <strong>${e.title}</strong>
            <p>${e.details}</p>
          </div>
        </div>
      `;
    }).join("");
  }

  // ================= 7. CONTACTS MANAGER =================
  initContactsManager() {
    const btnOpen = document.getElementById("btn-open-add-contact");
    const modal = document.getElementById("modal-add-contact");
    const btnClose = document.getElementById("btn-close-contact-modal");
    const btnCancel = document.getElementById("btn-cancel-contact");
    const form = document.getElementById("form-add-contact");

    if (btnOpen) btnOpen.addEventListener("click", () => modal.style.display = "flex");
    if (btnClose) btnClose.addEventListener("click", () => modal.style.display = "none");
    if (btnCancel) btnCancel.addEventListener("click", () => modal.style.display = "none");

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const contactData = {
          name: document.getElementById("contact-name").value.trim(),
          phone: document.getElementById("contact-phone").value.trim(),
          email: document.getElementById("contact-email").value.trim() || null,
          relationship: document.getElementById("contact-rel").value.trim() || "Contact",
          tier: parseInt(document.getElementById("contact-tier").value),
          notify_sms: document.getElementById("contact-sms").checked,
          notify_email: document.getElementById("contact-notify-email").checked,
          notify_call: document.getElementById("contact-call").checked
        };

        try {
          const res = await fetch("/api/contacts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(contactData)
          });
          if (res.ok) {
            form.reset();
            modal.style.display = "none";
            await this.loadContacts();
          }
        } catch (err) {
          console.error("Save contact error:", err);
        }
      });
    }
  }

  async loadContacts() {
    try {
      const res = await fetch("/api/contacts");
      if (res.ok) {
        const contacts = await res.json();
        this.renderContactsTiers(contacts);
        window.responderPortal.loadContacts(contacts);
      }
    } catch (e) {
      console.error("Failed to load contacts:", e);
    }
  }

  renderContactsTiers(contacts) {
    const t1 = document.getElementById("contacts-tier-1");
    const t2 = document.getElementById("contacts-tier-2");
    const t3 = document.getElementById("contacts-tier-3");

    if (t1) t1.innerHTML = "";
    if (t2) t2.innerHTML = "";
    if (t3) t3.innerHTML = "";

    contacts.forEach(c => {
      const card = document.createElement("div");
      card.className = "contact-card";
      card.innerHTML = `
        <div class="contact-info">
          <div class="contact-name">${c.name}</div>
          <div class="contact-meta">${c.relationship} • ${c.phone}</div>
        </div>
        <div class="contact-channels">
          ${c.notify_sms ? '<span title="SMS Active">💬</span>' : ''}
          ${c.notify_email ? '<span title="Email Active">✉️</span>' : ''}
          ${c.notify_call ? '<span title="RoboCall Active">📞</span>' : ''}
          <button class="btn-del-contact" data-id="${c.id}" title="Remove">&times;</button>
        </div>
      `;

      card.querySelector(".btn-del-contact").addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        if (confirm(`Remove ${c.name} from emergency contacts?`)) {
          await fetch(`/api/contacts/${id}`, { method: "DELETE" });
          await this.loadContacts();
        }
      });

      if (c.tier === 1 && t1) t1.appendChild(card);
      else if (c.tier === 2 && t2) t2.appendChild(card);
      else if (c.tier === 3 && t3) t3.appendChild(card);
    });
  }

  // ================= 8. SETTINGS =================
  initSettings() {
    const btnSaveKey = document.getElementById("btn-save-gemini-key");
    const btnSaveAll = document.getElementById("btn-save-all-settings");

    const saveSettings = async () => {
      const keyInput = document.getElementById("setting-gemini-key").value;
      const grace = parseInt(document.getElementById("setting-grace-sec").value);
      const tier1 = parseInt(document.getElementById("setting-tier1-sec").value);
      const tier2 = parseInt(document.getElementById("setting-tier2-sec").value);

      try {
        const res = await fetch("/api/system/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            gemini_api_key: keyInput ? keyInput : null,
            grace_period_seconds: grace,
            tier1_escalation_seconds: tier1,
            tier2_escalation_seconds: tier2
          })
        });

        if (res.ok) {
          alert("Settings updated successfully!");
        }
      } catch (e) {
        console.error("Settings error:", e);
      }
    };

    if (btnSaveKey) btnSaveKey.addEventListener("click", saveSettings);
    if (btnSaveAll) btnSaveAll.addEventListener("click", saveSettings);
  }
}

// Instantiate App on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.shaktiApp = new ShaktiApp();
});
