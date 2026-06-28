/* skills.js — Skill Detail View (Alpine.js)
 * Route B.2: Alpine-reactive detail tabs replacing innerHTML loading.
 */

// ── Alpine component ──────────────────────────────────

function skillView() {
  return {
    skillName: '',
    tab: 'overview',
    loading: false,
    tabContent: '',
    metaVisible: false,
    moreOpen: false,

    get moreTabActive() {
      return ['kb', 'verify', 'epistemic', 'dna', 'official', 'meta', 'evo', 'decisions'].indexOf(this.tab) >= 0;
    },

    async showDetail(name, initialTab) {
      if (!name) { this.skillName = ''; return; }
      _currentSkill = name;
      this.skillName = name;
      this.tab = initialTab || 'overview';
      this.moreOpen = false;
      this.loading = true;
      _pendingMermaid = [];
      Alpine.store('nav').currentSkill = name;
      Alpine.store('nav').goTo('detail-view');

      try {
        var r = await api('/api/skills/' + encodeURIComponent(name) + '/metaskill');
        if (r.ok) { var d = await r.json(); this.metaVisible = !!(d && d.steps); }
      } catch (e) { this.metaVisible = false; }

      await this.loadTabContent(this.tab);
    },

    switchTab(t) {
      this.tab = t;
      this.moreOpen = false;
      Alpine.store('nav').currentTab = t;
      this.loadTabContent(t);
    },

    async loadTabContent(t) {
      if (!this.skillName) return;
      _currentSkill = this.skillName;
      _pendingMermaid = [];
      this.loading = true;
      try {
        var name = this.skillName;
        if (t === 'overview') this.tabContent = await loadOverviewContent(name);
        else if (t === 'doc') this.tabContent = await loadDocContent(name);
        else if (t === 'quality') this.tabContent = await loadQualityContent(name);
        else if (t === 'evolution') this.tabContent = await loadEvolutionContent(name, this.metaVisible);
        else if (t === 'kb') this.tabContent = await loadKBContent(name);
        else if (t === 'verify') this.tabContent = await loadVerifyContent(name);
        else if (t === 'epistemic') this.tabContent = await loadEpistemicContent(name);
        else if (t === 'dna') this.tabContent = await loadDnaContent(name);
        else if (t === 'official') this.tabContent = await loadOfficialContent(name);
        else if (t === 'meta') this.tabContent = await loadMetaContent(name);
        else if (t === 'evo') this.tabContent = await loadEvoContent(name);
        else if (t === 'decisions') this.tabContent = await loadDecisionsContent(name);
      } catch (e) {
        this.tabContent = typeof renderErrorState === 'function'
          ? renderErrorState(e.message, function() { this.loadTabContent(this.tab); }.bind(this))
          : '<div class="u-err">加载失败: ' + escHtml(e.message) + '</div>';
      }
      this.loading = false;
      requestAnimationFrame(function() {
        requestAnimationFrame(function() { flushDetailMermaid(); });
      });
    },

    optimizeCurrent() { if (this.skillName) optimizeSkill(this.skillName); },
    publishCurrent() { if (this.skillName) showPublishForm(this.skillName); },
  };
}

// ── Staging DOM (legacy loaders write here; Alpine renders via x-html) ──

var _pendingMermaid = [];

function _detailStage() {
  return document.getElementById('d-content-staging');
}

function _getDContent() {
  var el = _detailStage();
  return el ? el.innerHTML : '';
}

function _queueMermaid(id, src) {
  if (id && src) _pendingMermaid.push({ id: id, src: src });
}

function flushDetailMermaid() {
  var q = _pendingMermaid.slice();
  _pendingMermaid = [];
  q.forEach(function(p) {
    if (typeof renderMermaidInto === 'function') renderMermaidInto(p.id, p.src);
  });
}

function skillDelegate(method) {
  var el = document.querySelector('[x-data="skillView()"]');
  if (el && el.__x && el.__x.$data && typeof el.__x.$data[method] === 'function') {
    el.__x.$data[method].apply(el.__x.$data, Array.prototype.slice.call(arguments, 1));
    return true;
  }
  return false;
}

// ── Content loaders (return HTML/text for Alpine) ──

async function loadOverviewContent(name) { _currentSkill = name; await loadOverview(); return _getDContent(); }
async function loadDocContent(name) {
  _currentSkill = name;
  var r = await api('/api/skills/' + encodeURIComponent(name));
  var d = await r.json();
  return d.content || 'No content';
}
async function loadKBContent(name) { _currentSkill = name; await loadKB(); return _getDContent(); }
async function loadVerifyContent(name) { _currentSkill = name; await loadVerify(); return _getDContent(); }
async function loadEpistemicContent(name) { _currentSkill = name; await loadEpistemic(); return _getDContent(); }
async function loadDnaContent(name) { _currentSkill = name; await loadDnaLineage(); return _getDContent(); }
async function loadOfficialContent(name) { _currentSkill = name; await loadOfficialBench(); return _getDContent(); }
async function loadMetaContent(name) { _currentSkill = name; await loadMeta(); return _getDContent(); }
async function loadEvoContent(name) { _currentSkill = name; await loadEvo(); return _getDContent(); }
async function loadDecisionsContent(name) { _currentSkill = name; await loadDecisions(); return _getDContent(); }

var _MORE_TABS = ['kb', 'verify', 'epistemic', 'dna', 'official', 'meta', 'evo', 'decisions'];

async function _loadCompositeSections(name, sections) {
  _currentSkill = name;
  var parts = [];
  for (var i = 0; i < sections.length; i++) {
    await sections[i].fn();
    parts.push(
      '<section class="detail-section">' +
      '<h3 class="detail-section-title">' + escHtml(sections[i].title) + '</h3>' +
      _getDContent() +
      '</section>'
    );
  }
  return '<div class="detail-composite">' + parts.join('') + '</div>';
}

async function loadQualityContent(name) {
  return _loadCompositeSections(name, [
    { title: 'MoE 验证', fn: loadVerify },
    { title: '认识论状态', fn: loadEpistemic },
    { title: 'SkillsBench 评测', fn: loadOfficialBench },
    { title: 'DNA 血缘', fn: loadDnaLineage }
  ]);
}

async function loadEvolutionContent(name, includeMeta) {
  var sections = [{ title: '进化轨迹', fn: loadEvo }, { title: '决策溯源', fn: loadDecisions }];
  if (includeMeta) sections.unshift({ title: 'MetaSkill 流水线', fn: loadMeta });
  return _loadCompositeSections(name, sections);
}

// ── Legacy wrappers (delegate to Alpine skillView) ───

function showDetail(name, tab) {
  if (skillDelegate('showDetail', name, tab)) return;
  if (!name) { showChat(); return; }
  if (window.__alpineReady && Alpine.store('nav')) {
    Alpine.store('nav').goTo('detail-view');
  } else {
    switchMainView('detail-view');
    document.getElementById('bar').style.display = 'none';
  }
  setTimeout(function() { skillDelegate('showDetail', name, tab); }, 150);
}

function switchTab(t) {
  _currentTab = t;
  if (skillDelegate('switchTab', t)) return;
  setTimeout(function() { skillDelegate('switchTab', t); }, 100);
}

function dedupReasonLabel(reason) {
  if (reason === 'name') return '名称相似';
  if (reason === 'content') return '内容重叠';
  return reason || '';
}

function _detailKpi(label, val, tone, hint) {
  tone = tone || 'muted';
  return '<div class="detail-kpi detail-kpi-' + tone + '">' +
    '<div class="detail-kpi-value">' + escHtml(String(val)) + '</div>' +
    '<div class="detail-kpi-label">' + escHtml(label) + '</div>' +
    (hint ? '<div class="detail-kpi-hint">' + escHtml(hint) + '</div>' : '') +
    '</div>';
}

function _detailDnaTone(passed) {
  var p = passed || 0;
  return p >= 5 ? 'good' : p >= 3 ? 'mid' : 'low';
}

function _detailAvgTone(score) {
  return score >= 4 ? 'good' : score >= 2 ? 'mid' : 'low';
}

function _detailCard(title, inner) {
  return '<div class="content-card detail-panel">' +
    '<div class="content-card-header">' + escHtml(title) + '</div>' +
    inner + '</div>';
}

function _detailChip(text) {
  return '<span class="detail-chip">' + escHtml(text) + '</span>';
}

function _detailCheckRow(passed, principle, detail) {
  return '<div class="detail-check-row">' +
    '<span class="detail-check-badge ' + (passed ? 'ok' : 'fail') + '">' + (passed ? '通过' : '未过') + '</span>' +
    '<span class="detail-check-principle">原则 ' + escHtml(String(principle)) + '</span>' +
    '<span class="detail-check-detail ' + (passed ? 'ok' : 'fail') + '">' + escHtml(detail || '') + '</span>' +
    '</div>';
}

function _detailWarnBanner(title, rowsHtml) {
  return '<div class="detail-warn-banner">' +
    '<div class="detail-warn-title">' + escHtml(title) + '</div>' +
    rowsHtml + '</div>';
}

function _detailActionRow(buttonsHtml) {
  return '<div class="detail-action-row">' + buttonsHtml + '</div>';
}

/** @deprecated use _detailKpi */
function _kpi(label, val, color, hint) {
  var tone = 'muted';
  if (color && color.indexOf('accent') >= 0) tone = 'good';
  else if (color && color.indexOf('warn') >= 0) tone = 'mid';
  else if (color && color.indexOf('err') >= 0) tone = 'low';
  return _detailKpi(label, val, tone, hint);
}

