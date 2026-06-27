/* SkillOS — Knowledge Views (Alpine.js)
 * Phase 9 migration. Alpine-managed knowledge browser with reactive filters.
 */

// ── Helpers ────────────────────────────────────────────

function _renderView(viewId, contentId, html) {
  var el = document.getElementById(contentId);
  if (el) el.innerHTML = html;
  var view = document.getElementById(viewId);
  if (view && view.__x) { view.__x.$data.html = html; }
}

// ── Constants ─────────────────────────────────────────

var _EVENT_LABELS = {
  skill_created:'技能创建', skill_optimized:'技能优化', knowledge_ingested:'知识摄入',
  claim_verified:'声明验证', cycle_started:'沉淀开始', cycle_completed:'沉淀完成', extraction:'技能萃取'
};
var _CYCLE_STATUS_LABELS = {pending:'待处理', digesting:'消化中', extracting:'萃取中', verifying:'验证中', embedding:'嵌入中', completed:'已完成', failed:'失败'};

function _eventLabel(type) { return _EVENT_LABELS[type] || type || '事件'; }
function _cycleStatusColor(status) {
  const m = {completed:'var(--accent)', failed:'var(--err)', pending:'var(--text3)', digesting:'var(--info)', extracting:'var(--warn)', verifying:'var(--warn)', embedding:'var(--info)'};
  return m[status] || 'var(--text3)';
}

// ── UI helpers ────────────────────────────────────────

function _viewHeader(title, subtitle) {
  return '<div class="knowledge-section-head"><div class="knowledge-section-title">'+escHtml(title)+'</div>'+(subtitle?'<div class="knowledge-section-sub">'+escHtml(subtitle)+'</div>':'')+'</div>';
}

function _emptyIcon(name) {
  return typeof Icons !== 'undefined' && Icons.svg ? '<div class="empty-state-icon">'+Icons.svg(name)+'</div>' : '<div class="empty-state-icon"></div>';
}

function _quickNav(active) {
  return '';
}

function _kpiCard(label, value, color, hint) {
  return '<div class="dash-card"><div class="value kpi-value" style="--kpi-color:'+color+'">'+value+'</div><div class="label">'+label+'</div>'+(hint?'<div class="kpi-hint">'+hint+'</div>':'')+'</div>';
}

function _kpiToggle(id, label, value, color, hint) {
  return '<div class="dash-card kpi-toggle" onclick="toggleKPIDetail(\''+id+'\')"><div class="value kpi-value" style="--kpi-color:'+color+'">'+value+'</div><div class="label">'+label+'</div>'+(hint?'<div class="kpi-hint">'+hint+'</div>':'')+'</div><div class="kpi-panel" id="kpi-panel-'+id+'"></div>';
}

function toggleKPIDetail(id) {
  var panel = document.getElementById('kpi-panel-'+id);
  if (panel) panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}

function handleLineageZoom(btn) {
  var pre = document.getElementById('lineage-mermaid');
  if (!pre) return;
  if (pre.style.maxHeight) { pre.style.maxHeight=''; pre.style.overflow=''; btn.textContent='🔍 全屏'; }
  else { pre.style.maxHeight='80vh'; pre.style.overflow='auto'; btn.textContent='缩小'; }
}

// ── Alpine: Knowledge Browser ─────────────────────────

