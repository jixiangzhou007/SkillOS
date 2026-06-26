/* chat.js — extraction chat engine */

function renderSidebarWorkspace(skills) {
  if (!Array.isArray(skills)) return;
  var recent = skills.filter(function(s) {
    return typeof SYSTEM_SKILLS === 'undefined' || !SYSTEM_SKILLS.includes(s.name);
  }).slice(0, 5);

  var welcomeEl = document.getElementById('welcome-recent-skills');
  if (welcomeEl && recent.length) {
    welcomeEl.innerHTML = '<div style="font-size:var(--t-xs);color:var(--text3);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">最近技能</div>' +
      recent.map(function(s) {
        return '<span class="welcome-skill-chip" onclick="showDetail(' + JSON.stringify(s.name) + ')">' + escHtml(s.name) + '</span>';
      }).join('');
  }

  var sbWs = document.getElementById('sb-workspace-content');
  if (sbWs) {
    sbWs.innerHTML = recent.length ? ('<div style="font-size:var(--t-xs);color:var(--text3);margin-bottom:var(--s-2)">最近技能</div>' + recent.map(function(s) {
      var badge = s.avg_score >= 4 ? '<span style="color:var(--a3);font-size:9px">●</span>' :
                  s.avg_score >= 2 ? '<span style="color:var(--amber);font-size:9px">●</span>' :
                  '<span style="color:var(--text3);font-size:9px">●</span>';
      return '<div class="sb-ws-item" onclick="showDetail(' + JSON.stringify(s.name) + ')" style="cursor:pointer;display:flex;align-items:center;gap:6px">' +
        badge + '<span style="font-size:var(--t-sm);color:var(--text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + escHtml(s.name) + '</span>' +
        '<span style="font-size:var(--t-xs);color:var(--text3)">v' + s.version + '</span>' +
        '</div>';
    }).join('')) : '<div style="padding:var(--s-2) var(--s-3);font-size:var(--t-xs);color:var(--text3);text-align:center">开始对话萃取新技能</div>';
  }
}

function loadRecentSkills() {
  if (typeof api !== 'function') return;
  api('/api/skills/').then(function(r) { return r.json(); }).then(function(skills) {
    if (!Array.isArray(skills) || !skills.length) return;
    renderSidebarWorkspace(skills);
  }).catch(function(e) { console.warn('chat fetch failed:', e); });
}

function apiErrorMessage(r, body) {
  body = body || {};
  if (r.status === 402) return body.detail || '额度已用尽，请启用 BYOK 或升级 Pro';
  if (r.status === 403) return body.detail || '无权限执行此操作';
  if (r.status === 401) return '请先登录';
  if (typeof body.detail === 'string') return body.detail;
  return '请求失败 (' + r.status + ')';
}

function finalizeSkill() {
  var sid = localStorage.getItem(StorageKeys.SESSION) || '';
  if (!sid) { addMsg('sys', '请先开始对话再生成技能'); return; }
  setStatus('generating'); setDot('blue');
  fetch(API + '/api/skills/finalize?session_id=' + encodeURIComponent(sid), {
    method: 'POST',
    headers: typeof authHeaders === 'function' ? authHeaders() : {}
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.reply) addMsg('ai', d.reply);
      if (d.skill_saved) {
        setStatus('saved: ' + d.skill_saved);
        setDot('on');
        if (typeof precipitateFromResponse === 'function') precipitateFromResponse(d, 'conversation');
        else refreshSkillList();
      } else { setStatus(d.error || 'done'); setDot(''); }
      updateWorkspace(d || {});
      // finalize button now handled by workspace phase bar
    })
    .catch(function(e) { addMsg('sys', '生成失败: ' + e.message); setStatus('error'); setDot(''); });
}

var _useStreaming = false;  // 默认走 /dispatch 一次性返回，避免 SSE+Alpine 不刷新

function sendText() {
  var inp = document.getElementById('input');
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  var ta = document.getElementById('input');
  if (ta) { ta.style.height = 'auto'; }
  document.getElementById('bar').style.display = 'flex';
  if (typeof maybeBeginSourceProgress === 'function') maybeBeginSourceProgress(text, isLikelyUrl(text) ? 'url' : '');
  if (_useStreaming) { sendTextStream(text); return; }
  _sendTextLegacy(text);
}

