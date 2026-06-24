/* SkillOS — Alpine.js Bridge
 *
 * Initializes Alpine stores and provides backward-compatible
 * getter/setter aliases for all legacy global variables.
 *
 * Loaded AFTER the 14 script files so legacy var declarations
 * are overridden by reactive Alpine-backed aliases.
 */

document.addEventListener('alpine:init', () => {
  // ── Stores ─────────────────────────────────────────────

  Alpine.store('nav', {
    currentView: 'chat-view',
    primaryNav: 'extract',
    knowledgeTab: 'dashboard',
    barVisible: true,
    dot: '',
    status: '就绪',
    currentSkill: null,
    currentTab: 'overview',
    settingsTab: 'model',
    skillListTab: 'mine',

    navigate(viewId) {
      this.currentView = viewId;
      this.barVisible = (viewId === 'chat-view');
      if (viewId === 'chat-view') this.primaryNav = 'extract';
      else if (viewId === 'hub-view') this.primaryNav = 'market';
      else if (viewId === 'knowledge-unified-view') this.primaryNav = 'knowledge';
    },

    goTo(viewId) {
      this.navigate(viewId);
      document.querySelectorAll('.main-view').forEach(function(v) { v.classList.remove('active'); });
      var el = document.getElementById(viewId);
      if (el) el.classList.add('active');
      var bar = document.getElementById('bar');
      if (bar) bar.style.display = (viewId === 'chat-view') ? 'flex' : 'none';
    },

    setPrimaryNav(id) {
      this.primaryNav = id;
    },

    showChat() {
      this.goTo('chat-view');
      this.currentSkill = null;
    },

    setDot(c) {
      this.dot = c;
    },

    setStatus(s) {
      this.status = s;
    }
  });

  Alpine.store('chat', {
    mode: localStorage.getItem(StorageKeys.MODE) || 'create',
    selectedModel: localStorage.getItem(StorageKeys.MODEL) || 'deepseek-v4-flash',
    autoMode: localStorage.getItem(StorageKeys.AUTO) === 'true',
    sessionId: localStorage.getItem(StorageKeys.SESSION) || '',
    ttsEnabled: true,
    messages: [],

    addMessage(role, text) {
      const msg = { role, text, ts: Date.now() };
      this.messages.push(msg);
      return msg;
    },

    setMode(m) {
      this.mode = m;
      localStorage.setItem(StorageKeys.MODE, m);
    },

    setModel(m) {
      this.selectedModel = m;
      localStorage.setItem(StorageKeys.MODEL, m);
    },

    setSessionId(id) {
      this.sessionId = id;
      if (id) localStorage.setItem(StorageKeys.SESSION, id);
      else localStorage.removeItem(StorageKeys.SESSION);
    },

    toggleAuto() {
      this.autoMode = !this.autoMode;
      localStorage.setItem(StorageKeys.AUTO, String(this.autoMode));
    }
  });

  Alpine.store('auth', {
    user: localStorage.getItem(StorageKeys.USER) || '',
    token: localStorage.getItem(StorageKeys.AUTH_TOKEN) || '',
    workspace: null,
    initialized: false,

    get isLoggedIn() {
      return !!this.token && this.user !== '';
    },

    authHeaders() {
      return this.token ? { Authorization: 'Bearer ' + this.token } : {};
    },

    get avatarLetter() {
      return (this.user || '?').charAt(0).toUpperCase();
    },

    get workspaceLabel() {
      if (!this.workspace) return '';
      return this.workspace.label || this.workspace.tenant_type || '';
    },

    saveSession(data) {
      if (data.token) { this.token = data.token; localStorage.setItem(StorageKeys.AUTH_TOKEN, data.token); }
      if (data.user) {
        const name = data.user.username || data.user;
        this.user = typeof name === 'string' ? name : (data.user.username || '');
        localStorage.setItem(StorageKeys.USER, this.user);
      }
      if (data.workspace) {
        this.workspace = data.workspace;
        localStorage.setItem(StorageKeys.WORKSPACE, JSON.stringify(data.workspace));
      }
    },

    async init() {
      if (window.location.pathname.indexOf('login') >= 0) return;
      if (!this.token) { window.location.href = '/login.html'; return; }
      try {
        const r = await fetch((window.API || '') + '/api/auth/me', {
          headers: { Authorization: 'Bearer ' + this.token }
        });
        const d = await r.json();
        if (!d.user || d.user.error || d.user.username === 'anonymous') {
          this._clearAndRedirect();
          return;
        }
        this.user = d.user.username;
        if (d.workspace) this.workspace = d.workspace;
        this.initialized = true;
        // Legacy UI update
        if (typeof loadWorkspaces === 'function') loadWorkspaces();
        if (typeof refreshSkillList === 'function') refreshSkillList();
        if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
        if (typeof setDot === 'function') setDot('on');
      } catch (e) {
        console.warn('initAuth failed', e);
        if (typeof setDot === 'function') setDot('');
      }
    },

    async switchWorkspace(tenantId) {
      if (!tenantId) return;
      try {
        const r = await fetch((window.API || '') + '/api/workspaces/switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + this.token },
          body: JSON.stringify({ tenant_id: tenantId }),
        });
        if (!r.ok) { toast('切换工作区失败', 'err'); return; }
        const d = await r.json();
        this.saveSession(d);
        // Reset session
        const chatStore = Alpine.store('chat');
        chatStore.sessionId = '';
        localStorage.removeItem(StorageKeys.SESSION);
        localStorage.removeItem('skillos_session_id');
        if (typeof refreshSkillList === 'function') refreshSkillList();
        toast('已切换至 ' + (d.workspace.label || d.workspace.tenant_type), 'success');
      } catch (e) {
        toast('切换工作区失败: ' + e.message, 'err');
      }
    },

    async createTeam(displayName) {
      if (!displayName) {
        displayName = prompt('团队名称', '我的团队');
        if (!displayName || !displayName.trim()) return;
        displayName = displayName.trim();
      }
      try {
        const r = await fetch((window.API || '') + '/api/orgs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + this.token },
          body: JSON.stringify({ display_name: displayName }),
        });
        if (!r.ok) { const err = await r.json().catch(() => ({})); toast(err.detail || '创建失败', 'error'); return; }
        const d = await r.json();
        this.saveSession(d);
        if (typeof loadWorkspaces === 'function') loadWorkspaces();
        if (typeof updateAdminNavVisibility === 'function') updateAdminNavVisibility();
        toast('团队「' + displayName + '」已创建', 'success');
      } catch (e) {
        toast('创建团队失败: ' + e.message, 'error');
      }
    },

    logout() {
      this.user = '';
      this.token = '';
      this.workspace = null;
      [StorageKeys.AUTH_TOKEN, StorageKeys.USER, StorageKeys.WORKSPACE, StorageKeys.SESSION, 'sd_auth_token', 'sd_token', 'sd_user', 'sd_workspace', 'sd_session'].forEach(function(k) { localStorage.removeItem(k); });
      window.location.href = '/login.html';
    },

    _clearAndRedirect() {
      localStorage.removeItem(StorageKeys.AUTH_TOKEN);
      localStorage.removeItem(StorageKeys.WORKSPACE);
      window.location.href = '/login.html';
    }
  });

  Alpine.store('skill', {
    allSkillsCache: [],
    filteredSkills: [],

    setCache(skills) {
      this.allSkillsCache = skills;
      this.filteredSkills = skills;
    },

    filter(query, tab) {
      let list = this.allSkillsCache;
      if (query) {
        const q = query.toLowerCase();
        list = list.filter(s => s.name.toLowerCase().includes(q));
      }
      this.filteredSkills = list;
      return list;
    }
  });

  // ── Mark Alpine as ready ─────────────────────────────
  window.__alpineReady = true;
});