async function renderSimilarSkillsBanner(skillName) {
  try {
    let simR = await api('/api/skills/' + encodeURIComponent(skillName) + '/similar');
    if (!simR.ok) return '';
    let simD = await simR.json();
    if (!simD.similar || !simD.similar.length) return '';
    var rows = '';
    simD.similar.forEach(function (s) {
      rows += '<div class="detail-warn-row" onclick="showDetail(' + JSON.stringify(s.name) + ')">' +
        escHtml(s.name) + ' · 相似度 ' + Math.round((s.score || 0) * 100) + '%（' + dedupReasonLabel(s.reason) + '）</div>';
    });
    return _detailWarnBanner('相似技能（去重提示）', rows);
  } catch (e) {
    return '';
  }
}

function _detailMuted(text) {
  return '<div class="detail-muted">' + escHtml(text) + '</div>';
}

function _detailPctTone(pct) {
  if (pct == null || pct === '') return 'muted';
  return String(pct).indexOf('-') === 0 ? 'low' : 'good';
}

function _detailIntro(html) {
  return '<div class="detail-intro">' + html + '</div>';
}

function _detailInfoBox(inner) {
  return '<div class="detail-info-box">' + inner + '</div>';
}

function _detailDecisionCard(outcome, inner) {
  var cls = outcome === 'accepted' ? 'accepted' : outcome === 'rejected' ? 'rejected' : 'partial';
  return '<div class="detail-decision-card ' + cls + '">' + inner + '</div>';
}

function _detailToneClass(tone) {
  if (tone === 'good') return 'tone-good';
  if (tone === 'low') return 'tone-low';
  if (tone === 'mid') return 'tone-mid';
  return 'tone-muted';
}

function _detailDeltaHtml(pct) {
  var tone = _detailPctTone(pct);
  return '<b class="detail-delta ' + _detailToneClass(tone) + '">' + escHtml(String(pct != null ? pct : '')) + '</b>';
}

function _detailQuick8PerTaskTable(rows) {
  var h = '<table class="detail-data-table"><thead><tr><th>题目</th><th class="center">有</th><th class="center">无</th><th class="center">注入</th></tr></thead><tbody>';
  rows.forEach(function (pt) {
    var delta = (pt.with_score || 0) - (pt.without_score || 0);
    var tone = delta > 0 ? 'good' : delta < 0 ? 'low' : 'muted';
    h += '<tr><td><code>' + escHtml(pt.task_id) + '</code></td>';
    h += '<td class="center">' + pt.with_score + '</td><td class="center">' + pt.without_score + '</td>';
    h += '<td class="center detail-delta ' + _detailToneClass(tone) + '">' + (pt.skill_used ? '✓' : '—') + '</td></tr>';
  });
  return h + '</tbody></table>';
}

function _detailQuick8HistoryTable(hist) {
  var h = '<table class="detail-data-table"><thead><tr><th>时间</th><th class="center">Δ</th><th class="center">域内</th><th class="center">注入</th></tr></thead><tbody>';
  hist.slice(0, 6).forEach(function (row) {
    var ts = row.timestamp ? new Date(row.timestamp * 1000).toLocaleString() : '';
    var pct = row.improvement_pct || '';
    var dpct = row.domain_improvement_pct || '';
    h += '<tr><td class="detail-file-meta">' + escHtml(ts) + '</td>';
    h += '<td class="center detail-delta ' + _detailToneClass(_detailPctTone(pct)) + '"><b>' + escHtml(pct) + '</b></td>';
    h += '<td class="center detail-delta ' + _detailToneClass(_detailPctTone(dpct)) + '">' + escHtml(dpct || '—') + '</td>';
    h += '<td class="center">' + escHtml(String(row.skills_injected != null ? row.skills_injected : '-')) + '/' + escHtml(String(row.tasks || 8)) + '</td></tr>';
  });
  return h + '</tbody></table>';
}

function _renderQuick8Section(q8) {
  if (!q8) {
    return '<div class="dna-layer"><div class="dna-layer-title"><span>本地 Quick8</span></div>' +
      _detailInfoBox(
        '<div class="detail-decision-sub">尚未运行自建 8 题评测。</div>' +
        '<div class="detail-btn-row">' +
        '<button type="button" class="btn-primary btn-sm" onclick="runLocalQuick8()">运行 Quick8</button>' +
        '<button type="button" class="btn-secondary btn-sm" onclick="runLocalQuick8(true)">域内</button>' +
        '<span id="local-quick8-status" class="detail-inline-status"></span></div>'
      ) + '</div>';
  }
  var inner = '<div class="detail-file-meta">' + escHtml(q8.file || '') + '</div>';
  inner += '<div class="detail-decision-sub">有技能 <b>' + escHtml(String(q8.with_skill_score)) + '/' + escHtml(String(q8.max_score || q8.domain_max_score || (q8.tasks || 8) * 100)) + '</b> [' + escHtml(q8.with_skill_grade || '') + ']';
  inner += ' · 无技能 ' + escHtml(String(q8.without_skill_score)) + ' · Δ ' + _detailDeltaHtml(q8.improvement_pct) + '</div>';
  if (q8.skills_injected != null) inner += '<div class="detail-decision-meta">技能注入 ' + q8.skills_injected + '/' + (q8.tasks || 8) + ' 题</div>';
  if (q8.domain_improvement_pct) {
    inner += '<div class="detail-decision-meta">域内提升 ' + _detailDeltaHtml(q8.domain_improvement_pct);
    if (q8.harm_tasks && q8.harm_tasks.length) inner += ' · 伤害题 ' + escHtml(q8.harm_tasks.join(', '));
    inner += '</div>';
  }
  if (q8.task_ids && q8.task_ids.length) {
    inner += '<div class="detail-decision-meta">题目: ' + q8.task_ids.map(function (id) { return '<code>' + escHtml(id) + '</code>'; }).join(' ') + '</div>';
  }
  if (q8.per_task && q8.per_task.length) inner += _detailQuick8PerTaskTable(q8.per_task);
  inner += '<pre class="detail-code-block">python scripts/run_new3skills_bench_quick8.py</pre>';
  inner += '<div class="detail-btn-row">' +
    '<button type="button" class="btn-primary btn-sm" onclick="runLocalQuick8()">运行 Quick8 评测</button>' +
    '<button type="button" class="btn-secondary btn-sm" onclick="runLocalQuick8(true)">域内 Quick8</button>' +
    '<span id="local-quick8-status" class="detail-inline-status"></span></div>';
  return '<div class="dna-layer"><div class="dna-layer-title"><span>最近本地 Quick8</span></div>' + _detailInfoBox(inner) + '</div>';
}