function buildChatHistory() {
  var history = [];
  var list = document.getElementById('chat-msgs-list');
  if (list) {
    list.querySelectorAll('.msg-row-user, .msg-row-ai').forEach(function(el) {
      var role = el.classList.contains('msg-row-user') ? 'user' : 'assistant';
      var body = el.querySelector('.msg-body');
      var txt = body ? body.textContent.trim() : el.textContent.trim();
      if (!txt || txt === '...') return;
      history.push({ role: role, content: txt });
    });
    if (history.length) return history;
  }
  try {
    if (Alpine && Alpine.store('chat')) {
      Alpine.store('chat').messages.forEach(function(m) {
        if (m.role !== 'user' && m.role !== 'ai') return;
        var txt = (m.text || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        if (!txt || txt === '...') return;
        history.push({ role: m.role === 'user' ? 'user' : 'assistant', content: txt });
      });
    }
  } catch (e) {}
  return history;
}

function _sendTextLegacy(text) {
  if (!text) return;

  addMsg('user', text);

  setStatus('thinking');

  setDot('blue');

  let msgEl = addMsg('ai', '<span class="typing-dots"><span></span><span></span><span></span></span>');

  msgEl.style.opacity = '1';



  // Build history from DOM (will be replaced by server-side session history)

  let history = buildChatHistory();

  api('/api/skills/dispatch', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({

      message: text,

      history: history.slice(-12),

      mode: _mode,

      model: _selectedModel,

      auto: _autoMode,

      session_id: _sessionId,

      tts_backend: localStorage.getItem(StorageKeys.TTS_BACKEND) || 'edge',

      tts_voice: localStorage.getItem(StorageKeys.TTS_VOICE) || 'Xiaoxiao (Natural)',

      tts_speed: parseFloat(localStorage.getItem(StorageKeys.TTS_SPEED) || '1.1'),

      tts_emotion: localStorage.getItem(StorageKeys.TTS_EMOTION) || 'friendly'

    })

  }).then(async r => {

    if (!r.ok) {
      let body = await r.json().catch(function() { return {}; });
      throw new Error(apiErrorMessage(r, body));
    }

    return r.json();

  }).then(d => {

    var actions = typeof resolveExtractionActions === 'function'
      ? resolveExtractionActions(d, d.reply) : (d.actions || []);
    if (typeof applySocraticReply === 'function') {
      applySocraticReply(msgEl, d.reply || '(no response)', actions, {
        multi: d.actions_multi,
        actionKey: d.action_key,
      });
    } else if (msgEl._msg) {
      patchChatMsg(msgEl._msg, _renderStreamHtml(d.reply || '(no response)'));
    } else {
      msgEl.textContent = d.reply || '(no response)';
    }

    scrollMsgs();

    // Persist session id

    _sessionId = d.session_id || _sessionId;

    if (_sessionId) localStorage.setItem(StorageKeys.SESSION, _sessionId);

    // Status handling

    if (d.skill_saved) {

      var statusText = 'saved: ' + d.skill_saved;
      if (d.quality && d.quality.official_score != null) {
        statusText += ' · 质量 ' + d.quality.official_score + '/100';
        if (d.quality.official_grade) statusText += ' (' + d.quality.official_grade + ')';
        if (d.quality.official_passed === false) statusText += ' ⚠未通过';
      }
      var bq = d.bench_quality || (d.epistemic_summary && d.epistemic_summary.bench_quality);
      if (bq) {
        if (bq.dna_compliance && bq.dna_compliance.score) {
          statusText += ' · DNA ' + bq.dna_compliance.score;
        }
        if (bq.moe && bq.moe.overall_score != null) {
          statusText += ' · MoE ' + bq.moe.overall_score;
        }
        if (bq.save_gate && bq.save_gate.smoke_pass === false) {
          statusText += ' · 烟测未过';
        }
      }
      var pb = d.post_bench;
      if (pb && pb.regression_scheduled) {
        statusText += ' · 回归评测后台运行中';
      }
      setStatus(statusText);

      refreshSkillList();

      if (typeof precipitateFromResponse === 'function') {
        precipitateFromResponse(d, (d.epistemic_summary && d.epistemic_summary.source_type) || 'conversation');
      }

    } else if (d.metaskill_active) {

      setStatus('🔗 Meta: ' + (d.draft_saved || 'designing'));

      refreshSkillList();

    } else if (d.optimize_active) {

      setStatus('optimizing: ' + d.draft_saved);

      refreshSkillList();

    } else if (d.draft_saved) {

      setStatus('draft: ' + d.draft_saved);

      refreshSkillList();

    } else {

      setStatus(d.skill_active ? 'extracting' : 'idle');

    }

    // Extraction panel
    updateWorkspace(d || {});
    // finalize button now handled by workspace phase bar

    setDot(d.skill_active || d.draft_saved || d.metaskill_active ? 'on' : '');

    if (_ttsEnabled) {

      let chunks = d.audio_chunks || (d.audio ? [d.audio] : []);

      let hasAudio = chunks.length > 0 && chunks.some(c => c && c.length > 10);

      if (hasAudio) {

        enqueueAudio(chunks, false);

      } else if (d.reply && window.speechSynthesis) {

        let u = new SpeechSynthesisUtterance(d.reply);

        u.lang = 'zh-CN'; u.rate = 1.1;

        speechSynthesis.speak(u);

      }

    }

  }).catch(e => {

    var errMsg = e.message || '请求失败';
    var errHtml = '<span>' + escHtml(errMsg) + '</span> <button type="button" class="nav-sm" style="font-size:11px;margin-left:4px;border-color:var(--warn);color:var(--warn)" onclick="sendText()">重试</button>';
    if (msgEl._msg) patchChatMsg(msgEl._msg, errHtml);
    else if (msgEl.innerHTML !== undefined) msgEl.innerHTML = errHtml;
    toast(errMsg, 'error');
    scrollMsgs();
    setStatus('error');
    setDot('');

  });

}

