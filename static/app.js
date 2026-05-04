'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let activeJobId = null;
let pollInterval = null;
let lastLogId = 0;
let selectedFilter = 'new';
let selectedLang = 'RU';

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadGroups();
  loadStats();
  setupForm();
  setupSettings();
  resumeActiveJob();
  setInterval(loadStats, 30000);
});

// ── Groups ─────────────────────────────────────────────────────────────────
async function loadGroups() {
  const res = await api('/api/groups');
  const groups = await res.json();
  renderGroups(groups);
  populateGroupSelect(groups);
}

function renderGroups(groups) {
  const el = document.getElementById('groupsList');
  if (!groups.length) {
    el.innerHTML = '<div class="empty-state">No groups yet. Add one above.</div>';
    return;
  }
  el.innerHTML = groups.map(g => `
    <div class="group-item ${g.pinned ? 'pinned' : ''}" data-id="${g.id}">
      ${g.avatar_url
        ? `<img class="group-avatar" src="${escHtml(g.avatar_url)}" alt="" onerror="this.style.display='none'">`
        : `<div class="group-avatar-placeholder">👥</div>`}
      <div class="group-info">
        <div class="group-name">${escHtml(g.name)}</div>
        <div class="group-meta">
          ${g.total_parsed} videos · ${g.last_used_at ? 'Last: ' + fmtDate(g.last_used_at) : 'Never used'}
        </div>
      </div>
      <div class="group-actions">
        <button class="btn btn-sm ${g.pinned ? 'btn-accent' : ''}" title="${g.pinned ? 'Unpin' : 'Pin'}"
          onclick="togglePin(${g.id})">${g.pinned ? '📌' : '📍'}</button>
        <button class="btn btn-sm btn-danger" title="Delete" onclick="deleteGroup(${g.id})">✕</button>
      </div>
    </div>
  `).join('');
}

function populateGroupSelect(groups) {
  const sel = document.getElementById('groupSelect');
  const current = sel.value;
  sel.innerHTML = '<option value="">— paste URL below —</option>' +
    groups.map(g => `<option value="${g.id}">${escHtml(g.name)}</option>`).join('');
  if (current) sel.value = current;
}

async function togglePin(id) {
  await api(`/api/groups/${id}/pin`, { method: 'POST' });
  loadGroups();
}

async function deleteGroup(id) {
  if (!confirm('Delete this group?')) return;
  await api(`/api/groups/${id}`, { method: 'DELETE' });
  loadGroups();
}

// Add group form
document.getElementById('addGroupBtn').addEventListener('click', () => {
  document.getElementById('addGroupForm').classList.remove('hidden');
  document.getElementById('newGroupUrl').focus();
});
document.getElementById('addGroupCancel').addEventListener('click', () => {
  document.getElementById('addGroupForm').classList.add('hidden');
});
document.getElementById('addGroupSubmit').addEventListener('click', async () => {
  const url = document.getElementById('newGroupUrl').value.trim();
  if (!url) return;
  const btn = document.getElementById('addGroupSubmit');
  btn.textContent = 'Adding…';
  btn.disabled = true;
  const res = await api('/api/groups', { method: 'POST', json: { vk_url: url } });
  btn.textContent = 'Add';
  btn.disabled = false;
  if (res.ok) {
    document.getElementById('newGroupUrl').value = '';
    document.getElementById('addGroupForm').classList.add('hidden');
    loadGroups();
  } else {
    const data = await res.json();
    alert(data.error || 'Failed to add group');
  }
});

