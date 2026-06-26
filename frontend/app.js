/* SkillOS Frontend — core state and init */

const API = '';

function api(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({}, typeof authHeaders === 'function' ? authHeaders() : {}, opts.headers || {});
  if (opts.method && opts.method !== 'GET' && !opts.headers['Content-Type'])
    opts.headers['Content-Type'] = 'application/json';
  return fetch(API + path, opts);
}

var _mode = 'create', _currentSkill = null, _currentTab = 'overview';
var _settingsTab = 'model', _skillListTab = 'mine';
var _selectedModel = lsGet(StorageKeys.MODEL, 'deepseek-v4-flash');
var _autoMode = localStorage.getItem(StorageKeys.AUTO) === 'true';
var _sessionId = '';  // Start fresh each page load; resume only via explicit user action
var _allSkillsCache = [];

const SYSTEM_SKILLS = ['brainstorming', 'skill-creator', 'deep-digest', 'cold-start-interview'];

refreshModelSelect();
var ms = document.getElementById('model-select');
if (ms && !ms.value) ms.value = _selectedModel || 'deepseek-v4-flash';
if (_autoMode) {
  document.getElementById('auto-btn').classList.add('active');
  document.getElementById('auto-btn').textContent = '自动';
} else {
  document.getElementById('auto-btn').textContent = '手动';
}

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(evt) {
  document.addEventListener(evt, function(e) { e.preventDefault(); e.stopPropagation(); }, false);
});
var _dragCounter = 0;
document.addEventListener('dragenter', function(e) {
  _dragCounter++; document.getElementById('body-wrap').classList.add('drag-over');
});
document.addEventListener('dragleave', function(e) {
  _dragCounter--; if (_dragCounter <= 0) { _dragCounter = 0; document.getElementById('body-wrap').classList.remove('drag-over'); }
});
document.addEventListener('drop', function(e) {
  _dragCounter = 0; document.getElementById('body-wrap').classList.remove('drag-over');
  var files = e.dataTransfer && e.dataTransfer.files;
  if (files && files.length) { for (var i = 0; i < files.length; i++) uploadFile(files[i]); }
});

// ── Global Search ──
var _searchTimer = null, _searchSeq = 0;

function onGlobalSearchFocus() {
  var q = document.getElementById('global-search').value.trim();
  if (q) doGlobalSearch();
}

function hideGlobalSearchPanel() {
  var panel = document.getElementById('global-search-panel');
  if (panel) { panel.style.display = 'none'; panel.innerHTML = ''; }
  var inp = document.getElementById('global-search');
  if (inp) inp.style.borderColor = '';
}

function clearGlobalSearch() {
  var inp = document.getElementById('global-search');
  if (inp) { inp.value = ''; inp.blur(); }
  hideGlobalSearchPanel();
}

function showGlobalSearchPanel(html) {
  var panel = document.getElementById('global-search-panel');
  if (!panel) return;
  panel.innerHTML = html;
  panel.style.display = html ? 'block' : 'none';
}

function pickGlobalSearchSkill(name) {
  clearGlobalSearch();
  if (typeof showDetail === 'function') showDetail(name);
}

function pickGlobalSearchMarket(skillId) {
  clearGlobalSearch();
  if (typeof showHub === 'function') showHub();
  if (typeof showHubSkill === 'function') showHubSkill(skillId);
}

function pickGlobalSearchKnowledge(content) {
  clearGlobalSearch();
  if (typeof showUnifiedKnowledge === 'function') showUnifiedKnowledge('knowledge');
  toast((content || '').slice(0, 100) + (content && content.length > 100 ? '…' : ''), 'info');
}

function renderGlobalSearchResults(q, skills, kItems, mSkills) {
  var inp = document.getElementById('global-search');
  var count = skills.length + kItems.length + mSkills.length;
  if (inp) inp.style.borderColor = count > 0 ? 'var(--accent)' : 'var(--err)';

  if (count === 0) {
    showGlobalSearchPanel('<div class="gs-empty">未找到「' + escHtml(q) + '」相关结果</div>');
    return;
  }

  var h = '';
  if (skills.length) {
    h += '<div class="gs-section"><div class="gs-label">我的技能 (' + skills.length + ')</div>';
    skills.slice(0, 8).forEach(function(s) {
      h += '<button type="button" class="gs-item" onclick="pickGlobalSearchSkill(' + JSON.stringify(s.name) + ')">';
      h += '<span class="gs-icon">📁</span><span class="gs-title">' + escHtml(s.name) + '</span>';
      h += '<span class="gs-meta">v' + (s.version || 1) + '</span></button>';
    });
    if (skills.length > 8) h += '<div class="gs-empty">还有 ' + (skills.length - 8) + ' 个技能…</div>';
    h += '</div>';
  }
  if (kItems.length) {
    h += '<div class="gs-section"><div class="gs-label">知识条目 (' + kItems.length + ')</div>';
    kItems.slice(0, 6).forEach(function(i) {
      var preview = (i.content || '').slice(0, 60);
      h += '<button type="button" class="gs-item" onclick="pickGlobalSearchKnowledge(' + JSON.stringify(i.content || '') + ')">';
      h += '<span class="gs-icon">📚</span><span class="gs-title">' + escHtml(preview || i.id || '知识条目') + '</span>';
      h += '<span class="gs-meta">' + escHtml(i.category || '') + '</span></button>';
    });
    h += '</div>';
  }
  if (mSkills.length) {
    h += '<div class="gs-section"><div class="gs-label">技能市场 (' + mSkills.length + ')</div>';
    mSkills.slice(0, 6).forEach(function(s) {
      var sid = s.id || s.skill_id || s.name;
      h += '<button type="button" class="gs-item" onclick="pickGlobalSearchMarket(' + JSON.stringify(String(sid)) + ')">';
      h += '<span class="gs-icon">🏪</span><span class="gs-title">' + escHtml(s.name || sid) + '</span>';
      h += '<span class="gs-meta">' + (s.score != null ? s.score + ' 分' : '') + '</span></button>';
    });
    h += '</div>';
  }
  showGlobalSearchPanel(h);
}

