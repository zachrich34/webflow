/**
 * WebFlow — frontend logic
 * All API communication uses the JWT stored in sessionStorage (NOT localStorage).
 * Keys never leave the server's memory.
 */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  token: sessionStorage.getItem('wf_token') || null,
  username: sessionStorage.getItem('wf_user') || null,
  currentStep: 1,
  detectedBrowsers: [],
  sourceBrowser: null,
  sourceProfile: null,
  snapshotId: null,
  selectedDataTypes: new Set(['bookmarks', 'history']),
  destBrowser: null,
  destProfile: null,
  jobId: null,
  transferResult: null,
  // Subscription
  subscriptionTier: 'free',
  subscriptionFeatures: ['bookmarks', 'history'],
  paymentsEnabled: false,
};

// Free tier data types
const FREE_TYPES = new Set(['bookmarks', 'history']);
// Pro/Premium data types
const PRO_TYPES  = new Set(['bookmarks', 'history', 'passwords', 'extensions', 'settings']);

// Browser display info
const BROWSER_INFO = {
  chrome:    { emoji: '🌐', label: 'Google Chrome',   color: '#4285F4' },
  firefox:   { emoji: '🦊', label: 'Mozilla Firefox', color: '#FF7139' },
  opera_gx:  { emoji: '🎮', label: 'Opera GX',        color: '#FF1B2D' },
  edge:      { emoji: '🔷', label: 'Microsoft Edge',   color: '#0078D7' },
  brave:     { emoji: '🦁', label: 'Brave',            color: '#FB542B' },
};

const DATA_TYPE_EMOJI = {
  bookmarks: '🔖',
  history: '📅',
  passwords: '🔑',
  extensions: '🧩',
  settings: '⚙️',
};

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Try auto-login from saved credentials
  const saved = loadRemembered();
  if (saved) {
    autoLogin(saved.username, saved.password);
    return;
  }

  if (state.token) {
    verifyToken().then(ok => {
      if (ok) {
        updateHeaderUI();
        loadSubscriptionStatus().then(() => showDash());
      } else {
        clearAuth();
      }
    });
  }

  // Allow Enter key on auth inputs
  ['loginUsername','loginPassword','regUsername','regEmail','regPassword'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') e.target.closest('.card').querySelector('.btn-primary').click(); });
  });
});

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    let msg = data.detail;
    if (Array.isArray(msg)) msg = msg.map(e => e.msg || JSON.stringify(e)).join(', ');
    throw new Error(msg || `HTTP ${resp.status}`);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

function switchAuthTab(tab) {
  document.getElementById('loginForm').style.display    = tab === 'login'    ? '' : 'none';
  document.getElementById('registerForm').style.display = tab === 'register' ? '' : 'none';
  document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
  document.getElementById('tabRegister').classList.toggle('active', tab === 'register');
}

async function login() {
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const remember = document.getElementById('rememberMe')?.checked || false;
  const errEl = document.getElementById('loginError');
  errEl.style.display = 'none';
  const btn = document.getElementById('loginBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Connexion…';

  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    if (remember) {
      saveRemembered(username, password);
    } else {
      clearRemembered();
    }
    updateHeaderUI();
    await loadSubscriptionStatus();
    toast('Bienvenue, ' + username + ' !', 'success');
    showDash();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = '';
  } finally {
    btn.disabled = false; btn.innerHTML = 'Continuer →';
  }
}