async function loadOverview() {
  let el = _detailStage();
  if (!el) return;

  el.innerHTML = '<div class="detail-loading">' +
    '<div class="skeleton skeleton-line w60"></div>' +
    '<div class="skeleton skeleton-line w80"></div>' +
    '<div class="skeleton skeleton-line w40"></div>' +
    '<div class="skeleton skeleton-card detail-loading-card"></div>' +
    '<div class="skeleton skeleton-card"></div>' +
    '</div>';

  try {
    let skillR = await api('/api/skills/' + encodeURIComponent(_currentSkill));
    let dnaR = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/dna-check')
      .catch(function() { return { json: function() { return Promise.resolve({ passed: 0, total: 6, checks: [], score: '0/6' }); } }; });
    let exportR = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/export?format=markdown')
      .catch(function() { return { json: function() { return Promise.resolve({}); } }; });
    let skill = await skillR.json();
    let dna = await dnaR.json();
    let exportMeta = await exportR.json();
    if (typeof buildInstallPaths === 'function' && exportMeta.portable_slug) {
      exportMeta.install_paths = buildInstallPaths(exportMeta.portable_slug);
    }

    var qsContainer = document.getElementById('quality-strip-container');
    if (qsContainer && typeof renderQualityStrip === 'function') {
      qsContainer.innerHTML = renderQualityStrip(skill.epistemic_summary || {}) ||
        (dna.passed != null ? '<div class="quality-strip">' + renderQualityBadge('dna', (dna.passed || 0) + '/' + (dna.total || 6), 'lg') + '</div>' : '');
    }

    var dnaP = dna.passed || 0;
    var h = '';
    if (typeof renderOverviewTrustCard === 'function') h += renderOverviewTrustCard(skill);
    if (typeof renderOverviewSourceCard === 'function') h += renderOverviewSourceCard(skill, exportMeta);
    h += '<div class="dash-grid detail-kpi-grid">';
    h += _detailKpi('DNA 合规', dna.score || '0/6', _detailDnaTone(dnaP), '设计规范遵循度');
    h += _detailKpi('技能版本', 'v' + skill.version, 'muted', '迭代 ' + skill.runs + ' 次');
    h += _detailKpi('验证得分', skill.avg_score + '/5', _detailAvgTone(skill.avg_score), '自动测试通过率');
    h += _detailKpi('历史版本', String((skill.versions || []).length), 'muted', '版本数量');
    var ds = skill.dir_stats || {};
    var dirCount = (ds.knowledge||0) + (ds.scripts||0) + (ds.references||0);
    if (dirCount > 0) h += _detailKpi('目录文件', String(dirCount), 'mid', 'knowledge/scripts/references');
    h += '</div>';

    h += await renderSimilarSkillsBanner(_currentSkill);

    var dnaInner = '';
    if (dna.checks && dna.checks.length) {
      dna.checks.forEach(function(c) { dnaInner += _detailCheckRow(c.passed, c.principle, c.detail); });
    } else {
      dnaInner = _detailMuted('暂无 DNA 合规数据');
    }
    h += _detailCard('DNA 设计规范合规检查', dnaInner);

    var depsInner = _detailMuted('依赖信息暂不可用');
    try {
      var kbR = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/kb').catch(function() { return null; });
      var deps = [];
      if (kbR) {
        var kb = await kbR.json();
        if (kb.templates > 0) deps.push(kb.templates + ' 个参考模板');
        if (kb.facts > 0) deps.push(kb.facts + ' 条事实知识');
        if (kb.heuristics > 0) deps.push(kb.heuristics + ' 条启发规则');
        if (kb.constraints > 0) deps.push(kb.constraints + ' 条约束条件');
      }
      if (deps.length) {
        depsInner = '<div class="detail-chip-row">' + deps.map(_detailChip).join('') + '</div>';
      } else {
        depsInner = _detailMuted('无外部依赖，可独立使用');
      }
    } catch (e) { /* keep fallback */ }
    h += _detailCard('依赖项', depsInner);

    try {
      var vR = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/variants').catch(function() { return null; });
      if (vR && vR.ok) {
        var vD = await vR.json();
        var vComp = vD.comparison || {};
        if (vComp.total_variants > 0) {
          var vInner = '<div class="detail-variant-title">技能变体 (' + vComp.total_variants + ')</div>';
          if (vComp.creators && vComp.creators.length) {
            vInner += '<div class="detail-variant-meta">创建者: ' + escHtml(vComp.creators.join(', ')) + '</div>';
          }
          if (vComp.commonality && vComp.commonality.length) {
            vInner += '<div class="detail-variant-meta accent">共识: ' + escHtml(vComp.commonality.slice(0, 3).join('; ')) + '</div>';
          }
          if (vComp.divergence && vComp.divergence.length) {
            vInner += '<div class="detail-variant-meta warn">分歧步骤: ' + vComp.divergence.length + ' 处</div>';
          }
          h += _detailCard('变体对比', vInner);
        }
      }
    } catch (e) { /* optional */ }

    var actions = '';
    actions += '<button type="button" class="btn-primary btn-sm" onclick="optimizeSkill(_currentSkill)">优化技能</button>';
    actions += '<button type="button" class="btn-secondary btn-sm" onclick="runEvolutionOptimize(_currentSkill)">MoE 优化</button>';
    actions += '<button type="button" class="btn-secondary btn-sm" onclick="exportSkillOpt(_currentSkill)">导出 SkillOpt</button>';
    if (skill.is_metaskill) {
      actions += '<button type="button" class="btn-accent btn-sm" onclick="runMetaSkill(_currentSkill)">运行流水线</button>';
    }
    actions += '<button type="button" class="btn-secondary btn-sm" onclick="exportSkill()">导出 Zip</button>';
    actions += '<button type="button" class="btn-secondary btn-sm" onclick="exportUniversal()">通用格式导出</button>';
    try {
      var ws = JSON.parse(localStorage.getItem(StorageKeys.WORKSPACE) || '{}');
      if (!ws.tenant_id || ws.tenant_id.indexOf('personal:') === 0) {
        actions += '<button type="button" class="btn-warn-solid btn-sm" onclick="copySkillToOrg(_currentSkill)">复制到公司</button>';
      }
    } catch (e) { /* optional */ }
    h += _detailActionRow(actions);

    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">加载失败: ' + escHtml(e.message) + '</div>';
  }
}


async function loadVerify() {
  let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/traces');
  let traces = await r.json();

  let h = '<div class="detail-toolbar">' +
    '<input id="verify-task" class="form-input detail-toolbar-input" placeholder="输入测试任务…">' +
    '<button type="button" class="btn-primary btn-sm" onclick="runVerify()">运行测试</button>' +
    '</div><div id="verify-result"></div>';

  if (traces.length) {
    h += '<div class="detail-trace-label">最近 Trace</div>';
    h += traces.slice(0, 10).map(function(t) {
      var tone = t.score >= 4 ? 'good' : t.score >= 3 ? 'mid' : 'low';
      return '<div class="detail-trace-item ' + tone + '">' +
        '<b>Score ' + t.score + '/5</b> · ' + escHtml((t.timestamp || '').slice(0, 10)) + '<br>' +
        '<span class="detail-trace-task">' + escHtml(t.task || '').slice(0, 80) + '</span><br>' +
        '<span class="detail-trace-feedback">' + escHtml(t.feedback || '').slice(0, 100) + '</span></div>';
    }).join('');
  }

  _detailStage().innerHTML = h;
}

