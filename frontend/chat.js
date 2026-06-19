/* chat.js — extracted from app.js */

function apiErrorMessage(r, body) {
  body = body || {};
  if (r.status === 402) return body.detail || '额度已用尽，请启用 BYOK 或升级 Pro';
  if (r.status === 403) return body.detail || '无权限执行此操作';
  if (r.status === 401) return '请先登录';
  if (typeof body.detail === 'string') return body.detail;
  return '请求失败 (' + r.status + ')';
}

function finalizeSkill() {
  var sid = localStorage.getItem('skillos_session_id') || '';
  if (!sid) { addMsg('sys', '请先开始对话再生成技能'); return; }
  setStatus('generating'); setDot('blue');
  fetch(API + '/api/skills/finalize?session_id=' + encodeURIComponent(sid), { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.reply) addMsg('ai', d.reply);
      if (d.skill_saved) { setStatus('saved: ' + d.skill_saved); setDot('on'); refreshSkillList(); }
      else { setStatus(d.error || 'done'); setDot(''); }
      document.getElementById('finalize-btn').style.display = d.skill_active ? '' : 'none';
    })
    .catch(function(e) { addMsg('sys', '生成失败: ' + e.message); setStatus('error'); setDot(''); });
}

var _useStreaming = true;  // Enable SSE streaming by default

function sendText() {
  if (_useStreaming) { sendTextStream(); return; }
  _sendTextLegacy();
}

function _sendTextLegacy() {

  if (welcome) welcome.style.display = 'none';

  addMsg('user', text);

  setStatus('thinking');

  setDot('blue');

  let msgEl = addMsg('ai', '<span class="typing-dots"><span></span><span></span><span></span></span>');

  msgEl.style.opacity = '1';



  // Build history from DOM (will be replaced by server-side session history)

  let history = [];

  document.querySelectorAll('#msgs .msg.user, #msgs .msg.ai').forEach(el => {

    let role = el.classList.contains('user') ? 'user' : 'assistant';

    let txt = el.textContent.trim();

    if (txt && txt !== '...') history.push({ role, content: txt });

  });



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

      tts_backend: localStorage.getItem('sd_tts_backend') || 'edge',

      tts_voice: localStorage.getItem('sd_tts_voice') || 'Xiaoxiao (Natural)',

      tts_speed: parseFloat(localStorage.getItem('sd_tts_speed') || '1.1'),

      tts_emotion: localStorage.getItem('sd_tts_emotion') || 'friendly'

    })

  }).then(async r => {

    if (!r.ok) {
      let body = await r.json().catch(function() { return {}; });
      throw new Error(apiErrorMessage(r, body));
    }

    return r.json();

  }).then(d => {

    msgEl.textContent = d.reply || '(no response)';

    msgEl.style.opacity = '1';

    scrollMsgs();

    // Persist session id

    _sessionId = d.session_id || _sessionId;

    if (_sessionId) localStorage.setItem('sd_session', _sessionId);

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
      if (typeof toast === 'function') {
        var toastMsg = '技能已保存';
        if (pb && pb.repair && pb.repair.dna_score) toastMsg += ' · DNA ' + pb.repair.dna_score;
        if (pb && pb.regression_scheduled) toastMsg += ' · 参考技能回归已排队';
        toast(toastMsg, 'success');
      }

      refreshSkillList();

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

    var banner = document.getElementById('extract-banner');
    if (banner) {
      if (d.skill_active || d.quick_mode) {
        banner.style.display = '';
        banner.textContent = d.quick_mode ? '● 快速萃取模式' : '● 技能萃取进行中';
      } else {
        banner.style.display = 'none';
      }
    }

    setDot(d.skill_active || d.draft_saved || d.metaskill_active ? 'on' : '');

    // Action buttons (clickable options)

    if (d.actions && d.actions.length > 0) {

      let ad = document.createElement('div');

      ad.className = 'msg ai';

      ad.style.cssText = 'display:flex;flex-direction:column;gap:8px;padding:10px 14px';



      if (d.actions_multi) {

        // Multi-select mode: checkboxes + confirm button

        let selected = new Set();

        d.actions.forEach((a, i) => {

          let row = document.createElement('label');

          row.style.cssText = 'display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:var(--text)';

          let cb = document.createElement('input');

          cb.type = 'checkbox';

          cb.style.cssText = 'accent-color:var(--accent);width:16px;height:16px';

          cb.onchange = () => cb.checked ? selected.add(i) : selected.delete(i);

          row.appendChild(cb);

          row.appendChild(document.createTextNode(a.label));

          ad.appendChild(row);

        });

        let confirmBtn = document.createElement('button');

        confirmBtn.className = 'opt-btn';

        confirmBtn.textContent = '确认选择 (' + d.actions.length + '项可选)';

        confirmBtn.style.cssText = 'font-size:12px;padding:8px 16px;margin-top:4px;align-self:flex-start';

        confirmBtn.onclick = () => {

          let picked = [...selected].map(i => d.actions[i]);

          if (picked.length === 0) { addMsg('sys', '请至少选择一项'); return; }

          doAction({action: d.action_key || 'multi_select', skills: picked.map(a => a.action).join(','), label: picked.map(a=>a.label).join(' + ')});

        };

        ad.appendChild(confirmBtn);

      } else {

        // Single-select mode: clickable buttons

        ad.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;padding:8px 14px';

        d.actions.forEach(a => {

          let btn = document.createElement('button');

          btn.className = 'opt-btn';

          btn.textContent = a.label;

          btn.style.cssText = 'font-size:12px;padding:6px 14px';

          btn.onclick = () => doAction(a);

          ad.appendChild(btn);

        });

      }

      document.getElementById('msgs').appendChild(ad);

      scrollMsgs();

    }

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
    msgEl.innerHTML = '<span>' + errMsg + '</span> ';
    var retryBtn = document.createElement('button');
    retryBtn.className = 'nav-sm';
    retryBtn.style.cssText = 'font-size:11px;margin-left:4px;border-color:var(--warn);color:var(--warn)';
    retryBtn.textContent = '重试';
    retryBtn.onclick = function(){ document.getElementById('input').value = ''; sendText(); };
    msgEl.appendChild(retryBtn);
    toast(errMsg, 'error');

    msgEl.style.opacity = '1';

    scrollMsgs();

    setStatus('error');

    setDot('');

  });

}

