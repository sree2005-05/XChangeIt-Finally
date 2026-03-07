/* ═══════════════════════════════════════
   XCHANGEIT — NOTIFICATION BELL
   Drop this script on every page that has
   a logged-in navbar. Requires the bell
   HTML snippet to already be in the DOM.
═══════════════════════════════════════ */

(function () {
  const bell      = document.getElementById('notifBell');
  const panel     = document.getElementById('notifPanel');
  const badge     = document.getElementById('notifBadge');
  const listEl    = document.getElementById('notifList');
  if (!bell || !panel) return;           // not logged in / bell not present

  let open        = false;
  let lastTotal   = -1;

  /* ── ICON MAP ── */
  const ICONS = {
    package:       { emoji: '📦', cls: 'type-order_received' },
    check:         { emoji: '✓',  cls: 'type-order_accepted' },
    x:             { emoji: '✕',  cls: 'type-order_declined' },
    chat:          { emoji: '💬', cls: 'type-chat_received'  },
    green:         { emoji: '✓',  cls: 'type-chat_accepted'  },
  };

  /* ── FETCH & RENDER ── */
  async function loadNotifications() {
    listEl.innerHTML = '<div class="notif-loading">Loading…</div>';
    try {
      const res  = await fetch('/api/notifications');
      const data = await res.json();
      const notifs = data.notifications || [];

      // Update badge
      if (data.total > 0) {
        badge.textContent = data.total > 9 ? '9+' : data.total;
        badge.style.display = 'inline-flex';
      } else {
        badge.style.display = 'none';
      }
      lastTotal = data.total;

      // Render list
      if (!notifs.length) {
        listEl.innerHTML = '<div class="notif-empty">No notifications yet</div>';
        return;
      }

      listEl.innerHTML = '';
      notifs.forEach(n => {
        const ic  = ICONS[n.icon] || { emoji: '🔔', cls: '' };
        const a   = document.createElement('a');
        a.className = 'notif-item';
        a.href      = n.link || '#';
        a.innerHTML = `
          <div class="notif-icon ${ic.cls}">${ic.emoji}</div>
          <div class="notif-text">
            ${escHtml(n.text)}
            <span class="notif-time">${fmtTime(n.time)}</span>
          </div>`;
        listEl.appendChild(a);
      });

    } catch (e) {
      listEl.innerHTML = '<div class="notif-empty">Could not load notifications</div>';
    }
  }

  /* ── BADGE POLL (background, every 12 s) ── */
  async function pollBadge() {
    try {
      const res  = await fetch('/api/notifications');
      const data = await res.json();
      if (data.total !== lastTotal) {
        lastTotal = data.total;
        if (data.total > 0) {
          badge.textContent = data.total > 9 ? '9+' : data.total;
          badge.style.display = 'inline-flex';
          // Animate bell
          bell.classList.add('bell-ring');
          setTimeout(() => bell.classList.remove('bell-ring'), 600);
        } else {
          badge.style.display = 'none';
        }
      }
    } catch (_) {}
  }
  setInterval(pollBadge, 12000);
  pollBadge(); // run once on load to set initial badge without opening panel

  /* ── TOGGLE ── */
  window.toggleNotifPanel = function (e) {
    e.stopPropagation();
    open = !open;
    panel.style.display = open ? 'block' : 'none';
    if (open) loadNotifications();
  };

  window.closeNotifPanel = function () {
    open = false;
    panel.style.display = 'none';
  };

  /* ── CLOSE ON OUTSIDE CLICK ── */
  document.addEventListener('click', function (e) {
    if (open && !document.getElementById('notifWrap').contains(e.target)) {
      open = false;
      panel.style.display = 'none';
    }
  });

  /* ── HELPERS ── */
  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtTime(t) {
    if (!t) return '';
    try {
      const d   = new Date(t.replace(' ', 'T'));
      const now = new Date();
      const diff = Math.floor((now - d) / 1000);
      if (diff < 60)   return 'just now';
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    } catch (_) { return t; }
  }
})();