async function register() {
  const username = document.getElementById('regUsername').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl    = document.getElementById('regError');
  errEl.style.display = 'none';
  const btn = document.getElementById('regBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Création du compte…';

  try {
    await api('POST', '/api/auth/register', { username, email, password });
    toast('Compte créé ! Connexion en cours…', 'success');
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    updateHeaderUI();
    await loadSubscriptionStatus();
    showDash();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = '';
  } finally {
    btn.disabled = false; btn.innerHTML = 'Créer le compte →';
  }
}

async function logout() {
  try { await api('POST', '/api/auth/logout'); } catch {}
  clearRemembered();
  clearAuth();
  goToStep(1);
  toast('Déconnecté.', 'info');
}

function clearAuth() {
  state.token = null; state.username = null;
  state.subscriptionTier = 'free';
  state.subscriptionFeatures = ['bookmarks', 'history'];
  sessionStorage.removeItem('wf_token');
  sessionStorage.removeItem('wf_user');
  updateHeaderUI();
}

// ---------------------------------------------------------------------------
// Remember me (credentials stored locally for auto-login on app restart)
// ---------------------------------------------------------------------------

function saveRemembered(username, password) {
  localStorage.setItem('wf_remember', btoa(JSON.stringify({ username, password })));
}

function loadRemembered() {
  try {
    const raw = localStorage.getItem('wf_remember');
    if (!raw) return null;
    return JSON.parse(atob(raw));
  } catch { return null; }
}

function clearRemembered() {
  localStorage.removeItem('wf_remember');
}

async function autoLogin(username, password) {
  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    updateHeaderUI();
    await loadSubscriptionStatus();
    showDash();
  } catch {
    // Server may have restarted with no session — fall back to login form
    clearRemembered();
    clearAuth();
    // Pre-fill username
    const el = document.getElementById('loginUsername');
    if (el) el.value = username;
  }
}

async function verifyToken() {
  try { await api('GET', '/api/auth/me'); return true; } catch { return false; }
}

function updateHeaderUI() {
  const userEl  = document.getElementById('headerUser');
  const logoutEl = document.getElementById('logoutBtn');
  const tierEl   = document.getElementById('tierBadge');
  const upgradeEl = document.getElementById('upgradeBtn');
  const manageEl  = document.getElementById('manageSubBtn');

  if (state.username) {
    userEl.textContent = '👤 ' + state.username;
    userEl.style.display = '';
    logoutEl.style.display = '';
    tierEl.style.display = '';
    // Upgrade / manage buttons based on tier
    if (state.subscriptionTier === 'beta') {
      // Beta: hide both buttons, everything is unlocked
      upgradeEl.style.display = 'none';
      manageEl.style.display = 'none';
    } else if (state.subscriptionTier === 'free') {
      upgradeEl.style.display = '';
      manageEl.style.display = 'none';
    } else {
      upgradeEl.style.display = 'none';
      manageEl.style.display = '';
    }
  } else {
    userEl.style.display = 'none';
    logoutEl.style.display = 'none';
    tierEl.style.display = 'none';
    upgradeEl.style.display = 'none';
    manageEl.style.display = 'none';
  }
}

// ---------------------------------------------------------------------------
// Subscription
// ---------------------------------------------------------------------------

async function loadSubscriptionStatus() {
  try {
    const data = await api('GET', '/api/billing/status');
    state.subscriptionTier = data.tier || 'free';
    state.subscriptionFeatures = data.features || ['bookmarks', 'history'];
    state.paymentsEnabled = data.payments_enabled || false;
    updateTierBadge(data.tier);
    applyTierToDataTypes(data.tier);
  } catch {
    state.subscriptionTier = 'free';
    state.paymentsEnabled = false;
  }
}

function updateTierBadge(tier) {
  const el = document.getElementById('tierBadge');
  if (!el) return;
  const labels = { free: 'Free', beta: '🧪 Bêta', pro: '⚡ Pro', premium: '👑 Premium' };
  el.textContent = labels[tier] || 'Free';
  el.className = `tier-badge ${tier === 'beta' ? 'pro' : tier}`;
  updateHeaderUI();
}

function applyTierToDataTypes(tier) {
  const proTypes = ['passwords', 'extensions', 'settings'];
  const hasAccess = tier === 'pro' || tier === 'premium' || tier === 'beta';

  proTypes.forEach(type => {
    const card = document.getElementById('dtcard-' + type);
    const lock = document.getElementById('lock-' + type);
    if (!card) return;

    if (hasAccess) {
      card.classList.remove('locked');
      if (lock) lock.style.display = 'none';
      // Auto-select on upgrade
      card.classList.add('selected');
      state.selectedDataTypes.add(type);
    } else {
      card.classList.add('locked');
      card.classList.remove('selected');
      state.selectedDataTypes.delete(type);
      if (lock) lock.style.display = '';
    }
  });
}