function setMode(m) {

  _mode = m;
  localStorage.setItem(StorageKeys.MODE, m);

  showChat();

  if (m === 'meta') {

    // Meta mode: immediately start MetaSkill creation

    clearChatMessages();

    addMsg('sys', '🔗 Meta 模式 — 正在启动流水线设计…');

    setStatus('loading');

    api('/api/skills/dispatch', {

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify({ message: '__metaskill__', history: [], mode: 'meta', model: _selectedModel })

    }).then(r => r.json()).then(d => {

      addMsg('ai', d.reply);

      scrollMsgs();

      setStatus(d.metaskill_active ? '🔗 Meta: designing' : 'idle');

      setDot(d.metaskill_active ? 'on' : '');

    });

  } else {

    addMsg('sys', m === 'create'

      ? '创建模式 — 描述你要沉淀的技能（新会话）'

      : 'Agent 模式 — 头脑风暴已激活');

    newSession();

  }

}

var _lastMsgDate = '';

function _msgListEl() {
  return document.getElementById('chat-msgs-list');
}

function _syncWelcome() {
  var w = document.getElementById('chat-welcome');
  var list = _msgListEl();
  if (w) w.style.display = (list && list.childElementCount > 0) ? 'none' : 'block';
}

function _chatStorePush(msg) {
  try {
    if (Alpine && Alpine.store('chat')) {
      Alpine.store('chat').messages = Alpine.store('chat').messages.concat([msg]);
    }
  } catch (e) {}
}

function _appendMsgRow(msg) {
  var list = _msgListEl();
  if (!list) return null;
  var row = document.createElement('div');
  row.className = 'msg-row msg-row-' + msg.role;
  row.setAttribute('data-msg-id', msg.id);
  var bodyEl;
  if (msg.role === 'sys') {
    bodyEl = document.createElement('div');
    bodyEl.className = 'msg-sys';
    bodyEl.innerHTML = msg.text;
    row.appendChild(bodyEl);
  } else {
    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble bubble-' + msg.role;
    bodyEl = document.createElement('div');
    bodyEl.className = 'msg-body';
    bodyEl.innerHTML = msg.text;
    bubble.appendChild(bodyEl);
    row.appendChild(bubble);
    var ts = document.createElement('span');
    ts.className = 'msg-time';
    ts.textContent = msg.time || '';
    row.appendChild(ts);
  }
  list.appendChild(row);
  return bodyEl;
}

function _touchChatMessages() {
  try {
    if (Alpine && Alpine.store('chat')) {
      Alpine.store('chat').messages = Alpine.store('chat').messages.slice();
    }
  } catch (e) {}
}

