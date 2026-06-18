/* ── Settings ───────────────────────────────────────────────── */

function getModels() {
  try { return JSON.parse(localStorage.getItem('sd_models') || '[]'); }
  catch(e) { return []; }
}
function saveModels(models) { localStorage.setItem('sd_models', JSON.stringify(models)); }

function getDefaultModels() {
  return [
    { id: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash', api_key: '', base_url: 'https://api.deepseek.com' },
    { id: 'deepseek-v4-pro',   label: 'DeepSeek V4 Pro',   api_key: '', base_url: 'https://api.deepseek.com' },
  ];
}

function loadModelSettings(el) {
  let models = getModels();
  if (!models.length) { models = getDefaultModels(); saveModels(models); }

  el.innerHTML = '';
  let title = document.createElement('div');
  title.style.cssText = 'font-size:13px;font-weight:600;color:var(--accent);margin-bottom:12px';
  title.textContent = '已配置模型';
  el.appendChild(title);

  models.forEach(function(m, i) {
    let isActive = (localStorage.getItem('sd_model') || 'deepseek-v4-flash') === m.id;

    let card = document.createElement('div');
    card.style.cssText = 'background:var(--surface2);border:1px solid ' + (isActive ? 'var(--accent)' : 'var(--border)') + ';border-radius:8px;padding:12px;margin-bottom:8px';

    let row1 = document.createElement('div');
    row1.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:6px';

    let labelEl = document.createElement('span');
    labelEl.style.cssText = 'font-weight:600;color:var(--text);flex:1';
    labelEl.textContent = m.label;
    row1.appendChild(labelEl);

    let idEl = document.createElement('span');
    idEl.style.cssText = 'font-size:10px;color:var(--text3)';
    idEl.textContent = m.id;
    row1.appendChild(idEl);

    if (isActive) {
      let badge = document.createElement('span');
      badge.style.cssText = 'font-size:10px;background:var(--accent);color:#fff;padding:2px 7px;border-radius:8px';
      badge.textContent = '当前';
      row1.appendChild(badge);
    }
    card.appendChild(row1);

    let urlEl = document.createElement('div');
    urlEl.style.cssText = 'font-size:11px;color:var(--text3);margin-bottom:6px';
    urlEl.textContent = m.base_url;
    card.appendChild(urlEl);

    let btns = document.createElement('div');
    btns.style.cssText = 'display:flex;gap:6px';

    let editBtn = document.createElement('button');
    editBtn.className = 'nav-sm';
    editBtn.style.fontSize = '10px';
    editBtn.textContent = '编辑';
    (function(idx) { editBtn.onclick = function() { editModel(idx); }; })(i);
    btns.appendChild(editBtn);

    if (!isActive) {
      let actBtn = document.createElement('button');
      actBtn.className = 'nav-sm';
      actBtn.style.cssText = 'font-size:10px;border-color:var(--accent);color:var(--accent)';
      actBtn.textContent = '启用';
      (function(idx) { actBtn.onclick = function() { activateModel(idx); }; })(i);
      btns.appendChild(actBtn);
    }

    let delBtn = document.createElement('button');
    delBtn.className = 'nav-sm';
    delBtn.style.cssText = 'font-size:10px;color:var(--err)';
    delBtn.textContent = '删除';
    (function(idx) { delBtn.onclick = function() { deleteModel(idx); }; })(i);
    btns.appendChild(delBtn);

    card.appendChild(btns);
    el.appendChild(card);
  });

  let addBtn = document.createElement('button');
  addBtn.className = 'btn a';
  addBtn.style.cssText = 'font-size:12px;padding:6px 14px;margin-top:8px';
  addBtn.textContent = '+ 添加模型';
  addBtn.onclick = addModel;
  el.appendChild(addBtn);

  let note = document.createElement('div');
  note.style.cssText = 'margin-top:12px;color:var(--text3);font-size:11px';
  note.textContent = '当前模型用于对话与技能萃取。API Key 请在 .env 中配置（DEEPSEEK_API_KEY、HUOSHAN_API_KEY）。';
  el.appendChild(note);
}

function activateModel(i) {
  let models = getModels();
  if (i < 0 || i >= models.length) return;
  localStorage.setItem('sd_model', models[i].id);
  _selectedModel = models[i].id;
  document.getElementById('model-select').value = models[i].id;
  refreshModelSelect();
  loadModelSettings(document.getElementById('s-content'));
  setStatus('model: ' + models[i].label);
}

/* ── Model Modal (Add / Edit) ────────────────────────────── */

let _editingModelIndex = -1;  // -1 = add mode, >=0 = edit mode

function openModelModal(index) {
  _editingModelIndex = index;
  let overlay = document.getElementById('model-modal');
  let title = document.getElementById('modal-title');
  let saveBtn = document.getElementById('modal-save-btn');

  if (index < 0) {
    title.textContent = '添加模型';
    saveBtn.textContent = '添加';
    document.getElementById('modal-label').value = '';
    document.getElementById('modal-id').value = '';
    document.getElementById('modal-url').value = 'https://api.deepseek.com';
  } else {
    let models = getModels();
    if (index >= models.length) return;
    let m = models[index];
    title.textContent = '编辑模型';
    saveBtn.textContent = '保存';
    document.getElementById('modal-label').value = m.label || '';
    document.getElementById('modal-id').value = m.id || '';
    document.getElementById('modal-url').value = m.base_url || '';
  }
  overlay.classList.add('open');
  document.getElementById('modal-label').focus();
}

function closeModelModal() {
  document.getElementById('model-modal').classList.remove('open');
  _editingModelIndex = -1;
}

function saveModelFromModal() {
  let label = document.getElementById('modal-label').value.trim();
  let id = document.getElementById('modal-id').value.trim();
  let url = document.getElementById('modal-url').value.trim();
  if (!label || !id || !url) { toast('请填写所有字段', 'error'); return; }

  let models = getModels();
  if (_editingModelIndex < 0) {
    // Add
    models.push({ id: id, label: label, base_url: url, api_key: '' });
  } else {
    // Edit
    let idx = _editingModelIndex;
    let oldId = models[idx].id;
    models[idx].label = label;
    models[idx].id = id;
    models[idx].base_url = url;
    if (localStorage.getItem('sd_model') === oldId) {
      localStorage.setItem('sd_model', id);
      _selectedModel = id;
    }
  }
  saveModels(models);
  refreshModelSelect();
  loadModelSettings(document.getElementById('s-content'));
  closeModelModal();
  setStatus(_editingModelIndex < 0 ? 'model added' : 'model updated');
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
  if (e.target.id === 'model-modal') closeModelModal();
  if (e.target.id === 'delete-modal') closeDeleteModal();
});
// Close on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { closeModelModal(); closeDeleteModal(); }
});

