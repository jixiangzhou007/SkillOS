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
    },

    showChat() {
      this.navigate('chat-view');
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
    mode: localStorage.getItem('sd_mode') || 'create',
    selectedModel: localStorage.getItem('sd_model') || 'deepseek-v4-flash',
    autoMode: localStorage.getItem('sd_auto') === 'true',
    sessionId: localStorage.getItem('sd_session') || '',
    ttsEnabled: true,
    messages: [],

    addMessage(role, text) {
      const msg = { role, text, ts: Date.now() };
      this.messages.push(msg);
      return msg;
    },

    setMode(m) {
      this.mode = m;
      localStorage.setItem('sd_mode', m);
    },

    setModel(m) {
      this.selectedModel = m;
      localStorage.setItem('sd_model', m);
    },

    setSessionId(id) {
      this.sessionId = id;
      if (id) localStorage.setItem('sd_session', id);
    },

    toggleAuto() {
      this.autoMode = !this.autoMode;
      localStorage.setItem('sd_auto', String(this.autoMode));
    }
  });

  Alpine.store('auth', {
    user: localStorage.getItem('sd_user') || '',
    token: localStorage.getItem('sd_auth_token') || '',
    workspace: null,
    initialized: false,

    get isLoggedIn() {
      return !!this.token && this.user !== '';
    },

    authHeaders() {
      return this.token ? { Authorization: 'Bearer ' + this.token } : {};
    },

    saveSession(data) {
      this.user = data.user || data.username || '';
      this.token = data.token || '';
      this.workspace = data.workspace || null;
      if (data.token) localStorage.setItem('sd_auth_token', data.token);
      if (data.user || data.username) localStorage.setItem('sd_user', data.user || data.username);
    },

    logout() {
      this.user = '';
      this.token = '';
      this.workspace = null;
      ['sd_auth_token', 'sd_token', 'sd_user', 'sd_workspace', 'sd_session'].forEach(k => localStorage.removeItem(k));
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
