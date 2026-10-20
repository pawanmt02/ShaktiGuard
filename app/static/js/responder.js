/**
 * ShaktiGuard Responder Portal & Mock Phone Controller
 * Simulates trusted contact reception & one-tap acknowledgment
 */

class ResponderPortalController {
  constructor() {
    this.currentSessionId = null;
    this.currentContactId = null;
    this.contacts = [];
    this.initEventListeners();
  }

  initEventListeners() {
    const select = document.getElementById("select-responder-contact");
    if (select) {
      select.addEventListener("change", (e) => {
        this.currentContactId = e.target.value;
        this.updateMockPhoneSMS();
      });
    }

    // Acknowledgment buttons in mockup
    document.querySelectorAll(".btn-responder").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const status = e.currentTarget.getAttribute("data-status");
        this.sendAcknowledgment(status);
      });
    });
  }

  async loadContacts(contacts) {
    this.contacts = contacts;
    const select = document.getElementById("select-responder-contact");
    if (!select) return;

    select.innerHTML = "";
    contacts.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.name} (${c.relationship} - Tier ${c.tier})`;
      select.appendChild(opt);
    });

    if (contacts.length > 0 && !this.currentContactId) {
      this.currentContactId = contacts[0].id;
    }
    this.updateMockPhoneSMS();
  }

  setSession(session, notifications) {
    this.currentSessionId = session ? session.id : null;
    this.renderDispatchTable(notifications);
    this.updateMockPhoneSMS();
  }

  updateMockPhoneSMS() {
    const bubble = document.getElementById("mock-sms-content");
    if (!bubble) return;

    const contact = this.contacts.find(c => c.id === this.currentContactId);
    const recipientName = contact ? contact.name : "Trusted Contact";

    if (!this.currentSessionId) {
      bubble.innerHTML = `
        <em>No active emergency alert. Smartphone in normal standby mode.</em>
      `;
      return;
    }

    const session = window.shaktiApp ? window.shaktiApp.activeSession : null;
    const urgency = session && session.understanding ? session.understanding.urgency : "HIGH";
    const incident = session && session.understanding ? session.understanding.incident_type.replace(/_/g, " ") : "Emergency Distress";
    const summary = session && session.understanding ? session.understanding.situational_summary : "User triggered emergency SOS.";
    const addr = session && session.location ? session.location.address : "Live GPS Location";
    const battery = session ? session.battery_level : 85;

    bubble.innerHTML = `
      🚨 <strong>SHAKTIGUARD ${urgency} SOS</strong><br>
      To: <strong>${recipientName}</strong><br>
      User reported: <strong>${incident}</strong><br>
      Context: ${summary}<br>
      Location: ${addr}<br>
      Battery: ${battery}%<br>
      <span class="sms-link">Tap to Respond & Track Live &gt;</span>
    `;
  }

  async sendAcknowledgment(status) {
    if (!this.currentSessionId) {
      alert("No active emergency session to acknowledge.");
      return;
    }

    const noteInput = document.getElementById("responder-custom-note");
    const customNote = noteInput && noteInput.value.trim() ? noteInput.value.trim() : "Responding to alert.";

    const contact = this.contacts.find(c => c.id === this.currentContactId);
    const responderName = contact ? contact.name : "Trusted Contact";

    try {
      const res = await fetch(`/api/responder/acknowledge?session_id=${this.currentSessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact_id: this.currentContactId,
          responder_name: responderName,
          status: status,
          note: customNote
        })
      });

      if (res.ok) {
        if (noteInput) noteInput.value = "";
        alert(`Acknowledgment sent: [${status}] by ${responderName}! The user's screen has been notified.`);
        if (window.shaktiApp) {
          window.shaktiApp.refreshActiveSession();
        }
      }
    } catch (e) {
      console.error("Ack error:", e);
    }
  }

  renderDispatchTable(notifications) {
    const tbody = document.getElementById("dispatch-log-body");
    if (!tbody) return;

    if (!notifications || notifications.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center">No notifications sent for current session.</td></tr>`;
      return;
    }

    tbody.innerHTML = notifications.map(n => {
      const timeStr = new Date(n.sent_at).toLocaleTimeString();
      const statusBadge = n.status === "ACKNOWLEDGED" 
        ? `<span style="color:#34d399; font-weight:700;">ACKNOWLEDGED</span>` 
        : `<span style="color:#60a5fa;">DELIVERED</span>`;
      const ackDetail = n.response_note ? `<small>${n.response_note}</small>` : `<em style="color:#64748b;">Pending</em>`;

      return `
        <tr>
          <td>${timeStr}</td>
          <td><strong>${n.recipient_name}</strong><br><small style="color:#94a3b8;">${n.recipient_phone || n.recipient_email}</small></td>
          <td><span class="pill-info">${n.channel}</span></td>
          <td>${statusBadge}</td>
          <td>${ackDetail}</td>
        </tr>
      `;
    }).join("");
  }
}

window.responderPortal = new ResponderPortalController();