async function loadEpistemic() {
  let el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载认识论状态…');
  try {
    let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/epistemic/pending');
    let d = await r.json();
    let ep = d.epistemic_summary || {};
    let pending = d.pending_claims || [];
    let h = '<div class="dash-grid detail-kpi-grid">';
    h += _detailKpi('已验证', ep.verified || 0, 'good', '已确认声明');
    h += _detailKpi('待确认', ep.pending || 0, 'mid', '经验/证据级');
    h += _detailKpi('总计', ep.total_claims || 0, 'muted', '提取的声明数');
    h += '</div>';

    h += await renderSimilarSkillsBanner(_currentSkill);

    if (!pending.length) {
      h += '<div class="empty-state"><div class="icon"><span data-icon="check"></span></div><div class="title">无待确认声明</div>';
      h += '<div class="hint">所有声明已验证，或尚未运行认识论提取。</div></div>';
      el.innerHTML = h;
      return;
    }

    var listInner = '<div id="epistemic-pending-list">';
    pending.forEach(function (c, i) {
      listInner += '<label class="detail-claim-row">' +
        '<input type="checkbox" class="ep-claim-cb" value="' + escHtml(c.claim_id) + '" checked>' +
        '<span><span class="detail-claim-meta">#' + (i + 1) + ' · ' + escHtml(c.level || '') + '</span><br>' +
        escHtml((c.content || '').slice(0, 240)) + '</span></label>';
    });
    listInner += '</div>';
    listInner += _detailActionRow(
      '<button type="button" class="btn-primary btn-sm" onclick="confirmEpistemicSelected(false)">确认选中</button>' +
      '<button type="button" class="btn-secondary btn-sm" onclick="confirmEpistemicSelected(true)">全部确认</button>'
    );
    h += _detailCard('待确认声明', listInner);
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function confirmEpistemicSelected(all) {
  if (!_currentSkill) return;
  let body = { confirm_all: !!all, claim_ids: [] };
  if (!all) {
    document.querySelectorAll('.ep-claim-cb:checked').forEach(function (cb) {
      body.claim_ids.push(cb.value);
    });
    if (!body.claim_ids.length) {
      toast('请先勾选要确认的声明', 'err');
      return;
    }
  }
  try {
    let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/epistemic/confirm', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    let d = await r.json();
    toast('已晋升 ' + (d.promoted || 0) + ' 条声明', 'success');
    loadEpistemic();
  } catch (e) {
    toast('确认失败: ' + e.message, 'err');
  }
}

function _dnaWeightBar(weight, color) {
  var pct = Math.round((weight || 0) * 100);
  return '<div class="dna-bar-wrap"><div class="dna-bar" style="width:' + pct + '%;background:' + (color || 'var(--accent)') + '"></div></div>' +
    '<span class="dna-weight">' + pct + '%</span>';
}

function _philosophicalLabel(id) {
  var map = {
    pdca: 'PDCA 循环',
    ooda: 'OODA 循环',
    'scientific-method': '科学方法',
    dialectical: '辩证思维',
    reductionist: '还原论',
    pragmatic: '实用主义',
  };
  return map[id] || id;
}

async function loadDnaLineage() {
  var el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载 DNA 血缘…');
  try {
    var skillEnc = encodeURIComponent(_currentSkill);
    var results = await Promise.all([
      api('/api/skills/' + skillEnc + '/dna-lineage'),
      api('/api/skills/' + skillEnc + '/dna-check').catch(function () { return null; }),
      api('/api/bench/official/skills/' + skillEnc + '/smoke').catch(function () { return null; }),
    ]);
    var r = results[0];
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var dnaCheck = results[1] && results[1].ok ? await results[1].json() : null;
    var smoke = results[2] && results[2].ok ? await results[2].json() : null;
    var lineage = d.dna_lineage || {};
    var meta = d.meta || {};
    var philoStats = d.philosophical_stats || {};
    var philo = lineage.philosophical || [];
    var domain = lineage.domain || [];
    var staleCount = domain.filter(function (x) { return x.is_stale; }).length;

    var h = '<div class="dash-grid detail-kpi-grid">';
    h += _detailKpi('哲学 DNA', String(philo.length), 'muted', '层 0 方法论');
    h += _detailKpi('领域 DNA', String(domain.length), 'good', '层 1 模板');
    h += _detailKpi('版本过期', String(staleCount), staleCount ? 'mid' : 'good', '需刷新血缘');
    h += '</div>';

    if (meta.domain_label || meta.methodology_label) {
      h += '<div class="detail-tag-row">';
      if (meta.domain_label) h += '<span class="dna-tag">' + escHtml(meta.domain_label) + '</span>';
      if (meta.philosophical_dna_label) h += '<span class="dna-tag">' + escHtml(meta.philosophical_dna_label) + '</span>';
      if (meta.methodology_label) h += '<span class="dna-tag">' + escHtml(meta.methodology_label) + '</span>';
      (meta.bench_categories || []).forEach(function (c) {
        h += '<span class="dna-tag">' + escHtml(c) + '</span>';
      });
      h += '</div>';
    }

    if (lineage.conflicts && lineage.conflicts.length) {
      h += '<div class="dna-conflict"><div class="detail-warn-title">方法论 / 领域冲突</div>';
      lineage.conflicts.forEach(function (c) {
        h += '<div class="detail-muted">' + escHtml(c) + '</div>';
      });
      h += '</div>';
    }
    if (lineage.domain_ambiguous) {
      h += '<div class="dna-conflict">⚠️ 多域竞争：多个领域模板得分接近，请在技能中明确主流程归属。</div>';
    }

    h += '<div class="dna-layer"><div class="dna-layer-title"><span>层 0 · 哲学方法论</span><span class="dna-layer-badge">Philosophical</span></div>';
    if (philo.length) {
      philo.forEach(function (p) {
        var stab = philoStats[p.id] && philoStats[p.id].stability;
        var hint = stab != null ? ' · 稳定性 ' + Math.round(stab * 100) + '%' : '';
        h += '<div class="dna-row"><span class="dna-id">' + escHtml(_philosophicalLabel(p.id)) + '</span>';
        h += _dnaWeightBar(p.weight, 'var(--blue)');
        h += '<span style="font-size:10px;color:var(--text3)">' + escHtml(p.id) + hint + '</span></div>';
      });
    } else {
      h += _detailMuted('暂无哲学 DNA 检测记录');
    }
    h += '</div>';

    h += '<div class="dna-layer"><div class="dna-layer-title"><span>层 1 · 领域模板</span><span class="dna-layer-badge">Domain</span></div>';
    if (domain.length) {
      domain.forEach(function (dom) {
        var cls = 'dna-domain-card' + (dom.primary ? ' primary' : '') + (dom.is_stale ? ' stale' : '');
        h += '<div class="' + cls + '"><div class="dna-domain-head">';
        h += '<span style="font-weight:600;font-size:13px">' + escHtml(dom.title || dom.id) + '</span>';
        if (dom.primary) h += '<span class="dna-tag primary">主模板</span>';
        if (dom.is_stale) h += '<span class="dna-tag warn">版本过期</span>';
        h += '</div>';
        h += '<div style="font-size:11px;color:var(--text3);margin-bottom:8px;font-family:var(--mono)">' + escHtml(dom.id) + '</div>';
        h += '<div class="dna-row" style="padding:4px 0;border:none">';
        h += '<span class="dna-id">继承权重</span>' + _dnaWeightBar(dom.weight, dom.primary ? 'var(--accent)' : 'var(--text3)');
        h += '</div>';
        h += '<div style="font-size:11px;color:var(--text2);margin-top:4px">记录版本 v' + escHtml(String(dom.version || '1.0.0'));
        if (dom.current_version) h += ' · 当前模板 v' + escHtml(dom.current_version);
        h += '</div></div>';
      });
    } else {
      h += _detailMuted('暂无领域模板匹配');
    }
    h += '</div>';

    if (dnaCheck && dnaCheck.dna_compliance) {
      var dc = dnaCheck.dna_compliance;
      var dcOk = dc.all_passed || (dc.passed >= 5);
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>DNA 合规</span><span class="dna-layer-badge">' + escHtml(dc.score || '') + '</span></div>';
      h += '<div style="font-size:var(--t-sm);color:' + (dcOk ? 'var(--accent)' : 'var(--warn)') + ';margin-bottom:8px">';
      h += dcOk ? '✓ 合规通过' : '⚠ 待改进（目标 ≥5/6）';
      h += '</div>';
      (dc.checks || []).forEach(function (c) {
        var icon = c.passed ? '✓' : '✗';
        var col = c.passed ? 'var(--text2)' : 'var(--warn)';
        h += '<div style="font-size:11px;color:' + col + ';margin:3px 0">' + icon + ' ' + escHtml(c.rule || '') + '</div>';
      });
      h += '</div>';
    }

    if (meta.bench_quality && meta.bench_quality.moe) {
      var moe = meta.bench_quality.moe;
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>MoE 评分</span><span class="dna-layer-badge">' + escHtml(String(moe.overall_score || '—')) + '</span></div>';
      h += '<div style="font-size:var(--t-sm);color:var(--text2)">';
      h += '通过 ' + (moe.passed ? '✓' : '✗');
      if (moe.confidence != null) h += ' · 置信度 ' + Math.round(moe.confidence * 100) + '%';
      if (moe.boost_rounds && moe.boost_rounds.length) h += ' · 补强 ' + moe.boost_rounds.length + ' 轮';
      h += '</div></div>';
    }

    if (smoke && smoke.suite && smoke.suite.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>域内烟测</span><span class="dna-layer-badge">Save Gate</span></div>';
      h += '<div style="font-size:var(--t-sm);color:' + (smoke.smoke_pass ? 'var(--accent)' : 'var(--err)') + ';margin-bottom:8px">';
      h += smoke.smoke_pass ? '✓ 烟测通过（min≥80）' : '✗ 烟测未达标 min=' + smoke.min_with_score;
      h += '</div>';
      smoke.suite.forEach(function (row) {
        h += '<div style="font-size:11px;color:var(--text2);margin:3px 0"><code>' + escHtml(row.task_id) + '</code> ';
        h += '有 ' + row.with_score + ' / 无 ' + row.without_score + '</div>';
      });
      h += '</div>';
    } else if (meta.bench_quality && meta.bench_quality.save_gate) {
      var g = meta.bench_quality.save_gate;
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>域内烟测</span><span class="dna-layer-badge">已持久化</span></div>';
      h += '<div style="font-size:var(--t-sm);color:' + (g.smoke_pass ? 'var(--accent)' : 'var(--err)') + '">';
      h += g.smoke_pass ? '✓ 烟测通过' : '✗ 烟测未达标 min=' + (g.min_with_score || '—');
      if (g.tasks && g.tasks.length) {
        h += '<div style="font-size:11px;color:var(--text3);margin-top:4px">任务: ' + g.tasks.map(function (t) { return '<code>' + escHtml(t) + '</code>'; }).join(' ') + '</div>';
      }
      h += '</div></div>';
    }

    if (meta.bench_quality && meta.bench_quality.dna_compliance && !dnaCheck) {
      var bdc = meta.bench_quality.dna_compliance;
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>DNA 合规（存档）</span><span class="dna-layer-badge">' + escHtml(bdc.score || '') + '</span></div></div>';
    }

    if (lineage.detected_at) {
      h += '<div class="detail-meta-row">检测时间 ' + escHtml(lineage.detected_at) + '</div>';
    }

    var dnaActions = '<button type="button" class="btn-primary btn-sm" onclick="refreshDnaLineage()">刷新血缘版本</button>';
    if (staleCount) {
      dnaActions += '<span class="detail-status-note">有 ' + staleCount + ' 个领域模板版本落后于当前 DNA</span>';
    }
    h += _detailActionRow(dnaActions);

    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function refreshDnaLineage() {
  if (!_currentSkill) return;
  try {
    var r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/refresh-dna-lineage', {
      method: 'POST',
    });
    var d = await r.json();
    if (d.changed) {
      toast('DNA 血缘已更新到最新模板版本', 'success');
    } else if (d.still_stale) {
      toast('刷新后仍有过期项，请检查模板配置', 'err');
    } else {
      toast('血缘已是最新，无需变更', 'success');
    }
    loadDnaLineage();
  } catch (e) {
    toast('刷新失败: ' + e.message, 'err');
  }
}

async function loadOfficialBench() {
  var el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载官方 SkillsBench…');
  try {
    var r = await api('/api/bench/official/skills/' + encodeURIComponent(_currentSkill));
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var plan = d.plan || {};
    var h = _detailIntro(
      '对接 <a href="https://github.com/benchflow-ai/skillsbench" target="_blank" rel="noopener">官方 SkillsBench</a>（BenchFlow + Docker）。' +
      ' 本地快速分为自建 88 题；此处为<strong>官方沙箱 pass rate</strong>评测计划。'
    );

    h += '<div class="dash-grid detail-kpi-grid">';
    h += _detailKpi('推荐 task', String((plan.suggested_official_tasks || []).length), 'muted', '官方任务');
    h += _detailKpi('预设', String((plan.matching_presets || []).length), 'good', '一键对比');
    var q8 = d.latest_quick8;
    if (q8 && q8.improvement_pct) {
      h += _detailKpi('Quick8 Δ', escHtml(q8.improvement_pct), _detailPctTone(q8.improvement_pct), '自建8题');
    }
    if (q8 && q8.domain_improvement_pct) {
      var dlabel = q8.domain_only || q8.mode === 'skill_domain_quick8' ? (q8.tasks || 1) + '题域内' : (q8.skills_injected || 0) + '题注入';
      h += _detailKpi('域内 Δ', escHtml(q8.domain_improvement_pct), _detailPctTone(q8.domain_improvement_pct), dlabel);
    }
    h += '</div>';

    h += _renderQuick8Section(q8);

    var hist = d.quick8_history || [];
    if (hist.length > 1) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>Quick8 历史趋势</span></div>';
      h += _detailQuick8HistoryTable(hist);
      h += '</div>';
    }

    if (plan.windows_note) {
      h += '<div class="dna-conflict detail-panel">' + escHtml(plan.windows_note) + '</div>';
    }

    if (plan.suggested_official_tasks && plan.suggested_official_tasks.length) {
      var tasksInner = '<ul class="detail-task-list">';
      plan.suggested_official_tasks.forEach(function (tid) {
        tasksInner += '<li><code>' + escHtml(tid) + '</code></li>';
      });
      tasksInner += '</ul>';
      h += _detailCard('推荐官方 Task', tasksInner);
    }

    if (plan.matching_presets && plan.matching_presets.length) {
      var presetsInner = '';
      plan.matching_presets.forEach(function (p) {
        presetsInner += '<div class="dna-domain-card"><div class="detail-variant-title">' + escHtml(p.id) + '</div>';
        presetsInner += '<div class="detail-variant-meta">' + escHtml(p.description || '') + '</div>';
        presetsInner += '<div class="detail-decision-meta">task: <code>' + escHtml(p.task) + '</code></div>';
        presetsInner += '<pre class="detail-code-block">python scripts/run_official_skill_compare.py --preset ' + escHtml(p.id) + '</pre></div>';
      });
      presetsInner += '<div class="detail-btn-row">' +
        '<button type="button" class="btn-secondary btn-sm" onclick="triggerOfficialCi()">请求 GitHub CI 评测</button>' +
        '<span id="official-ci-status" class="detail-inline-status"></span></div>';
      h += _detailCard('Agent 对比预设', presetsInner);
    }

    if (plan.commands) {
      var cmdInner = '';
      Object.keys(plan.commands).forEach(function (k) {
        if (!plan.commands[k]) return;
        cmdInner += '<div class="detail-file-meta">' + escHtml(k) + '</div>';
        cmdInner += '<pre class="detail-code-block">' + escHtml(plan.commands[k]) + '</pre>';
      });
      h += _detailCard('CLI 命令（Linux / CI）', cmdInner);
    }

    var latest = d.latest_official || {};
    var latestCompare = (latest.compare || []).slice(0, 2);
    var latestSmoke = (latest.smoke || []).slice(0, 1);
    if (latestCompare.length || latestSmoke.length) {
      var ciInner = '';
      latestCompare.forEach(function (item) {
        var cmp = item.comparison || {};
        ciInner += _detailInfoBox(
          '<div class="detail-file-meta">' + escHtml(item._file || '') + '</div>' +
          (cmp.improvement ? 'Agent 对比 Δ: <b>' + escHtml(cmp.improvement) + '</b>' : '') +
          (item.preset ? ' · preset: <code>' + escHtml(item.preset) + '</code>' : '')
        );
      });
      latestSmoke.forEach(function (item) {
        ciInner += _detailInfoBox(
          '<div class="detail-file-meta">' + escHtml(item._file || '') + ' · oracle smoke</div>' +
          (item.reward != null ? 'reward: <b>' + escHtml(String(item.reward)) + '</b>' : '')
        );
      });
      h += _detailCard('最近官方 CI 结果', ciInner);
    }

    var related = d.related_benchmarks || [];
    if (related.length) {
      var relInner = '';
      related.forEach(function (item) {
        var data = item.data || {};
        var block = '<div class="detail-file-meta">' + escHtml(item.file) + '</div>';
        if (data.comparison) {
          block += '官方对比 Δ: <b>' + escHtml(data.comparison.improvement || '') + '</b>';
        } else if (data.task_compare) {
          data.task_compare.forEach(function (tc) {
            if (tc.label || tc.skill === _currentSkill || (tc.skill && tc.skill.indexOf(_currentSkill) >= 0)) {
              block += '<div class="detail-decision-meta">' + escHtml(tc.label || tc.skill || '') + ' · Δ ' + escHtml(tc.improvement_pct || '') + '</div>';
            }
          });
        } else if (data.structural) {
          data.structural.forEach(function (s) {
            if (s.skill === _currentSkill) {
              block += '<div class="detail-decision-meta">结构分 ' + s.total + '/100 [' + escHtml(s.grade || '') + ']</div>';
            }
          });
        }
        relInner += _detailInfoBox(block);
      });
      h += _detailCard('本地历史评测', relInner);
    } else {
      h += _detailMuted('暂无本地官方/快速评测记录。配置 GitHub DEEPSEEK_API_KEY 后可在 Actions 运行 Official SkillsBench。');
    }

    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function runLocalQuick8(domainOnly) {
  var statusEl = document.getElementById('local-quick8-status');
  if (!_currentSkill) return;
  if (statusEl) statusEl.textContent = (domainOnly ? '域内' : '') + '评测中…';
  try {
    var url = '/api/bench/official/skills/' + encodeURIComponent(_currentSkill) + '/quick8';
    if (domainOnly) url += '?domain_only=true';
    var r = await api(url, { method: 'POST' });
    var d = await r.json();
    if (!r.ok) throw new Error((d && d.detail) || ('HTTP ' + r.status));
    if (statusEl) statusEl.textContent = '完成 · Δ ' + (d.improvement_pct || '') + (d.domain_improvement_pct ? ' · 域内 ' + d.domain_improvement_pct : '') + ' · 注入 ' + (d.skills_injected != null ? d.skills_injected : '?') + '/' + (d.tasks || 8);
    toast('Quick8 完成: ' + (d.domain_improvement_pct || d.improvement_pct || ''), 'success');
    loadOfficialBench();
  } catch (e) {
    if (statusEl) statusEl.textContent = e.message;
    toast('Quick8 失败: ' + e.message, 'err');
  }
}

async function triggerOfficialCi() {
  var statusEl = document.getElementById('official-ci-status');
  if (!_currentSkill) return;
  if (statusEl) statusEl.textContent = '请求中…';
  try {
    var r = await api('/api/bench/official/skills/' + encodeURIComponent(_currentSkill) + '/trigger-ci', { method: 'POST' });
    var d = await r.json();
    if (d.ok) {
      if (statusEl) statusEl.textContent = '已触发 CI · preset ' + (d.preset || '');
      toast('已请求 GitHub Actions 官方评测', 'success');
    } else {
      var hint = d.reason || '未配置 GITHUB_TOKEN';
      if (statusEl) statusEl.textContent = hint;
      toast(hint + ' · 可手动运行 CLI', 'warn');
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = e.message;
    toast('触发失败: ' + e.message, 'err');
  }
}

async function loadMeta() {
  var el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载 MetaSkill 流水线…');
  try {
    var r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/metaskill');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var h = '<div class="detail-meta-header">';
    h += '<div class="detail-meta-title">' + escHtml(d.name || _currentSkill) + '</div>';
    h += '<div class="detail-meta-sub">' + escHtml(d.goal || '') + '</div></div>';
    h += '<div class="detail-status-inline">风险等级: <b>' + escHtml(d.risk_level || 'low') + '</b> · ';
    h += d.valid
      ? '<span class="detail-status-ok">结构有效</span>'
      : '<span class="detail-status-err">' + escHtml(d.validation_message || '结构无效') + '</span>';
    h += '</div>';

    var dagId = '';
    if (d.mermaid) {
      dagId = 'meta-dag-' + Date.now();
      h += _detailCard('流水线 DAG', '<div class="mermaid-wrap"><pre class="mermaid" id="' + dagId + '"></pre></div>');
    }

    var stepsInner = '';
    if (d.steps && d.steps.length) {
      d.steps.forEach(function (s, i) {
        stepsInner += '<div class="detail-step-card">';
        stepsInner += '<div class="detail-step-name">' + (i + 1) + '. ' + escHtml(s.name) + ' → ' + escHtml(s.skill_name) + '</div>';
        if (s.depends_on && s.depends_on.length) {
          stepsInner += '<div class="detail-step-meta">依赖: ' + escHtml(s.depends_on.join(', ')) + '</div>';
        }
        if (s.output_key) stepsInner += '<div class="detail-step-meta">输出键: ' + escHtml(s.output_key) + '</div>';
        stepsInner += '</div>';
      });
    } else {
      stepsInner = _detailMuted('无步骤');
    }
    h += _detailCard('流水线步骤', stepsInner);
    h += _detailActionRow(
      '<button type="button" class="btn-primary btn-sm" onclick="runMetaSkill(_currentSkill, false)">完整运行</button>' +
      '<button type="button" class="btn-secondary btn-sm" onclick="runMetaSkill(_currentSkill, true)">试运行（无 LLM）</button>'
    );
    h += '<div id="meta-run-result" class="detail-run-result"></div>';
    el.innerHTML = h;
    if (d.mermaid) _queueMermaid(dagId, d.mermaid);
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">MetaSkill 加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function runMetaSkill(name, dryRun) {
  if (!name) return;
  if (dryRun === undefined) dryRun = true;
  var resultEl = document.getElementById('meta-run-result');
  if (resultEl) resultEl.innerHTML = _detailMuted('运行中…');
  toast(dryRun ? 'MetaSkill 试运行…' : 'MetaSkill 完整运行…');
  try {
    var r = await api('/api/skills/' + encodeURIComponent(name) + '/metaskill/run', {
      method: 'POST',
      body: JSON.stringify({ user_input: '', dry_run: !!dryRun }),
    });
    var d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'run failed');
    var h = _detailInfoBox(
      '<div class="detail-step-name" style="margin-bottom:var(--s-2)">' + (d.success ? '运行成功' : '运行未完成') + '</div>' +
      (d.trace && d.trace.length ? '<pre class="detail-doc-pre" style="margin:0 0 var(--s-2)">' + escHtml(d.trace.join('\n')) + '</pre>' : '') +
      (d.errors && d.errors.length ? '<div class="detail-status-err">' + escHtml(d.errors.join('; ')) + '</div>' : '')
    );
    if (resultEl) resultEl.innerHTML = h;
    else toast(d.success ? 'MetaSkill 运行完成' : 'MetaSkill 运行失败', d.success ? 'success' : 'error');
  } catch (e) {
    if (resultEl) resultEl.innerHTML = '<div style="color:var(--err);font-size:var(--t-sm)">' + escHtml(e.message) + '</div>';
    toast('MetaSkill 运行失败: ' + e.message, 'error');
  }
}

async function loadEvo() {
  let el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载进化状态…');

  try {
    let [stateR, routeR, tracesR, triggersR] = await Promise.all([
      api('/api/evolution/' + encodeURIComponent(_currentSkill) + '/state'),
      api('/api/evolution/' + encodeURIComponent(_currentSkill) + '/route', { method: 'POST' }),
      api('/api/skills/' + encodeURIComponent(_currentSkill) + '/traces'),
      api('/api/evolution/triggers').catch(function() { return null; }),
    ]);

    let state = stateR.ok ? await stateR.json() : {};
    let route = routeR.ok ? await routeR.json() : {};
    let traces = tracesR.ok ? await tracesR.json() : [];
    let triggers = (triggersR && triggersR.ok) ? await triggersR.json() : {};

    let scores = traces.map(t => t.score).filter(s => s > 0);
    let avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 'N/A';
    let routing = route.routing || {};

    let h = '<div class="dash-grid detail-kpi-grid">';
    h += _detailKpi('Trace 数', state.trace_count || 0, 'muted', '执行记录');
    h += _detailKpi('平均分', avg + '/5', avg === 'N/A' ? 'muted' : _detailAvgTone(parseFloat(avg)), '验证得分');
    h += _detailKpi('成熟度', (state.maturity_days || 0) + ' 天', 'muted', '技能年龄');
    h += _detailKpi('推荐专家', routing.primary || state.recommended_expert || '—', 'mid', 'MoE 路由');
    h += '</div>';

    if (routing.reason) {
      h += _detailCard('MoE 路由 · 置信度 ' + Math.round((routing.confidence || 0) * 100) + '%', escHtml(routing.reason));
    }

    // Evolution triggers summary
    if (triggers && triggers.triggers > 0 && triggers.top_triggers) {
      var trigInner = '';
      triggers.top_triggers.slice(0, 3).forEach(function(t) {
        trigInner += '<div class="detail-decision-sub">' + escHtml(typeof t === 'string' ? t : (t.skill || t.reason || '')) + '</div>';
      });
      if (triggers.suggestion) trigInner += '<div class="detail-decision-meta">' + escHtml(triggers.suggestion) + '</div>';
      h += '<div class="content-card detail-panel" style="border-color:rgba(212,160,84,.2)">';
      h += '<div class="content-card-header" style="color:var(--warn)">进化触发器 (' + triggers.triggers + ')</div>' + trigInner + '</div>';
    }

    h += _detailActionRow(
      '<button type="button" class="btn-primary btn-sm" onclick="runEvolutionOptimize(_currentSkill)">MoE 优化一轮</button>' +
      '<button type="button" class="btn-secondary btn-sm" onclick="exportSkillOpt(_currentSkill)">导出 SkillOpt</button>' +
      '<button type="button" class="btn-secondary btn-sm" onclick="runSkillOptCli(_currentSkill)">SkillOpt CLI</button>'
    );

    h += '<div id="evo-cli-block"></div>';
    h += '<div id="evo-result" class="detail-run-result"></div>';

    h += '<div class="content-card detail-panel"><div class="content-card-header">自我改进循环</div>';
    h += '<div class="detail-loop-row">';
    h += '<div class="detail-loop-cell"><div class="detail-loop-cell-title blue">内循环</div><div class="detail-loop-cell-sub">执行 ' + (traces.length || 0) + ' 次 · 记录轨迹</div></div>';
    h += '<div class="detail-loop-arrow">→</div>';
    h += '<div class="detail-loop-cell"><div class="detail-loop-cell-title amber">反馈</div><div class="detail-loop-cell-sub">' + (state.trace_count || 0) + ' 条记录 · 人工审阅</div></div>';
    h += '<div class="detail-loop-arrow">→</div>';
    h += '<div class="detail-loop-cell"><div class="detail-loop-cell-title green">外循环</div><div class="detail-loop-cell-sub">生成 diff · 改进 Skill v' + (state.version || '1') + '</div></div>';
    h += '</div></div>';

    h += '<div class="content-card detail-panel"><div class="content-card-header">三种进化范式</div>';
    h += '<div class="detail-paradigm-row">';
    h += '<div class="detail-paradigm-cell t-green"><b style="color:var(--accent)">Trace2Skill</b><br>归纳法 · 批量轨迹 → 一次成型</div>';
    h += '<div class="detail-paradigm-cell t-blue"><b style="color:var(--info)">EvoSkill</b><br>验证选择 · 前沿集合淘汰</div>';
    h += '<div class="detail-paradigm-cell t-violet"><b style="color:var(--violet)">SkillOpt</b><br>训练范式 · 学习率+动量</div>';
    h += '</div>';
    h += '<div class="detail-decision-meta" style="margin-top:var(--s-2)">SkillOS 当前采用 Trace2Skill + EvoSkill 混合策略。<br>参考：阿里千问 Trace2Skill、Sentient Labs EvoSkill、微软 SkillOpt</div>';
    h += '</div>';

    h += '<div class="content-card detail-panel"><div class="content-card-header">进化时间线</div>';
    if (traces.length) {
      h += '<div class="evo-timeline">';
      traces.slice(0, 8).forEach(function(t, i) {
        var color = t.score >= 4 ? 'var(--a3)' : t.score >= 3 ? 'var(--amber)' : 'var(--red)';
        var date = (t.timestamp || '').slice(0, 10);
        h += '<div class="evo-tl-item">' +
          '<div class="evo-tl-dot" style="background:' + color + '"></div>' +
          '<div class="evo-tl-line"></div>' +
          '<div class="evo-tl-content">' +
            '<div class="evo-tl-score" style="color:' + color + '">' + t.score + '/5</div>' +
            '<div class="evo-tl-task">' + escHtml((t.task || '').slice(0, 60)) + '</div>' +
            '<div class="evo-tl-date">' + date + '</div>' +
          '</div>' +
        '</div>';
      });
      h += '</div>';
    } else {
      h += '<div class="content-empty">暂无进化记录<br><small>在「验证」Tab 运行测试后可触发优化</small></div>';
    }
    h += '</div>';

    el.innerHTML = h;

    if (typeof fetchSkillOptCliHelp === 'function') {
      fetchSkillOptCliHelp().then(function (help) {
        var cliEl = document.getElementById('evo-cli-block');
        if (!cliEl || !help || !help.commands) return;
        var skill = _currentSkill || '<skill_name>';
        cliEl.innerHTML = skillOptCliBlock({
          export: (help.commands.export || '').replace('<skill_name>', skill),
          validate: 'python scripts/skillopt_cli.py validate <export_dir>',
          run_dry: (help.commands.run || '').replace('<skill_name>', skill) + ' --dry-run',
        }) + '<div style="font-size:11px;color:var(--text3);margin-top:6px">设置 SKILLOPT_EXTERNAL_CMD 可挂载外部 SkillOpt</div>';
      });
    }
  } catch (e) {
    el.innerHTML = (typeof renderErrorState === 'function' ? renderErrorState(e.message) : '<div class="u-err">加载失败: ' + escHtml(e.message) + '</div>');
  }
}

async function runEvolutionOptimize(name) {
  if (!name) return;
  var resultEl = document.getElementById('evo-result');
  if (resultEl) resultEl.innerHTML = '<div style="color:var(--text3);font-size:var(--t-sm)">MoE 优化中…</div>';
  toast('MoE 优化运行中…');
  try {
    var r = await api('/api/evolution/' + encodeURIComponent(name) + '/optimize', {
      method: 'POST',
      body: JSON.stringify({ feedback: '' }),
    });
    var d = await r.json();
    var msg = (d.accepted ? '✅ 优化已接受' : '⚠ 未接受变更') + ' · 专家 ' + (d.expert || '—') + ' · ' + escHtml(d.detail || d.improvement || '');
    if (resultEl) resultEl.innerHTML = '<div style="font-size:var(--t-sm);padding:10px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">' + msg + '</div>';
    toast(d.accepted ? '优化已接受' : '优化未接受变更', d.accepted ? 'success' : 'warn');
    loadEvo();
  } catch (e) {
    if (resultEl) resultEl.innerHTML = '<div style="color:var(--err);font-size:var(--t-sm)">' + escHtml(e.message) + '</div>';
    toast('优化失败: ' + e.message, 'error');
  }
}

async function exportSkillOpt(name) {
  if (!name) return;
  toast('导出 SkillOpt 包…');
  try {
    var r = await api('/api/evolution/' + encodeURIComponent(name) + '/export-skillopt', { method: 'POST' });
    var d = await r.json();
    if (!d.ok) throw new Error(d.error || 'export failed');
    toast('已导出至 ' + (d.export_dir || 'data/exports/skillopt'), 'success');
    var cliEl = document.getElementById('evo-cli-block');
    if (cliEl && d.cli) cliEl.innerHTML = skillOptCliBlock(d.cli);
  } catch (e) {
    toast('导出失败: ' + e.message, 'error');
  }
}

async function runSkillOptCli(name) {
  if (!name) return;
  toast('SkillOpt CLI 试运行…');
  try {
    var r = await api('/api/evolution/' + encodeURIComponent(name) + '/skillopt-run?dry_run=true', { method: 'POST' });
    var d = await r.json();
    var cliEl = document.getElementById('evo-cli-block');
    var msg = (d.ok ? '✅ 导出验证通过' : '⚠ 验证失败') + (d.cli_hint ? ' · ' + d.cli_hint : '');
    if (d.external_command) msg += '<br><code style="color:var(--accent)">' + escHtml(d.external_command) + '</code>';
    if (cliEl) cliEl.innerHTML = '<div style="font-size:var(--t-sm);padding:10px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">' + msg + '</div>';
    toast(d.ok ? 'CLI dry-run 完成' : 'CLI 失败', d.ok ? 'success' : 'error');
  } catch (e) {
    toast('CLI 失败: ' + e.message, 'error');
  }
}

async function loadKB() {
  var h = '<div class="detail-kb-toolbar">' +
    '<button type="button" class="btn-primary btn-sm" onclick="compareTemplate()">对比模板</button>' +
    '<input type="file" id="tpl-upload" style="display:none" accept=".txt,.md" onchange="uploadTemplate(event)">' +
    '</div>' +
    '<div class="detail-kb-field">' +
    '<label class="detail-kb-label">添加到知识库</label>' +
    '<div class="detail-kb-url-row">' +
    '<input id="kb-url" class="form-input detail-toolbar-input" placeholder="粘贴 URL…">' +
    '<button type="button" class="btn-secondary btn-sm" onclick="addToKB()">添加 URL</button>' +
    '</div></div>' +
    '<div id="kb-status" class="detail-kb-status">在对话中发送 URL，或使用「对比模板」检查文档与已存模板的差异。</div>';
  _detailStage().innerHTML = h;
}

async function loadDecisions() {
  let el = _detailStage();
  if (!el) return;
  el.innerHTML = _detailMuted('加载决策历史…');

  try {
    let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/decisions');
    let d = await r.json();
    let decisions = d.decisions || [];

    if (!decisions.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon"><span data-icon="brain"></span></div><div class="title">暂无决策记录</div><div class="hint">技能优化轮次完成后会在此显示决策历史，记录「为什么改」而不仅是「改了什么」。</div></div>';
      return;
    }

    let h = '<div class="detail-meta-row">' + decisions.length + ' 条决策记录 — WHY 链</div>';
    decisions.reverse().forEach(function(rec) {
      var outcome = rec.outcome || '';
      var ocClass = outcome === 'accepted' ? 'accepted' : outcome === 'rejected' ? 'rejected' : 'partial';
      var inner = '<div class="detail-decision-head">';
      inner += '<span class="detail-decision-round">Round ' + escHtml(String(rec.round_num)) + '</span>';
      inner += '<span class="detail-decision-ver">v' + escHtml(String(rec.version_from)) + '→v' + escHtml(String(rec.version_to)) + '</span>';
      inner += '<span class="detail-decision-outcome ' + ocClass + '">' + escHtml(outcome) + '</span></div>';
      inner += '<div class="detail-decision-body"><b>诊断:</b> ' + escHtml((rec.diagnosis || '').slice(0, 200)) + '</div>';
      inner += '<div class="detail-decision-sub"><b>结果:</b> ' + escHtml((rec.outcome_detail || '').slice(0, 200)) + '</div>';
      if (rec.candidate_revisions && rec.candidate_revisions.length) {
        inner += '<div class="detail-decision-meta">修改: ' + escHtml(rec.candidate_revisions.map(function(e) { return e.type + ' ' + e.detail; }).join(', ').slice(0, 150)) + '</div>';
      }
      if (rec.rejected_alternatives && rec.rejected_alternatives.length) {
        inner += '<div class="detail-decision-meta err">拒绝的方案: ' + escHtml(rec.rejected_alternatives.join('; ').slice(0, 150)) + '</div>';
      }
      if (rec.evaluation_evidence && rec.evaluation_evidence.old_score !== undefined) {
        var ev = rec.evaluation_evidence;
        inner += '<div class="detail-decision-meta">评估: ' + ev.old_score + '→' + ev.new_score +
          ' (执行:' + ev.old_execution + '→' + ev.new_execution +
          ' 审计:' + ev.old_audit + '→' + ev.new_audit + ')</div>';
      }
      h += _detailDecisionCard(outcome, inner);
    });
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = typeof renderErrorState === 'function'
      ? renderErrorState(e.message)
      : '<div class="detail-muted" style="color:var(--err)">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

function uploadTemplate(ev) {
  var file = ev.target && ev.target.files && ev.target.files[0];
  if (!file || !_currentSkill) return;
  var reader = new FileReader();
  reader.onload = async function () {
    try {
      var r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/compare-template', {
        method: 'POST',
        body: JSON.stringify({ input: reader.result || '' }),
      });
      var d = await r.json();
      var el = document.getElementById('kb-status');
      if (el) el.innerHTML = '<pre style="white-space:pre-wrap;font-size:var(--t-sm);color:var(--text)">' + escHtml(JSON.stringify(d, null, 2)) + '</pre>';
      toast('模板对比完成');
    } catch (e) {
      toast('对比失败: ' + e.message, 'error');
    }
  };
  reader.readAsText(file);
}

async function runVerify() {

  let task = document.getElementById('verify-task').value.trim();

  if (!task) {

    document.getElementById('verify-result').innerHTML =

      '<span style="color:var(--err)">Enter a test task</span>';

    return;

  }

  document.getElementById('verify-result').innerHTML = 'Running...';

  let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/run', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({ task })

  });

  let d = await r.json();

  if (d.error) {

    document.getElementById('verify-result').innerHTML =

      '<span style="color:var(--err)">' + escHtml(d.error) + '</span>';

    return;

  }

  document.getElementById('verify-result').innerHTML =

    '<div style="padding:10px;background:#0a1a0a;border-radius:4px;margin-top:8px;font-size:14px">' +

    '<b>Result:</b><br>' +

    '<span style="font-size:13px;color:var(--dim)">' + escHtml((d.result || '').slice(0, 300)) + '</span></div>';

  setTimeout(() => loadVerify(), 500);

}

function compareTemplate() {

  let input = document.createElement('textarea');

  input.style.cssText = 'width:100%;height:150px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;color:var(--text);font-size:13px;margin-bottom:8px;font-family:inherit';

  input.placeholder = '粘贴文档内容，与已存模板对比…';

  let btn = document.createElement('button');

  btn.className = 'btn a'; btn.textContent = '对比'; btn.style.cssText = 'font-size:var(--t-sm);padding:5px 14px';

  btn.onclick = async () => {

    let text = input.value.trim();

    if (!text) return;

    setStatus('comparing...');

    try {

      let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/compare-template', {

        method: 'POST',

        body: JSON.stringify({input: text})

      });

      let d = await r.json();

      document.getElementById('kb-status').innerHTML = '<pre style=\"white-space:pre-wrap;font-size:var(--t-sm);color:var(--text)\">' + JSON.stringify(d,null,2) + '</pre>';

      setStatus('对比完成');

    } catch(e) { setStatus('error'); }

  };

  document.getElementById('kb-status').innerHTML = '';

  document.getElementById('kb-status').appendChild(input);

  document.getElementById('kb-status').appendChild(btn);

}

