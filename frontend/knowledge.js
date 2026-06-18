/* knowledge.js — extracted from app.js */

var _EVENT_LABELS = {
  skill_created: '技能创建',
  skill_optimized: '技能优化',
  url_learned: 'URL 学习',
  knowledge_extracted: '知识萃取',
  analogy_found: '类比发现',
  feynman_deepened: '费曼深化'
};

function _viewHeader(title, subtitle) {
  var h = '<div class="view-header"><button class="nav-sm" onclick="showChat()">← 返回</button><div>';
  h += '<div style="font-size:16px;font-weight:700;color:var(--text)">' + escHtml(title) + '</div>';
  if (subtitle) h += '<div style="font-size:12px;color:var(--text3);margin-top:2px">' + subtitle + '</div>';
  h += '</div></div>';
  return h;
}

function _quickNav(active) {
  var items = [
    ['showDashboard()', '工作台', 'dashboard'],
    ['showKnowledgeView()', '知识库', 'knowledge'],
    ['showPrecipitateView()', '知识沉淀', 'precipitate'],
    ['showReviewView()', '待复核', 'review'],
    ['showGraphView()', '知识图谱', 'graph'],
    ['showLineageView()', '数据溯源', 'lineage'],
    ['showJournalView()', '学习日志', 'journal']
  ];
  var h = '<div class="quick-nav">';
  items.forEach(function(it) {
    var on = active === it[2];
    h += '<button class="nav-sm" onclick="' + it[0] + '" style="' +
      (on ? 'border-color:var(--accent);color:var(--accent)' : '') + '">' + it[1] + '</button>';
  });
  h += '</div>';
  return h;
}

function _eventLabel(type) {
  return _EVENT_LABELS[type] || type || '事件';
}

function _skillCard(name, meta, extraStyle) {
  return '<div class="skill-card" style="margin-bottom:4px;cursor:pointer;' + (extraStyle || '') +
    '" onclick="showDetail(' + JSON.stringify(name) + ')">' +
    '<div class="name">' + escHtml(name) + '</div>' +
    '<div class="meta">' + meta + '</div></div>';
}