function knowledgeView() {
  return {
    items: [], loading: true, filterCategory: '', filterStatus: 'all',
    categories: [], kpiTotal: 0, kpiKnowledge: 0, kpiExperience: 0, kpiPending: 0,

    async init() {
      this.loading = true;
      try {
        var r = await api('/api/knowledge/'); if (!r.ok) { this.loading=false; return; }
        var d = await r.json(); this.items = d.items || [];
        var cats = new Set(); this.items.forEach(function(i){ if(i.category) cats.add(i.category); });
        this.categories = Array.from(cats);
        this.kpiTotal = this.items.length;
        this.kpiKnowledge = this.items.filter(function(i){return i.level==='knowledge'}).length;
        this.kpiExperience = this.items.filter(function(i){return i.level==='experience'}).length;
        this.kpiPending = this.items.filter(function(i){return i.status==='pending'||i.level==='experience'}).length;
      } catch(e) { console.warn('epistemic load failed:', e); }
      this.loading = false;
    },

    get filteredItems() {
      var list = this.items;
      if (this.filterCategory) list = list.filter(function(i){return i.category===this.filterCategory;}.bind(this));
      if (this.filterStatus === 'knowledge') list = list.filter(function(i){return i.level==='knowledge'});
      else if (this.filterStatus === 'experience') list = list.filter(function(i){return i.level==='experience'});
      else if (this.filterStatus === 'pending') list = list.filter(function(i){return i.status==='pending'||i.level==='experience'});
      return list;
    },

    setCategory: function(cat) { this.filterCategory = this.filterCategory === cat ? '' : cat; },
    setStatus: function(s) { this.filterStatus = this.filterStatus === s ? 'all' : s; },
    levelLabel: function(level) {
      var m = {knowledge:'已验证', experience:'经验', evidence:'证据', preference:'偏好', error:'已证伪'};
      return m[level] || level;
    },
    levelColor: function(level) {
      var m = {knowledge:'var(--accent)', experience:'var(--warn)', evidence:'var(--text3)', preference:'var(--text3)', error:'var(--err)'};
      return m[level] || 'var(--text3)';
    }
  };
}

// ── Views ─────────────────────────────────────────────

function showDashboard() { showUnifiedKnowledge('dashboard'); }
function showGraphView() { showUnifiedKnowledge('graph'); }
function showJournalView() { showUnifiedKnowledge('journal'); }
function showKnowledgeView() { showUnifiedKnowledge('knowledge'); }
function showLineageView() { showUnifiedKnowledge('lineage'); }
function showPrecipitateView() { showUnifiedKnowledge('precipitate'); }
function showReviewView() { showUnifiedKnowledge('review'); }

// Dashboard

