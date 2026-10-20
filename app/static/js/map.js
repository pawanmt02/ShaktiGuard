/**
 * ShaktiGuard Leaflet Map Subsystem
 * Interactive live GPS tracking, accuracy pulse, and nearby Safe Havens
 */

class EmergencyMapController {
  constructor() {
    this.map = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.havenLayerGroup = null;
    this.breadcrumbPolyline = null;
    this.breadcrumbs = [];
    this.showBreadcrumbs = true;
    this.currentLat = 12.9716;
    this.currentLng = 77.5946;
  }

  initMap(containerId = "emergency-map") {
    const el = document.getElementById(containerId);
    if (!el || this.map) return;

    // Default center (e.g. Bangalore center, auto-updates on GPS locate)
    this.map = L.map(containerId, {
      center: [this.currentLat, this.currentLng],
      zoom: 15,
      zoomControl: true
    });

    // Dark-themed tiles from CartoDB or standard OSM
    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19
    }).addTo(this.map);

    this.havenLayerGroup = L.layerGroup().addTo(this.map);

    // Initial user location marker
    this.updateUserPosition(this.currentLat, this.currentLng, 12);
  }

  updateUserPosition(lat, lng, accuracy = 10, pan = true) {
    this.currentLat = lat;
    this.currentLng = lng;

    if (!this.map) return;

    // Custom glowing red emergency marker
    const userIcon = L.divIcon({
      className: "custom-user-icon",
      html: `
        <div style="
          width: 20px; height: 20px;
          background: #ef4444;
          border: 3px solid #ffffff;
          border-radius: 50%;
          box-shadow: 0 0 14px rgba(239, 68, 68, 0.9);
        "></div>
      `,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    if (this.userMarker) {
      this.userMarker.setLatLng([lat, lng]);
    } else {
      this.userMarker = L.marker([lat, lng], { icon: userIcon }).addTo(this.map);
      this.userMarker.bindPopup("<strong>You are here</strong><br>Live GPS Streaming Active");
    }

    if (this.accuracyCircle) {
      this.accuracyCircle.setLatLng([lat, lng]);
      this.accuracyCircle.setRadius(accuracy);
    } else {
      this.accuracyCircle = L.circle([lat, lng], {
        radius: accuracy,
        color: "#ef4444",
        fillColor: "#ef4444",
        fillOpacity: 0.15,
        weight: 1
      }).addTo(this.map);
    }

    // Add to breadcrumb trail
    this.breadcrumbs.push([lat, lng]);
    if (this.breadcrumbPolyline) {
      this.breadcrumbPolyline.setLatLngs(this.breadcrumbs);
    } else {
      this.breadcrumbPolyline = L.polyline(this.breadcrumbs, {
        color: "#38bdf8",
        weight: 3,
        dashArray: "5, 5",
        opacity: 0.7
      }).addTo(this.map);
    }

    if (pan) {
      this.map.panTo([lat, lng]);
    }
  }

  renderSafeHavens(havens) {
    if (!this.map || !this.havenLayerGroup) return;
    this.havenLayerGroup.clearLayers();

    if (!havens || havens.length === 0) return;

    havens.forEach(h => {
      let iconColor = "#3b82f6";
      let iconEmoji = "🛡️";

      if (h.type === "POLICE") {
        iconColor = "#2563eb";
        iconEmoji = "🚓";
      } else if (h.type === "HOSPITAL") {
        iconColor = "#dc2626";
        iconEmoji = "🏥";
      } else if (h.type === "PHARMACY") {
        iconColor = "#059669";
        iconEmoji = "💊";
      }

      const havenIcon = L.divIcon({
        className: "custom-haven-icon",
        html: `
          <div style="
            background: ${iconColor};
            color: #ffffff;
            width: 28px; height: 28px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 14px;
            border: 2px solid #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
          ">${iconEmoji}</div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker([h.latitude, h.longitude], { icon: havenIcon });
      marker.bindPopup(`
        <div style="font-size:12px;">
          <strong>${h.name}</strong><br>
          <em>${h.address}</em><br>
          Distance: <strong>~${h.estimated_distance_meters}m</strong><br>
          <a href="tel:${h.phone.split('/')[0].trim()}" style="color:#2563eb; font-weight:700;">📞 Call ${h.phone}</a>
        </div>
      `);
      this.havenLayerGroup.addLayer(marker);
    });
  }

  recenter() {
    if (this.map && this.currentLat && this.currentLng) {
      this.map.setView([this.currentLat, this.currentLng], 16);
    }
  }

  toggleBreadcrumbs() {
    this.showBreadcrumbs = !this.showBreadcrumbs;
    if (this.breadcrumbPolyline) {
      if (this.showBreadcrumbs) {
        this.breadcrumbPolyline.addTo(this.map);
      } else {
        this.map.removeLayer(this.breadcrumbPolyline);
      }
    }
  }
}

window.emergencyMap = new EmergencyMapController();