async function addToKB() {

  document.getElementById('kb-status').textContent =

    'Send the URL in chat and the agent will fetch & store it.';

}

async function loadBenchDashboard() {
  var el = document.getElementById('bench-dashboard');
  if (!el) return;
  el.style.display = 'block';
  try {
    var r = await api('/api/bench/official/summary');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var rows = d.reference_skills || [];
    var reg = d.latest_regression;
    var postExt = d.latest_post_extract;
    var h = '';
    if (reg && reg.summary) {
      var ok = reg.summary.all_pass;
      h += '<div style="font-weight:600;color:' + (ok ? 'var(--accent)' : 'var(--err)') + ';margin-bottom:6px">';
      h += ok ? '✓ 回归门禁通过' : '✗ 回归门禁未通过';
      if (reg.file) h += ' <span style="font-weight:400;font-size:10px;color:var(--text3)">' + escHtml(reg.file) + '</span>';
      h += '</div>';
    } else if (postExt && postExt.regression_scheduled !== undefined) {
      var peOk = postExt.all_pass;
      var peCol = peOk === true ? 'var(--accent)' : (peOk === false ? 'var(--err)' : 'var(--warn)');
      h += '<div style="font-weight:600;color:' + peCol + ';margin-bottom:6px">';
      h += peOk === true ? '✓ 萃取后回归通过' : (peOk === false ? '✗ 萃取后回归失败' : '⏳ 萃取后回归运行中…');
      if (postExt.trigger_skill) h += ' <span style="font-size:10px;color:var(--text3)">' + escHtml(postExt.trigger_skill) + '</span>';
      h += '</div>';
    }
    if (!rows.length && !h) {
      el.innerHTML = '暂无参考技能评测';
      return;
    }
    h += '<div style="font-weight:600;color:var(--text2);margin-bottom:6px">📊 Quick8 参考技能</div>';
    rows.forEach(function (row) {
      var pct = row.domain_improvement_pct || row.improvement_pct || '—';
      var col = String(pct).indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)';
      h += '<div style="display:flex;justify-content:space-between;gap:6px;margin:3px 0;cursor:pointer" onclick="showDetail(' + JSON.stringify(row.skill) + ',\'official\')">';
      h += '<span style="color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px">' + escHtml(row.skill) + '</span>';
      h += '<span style="color:' + col + ';flex-shrink:0">' + escHtml(pct) + '</span></div>';
    });
    el.innerHTML = h;
  } catch (e) {
    // Fallback: show skill count
    var total = (typeof _allSkillsCache !== 'undefined' && _allSkillsCache.length) ? _allSkillsCache.length : '—';
    el.innerHTML = '<span style=\"color:var(--text3)\">' + total + ' 个技能</span>';
  }
}