function doGlobalSearch() {
  var inp = document.getElementById('global-search');
  if (!inp) return;
  var q = inp.value.trim();
  clearTimeout(_searchTimer);
  if (!q) { hideGlobalSearchPanel(); return; }

  showGlobalSearchPanel('<div class="gs-loading">搜索中…</div>');
  _searchTimer = setTimeout(function() {
    var seq = ++_searchSeq;
    Promise.all([
      fetch(API + '/api/skills/?q=' + encodeURIComponent(q), { headers: authHeaders() }).then(function(r) { return r.json(); }).catch(function() { return []; }),
      fetch(API + '/api/knowledge/?q=' + encodeURIComponent(q), { headers: authHeaders() }).then(function(r) { return r.json(); }).catch(function() { return { items: [] }; }),
      fetch(API + '/api/marketplace/search?q=' + encodeURIComponent(q)).then(function(r) { return r.json(); }).catch(function() { return { skills: [] }; })
    ]).then(function(results) {
      if (seq !== _searchSeq) return;
      var skills = Array.isArray(results[0]) ? results[0] : [];
      var kItems = (results[1] && results[1].items) ? results[1].items : [];
      var mSkills = (results[2] && results[2].skills) ? results[2].skills : [];
      renderGlobalSearchResults(q, skills, kItems, mSkills);
    });
  }, 280);
}

document.addEventListener('click', function(e) {
  var wrap = document.getElementById('global-search-wrap');
  if (wrap && !wrap.contains(e.target)) hideGlobalSearchPanel();
});

// ── Keyboard Shortcuts ──
document.addEventListener('keydown', function(e) {
  // Ctrl+K: focus global search
  if (e.ctrlKey && e.key === 'k') { e.preventDefault(); document.getElementById('global-search').focus(); return; }
  // Ctrl+N: new chat
  if (e.ctrlKey && e.key === 'n') { e.preventDefault(); showChat(); document.getElementById('input').focus(); return; }
  // Ctrl+Enter: send message
  if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); if (typeof sendText === 'function') sendText(); return; }
  // / or \: focus chat input (skip if already in an input/textarea)
  if ((e.key === '/' || e.key === '\\') && document.activeElement && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault(); showChat(); document.getElementById('input').focus(); return;
  }
  // Escape: close dropdowns, modals, search
  if (e.key === 'Escape') {
    var drop = document.getElementById('user-drop');
    if (drop && drop.classList.contains('open')) { drop.classList.remove('open'); return; }
    if (typeof closeSourceMaterialModal === 'function') {
      var sm = document.getElementById('source-material-modal');
      if (sm && sm.classList.contains('open')) { closeSourceMaterialModal(); return; }
    }
    if (typeof hideGlobalSearchPanel === 'function') hideGlobalSearchPanel();
    var inp = document.getElementById('global-search'); if (inp) inp.value = '';
    return;
  }
  // 1-9: switch detail tabs when in detail view
  if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.metaKey && document.activeElement && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    var detailView = document.getElementById('detail-view');
    if (!detailView || !detailView.classList.contains('active')) return;
    var tabs = ['overview', 'doc', 'quality', 'evolution'];
    var idx = parseInt(e.key) - 1;
    if (idx < tabs.length && typeof switchTab === 'function') switchTab(tabs[idx]);
  }
});

// ── Toast ──
function toast(msg, type) {
  type = type || 'info';
  var container = document.getElementById('toast-container');
  if (!container) return;
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  el.title = '点击关闭';
  el.onclick = function(){ el.classList.add('out'); setTimeout(function(){ el.remove(); }, 300); };
  var duration = Math.max(2000, Math.min(8000, msg.length * 60));
  container.appendChild(el);
  setTimeout(function(){ if (el.parentNode) { el.classList.add('out'); setTimeout(function(){ el.remove(); }, 300); } }, duration);
}

initAuth();

// Show chat input bar on initial load
if (typeof showChat === 'function') showChat();

// Check for active extraction session to resume
(function checkResumeSession() {
  var sid = localStorage.getItem(StorageKeys.SESSION);
  if (!sid || typeof api !== 'function') return;
  api('/api/skills/status?session_id=' + encodeURIComponent(sid))
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) {
      if (d && d.active && d.can_resume) {
        var name = d.skill_name || '技能';
        var phaseLabel = d.phase || '';
        setTimeout(function() {
          if (typeof addMsg === 'function') {
            addMsg('sys', '检测到进行中的萃取「<b>' + name + '</b>」(第 ' + (d.turn||0) + ' 轮' + (phaseLabel ? ', ' + phaseLabel : '') + ') <button class="nav-sm" style="font-size:11px;margin-left:6px;border-color:var(--accent);color:var(--accent)" onclick="resumeSession()">继续</button>');
          }
        }, 1000);
      }
    }).catch(function(e) { console.warn('resume check failed:', e); });
})();

// Load recent skills for welcome screen and sidebar
if (typeof loadRecentSkills === 'function') { setTimeout(loadRecentSkills, 500); }

// 预加载市场只读模式，隐藏发布按钮
api('/api/marketplace/catalog?limit=1').then(function(r) {
  return r.ok ? r.json() : null;
}).then(function(d) {
  if (d && typeof applyMarketplaceMode === 'function') applyMarketplaceMode(d);
}).catch(function(e) { console.warn('marketplace catalog check failed:', e); });
