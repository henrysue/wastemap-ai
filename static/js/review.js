/* WasteMap AI — Review Queue */
'use strict';

function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

async function postAction(pk, payload) {
  const res = await fetch(`/api/review/${pk}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function removeCard(card) {
  card.style.transition = 'opacity 0.25s';
  card.style.opacity = '0';
  setTimeout(() => {
    card.remove();
    updatePendingBadge();
    const grid = document.getElementById('reviewGrid');
    if (grid && !grid.children.length) {
      window.location.reload();
    }
  }, 260);
}

function updatePendingBadge() {
  const badge = document.querySelector('h1 .badge');
  if (!badge) return;
  const remaining = document.querySelectorAll('#reviewGrid [data-item-id]').length;
  badge.textContent = `${remaining} pending`;
}

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('reviewGrid');
  if (!grid) return;

  grid.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const card = btn.closest('[data-item-id]');
    if (!card) return;
    const pk = card.dataset.itemId;
    btn.disabled = true;

    try {
      if (btn.classList.contains('js-confirm')) {
        await postAction(pk, { action: 'confirm' });
        removeCard(card);
      } else if (btn.classList.contains('js-correct')) {
        const waste_type = card.querySelector('.js-waste-type').value;
        const properties = card.querySelector('.js-properties').value;
        await postAction(pk, { action: 'correct', waste_type, properties });
        removeCard(card);
      } else if (btn.classList.contains('js-delete')) {
        if (!confirm('Delete this item permanently?')) {
          btn.disabled = false;
          return;
        }
        await postAction(pk, { action: 'delete' });
        removeCard(card);
      }
    } catch (err) {
      console.error('Review action failed:', err);
      alert('Action failed: ' + err.message);
      btn.disabled = false;
    }
  });
});