function refreshSkillList() {

  api('/api/skills/').then(r => r.json()).then(skills => {

    _allSkillsCache = skills;
    if (typeof renderSidebarWorkspace === 'function') renderSidebarWorkspace(skills);

    // Separate knowledge packages from regular skills
    var isKP = function(s) { return s.kb_items > 0 && s.avg_score === 0 && s.runs === 0; };
    var kpCount = skills.filter(isKP).length;
    document.getElementById('kp-count').textContent = kpCount;

    var filtered;
    if (_skillListTab === 'system') {
      filtered = skills.filter(function(s) { return SYSTEM_SKILLS.includes(s.name) && !isKP(s); });
    } else if (_skillListTab === 'packages') {
      filtered = skills.filter(isKP);
    } else {
      // 'mine' — exclude system skills AND knowledge packages
      filtered = skills.filter(function(s) { return !SYSTEM_SKILLS.includes(s.name) && !isKP(s); });
    }

    renderSkillCards(filtered);

  });

}

function renderSkillCards(skills) {

    document.getElementById('skill-list').innerHTML =

      skills.map(s => {

        let isMeta = s.name.startsWith('[Meta]');

        let health = s.avg_score >= 4 ? 'good' : s.avg_score >= 2 ? 'warn' : 'bad';
        let treeId = 'tree-' + s.name.replace(/[^a-zA-Z0-9]/g, '');
        let icon = isMeta ? '🔗 ' : '';
        let qualityBadges = typeof renderQualityMiniBadges === 'function' ? renderQualityMiniBadges(s) : '';
        var score = s.avg_score || 0;
        var scoreColor = score >= 4 ? 'var(--a2)' : score >= 2 ? 'var(--amber)' : 'var(--text3)';
        var metaLine = 'v' + s.version + ' · ' + s.runs + ' exec';

        return '<div class="skill-tree-node">' +

        '<div class="tree-row" data-tree="' + treeId + '" data-skill="' + s.name + '" onclick="toggleTreeNode(this.dataset.tree)">' +

        '<span class="tree-toggle" id="tgl-' + treeId + '">▸</span>' +

        '<span class="health ' + health + '"></span>' +

        '<span class="tree-name">' + icon + s.name.replace('[Meta] ', '') + '</span>' +
        '<span class="tree-score" style="color:' + scoreColor + '">' + (s.avg_score ? s.avg_score.toFixed(1) : '—') + '</span>' +
        '<span class="tree-meta">' + metaLine + '</span>' +

        (_skillListTab === 'mine' ? '<button class="opt-btn" style="margin-left:auto" onclick="event.stopPropagation();optimizeSkill(this.dataset.skill)" data-skill="' + escHtml(s.name) + '">⚡</button>' : '') +

        '</div>' +

        '<div class="tree-children" id="' + treeId + '">' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="showDetail(this.dataset.skill)">📄 SKILL.md</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill,\'kb\')">📚 KB</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill,\'verify\')">🧪 验证</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill,\'evo\')">🔄 进化</div>' +

        (isMeta ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill,\'meta\')">🔗 流水线</div>' : '') +

        (isMeta ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();runMetaSkill(this.dataset.skill)">▶ Run</div>' : '') +

        (_skillListTab === 'mine' ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showPublishForm(this.dataset.skill)" style="color:var(--warn);font-weight:600">📡 发布到市场</div>' : '') +

        '</div></div>';

      }).join('')

      || '<div class="empty-state"><div class="icon">📁</div><div class="title">' +

        (_skillListTab === 'mine' ? '还没有技能' : '系统技能') +

        '</div><div class="hint">' +

        (_skillListTab === 'mine' ? '在下方输入框描述你的工作流程，AI 会边聊边写，帮你沉淀成标准技能文档' : 'Agent 技能将在此显示') +
        (_skillListTab === 'mine' ? '<br><button class="action-btn" style="margin-top:12px;font-size:var(--t-sm);padding:6px 16px" onclick="showChat();document.getElementById(\'input\').focus()">开始创建</button>' : '') +

        '</div></div>';

    document.getElementById('skill-count').textContent = skills.length;

}

function toggleTreeNode(id) {
  var el = document.getElementById(id);
  var tgl = document.getElementById('tgl-' + id);
  var row = document.querySelector('[data-tree="' + id + '"]');
  if (!el || !tgl) return;
  var open = el.classList.toggle('open');
  if (row) row.classList.toggle('open', open);
  tgl.textContent = open ? '▾' : '▸';
}

function toggleSection(h) {

  h.classList.toggle('collapsed');

  h.nextElementSibling.classList.toggle('open');

}

function focusKnowledgeSection(h) {

  // Collapse Skills section

  let sections = document.querySelectorAll('#sidebar .sb-section');

  if (sections.length >= 1) {

    let skillsHeader = sections[0].querySelector('.sb-section-header');

    let skillsBody = sections[0].querySelector('.sb-section-body');

    if (skillsHeader) skillsHeader.classList.add('collapsed');

    if (skillsBody) skillsBody.classList.remove('open');

  }

  // Expand Knowledge section

  h.classList.remove('collapsed');

  let body = h.nextElementSibling;

  if (body) body.classList.add('open');

  // Scroll Knowledge header to top of sidebar

  h.scrollIntoView({ behavior: 'smooth', block: 'start' });

}

function filterSkillList() {

  let q = (document.getElementById('skill-search')||{}).value || '';

  if (!q) { refreshSkillList(); return; }

  q = q.toLowerCase();

  let filtered = _allSkillsCache.filter(s => {

    if (_skillListTab === 'system') return SYSTEM_SKILLS.includes(s.name) && s.name.toLowerCase().includes(q);

    if (_skillListTab === 'mine') return !SYSTEM_SKILLS.includes(s.name) && s.name.toLowerCase().includes(q);

    return s.name.toLowerCase().includes(q);

  });

  renderSkillCards(filtered);

}

function switchSkillTab(tab) {

  _skillListTab = tab;

  document.querySelectorAll('#sidebar .sb-tab').forEach(b =>

    b.classList.toggle('active', b.getAttribute('data-tab') === tab)

  );

  if (tab === 'knowledge') { showUnifiedKnowledge('knowledge'); return; }

  if (tab === 'journal') { showUnifiedKnowledge('journal'); return; }

  if (tab === 'lineage') { showUnifiedKnowledge('lineage'); return; }

  refreshSkillList();

}

// Export functions moved to skills_io.js (loaded before this file)

function importSkill() {

  let input = document.createElement('input');

  input.type = 'file'; input.accept = '.zip';

  input.onchange = async (e) => {

    let file = e.target.files[0];

    if (!file) return;

    addMsg('sys', '📥 Importing: ' + file.name + '...');

    setStatus('importing');

    let reader = new FileReader();

    reader.onload = async () => {

      let b64 = btoa(String.fromCharCode(...new Uint8Array(reader.result)));

      try {

        let r = await api('/api/skills/import-and-adapt', {

          method: 'POST',

          body: JSON.stringify({ zip: b64, model: _selectedModel })

        });

        let d = await r.json();

        addMsg('ai', d.reply);

        scrollMsgs();

        setStatus('imported: ' + d.imported);

        refreshSkillList();

      } catch (e) {

        addMsg('sys', '导入失败: ' + e.message);

        setStatus('error');

      }

    };

    reader.readAsArrayBuffer(file);

  };

  input.click();

}

function optimizeSkill(name) {

  var history = typeof buildChatHistory === 'function' ? buildChatHistory() : [];

  showChat();

  if (typeof clearChatMessages === 'function') clearChatMessages();

  addMsg('sys', '⚡ 优化模式: ' + name);

  setStatus('loading');

  setDot('blue');

  api('/api/skills/dispatch', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({

      message: '__optimize__:' + name,

      history: history.slice(-10),

      mode: 'create',

      model: _selectedModel,

      auto: _autoMode,

      session_id: _sessionId

    })

  }).then(r => {

    if (!r.ok) throw new Error('Server ' + r.status);

    return r.json();

  }).then(d => {

    if (!d.reply) { addMsg('sys', 'Error: ' + JSON.stringify(d)); return; }

    _sessionId = d.session_id || _sessionId;

    if (_sessionId) localStorage.setItem('sd_session', _sessionId);

    addMsg('ai', d.reply);

    scrollMsgs();

    setStatus('optimizing: ' + name);

    setDot('on');

    refreshSkillList();

  }).catch(e => {

    addMsg('sys', '优化请求失败: ' + e.message);

    setStatus('error');

    setDot('');

  });

}

// switchSettings/showSettings moved to settings.js — Alpine settingsView() component
