/* SkillOS — Settings (Alpine.js)
 * Phase 6 migration. 4 subtabs (model/usage/skills/voice) + 2 modals.
 */

// ── Utilities (keep global for backward compat) ──────

function getModels() {
  try { return JSON.parse(localStorage.getItem('sd_models') || '[]'); } catch (e) { return []; }
}
function saveModels(models) { localStorage.setItem('sd_models', JSON.stringify(models)); }

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
      this.activeModelId = localStorage.getItem('sd_model') || 'deepseek-v4-flash';
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
      this.$nextTick(() => { const el = this.$refs.modalLabel; if (el) el.focus(); });
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
        if (localStorage.getItem('sd_model') === oldId) {
          localStorage.setItem('sd_model', id);
          this.activeModelId = id;
        }
      }
      saveModels(models);
      refreshModelSelect();
      this.loadModels();
      this.closeModelModal();
    },

    activateModel(i) {
      const m = this.models[i];
      if (!m) return;
      localStorage.setItem('sd_model', m.id);
      this.activeModelId = m.id;
      if (typeof _selectedModel !== 'undefined') _selectedModel = m.id;
      const sel = document.getElementById('model-select');
      if (sel) sel.value = m.id;
      refreshModelSelect();
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
      if (localStorage.getItem('sd_model') === m.id) {
        localStorage.setItem('sd_model', models[0].id);
        this.activeModelId = models[0].id;
        if (typeof _selectedModel !== 'undefined') _selectedModel = models[0].id;
      }
      refreshModelSelect();
      this.loadModels();
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
        this.disabledSkills = JSON.parse(localStorage.getItem('sd_disabled_skills') || '[]');
      } catch (e) {
        this.skills = [];
      }
    },

    isSkillEnabled(name) { return !this.disabledSkills.includes(name); },

    toggleSkill(name) {
      let disabled = JSON.parse(localStorage.getItem('sd_disabled_skills') || '[]');
      if (disabled.includes(name)) {
        disabled = disabled.filter(n => n !== name);
      } else {
        disabled.push(name);
      }
      localStorage.setItem('sd_disabled_skills', JSON.stringify(disabled));
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
      this.ttsBackend = localStorage.getItem('sd_tts_backend') || 'edge';
      this.ttsVoice = localStorage.getItem('sd_tts_voice') || 'Xiaoxiao (Natural)';
      this.ttsSpeed = localStorage.getItem('sd_tts_speed') || '1.1';
      this.ttsEmotion = localStorage.getItem('sd_tts_emotion') || 'neutral';
      this.asrEngine = localStorage.getItem('sd_asr_engine') || 'whisper';
    },

    get edgeVoices() { return ['Xiaoxiao (Natural)', 'Yunxi (Warm)', 'Yunyang (News)', 'Xiaoyi (Lively)']; },
    get omniVoices() { return ['Default (Neutral)', 'Female Warm', 'Male Deep', 'Energetic']; },
    get voiceList() { return this.ttsBackend === 'omnivoice' ? this.omniVoices : this.edgeVoices; },

    saveVoiceSetting(key, value) {
      localStorage.setItem('sd_' + key, value);
    },

    onTTSBackendChange() {
      localStorage.setItem('sd_tts_backend', this.ttsBackend);
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
  if (t === 'model') loadModelSettings(content);
  else if (t === 'usage') loadUsageSettings(content);
  else if (t === 'skills') loadSkillSettings(content);
  else if (t === 'voice') loadVoiceSettings(content);
}

function showSettings() {
  if (window.__alpineReady) {
    Alpine.store('nav').navigate('settings-view');
    Alpine.store('nav').barVisible = false;
    document.getElementById('bar').style.display = 'none';
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
  const current = localStorage.getItem('sd_model') || (typeof _selectedModel !== 'undefined' ? _selectedModel : '') || models[0].id;
  sel.innerHTML = models.map(function (m) {
    const label = (m.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return '<option value="' + m.id + '"' + (m.id === current ? ' selected' : '') + '>' + label + '</option>';
  }).join('');
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
  localStorage.setItem('sd_model', models[i].id);
  if (typeof _selectedModel !== 'undefined') _selectedModel = models[i].id;
  document.getElementById('model-select').value = models[i].id;
  refreshModelSelect();
}

function openModelModal(i) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.openModelModal(i); }
function closeModelModal() { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.closeModelModal(); }
function saveModelFromModal() { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.saveModel(); }

function editModel(i) { openModelModal(i); }
function deleteModel(i) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.openDeleteModal(i); }
function addModel() { openModelModal(-1); }

function toggleSkill(name) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.toggleSkill(name); }
function deleteSkill(name) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.deleteSkill(name); }

function saveByok(enabled) { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.saveByok(enabled); }
function enableProPlan() { const el = document.querySelector('[x-data="settingsView()"]'); if (el && el.__x) el.__x.$data.enableProPlan(); }

function saveVoiceSetting(key, value) { localStorage.setItem('sd_' + key, value); }
function onTTSBackendChange() {
  const el = document.querySelector('[x-data="settingsView()"]');
  if (el && el.__x) el.__x.$data.onTTSBackendChange();
}