function setMode(m) {

  _mode = m;

  let labels = {create:'Create', agent:'Chat', meta:'Pipeline'};

  document.querySelectorAll('.nav-mode').forEach(b =>

    b.classList.toggle('active', b.textContent === labels[m])

  );

  showChat();

  if (m === 'meta') {

    // Meta mode: immediately start MetaSkill creation

    document.getElementById('msgs').innerHTML = '';

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

function addMsg(role, text) {
  var now = new Date();
  var time = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
  var dateStr = now.getFullYear() + '-' + (now.getMonth()+1).toString().padStart(2,'0') + '-' + now.getDate().toString().padStart(2,'0');
  if (role === 'sys') text += ' <span style="font-size:10px;opacity:.5">' + time + '</span>';

  // Push to Alpine store for reactive rendering
  var msg = {
    id: 'm_' + Date.now() + '_' + Math.random().toString(36).slice(2,6),
    role: role,
    text: text,
    time: time,
    date: dateStr,
    opacity: 1
  };

  // Inject date separator when day changes
  if (dateStr !== _lastMsgDate && _lastMsgDate !== '') {
    try {
      if (Alpine && Alpine.store('chat')) {
        Alpine.store('chat').messages.push({
          id: 'd_' + Date.now(),
          role: 'sys',
          text: '<div style="text-align:center;font-size:11px;color:var(--text3);padding:12px 0"><span style="background:var(--surface2);padding:2px 12px;border-radius:10px">' + dateStr + '</span></div>',
          time: '', date: dateStr, opacity: 1
        });
      }
    } catch(e) {}
  }
  _lastMsgDate = dateStr;

  try {
    if (Alpine && Alpine.store('chat')) {
      Alpine.store('chat').messages.push(msg);
      setTimeout(function(){ scrollMsgs(); }, 20);
      // Return proxy for backward compat (style.opacity manipulation)
      return {
        get style() { return { set opacity(v) {
          msg.opacity = v;
          try { Alpine.store('chat').messages = Alpine.store('chat').messages.map(function(m) { return m; }); } catch(e) {}
        }}; },
        set textContent(v) { msg.text = v; },
        set onclick(v) {}
      };
    }
  } catch(e) {}

  // Legacy fallback
  var el = document.createElement('div');
  el.className = 'msg ' + role;
  if (role === 'user' || role === 'ai') {
    var ts = document.createElement('span');
    ts.style.cssText = 'font-size:9px;color:var(--text3);display:block;margin-top:4px;text-align:' + (role==='user'?'right':'left');
    ts.textContent = time;
    el.appendChild(ts);
  }
  el.textContent = text;
  document.getElementById('msgs').appendChild(el);
  scrollMsgs();
  return el;
}

function scrollMsgs() {

  let m = document.getElementById('msgs');

  m.scrollTop = m.scrollHeight;

}

function setDot(c) { document.getElementById('conn-dot').className = 'dot ' + c; }

function setStatus(s) { document.getElementById('status').textContent = s; }

function escHtml(s) {

  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

}

async function uploadFile(file) {

  if (!file) return;

  addMsg('sys', '📎 上传中：' + file.name + ' (' + (file.size/1024).toFixed(0) + 'KB)…');

  setStatus('uploading');

  setDot('blue');

  let form = new FormData();

  form.append('file', file);

  // Include session_id so backend can inject into active extraction conversation
  let sid = localStorage.getItem('skillos_session_id') || '';
  if (sid) form.append('session_id', sid);

  try {

    let r = await fetch(API + '/api/skills/ingest', { method: 'POST', body: form, headers: authHeaders() });

    if (!r.ok) {
      let body = await r.json().catch(function() { return {}; });
      throw new Error(apiErrorMessage(r, body));
    }

    let d = await r.json();

    if (d.reply) addMsg('ai', d.reply);
    else if (d.title) {
      var digestMsg = '📦 知识包「' + d.title + '」(' + (d.glossary_terms || 0) + '术语, ' + (d.patterns || 0) + '模式)';
      if (d.lineage_notice) digestMsg += '\n\n🔗 ' + d.lineage_notice;
      addMsg('ai', digestMsg);
    }
    else if (d.note) addMsg('sys', d.note);

    if (d.lineage_notice && !d.title && !d.reply) addMsg('sys', '🔗 ' + d.lineage_notice);
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

    let label = d.skill_saved ? 'skill: ' + d.skill_saved : (d.title ? 'digest: ' + d.title : 'done');
    if (d.injected_into_extraction) label = 'injected into extraction';
    setStatus(label);

    setDot(d.skill_saved || d.title || d.injected_into_extraction ? 'on' : '');

    if (d.skill_saved || d.title) refreshSkillList();

  } catch(e) {

    addMsg('sys', '上传失败：' + e.message);

    setStatus('error');

    setDot('');

  }

  document.getElementById('file-input').value = '';

}

function switchMainView(id) {

  document.querySelectorAll('.main-view').forEach(v => v.classList.remove('active'));

  let el = document.getElementById(id);

  if (el) el.classList.add('active');

  // Sync with Alpine store for reactive views
  try { if (Alpine && Alpine.store('nav')) Alpine.store('nav').currentView = id; } catch(e) {}

}

function showChat() {

  switchMainView('chat-view');
  document.getElementById('bar').style.display = 'flex';
  _currentSkill = null;
  try { if (Alpine && Alpine.store('nav')) Alpine.store('nav').currentSkill = null; } catch(e) {}

}

function newSession() {

  _sessionId = '';

  localStorage.removeItem('sd_session');

  document.getElementById('msgs').innerHTML = '';

  addMsg('sys', '已开始新会话');

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

  localStorage.setItem('sd_auto', _autoMode);

  addMsg('sys', _autoMode ? '自动模式：AI 将自动选择工具' : '手动模式：逐步确认');

}

function onModelChange() {

  _selectedModel = document.getElementById('model-select').value;

  localStorage.setItem('sd_model', _selectedModel);

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

async function sendTextStream() {
  var ta = document.getElementById('input');
  ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  var inp = document.getElementById('input'), text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  document.getElementById('bar').style.display = 'flex';
  var welcome = document.querySelector('.welcome');
  if (welcome) welcome.style.display = 'none';

  addMsg('user', text);
  var msgEl = addMsg('ai', '<span class=\"typing-dots\"><span></span><span></span><span></span></span>');
  setStatus('streaming'); setDot('blue');

  // Build history from DOM
  var history = [];
  document.querySelectorAll('#msgs .msg.user, #msgs .msg.ai').forEach(function(el) {
    var role = el.classList.contains('user') ? 'user' : 'assistant';
    var txt = el.textContent.trim();
    if (txt && txt !== '...') history.push({ role: role, content: txt });
  });

  var body = JSON.stringify({
    message: text, history: history.slice(-12), mode: _mode,
    model: _selectedModel, auto: _autoMode, session_id: _sessionId,
    tts_backend: localStorage.getItem('sd_tts_backend') || 'edge',
    tts_voice: localStorage.getItem('sd_tts_voice') || 'Xiaoxiao (Natural)',
  });

  try {
    var resp = await fetch(API + '/api/skills/dispatch/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body,
    });
    if (!resp.ok) { msgEl.textContent = 'HTTP ' + resp.status; setStatus('error'); setDot(''); return; }

    var reader = resp.body.getReader(), decoder = new TextDecoder(), buffer = '';
    var fullReply = '';

    while (true) {
      var { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      var lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line.startsWith('data: ')) continue;
        var data = line.substring(6);
        // Find event type from previous line
        var eventType = 'token';
        if (i > 0 && lines[i-1].startsWith('event: ')) eventType = lines[i-1].substring(7).trim();

        if (eventType === 'token') {
          fullReply += data;
          msgEl.innerHTML = '<span>' + fullReply.replace(/\n/g, '<br>') + '</span>';
        } else if (eventType === 'done') {
          try { var meta = JSON.parse(data); _sessionId = meta.session_id || _sessionId;
            if (_sessionId) localStorage.setItem('sd_session', _sessionId);
            if (meta.skill_saved) refreshSkillList();
          } catch(e) {}
        } else if (eventType === 'error') {
          msgEl.innerHTML = '<span>' + data + '</span> <button class=\"nav-sm\" style=\"font-size:11px;border-color:var(--warn);color:var(--warn)\" onclick=\"sendText()\">重试</button>';
        }
      }
    }
    msgEl.style.opacity = '1';
    scrollMsgs();
    setStatus('idle'); setDot('on');
    try { if (Alpine && Alpine.store('chat')) Alpine.store('chat').addMessage('ai', fullReply); } catch(e) {}
  } catch(e) {
    msgEl.textContent = e.message || '流式请求失败';
    toast(e.message, 'error');
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
