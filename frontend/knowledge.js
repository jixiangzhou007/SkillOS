/* SkillOS — Knowledge Views (Alpine.js)
 * Phase 9 migration. Alpine-managed knowledge browser with reactive filters.
 */

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
  return '<div class="view-header"><button class="nav-sm" onclick="showChat()">← 返回</button><div><div style="font-size:16px;font-weight:600">'+escHtml(title)+'</div>'+(subtitle?'<div style="font-size:12px;color:var(--text3)">'+escHtml(subtitle)+'</div>':'')+'</div></div>';
}

function _quickNav(active) {
  var items = [
    {id:'dashboard',label:'仪表盘',icon:'📊',fn:'showDashboard()'},
    {id:'graph',label:'图谱',icon:'🧠',fn:'showGraphView()'},
    {id:'journal',label:'日志',icon:'📋',fn:'showJournalView()'},
    {id:'knowledge',label:'知识库',icon:'📚',fn:'showKnowledgeView()'},
    {id:'precipitate',label:'沉淀',icon:'⚗️',fn:'showPrecipitateView()'},
    {id:'review',label:'审核',icon:'✅',fn:'showReviewView()'},
    {id:'lineage',label:'血缘',icon:'🔗',fn:'showLineageView()'},
  ];
  return '<div class="tab-row" style="margin-bottom:16px;flex-wrap:wrap">'+items.map(function(i){
    return '<button class="tab'+(i.id===active?' active':'')+'" onclick="'+i.fn+'">'+i.icon+' '+i.label+'</button>';
  }).join('')+'</div>';
}

function _kpiCard(label, value, color, hint) {
  return '<div class="dash-card"><div class="value" style="color:'+color+'">'+value+'</div><div class="label">'+label+'</div>'+(hint?'<div style="font-size:10px;color:var(--text3)">'+hint+'</div>':'')+'</div>';
}

function _kpiToggle(id, label, value, color, hint) {
  return '<div class="dash-card" style="cursor:pointer" onclick="toggleKPIDetail(\''+id+'\')"><div class="value" style="color:'+color+'">'+value+'</div><div class="label">'+label+'</div>'+(hint?'<div style="font-size:10px;color:var(--text3)">'+hint+'</div>':'')+'</div><div class="kpi-panel" id="kpi-panel-'+id+'"></div>';
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
      } catch(e) {}
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
      var m = {knowledge:'✅ 已验证', experience:'📝 经验', evidence:'📄 证据', preference:'💭 偏好', error:'❌ 已证伪'};
      return m[level] || level;
    },
    levelColor: function(level) {
      var m = {knowledge:'var(--accent)', experience:'var(--warn)', evidence:'var(--text3)', preference:'var(--text3)', error:'var(--err)'};
      return m[level] || 'var(--text3)';
    }
  };
}

// ── Views ─────────────────────────────────────────────

function showDashboard() { switchMainView('dashboard-view'); document.getElementById('bar').style.display='none'; loadDashboard(); }
function showGraphView() { switchMainView('graph-view'); document.getElementById('bar').style.display='none'; loadGraphView(); }
function showJournalView() { switchMainView('journal-view'); document.getElementById('bar').style.display='none'; loadJournalView(); }
function showKnowledgeView() { switchMainView('knowledge-view'); document.getElementById('bar').style.display='none'; loadKnowledgeView(); }
function showLineageView() { switchMainView('lineage-view'); document.getElementById('bar').style.display='none'; loadLineageView(); }
function showPrecipitateView() { switchMainView('precipitate-view'); document.getElementById('bar').style.display='none'; loadPrecipitateView(); }
function showReviewView() { switchMainView('review-view'); document.getElementById('bar').style.display='none'; loadReviewView(); }

// Dashboard

