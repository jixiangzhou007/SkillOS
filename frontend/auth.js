/* SkillOS — Authentication (Alpine.js)
 * Phase 8 migration. All auth logic now in Alpine.store('auth').
 * Legacy functions kept as thin wrappers for backward compat.
 */

// Legacy globals — aliased via alpine-bridge.js getter/setter
var _authUser = '';
var _authWorkspace = null;

function getAuthToken() {
  try { return Alpine.store('auth').token; } catch (e) { return localStorage.getItem('sd_auth_token') || ''; }
}

function authHeaders() {
  try { return Alpine.store('auth').authHeaders(); } catch (e) {
    const token = localStorage.getItem('sd_auth_token') || '';
    return token ? { Authorization: 'Bearer ' + token } : {};
  }
}

function saveAuthSession(data) {
  try { Alpine.store('auth').saveSession(data); } catch (e) {
    if (data.token) localStorage.setItem('sd_auth_token', data.token);
    if (data.user && data.user.username) {
      localStorage.setItem('sd_user', data.user.username);
      _authUser = data.user.username;
    }
    if (data.workspace) {
      localStorage.setItem('sd_workspace', JSON.stringify(data.workspace));
      _authWorkspace = data.workspace;
    }
  }
}

function updateUserUI(me) {
  // Alpine bindings handle this reactively. Kept for backward compat.
  const user = (me && me.user) || {};
  const name = user.username || localStorage.getItem('sd_user') || '用户';
  _authUser = name;
  try { Alpine.store('auth').user = name; } catch (e) {}
  try { if (me && me.workspace) Alpine.store('auth').workspace = me.workspace; } catch (e) {}
}

async function loadWorkspaces() {
  const sel = document.getElementById('workspace-select');
  if (!sel) return;
  try {
    const r = await api('/api/workspaces/list');
    if (!r.ok) return;
    const d = await r.json();
    sel.innerHTML = (d.workspaces || []).map(function (w) {
      const selected = w.tenant_id === d.active_tenant_id ? ' selected' : '';
      const label = w.label || w.tenant_type || w.tenant_id;
      return '<option value="' + w.tenant_id + '"' + selected + '>' + label + '</option>';
    }).join('');
  } catch (e) {
    console.warn('loadWorkspaces failed', e);
  }
}

async function switchWorkspace(tenantId) {
  try { await Alpine.store('auth').switchWorkspace(tenantId); } catch (e) {
    // Legacy fallback
    if (!tenantId) return;
    try {
      const r = await api('/api/workspaces/switch', {
        method: 'POST', body: JSON.stringify({ tenant_id: tenantId }),
      });
      if (!r.ok) { toast('切换工作区失败', 'err'); return; }
      const d = await r.json();
      saveAuthSession(d);
      updateUserUI({ user: d.user, workspace: d.workspace });
      _sessionId = ''; localStorage.removeItem('sd_session'); localStorage.removeItem('skillos_session_id');
      if (typeof refreshSkillList === 'function') refreshSkillList();
      toast('已切换至 ' + (d.workspace.label || d.workspace.tenant_type), 'success');
    } catch (e2) { toast('切换工作区失败: ' + e2.message, 'err'); }
  }
}

async function initAuth() {
  try { await Alpine.store('auth').init(); } catch (e) {
    // Legacy fallback (only if Alpine not ready)
    if (window.location.pathname.indexOf('login') >= 0) return;
    const token = getAuthToken();
    if (!token) { window.location.href = '/login.html'; return; }
    try {
      const r = await api('/api/auth/me');
      const d = await r.json();
      if (!d.user || d.user.error || d.user.username === 'anonymous') {
        localStorage.removeItem('sd_auth_token'); localStorage.removeItem('sd_workspace');
        window.location.href = '/login.html'; return;
      }
      if (d.workspace) localStorage.setItem('sd_workspace', JSON.stringify(d.workspace));
      updateUserUI(d);
      await loadWorkspaces();
      if (typeof refreshSkillList === 'function') refreshSkillList();
      if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
      setDot('on');
    } catch (e2) { console.warn('initAuth failed', e2); setDot(''); }
  }
}

function doLogout() {
  try { Alpine.store('auth').logout(); } catch (e) {
    _authUser = ''; _authWorkspace = null;
    ['sd_auth_token', 'sd_token', 'sd_user', 'sd_workspace', 'sd_session'].forEach(k => localStorage.removeItem(k));
    window.location.href = '/login.html';
  }
}

async function createTeam(displayName) {
  try { await Alpine.store('auth').createTeam(displayName); } catch (e) {
    if (!displayName) {
      displayName = prompt('团队名称', '我的团队');
      if (!displayName || !displayName.trim()) return;
      displayName = displayName.trim();
    }
    try {
      const r = await api('/api/orgs', { method: 'POST', body: JSON.stringify({ display_name: displayName }) });
      if (!r.ok) { const err = await r.json().catch(() => ({})); toast(err.detail || '创建失败', 'error'); return; }
      const d = await r.json();
      saveAuthSession(d);
      updateUserUI({ user: d.user, workspace: d.org ? { tenant_id: d.org.tenant_id, label: d.org.display_name, org_id: d.org.org_id, tenant_type: 'organization' } : d.workspace });
      await loadWorkspaces();
      if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
      toast('团队「' + displayName + '」已创建', 'success');
    } catch (e2) { toast('创建团队失败: ' + e2.message, 'error'); }
  }
}
