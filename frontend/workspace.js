/* workspace.js — Extraction workspace: unified strip + draft preview */

var _PHASE_LABELS = {
  EXPLORING: '探索中', REFINING: '细化中', CONFIRMING: '确认中',
  OPTIMIZING: '优化中', METASKILL: '流水线', GENERATING: '生成中', DONE: '已完成'
};
var _PHASE_CSS = {
  EXPLORING: 'exploring', REFINING: 'refining', CONFIRMING: 'confirming',
  OPTIMIZING: 'refining', METASKILL: 'generating', GENERATING: 'generating', DONE: 'done'
};
var _SOURCE_LABELS = { conversation: '对话萃取', url: '链接沉淀', file: '文件上传' };
var _extractionSource = 'conversation';
var _ingestActive = false;

function setExtractionSource(kind) {
  _extractionSource = kind || 'conversation';
}

function _syncChatStripChrome() {
  var cv = document.getElementById('chat-view');
  var bar = document.getElementById('workspace-phase');
  var visible = bar && bar.style.display !== 'none';
  if (cv) cv.classList.toggle('extraction-strip-active', visible);
}

function showIngestStrip(label, sourceKind) {
  _ingestActive = true;
  if (sourceKind) setExtractionSource(sourceKind);
  var bar = document.getElementById('workspace-phase');
  if (!bar) return;
  var badge = document.getElementById('wp-badge');
  var nameEl = document.getElementById('wp-name');
  var turnEl = document.getElementById('wp-turn');
  var qualityEl = document.getElementById('wp-quality');
  var pathEl = document.getElementById('wp-source');
  var fin = document.getElementById('wp-finalize');
  bar.style.display = 'flex';
  bar.className = 'workspace-phase ingest';
  if (badge) { badge.textContent = '资料处理中'; badge.className = 'wp-badge ingest'; }
  if (pathEl) pathEl.textContent = _SOURCE_LABELS[_extractionSource] || '';
  if (nameEl) nameEl.textContent = label || '正在沉淀…';
  if (turnEl) turnEl.textContent = '';
  if (qualityEl) qualityEl.innerHTML = '';
  if (fin) fin.style.display = 'none';
  _syncChatStripChrome();
}

function hideIngestStrip() {
  _ingestActive = false;
  var bar = document.getElementById('workspace-phase');
  if (bar && bar.classList.contains('ingest')) {
    bar.style.display = 'none';
    bar.className = 'workspace-phase';
    var fin = document.getElementById('wp-finalize');
    if (fin) fin.style.display = '';
  }
  _syncChatStripChrome();
}

function hideExtractionStrip() {
  hideIngestStrip();
  var bar = document.getElementById('workspace-phase');
  if (bar) { bar.style.display = 'none'; bar.className = 'workspace-phase'; }
  _syncChatStripChrome();
}

function updateWorkspace(meta) {
  meta = meta || {};
  if (_ingestActive && (meta.skill_active || meta.extraction_phase)) hideIngestStrip();

  var phaseBar = document.getElementById('workspace-phase');
  var divider = document.getElementById('ws-divider');
  var draftPanel = document.getElementById('ws-draft-panel');
  var phase = meta.extraction_phase || '';
  var active = meta.skill_active;
  var name = meta.draft_preview || meta.skill_saved || '';
  var draftContent = meta.draft_content || '';
  var pathEl = document.getElementById('wp-source');

  if (!active || phase === 'IDLE') {
    if (phaseBar && !meta.keep_strip) {
      phaseBar.style.display = 'none';
      phaseBar.className = 'workspace-phase';
    }
    if (divider) divider.style.display = 'none';
    if (draftPanel) draftPanel.style.display = 'none';
    syncFinalizeButton(null);
    _syncChatStripChrome();
    return;
  }

  if (phaseBar) {
    phaseBar.style.display = 'flex';
    phaseBar.className = 'workspace-phase ' + (_PHASE_CSS[phase] || '');
  }
  if (pathEl) pathEl.textContent = _SOURCE_LABELS[_extractionSource] || _SOURCE_LABELS.conversation;
  if (divider) divider.style.display = '';
  if (draftPanel) draftPanel.style.display = '';

  // Phase badge
  var badge = document.getElementById('wp-badge');
  if (badge) {
    badge.textContent = _PHASE_LABELS[phase] || phase;
    badge.className = 'wp-badge ' + (_PHASE_CSS[phase] || '');
  }

  // Skill name
  var nameEl = document.getElementById('wp-name');
  if (nameEl) nameEl.textContent = name || '新技能';

  // Turn count + completion percentage
  var turnEl = document.getElementById('wp-turn');
  if (turnEl) {
    var parts = [];
    if (meta.extraction_turn) parts.push('第 ' + meta.extraction_turn + ' 轮');
    if (meta.completion_pct > 0) parts.push('完整度 ' + meta.completion_pct + '%');
    turnEl.textContent = parts.join(' · ');
  }

  // Quality mini-badges
  var qualityEl = document.getElementById('wp-quality');
  if (qualityEl && typeof renderQualityMiniBadges === 'function') {
    qualityEl.innerHTML = renderQualityMiniBadges(meta, 'md');
  }

  // Sidebar CTA area — show active extraction status
  var sbWs = document.getElementById('sb-workspace-content');
  if (sbWs && name) {
    sbWs.innerHTML = '<div class="sb-ws-item" onclick="showChat()" style="cursor:pointer;padding:var(--s-2);border-radius:var(--r-sm);background:var(--accent-bg);text-align:center">' +
      '<span class="wp-badge ' + (_PHASE_CSS[phase] || '') + '" style="display:inline-block">' + (_PHASE_LABELS[phase] || phase) + '</span>' +
      '<div style="font-size:var(--t-sm);color:var(--text);margin-top:4px;font-weight:500">' + name + '</div>' +
      '</div>';
  }

  // Auto-focus input when done, so user can continue refining
  if (phase === 'DONE') {
    setTimeout(function() {
      var inp = document.getElementById('input');
      if (inp && document.activeElement !== inp) inp.focus();
    }, 300);
  }

  // Finalize / close button — single entry for skill generation
  syncFinalizeButton(phase);

  // Draft panel — phase-aware content
  var draftEl = document.getElementById('ws-draft-content');
  if (draftEl) {
    draftEl.innerHTML = renderDraftPanel(meta, draftContent);
  }
  _syncChatStripChrome();
}