async function loadDashboard() {
  var el = document.getElementById('dash-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-line w60"></div><div class="skeleton skeleton-card"></div></div>';
  try {
    var results = await Promise.all([
      api('/api/knowledge/metrics').catch(function(){ return null; }),
      api('/api/knowledge/journal?limit=15').catch(function(){ return null; }),
      api('/api/knowledge/graph/clusters').catch(function(){ return null; }),
    ]);
    var metrics = results[0]&&results[0].ok ? await results[0].json() : {};
    var journal = results[1]&&results[1].ok ? await results[1].json() : {};
    var clusters = results[2]&&results[2].ok ? await results[2].json() : {};
    var events = journal.events || [];
    var h = '<div class="knowledge-kpi-grid">'+
      _kpiCard('总节点',clusters.total_nodes||'—','var(--accent)','知识图谱节点')+
      _kpiCard('总边',clusters.total_edges||'—','var(--info)','关系连接数')+
      _kpiCard('知识簇',(clusters.clusters||[]).length||'—','var(--a3)','自动聚类')+
      _kpiCard('覆盖率',metrics.lineage_coverage_pct ? Math.round(metrics.lineage_coverage_pct)+'%' : '—','var(--warn)','血缘覆盖率')+'</div>'+
      '<div class="content-card"><div class="content-card-header">知识图谱概览</div>';
    if (clusters.clusters && clusters.clusters.length) {
      h += '<table class="knowledge-table"><thead><tr><th>簇ID</th><th>标签</th><th>节点</th><th>凝聚度</th></tr></thead><tbody>';
      clusters.clusters.forEach(function(c){
        h += '<tr><td>'+c.id+'</td><td>'+escHtml(c.label||'')+'</td><td>'+c.nodes+'</td><td>'+Math.round((c.cohesion||0)*100)+'%</td></tr>';
      });
      h += '</tbody></table>';
    } else h += '<div class="content-empty">暂无知识簇<br><small>积累更多知识后系统会自动发现聚类关系</small></div>';
    h += '</div>'+
      '<div class="content-card"><div class="content-card-header">最近事件</div>';
    h += (events.length ? '<table class="knowledge-table"><thead><tr><th>时间</th><th>类型</th><th>内容</th></tr></thead><tbody>' + events.slice(0,10).map(function(e){
      return '<tr><td class="knowledge-td-time">'+(e.timestamp||'').slice(0,16)+'</td><td>'+_eventLabel(e.type)+'</td><td>'+escHtml((e.summary||e.content||'').slice(0,60))+'</td></tr>';
    }).join('') + '</tbody></table>' : '<div class="content-empty">暂无事件</div>') + '</div>';
    el.innerHTML = h;
  } catch(e) {
    el.innerHTML = '<div class="empty-state">'+_emptyIcon('chart')+'<div class="title">概览暂不可用</div><div class="hint">请确认后端服务已启动</div><button class="btn-primary" onclick="loadDashboard()">重试</button></div>';
  }
}

// Graph

async function loadGraphView() {
  var el = document.getElementById('graph-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-block"></div></div>';
  try {
    var r = await api('/api/knowledge/graph/clusters'), d = await r.json();
    var clusters = d.clusters || [];
    var totalNodes = d.total_nodes || 0, totalEdges = d.total_edges || 0;
    var h = _viewHeader('知识图谱','概念与关系网络');
    h += '<div class="knowledge-kpi-grid">'+_kpiCard('节点',totalNodes,'var(--accent)')+_kpiCard('边',totalEdges,'var(--info)')+_kpiCard('簇',clusters.length,'var(--warn)')+'</div>';
    if (clusters.length) {
      h += '<div class="content-card"><div class="content-card-header">知识簇 ('+clusters.length+')</div>';
      clusters.forEach(function(c) {
        h += '<div class="content-row knowledge-cluster-row"><span class="knowledge-cluster-id">簇 '+c.id+'</span><span class="content-row-value">'+escHtml(c.label||'')+'</span><span class="content-row-meta">'+c.nodes+' 节点 · 凝聚度 '+Math.round((c.cohesion||0)*100)+'%</span></div>';
      });
      h += '</div>';
    } else h += '<div class="content-empty">暂无知识簇数据<br><small>积累更多知识后，系统会自动发现知识之间的聚类关系</small></div>';
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<div class="empty-state">'+_emptyIcon('graph')+'<div class="title">加载失败</div><button class="btn-primary" onclick="loadGraphView()">重试</button></div>'; }
}

// Journal

async function loadJournalView() {
  var el = document.getElementById('journal-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-line w60"></div><div class="skeleton skeleton-card"></div></div>';
  try {
    var r = await api('/api/knowledge/journal?limit=50'), d = await r.json(), events = d.events||[];
    var h = _viewHeader('事件日志','知识库变更记录')+'<div class="content-card">';
    h += events.length ? '<table class="knowledge-table"><thead><tr><th>时间</th><th>类型</th><th>内容</th></tr></thead><tbody>' + events.map(function(e){
      return '<tr><td class="knowledge-td-time">'+(e.timestamp||'').slice(0,16)+'</td><td class="knowledge-td-type">'+_eventLabel(e.type)+'</td><td>'+escHtml((e.summary||e.content||'').slice(0,80))+'</td></tr>';
    }).join('') + '</tbody></table>' : '<div class="content-empty">暂无事件<br><small>创建技能、摄入知识、验证声明后会自动记录</small></div>';
    el.innerHTML = h + '</div>';
  } catch(e) { el.innerHTML = '<div class="empty-state">'+_emptyIcon('journal')+'<div class="title">加载失败</div></div>'; }
}

async function loadPrecipitateView() {
  var el = document.getElementById('precipitate-content'); if (!el) return;
  el.innerHTML = _viewHeader('后台摄入','异步资料消化与队列 — 喂大脑，不是做 Skill')+
    '<div class="content-card"><div class="content-card-header">手动触发摄入循环</div><button type="button" class="btn-primary" onclick="submitKnowledgeCycle()">启动摄入循环</button><div id="precipitate-progress" class="precipitate-progress"></div></div>'+
    '<div class="content-card"><div class="content-card-header">最近摄入任务</div><div id="recent-cycle-tasks"><div class="content-empty">加载中…</div></div></div>';
  loadRecentCycleTasks(); loadIngestionQueuePanel();
}

// Knowledge Browser (Alpine mount)

function loadKnowledgeView() {
  var el = document.getElementById('knowledge-content'); if (!el) return;
  el.innerHTML = _viewHeader('知识库','已验证知识 + 待审核经验')+
    '<div x-data="knowledgeView()" x-init="init()">'+
    '<template x-if="loading"><div class="knowledge-skeleton"><div class="skeleton skeleton-line w60"></div><div class="skeleton skeleton-card"></div></div></template>'+
    '<template x-if="!loading"><div>'+
    '<div class="kb-filter-row">'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'all\'}" @click="setStatus(\'all\')">全部 (<span x-text="kpiTotal"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'knowledge\'}" @click="setStatus(\'knowledge\')">已验证 (<span x-text="kpiKnowledge"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'experience\'}" @click="setStatus(\'experience\')">经验 (<span x-text="kpiExperience"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'pending\'}" @click="setStatus(\'pending\')">待审核 (<span x-text="kpiPending"></span>)</span></div>'+
    '<template x-if="categories.length"><div class="kb-filter-row kb-filter-cats">'+
    '<template x-for="cat in categories" :key="cat"><span class="kb-filter" :class="{\'active-kb-filter\':filterCategory===cat}" @click="setCategory(cat)" x-text="cat"></span></template></div></template>'+
    '<template x-if="!filteredItems.length"><div class="content-empty">暂无匹配项</div></template>'+
    '<template x-for="item in filteredItems" :key="item.id||item.content"><div class="content-row kb-item-row">'+
    '<span class="kb-level" :style="\'color:\'+levelColor(item.level)" x-text="levelLabel(item.level)"></span><span class="kb-cat" x-text="item.category||\'\'"></span><span class="kb-spacer"></span><span class="kb-source" x-text="(item.source||\'\').substring(0,30)"></span>'+
    '<div class="kb-item-body" x-text="item.content||\'\'"></div></div></template></div></template></div>';
  setTimeout(function(){ var m = el.querySelector('[x-data]'); if (m && !m.__x && typeof Alpine!=='undefined') Alpine.initTree(m); }, 10);
}

// Lineage

async function loadLineageView() {
  var el = document.getElementById('lineage-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-block"></div></div>';
  try {
    var r = await api('/api/knowledge/lineage'), d = await r.json();
    var h = _viewHeader('数据血缘','从源头到知识的完整链路');
    if (d.mermaid) {
      h += '<div class="content-card lineage-card"><pre class="mermaid" id="lineage-mermaid">'+escHtml(d.mermaid)+'</pre></div><div class="lineage-actions"><button type="button" class="nav-sm lineage-zoom-btn" onclick="handleLineageZoom(this)"><span class="nav-icon" data-icon="zoom"></span>全屏</button></div>';
      el.innerHTML = h;
      if (typeof hydrateIcons === 'function') hydrateIcons(el);
      setTimeout(function(){renderMermaidInto('lineage-mermaid',d.mermaid);},50);
    } else {
      el.innerHTML = h + '<div class="content-empty">暂无血缘数据</div>';
    }
  } catch(e) { el.innerHTML = '<div class="empty-state">'+_emptyIcon('link')+'<div class="title">加载失败</div></div>'; }
}

function loadLineageGraph(sessionId) {
  var el = document.getElementById('lineage-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-block"></div></div>';
  api('/api/knowledge/lineage?session_id='+encodeURIComponent(sessionId)).then(function(r){return r.json()}).then(function(d){
    if (d.mermaid) {
      el.innerHTML = _viewHeader('数据血缘','会话: '+sessionId)+'<div class="content-card lineage-card"><pre class="mermaid" id="lineage-mermaid">'+escHtml(d.mermaid)+'</pre></div>';
      setTimeout(function(){renderMermaidInto('lineage-mermaid',d.mermaid);},50);
    }
  });
}

// Review

async function loadReviewView() {
  var el = document.getElementById('review-content'); if (!el) return;
  el.innerHTML = '<div class="knowledge-skeleton"><div class="skeleton skeleton-line w60"></div><div class="skeleton skeleton-card"></div></div>';
  try {
    var r = await api('/api/knowledge/review'), d = await r.json(), items = d.items||[];
    var h = _viewHeader('审核队列','待确认的经验与声明');
    h += items.length ? items.map(function(item){
      return '<div class="content-card review-card"><div class="review-card-body">'+escHtml(item.content||item.claim||'')+'</div><div class="review-card-meta"><span>来源: '+escHtml(item.source||'—')+'</span><span>置信度: '+(item.confidence||'—')+'</span></div><div class="review-card-actions"><button type="button" class="btn-primary btn-sm" onclick="confirmReviewItem(' + JSON.stringify(item.id||'') + ',true)">确认</button><button type="button" class="btn-ghost btn-sm review-reject" onclick="confirmReviewItem(' + JSON.stringify(item.id||'') + ',false)">驳回</button></div></div>';
    }).join('') : '<div class="content-empty">暂无待审核项<br><small>知识摄入后，系统会自动生成审核项</small></div>';
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<div class="empty-state">'+_emptyIcon('review')+'<div class="title">加载失败</div></div>'; }
}

async function confirmReviewItem(id, approved) {
  await api('/api/knowledge/review/'+encodeURIComponent(id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:approved})});
  toast(approved?'已确认':'已驳回','success'); showReviewView();
}

// ── Cycle polling ────────────────────────────────────

var _cyclePollTimer = null;
function _stopCyclePoll() { if (_cyclePollTimer) { clearInterval(_cyclePollTimer); _cyclePollTimer = null; } }

function _renderCycleProgress(task) {
  var pct = task.progress||0;
  return '<div class="content-card cycle-card"><div class="cycle-card-head"><span class="cycle-card-title">'+escHtml(task.label||task.task_id)+'</span><span class="cycle-card-status" style="color:'+_cycleStatusColor(task.status)+'">'+(_CYCLE_STATUS_LABELS[task.status]||task.status)+'</span></div><div class="cycle-progress-bar"><div class="cycle-progress-fill" style="width:'+pct+'%"></div></div><div class="cycle-card-msg">'+escHtml(task.message||'')+'</div></div>';
}

function pollKnowledgeCycle(taskId, onUpdate, onDone) {
  _stopCyclePoll();
  _cyclePollTimer = setInterval(async function(){
    try {
      var r = await api('/api/knowledge/cycle/'+encodeURIComponent(taskId)+'/status');
      if (!r.ok) { _stopCyclePoll(); if (onDone) onDone({status:'error',message:'HTTP '+r.status}); return; }
      var d = await r.json(); if (onUpdate) onUpdate(d);
      if (d.status==='completed'||d.status==='failed') { _stopCyclePoll(); if (onDone) onDone(d); }
    } catch(e) { _stopCyclePoll(); if (onDone) onDone({status:'error',message:e.message}); }
  }, 2000);
}

async function submitKnowledgeCycle() {
  toast('启动知识沉淀…','info');
  try {
    var r = await api('/api/knowledge/cycle',{method:'POST'}), d = await r.json(), taskId = d.task_id;
    var progressEl = document.getElementById('precipitate-progress');
    if (progressEl) {
      pollKnowledgeCycle(taskId, function(task){ if(progressEl) progressEl.innerHTML = _renderCycleProgress(task); }, function(result){
        if(progressEl) progressEl.innerHTML = '<div class="cycle-result '+(result.status==='completed'?'ok':'err')+'">'+(result.status==='completed'?'沉淀完成':'沉淀失败: '+escHtml(result.message||''))+'</div>'+_renderCycleProgress(result);
        loadRecentCycleTasks();
      });
    }
    toast('沉淀循环已启动: '+taskId,'success');
  } catch(e) { toast('启动失败: '+e.message,'error'); }
}

async function loadRecentCycleTasks() {
  var el = document.getElementById('recent-cycle-tasks'); if (!el) return;
  try {
    var r = await api('/api/knowledge/cycle-tasks?limit=5'), d = await r.json(), tasks = d.tasks||[];
    el.innerHTML = tasks.length ? tasks.map(function(t){return _renderCycleProgress(t);}).join('') : '<div class="content-empty">暂无沉淀任务</div>';
  } catch(e) { el.innerHTML = '<div class="content-empty content-empty-err">加载失败</div>'; }
}

async function loadIngestionQueuePanel() {
  var el = document.getElementById('recent-cycle-tasks'); if (!el) return;
  try {
    var r = await api('/api/knowledge/ingestion-queue'), d = await r.json(), items = d.items||[];
    if (items.length) el.innerHTML = (el.innerHTML||'')+'<div class="content-card ingest-queue-card"><div class="content-card-header">摄入队列 ('+items.length+')</div>'+items.map(function(i){return '<div class="ingest-queue-item"><span class="nav-icon" data-icon="file"></span>'+escHtml(i.source||i.url||'')+' <span class="ingest-queue-status">'+(i.status||'queued')+'</span></div>';}).join('')+'</div>';
    if (typeof hydrateIcons === 'function') hydrateIcons(el);
  } catch(e) { console.warn('ingest queue render failed:', e); }
}

function resumeCycleTask(taskId) {
  toast('恢复任务…','info');
  api('/api/knowledge/cycle/'+encodeURIComponent(taskId)+'/resume',{method:'POST'}).then(function(){toast('任务已恢复','success');showPrecipitateView();});
}

// ── Unified Knowledge View ──────────────────────────────

function showUnifiedKnowledge(tab) {
  tab = tab || 'dashboard';
  if (window.__alpineReady && typeof Alpine !== 'undefined' && Alpine.store('nav')) {
    Alpine.store('nav').goTo('knowledge-unified-view');
  } else if (typeof switchMainView === 'function') {
    switchMainView('knowledge-unified-view');
  }
  switchKnowledgeTab(tab);
}

function switchKnowledgeTab(tab) {
  if (window.__alpineReady && typeof Alpine !== 'undefined' && Alpine.store('nav')) {
    Alpine.store('nav').knowledgeTab = tab;
  }
  document.querySelectorAll('#knowledge-tabs .kt').forEach(function(btn) {
    btn.classList.toggle('active', btn.getAttribute('data-kt') === tab);
  });
  if (typeof hydrateIcons === 'function') hydrateIcons(document.getElementById('knowledge-tabs'));

  var container = document.getElementById('knowledge-tab-content');
  if (!container) return;

  container.innerHTML = '<div class="knowledge-skeleton">' +
    '<div class="skeleton skeleton-line w60"></div>' +
    '<div class="skeleton skeleton-line w80"></div>' +
    '<div class="skeleton skeleton-line w40"></div>' +
    '<div class="skeleton skeleton-card"></div>' +
    '</div>';

  var contentIdMap = {
    dashboard: 'dash-content', knowledge: 'knowledge-content', graph: 'graph-content',
    lineage: 'lineage-content', precipitate: 'precipitate-content', review: 'review-content',
    journal: 'journal-content'
  };
  var fnMap = {
    dashboard: loadDashboard, knowledge: loadKnowledgeView, graph: loadGraphView,
    lineage: loadLineageView, precipitate: loadPrecipitateView, review: loadReviewView,
    journal: loadJournalView
  };

  var srcId = contentIdMap[tab];
  var loadFn = typeof fnMap[tab] === 'function' ? fnMap[tab] : null;

  if (tab === 'account') {
    if (typeof showAccountWatcher === 'function') showAccountWatcher();
    return;
  }

  if (!loadFn || !srcId) {
    container.innerHTML = '<div class="empty-state"><div class="title">视图暂不可用</div></div>';
    return;
  }

  var srcEl = document.getElementById(srcId);
  if (!srcEl) { container.innerHTML = '<div class="empty-state"><div class="title">加载失败</div></div>'; return; }

  // Use MutationObserver to detect when legacy loader writes content
  var observer = new MutationObserver(function() {
    var html = srcEl.innerHTML || '';
    // Skip skeleton/loading states — only copy when real content arrives
    if (html && html.indexOf('skeleton') < 0 && html.indexOf('加载') < 0) {
      container.innerHTML = html;
      if (typeof hydrateIcons === 'function') hydrateIcons(container);
      observer.disconnect();
    }
  });
  observer.observe(srcEl, { childList: true, characterData: true, subtree: true });
  loadFn();

  // Fallback timeout
  setTimeout(function() {
    observer.disconnect();
    if (srcEl.innerHTML && container.innerHTML.indexOf('skeleton') >= 0) {
      container.innerHTML = srcEl.innerHTML;
      if (typeof hydrateIcons === 'function') hydrateIcons(container);
    }
  }, 4000);
}

// Legacy stubs
function filterKB(el) {}
function filterKBStat(type, cardEl) {}
