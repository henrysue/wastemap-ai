/* WasteMap AI — GeoMap */
'use strict';

const WASTE_LABELS_MAP = {
  msw: 'MSW', hazardous: 'Hazardous', organic: 'Organic',
  recyclable: 'Recyclable', liquid: 'Liquid', ewaste: 'E-waste',
  cd: 'C&D Debris', medical: 'Medical', gaseous: 'Gaseous',
};

function getColor(total) {
  if (total === 0) return '#94a3b8';
  if (total < 5) return '#86efac';
  if (total < 20) return '#facc15';
  if (total < 50) return '#fb923c';
  return '#ef4444';
}

function getRadius(total) {
  return Math.max(10, Math.min(50, 10 + total * 0.8));
}

async function initMap() {
  const map = L.map('map').setView([34.0195, -118.4912], 12);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map);

  try {
    const res = await fetch('/api/geomap-data/');
    const { subsections } = await res.json();

    subsections.forEach(sub => {
      const color = getColor(sub.total);
      const radius = getRadius(sub.total);

      const circle = L.circleMarker([sub.latitude, sub.longitude], {
        radius,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
      }).addTo(map);

      const breakdownRows = Object.entries(sub.breakdown)
        .sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `<tr><td>${WASTE_LABELS_MAP[k] || k}</td><td>${v}</td></tr>`)
        .join('');

      circle.bindPopup(`
        <strong>${sub.name}</strong><br>
        <em>${sub.section}</em><br>
        <b>Total: ${sub.total}</b>
        ${breakdownRows ? `<table class="table table-sm mt-1"><thead><tr><th>Type</th><th>Count</th></tr></thead><tbody>${breakdownRows}</tbody></table>` : '<p class="text-muted mt-1">No items yet</p>'}
      `);
    });
  } catch (e) {
    console.error('Failed to load geomap data:', e);
  }
}

document.addEventListener('DOMContentLoaded', initMap);