// ── Backward-compatible getter/setter aliases ───────────
// These override legacy 'var' declarations with reactive
// Alpine-backed properties. Old code continues to read/write
// these globals transparently.

function _defineGlobalAlias(name, storeName, key) {
  let storeReady = false;
  Object.defineProperty(window, name, {
    get() {
      try {
        return Alpine.store(storeName)[key];
      } catch (e) {
        return undefined;
      }
    },
    set(v) {
      try {
        Alpine.store(storeName)[key] = v;
      } catch (e) {
        // Store not initialized yet, defer to localStorage fallback
      }
    },
    configurable: true,
    enumerable: true
  });
}

// Nav store aliases
_defineGlobalAlias('_mode', 'chat', 'mode');
_defineGlobalAlias('_currentSkill', 'nav', 'currentSkill');
_defineGlobalAlias('_currentTab', 'nav', 'currentTab');
_defineGlobalAlias('_settingsTab', 'nav', 'settingsTab');
_defineGlobalAlias('_skillListTab', 'nav', 'skillListTab');

// Chat store aliases
_defineGlobalAlias('_selectedModel', 'chat', 'selectedModel');
_defineGlobalAlias('_autoMode', 'chat', 'autoMode');
_defineGlobalAlias('_sessionId', 'chat', 'sessionId');

// Skill store aliases
_defineGlobalAlias('_allSkillsCache', 'skill', 'allSkillsCache');

// Auth aliases
_defineGlobalAlias('_authUser', 'auth', 'user');
_defineGlobalAlias('_authWorkspace', 'auth', 'workspace');
