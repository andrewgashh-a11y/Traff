'use strict';

// ── Translations ───────────────────────────────────────────────────────────
const TRANSLATIONS = {
  RU: {
    ready:            'Готово',
    processing:       'Обработка…',
    done:             'Готово',
    error:            'Ошибка',
    savedGroups:      'Группы ВКонтакте',
    addGroup:         '+ Добавить',
    add:              'Добавить',
    adding:           'Добавление…',
    cancel:           'Отмена',
    loadingGroups:    'Загрузка групп…',
    noGroups:         'Нет групп. Добавьте выше.',
    groupUrlPlaceholder: 'vk.com/groupname',
    neverUsed:        'Не использовалась',
    lastUsed:         'Последний: ',
    pinTitle:         'Закрепить',
    unpinTitle:       'Открепить',
    deleteTitle:      'Удалить',
    confirmDelete:    'Удалить эту группу?',
    launchJob:        'Запуск задачи',
    group:            'Группа',
    pasteUrlBelow:    '— вставьте ссылку ниже —',
    orPasteUrl:       'Или вставьте ссылку',
    filter:           'Фильтр',
    filterNew:        'Новые',
    filterPopular:    'Популярные',
    filterRandom:     'Случайные',
    videos:           'Видео',
    genLang:          'Язык генерации',
    startJob:         '▶ Запустить',
    starting:         'Запуск…',
    alertSelectGroup: 'Выберите группу или вставьте ссылку',
    alertFailedAdd:   'Не удалось добавить группу',
    alertFailedStart: 'Не удалось запустить задачу',
    liveLog:          'Лог обработки',
    noActiveJob:      'Нет активных задач. Запустите выше.',
    statistics:       'Статистика',
    statOrToday:      'OpenRouter запросов сегодня',
    statVideosToday:  'Видео сегодня',
    statVideosTotal:  'Видео всего',
    statLastActivity: 'Последняя активность',
    settings:         'Настройки',
    vkToken:          'VK API Token',
    orKey:            'OpenRouter API Key',
    tgToken:          'Telegram Bot Token',
    tgChannel:        'Telegram Channel ID',
    enterToken:       'Введите токен',
    enterKey:         'Введите ключ',
    save:             'Сохранить',
    test:             'Тест',
    clear:            'Очистить',
    testTelegram:     'Тест Telegram',
    saved:            '✓ Сохранено',
    cleared:          '✓ Удалено',
    connected:        '✓ Подключено',
    connectedAs:      '✓ Подключено как',
    msgSent:          '✓ Сообщение отправлено',
  },
  EN: {
    ready:            'Ready',
    processing:       'Processing…',
    done:             'Done',
    error:            'Error',
    savedGroups:      'Saved VK Groups',
    addGroup:         '+ Add Group',
    add:              'Add',
    adding:           'Adding…',
    cancel:           'Cancel',
    loadingGroups:    'Loading groups…',
    noGroups:         'No groups yet. Add one above.',
    groupUrlPlaceholder: 'vk.com/groupname',
    neverUsed:        'Never used',
    lastUsed:         'Last: ',
    pinTitle:         'Pin',
    unpinTitle:       'Unpin',
    deleteTitle:      'Delete',
    confirmDelete:    'Delete this group?',
    launchJob:        'Launch Job',
    group:            'Group',
    pasteUrlBelow:    '— paste URL below —',
    orPasteUrl:       'Or paste URL',
    filter:           'Filter',
    filterNew:        'New',
    filterPopular:    'Popular',
    filterRandom:     'Random',
    videos:           'Videos',
    genLang:          'Language',
    startJob:         '▶ Start Job',
    starting:         'Starting…',
    alertSelectGroup: 'Select a group or paste a URL',
    alertFailedAdd:   'Failed to add group',
    alertFailedStart: 'Failed to start job',
    liveLog:          'Live Log',
    noActiveJob:      'No active job. Start one above.',
    statistics:       'Statistics',
    statOrToday:      'OpenRouter requests today',
    statVideosToday:  'Videos today',
    statVideosTotal:  'Videos total',
    statLastActivity: 'Last activity',
    settings:         'Settings',
    vkToken:          'VK API Token',
    orKey:            'OpenRouter API Key',
    tgToken:          'Telegram Bot Token',
    tgChannel:        'Telegram Channel ID',
    enterToken:       'Enter token',
    enterKey:         'Enter key',
    save:             'Save',
    test:             'Test',
    clear:            'Clear',
    testTelegram:     'Test Telegram',
    saved:            '✓ Saved',
    cleared:          '✓ Cleared',
    connected:        '✓ Connected',
    connectedAs:      '✓ Connected as',
    msgSent:          '✓ Message sent',
  },
};