/* ── Delete Modal ────────────────────────────────────────── */

let _deleteModelIndex = -1;

function openDeleteModal(index) {
  let models = getModels();
  if (index < 0 || index >= models.length) return;
  _deleteModelIndex = index;
  document.getElementById('delete-model-name').textContent = models[index].label + ' (' + models[index].id + ')';
  document.getElementById('delete-modal').classList.add('open');
  // Set up one-time delete handler
  let delBtn = document.getElementById('modal-delete-btn');
  delBtn.onclick = function() { confirmDeleteModel(); };
}

function closeDeleteModal() {
  document.getElementById('delete-modal').classList.remove('open');
  _deleteModelIndex = -1;
}

function confirmDeleteModel() {
  let i = _deleteModelIndex;
  closeDeleteModal();
  if (i < 0) return;
  let models = getModels();
  if (i >= models.length) return;
  let m = models[i];
  models.splice(i, 1);
  if (!models.length) models = getDefaultModels();
  saveModels(models);
  if (localStorage.getItem('sd_model') === m.id) {
    localStorage.setItem('sd_model', models[0].id);
    _selectedModel = models[0].id;
  }
  refreshModelSelect();
  loadModelSettings(document.getElementById('s-content'));
  setStatus('model deleted: ' + m.label);
}

// Override the old editModel/deleteModel/addModel to use modals
function editModel(i) { openModelModal(i); }
function deleteModel(i) { openDeleteModal(i); }
function addModel() { openModelModal(-1); }

