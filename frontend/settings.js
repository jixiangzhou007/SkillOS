/* SkillOS — Settings (Alpine.js)
 * Phase 6 migration. 4 subtabs (model/usage/skills/voice) + 2 modals.
 */

// ── Utilities (keep global for backward compat) ──────

function renderModelList(models, activeId) {
  var container = document.getElementById('model-list-container');
  if (!container) { console.warn('renderModelList: container not found'); return; }
  if (!models || !models.length) { container.innerHTML = ''; return; }
  container.innerHTML = models.map(function(m, i) {
    var isActive = m.id === activeId;
    return '<div class="model-card' + (isActive ? ' active' : '') + '">' +
      '<div class="model-card-header">' +
        '<span class="model-card-name">' + (m.label || '').replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</span>' +
        '<span class="model-card-id">' + (m.id || '').replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</span>' +
        (isActive ? '<span class="model-card-badge current">当前</span>' : '') +
      '</div>' +
      '<div class="model-card-url">' + (m.base_url || '').replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</div>' +
      '<div class="model-card-actions">' +
        '<button class="nav-sm" onclick="openModelModal(' + i + ')" type="button">编辑</button>' +
        (!isActive ? '<button class="nav-sm" style="border-color:var(--accent);color:var(--accent)" onclick="activateModel(' + i + ')" type="button">启用</button>' : '') +
        '<button class="nav-sm" style="color:var(--err)" onclick="openDeleteModal(' + i + ')" type="button">删除</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

function getModels() {
  try { return JSON.parse(localStorage.getItem(StorageKeys.MODELS) || '[]'); } catch (e) { return []; }
}
function saveModels(models) { localStorage.setItem(StorageKeys.MODELS, JSON.stringify(models)); }

function voiceStorageKey(key) {
  var map = {
    asr_engine: StorageKeys.ASR_ENGINE,
    tts_backend: StorageKeys.TTS_BACKEND,
    tts_voice: StorageKeys.TTS_VOICE,
    tts_speed: StorageKeys.TTS_SPEED,
    tts_emotion: StorageKeys.TTS_EMOTION
  };
  return map[key] || ('sd_' + key);
}

function getDefaultModels() {
  return [
    { id: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash', api_key: '', base_url: 'https://api.deepseek.com' },
    { id: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro', api_key: '', base_url: 'https://api.deepseek.com' },
  ];
}

// ── Alpine component ──────────────────────────────────

function settingsView() {
  return {
    tab: 'model',

    // Model tab
    models: [],
    activeModelId: '',
    modelModalOpen: false,
    editingIndex: -1,            // -1 = add mode
    editLabel: '',
    editId: '',
    editUrl: '',
    deleteModalOpen: false,
    deleteTargetIndex: -1,

    // Usage tab
    usage: null,
    usageError: '',
    byokKey: '',

    // Skills tab
    skills: [],
    disabledSkills: [],

    // Voice tab
    ttsBackend: 'edge',
    ttsVoice: 'Xiaoxiao (Natural)',
    ttsSpeed: '1.1',
    ttsEmotion: 'neutral',
    asrEngine: 'whisper',

    init() {
      this.loadModels();
      // Restore tab from store
      this.tab = Alpine.store('nav').settingsTab || 'model';
    },

    switchTab(t) {
      this.tab = t;
      Alpine.store('nav').settingsTab = t;
      if (t === 'model') this.loadModels();
      else if (t === 'usage') this.loadUsage();
      else if (t === 'skills') this.loadSkills();
      else if (t === 'voice') this.loadVoice();
    },

    // ── Model CRUD ─────────────────────────────

    loadModels() {
      let models = getModels();
      if (!models.length) { models = getDefaultModels(); saveModels(models); }
      this.models = models;
      this.activeModelId = localStorage.getItem(StorageKeys.MODEL) || 'deepseek-v4-flash';
      var self = this;
      setTimeout(function() { renderModelList(self.models, self.activeModelId); }, 100);
    },

    openModelModal(index) {
      this.editingIndex = index;
      if (index < 0) {
        this.editLabel = '';
        this.editId = '';
        this.editUrl = 'https://api.deepseek.com';
      } else {
        const m = this.models[index];
        if (!m) return;
        this.editLabel = m.label || '';
        this.editId = m.id || '';
        this.editUrl = m.base_url || '';
      }
      this.modelModalOpen = true;
    },

    testConnection() {
      var url = this.editUrl.trim();
      var key = this.editId.trim();
      if (!url) { toast('请先填写 API 地址', 'warn'); return; }
      toast('测试连接中…', 'info');
      fetch(url + '/models', {
        headers: key ? { 'Authorization': 'Bearer ' + key } : {},
      }).then(function(r){
        if (r.ok) { toast('连接成功', 'success'); }
        else { toast('连接失败: HTTP ' + r.status, 'error'); }
      }).catch(function(e){
        toast('连接失败: ' + e.message, 'error');
      });
    },

    closeModelModal() {
      this.modelModalOpen = false;
      this.editingIndex = -1;
    },

    saveModel() {
      const label = this.editLabel.trim();
      const id = this.editId.trim();
      const url = this.editUrl.trim();
      if (!label || !id || !url) { toast('请填写所有字段', 'error'); return; }

      let models = getModels();
      if (this.editingIndex < 0) {
        models.push({ id, label, base_url: url, api_key: '' });
      } else {
        const oldId = models[this.editingIndex].id;
        models[this.editingIndex] = { id, label, base_url: url, api_key: '' };
        if (localStorage.getItem(StorageKeys.MODEL) === oldId) {
          localStorage.setItem(StorageKeys.MODEL, id);
          this.activeModelId = id;
        }
      }
      saveModels(models);
      refreshModelSelect();
      this.models = models; this.activeModelId = localStorage.getItem(StorageKeys.MODEL) || models[0].id;
      var self = this; setTimeout(function() { renderModelList(self.models, self.activeModelId); }, 100);
      this.closeModelModal();
    },

    activateModel(i) {
      const m = this.models[i];
      if (!m) return;
      localStorage.setItem(StorageKeys.MODEL, m.id);
      this.activeModelId = m.id;
      if (typeof _selectedModel !== 'undefined') _selectedModel = m.id;
      const sel = document.getElementById('model-select');
      if (sel) sel.value = m.id;
      refreshModelSelect();
      var self = this; setTimeout(function() { renderModelList(self.models, self.activeModelId); }, 100);
      setStatus('model: ' + m.label);
    },

    // Delete modal
    openDeleteModal(i) {
      if (i < 0 || i >= this.models.length) return;
      this.deleteTargetIndex = i;
      this.deleteModalOpen = true;
    },

    closeDeleteModal() {
      this.deleteModalOpen = false;
      this.deleteTargetIndex = -1;
    },

    confirmDelete() {
      const i = this.deleteTargetIndex;
      this.closeDeleteModal();
      if (i < 0) return;
      let models = getModels();
      if (i >= models.length) return;
      const m = models[i];
      models.splice(i, 1);
      if (!models.length) models = getDefaultModels();
      saveModels(models);
      if (localStorage.getItem(StorageKeys.MODEL) === m.id) {
        localStorage.setItem(StorageKeys.MODEL, models[0].id);
        this.activeModelId = models[0].id;
        if (typeof _selectedModel !== 'undefined') _selectedModel = models[0].id;
      }
      refreshModelSelect();
      this.models = models; this.activeModelId = localStorage.getItem(StorageKeys.MODEL) || models[0].id;
      var self = this; setTimeout(function() { renderModelList(self.models, self.activeModelId); }, 100);
    },

    // ── Usage ─────────────────────────────────

    async loadUsage() {
      this.usage = null;
      this.usageError = '';
      try {
        const r = await api('/api/usage/me');
        if (!r.ok) { this.usageError = '无法加载用量（请先登录）'; return; }
        this.usage = await r.json();
      } catch (e) {
        this.usageError = '加载失败: ' + e.message;
      }
    },

    get skillPct() {
      if (!this.usage) return 0;
      return this.usage.skills.limit ? Math.min(100, Math.round(this.usage.skills.used / this.usage.skills.limit * 100)) : 0;
    },
    get llmPct() {
      if (!this.usage) return 0;
      return this.usage.llm_calls.limit ? Math.min(100, Math.round(this.usage.llm_calls.used / this.usage.llm_calls.limit * 100)) : 0;
    },

    async saveByok(enabled) {
      const key = this.byokKey.trim();
      if (enabled && key.length < 8) { toast('API Key 至少 8 个字符', 'error'); return; }
      const r = await api('/api/usage/byok', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, api_key: key }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        toast(err.detail || '保存失败', 'error');
        return;
      }
      toast(enabled ? 'BYOK 已启用' : 'BYOK 已关闭');
      this.loadUsage();
    },

    async enableProPlan() {
      const code = document.getElementById('pro-beta-code')?.value || '';
      const r = await api('/api/billing/enable-pro', {
        method: 'POST', body: JSON.stringify({ beta_code: code }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        toast(err.detail || '启用失败', 'error');
        return;
      }
      toast('Personal Pro 已启用');
      this.loadUsage();
    },

    // ── Skills ────────────────────────────────

    async loadSkills() {
      try {
        const r = await api('/api/skills/');
        this.skills = await r.json();
        this.disabledSkills = JSON.parse(localStorage.getItem(StorageKeys.DISABLED_SKILLS) || '[]');
      } catch (e) {
        this.skills = [];
      }
    },

    isSkillEnabled(name) { return !this.disabledSkills.includes(name); },

    toggleSkill(name) {
      let disabled = JSON.parse(localStorage.getItem(StorageKeys.DISABLED_SKILLS) || '[]');
      if (disabled.includes(name)) {
        disabled = disabled.filter(n => n !== name);
      } else {
        disabled.push(name);
      }
      localStorage.setItem(StorageKeys.DISABLED_SKILLS, JSON.stringify(disabled));
      this.disabledSkills = disabled;
    },

    async deleteSkill(name) {
      if (!confirm('确定删除「' + name + '」及全部数据？')) return;
      const r = await api('/api/skills/' + encodeURIComponent(name), { method: 'DELETE' });
      const d = await r.json();
      if (d.deleted) {
        addMsg('sys', '已删除: ' + name);
        refreshSkillList();
        this.loadSkills();
      } else {
        addMsg('sys', '删除失败: ' + (d.error || '未知错误'));
      }
    },

    // ── Voice ─────────────────────────────────

    loadVoice() {
      this.ttsBackend = localStorage.getItem(StorageKeys.TTS_BACKEND) || 'edge';
      this.ttsVoice = localStorage.getItem(StorageKeys.TTS_VOICE) || 'Xiaoxiao (Natural)';
      this.ttsSpeed = localStorage.getItem(StorageKeys.TTS_SPEED) || '1.1';
      this.ttsEmotion = localStorage.getItem(StorageKeys.TTS_EMOTION) || 'neutral';
      this.asrEngine = localStorage.getItem(StorageKeys.ASR_ENGINE) || 'whisper';
    },

    get edgeVoices() { return ['Xiaoxiao (Natural)', 'Yunxi (Warm)', 'Yunyang (News)', 'Xiaoyi (Lively)']; },
    get omniVoices() { return ['Default (Neutral)', 'Female Warm', 'Male Deep', 'Energetic']; },
    get voiceList() { return this.ttsBackend === 'omnivoice' ? this.omniVoices : this.edgeVoices; },

    saveVoiceSetting(key, value) {
      localStorage.setItem(voiceStorageKey(key), value);
    },

    onTTSBackendChange() {
      localStorage.setItem(StorageKeys.TTS_BACKEND, this.ttsBackend);
    }
  };
}

// ── Backward-compatible wrappers ─────────────────────

function switchSettings(t) {
  const el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x) { el.__x.$data.switchTab(t); return; }
  // Legacy fallback
  document.querySelectorAll('#settings-view .tab').forEach(function (b) {
    b.classList.toggle('active', b.getAttribute('data-tab') === t);
  });
  const content = document.getElementById('s-content');
  if (!content) return;
  if (t === 'model') loadModelSettings(content);
  else if (t === 'usage') loadUsageSettings(content);
  else if (t === 'skills') loadSkillSettings(content);
  else if (t === 'voice') loadVoiceSettings(content);
}

function showSettings() {
  if (window.__alpineReady) {
    Alpine.store('nav').goTo('settings-view');
  } else {
    switchMainView('settings-view');
    document.getElementById('bar').style.display = 'none';
  }
  switchSettings('model');
}

function refreshModelSelect() {
  const sel = document.getElementById('model-select');
  if (!sel) return;
  let models = getModels();
  if (!models.length) models = getDefaultModels();
  var current = localStorage.getItem(StorageKeys.MODEL) || (typeof _selectedModel !== 'undefined' ? _selectedModel : '') || '';
  // Ensure current model exists in list
  var found = models.some(function(m) { return m.id === current; });
  if (!found) current = models[0].id;
  sel.innerHTML = models.map(function (m) {
    const label = (m.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return '<option value="' + m.id + '"' + (m.id === current ? ' selected' : '') + '>' + label + '</option>';
  }).join('');
  sel.value = current;
}

// ── Legacy loaders (keep for backward compat) ─────

function loadModelSettings(el) {
  el.innerHTML = '<div style="color:var(--text3)">请通过设置面板管理模型</div>';
}
function loadUsageSettings(el) { loadModelSettings(el); }
function loadSkillSettings(el) { loadModelSettings(el); }
function loadVoiceSettings(el) { loadModelSettings(el); }

function activateModel(i) {
  const el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x) { el.__x.$data.activateModel(i); return; }
  let models = getModels();
  if (i < 0 || i >= models.length) return;
  localStorage.setItem(StorageKeys.MODEL, models[i].id);
  if (typeof _selectedModel !== 'undefined') _selectedModel = models[i].id;
  document.getElementById('model-select').value = models[i].id;
  refreshModelSelect();
  setTimeout(function() { renderModelList(models, models[i].id); }, 100);
}

function openModelModal(i) {
  // Try Alpine component first
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) {
    el.__x.$data.openModelModal(i);
    return;
  }
  // Fallback: direct DOM manipulation
  var models = getModels();
  if (i < 0) {
    // Add mode
    var modal = document.querySelector('#settings-view .modal-overlay');
    if (modal) modal.style.display = 'flex';
  } else if (i >= 0 && i < models.length) {
    var m = models[i];
    // Set form fields manually
    var labelInput = document.querySelector('#settings-view input[x-model=\"editLabel\"]');
    var idInput = document.querySelector('#settings-view input[x-model=\"editId\"]');
    var urlInput = document.querySelector('#settings-view input[x-model=\"editUrl\"]');
    if (labelInput) labelInput.value = m.label || '';
    if (idInput) idInput.value = m.id || '';
    if (urlInput) urlInput.value = m.base_url || '';
    var modalOverlay = document.querySelector('#settings-view .modal-overlay');
    if (modalOverlay) modalOverlay.style.display = 'flex';
  }
}
function closeModelModal() {
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) { el.__x.$data.closeModelModal(); return; }
  var modals = document.querySelectorAll('#settings-view .modal-overlay');
  for (var i = 0; i < modals.length; i++) { modals[i].style.display = 'none'; }
}
function saveModelFromModal() {
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) { el.__x.$data.saveModel(); return; }
  // Fallback save
  var label = (document.querySelector('#settings-view input[x-model=\"editLabel\"]')||{}).value || '';
  var id = (document.querySelector('#settings-view input[x-model=\"editId\"]')||{}).value || '';
  var url = (document.querySelector('#settings-view input[x-model=\"editUrl\"]')||{}).value || '';
  if (!label || !id) return;
  var models = getModels();
  models.push({id:id, label:label, base_url:url, api_key:''});
  saveModels(models);
  refreshModelSelect();
  renderModelList(models, localStorage.getItem(StorageKeys.MODEL)||models[0].id);
  closeModelModal();
}

function _findModelIndex(btn) {
  var cards = document.querySelectorAll('#settings-view .model-card');
  var card = btn.closest('.model-card');
  if (!card) return -1;
  for (var i = 0; i < cards.length; i++) { if (cards[i] === card) return i; }
  return -1;
}
function editModelByBtn(btn) { var i = _findModelIndex(btn); if (i >= 0) openModelModal(i); }
function activateModelByBtn(btn) { var i = _findModelIndex(btn); if (i >= 0) activateModel(i); }
function deleteModelByBtn(btn) { var i = _findModelIndex(btn); if (i >= 0) deleteModel(i); }

function editModel(i) { if (typeof i === 'string') i = parseInt(i); if (isNaN(i)) return; openModelModal(i); }
function deleteModel(i) { if (typeof i === 'string') i = parseInt(i); if (isNaN(i)) return; var el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.openDeleteModal(i); }

function closeDeleteModal() {
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) { el.__x.$data.closeDeleteModal(); return; }
  var modals = document.querySelectorAll('#settings-view .modal-overlay');
  for (var i = 0; i < modals.length; i++) { modals[i].style.display = 'none'; }
}
function confirmDelete() {
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) { el.__x.$data.confirmDelete(); return; }
  closeDeleteModal();
}
function testConnection() {
  var el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x && el.__x.$data) { el.__x.$data.testConnection(); return; }
  if (typeof toast === 'function') toast('连接测试需要 Alpine 支持', 'warn');
}
function addModel() { openModelModal(-1); }

function toggleSkill(name) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.toggleSkill(name); }
function deleteSkill(name) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.deleteSkill(name); }

function saveByok(enabled) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.saveByok(enabled); }
function enableProPlan() { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.enableProPlan(); }

function saveVoiceSetting(key, value) { localStorage.setItem(voiceStorageKey(key), value); }
function onTTSBackendChange() {
  const el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x) el.__x.$data.onTTSBackendChange();
}