function renderDraftPanel(meta, draftContent) {
  var phase = meta.extraction_phase || '';
  var progress = meta.draft_progress || {};
  var name = meta.draft_preview || meta.skill_saved || '';

  if (!draftContent && !progress.probes_done && phase !== 'DONE' && !progress.goal) {
    return '<div class="ws-draft-empty">对话开始后，草稿将按<strong>目标 → 结构 → 预览</strong>分区生长</div>';
  }

  var html = '<div class="draft-sections">';
  html += _draftSection('当前目标', _draftGoalBody(progress, name), 'draft-goal');
  html += _draftSection('萃取维度', _draftProbeBody(progress), 'draft-probes');
  if (draftContent) {
    html += _draftSection('草稿结构', _draftOutlineBody(draftContent), 'draft-outline');
    html += _draftSection('内容预览', renderDraftMarkdown(draftContent.slice(0, 2400)), 'draft-preview');
  } else if (phase === 'GENERATING') {
    html += '<div class="draft-section draft-generating"><div class="typing-dots"><span></span><span></span><span></span></div> 生成 SKILL.md…</div>';
  }
  if (phase === 'DONE') {
    html += '<div class="draft-done-banner">技能已生成</div>';
    if (meta.diffusion && meta.diffusion.length) {
      html += '<div class="ws-diffusion"><div class="ws-diffusion-title">知识扩散 (' + meta.diffusion.length + ')</div>';
      meta.diffusion.forEach(function(item) { html += '<div class="ws-diffusion-item">' + item + '</div>'; });
      html += '</div>';
    }
  }
  if (draftContent || (progress && progress.probes_done)) {
    html += '<details class="draft-skill-tree-fold"><summary>Skill 文件结构（参考）</summary>' +
      renderSkillTree(progress, draftContent, meta) + '</details>';
  }
  html += '</div>';
  return html;
}

function _draftSection(title, body, cls) {
  return '<div class="draft-section ' + (cls || '') + '">' +
    '<div class="draft-section-title">' + title + '</div>' +
    '<div class="draft-section-body">' + body + '</div></div>';
}

function _draftGoalBody(progress, name) {
  var goal = (progress && progress.goal) || name || '';
  if (!goal) return '<span class="draft-muted">描述工作流程后，目标会出现在这里</span>';
  return '<p class="draft-goal-text">' + _wsEsc(goal) + '</p>';
}

function _draftProbeBody(progress) {
  var probes = (progress && progress.probe_dimensions) || [];
  if (!probes.length) {
    var pct = progress.probes_total ? Math.round((progress.probes_done || 0) / progress.probes_total * 100) : 0;
    return '<span class="draft-muted">' + (progress.probes_done || 0) + '/' + (progress.probes_total || 5) + ' 维度 · ' + pct + '%</span>';
  }
  return '<div class="draft-probe-chips">' + probes.map(function(d) {
    return '<span class="draft-probe-chip' + (d.covered ? ' covered' : '') + '">' +
      (d.covered ? '✓ ' : '') + _wsEsc(d.label || d.key) + '</span>';
  }).join('') + '</div>';
}

