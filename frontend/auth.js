/* auth.js — JWT login, workspace switch, session (Sprint 2 portal v0) */

var _authUser = '';
var _authWorkspace = null;

function getAuthToken() {
  return localStorage.getItem('sd_auth_token') || '';
}

function authHeaders() {
  var token = getAuthToken();
  return token ? { Authorization: 'Bearer ' + token } : {};
}

function saveAuthSession(data) {
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

function updateUserUI(me) {
  var user = (me && me.user) || {};
  var name = user.username || localStorage.getItem('sd_user') || '用户';
  _authUser = name;
  var avatar = document.getElementById('user-avatar');
  var userName = document.getElementById('user-name');
  var dropName = document.getElementById('user-drop-name');
  var dropRole = document.getElementById('user-drop-role');
  if (avatar) avatar.textContent = name.charAt(0).toUpperCase();
  if (userName) userName.textContent = name;
  if (dropName) dropName.textContent = name;
  if (dropRole) dropRole.textContent = user.role || 'member';
  var wsLabel = document.getElementById('workspace-label');
  if (wsLabel && me && me.workspace) {
    wsLabel.textContent = me.workspace.label || me.workspace.tenant_type || 'Personal';
  }
}

async function loadWorkspaces() {
  var sel = document.getElementById('workspace-select');
  if (!sel) return;
  try {
    var r = await api('/api/workspaces/list');
    if (!r.ok) return;
    var d = await r.json();
    sel.innerHTML = (d.workspaces || []).map(function (w) {
      var selected = w.tenant_id === d.active_tenant_id ? ' selected' : '';
      var label = w.label || w.tenant_type || w.tenant_id;
      return '<option value="' + w.tenant_id + '"' + selected + '>' + label + '</option>';
    }).join('');
  } catch (e) {
    console.warn('loadWorkspaces failed', e);
  }
}

async function switchWorkspace(tenantId) {
  if (!tenantId) return;
  try {
    var r = await api('/api/workspaces/switch', {
      method: 'POST',
      body: JSON.stringify({ tenant_id: tenantId }),
    });
    if (!r.ok) {
      toast('切换工作区失败', 'err');
      return;
    }
    var d = await r.json();
    saveAuthSession(d);
    updateUserUI({ user: d.user, workspace: d.workspace });
    _sessionId = '';
    localStorage.removeItem('sd_session');
    localStorage.removeItem('skillos_session_id');
    if (typeof refreshSkillList === 'function') refreshSkillList();
    toast('已切换至 ' + (d.workspace.label || d.workspace.tenant_type), 'success');
  } catch (e) {
    toast('切换工作区失败: ' + e.message, 'err');
  }
}

async function initAuth() {
  if (window.location.pathname.indexOf('login') >= 0) return;

  var token = getAuthToken();
  if (!token) {
    window.location.href = '/login.html';
    return;
  }

  try {
    var r = await api('/api/auth/me');
    var d = await r.json();
    if (!d.user || d.user.error || d.user.username === 'anonymous') {
      localStorage.removeItem('sd_auth_token');
      localStorage.removeItem('sd_workspace');
      window.location.href = '/login.html';
      return;
    }
    if (d.workspace) localStorage.setItem('sd_workspace', JSON.stringify(d.workspace));
    updateUserUI(d);
    await loadWorkspaces();
    if (typeof refreshSkillList === 'function') refreshSkillList();
    if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
    setDot('on');
  } catch (e) {
    console.warn('initAuth failed', e);
    setDot('');
  }
}

function doLogout() {
  _authUser = '';
  _authWorkspace = null;
  localStorage.removeItem('sd_auth_token');
  localStorage.removeItem('sd_token');
  localStorage.removeItem('sd_user');
  localStorage.removeItem('sd_workspace');
  localStorage.removeItem('sd_session');
  window.location.href = '/login.html';
}

async function createTeam(displayName) {
  if (!displayName) {
    displayName = prompt('团队名称', '我的团队');
    if (!displayName || !displayName.trim()) return;
    displayName = displayName.trim();
  }
  try {
    var r = await api('/api/orgs', {
      method: 'POST',
      body: JSON.stringify({ display_name: displayName }),
    });
    if (!r.ok) {
      var err = await r.json().catch(function () { return {}; });
      toast(err.detail || '创建失败', 'error');
      return;
    }
    var d = await r.json();
    saveAuthSession(d);
    updateUserUI({ user: d.user, workspace: d.org ? { tenant_id: d.org.tenant_id, label: d.org.display_name, org_id: d.org.org_id, tenant_type: 'organization' } : d.workspace });
    await loadWorkspaces();
    if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
    toast('团队「' + displayName + '」已创建', 'success');
  } catch (e) {
    toast('创建团队失败: ' + e.message, 'error');
  }
}
