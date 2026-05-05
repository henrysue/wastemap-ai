/* WasteMap AI — Monitoring */
'use strict';

function escapeHTML(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

const WASTE_COLORS = {
  msw: '#6366f1', hazardous: '#ef4444', organic: '#22c55e',
  recyclable: '#3b82f6', liquid: '#06b6d4', ewaste: '#f59e0b',
  cd: '#8b5cf6', medical: '#ec4899', gaseous: '#64748b',
};

let ws = null;
let captureInterval = null;
let isRunning = false;
let feedItemCount = 0;

const videoEl = document.getElementById('videoEl');
const overlayCanvas = document.getElementById('overlayCanvas');
const classOverlay = document.getElementById('classOverlay');
const liveFeed = document.getElementById('liveFeed');
const statusBadge = document.getElementById('statusBadge');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const sectionSelect = document.getElementById('sectionSelect');
const subsectionSelect = document.getElementById('subsectionSelect');
const feedCount = document.getElementById('feedCount');

function setStatus(text, type) {
  if (!statusBadge) return;
  statusBadge.textContent = text;
  statusBadge.className = `badge bg-${type} ms-2`;
}

function updateFeedCount() {
  if (feedCount) feedCount.textContent = `${feedItemCount} item${feedItemCount !== 1 ? 's' : ''}`;
}

function addFeedItem(result) {
  if (!liveFeed) return;

  // Remove the placeholder if present
  const placeholder = liveFeed.querySelector('.text-muted.text-center');
  if (placeholder) placeholder.remove();

  feedItemCount += 1;
  updateFeedCount();

  const li = document.createElement('li');
  li.className = 'list-group-item live-item new-item px-3 py-2';
  const color = WASTE_COLORS[result.waste_type] || '#888';
  li.innerHTML = `
    <div class="d-flex justify-content-between align-items-center">
      <span class="badge rounded-pill" style="background:${color}">${escapeHTML(result.waste_type_label || result.waste_type)}</span>
      <small class="text-muted">${(result.confidence * 100).toFixed(0)}%</small>
    </div>
    <div class="small mt-1 text-muted">${escapeHTML(result.properties_label || result.properties)}</div>
    <div class="text-muted small mt-1">${new Date().toLocaleTimeString()}</div>
  `;
  liveFeed.prepend(li);

  // Keep max 50 items visible
  let feedItems = liveFeed.querySelectorAll('li');
  while (feedItems.length > 50) {
    feedItems[feedItems.length - 1].remove();
    feedItems = liveFeed.querySelectorAll('li');
  }

  setTimeout(() => li.classList.remove('new-item'), 1500);
}

function showOverlay(result) {
  if (!classOverlay) return;
  classOverlay.innerHTML = `
    <strong>${escapeHTML(result.waste_type_label || result.waste_type)}</strong><br>
    <small>${escapeHTML(result.properties_label || result.properties)} &bull; ${(result.confidence * 100).toFixed(0)}% confidence</small>
  `;
  classOverlay.classList.add('visible');
}

async function persistItem(result) {
  const sectionId = sectionSelect ? sectionSelect.value : '';
  const subsectionId = subsectionSelect ? subsectionSelect.value : '';
  try {
    const res = await fetch('/api/add-waste-item/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({
        waste_type: result.waste_type,
        properties: result.properties,
        confidence: result.confidence,
        section_id: sectionId || null,
        subsection_id: subsectionId || null,
      }),
    });
    if (!res.ok) console.warn('Failed to persist item:', res.status);
  } catch (e) {
    console.error('Error persisting item:', e);
  }
}

function captureFrame() {
  if (!videoEl || !overlayCanvas) return;
  const canvas = document.createElement('canvas');
  canvas.width = videoEl.videoWidth || 640;
  canvas.height = videoEl.videoHeight || 480;
  canvas.getContext('2d').drawImage(videoEl, 0, 0, canvas.width, canvas.height);
  const b64 = canvas.toDataURL('image/jpeg', 0.5).split(',')[1];
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'classify_frame', image: b64 }));
  }
}

function connectWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/monitoring/`);

  ws.onopen = () => setStatus('Connected', 'success');
  ws.onclose = () => setStatus('Disconnected', 'secondary');
  ws.onerror = () => setStatus('Error', 'danger');

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'classification_result') {
        showOverlay(data);
        addFeedItem(data);
        persistItem(data);
      } else if (data.type === 'item_added') {
        addFeedItem(data.item);
      }
    } catch (e) {
      console.error('WS message parse error:', e);
    }
  };
}

async function startMonitoring() {
  if (isRunning) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Your browser does not support camera access. Please use a modern browser over HTTPS.');
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    videoEl.srcObject = stream;
    isRunning = true;
    setStatus('Running', 'success');
    if (startBtn) startBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = false;
    connectWS();
    captureInterval = setInterval(captureFrame, 3000);
  } catch (err) {
    alert('Camera access denied or not available: ' + err.message);
  }
}

function stopMonitoring() {
  if (!isRunning) return;
  clearInterval(captureInterval);
  captureInterval = null;
  if (videoEl.srcObject) {
    videoEl.srcObject.getTracks().forEach(t => t.stop());
    videoEl.srcObject = null;
  }
  if (ws) { ws.close(); ws = null; }
  if (classOverlay) classOverlay.classList.remove('visible');
  isRunning = false;
  setStatus('Stopped', 'secondary');
  if (startBtn) startBtn.disabled = false;
  if (stopBtn) stopBtn.disabled = true;
}

document.addEventListener('DOMContentLoaded', () => {
  if (startBtn) startBtn.addEventListener('click', startMonitoring);
  if (stopBtn) { stopBtn.disabled = true; stopBtn.addEventListener('click', stopMonitoring); }
  setStatus('Ready', 'secondary');
});