function patchChatMsg(msg, html) {
  if (!msg) return;
  msg.text = html;
  var list = _msgListEl();
  if (list && msg.id) {
    var row = list.querySelector('[data-msg-id="' + msg.id.replace(/"/g, '\\"') + '"]');
    if (row) {
      var body = row.querySelector('.msg-body') || row.querySelector('.msg-sys');
      if (body) body.innerHTML = html;
    }
  }
  try {
    if (Alpine && Alpine.store('chat') && msg.id) {
      var store = Alpine.store('chat');
      store.messages = store.messages.map(function(m) {
        return m.id === msg.id ? Object.assign({}, m, { text: html }) : m;
      });
    }
  } catch (e) {}
  scrollMsgs();
}

function clearChatMessages() {
  var list = _msgListEl();
  if (list) list.innerHTML = '';
  try {
    if (Alpine && Alpine.store('chat')) Alpine.store('chat').messages = [];
  } catch (e) {}
  _lastMsgDate = '';
  _syncWelcome();
}

function addMsg(role, text) {
  var now = new Date();
  var time = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
  var dateStr = now.getFullYear() + '-' + (now.getMonth()+1).toString().padStart(2,'0') + '-' + now.getDate().toString().padStart(2,'0');
  if (role === 'sys') text += ' <span class="msg-sys-time">' + time + '</span>';

  var msg = {
    id: 'm_' + Date.now() + '_' + Math.random().toString(36).slice(2,6),
    role: role,
    text: text,
    time: time,
    date: dateStr,
    opacity: 1
  };

  if (dateStr !== _lastMsgDate && _lastMsgDate !== '') {
    var sep = {
      id: 'd_' + Date.now(),
      role: 'sys',
      text: '<div class="msg-date-sep">' + dateStr + '</div>',
      time: '', date: dateStr, opacity: 1
    };
    _appendMsgRow(sep);
    _chatStorePush(sep);
  }
  _lastMsgDate = dateStr;

  var bodyEl = _appendMsgRow(msg);
  _chatStorePush(msg);
  _syncWelcome();
  setTimeout(function() { scrollMsgs(); }, 10);

  return {
    _msg: msg,
    _bodyEl: bodyEl,
    get style() { return { set opacity(v) { msg.opacity = v; } }; },
    set textContent(v) { patchChatMsg(msg, escHtml(String(v))); },
    set innerHTML(v) { patchChatMsg(msg, v); },
    set onclick(v) {}
  };
}

function scrollMsgs() {

  let m = document.getElementById('msgs');

  m.scrollTop = m.scrollHeight;

}

function setDot(c) { var d = document.getElementById('conn-dot'); if (d) d.className = 'header-dot ' + c; }

function setStatus(s) {
  s = s || '';
  var statusEl = document.getElementById('status');
  if (statusEl) statusEl.textContent = s;
  var turnEl = document.getElementById('wp-turn');
  var bar = document.getElementById('workspace-phase');
  if (turnEl && bar && bar.style.display !== 'none') {
    turnEl.textContent = _formatStatusHint(s);
  }
  try { if (Alpine && Alpine.store('nav')) Alpine.store('nav').setStatus(s); } catch (e) {}
}

function _formatStatusHint(s) {
  if (!s || s === 'idle' || s === '就绪') return '';
  if (s.indexOf('extracting') >= 0) return '萃取进行中';
  if (s.indexOf('thinking') >= 0 || s.indexOf('streaming') >= 0) return '等待回复…';
  if (s.indexOf('generating') >= 0) return '生成技能中…';
  if (s.indexOf('uploading') >= 0) return '上传处理中…';
  if (s.indexOf('saved:') >= 0 || s.indexOf('skill:') >= 0) return '已沉淀';
  if (s === 'error') return '出错了';
  return s.length > 24 ? s.slice(0, 24) + '…' : s;
}

function escHtml(s) {

  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

}

async function uploadFile(file) {

  if (!file) return;

  showChat();
  document.getElementById('bar').style.display = 'flex';
  if (typeof maybeBeginSourceProgress === 'function') maybeBeginSourceProgress('', 'file');

  addMsg('sys', '📎 上传中：' + file.name + ' (' + (file.size/1024).toFixed(0) + 'KB)…');

  setStatus('uploading');

  setDot('blue');

  let form = new FormData();

  form.append('file', file);

  // Include session_id so backend can inject into active extraction conversation
  let sid = localStorage.getItem(StorageKeys.SESSION) || '';
  if (sid) form.append('session_id', sid);

  try {

    let r = await fetch(API + '/api/skills/ingest', { method: 'POST', body: form, headers: authHeaders() });

    if (!r.ok) {
      let body = await r.json().catch(function() { return {}; });
      throw new Error(apiErrorMessage(r, body));
    }

    let d = await r.json();

    if (typeof hideSourceProgress === 'function') hideSourceProgress();

    if (d.reply) addMsg('ai', d.reply);

    if (d.lineage_notice && !d.title && !d.reply && !d.skill_saved) addMsg('sys', '🔗 ' + d.lineage_notice);
    if (d.note && !d.skill_saved && !d.title) addMsg('sys', d.note);
    if (d.warnings && d.warnings.length) {
      d.warnings.forEach(function(w) {
        addMsg('sys', w);
        toast(w, 'warn');
      });
    }
    if (d.knowledge && d.knowledge.needs_review > 0) {
      toast(d.knowledge.needs_review + ' 条知识待复核', 'warn');
    }

    scrollMsgs();

    if (typeof precipitateFromResponse === 'function') {
      precipitateFromResponse(d, 'file');
    } else if (d.skill_saved || d.title) {
      refreshSkillList();
    }

    setDot(d.skill_saved || d.title || d.injected_into_extraction ? 'on' : '');
    setStatus(d.skill_saved ? 'saved: ' + d.skill_saved : (d.title ? 'digest: ' + d.title : 'done'));

  } catch(e) {

    if (typeof hideSourceProgress === 'function') hideSourceProgress();

    addMsg('sys', '上传失败：' + e.message);

    setStatus('error');

    setDot('');

  }

  document.getElementById('file-input').value = '';

}

function switchMainView(id) {

  try {
    if (window.__alpineReady && typeof Alpine !== 'undefined' && Alpine.store('nav') && Alpine.store('nav').goTo) {
      Alpine.store('nav').goTo(id);
      return;
    }
  } catch (e) {}

  document.querySelectorAll('.main-view').forEach(v => v.classList.remove('active'));

  let el = document.getElementById(id);

  if (el) el.classList.add('active');

  try {
    if (Alpine && Alpine.store('nav')) {
      var nav = Alpine.store('nav');
      nav.currentView = id;
      nav.barVisible = (id === 'chat-view');
      if (id === 'chat-view') nav.primaryNav = 'extract';
      else if (id === 'hub-view') nav.primaryNav = 'market';
      else if (id === 'knowledge-unified-view') nav.primaryNav = 'knowledge';
    }
  } catch(e) {}

  var bar = document.getElementById('bar');
  if (bar) bar.style.display = (id === 'chat-view') ? 'flex' : 'none';
}

function showChat() {

  if (window.__alpineReady && typeof Alpine !== 'undefined' && Alpine.store('nav')) {
    Alpine.store('nav').showChat();
  } else {
    switchMainView('chat-view');
    document.getElementById('bar').style.display = 'flex';
  }
  _currentSkill = null;
  if (_mode !== 'create') { _mode = 'create'; localStorage.setItem(StorageKeys.MODE, 'create'); }
  try { if (Alpine && Alpine.store('nav')) Alpine.store('nav').currentSkill = null; } catch(e) {}
  // If no active session, ensure clean state
  if (!_sessionId) resetWorkspace();
}

function resumeSession() {
  var sid = localStorage.getItem(StorageKeys.SESSION);
  if (!sid) return;
  _sessionId = sid;
  api('/api/skills/status?session_id=' + encodeURIComponent(sid))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d && d.active) {
        updateWorkspace({
          skill_active: true,
          extraction_phase: d.phase || 'EXPLORING',
          extraction_turn: d.turn || 0,
          draft_preview: d.skill_name || '',
          draft_content: '',
          draft_progress: { probes_done: 0, probes_total: 5, messages_collected: d.context_turns || 0 }
        });
        setStatus('extracting');
        setDot('on');
        addMsg('sys', '已恢复萃取「' + (d.skill_name || '技能') + '」，继续对话即可');
      }
    }).catch(function(e) { console.warn('chat fetch failed:', e); });
}

