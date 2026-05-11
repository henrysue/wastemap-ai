/* WasteMap AI — GeoMap (heatmap mode) */
'use strict';

const WASTE_LABELS_MAP = {
  msw: 'MSW', hazardous: 'Hazardous', organic: 'Organic',
  recyclable: 'Recyclable', liquid: 'Liquid', ewaste: 'E-waste',
  cd: 'C&D Debris', medical: 'Medical', gaseous: 'Gaseous',
};

async function initMap() {
  const map = L.map('map').setView([34.0195, -118.4912], 12);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map);

  try {
    const res = await fetch('/api/geomap-data/');
    const { subsections } = await res.json();

    if (!subsections.length) return;

    const maxCount = subsections.reduce((m, s) => Math.max(m, s.total), 0) || 1;

    // Heat layer — weighted by per-subsection item count.
    const heatPoints = subsections
      .filter(s => s.total > 0)
      .map(s => [s.latitude, s.longitude, s.total / maxCount]);

    const heatLayer = L.heatLayer(heatPoints, {
      radius: 35,
      blur: 25,
      maxZoom: 13,
      max: 1.0,
      minOpacity: 0.35,
      gradient: {
        0.2: '#4a6275',  // slate blue (low)
        0.4: '#2e7d4f',  // forest
        0.6: '#a37c19',  // ochre
        0.8: '#a02c2c',  // brick (high)
      },
    }).addTo(map);

    // leaflet.heat renders to a canvas that doesn't transform with the map
    // during animated pan/zoom — hide it mid-animation, redraw on completion.
    map.on('movestart zoomstart', () => {
      if (heatLayer._canvas) heatLayer._canvas.style.visibility = 'hidden';
    });
    map.on('moveend zoomend', () => {
      if (heatLayer._canvas) heatLayer._canvas.style.visibility = '';
      if (typeof heatLayer.redraw === 'function') heatLayer.redraw();
    });

    // Invisible clickable markers so popups still work over the heat layer.
    const clickGroup = L.layerGroup();
    const markersById = {};
    subsections.forEach(sub => {
      const marker = L.circleMarker([sub.latitude, sub.longitude], {
        radius: 10,
        fillColor: '#000',
        color: '#000',
        weight: 0,
        opacity: 0,
        fillOpacity: 0,
      });

      const breakdownRows = Object.entries(sub.breakdown)
        .sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `<tr><td>${WASTE_LABELS_MAP[k] || k}</td><td>${v}</td></tr>`)
        .join('');

      marker.bindPopup(`
        <strong>${sub.name}</strong><br>
        <em>${sub.section}</em><br>
        <b>Total: ${sub.total}</b>
        ${breakdownRows ? `<table class="table table-sm mt-1"><thead><tr><th>Type</th><th>Count</th></tr></thead><tbody>${breakdownRows}</tbody></table>` : '<p class="text-muted mt-1">No items yet</p>'}
      `);
      clickGroup.addLayer(marker);
      markersById[sub.id] = marker;
    });
    clickGroup.addTo(map);

    // Fit to data bounds.
    const bounds = L.latLngBounds(subsections.map(s => [s.latitude, s.longitude]));
    map.fitBounds(bounds.pad(0.15));

    // Wire legend subsection links: fly to location + open popup.
    document.querySelectorAll('.sub-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const lat = parseFloat(link.dataset.lat);
        const lng = parseFloat(link.dataset.lng);
        const id = parseInt(link.dataset.subId, 10);
        if (!isFinite(lat) || !isFinite(lng)) return;
        map.flyTo([lat, lng], 14, { duration: 0.8 });
        const marker = markersById[id];
        if (marker) {
          setTimeout(() => marker.openPopup(), 850);
        }
      });
    });
  } catch (e) {
    console.error('Failed to load geomap data:', e);
  }
}

document.addEventListener('DOMContentLoaded', initMap);