function showDashboard() {

  switchMainView('dashboard-view');
  document.getElementById('bar').style.display = 'none';

  let el = document.getElementById('dash-content');

  el.innerHTML = '<div class="dash-grid"><div class="skeleton skeleton-kpi"></div><div class="skeleton skeleton-kpi"></div><div class="skeleton skeleton-kpi"></div></div><div class="skeleton skeleton-card"></div>';

  Promise.all([
    api('/api/skills/'),
    api('/api/knowledge/graph/clusters'),
    api('/api/knowledge/journal'),
    api('/api/knowledge/metrics'),
    api('/api/knowledge/queue')
  ]).then(async function(responses) {
    if (!responses[0].ok) throw new Error('技能列表加载失败');
    let skills = await responses[0].json();
    let graph = responses[1].ok ? await responses[1].json() : { clusters: [], total_nodes: 0, total_edges: 0 };
    let journal = responses[2].ok ? await responses[2].json() : { entries: [] };
    let metrics = responses[3].ok ? await responses[3].json() : {};
    let queueData = responses[4].ok ? await responses[4].json() : { stats: {}, tasks: [] };
    let queue = queueData.stats || {};

    let user = skills.filter(s => !['brainstorming', 'skill-creator', 'deep-digest', 'cold-start-interview'].includes(s.name));
    let meta = user.filter(s => s.name.startsWith('[Meta]'));
    let knowledgePkgs = user.filter(s => (s.kb_items || 0) > 0 && (s.runs || 0) === 0);

    let successPct = metrics.success_rate != null ? Math.round(metrics.success_rate * 100) : null;
    let lineagePct = metrics.lineage_coverage_rate != null ? Math.round(metrics.lineage_coverage_rate * 100) : null;
    let refresher = metrics.refresher || {};
    let refresherLabel = refresher.running ? ('运行中 · ' + (refresher.interval_hours || 24) + 'h') : (refresher.enabled ? '已启用' : '已关闭');
    let queuePending = queue.pending || 0;
    let queueLabel = queuePending ? (queuePending + ' 待处理') : ((queue.done || 0) + ' 已完成');

    let h = _viewHeader('工作台', '技能、知识图谱与学习事件概览');
    h += _quickNav('dashboard');

    h += '<div class="dash-grid">';
    h += _kpiToggle('kpi-skills-panel', '技能', user.length, 'var(--accent)', meta.length + ' Meta · ' + knowledgePkgs.length + ' 知识包');
    h += _kpiToggle('kpi-graph-panel', '图谱节点', graph.total_nodes || 0, 'var(--warn)',
      (graph.total_edges || 0) + ' 边 · ' + (graph.clusters || []).length + ' 簇');
    h += _kpiToggle('kpi-journal-panel', '学习日志', (journal.entries || []).length, 'var(--info)', '最近学习事件');
    h += '</div>';

    h += '<div class="dash-grid" style="margin-top:4px">';
    h += _kpiCard('沉淀成功率', successPct != null ? successPct + '%' : '—', successPct == null ? 'var(--text3)' : (successPct >= 80 ? 'var(--accent)' : 'var(--warn)'),
      (metrics.total_events || 0) + ' 次 · 近 ' + Math.round((metrics.window_hours || 168) / 24) + ' 天');
    h += _kpiCard('血缘覆盖率', lineagePct != null ? lineagePct + '%' : '—', lineagePct == null ? 'var(--text3)' : (lineagePct >= 70 ? 'var(--accent)' : 'var(--warn)'),
      (metrics.lineage_applied_count || 0) + ' 次写入血缘');
    h += _kpiCard('后台刷新', refresher.running ? 'ON' : 'OFF', refresher.running ? 'var(--accent)' : 'var(--text3)', refresherLabel);
    h += _kpiCard('摄入队列', queuePending || '—', queuePending ? 'var(--warn)' : 'var(--text3)', queueLabel + (queue.failed ? ' · ' + queue.failed + ' 失败' : ''));
    h += '</div>';

    if ((metrics.recent_failures || []).length) {
      h += '<div style="margin-top:12px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 16px">';
      h += '<div style="font-size:13px;font-weight:600;color:var(--err);margin-bottom:8px">最近沉淀失败 (' + metrics.recent_failures.length + ')</div>';
      metrics.recent_failures.slice(0, 5).forEach(function(f) {
        h += '<div style="font-size:11px;color:var(--text2);padding:4px 0;border-bottom:1px solid var(--border)">';
        h += '<span style="color:var(--text3)">' + escHtml(f.channel || '') + '</span> · ';
        h += escHtml((f.reason || 'unknown').slice(0, 120));
        if (f.source_url) h += '<div style="font-size:10px;color:var(--text3);margin-top:2px">' + escHtml(f.source_url.slice(0, 80)) + '</div>';
        h += '</div>';
      });
      h += '</div>';
    }

    h += '<div id="kpi-skills-panel" class="kpi-panel" style="display:none">';
    h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">📁 我的技能 (' + user.length + ')</div>';
    if (user.length > 0) {
      user.slice(0, 20).forEach(function(s) {
        let sc = (s.avg_score || 0) >= 4 ? 'var(--accent)' : (s.avg_score || 0) >= 2 ? 'var(--warn)' : 'var(--err)';
        h += _skillCard(s.name, 'v' + (s.version || 1) + ' · <span style="color:' + sc + '">' + (s.avg_score || 0) + '/5</span> · ' + (s.runs || 0) + ' 次运行');
      });
      if (user.length > 20) h += '<div style="font-size:11px;color:var(--text3);padding:8px 0">还有 ' + (user.length - 20) + ' 个技能…</div>';
    } else {
      h += '<div class="empty-state" style="padding:24px"><div class="icon">📁</div><div class="title">还没有技能</div><div class="hint">在对话区描述工作流程，系统会自动沉淀技能</div></div>';
    }
    h += '</div>';

    h += '<div id="kpi-graph-panel" class="kpi-panel" style="display:none">';
    h += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">';
    h += '<div style="font-size:13px;font-weight:600;color:var(--text2)">🧠 主题簇</div>';
    h += '<button class="nav-sm" onclick="showGraphView()">查看图谱 →</button></div>';
    (graph.clusters || []).slice(0, 8).forEach(function(c) {
      let cohesion = c.cohesion != null ? Math.round(c.cohesion * 100) : 0;
      h += '<div style="font-size:12px;color:var(--text2);padding:4px 0">• <b>' + escHtml(c.label || '未命名簇') + '</b>：' +
        (c.nodes || 0) + ' 节点 · 内聚 ' + cohesion + '%</div>';
    });
    if (!graph.clusters || !graph.clusters.length) {
      h += '<div style="font-size:12px;color:var(--text3)">暂无主题簇，积累技能与知识后会自动涌现</div>';
    }
    h += '</div>';

    h += '<div id="kpi-journal-panel" class="kpi-panel" style="display:none">';
    h += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">';
    h += '<div style="font-size:13px;font-weight:600;color:var(--text2)">📖 最近事件</div>';
    h += '<button class="nav-sm" onclick="showJournalView()">全部日志 →</button></div>';
    (journal.entries || []).slice(0, 10).forEach(function(e) {
      let dt = e.timestamp ? new Date(e.timestamp * 1000).toLocaleString() : '';
      h += '<div style="font-size:12px;color:var(--text2);padding:3px 0">' +
        (e.skill_name ? '<b>' + escHtml(e.skill_name) + '</b> · ' : '') +
        escHtml(_eventLabel(e.event_type)) +
        ' <span style="color:var(--text3);font-size:10px">' + dt + '</span></div>';
    });
    if (!journal.entries || !journal.entries.length) {
      h += '<div style="font-size:12px;color:var(--text3)">暂无学习事件</div>';
    }
    h += '</div>';

    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('工作台') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}
function showGraphView() {

  switchMainView('graph-view');
  document.getElementById('bar').style.display = 'none';

  let el = document.getElementById('graph-content');
  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载中…</div>';

  api('/api/knowledge/graph/clusters').then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(d) {
    let h = _viewHeader('知识图谱', '主题簇与节点关系概览');
    h += _quickNav('graph');

    h += '<div class="dash-grid">';
    h += _kpiCard('节点', d.total_nodes || 0, 'var(--accent)', '概念、事实、技能');
    h += _kpiCard('边', d.total_edges || 0, 'var(--info)', '类型化关系');
    h += _kpiCard('主题簇', (d.clusters || []).length, 'var(--warn)', '涌现主题组');
    h += '</div>';

    if (!d.clusters || !d.clusters.length) {
      h += '<div class="empty-state"><div class="icon">🧠</div><div class="title">暂无主题簇</div><div class="hint">技能与知识积累后，主题簇会自动涌现</div></div>';
    } else {
      h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin:16px 0 8px">主题簇</div>';
      (d.clusters || []).forEach(function(c, i) {
        let cohesion = c.cohesion != null ? c.cohesion : 0;
        let cohesionColor = cohesion >= 0.7 ? 'var(--accent)' : cohesion >= 0.4 ? 'var(--warn)' : 'var(--text3)';
        h += '<div class="skill-card" style="margin-bottom:6px;border-left:3px solid ' + cohesionColor + '">';
        h += '<div class="name">' + (i + 1) + '. ' + escHtml(c.label || '未命名簇') + '</div>';
        h += '<div class="meta">' + (c.nodes || 0) + ' 节点 · 内聚 <span style="color:' + cohesionColor + '">' + Math.round(cohesion * 100) + '%</span></div>';
        h += '</div>';
      });
    }

    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('知识图谱') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}
function showJournalView() {

  switchMainView('journal-view');
  document.getElementById('bar').style.display = 'none';

  let el = document.getElementById('journal-content');
  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载日志…</div>';

  api('/api/knowledge/journal').then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(d) {
    if (!d.entries || !d.entries.length) {
      el.innerHTML = _viewHeader('学习日志') + _quickNav('journal') +
        '<div class="empty-state"><div class="icon">📖</div><div class="title">暂无学习事件</div><div class="hint">创建、优化技能或交叉引用时，学习事件会自动记录</div></div>';
      return;
    }

    let groups = {};
    d.entries.forEach(function(e) {
      let day = e.timestamp ? new Date(e.timestamp * 1000).toLocaleDateString() : '未知日期';
      if (!groups[day]) groups[day] = [];
      groups[day].push(e);
    });

    let icons = { skill_created: '📝', skill_optimized: '⚡', url_learned: '🔗', knowledge_extracted: '📚', analogy_found: '🔍', feynman_deepened: '✍️' };
    let h = _viewHeader('学习日志', d.entries.length + ' 条事件');
    h += _quickNav('journal');

    Object.keys(groups).sort().reverse().forEach(function(day) {
      h += '<div style="font-size:11px;font-weight:600;color:var(--text3);margin:12px 0 4px;padding:4px 0;border-bottom:1px solid var(--border)">' + day + ' (' + groups[day].length + ' 条)</div>';
      groups[day].forEach(function(e) {
        let icon = icons[e.event_type] || '📌';
        let tm = e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString() : '';
        h += '<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;font-size:12px;border-radius:4px;margin-bottom:2px">';
        h += '<span style="font-size:16px">' + icon + '</span>';
        h += '<span style="color:var(--text);flex:1">' + (e.skill_name ? '<b>' + escHtml(e.skill_name) + '</b> · ' : '') + escHtml(_eventLabel(e.event_type)) + '</span>';
        h += '<span style="color:var(--text3);font-size:10px">' + tm + '</span></div>';
        if (e.description) h += '<div style="font-size:10px;color:var(--text3);padding:0 8px 4px 32px">' + escHtml(e.description).slice(0, 120) + '</div>';
      });
    });

    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('学习日志') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}
function showKnowledgeView() {

  switchMainView('knowledge-view');
  document.getElementById('bar').style.display = 'none';

  let el = document.getElementById('knowledge-content');
  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载知识库…</div>';

  Promise.all([api('/api/knowledge/'), api('/api/skills/')]).then(async function(responses) {
    if (!responses[0].ok) throw new Error('知识 API 错误');
    let kd = await responses[0].json();
    let skills = responses[1].ok ? await responses[1].json() : [];

    let h = _viewHeader('浏览知识', '全局萃取的知识条目与技能知识库');
    h += _quickNav('knowledge');
    h += '<div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">';
    h += '<button class="nav-sm" style="border-color:var(--accent);color:var(--accent)" onclick="showPrecipitateView()">+ 触发沉淀</button>';
    h += '<button class="nav-sm" style="border-color:var(--warn);color:var(--warn)" onclick="showReviewView()">待复核</button>';
    h += '</div>';

    if (!kd.items || !kd.items.length) {
      h += '<div class="empty-state"><div class="icon">📚</div><div class="title">暂无知识条目</div><div class="hint">在对话中发送 URL 或上传文件，知识会自动萃取</div></div>';
    } else {
      let verified = kd.items.filter(function(i) { return (i.confidence || 0) >= 0.7; }).length;
      let review = kd.items.filter(function(i) { return i.needs_review; }).length;

      h += '<div class="dash-grid" style="margin-bottom:12px">';
      h += '<div class="dash-card" style="cursor:pointer" onclick="filterKBStat(\'all\',this)"><div class="value" style="color:var(--text)">' + kd.total + '</div><div class="label">总计</div></div>';
      h += '<div class="dash-card" style="cursor:pointer" onclick="filterKBStat(\'verified\',this)"><div class="value" style="color:var(--accent)">' + verified + '</div><div class="label">已验证</div></div>';
      h += '<div class="dash-card" style="cursor:pointer" onclick="filterKBStat(\'review\',this)"><div class="value" style="color:' + (review > 0 ? 'var(--err)' : 'var(--accent)') + '">' + review + '</div><div class="label">待复核</div></div>';
      h += '</div>';

      let cats = [...new Set(kd.items.map(function(i) { return i.category; }))];
      h += '<div style="display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap">';
      h += '<span class="kb-filter active-kb-filter" data-cat="all" onclick="filterKB(this)" style="padding:4px 12px;font-size:11px;border-radius:14px;cursor:pointer;background:var(--accent);color:#fff;font-weight:600">全部 (' + kd.total + ')</span>';
      cats.forEach(function(c) {
        let count = kd.items.filter(function(i) { return i.category === c; }).length;
        h += '<span class="kb-filter" data-cat="' + escHtml(c) + '" onclick="filterKB(this)" style="padding:4px 12px;font-size:11px;border-radius:14px;cursor:pointer;background:var(--surface2);color:var(--text2);border:1px solid var(--border)">' + escHtml(c) + ' (' + count + ')</span>';
      });
      h += '</div>';

      kd.items.forEach(function(i) {
        let conf = i.confidence != null ? i.confidence : 0.5;
        let created = i.created_at ? new Date(i.created_at * 1000).toLocaleString() : '—';
        let confColor = conf >= 0.7 ? 'var(--accent)' : conf >= 0.4 ? 'var(--warn)' : 'var(--err)';
        let confPct = Math.round(conf * 100);
        h += '<div class="kb-item" data-cat="' + escHtml(i.category || '') + '" data-conf="' + conf + '" data-review="' + (i.needs_review ? '1' : '0') + '" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-bottom:8px">';
        h += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;flex-wrap:wrap">';
        h += '<span style="font-size:10px;padding:2px 8px;border-radius:10px;background:var(--surface);color:var(--text3);border:1px solid var(--border)">' + escHtml(i.category || 'unknown') + '</span>';
        h += '<span style="font-size:12px;font-weight:700;color:' + confColor + '">' + confPct + '%</span>';
        if (i.needs_review) h += '<span style="font-size:10px;padding:2px 6px;border-radius:6px;background:rgba(239,68,68,.12);color:var(--err)">⚠ 待复核</span>';
        h += '<span style="flex:1"></span><span style="font-size:10px;color:var(--text3)">' + created + '</span></div>';
        h += '<div style="font-size:13px;color:var(--text);line-height:1.7">' + escHtml(i.content || '') + '</div>';
        if (i.source_url) h += '<div style="font-size:10px;color:var(--text3);margin-top:6px">📎 ' + escHtml(i.source_url).slice(0, 100) + '</div>';
        h += '</div>';
      });
    }

    let userSkills = skills.filter(function(s) { return (s.kb_items || 0) > 0; });
    if (userSkills.length > 0) {
      h += '<div style="font-size:14px;font-weight:700;color:var(--text);margin:24px 0 12px">📁 技能知识库 (' + userSkills.length + ')</div>';
      userSkills.forEach(function(s) {
        h += '<div class="skill-card" style="margin-bottom:4px;cursor:pointer" onclick="showDetail(' + JSON.stringify(s.name) + ');setTimeout(function(){switchTab(\'kb\')},80)">';
        h += '<div class="name">' + escHtml(s.name) + '</div>';
        h += '<div class="meta">' + (s.kb_items || 0) + ' 条</div></div>';
      });
    }

    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('浏览知识') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}
function showLineageView() {

  switchMainView('lineage-view');
  document.getElementById('bar').style.display = 'none';

  let el = document.getElementById('lineage-content');
  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载溯源…</div>';

  api('/api/knowledge/lineage').then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(d) {
    let sessions = d.sessions || [];
    let h = _viewHeader('知识溯源', '每条知识从来源到影响的全程追踪');
    h += _quickNav('lineage');

    if (!sessions.length) {
      h += '<div class="empty-state"><div class="icon">🔗</div><div class="title">暂无溯源会话</div><div class="hint">通过 URL 或文件摄入内容时，溯源会自动记录</div></div>';
    } else {
      h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px">' + sessions.length + ' 个溯源会话</div>';
      sessions.forEach(function(s) {
        let dt = s.created_at ? new Date(s.created_at * 1000).toLocaleString() : '—';
        h += '<div class="skill-card" style="margin-bottom:6px;cursor:pointer;border-left:3px solid var(--warn)" onclick="loadLineageGraph(' + JSON.stringify(s.session_id) + ')">';
        h += '<div class="name">' + escHtml(s.source_title || s.source_url || s.session_id) + '</div>';
        h += '<div class="meta">' + (s.total_items || 0) + ' 条 · ' + dt + '</div></div>';
      });
    }

    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('知识溯源') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}

function loadLineageGraph(sessionId) {

  let el = document.getElementById('lineage-content');

  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载中…</div>';

  api('/api/knowledge/lineage/' + encodeURIComponent(sessionId) + '/graph')

    .then(function(r) {

      if (!r.ok) throw new Error('HTTP ' + r.status);

      return r.json();

    })

    .then(function(d) {

      var h = '<button class="nav-sm" onclick="showLineageView()">← 返回</button>';

      h += '<div style="font-size:16px;font-weight:700;color:var(--text);margin:12px 0">知识溯源图</div>';

      h += '<div style="font-size:12px;color:var(--text3);margin-bottom:12px">会话: ' + escHtml(sessionId) + '</div>';



      var cy = d.cytoscape || {};

      var nodes = cy.nodes || [];

      var edges = cy.edges || [];



      h += '<div class="dash-grid" style="margin-bottom:16px">';

      h += '<div class="dash-card"><div class="value" style="color:var(--accent)">' + nodes.length + '</div><div class="label">节点</div></div>';

      h += '<div class="dash-card"><div class="value" style="color:var(--info)">' + edges.length + '</div><div class="label">边</div></div>';

      h += '<div class="dash-card"><div class="value" style="color:var(--text2)">' + (d.mermaid ? d.mermaid.length : 0) + '</div><div class="label">Mermaid 字符</div></div>';

      h += '</div>';



      // Show Mermaid diagram with zoom + fullscreen controls
      if (d.mermaid) {
        var mermaidId = 'mermaid-' + Date.now();
        var wrapId = 'mermaid-wrap-' + mermaidId;
        var cleanCode = d.mermaid.replace('```mermaid','').replace('```','').trim();
        h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
        h += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">';
        h += '<div style="font-size:13px;font-weight:600;color:var(--text2);flex:1">数据溯源流</div>';
        h += '<button class="nav-sm" data-act="zin" data-w="'+wrapId+'" onclick="handleLineageZoom(this)" title="放大" style="font-size:14px">+</button>';
        h += '<button class="nav-sm" data-act="zout" data-w="'+wrapId+'" onclick="handleLineageZoom(this)" title="缩小" style="font-size:14px">-</button>';
        h += '<button class="nav-sm" data-act="zrst" data-w="'+wrapId+'" onclick="handleLineageZoom(this)" title="重置" style="font-size:11px">1:1</button>';
        h += '<button class="nav-sm" data-act="full" data-w="'+wrapId+'" onclick="handleLineageZoom(this)" title="全屏" style="font-size:14px">&#x26F6;</button>';
        h += '</div>';
        h += '<div id="'+wrapId+'" style="overflow:auto;max-height:500px;transition:all .3s;background:var(--surface);border-radius:6px;padding:12px">';
        h += '<div class="mermaid" id="'+mermaidId+'" style="font-size:12px;transform-origin:top left">'+cleanCode+'</div>';
        h += '</div></div>';
        setTimeout(function() {
          try { mermaid.run({ querySelector: '#'+mermaidId }); } catch(e) {}
        }, 200);
      }




      // Show node cards

      if (nodes.length > 0) {

        h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">知识条目</div>';

        nodes.forEach(function(n) {

          if (n.data.type === 'source') {

            h += '<div class="skill-card" style="margin-bottom:6px;border-left:3px solid var(--warn)">';

            h += '<div class="name">来源: ' + escHtml((n.data.label||'')) + '</div>';

            h += '</div>';

          } else if (n.data.type === 'skill') {

            h += '<div class="skill-card" style="margin-bottom:6px;border-left:3px solid var(--accent)">';

            h += '<div class="name">技能: ' + escHtml((n.data.label||'')) + '</div>';

            h += '</div>';

          } else {

            var color = n.data.color || 'var(--text3)';

            h += '<div class="skill-card" style="margin-bottom:6px;border-left:3px solid ' + color + '">';

            h += '<div class="name">' + escHtml((n.data.label||'')) + '</div>';

            h += '<div style="font-size:11px;color:var(--text2);line-height:1.6;margin-top:4px">' + escHtml((n.data.label||'')) + '</div>';

            h += '<div class="meta">类型: ' + n.data.type + ' | 置信度: ' + Math.round((n.data.confidence||0)*100) + '% | 层级: ' + (n.data.level||'experience') + '</div>';

            h += '</div>';

          }

        });

      }



      el.innerHTML = h || '<div class="empty-state"><div class="icon">🔗</div><div class="title">此会话暂无数据</div></div>';

    })

    .catch(function(e) {

      el.innerHTML = '<div style="color:var(--err);padding:20px">溯源图加载失败:<br>' + e.message + '</div>';

      console.error('Lineage graph error:', e);

    });

}

function filterKB(el) {

  let cat = el.dataset.cat;

  document.querySelectorAll('.kb-filter').forEach(function(f) {
    f.style.background = 'var(--surface2)'; f.style.color = 'var(--text2)'; f.style.border = '1px solid var(--border)';
    f.classList.remove('active-kb-filter');
  });

  el.style.background = 'var(--accent)'; el.style.color = '#fff'; el.style.border = '1px solid var(--accent)';
  el.classList.add('active-kb-filter');

  document.querySelectorAll('.kb-item').forEach(function(item) {
    var stat = item.getAttribute('data-stat-filter') || 'all';
    var catOk = cat === 'all' || item.dataset.cat === cat;
    var statOk = stat === 'all' || (stat === 'verified' && parseFloat(item.dataset.conf || 0) >= 0.7) || (stat === 'review' && item.dataset.review === '1');
    item.style.display = catOk && statOk ? '' : 'none';
  });
}

function filterKBStat(type, cardEl) {
  document.querySelectorAll('.kb-item').forEach(function(item) {
    item.setAttribute('data-stat-filter', type);
  });
  document.querySelectorAll('.dash-card').forEach(function(c) { c.style.outline = ''; });
  if (cardEl) cardEl.style.outline = '2px solid var(--accent)';
  var active = document.querySelector('.kb-filter.active-kb-filter') || document.querySelector('.kb-filter[data-cat="all"]');
  if (active) filterKB(active);
  else document.querySelectorAll('.kb-item').forEach(function(item) {
    var statOk = type === 'all' || (type === 'verified' && parseFloat(item.dataset.conf || 0) >= 0.7) || (type === 'review' && item.dataset.review === '1');
    item.style.display = statOk ? '' : 'none';
  });
}

function toggleKPIDetail(id) {

  let el = document.getElementById(id);

  if (!el) return;

  if (el.style.display === 'block') {
    el.style.display = 'none';
  } else {
    document.querySelectorAll('.kpi-panel').forEach(function(d) { d.style.display = 'none'; });
    el.style.display = 'block';
  }
}
function _kpiCard(label, value, color, hint) {

  return '<div class="dash-card" style="cursor:pointer"><div class="value" style="color:' + color + '">' + value + '</div><div class="label">' + label + '</div><div style="font-size:10px;color:var(--text3);margin-top:2px">' + hint + '</div></div>';

}

function _kpiToggle(id, label, value, color, hint) {

  return '<div class="dash-card" style="cursor:pointer" onclick="toggleKPIDetail(\'' + id + '\')"><div class="value" style="color:' + color + '">' + value + '</div><div class="label">' + label + '</div><div style="font-size:10px;color:var(--text3);margin-top:2px">' + hint + ' ▾</div></div>';

}

function handleLineageZoom(btn) {
  var act = btn.getAttribute("data-act");
  var wrapId = btn.getAttribute("data-w");
  var el = document.getElementById(wrapId);
  if (!el) return;
  if (act === "full") {
    if (el.classList.contains("fullscreen")) {
      el.classList.remove("fullscreen");
      el.style.cssText = "overflow:auto;max-height:500px;transition:all .3s;background:var(--surface);border-radius:6px;padding:12px";
    } else {
      el.classList.add("fullscreen");
      el.style.cssText = "position:fixed;inset:0;z-index:200;background:var(--bg);overflow:auto;padding:24px";
    }
    return;
  }
  var cur = parseFloat(el.getAttribute("data-zoom") || "1");
  var z = act === "zin" ? cur + 0.2 : act === "zout" ? cur - 0.2 : 1;
  z = Math.max(0.2, Math.min(3, z));
  el.setAttribute("data-zoom", z);
  el.style.maxHeight = z === 1 ? "500px" : (500 * z) + "px";
  var inner = el.querySelector(".mermaid");
  if (inner) { inner.style.transform = "scale(" + z + ")"; inner.style.transformOrigin = "top left"; }
}

var _CYCLE_STATUS_LABELS = {
  pending: '排队中',
  running: '沉淀中',
  completed: '已完成',
  failed: '失败',
  not_found: '未找到'
};

function _cycleStatusColor(status) {
  if (status === 'completed') return 'var(--accent)';
  if (status === 'failed') return 'var(--err)';
  if (status === 'running') return 'var(--warn)';
  return 'var(--info)';
}

function _renderCycleProgress(task) {
  var status = task.status || 'pending';
  var label = _CYCLE_STATUS_LABELS[status] || status;
  var color = _cycleStatusColor(status);
  var pct = status === 'completed' ? 100 : status === 'running' ? 55 : status === 'failed' ? 100 : 12;
  var barColor = status === 'failed' ? 'var(--err)' : 'var(--accent)';
  var h = '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
  h += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">';
  h += '<div style="font-size:14px;font-weight:700;color:var(--text)">任务 ' + escHtml(task.task_id || '') + '</div>';
  h += '<span style="font-size:12px;font-weight:700;color:' + color + '">' + escHtml(label) + '</span></div>';
  h += '<div style="height:8px;background:var(--surface);border-radius:999px;overflow:hidden;margin-bottom:10px">';
  h += '<div style="height:100%;width:' + pct + '%;background:' + barColor + ';transition:width .4s"></div></div>';
  if (task.source_url) h += '<div style="font-size:11px;color:var(--text3);margin-bottom:6px">来源：' + escHtml(task.source_url) + '</div>';
  if (status === 'completed' && task.result) {
    var r = task.result;
    if (r.skipped) {
      h += '<div style="font-size:12px;color:var(--text2);line-height:1.7">⏭ 内容未变化，已跳过重复沉淀（dedup）</div>';
      h += '<div style="margin-top:10px"><button class="nav-sm" onclick="showKnowledgeView()">浏览知识库</button></div>';
    } else {
    var digest = r.digest || {};
    h += '<div style="font-size:12px;color:var(--text2);line-height:1.7">';
    h += '✓ 会话 <code style="font-size:11px">' + escHtml(r.session_id || task.session_id || '') + '</code><br>';
    h += '术语 ' + (digest.glossary_terms || 0) + ' · 模式 ' + (digest.patterns || 0) + ' · 章节 ' + (digest.sections || 0);
    if (r.lineage && r.lineage.lineage_applied) {
      h += '<br>血缘 ' + (r.lineage.total_items || 0) + ' 条 · 边 ' + (r.lineage.edges_created || 0);
    }
    h += '<br>耗时 ' + (r.elapsed_s || task.elapsed_s || 0) + 's';
    h += '</div>';
    h += '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">';
    if (r.session_id) h += '<button class="nav-sm" onclick="loadLineageGraph(' + JSON.stringify(r.session_id) + ')">查看溯源</button>';
    h += '<button class="nav-sm" onclick="showKnowledgeView()">浏览知识库</button>';
    h += '<button class="nav-sm" onclick="showReviewView()">待复核</button>';
    h += '</div>';
    }
  }
  if (status === 'failed' && task.error) {
    h += '<div style="font-size:12px;color:var(--err);margin-top:8px">失败原因：' + escHtml(task.error) + '</div>';
  }
  h += '</div>';
  return h;
}

function _stopCyclePoll() {
  if (window._cyclePollTimer) {
    clearInterval(window._cyclePollTimer);
    window._cyclePollTimer = null;
  }
}

function pollKnowledgeCycle(taskId, onUpdate, onDone) {
  _stopCyclePoll();
  function tick() {
    api('/api/knowledge/cycle/' + encodeURIComponent(taskId)).then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function(task) {
      if (onUpdate) onUpdate(task);
      if (task.status === 'completed' || task.status === 'failed' || task.status === 'not_found') {
        _stopCyclePoll();
        if (onDone) onDone(task);
      }
    }).catch(function(e) {
      _stopCyclePoll();
      if (onDone) onDone({ task_id: taskId, status: 'failed', error: e.message });
    });
  }
  tick();
  window._cyclePollTimer = setInterval(tick, 1200);
}

function submitKnowledgeCycle() {
  var urlEl = document.getElementById('precipitate-url');
  var contentEl = document.getElementById('precipitate-content-input');
  var progressEl = document.getElementById('precipitate-progress');
  var sourceUrl = (urlEl && urlEl.value || '').trim() || 'manual://precipitate';
  var content = (contentEl && contentEl.value || '').trim();
  if (content.length < 200) {
    toast('内容至少 200 字才能触发全周期沉淀', 'warn');
    return;
  }
  if (progressEl) progressEl.innerHTML = '<div style="color:var(--text3);padding:12px">提交任务中…</div>';
  api('/api/knowledge/cycle', {
    method: 'POST',
    body: JSON.stringify({ content: content, source_url: sourceUrl })
  }).then(function(r) {
    if (!r.ok) return r.json().then(function(b) { throw new Error(b.error || b.detail || ('HTTP ' + r.status)); });
    return r.json();
  }).then(function(task) {
    if (!task.task_id) throw new Error(task.error || '未返回 task_id');
    toast('沉淀任务已提交', 'success');
    if (progressEl) progressEl.innerHTML = _renderCycleProgress(task);
    pollKnowledgeCycle(task.task_id, function(updated) {
      if (progressEl) progressEl.innerHTML = _renderCycleProgress(updated);
    }, function(finalTask) {
      if (finalTask.status === 'completed') {
        if (finalTask.result && finalTask.result.skipped) toast('内容未变化，已跳过沉淀', 'info');
        else toast('知识沉淀完成', 'success');
      } else if (finalTask.status === 'failed') toast('沉淀失败：' + (finalTask.error || '未知错误'), 'error');
      loadRecentCycleTasks();
    });
  }).catch(function(e) {
    if (progressEl) progressEl.innerHTML = '<div style="color:var(--err);padding:12px">提交失败：' + escHtml(e.message) + '</div>';
    toast('提交失败：' + e.message, 'error');
  });
}

function loadRecentCycleTasks() {
  var el = document.getElementById('precipitate-recent');
  if (!el) return;
  api('/api/knowledge/cycle/recent?limit=8').then(function(r) { return r.ok ? r.json() : { tasks: [] }; }).then(function(d) {
    var tasks = d.tasks || [];
    if (!tasks.length) {
      el.innerHTML = '<div style="font-size:12px;color:var(--text3)">暂无历史任务</div>';
      return;
    }
    var h = '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">最近任务</div>';
    tasks.forEach(function(t) {
      var color = _cycleStatusColor(t.status);
      h += '<div class="skill-card" style="margin-bottom:6px;cursor:pointer" onclick="resumeCycleTask(' + JSON.stringify(t.task_id) + ')">';
      h += '<div class="name">' + escHtml(t.task_id) + ' · <span style="color:' + color + '">' + escHtml(_CYCLE_STATUS_LABELS[t.status] || t.status) + '</span></div>';
      h += '<div class="meta">' + escHtml((t.source_url || '').slice(0, 80)) + '</div></div>';
    });
    el.innerHTML = h;
  });
}

function resumeCycleTask(taskId) {
  var progressEl = document.getElementById('precipitate-progress');
  if (!progressEl) return;
  api('/api/knowledge/cycle/' + encodeURIComponent(taskId)).then(function(r) { return r.json(); }).then(function(task) {
    progressEl.innerHTML = _renderCycleProgress(task);
    if (task.status === 'pending' || task.status === 'running') {
      pollKnowledgeCycle(taskId, function(updated) {
        progressEl.innerHTML = _renderCycleProgress(updated);
      }, function(finalTask) {
        if (finalTask.status === 'completed') {
          if (finalTask.result && finalTask.result.skipped) toast('内容未变化，已跳过沉淀', 'info');
          else toast('知识沉淀完成', 'success');
        }
        loadRecentCycleTasks();
      });
    }
  });
}

function showPrecipitateView() {
  switchMainView('precipitate-view');
  document.getElementById('bar').style.display = 'none';
  var el = document.getElementById('precipitate-content');
  var h = _viewHeader('知识沉淀', '触发全周期内化：消化 → 血缘 → 图谱 → 智慧');
  h += _quickNav('precipitate');
  h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
  h += '<label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">来源 URL（可选）</label>';
  h += '<input id="precipitate-url" placeholder="https://example.com/article 或 file://doc.pdf" style="width:100%;box-sizing:border-box;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:10px 12px;color:var(--text);font-size:13px;margin-bottom:12px;outline:none">';
  h += '<label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">正文内容（≥200 字）</label>';
  h += '<textarea id="precipitate-content-input" rows="10" placeholder="粘贴文章、文档或笔记全文…" style="width:100%;box-sizing:border-box;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:10px 12px;color:var(--text);font-size:13px;outline:none;resize:vertical;font-family:inherit"></textarea>';
  h += '<div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">';
  h += '<button class="nav-sm" style="border-color:var(--accent);color:var(--accent)" onclick="submitKnowledgeCycle()">开始沉淀</button>';
  h += '<button class="nav-sm" onclick="document.getElementById(\'file-input\').click()">上传文件</button>';
  h += '</div></div>';
  h += '<div id="precipitate-progress"></div>';
  h += '<div id="precipitate-queue" style="margin-top:16px"></div>';
  h += '<div id="precipitate-recent" style="margin-top:16px"></div>';
  el.innerHTML = h;
  loadRecentCycleTasks();
  loadIngestionQueuePanel();
}

function loadIngestionQueuePanel() {
  var el = document.getElementById('precipitate-queue');
  if (!el) return;
  api('/api/knowledge/queue?limit=6').then(function(r) { return r.ok ? r.json() : { stats: {}, tasks: [] }; }).then(function(d) {
    var stats = d.stats || {};
    var tasks = d.tasks || [];
    var h = '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">摄入队列 · 待处理 ' + (stats.pending || 0) + ' · 已完成 ' + (stats.done || 0) + '</div>';
    if (!tasks.length) {
      h += '<div style="font-size:12px;color:var(--text3)">暂无队列任务（文件 inbox / 公众号 / URL 会自动入队）</div>';
    } else {
      tasks.forEach(function(t) {
        var st = t.status || '';
        var color = st === 'done' ? 'var(--accent)' : st === 'failed' ? 'var(--err)' : 'var(--warn)';
        h += '<div style="font-size:11px;padding:6px 0;border-bottom:1px solid var(--border)">';
        h += '<span style="color:' + color + ';font-weight:600">' + escHtml(st) + '</span> · ';
        h += escHtml(t.source_type || '') + ' · ' + escHtml((t.source_path || '').slice(0, 72));
        if (t.result) h += '<div style="color:var(--text3);margin-top:2px">' + escHtml(String(t.result).slice(0, 80)) + '</div>';
        h += '</div>';
      });
    }
    el.innerHTML = h;
  }).catch(function() {
    el.innerHTML = '<div style="font-size:12px;color:var(--text3)">队列状态加载失败</div>';
  });
}

function showReviewView() {
  switchMainView('review-view');
  document.getElementById('bar').style.display = 'none';
  var el = document.getElementById('review-content');
  el.innerHTML = '<div style="color:var(--text3);padding:40px;text-align:center">加载待复核队列…</div>';

  Promise.all([
    api('/api/knowledge/review'),
    api('/api/knowledge/?show=all')
  ]).then(async function(responses) {
    var review = responses[0].ok ? await responses[0].json() : { items: [], count: 0 };
    var all = responses[1].ok ? await responses[1].json() : { items: [] };
    var flagged = (all.items || []).filter(function(i) { return i.needs_review; });
    var merged = review.items || [];
    var seen = {};
    merged.forEach(function(i) { seen[i.id] = true; });
    flagged.forEach(function(i) {
      if (!seen[i.id]) merged.push(Object.assign({}, i, { review_kind: 'extractor' }));
    });

    var h = _viewHeader('待复核', merged.length + ' 条需人工确认');
    h += _quickNav('review');
    h += '<div style="font-size:12px;color:var(--text3);margin-bottom:12px">低置信度萃取、经验性声明与矛盾知识会进入此队列。</div>';

    if (!merged.length) {
      h += '<div class="empty-state"><div class="icon">✅</div><div class="title">暂无待复核项</div><div class="hint">知识沉淀后会自动标记需复核条目</div></div>';
    } else {
      merged.forEach(function(i) {
        var conf = i.confidence != null ? Math.round(i.confidence * 100) : 0;
        var kind = i.review_kind === 'experience' ? '经验性' : '萃取';
        h += '<div class="kb-item" style="background:var(--surface2);border:1px solid var(--border);border-left:3px solid var(--err);border-radius:8px;padding:12px 16px;margin-bottom:8px">';
        h += '<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap">';
        h += '<span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(239,68,68,.12);color:var(--err)">⚠ 待复核 · ' + escHtml(kind) + '</span>';
        h += '<span style="font-size:12px;font-weight:700;color:var(--warn)">' + conf + '%</span></div>';
        h += '<div style="font-size:13px;color:var(--text);line-height:1.7">' + escHtml(i.content || '') + '</div>';
        if (i.review_reason) h += '<div style="font-size:11px;color:var(--text3);margin-top:6px">原因：' + escHtml(i.review_reason) + '</div>';
        if (i.source) h += '<div style="font-size:10px;color:var(--text3);margin-top:6px">📎 ' + escHtml(String(i.source).slice(0, 120)) + '</div>';
        h += '</div>';
      });
    }
    el.innerHTML = h;
  }).catch(function(e) {
    el.innerHTML = _viewHeader('待复核') + '<div style="color:var(--err);padding:12px">加载失败：' + escHtml(e.message) + '</div>';
  });
}