function refreshModelSelect() {
  let sel = document.getElementById('model-select');
  if (!sel) return;
  let models = getModels();
  if (!models.length) models = getDefaultModels();
  let current = localStorage.getItem('sd_model') || (typeof _selectedModel !== 'undefined' ? _selectedModel : '') || models[0].id;
  sel.innerHTML = models.map(function(m) {
    let label = (m.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return '<option value="' + m.id + '"' + (m.id === current ? ' selected' : '') + '>' + label + '</option>';
  }).join('');
}

async function loadUsageSettings(el) {
  el.innerHTML = '<div style="color:var(--text3);font-size:13px">加载用量…</div>';
  try {
    let r = await api('/api/usage/me');
    if (!r.ok) {
      el.innerHTML = '<div style="color:var(--err)">无法加载用量（请先登录）</div>';
      return;
    }
    let d = await r.json();
    let skillPct = d.skills.limit ? Math.min(100, Math.round(d.skills.used / d.skills.limit * 100)) : 0;
    let llmPct = d.llm_calls.limit ? Math.min(100, Math.round(d.llm_calls.used / d.llm_calls.limit * 100)) : 0;
    el.innerHTML =
      '<div style="font-size:13px;font-weight:600;color:var(--accent);margin-bottom:12px">Personal Free 用量</div>' +
      '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px">' +
      '<div style="font-size:12px;color:var(--text3);margin-bottom:4px">技能</div>' +
      '<div style="font-size:18px;font-weight:600">' + d.skills.used + ' / ' + d.skills.limit + '</div>' +
      '<div style="height:6px;background:#222;border-radius:3px;margin-top:8px"><div style="height:100%;width:' + skillPct + '%;background:var(--accent);border-radius:3px"></div></div>' +
      '</div>' +
      '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px">' +
      '<div style="font-size:12px;color:var(--text3);margin-bottom:4px">本月 AI 萃取（' + (d.llm_calls.period || '') + '）</div>' +
      '<div style="font-size:18px;font-weight:600">' + d.llm_calls.used + ' / ' + d.llm_calls.limit + '</div>' +
      '<div style="height:6px;background:#222;border-radius:3px;margin-top:8px"><div style="height:100%;width:' + llmPct + '%;background:var(--accent);border-radius:3px"></div></div>' +
      '</div>' +
      '<div style="font-size:12px;color:var(--text3);margin-bottom:10px">BYOK：' + (d.byok ? '已启用（自带 Key 不计入额度）' : '未启用') + '</div>' +
      '<div style="font-size:13px;font-weight:600;color:var(--accent);margin:16px 0 8px">自带 API Key（BYOK）</div>' +
      '<input id="byok-key" type="password" placeholder="sk-..." style="width:100%;background:var(--srf);border:1px solid #333;border-radius:6px;padding:10px;color:var(--text);font-size:13px;margin-bottom:8px">' +
      '<div style="display:flex;gap:8px">' +
      '<button class="btn a" style="font-size:12px;padding:6px 14px" onclick="saveByok(true)">启用 BYOK</button>' +
      '<button class="btn" style="font-size:12px;padding:6px 14px" onclick="saveByok(false)">关闭 BYOK</button>' +
      '</div>' +
      '<div style="margin-top:12px;color:var(--text3);font-size:11px">配置后平台 LLM 额度不再扣减；Key 仅存于本地数据库。</div>';
    if (d.plan === 'personal_free') {
      el.innerHTML +=
        '<div style="margin-top:16px;padding:12px;background:#1a1a2a;border:1px solid var(--border);border-radius:8px">' +
        '<div style="font-size:13px;font-weight:600;margin-bottom:8px">Personal Pro 内测</div>' +
        '<div style="font-size:12px;color:var(--text3);margin-bottom:8px">无限技能 · 500 次/月 LLM</div>' +
        '<input id="pro-beta-code" placeholder="内测邀请码" style="width:100%;padding:8px;margin-bottom:8px;background:var(--srf);border:1px solid #333;border-radius:6px;color:var(--text)">' +
        '<button class="btn a" style="font-size:12px" onclick="enableProPlan()">启用 Pro</button></div>';
    }
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err)">加载失败: ' + e.message + '</div>';
  }
}

async function saveByok(enabled) {
  let keyEl = document.getElementById('byok-key');
  let key = keyEl ? keyEl.value.trim() : '';
  if (enabled && key.length < 8) {
    toast('API Key 至少 8 个字符', 'error');
    return;
  }
  let r = await api('/api/usage/byok', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: enabled, api_key: key }),
  });
  if (!r.ok) {
    let err = await r.json().catch(function() { return {}; });
    toast(err.detail || '保存失败', 'error');
    return;
  }
  toast(enabled ? 'BYOK 已启用' : 'BYOK 已关闭');
  loadUsageSettings(document.getElementById('s-content'));
}

