/* WasteMap AI — Dashboard */
'use strict';

// Government data-viz palette (USWDS / BLS / FRED-inspired): muted earth tones.
const WASTE_COLORS = {
  msw:        '#5b616b', // slate
  hazardous:  '#a02c2c', // brick
  organic:    '#2e7d4f', // forest
  recyclable: '#205493', // navy
  liquid:     '#1f7a87', // teal
  ewaste:     '#a37c19', // ochre
  cd:         '#8a5d3b', // earth brown
  medical:    '#884070', // mulberry
  gaseous:    '#4a6275', // slate blue
};

const WASTE_LABELS = {
  msw: 'MSW', hazardous: 'Hazardous', organic: 'Organic',
  recyclable: 'Recyclable', liquid: 'Liquid', ewaste: 'E-waste',
  cd: 'C&D Debris', medical: 'Medical', gaseous: 'Gaseous',
};

// Reverse lookup so the legend callback can resolve a label → solid color.
const SOLID_FILL_BY_LABEL = Object.fromEntries(
  Object.entries(WASTE_LABELS).map(([k, label]) => [label, WASTE_COLORS[k]])
);

function hexToRgba(hex, alpha) {
  const [r, g, b] = hex.replace('#', '').match(/.{2}/g).map(x => parseInt(x, 16));
  return `rgba(${r},${g},${b},${alpha})`;
}

let wasteChart = null;
let trendsChart = null;
let trendDays = 30;

function renderLegend(labels, solidColors) {
  const ul = document.getElementById('wasteLegend');
  if (!ul) return;
  ul.innerHTML = labels.map((label, i) => `
    <li class="d-flex align-items-center mb-1">
      <span style="display:inline-block;width:12px;height:12px;background:${solidColors[i]};border-radius:2px;margin-right:8px;flex-shrink:0;"></span>
      <span>${label}</span>
    </li>
  `).join('');
}

async function loadStats() {
  try {
    const res = await fetch('/api/waste-stats/');
    const data = await res.json();
    const keys = Object.keys(data);
    const values = keys.map(k => data[k]);
    const solidColors = keys.map(k => WASTE_COLORS[k] || '#888');
    const fills = solidColors.map(c => hexToRgba(c, 0.5));
    const labels = keys.map(k => WASTE_LABELS[k] || k);

    const total = values.reduce((a, b) => a + b, 0);
    const diverted = (data.organic || 0) + (data.recyclable || 0);
    const diversionEl = document.getElementById('diversionRate');
    if (diversionEl) diversionEl.textContent = total ? (diverted / total * 100).toFixed(1) : '0.0';

    renderLegend(labels, solidColors);

    if (wasteChart) {
      wasteChart.data.labels = labels;
      wasteChart.data.datasets[0].data = values;
      wasteChart.data.datasets[0].backgroundColor = fills;
      wasteChart.update();
    } else {
      const ctx = document.getElementById('wasteChart').getContext('2d');
      wasteChart = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{
          data: values,
          backgroundColor: fills,
          borderColor: '#000',
          borderWidth: 1.25,
        }] },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}` } },
          },
        },
      });
    }
  } catch (e) {
    console.error('Failed to load waste stats:', e);
  }
}

async function loadTrends() {
  try {
    const res = await fetch(`/api/waste-timeseries/?days=${trendDays}`);
    const { dates, series } = await res.json();

    const datasets = Object.keys(series).map(key => {
      const solid = WASTE_COLORS[key] || '#888';
      return {
        label: WASTE_LABELS[key] || key,
        data: series[key],
        backgroundColor: hexToRgba(solid, 0.5),
        borderColor: solid,
        borderWidth: 1,
        fill: true,
        pointRadius: 0,
        tension: 0.25,
      };
    });

    if (trendsChart) {
      trendsChart.data.labels = dates;
      trendsChart.data.datasets = datasets;
      trendsChart.update();
      return;
    }

    const ctx = document.getElementById('trendsChart').getContext('2d');
    trendsChart = new Chart(ctx, {
      type: 'line',
      data: { labels: dates, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0, autoSkipPadding: 16 } },
          y: { stacked: true, beginAtZero: true, ticks: { font: { size: 10 } }, grid: { color: 'rgba(0,0,0,0.05)' } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 }, padding: 8 } },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}` } },
        },
      },
    });
  } catch (e) {
    console.error('Failed to load trends:', e);
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
      loadTrends();
    }
    if (badge) badge.textContent = `Auto-refresh: ${remaining}s`;
  }, 1000);
  return intervalId;
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadRecent();
  loadTrends();
  startCountdown();

  const rangeSel = document.getElementById('trendRange');
  if (rangeSel) {
    rangeSel.addEventListener('change', (e) => {
      trendDays = parseInt(e.target.value, 10) || 30;
      loadTrends();
    });
  }
});