function _draftOutlineBody(md) {
  var items = [];
  (md || '').split('\n').forEach(function(line) {
    var m = line.match(/^#{1,3}\s+(.+)/);
    if (m) items.push(m[1].trim());
  });
  if (!items.length) return '<span class="draft-muted">结构尚未成型，继续对话</span>';
  return '<ul class="draft-outline-list">' + items.map(function(t) {
    return '<li>' + _wsEsc(t) + '</li>';
  }).join('') + '</ul>';
}

function _wsEsc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderSkillTree(progress, draftContent, meta) {
  var probes = (progress && progress.probe_dimensions) || [];
  var gotchasDone = false; for (var i = 0; i < probes.length; i++) { if (probes[i].key === 'gotchas' && probes[i].covered) gotchasDone = true; }
  var hasDraft = !!draftContent;

  var items = [
    { icon: '📋', label: 'SKILL.md', sub: '导航页 + 核心步骤', done: hasDraft, hint: hasDraft ? '已有草稿' : '对话中构建' },
    { icon: '📖', label: 'references/', sub: '详细说明、API参考', done: hasDraft, hint: '按需加载' },
    { icon: '📜', label: 'scripts/', sub: '可执行脚本', done: false, hint: '重复步骤提取为脚本' },
    { icon: '📂', label: 'examples/', sub: '示例案例', done: (progress && progress.messages_collected > 3), hint: (progress && progress.messages_collected > 3) ? (progress.messages_collected||0)+'条参考' : '待收集' },
    { icon: '🎨', label: 'assets/', sub: '模板、素材', done: false, hint: '拖拽文件添加' },
    { icon: '⚠️', label: 'Gotchas', sub: '常见坑点', done: gotchasDone, hint: gotchasDone ? '已覆盖' : '对话中追问' },
    { icon: '🔌', label: 'Ecosystem', sub: 'hooks · MCP · subagents', done: (meta && !meta.skill_active), hint: '生成后可配置' },
  ];

  var h = '<div class="skill-tree">';
  items.forEach(function(item) {
    h += '<div class="st-item' + (item.done ? ' st-done' : '') + '">' +
      '<span class="st-icon">' + item.icon + '</span>' +
      '<span class="st-label">' + item.label + '</span>' +
      '<span class="st-sub">' + item.sub + '</span>' +
      '<span class="st-hint">' + item.hint + '</span>' +
      '</div>';
  });
  h += '</div>';
  return h;
}

function renderProgressCard(p, name) {
  var probesHtml = (p.probe_dimensions || []).map(function(d) {
    var icon = d.covered ? '✓' : '⬜';
    var cls = d.covered ? 'ws-probe-done' : 'ws-probe-pending';
    return '<span class="' + cls + '">' + icon + ' ' + d.label + '</span>';
  }).join('');

  var pct = p.probes_total ? Math.round(p.probes_done / p.probes_total * 100) : 0;
  var phaseHint = '';
  if (pct === 0) phaseHint = '开始描述你的工作流程，AI 会追问细节（包括容易踩的坑）';
  else if (pct < 50) phaseHint = '继续对话补充细节，多说说这个流程容易出错的地方';
  else if (pct < 80) phaseHint = '信息接近完整，可以生成草稿了';
  else phaseHint = '信息充足，点击「生成技能」完成萃取';

  return '<div class="ws-progress-card">' +
    '<div class="ws-progress-title">📝 ' + (name || p.draft_name || p.goal || '新技能') + '</div>' +
    '<div class="ws-progress-bar-wrap"><div class="ws-progress-bar" style="width:' + pct + '%"></div></div>' +
    '<div class="ws-progress-pct">' + p.probes_done + '/' + p.probes_total + ' 维度覆盖</div>' +
    '<div class="ws-progress-probes">' + probesHtml + '</div>' +
    '<div class="ws-progress-hint">💡 ' + phaseHint + '</div>' +
    '<div class="ws-progress-meta">' +
      (p.messages_collected || 0) + ' 条消息' +
      (p.has_research ? ' · 已研究行业实践' : '') +
      (p.saturated ? ' · 信息充足' : '') +
    ' · <span style="opacity:.5">自动检测</span>' +
    '</div>' +
    '<div class="ws-progress-meta" style="border-top:none;padding-top:2px;font-size:var(--t-xs);color:var(--text3)">' +
      '生成后可配合 hooks · MCP · subagents 使用' +
    '</div>' +
  '</div>';
}

function syncFinalizeButton(phase) {
  var finalizeEl = document.getElementById('wp-finalize');
  if (!finalizeEl) return;
  if (!phase) {
    finalizeEl.style.display = 'none';
    return;
  }
  finalizeEl.style.display = '';
  if (phase === 'DONE') {
    finalizeEl.textContent = '✕ 关闭工作区';
    finalizeEl.title = '关闭草稿预览，继续对话或开始新萃取';
    finalizeEl.classList.add('wp-finalize-muted');
    finalizeEl.onclick = function() { resetWorkspace(); document.getElementById('input').focus(); };
  } else {
    finalizeEl.textContent = '⚡ 生成技能';
    finalizeEl.title = '将当前对话沉淀为 SKILL.md（唯一生成入口）';
    finalizeEl.classList.remove('wp-finalize-muted');
    finalizeEl.onclick = function() { finalizeSkill(); };
  }
}

function resetWorkspace() {
  _ingestActive = false;
  var phaseBar = document.getElementById('workspace-phase');
  var divider = document.getElementById('ws-divider');
  var draftPanel = document.getElementById('ws-draft-panel');
  var fb = document.getElementById('wp-finalize');
  if (phaseBar) { phaseBar.style.display = 'none'; phaseBar.className = 'workspace-phase'; }
  if (divider) divider.style.display = 'none';
  if (draftPanel) draftPanel.style.display = 'none';
  if (fb) {
    fb.style.display = 'none';
    fb.textContent = '⚡ 生成技能';
    fb.classList.remove('wp-finalize-muted');
    fb.style.background = ''; fb.style.color = ''; fb.style.boxShadow = '';
    fb.onclick = function() { finalizeSkill(); };
  }
  var dc = document.getElementById('ws-draft-content');
  if (dc) dc.innerHTML = '<div class="ws-draft-empty">草稿正在构建中…<br><small>继续对话，AI 会在后台逐步完善</small></div>';
  var sbWs = document.getElementById('sb-workspace-content');
  if (sbWs) sbWs.innerHTML = '<div style="padding:var(--s-2) var(--s-3);font-size:var(--t-xs);color:var(--text3);text-align:center">开始对话萃取新技能</div>';
  // Also reset the session ID so it starts fresh
  if (typeof _sessionId !== 'undefined') _sessionId = '';
  localStorage.removeItem(StorageKeys.SESSION);
  _syncChatStripChrome();
}

function renderPipelineLog(log) {
  if (!log || !log.length) return '';
  var steps = log.map(function(entry, i) {
    var icon = '⏳';
    if (entry.indexOf('完成') >= 0 || entry.indexOf('✅') >= 0) icon = '✅';
    else if (entry.indexOf('扩散') >= 0) icon = '🌐';
    return '<div class="ws-pipeline-step">' +
      '<span class="ws-pipeline-icon">' + icon + '</span>' +
      '<span class="ws-pipeline-text">' + (typeof entry === 'string' ? entry : (entry.step || '')) + '</span>' +
      '</div>';
  }).join('');
  return '<div class="ws-pipeline"><div class="ws-pipeline-title">📖 学习过程 (' + log.length + ' 步)</div>' + steps + '</div>';
}

function toggleDraftPanel() {
  var panel = document.getElementById('ws-draft-panel');
  var toggle = document.getElementById('ws-draft-toggle');
  if (!panel) return;
  panel.classList.toggle('collapsed');
  if (toggle) toggle.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
}

function renderDraftMarkdown(md) {
  if (!md) return '<div class="ws-draft-empty">草稿正在构建中…</div>';
  try {
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(md);
    }
  } catch(e) {}
  // Fallback: basic escaping for safety
  return '<pre style="white-space:pre-wrap;font:var(--t-sm)/1.5 var(--mono);color:var(--text2)">' +
    md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
    '</pre>';
}

// ── Divider drag-to-resize ──────────────────────────

(function initDividerDrag() {
  var divider = document.getElementById('ws-divider');
  var draftPanel = document.getElementById('ws-draft-panel');
  if (!divider || !draftPanel) return;

  var isDragging = false, startX = 0, startWidth = 0;

  divider.addEventListener('mousedown', function(e) {
    isDragging = true;
    startX = e.clientX;
    startWidth = draftPanel.offsetWidth;
    divider.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    var dx = startX - e.clientX;
    var newWidth = startWidth + dx;
    if (newWidth >= 240 && newWidth <= 640) {
      draftPanel.style.width = newWidth + 'px';
    }
  });

  document.addEventListener('mouseup', function() {
    if (!isDragging) return;
    isDragging = false;
    divider.classList.remove('active');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
})();