// ---------------------------------------------------------------------------
// Step navigation
// ---------------------------------------------------------------------------

function goToStep(n, summary) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page' + n).classList.add('active');
  state.currentStep = n;
  updateProgressBar(n);

  const bar = document.getElementById('progressBar');
  bar.style.display = (n === 1) ? 'none' : 'flex';

  if (n === 2) loadBrowserGrid('source');
  if (n === 4) loadBrowserGrid('dest');
  if (n === 6 && summary) buildSummary(summary);
}

function updateProgressBar(active) {
  for (let i = 1; i <= 6; i++) {
    const dot  = document.getElementById('sdot' + i);
    const line = document.getElementById('sline' + i);
    dot.classList.toggle('active', i === active);
    dot.classList.toggle('done',   i < active);
    if (line) line.classList.toggle('done', i < active);
  }
}

// ---------------------------------------------------------------------------
// Step 2 — Browser detection
// ---------------------------------------------------------------------------

async function loadBrowserGrid(role) {
  if (!state.detectedBrowsers.length) {
    try {
      const data = await api('GET', '/api/browsers/detect');
      state.detectedBrowsers = data.browsers || [];
    } catch (e) {
      toast('Impossible de détecter les navigateurs : ' + e.message, 'error');
      state.detectedBrowsers = [];
    }
  }

  const gridId   = role === 'source' ? 'sourceBrowserGrid' : 'destBrowserGrid';
  const grid     = document.getElementById(gridId);
  grid.innerHTML = '';

  const grouped = {};
  for (const p of state.detectedBrowsers) {
    if (!grouped[p.browser]) grouped[p.browser] = [];
    grouped[p.browser].push(p);
  }

  const allBrowsers = ['chrome', 'firefox', 'opera_gx', 'edge', 'brave'];
  for (const b of allBrowsers) {
    const info     = BROWSER_INFO[b];
    const profiles = grouped[b] || [];
    const avail    = profiles.length > 0;

    const card = document.createElement('div');
    card.className = 'browser-card' + (avail ? '' : ' unavailable');
    card.dataset.browser = b;
    card.innerHTML = `
      <div class="browser-icon" style="background:${info.color}22">${info.emoji}</div>
      <div class="browser-name">${info.label}</div>
      <div class="browser-profiles">${avail ? profiles.length + ' profil(s)' : 'Non détecté'}</div>
    `;
    if (avail) {
      card.onclick = () => selectBrowser(role, b, profiles, card);
    }
    grid.appendChild(card);
  }
}

function selectBrowser(role, browser, profiles, cardEl) {
  const gridId = role === 'source' ? 'sourceBrowserGrid' : 'destBrowserGrid';
  document.querySelectorAll('#' + gridId + ' .browser-card').forEach(c => c.classList.remove('selected'));
  cardEl.classList.add('selected');

  const profileGroupId  = role === 'source' ? 'sourceProfileGroup'  : 'destProfileGroup';
  const profileSelectId = role === 'source' ? 'sourceProfileSelect' : 'destProfileSelect';
  const profileGroup    = document.getElementById(profileGroupId);
  const profileSelect   = document.getElementById(profileSelectId);
  profileSelect.innerHTML = '';
  profiles.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.path;
    opt.textContent = p.profile + ' — ' + p.path;
    profileSelect.appendChild(opt);
  });
  profileGroup.style.display = '';

  if (role === 'source') {
    state.sourceBrowser = browser;
    state.sourceProfile = profiles[0]?.path;
    profileSelect.onchange = () => { state.sourceProfile = profileSelect.value; };
    document.getElementById('step2Next').disabled = false;
    state.snapshotId = null;
    document.getElementById('step3Next').disabled = true;
    document.getElementById('scanBtn').disabled = false;
    resetCounters();
  } else {
    state.destBrowser = browser;
    state.destProfile = profiles[0]?.path;
    profileSelect.onchange = () => {
      state.destProfile = profileSelect.value;
      checkSameSource();
    };
    checkSameSource();
  }
}