function newSession() {

  _sessionId = '';

  localStorage.removeItem(StorageKeys.SESSION);

  clearChatMessages();

  if (typeof setExtractionSource === 'function') setExtractionSource('conversation');
  resetWorkspace();
  addMsg('sys', '开始新的萃取——请描述你要沉淀的工作流程');

  api('/api/skills/dispatch', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({ message: '__reset__', history: [], mode: _mode, model: _selectedModel })

  }).catch(() => {});

}

function toggleAuto() {

  _autoMode = !_autoMode;

  let b = document.getElementById('auto-btn');

  if (_autoMode) {
    b.classList.add('active');
    b.textContent = '自动';
  } else {
    b.classList.remove('active');
    b.textContent = '手动';
  }

  localStorage.setItem(StorageKeys.AUTO, _autoMode);

  addMsg('sys', _autoMode ? '自动模式：AI 将自动选择工具' : '手动模式：逐步确认');

}

function onModelChange() {

  _selectedModel = document.getElementById('model-select').value;
  if (!_selectedModel) return;
  localStorage.setItem(StorageKeys.MODEL, _selectedModel);
  try { if (Alpine && Alpine.store('chat')) Alpine.store('chat').selectedModel = _selectedModel; } catch(e) {}
  setStatus('model: ' + _selectedModel.split('-').slice(0, 2).join(' '));

}