// ── i18n state ─────────────────────────────────────────────────────────────
let uiLang = localStorage.getItem('uiLang') || 'RU';

function t(key) {
  return (TRANSLATIONS[uiLang] || TRANSLATIONS.RU)[key] || key;
}

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  // Keep the select first option in sync
  const firstOpt = document.querySelector('#groupSelect option[value=""]');
  if (firstOpt) firstOpt.textContent = t('pasteUrlBelow');

  document.documentElement.lang = uiLang === 'RU' ? 'ru' : 'en';
}

function setupUiLangToggle() {
  document.getElementById('uiLangToggle').addEventListener('click', e => {
    const btn = e.target.closest('.ui-lang-btn');
    if (!btn) return;
    uiLang = btn.dataset.uiLang;
    localStorage.setItem('uiLang', uiLang);
    document.querySelectorAll('.ui-lang-btn').forEach(b => b.classList.toggle('active', b.dataset.uiLang === uiLang));
    applyI18n();
    // Re-render groups so dynamic strings update too
    loadGroups();
  });

  // Restore active state from saved preference
  document.querySelectorAll('.ui-lang-btn').forEach(b => b.classList.toggle('active', b.dataset.uiLang === uiLang));
}

// ── State ──────────────────────────────────────────────────────────────────
let activeJobId = null;
let pollInterval = null;
let lastLogId = 0;
let selectedFilter = 'new';
let selectedLang = 'RU';

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupUiLangToggle();
  applyI18n();
  loadGroups();
  loadStats();
  loadSettings();
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
    el.innerHTML = `<div class="empty-state">${escHtml(t('noGroups'))}</div>`;
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
          ${g.total_parsed} · ${g.last_used_at ? t('lastUsed') + fmtDate(g.last_used_at) : t('neverUsed')}
        </div>
      </div>
      <div class="group-actions">
        <button class="btn btn-sm ${g.pinned ? 'btn-accent' : ''}" title="${g.pinned ? t('unpinTitle') : t('pinTitle')}"
          onclick="togglePin(${g.id})">${g.pinned ? '📌' : '📍'}</button>
        <button class="btn btn-sm btn-danger" title="${t('deleteTitle')}" onclick="deleteGroup(${g.id})">✕</button>
      </div>
    </div>
  `).join('');
}

function populateGroupSelect(groups) {
  const sel = document.getElementById('groupSelect');
  const current = sel.value;
  sel.innerHTML = `<option value="">${escHtml(t('pasteUrlBelow'))}</option>` +
    groups.map(g => `<option value="${g.id}">${escHtml(g.name)}</option>`).join('');
  if (current) sel.value = current;
}

async function togglePin(id) {
  await api(`/api/groups/${id}/pin`, { method: 'POST' });
  loadGroups();
}

async function deleteGroup(id) {
  if (!confirm(t('confirmDelete'))) return;
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
  btn.textContent = t('adding');
  btn.disabled = true;
  const res = await api('/api/groups', { method: 'POST', json: { vk_url: url } });
  btn.textContent = t('add');
  btn.disabled = false;
  if (res.ok) {
    document.getElementById('newGroupUrl').value = '';
    document.getElementById('addGroupForm').classList.add('hidden');
    loadGroups();
  } else {
    const data = await res.json();
    alert(data.error || t('alertFailedAdd'));
  }
});

// ── Job form ───────────────────────────────────────────────────────────────
function setupForm() {
  document.getElementById('filterGroup').addEventListener('click', e => {
    const btn = e.target.closest('.btn-toggle');
    if (!btn) return;
    document.querySelectorAll('#filterGroup .btn-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedFilter = btn.dataset.value;
  });

  document.getElementById('langToggle').addEventListener('click', e => {
    const btn = e.target.closest('.lang-btn');
    if (!btn) return;
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedLang = btn.dataset.lang;
  });

  const slider = document.getElementById('videoCount');
  slider.addEventListener('input', () => {
    document.getElementById('videoCountLabel').textContent = slider.value;
  });

  document.getElementById('groupSelect').addEventListener('change', e => {
    document.getElementById('customUrlGroup').style.display = e.target.value ? 'none' : '';
  });

  document.getElementById('jobForm').addEventListener('submit', async e => {
    e.preventDefault();
    const groupId = document.getElementById('groupSelect').value;
    const groupUrl = document.getElementById('customGroupUrl').value.trim();

    if (!groupId && !groupUrl) {
      alert(t('alertSelectGroup'));
      return;
    }

    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = t('starting');

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
    btn.querySelector('.btn-text').textContent = t('startJob');

    if (res.ok) {
      const job = await res.json();
      startPolling(job.id);
    } else {
      const data = await res.json();
      alert(data.error || t('alertFailedStart'));
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
  document.getElementById('botStatus').querySelector('.status-label').textContent = t('processing');

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

  const job = data.job;
  if (job.videos_total > 0) {
    const pct = Math.round((job.videos_done / job.videos_total) * 100);
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressLabel').textContent = `${job.videos_done} / ${job.videos_total}`;
  }

  if (job.status === 'done' || job.status === 'error') {
    clearInterval(pollInterval);
    pollInterval = null;
    document.getElementById('activePulse').classList.add('hidden');
    document.getElementById('botStatus').querySelector('.status-label').textContent =
      job.status === 'done' ? t('done') : t('error');
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

async function loadSettings() {
  const res = await api('/api/settings');
  if (!res.ok) return;
  const s = await res.json();
  // Pre-fill inputs; password inputs will mask the value automatically
  const map = {
    vk_token: 'vkToken',
    openrouter_api_key: 'orKey',
    telegram_bot_token: 'tgToken',
    telegram_channel_id: 'tgChannel',
  };
  for (const [key, inputId] of Object.entries(map)) {
    const input = document.getElementById(inputId);
    if (input && s[key]) input.value = s[key];
  }
}

async function saveSetting(key, inputId, resultId) {
  const val = document.getElementById(inputId).value.trim();
  if (!val) { showResult(resultId, '⚠ ' + (uiLang === 'RU' ? 'Поле пустое' : 'Field is empty'), 'err'); return; }
  const res = await api('/api/settings', { method: 'POST', json: { [key]: val } });
  if (res.ok) {
    showResult(resultId, t('saved'), 'ok');
  } else {
    const data = await res.json();
    showResult(resultId, '✗ ' + (data.error || 'Error'), 'err');
  }
}

async function deleteSetting(key, inputId, resultId) {
  const res = await api(`/api/settings/${key}`, { method: 'DELETE' });
  if (res.ok) {
    document.getElementById(inputId).value = '';
    showResult(resultId, t('cleared'), 'ok');
  } else {
    showResult(resultId, '✗ Error', 'err');
  }
}

async function testVK() {
  const token = document.getElementById('vkToken').value.trim();
  const res = await api('/api/settings/test/vk', { method: 'POST', json: { token } });
  const data = await res.json();
  showResult('vkResult', data.ok ? `${t('connectedAs')} ${data.user}` : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
}

async function testOR() {
  const api_key = document.getElementById('orKey').value.trim();
  const res = await api('/api/settings/test/openrouter', { method: 'POST', json: { api_key } });
  const data = await res.json();
  showResult('orResult', data.ok ? t('connected') : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
}

async function testTelegram() {
  const token = document.getElementById('tgToken').value.trim();
  const channel_id = document.getElementById('tgChannel').value.trim();
  const res = await api('/api/settings/test/telegram', { method: 'POST', json: { token, channel_id } });
  const data = await res.json();
  showResult('tgResult', data.ok ? t('msgSent') : `✗ ${data.error}`, data.ok ? 'ok' : 'err');
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
  const options = { method: opts.method || 'GET', headers: {} };
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