function checkSameSource() {
  const same = state.sourceBrowser === state.destBrowser && state.sourceProfile === state.destProfile;
  document.getElementById('sameSourceWarning').style.display = same ? '' : 'none';
  document.getElementById('step4Next').disabled = !state.destBrowser || same;
}

// ---------------------------------------------------------------------------
// Step 3 — Data type selection & scan
// ---------------------------------------------------------------------------

function toggleDataType(card, type) {
  // Check if locked by subscription tier
  if (!FREE_TYPES.has(type) && state.subscriptionTier === 'free') {
    showPricingModal('pro');
    return;
  }

  card.classList.toggle('selected');
  if (card.classList.contains('selected')) {
    state.selectedDataTypes.add(type);
  } else {
    state.selectedDataTypes.delete(type);
  }
}

function resetCounters() {
  ['bookmarks','history','passwords','extensions','settings'].forEach(t => {
    const el = document.getElementById('count-' + t);
    if (el) el.textContent = 'Non scanné';
  });
}

async function scanBrowser() {
  const btn = document.getElementById('scanBtn');
  const statusEl = document.getElementById('scanStatus');
  const errorEl  = document.getElementById('scanError');
  errorEl.style.display = 'none';
  statusEl.style.display = '';
  btn.disabled = true;

  try {
    const types = Array.from(state.selectedDataTypes);
    const data = await api('POST', '/api/browsers/snapshot', {
      browser: state.sourceBrowser,
      profile: state.sourceProfile,
      data_types: types,
    });

    state.snapshotId = data.id;

    const summary = data.data_summary || {};
    Object.entries(summary).forEach(([type, count]) => {
      const el = document.getElementById('count-' + type);
      if (el) el.textContent = count.toLocaleString() + ' éléments';
    });

    if (data.status === 'error') {
      errorEl.textContent = '⚠️ Scan partiel : ' + (data.error_message || 'Certaines données inaccessibles');
      errorEl.style.display = '';
    }

    document.getElementById('step3Next').disabled = false;
    toast('Navigateur scanné — ' + Object.values(summary).reduce((a,b)=>a+b,0).toLocaleString() + ' éléments trouvés', 'success');
  } catch (e) {
    // If tier-related error, show upgrade modal
    if (e.message && e.message.includes('plan')) {
      showPricingModal('pro');
    } else {
      errorEl.textContent = '❌ ' + e.message;
      errorEl.style.display = '';
      toast('Scan échoué : ' + e.message, 'error');
    }
  } finally {
    statusEl.style.display = 'none';
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Step 4 → 5 — Start transfer
// ---------------------------------------------------------------------------

async function startTransfer() {
  goToStep(5);
  const types = Array.from(state.selectedDataTypes);

  const container = document.getElementById('transferProgress');
  container.innerHTML = '';
  types.forEach(type => {
    container.innerHTML += `
      <div class="progress-item" id="prog-${type}">
        <div class="progress-item-header">
          <span>${DATA_TYPE_EMOJI[type] || '📦'} ${type.charAt(0).toUpperCase() + type.slice(1)}</span>
          <span class="status-badge badge-pending" id="badge-${type}">En attente</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill" id="fill-${type}"></div>
        </div>
      </div>`;
  });

  types.forEach(type => {
    setBadge(type, 'running');
    setFill(type, 30);
  });

  try {
    const job = await api('POST', '/api/transfer/start', {
      source_snapshot_id: state.snapshotId,
      target_browser: state.destBrowser,
      target_profile: state.destProfile,
      data_types: types,
    });
    state.jobId = job.id;
    pollJob(types);
  } catch (e) {
    if (e.message && e.message.includes('plan')) {
      goToStep(3);
      showPricingModal('pro');
    } else {
      document.getElementById('transferError').textContent = '❌ ' + e.message;
      document.getElementById('transferError').style.display = '';
      types.forEach(t => { setBadge(t, 'error'); setFill(t, 100, true); });
    }
  }
}

async function pollJob(types) {
  let attempts = 0;
  const maxAttempts = 120;

  const poll = async () => {
    try {
      const job = await api('GET', '/api/transfer/status/' + state.jobId);

      if (job.status === 'running' || job.status === 'pending') {
        types.forEach(t => { setBadge(t, 'running'); setFill(t, 50 + Math.random() * 20); });
        if (attempts++ < maxAttempts) setTimeout(poll, 1000);
        return;
      }

      if (job.status === 'done') {
        const summary = JSON.parse(job.result_summary || '{}');
        types.forEach(t => { setBadge(t, 'done'); setFill(t, 100); });
        state.transferResult = summary;
        setTimeout(() => goToStep(6, summary), 800);
        return;
      }

      if (job.status === 'error') {
        types.forEach(t => { setBadge(t, 'error'); setFill(t, 100, true); });
        document.getElementById('transferError').textContent = '❌ ' + (job.error_message || 'Transfert échoué');
        document.getElementById('transferError').style.display = '';
      }
    } catch (e) {
      if (attempts++ < maxAttempts) setTimeout(poll, 2000);
    }
  };

  poll();
}

function setBadge(type, status) {
  const el = document.getElementById('badge-' + type);
  if (!el) return;
  const labels = { pending: 'En attente', running: 'En cours', done: 'Terminé', error: 'Erreur' };
  el.className = 'status-badge badge-' + status;
  el.textContent = labels[status] || status;
}

function setFill(type, pct, error = false) {
  const el = document.getElementById('fill-' + type);
  if (!el) return;
  el.style.width = pct + '%';
  if (error) el.style.background = 'var(--danger)';
  else if (pct >= 100) el.classList.add('done');
}

// ---------------------------------------------------------------------------
// Step 6 — Summary
// ---------------------------------------------------------------------------

function buildSummary(summary) {
  const grid = document.getElementById('summaryGrid');
  grid.innerHTML = '';
  Object.entries(summary).forEach(([type, count]) => {
    grid.innerHTML += `
      <div class="summary-item">
        <div style="font-size:1.5rem">${DATA_TYPE_EMOJI[type] || '📦'}</div>
        <div class="summary-count">${Number(count).toLocaleString()}</div>
        <div class="summary-label">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
      </div>`;
  });

  if (summary.passwords !== undefined) {
    document.getElementById('passwordNote').style.display = '';
  }
  if (summary.extensions !== undefined) {
    document.getElementById('extensionNote').style.display = '';
  }
}

function downloadReport() {
  const lines = [
    'WebFlow — Rapport de transfert',
    'Date : ' + new Date().toLocaleString(),
    'Source : ' + (BROWSER_INFO[state.sourceBrowser]?.label || state.sourceBrowser) + ' — ' + state.sourceProfile,
    'Destination : ' + (BROWSER_INFO[state.destBrowser]?.label || state.destBrowser) + ' — ' + state.destProfile,
    '',
    'Éléments transférés :',
  ];
  if (state.transferResult) {
    Object.entries(state.transferResult).forEach(([k, v]) => lines.push('  ' + k + ' : ' + v));
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'webflow-rapport-' + Date.now() + '.txt';
  a.click();
}

function startOver() {
  state.sourceBrowser = null;
  state.sourceProfile = null;
  state.snapshotId = null;
  state.destBrowser = null;
  state.destProfile = null;
  state.jobId = null;
  state.transferResult = null;
  // Reset selected types to match current tier
  if (state.subscriptionTier === 'free') {
    state.selectedDataTypes = new Set(['bookmarks', 'history']);
  } else {
    state.selectedDataTypes = new Set(['bookmarks', 'history', 'passwords', 'extensions', 'settings']);
  }
  showDash();
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function showDash() {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('pageDash').classList.add('active');
  state.currentStep = 0;
  document.getElementById('progressBar').style.display = 'none';

  const greetEl = document.getElementById('dashGreeting');
  if (greetEl && state.username) {
    greetEl.textContent = 'Bonjour, ' + state.username + ' ! 👋';
  }

  switchDashTab('new');
  updatePlanDetails();
}

function switchDashTab(tab) {
  ['new', 'transfers', 'plan', 'faq'].forEach(t => {
    const btn     = document.getElementById('dtab-' + t);
    const content = document.getElementById('dtab-content-' + t);
    if (btn)     btn.classList.toggle('active', t === tab);
    if (content) content.style.display = (t === tab) ? '' : 'none';
  });
}

function beginTransfer() {
  goToStep(2);
}

function showComingSoonToast() {
  toast('À venir pour Pro / Premium', 'info');
}

function updatePlanDetails() {
  const el = document.getElementById('planDetails');
  if (!el) return;
  const tier = state.subscriptionTier;
  const labels = { free: 'Free', beta: '🧪 Bêta', pro: '⚡ Pro', premium: '👑 Premium' };
  const label  = labels[tier] || 'Free';

  let html = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <span class="tier-badge ${tier === 'beta' ? 'pro' : tier}" style="font-size:0.85rem;padding:5px 14px">${label}</span>
      <span style="color:var(--muted);font-size:0.875rem">Plan actuel</span>
    </div>
  `;
  if (tier === 'beta') {
    html += `<div class="alert alert-info">🧪 Accès bêta — toutes les fonctionnalités disponibles gratuitement.</div>`;
  } else if (tier === 'free') {
    html += `<div class="alert alert-warning">Passez à Pro ou Premium pour accéder aux mots de passe, extensions et paramètres.</div>`;
  } else if (tier === 'pro') {
    html += `<div class="alert alert-info">⚡ Accès complet — sauf sync quotidienne et accès anticipé (Premium).</div>`;
  } else if (tier === 'premium') {
    html += `<div class="alert alert-info" style="border-color:rgba(255,196,77,0.4);color:#ffc44d">👑 Vous avez accès à toutes les fonctionnalités.</div>`;
  }
  el.innerHTML = html;
}

function toggleFaq(el) {
  el.nextElementSibling.classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Pricing modal
// ---------------------------------------------------------------------------

function showPricingModal(suggestedPlan) {
  const modal = document.getElementById('pricingModal');
  modal.style.display = 'flex';

  // Highlight suggested plan card
  if (suggestedPlan) {
    document.querySelectorAll('.pricing-card').forEach(c => c.style.transform = '');
    const target = document.getElementById('pcard-' + suggestedPlan);
    if (target) target.style.transform = 'scale(1.03)';
  }

  // Show current plan badge
  ['free','pro','premium'].forEach(t => {
    const b = document.getElementById('badge-' + t);
    if (b) b.style.display = (t === state.subscriptionTier) ? '' : 'none';
  });

  // Disable checkout buttons for current/lower tiers
  const tier = state.subscriptionTier;
  const btnPro = document.getElementById('btnCheckoutPro');
  const btnPremium = document.getElementById('btnCheckoutPremium');
  if (btnPro)     btnPro.disabled     = (tier === 'pro' || tier === 'premium');
  if (btnPremium) btnPremium.disabled = (tier === 'premium');

  document.getElementById('paymentPendingBox').style.display = 'none';
}

function closePricingModal() {
  document.getElementById('pricingModal').style.display = 'none';
}

async function startCheckout(plan) {
  if (!state.paymentsEnabled) {
    showComingSoonModal();
    return;
  }

  const btn = document.getElementById('btnCheckout' + plan.charAt(0).toUpperCase() + plan.slice(1));
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>'; }

  try {
    const data = await api('POST', '/api/billing/checkout/' + plan);
    window.open(data.url, '_blank');
    document.getElementById('paymentPendingBox').style.display = 'flex';
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = 'Souscrire ' + plan.charAt(0).toUpperCase() + plan.slice(1) + ' →'; }
  }
}

async function refreshSubscription() {
  await loadSubscriptionStatus();
  closePricingModal();
  toast('Abonnement mis à jour : ' + state.subscriptionTier, 'success');
  resetCounters();
}

async function openBillingPortal() {
  if (!state.paymentsEnabled) {
    showComingSoonModal();
    return;
  }
  try {
    const data = await api('POST', '/api/billing/portal');
    window.open(data.url, '_blank');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  }
}

function showComingSoonModal() {
  document.getElementById('comingSoonModal').style.display = 'flex';
}

function closeComingSoonModal() {
  document.getElementById('comingSoonModal').style.display = 'none';
}

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function toast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const div = document.createElement('div');
  div.className = 'toast ' + type;
  div.textContent = message;
  container.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}