function doAction(a) {
  var label = a.label || a.action;
  addMsg('user', label);
  var inp = document.getElementById('input');
  inp.value = (a.action || '') + (a.skills ? ' ' + (Array.isArray(a.skills) ? a.skills.join(',') : a.skills) : '');
  sendText();
}


function toggleSidebar() {
  var sb = document.getElementById('sidebar');
  if (!sb) return;
  sb.classList.toggle('open');
}

// ── SSE Streaming ──────────────────────────────────────

function _consumeSSELines(buffer, state) {
  state.buf += buffer;
  var lines = state.buf.split('\n');
  state.buf = lines.pop() || '';
  var events = [];
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].replace(/\r$/, '');
    if (!line) continue;
    if (line.indexOf('event:') === 0) {
      state.event = line.slice(6).trim();
    } else if (line.indexOf('data:') === 0) {
      events.push({ event: state.event || 'token', data: line.slice(5).replace(/^\s/, '') });
    }
  }
  return events;
}

function _renderStreamHtml(text) {
  return '<span>' + String(text || '').replace(/\n/g, '<br>') + '</span>';
}

async function sendTextStream(text) {
  text = (text || '').trim();
  if (!text) {
    var inp = document.getElementById('input');
    text = inp && inp.value.trim();
    if (!text) return;
    inp.value = '';
  }
  document.getElementById('bar').style.display = 'flex';

  addMsg('user', text);
  if (typeof setExtractionSource === 'function') setExtractionSource('conversation');
  var msgEl = addMsg('ai', '<span class="typing-dots"><span></span><span></span><span></span></span>');
  var streamMsg = msgEl._msg || null;
  var streamBody = msgEl._bodyEl || null;
  setStatus('streaming'); setDot('blue');

  // Build history from DOM
  var history = buildChatHistory();

  var body = JSON.stringify({
    message: text, history: history.slice(-12), mode: _mode,
    model: _selectedModel, auto: _autoMode, session_id: _sessionId,
    tts_backend: localStorage.getItem(StorageKeys.TTS_BACKEND) || 'edge',
    tts_voice: localStorage.getItem(StorageKeys.TTS_VOICE) || 'Xiaoxiao (Natural)',
    tts_speed: parseFloat(localStorage.getItem(StorageKeys.TTS_SPEED) || '1.1'),
    tts_emotion: localStorage.getItem(StorageKeys.TTS_EMOTION) || 'friendly'
  });

  try {
    var resp = await fetch(API + '/api/skills/dispatch/stream', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, typeof authHeaders === 'function' ? authHeaders() : {}),
      body: body,
    });
    if (!resp.ok) { msgEl.textContent = 'HTTP ' + resp.status; setStatus('error'); setDot(''); return; }

    var reader = resp.body.getReader(), decoder = new TextDecoder();
    var fullReply = '';
    var sseState = { buf: '', event: 'token' };

    while (true) {
      var { done, value } = await reader.read();
      if (done) break;
      var events = _consumeSSELines(decoder.decode(value, { stream: true }), sseState);

      for (var j = 0; j < events.length; j++) {
        var ev = events[j];
        if (ev.event === 'token' || ev.event === 'reply') {
          fullReply += ev.data;
          var html = _renderStreamHtml(fullReply);
          if (streamBody) streamBody.innerHTML = html;
          else if (streamMsg) patchChatMsg(streamMsg, html);
          else msgEl.innerHTML = html;
        } else if (ev.event === 'done') {
          try {
            var meta = JSON.parse(ev.data || '{}');
            _sessionId = meta.session_id || _sessionId;
            if (_sessionId) { localStorage.setItem(StorageKeys.SESSION, _sessionId); }

            if (meta.skill_saved) {
              setStatus('saved: ' + meta.skill_saved);
              if (typeof hideSourceProgress === 'function') hideSourceProgress();
              if (typeof precipitateFromResponse === 'function') {
                precipitateFromResponse(meta, (meta.epistemic_summary && meta.epistemic_summary.source_type) || 'conversation');
              } else if (typeof refreshSkillList === 'function') refreshSkillList();
            } else if (meta.skill_active) {
              if (typeof hideSourceProgress === 'function') hideSourceProgress();
              setStatus('extracting');
            } else {
              if (typeof hideSourceProgress === 'function') hideSourceProgress();
              setStatus('idle');
            }

            updateWorkspace(meta);
            setDot(meta.skill_active || meta.skill_saved ? 'on' : '');
          } catch (e) {}
        } else if (ev.event === 'error') {
          var errHtml = _renderStreamHtml(ev.data) + ' <button class="nav-sm" style="font-size:11px;border-color:var(--warn);color:var(--warn)" onclick="sendText()">重试</button>';
          if (streamBody) streamBody.innerHTML = errHtml;
          else if (streamMsg) patchChatMsg(streamMsg, errHtml);
          else msgEl.innerHTML = errHtml;
        }
      }
    }
    // Flush any trailing SSE frame in buffer
    if (sseState.buf.trim()) {
      _consumeSSELines('\n', sseState).forEach(function(ev) {
        if (ev.event === 'token' || ev.event === 'reply') {
          fullReply += ev.data;
        }
      });
      if (fullReply) {
        var finalHtml = _renderStreamHtml(fullReply);
        if (streamBody) streamBody.innerHTML = finalHtml;
        else if (streamMsg) patchChatMsg(streamMsg, finalHtml);
        else msgEl.innerHTML = finalHtml;
      }
    }
    scrollMsgs();
    if (!fullReply) {
      var emptyHtml = '<span style="color:var(--text3)">未收到回复，请重试</span>';
      if (streamBody) streamBody.innerHTML = emptyHtml;
      else if (streamMsg) patchChatMsg(streamMsg, emptyHtml);
      else msgEl.innerHTML = emptyHtml;
    }
    // Status/dot are set by the 'done' SSE event; fallback for missing done event
    if (!_sessionId) { setStatus('idle'); setDot(''); }
    // TTS audio output
    if (_ttsEnabled && fullReply && window.speechSynthesis) {
      var u = new SpeechSynthesisUtterance(fullReply);
      u.lang = 'zh-CN'; u.rate = 1.1;
      speechSynthesis.speak(u);
    }
  } catch(e) {
    if (typeof hideSourceProgress === 'function') hideSourceProgress();
    resetSSERetry();
    var streamErr = escHtml(e.message || '流式请求失败');
    var streamErrHtml = '<span>' + streamErr + '</span> <button type="button" class="nav-sm" style="font-size:11px;border-color:var(--warn);color:var(--warn)" onclick="sendText()">重试</button>';
    if (streamBody) streamBody.innerHTML = streamErrHtml;
    else if (streamMsg) patchChatMsg(streamMsg, streamErrHtml);
    else msgEl.textContent = e.message || '流式请求失败';
    if (e.message === 'Failed to fetch' || e.name === 'TypeError') {
      showConnectionError();
    } else {
      toast(e.message, 'error');
    }
    setStatus('error'); setDot('');
  }
}

var _ttsEnabled = true;
function toggleTTS() {
  _ttsEnabled = !_ttsEnabled;
  var btn = document.getElementById('tts-btn');
  btn.textContent = _ttsEnabled ? '🔊' : '🔇';
  btn.title = _ttsEnabled ? '语音播报：开' : '语音播报：关';
}