// ── Job form ───────────────────────────────────────────────────────────────
function setupForm() {
  // Filter toggles
  document.getElementById('filterGroup').addEventListener('click', e => {
    const btn = e.target.closest('.btn-toggle');
    if (!btn) return;
    document.querySelectorAll('#filterGroup .btn-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedFilter = btn.dataset.value;
  });

  // Lang toggle
  document.getElementById('langToggle').addEventListener('click', e => {
    const btn = e.target.closest('.lang-btn');
    if (!btn) return;
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedLang = btn.dataset.lang;
  });

  // Slider
  const slider = document.getElementById('videoCount');
  slider.addEventListener('input', () => {
    document.getElementById('videoCountLabel').textContent = slider.value;
  });

  // Group select — hide custom URL when group selected
  document.getElementById('groupSelect').addEventListener('change', e => {
    const custom = document.getElementById('customUrlGroup');
    custom.style.display = e.target.value ? 'none' : '';
  });

  // Submit
  document.getElementById('jobForm').addEventListener('submit', async e => {
    e.preventDefault();
    const groupId = document.getElementById('groupSelect').value;
    const groupUrl = document.getElementById('customGroupUrl').value.trim();

    if (!groupId && !groupUrl) {
      alert('Select a group or paste a URL');
      return;
    }

    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Starting…';

    const res = await api('/api/jobs', {
      method: 'POST',
      json: {
        group_id: groupId ? parseInt(groupId) : null,
        group_url: groupUrl || null,
        video_count: parseInt(document.getElementById('videoCount').value),
        filter_type: selectedFilter,
        language: selectedLang,
      },
    });

    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = '▶ Start Job';

    if (res.ok) {
      const job = await res.json();
      startPolling(job.id);
    } else {
      const data = await res.json();
      alert(data.error || 'Failed to start job');
    }
  });
}

// ── Polling / Live Log ─────────────────────────────────────────────────────
function startPolling(jobId) {
  if (pollInterval) clearInterval(pollInterval);
  activeJobId = jobId;
  lastLogId = 0;
  document.getElementById('logOutput').innerHTML = '';
  document.getElementById('progressWrap').style.display = 'flex';
  document.getElementById('activePulse').classList.remove('hidden');
  document.getElementById('botStatus').querySelector('.status-label').textContent = 'Processing…';

  pollInterval = setInterval(() => fetchLogs(jobId), 2000);
  fetchLogs(jobId);
}

async function fetchLogs(jobId) {
  const res = await api(`/api/jobs/${jobId}/logs?since=${lastLogId}`);
  if (!res.ok) return;
  const data = await res.json();

  const output = document.getElementById('logOutput');
  data.logs.forEach(entry => {
    lastLogId = Math.max(lastLogId, entry.id);
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="log-time">[${entry.time}]</span><span class="log-${entry.level}">${escHtml(entry.message)}</span>`;
    output.appendChild(line);
  });
  if (data.logs.length) output.scrollTop = output.scrollHeight;

  // Update progress
  const job = data.job;
  if (job.videos_total > 0) {
    const pct = Math.round((job.videos_done / job.videos_total) * 100);
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressLabel').textContent = `${job.videos_done} / ${job.videos_total}`;
  }

  // Stop when done
  if (job.status === 'done' || job.status === 'error') {
    clearInterval(pollInterval);
    pollInterval = null;
    document.getElementById('activePulse').classList.add('hidden');
    document.getElementById('botStatus').querySelector('.status-label').textContent = job.status === 'done' ? 'Done' : 'Error';
    loadStats();
  }
}

async function resumeActiveJob() {
  const res = await api('/api/jobs/latest');
  if (!res.ok) return;
  const job = await res.json();
  if (job && job.status === 'processing') {
    startPolling(job.id);
  }
}

// ── Stats ──────────────────────────────────────────────────────────────────
async function loadStats() {
  const res = await api('/api/stats');
  if (!res.ok) return;
  const s = await res.json();
  document.getElementById('statOrToday').textContent = s.openrouter_today;
  document.getElementById('statVideosToday').textContent = s.videos_today;
  document.getElementById('statVideosTotal').textContent = s.videos_total;
  document.getElementById('statLastActivity').textContent = s.last_activity ? fmtDate(s.last_activity) : '—';
}

// ── Settings ───────────────────────────────────────────────────────────────
function setupSettings() {
  const toggle = document.getElementById('settingsToggle');
  const body = document.getElementById('settingsBody');
  const chevron = document.getElementById('settingsChevron');
  toggle.addEventListener('click', () => {
    body.classList.toggle('hidden');
    chevron.classList.toggle('open');
  });
}

async function saveSetting(key, inputId) {
  const val = document.getElementById(inputId).value.trim();
  if (!val) return;
  await api('/api/settings', { method: 'POST', json: { [key]: val } });
  showResult(inputId + 'Saved', '✓ Saved', 'ok');
}

async function testVK() {
  const token = document.getElementById('vkToken').value.trim();
  const res = await api('/api/settings/test/vk', { method: 'POST', json: { token } });
  const data = await res.json();
  showResult('vkResult', data.ok ? `✓ Connected as ${data.user}` : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
}

async function testOR() {
  const api_key = document.getElementById('orKey').value.trim();
  const res = await api('/api/settings/test/openrouter', { method: 'POST', json: { api_key } });
  const data = await res.json();
  showResult('orResult', data.ok ? '✓ Connected' : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
}

async function testTelegram() {
  const token = document.getElementById('tgToken').value.trim();
  const channel_id = document.getElementById('tgChannel').value.trim();
  const res = await api('/api/settings/test/telegram', { method: 'POST', json: { token, channel_id } });
  const data = await res.json();
  showResult('tgResult', data.ok ? '✓ Message sent' : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
}

function showResult(id, text, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'setting-result ' + cls;
  setTimeout(() => { el.textContent = ''; el.className = 'setting-result'; }, 4000);
}

// ── Helpers ────────────────────────────────────────────────────────────────
async function api(url, opts = {}) {
  const options = {
    method: opts.method || 'GET',
    headers: {},
  };
  if (opts.json) {
    options.body = JSON.stringify(opts.json);
    options.headers['Content-Type'] = 'application/json';
  }
  try {
    return await fetch(url, options);
  } catch (e) {
    console.error('API error', e);
    return { ok: false, json: async () => ({ error: e.message }) };
  }
}

function escHtml(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