async function enableProPlan() {
  var code = (document.getElementById('pro-beta-code') || {}).value || '';
  var r = await api('/api/billing/enable-pro', {
    method: 'POST',
    body: JSON.stringify({ beta_code: code }),
  });
  if (!r.ok) {
    var err = await r.json().catch(function () { return {}; });
    toast(err.detail || '启用失败', 'error');
    return;
  }
  toast('Personal Pro 已启用');
  loadUsageSettings(document.getElementById('s-content'));
}

async function loadSkillSettings(el) {
  let r = await api('/api/skills/');
  let skills = await r.json();
  let disabled = JSON.parse(localStorage.getItem('sd_disabled_skills') || '[]');
  el.innerHTML = '<div style="margin:10px 0;color:var(--dim);font-size:14px">技能列表</div>';
  skills.forEach(s => {
    let on = !disabled.includes(s.name);
    el.innerHTML +=
      '<div style="padding:12px;margin:6px 0;background:var(--srf);border-radius:6px;display:flex;align-items:center">' +
      '<span style="flex:1;font-size:14px">' + s.name +
      ' <span style="color:var(--dim);font-size:12px">v' + s.version + ' · ' + s.runs + ' 次运行</span></span>' +
      '<button class="tgl on" id="tgl-' + s.name + '" style="font-size:11px;padding:4px 14px;margin-left:6px;border-radius:12px;border:1px solid ' + (on ? 'var(--accent)' : '#444') + ';cursor:pointer;background:' + (on ? 'var(--accent)' : 'transparent') + ';color:' + (on ? '#fff' : 'var(--dim)') + '" onclick="toggleSkill(\'' + s.name + '\')">' + (on ? '开' : '关') + '</button>' +
      '<button class="btn r" style="font-size:10px;padding:3px 8px;margin-left:4px" onclick="deleteSkill(\'' + s.name + '\')">✕</button></div>';
  });
  if (!skills.length)
    el.innerHTML += '<div style="color:var(--dim);font-size:14px">暂无技能</div>';
  el.innerHTML +=
    '<div style="margin-top:16px;color:var(--dim);font-size:13px">Create 模式：全部启用技能；Agent 模式：仅 brainstorming。</div>';
}

