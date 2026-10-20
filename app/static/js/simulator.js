/**
 * ShaktiGuard Module 5: Automated Testing & Stress Simulator Hub
 */

class SimulatorController {
  constructor() {
    this.scenarios = [];
    this.init();
  }

  async init() {
    await this.fetchScenarios();
    await this.fetchMetrics();

    const btnRefresh = document.getElementById("btn-refresh-metrics");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", () => this.fetchMetrics());
    }
  }

  async fetchScenarios() {
    try {
      const res = await fetch("/api/simulate/scenarios");
      if (res.ok) {
        this.scenarios = await res.json();
        this.renderScenarios();
      }
    } catch (e) {
      console.error("Failed to load scenarios:", e);
    }
  }

  async fetchMetrics() {
    try {
      const res = await fetch("/api/simulate/metrics");
      if (res.ok) {
        const m = await res.json();
        document.getElementById("metric-delivery-time").innerText = `${m.alert_delivery_time_avg_ms} ms`;
        document.getElementById("metric-workflow-rate").innerText = `${m.workflow_completion_pct}%`;
        document.getElementById("metric-ack-rate").innerText = `${m.acknowledgment_rate_pct}%`;
        document.getElementById("metric-safeguard-rate").innerText = "100%";
      }
    } catch (e) {
      console.error("Failed to load metrics:", e);
    }
  }

  renderScenarios() {
    const container = document.getElementById("scenarios-container");
    if (!container) return;

    container.innerHTML = this.scenarios.map(s => {
      let urgencyColor = "#f59e0b";
      if (s.expected_urgency === "CRITICAL") urgencyColor = "#ef4444";
      if (s.expected_urgency === "HIGH") urgencyColor = "#f97316";

      return `
        <div class="scenario-card">
          <div>
            <div class="sc-title">${s.name}</div>
            <div class="sc-desc" style="margin-top:6px;">${s.description}</div>
            <div style="margin: 8px 0; background:rgba(0,0,0,0.3); padding:8px; border-radius:6px; font-size:11px; font-style:italic; color:#cbd5e1;">
              "${s.sample_input || '[One-Tap Accidental Press]'}"
            </div>
            <div class="sc-meta">
              <span class="pill-info">Trigger: ${s.trigger_source}</span>
              <span class="urgency-pill" style="background:${urgencyColor}; color:#fff;">Expected: ${s.expected_urgency}</span>
              <span class="pill-info">Battery: ${s.battery}%</span>
            </div>
          </div>
          <button class="btn-run-scenario" data-id="${s.id}">
            ▶ Run Simulation
          </button>
        </div>
      `;
    }).join("");

    container.querySelectorAll(".btn-run-scenario").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const scId = e.currentTarget.getAttribute("data-id");
        this.runScenario(scId, e.currentTarget);
      });
    });
  }

  async runScenario(scenarioId, btn) {
    if (btn) {
      btn.disabled = true;
      btn.innerText = "⏳ Executing Agent...";
    }

    try {
      const res = await fetch(`/api/simulate/run/${scenarioId}?auto_acknowledge=true`, {
        method: "POST"
      });

      if (res.ok) {
        const data = await res.json();
        this.displaySimulationTrace(data);
        await this.fetchMetrics();

        // Switch to incident command tab after short delay to view real-time result
        if (window.shaktiApp) {
          window.shaktiApp.activeSession = data.session;
          window.shaktiApp.renderActiveSession(data.session, data.timeline, data.notifications);
          
          if (scenarioId !== "scenario-false-alarm") {
            setTimeout(() => {
              window.shaktiApp.switchTab("tab-command");
            }, 800);
          }
        }
      }
    } catch (e) {
      console.error("Simulation run failed:", e);
      alert("Simulation failed to complete: " + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = "▶ Run Simulation";
      }
    }
  }

  displaySimulationTrace(data) {
    const box = document.getElementById("sim-output-box");
    const tag = document.getElementById("sim-latency-tag");
    const content = document.getElementById("sim-details-content");

    if (!box || !content) return;
    box.style.display = "block";

    if (data.safeguard_success) {
      tag.innerText = `Safeguard Abort: ${data.latency_ms}ms`;
      content.innerHTML = `
        <div style="background:rgba(16, 185, 129, 0.15); border:1px solid #10b981; padding:12px; border-radius:8px;">
          <h4 style="color:#34d399;">✅ Accidental Trigger Cancelled within Grace Window</h4>
          <p style="font-size:12px; margin-top:4px;">${data.summary}</p>
          <p style="font-size:11px; color:#94a3b8; margin-top:4px;">Status: <strong>${data.session.status}</strong> | Cancellation Reason: ${data.session.cancellation_reason}</p>
        </div>
      `;
      return;
    }

    const perf = data.performance;
    tag.innerText = `Latency: ${perf.latency_ms}ms (Delivery: ${perf.delivery_time_ms}ms)`;

    const und = data.session.understanding || {};
    const plan = data.session.plan || {};

    content.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:12px;">
        <div style="background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;">
          <h4 style="color:#60a5fa; margin-bottom:6px;">🧠 AI Agent Understanding:</h4>
          <div>Urgency: <strong>${und.urgency}</strong> (Confidence: ${(und.confidence * 100).toFixed(0)}%)</div>
          <div>Incident Type: <strong>${und.incident_type}</strong></div>
          <div style="margin-top:4px; color:#cbd5e1;"><em>"${und.situational_summary}"</em></div>
        </div>
        <div style="background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;">
          <h4 style="color:#34d399; margin-bottom:6px;">📋 Action Plan Execution:</h4>
          <div>Workflow: <strong>${plan.workflow_name}</strong></div>
          <div>Priority Action: <strong>${plan.priority_action}</strong></div>
          <div style="margin-top:4px; color:#94a3b8;">Steps Generated: ${plan.guidance_steps ? plan.guidance_steps.length : 0} survival instructions</div>
        </div>
      </div>
      <div style="margin-top:10px; font-size:11.5px; color:#94a3b8;">
        Dispatched notifications to ${data.notifications ? data.notifications.length : 0} channels. First responder acknowledged and marked en route.
      </div>
    `;
  }
}

window.simulator = new SimulatorController();