async function loadDashboard() {
  var el = document.getElementById('dash-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载仪表盘…</div>';
  try {
    var statsR = await api('/api/knowledge/stats'), recentR = await api('/api/knowledge/recent?limit=10');
    var stats = statsR.ok ? await statsR.json() : {}, recent = recentR.ok ? (await recentR.json()).items||[] : [];
    var h = _viewHeader('知识仪表盘','知识库总览') + _quickNav('dashboard') +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px">'+
      _kpiCard('知识节点',stats.total_nodes||0,'var(--accent)','概念、事实、技能')+
      _kpiCard('已验证',stats.verified||0,'#10b981','Plato 四条件通过')+
      _kpiCard('待验证',stats.pending||0,'var(--warn)','经验、声明待审核')+
      _kpiCard('图谱边',stats.edges||0,'var(--info)','关系连接')+'</div>'+
      '<div style="font-size:14px;font-weight:600;color:var(--text);margin-bottom:8px">最近活动</div>';
    el.innerHTML = h + (recent.length ? recent.map(function(e){
      return '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;display:flex;gap:8px"><span>'+(e.type==='knowledge_ingested'?'📥':e.type==='claim_verified'?'✅':'📌')+'</span><span style="flex:1;color:var(--text2)">'+escHtml(e.summary||e.content||'')+'</span><span style="color:var(--text3);white-space:nowrap">'+_eventLabel(e.type)+'</span></div>';
    }).join('') : '<div style="color:var(--text3);font-size:12px;padding:20px">暂无活动</div>') + '</div>';
  } catch(e) { el.innerHTML = _viewHeader('知识仪表盘','')+_quickNav('dashboard')+'<div style="color:var(--err)">加载失败</div>'; }
}

// Graph

async function loadGraphView() {
  var el = document.getElementById('graph-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载知识图谱…</div>';
  try {
    var r = await api('/api/knowledge/graph'), d = await r.json();
    if (d.mermaid) {
      el.innerHTML = _viewHeader('知识图谱','概念与关系网络')+_quickNav('graph')+'<div style="overflow:auto;background:var(--srf);border-radius:8px;padding:12px"><pre class="mermaid" id="kg-mermaid" style="margin:0;background:transparent">'+escHtml(d.mermaid)+'</pre></div>';
      setTimeout(function(){renderMermaidInto('kg-mermaid',d.mermaid);},50);
    } else el.innerHTML = _viewHeader('知识图谱','')+_quickNav('graph')+'<div style="color:var(--text3);padding:20px">暂无图谱数据</div>';
    el.innerHTML += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:12px">'+_kpiCard('节点',d.total_nodes||0,'var(--accent)')+_kpiCard('边',d.total_edges||0,'var(--info)')+_kpiCard('簇',d.clusters||0,'var(--warn)')+'</div>';
  } catch(e) { el.innerHTML = _viewHeader('知识图谱','')+_quickNav('graph')+'<div style="color:var(--err)">加载失败</div>'; }
}

// Journal

async function loadJournalView() {
  var el = document.getElementById('journal-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载事件日志…</div>';
  try {
    var r = await api('/api/knowledge/journal?limit=50'), d = await r.json(), events = d.events||[];
    el.innerHTML = _viewHeader('事件日志','知识库变更记录')+_quickNav('journal')+(events.length?events.map(function(e){return '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;display:flex;gap:8px"><span style="color:var(--text3);white-space:nowrap">'+(e.timestamp||'').substring(0,16)+'</span><span style="color:var(--accent);white-space:nowrap">'+_eventLabel(e.type)+'</span><span style="flex:1;color:var(--text2)">'+escHtml(e.summary||e.content||'')+'</span></div>';}).join(''):'<div style="color:var(--text3);padding:20px">暂无事件</div>')+'</div>';
  } catch(e) { el.innerHTML = _viewHeader('事件日志','')+_quickNav('journal')+'<div style="color:var(--err)">加载失败</div>'; }
}

// Knowledge Browser (Alpine mount)

function loadKnowledgeView() {
  var el = document.getElementById('knowledge-content'); if (!el) return;
  el.innerHTML = _viewHeader('知识库','已验证知识 + 待审核经验')+_quickNav('knowledge')+
    '<div x-data="knowledgeView()" x-init="init()">'+
    '<template x-if="loading"><div style="color:var(--text3);padding:20px">加载知识库…</div></template>'+
    '<template x-if="!loading"><div>'+
    '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'all\'}" @click="setStatus(\'all\')">全部 (<span x-text="kpiTotal"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'knowledge\'}" @click="setStatus(\'knowledge\')">已验证 (<span x-text="kpiKnowledge"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'experience\'}" @click="setStatus(\'experience\')">经验 (<span x-text="kpiExperience"></span>)</span>'+
    '<span class="kb-filter" :class="{\'active-kb-filter\':filterStatus===\'pending\'}" @click="setStatus(\'pending\')">待审核 (<span x-text="kpiPending"></span>)</span></div>'+
    '<template x-if="categories.length"><div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap">'+
    '<template x-for="cat in categories" :key="cat"><span class="kb-filter" :class="{\'active-kb-filter\':filterCategory===cat}" @click="setCategory(cat)" x-text="cat"></span></template></div></template>'+
    '<template x-if="!filteredItems.length"><div style="color:var(--text3);padding:20px">暂无匹配项</div></template>'+
    '<template x-for="item in filteredItems" :key="item.id||item.content"><div style="padding:10px 0;border-bottom:1px solid var(--border)">'+
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px"><span :style="\'color:\'+levelColor(item.level)" x-text="levelLabel(item.level)"></span><span style="font-size:11px;color:var(--text3)" x-text="item.category||\'\'"></span><span style="flex:1"></span><span style="font-size:10px;color:var(--text3)" x-text="(item.source||\'\').substring(0,30)"></span></div>'+
    '<div style="font-size:13px;color:var(--text)" x-text="item.content||\'\'"></div></div></template></div></template></div>';
  setTimeout(function(){ var m = el.querySelector('[x-data]'); if (m && !m.__x && typeof Alpine!=='undefined') Alpine.initTree(m); }, 10);
}

// Lineage

async function loadLineageView() {
  var el = document.getElementById('lineage-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载数据血缘…</div>';
  try {
    var r = await api('/api/knowledge/lineage'), d = await r.json();
    if (d.mermaid) {
      el.innerHTML = _viewHeader('数据血缘','从源头到知识的完整链路')+_quickNav('lineage')+'<div style="overflow:auto;background:var(--srf);border-radius:8px;padding:12px;margin-bottom:12px"><pre class="mermaid" id="lineage-mermaid" style="margin:0;background:transparent">'+escHtml(d.mermaid)+'</pre></div><div style="display:flex;gap:8px"><button class="nav-sm" onclick="handleLineageZoom(this)">🔍 全屏</button></div>';
      setTimeout(function(){renderMermaidInto('lineage-mermaid',d.mermaid);},50);
    } else el.innerHTML = _viewHeader('数据血缘','')+_quickNav('lineage')+'<div style="color:var(--text3);padding:20px">暂无血缘数据</div>';
  } catch(e) { el.innerHTML = _viewHeader('数据血缘','')+_quickNav('lineage')+'<div style="color:var(--err)">加载失败</div>'; }
}

function loadLineageGraph(sessionId) {
  var el = document.getElementById('lineage-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载会话血缘…</div>';
  api('/api/knowledge/lineage?session_id='+encodeURIComponent(sessionId)).then(function(r){return r.json()}).then(function(d){
    if (d.mermaid) { el.innerHTML = _viewHeader('数据血缘','会话: '+sessionId)+_quickNav('lineage')+'<div style="overflow:auto;background:var(--srf);border-radius:8px;padding:12px"><pre class="mermaid" id="lineage-mermaid">'+escHtml(d.mermaid)+'</pre></div>'; setTimeout(function(){renderMermaidInto('lineage-mermaid',d.mermaid);},50); }
  });
}

// Precipitate

function loadPrecipitateView() {
  var el = document.getElementById('precipitate-content'); if (!el) return;
  el.innerHTML = _viewHeader('知识沉淀','异步摄入与消化循环')+_quickNav('precipitate')+
    '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px"><div style="font-size:14px;font-weight:600;margin-bottom:8px">手动触发沉淀</div><button class="btn a" style="font-size:13px;padding:8px 20px" onclick="submitKnowledgeCycle()">▶ 启动知识沉淀循环</button><div id="precipitate-progress" style="margin-top:12px"></div></div>'+
    '<div style="margin-top:16px"><div style="font-size:14px;font-weight:600;margin-bottom:8px">最近沉淀任务</div><div id="recent-cycle-tasks">加载中…</div></div>';
  loadRecentCycleTasks(); loadIngestionQueuePanel();
}

// Review

async function loadReviewView() {
  var el = document.getElementById('review-content'); if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载审核队列…</div>';
  try {
    var r = await api('/api/knowledge/review-queue'), d = await r.json(), items = d.items||[];
    el.innerHTML = _viewHeader('审核队列','待确认的经验与声明')+_quickNav('review')+(items.length?items.map(function(item){
      return '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px"><div style="font-size:13px;color:var(--text);margin-bottom:6px">'+escHtml(item.content||item.claim||'')+'</div><div style="font-size:11px;color:var(--text3);margin-bottom:8px">来源: '+escHtml(item.source||'')+' · 置信度: '+(item.confidence||0)+'</div><div style="display:flex;gap:6px"><button class="nav-sm" style="border-color:var(--accent);color:var(--accent);font-size:10px" onclick="confirmReviewItem(\''+(item.id||'')+'\',true)">确认</button><button class="nav-sm" style="color:var(--err);font-size:10px" onclick="confirmReviewItem(\''+(item.id||'')+'\',false)">驳回</button></div></div>';
    }).join(''):'<div style="color:var(--text3);padding:20px">暂无待审核项</div>')+'</div>';
  } catch(e) { el.innerHTML = _viewHeader('审核队列','')+_quickNav('review')+'<div style="color:var(--err)">加载失败</div>'; }
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
  return '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:13px;font-weight:600">'+escHtml(task.label||task.task_id)+'</span><span style="font-size:11px;color:'+_cycleStatusColor(task.status)+'">'+(_CYCLE_STATUS_LABELS[task.status]||task.status)+'</span></div><div style="height:6px;background:#222;border-radius:3px;margin-bottom:4px"><div style="height:100%;background:var(--accent);border-radius:3px;width:'+pct+'%"></div></div><div style="font-size:10px;color:var(--text3)">'+escHtml(task.message||'')+'</div></div>';
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
        if(progressEl) progressEl.innerHTML = (result.status==='completed'?'✅ 沉淀完成':'❌ 沉淀失败: '+escHtml(result.message||''))+'<br>'+_renderCycleProgress(result);
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
    el.innerHTML = tasks.length ? tasks.map(function(t){return _renderCycleProgress(t);}).join('') : '<div style="color:var(--text3);font-size:12px">暂无沉淀任务</div>';
  } catch(e) { el.innerHTML = '<div style="color:var(--err);font-size:12px">加载失败</div>'; }
}

function resumeCycleTask(taskId) {
  toast('恢复任务…','info');
  api('/api/knowledge/cycle/'+encodeURIComponent(taskId)+'/resume',{method:'POST'}).then(function(){toast('任务已恢复','success');showPrecipitateView();});
}

async function loadIngestionQueuePanel() {
  var el = document.getElementById('recent-cycle-tasks'); if (!el) return;
  try {
    var r = await api('/api/knowledge/ingestion-queue'), d = await r.json(), items = d.items||[];
    if (items.length) el.innerHTML = (el.innerHTML||'')+'<div style="margin-top:16px"><div style="font-size:14px;font-weight:600;margin-bottom:8px">摄入队列 ('+items.length+')</div>'+items.map(function(i){return '<div style="padding:4px 0;font-size:11px;color:var(--text2)">📄 '+escHtml(i.source||i.url||'')+' <span style="color:var(--text3)">'+(i.status||'queued')+'</span></div>';}).join('')+'</div>';
  } catch(e) {}
}

// Legacy stubs
function filterKB(el) {}
function filterKBStat(type, cardEl) {}
