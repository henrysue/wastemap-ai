/* WasteMap AI — Dashboard */
'use strict';

const WASTE_COLORS = {
  msw: '#6366f1', hazardous: '#ef4444', organic: '#22c55e',
  recyclable: '#3b82f6', liquid: '#06b6d4', ewaste: '#f59e0b',
  cd: '#8b5cf6', medical: '#ec4899', gaseous: '#64748b',
};

const WASTE_LABELS = {
  msw: 'MSW', hazardous: 'Hazardous', organic: 'Organic',
  recyclable: 'Recyclable', liquid: 'Liquid', ewaste: 'E-waste',
  cd: 'C&D Debris', medical: 'Medical', gaseous: 'Gaseous',
};

let wasteChart = null;

async function loadStats() {
  try {
    const res = await fetch('/api/waste-stats/');
    const data = await res.json();
    const keys = Object.keys(data);
    const values = keys.map(k => data[k]);
    const colors = keys.map(k => WASTE_COLORS[k] || '#888');
    const labels = keys.map(k => WASTE_LABELS[k] || k);

    if (wasteChart) {
      wasteChart.data.labels = labels;
      wasteChart.data.datasets[0].data = values;
      wasteChart.data.datasets[0].backgroundColor = colors;
      wasteChart.update();
    } else {
      const ctx = document.getElementById('wasteChart').getContext('2d');
      wasteChart = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2 }] },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}` } },
          },
        },
      });
    }
  } catch (e) {
    console.error('Failed to load waste stats:', e);
  }
}

async function loadRecent() {
  try {
    const res = await fetch('/api/recent-items/');
    const { items } = await res.json();
    const tbody = document.getElementById('recentTableBody');
    if (!tbody) return;
    tbody.innerHTML = items.map(item => `
      <tr>
        <td><span class="badge badge-${item.waste_type}">${escapeHTML(item.waste_type_label)}</span></td>
        <td>${escapeHTML(item.properties_label)}</td>
        <td>${(item.confidence * 100).toFixed(0)}%</td>
        <td>${escapeHTML(item.section)}</td>
        <td class="text-muted small">${escapeHTML(item.timestamp)}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to load recent items:', e);
  }
}

function escapeHTML(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function startCountdown() {
  let remaining = 30;
  const badge = document.getElementById('refreshBadge');
  const intervalId = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      remaining = 30;
      loadStats();
      loadRecent();
    }
    if (badge) badge.textContent = `Auto-refresh: ${remaining}s`;
  }, 1000);
  return intervalId;
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadRecent();
  startCountdown();
});