async function loadVoiceSettings(el) {
  let ttsBackend = localStorage.getItem('sd_tts_backend') || 'edge';
  let ttsVoice = localStorage.getItem('sd_tts_voice') || 'Xiaoxiao (Natural)';
  let ttsSpeed = localStorage.getItem('sd_tts_speed') || '1.1';
  let ttsEmotion = localStorage.getItem('sd_tts_emotion') || 'neutral';
  let asrEngine = localStorage.getItem('sd_asr_engine') || 'whisper';

  let edgeVoices = ['Xiaoxiao (Natural)', 'Yunxi (Warm)', 'Yunyang (News)', 'Xiaoyi (Lively)'];
  let omniVoices = ['Default (Neutral)', 'Female Warm', 'Male Deep', 'Energetic'];

  el.innerHTML =
    '<h3 style="color:var(--accent);font-size:14px;margin-bottom:12px">🎙️ 语音识别 (ASR)</h3>' +
    '<div style="margin:8px 0"><label style="color:var(--dim);font-size:12px">识别引擎</label>' +
    '<select id="cfg-asr" onchange="saveVoiceSetting(\'asr_engine\',this.value)" style="width:100%;background:var(--srf);border:1px solid #222;border-radius:6px;padding:10px;color:var(--text);font-size:14px;margin-top:4px">' +
    '<option value="whisper"' + (asrEngine === 'whisper' ? ' selected' : '') + '>Whisper（本地，CPU/GPU）</option>' +
    '<option value="funasr"' + (asrEngine === 'funasr' ? ' selected' : '') + '>FunASR SenseVoice（GPU，含情感/说话人）</option>' +
    '<option value="hybrid"' + (asrEngine === 'hybrid' ? ' selected' : '') + '>混合（本地 + 云端回退）</option>' +
    '</select></div>' +

    '<h3 style="color:var(--accent);font-size:14px;margin:20px 0 12px">🔊 语音合成 (TTS)</h3>' +
    '<div style="margin:8px 0"><label style="color:var(--dim);font-size:12px">合成后端</label>' +
    '<select id="cfg-tts-backend" onchange="onTTSBackendChange()" style="width:100%;background:var(--srf);border:1px solid #222;border-radius:6px;padding:10px;color:var(--text);font-size:14px;margin-top:4px">' +
    '<option value="edge"' + (ttsBackend === 'edge' ? ' selected' : '') + '>Edge TTS（云端免费，无需 GPU）</option>' +
    '<option value="omnivoice"' + (ttsBackend === 'omnivoice' ? ' selected' : '') + '>OmniVoice（本地，646 语言，建议 GPU）</option>' +
    '</select></div>' +

    '<div style="margin:8px 0"><label style="color:var(--dim);font-size:12px">音色</label>' +
    '<select id="cfg-tts-voice" onchange="saveVoiceSetting(\'tts_voice\',this.value)" style="width:100%;background:var(--srf);border:1px solid #222;border-radius:6px;padding:10px;color:var(--text);font-size:14px;margin-top:4px">' +
    (ttsBackend === 'omnivoice' ? omniVoices : edgeVoices).map(v =>
      '<option value="' + v + '"' + (ttsVoice === v ? ' selected' : '') + '>' + v + '</option>'
    ).join('') +
    '</select></div>' +

    '<div style="margin:8px 0"><label style="color:var(--dim);font-size:12px">语速: <span id="speed-val">' + ttsSpeed + 'x</span></label>' +
    '<input type="range" id="cfg-tts-speed" min="0.7" max="1.5" step="0.05" value="' + ttsSpeed + '" oninput="document.getElementById(\'speed-val\').textContent=this.value+\'x\';saveVoiceSetting(\'tts_speed\',this.value)" style="width:100%;margin-top:4px;accent-color:var(--accent)"></div>' +

    '<div style="margin:8px 0"><label style="color:var(--dim);font-size:12px">情感预设</label>' +
    '<select id="cfg-tts-emotion" onchange="saveVoiceSetting(\'tts_emotion\',this.value)" style="width:100%;background:var(--srf);border:1px solid #222;border-radius:6px;padding:10px;color:var(--text);font-size:14px;margin-top:4px">' +
    '<option value="neutral"' + (ttsEmotion === 'neutral' ? ' selected' : '') + '>😐 中性</option>' +
    '<option value="happy"' + (ttsEmotion === 'happy' ? ' selected' : '') + '>😊 愉快</option>' +
    '<option value="gentle"' + (ttsEmotion === 'gentle' ? ' selected' : '') + '>🌸 温柔</option>' +
    '<option value="excited"' + (ttsEmotion === 'excited' ? ' selected' : '') + '>🎉 兴奋</option>' +
    '<option value="sad"' + (ttsEmotion === 'sad' ? ' selected' : '') + '>😢 柔和</option>' +
    '</select></div>' +

    '<div style="margin:16px 0;padding:10px;background:#0a1a10;border-radius:6px;font-size:12px;color:var(--accent)">' +
    '💡 TTS 后端、语速与情感立即生效；ASR 引擎变更需重启服务。' +
    '</div>';
}

function onTTSBackendChange() {
  let v = document.getElementById('cfg-tts-backend').value;
  localStorage.setItem('sd_tts_backend', v);
  loadVoiceSettings(document.getElementById('s-content'));
}

function saveVoiceSetting(key, value) {
  localStorage.setItem('sd_' + key, value);
}

async function toggleSkill(name) {
  let disabled = JSON.parse(localStorage.getItem('sd_disabled_skills') || '[]');
  let btn = document.getElementById('tgl-' + name);
  if (!btn) return;
  let isOn = btn.textContent.trim() === '开';
  if (isOn) {
    if (!disabled.includes(name)) disabled.push(name);
    btn.textContent = '关';
    btn.style.background = 'transparent';
    btn.style.color = 'var(--dim)';
    btn.style.borderColor = '#444';
  } else {
    disabled = disabled.filter(function(n) { return n !== name; });
    btn.textContent = '开';
    btn.style.background = 'var(--accent)';
    btn.style.color = '#fff';
    btn.style.borderColor = 'var(--accent)';
  }
  localStorage.setItem('sd_disabled_skills', JSON.stringify(disabled));
  toast(isOn ? '已禁用: ' + name : '已启用: ' + name);
}

async function deleteSkill(name) {
  if (!confirm('确定删除「' + name + '」及全部数据？')) return;
  let r = await api('/api/skills/' + encodeURIComponent(name), { method: 'DELETE' });
  let d = await r.json();
  if (d.deleted) {
    addMsg('sys', '已删除: ' + name);
    refreshSkillList();
    switchSettings('skills');
  } else {
    addMsg('sys', '删除失败: ' + (d.error || '未知错误'));
  }
}

