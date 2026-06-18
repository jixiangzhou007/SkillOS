/* skills.js — extracted from app.js */

function showDetail(name) {

  if (!name) { showChat(); return; }

  _currentSkill = name;

  document.getElementById('d-name').textContent = name;

  switchMainView('detail-view');
  document.getElementById('bar').style.display = 'none';

  updateMetaTabVisibility(name);
  switchTab('overview');

}

async function updateMetaTabVisibility(name) {
  var metaTab = document.getElementById('d-tab-meta');
  if (!metaTab) return;
  try {
    var r = await api('/api/skills/' + encodeURIComponent(name));
    if (!r.ok) { metaTab.style.display = 'none'; return; }
    var d = await r.json();
    metaTab.style.display = d.is_metaskill ? '' : 'none';
  } catch (e) {
    metaTab.style.display = 'none';
  }
}

function switchTab(t) {

  _currentTab = t;

  document.querySelectorAll('#detail-tabs .dt').forEach(b =>

    b.classList.toggle('active', b.getAttribute('data-tab') === t)

  );

  if (t === 'overview') loadOverview();

  else if (t === 'doc') loadDoc();

  else if (t === 'verify') loadVerify();

  else if (t === 'epistemic') loadEpistemic();

  else if (t === 'dna') loadDnaLineage();

  else if (t === 'official') loadOfficialBench();

  else if (t === 'meta') loadMeta();

  else if (t === 'evo') loadEvo();

  else if (t === 'kb') loadKB();

  else if (t === 'decisions') loadDecisions();

}

function dedupReasonLabel(reason) {
  if (reason === 'name') return '名称相似';
  if (reason === 'content') return '内容重叠';
  return reason || '';
}

function _kpi(label, val, color, hint) {
  return '<div style="flex:1;min-width:100px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;text-align:center">' +
    '<div style="font-size:22px;font-weight:700;color:' + color + '">' + val + '</div>' +
    '<div style="font-size:11px;color:var(--text2);margin-top:4px">' + label + '</div>' +
    '<div style="font-size:10px;color:var(--text3);margin-top:2px">' + (hint || '') + '</div></div>';
}

async function renderSimilarSkillsBanner(skillName) {
  try {
    let simR = await api('/api/skills/' + encodeURIComponent(skillName) + '/similar');
    if (!simR.ok) return '';
    let simD = await simR.json();
    if (!simD.similar || !simD.similar.length) return '';
    let h = '<div style="background:var(--surface2);border:1px solid var(--warn);border-radius:8px;padding:12px;margin-bottom:16px">';
    h += '<div style="font-size:12px;font-weight:600;color:var(--warn);margin-bottom:8px">⚠️ 相似技能（去重提示）</div>';
    simD.similar.forEach(function (s) {
      h += '<div style="font-size:12px;color:var(--text2);padding:4px 0;cursor:pointer" onclick="showDetail(' + JSON.stringify(s.name) + ')">' +
        escHtml(s.name) + ' · 相似度 ' + Math.round((s.score || 0) * 100) + '%（' + dedupReasonLabel(s.reason) + '）</div>';
    });
    h += '</div>';
    return h;
  } catch (e) {
    return '';
  }
}

async function loadOverview() {

  let el = document.getElementById('d-content');

  el.innerHTML = '<div style=\"color:var(--text3);padding:20px;text-align:center\">加载中...</div>';

  try {

    let[skillR,dnaR]=await Promise.all([

      api('/api/skills/'+encodeURIComponent(_currentSkill)),

      api('/api/skills/'+encodeURIComponent(_currentSkill)+'/dna-check').catch(()=>({json:()=>Promise.resolve({passed:0,total:6,checks:[],score:'0/6'})}))

    ]);

    let skill=await skillR.json(), dna=await dnaR.json();

    let dnaP=dna.passed||0, dnaC=dnaP>=5?'var(--accent)':dnaP>=3?'var(--warn)':'var(--err)';

    let sC=skill.avg_score>=4?'var(--accent)':skill.avg_score>=2?'var(--warn)':'var(--err)';

    let h='<div style=\"display:flex;gap:12px;margin-bottom:20px\">';

    h+=_kpi('DNA 合规',dna.score||'0/6',dnaC,'设计规范遵循度');

    h+=_kpi('技能版本','v'+skill.version,'var(--info)','迭代 '+skill.runs+' 次');

    h+=_kpi('验证得分',skill.avg_score+'/5',sC,'自动测试通过率');

    h+=_kpi('历史版本',String((skill.versions||[]).length),'var(--text2)','版本数量');

    h+='</div>';

    h += await renderSimilarSkillsBanner(_currentSkill);

    h+='<div style=\"background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:16px\">';

    h+='<div style=\"font-size:13px;font-weight:600;color:var(--text2);margin-bottom:12px\">DNA 设计规范合规检查</div>';

    if(dna.checks&&dna.checks.length>0){dna.checks.forEach(function(c){var icon=c.passed?'通过':'未过',color=c.passed?'var(--accent)':'var(--err)';h+='<div style=\"display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);font-size:12px\"><span style=\"color:'+color+';font-weight:700;min-width:36px;font-size:10px\">'+icon+'</span><span style=\"color:var(--text3);min-width:50px\">原则 '+c.principle+'</span><span style=\"color:'+color+';flex:1\">'+c.detail+'</span></div>'})}else{h+='<div style=\"color:var(--text3);font-size:12px\">暂无 DNA 合规数据</div>'}

    h+='</div>';

    h+='<div style=\"background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:16px\">';

    h+='<div style=\"font-size:13px;font-weight:600;color:var(--text2);margin-bottom:12px\">依赖项</div>';

    try{let r=await api('/api/skills/'+encodeURIComponent(_currentSkill)+'/kb').catch(()=>null);var deps=[];if(r){let kb=await r.json();if(kb.templates>0)deps.push(kb.templates+' 个参考模板');if(kb.facts>0)deps.push(kb.facts+' 条事实知识');if(kb.heuristics>0)deps.push(kb.heuristics+' 条启发规则');if(kb.constraints>0)deps.push(kb.constraints+' 条约束条件')}if(deps.length>0){h+='<div style=\"display:flex;flex-wrap:wrap;gap:6px\">';deps.forEach(function(d){h+='<span style=\"padding:5px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:16px;font-size:11px;color:var(--text2)\">'+d+'</span>'});h+='</div>'}else h+='<div style=\"color:var(--text3);font-size:12px\">无外部依赖，可独立使用</div>'}catch(e){h+='<div style=\"color:var(--text3);font-size:12px\">依赖信息暂不可用</div>'}

    h+='</div>';

    h+='<div style=\"display:flex;gap:8px;flex-wrap:wrap\">';

    h+='<button class=\"btn a\" style=\"font-size:12px;padding:8px 16px\" onclick=\"optimizeSkill(_currentSkill)\">优化技能</button>';

    h+='<button class=\"btn\" style=\"background:var(--surface2);border:1px solid var(--border);color:var(--text2);font-size:12px;padding:8px 16px\" onclick=\"runEvolutionOptimize(_currentSkill)\">MoE 优化</button>';

    h+='<button class=\"btn\" style=\"background:var(--surface2);border:1px solid var(--border);color:var(--text2);font-size:12px;padding:8px 16px\" onclick=\"exportSkillOpt(_currentSkill)\">导出 SkillOpt</button>';

    if (skill.is_metaskill) {
      h+='<button class=\"btn\" style=\"background:var(--info);border:1px solid var(--info);color:#fff;font-size:12px;padding:8px 16px\" onclick=\"runMetaSkill(_currentSkill)\">▶ 运行流水线</button>';
    }

    h+='<button class=\"btn\" style=\"background:var(--surface2);border:1px solid var(--border);color:var(--text2);font-size:12px;padding:8px 16px\" onclick=\"exportSkill()\">导出 Zip</button>';

    h+='<button class=\"btn\" style=\"background:var(--surface2);border:1px solid var(--border);color:var(--text2);font-size:12px;padding:8px 16px\" onclick=\"exportUniversal()\">通用格式导出</button>';

    try{var ws=JSON.parse(localStorage.getItem('sd_workspace')||'{}');if(!ws.tenant_id||ws.tenant_id.indexOf('personal:')===0){h+='<button class=\"btn\" style=\"background:var(--warn);border:1px solid var(--warn);color:#fff;font-size:12px;padding:8px 16px\" onclick=\"copySkillToOrg(_currentSkill)\">复制到公司</button>'}}catch(e){}

    h+='</div>';

    el.innerHTML=h;

  }catch(e){el.innerHTML='<div style=\"color:var(--err);padding:20px\">加载失败: '+e.message+'</div>'}

}

async function loadDoc() {

  let r = await api('/api/skills/' + encodeURIComponent(_currentSkill));

  let d = await r.json();

  document.getElementById('d-content').innerHTML =

    '<pre style="white-space:pre-wrap;font:12px monospace;color:var(--text)">' +

    escHtml(d.content || 'No content') + '</pre>';

}

async function loadVerify() {

  let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/traces');

  let traces = await r.json();

  let h = '<div style="margin-bottom:16px;display:flex;gap:8px">' +

    '<input id="verify-task" placeholder="输入测试任务…" style="flex:1;background:var(--srf);border:1px solid #222;border-radius:6px;padding:10px;color:var(--text);font-size:14px">' +

    '<button class="btn a" style="font-size:13px;padding:6px 14px" onclick="runVerify()">运行测试</button>' +

    '</div><div id="verify-result"></div>';

  if (traces.length) {

    h += '<div style="margin-top:16px;font-size:12px;color:var(--dim)">最近 Trace：</div>';

    h += traces.slice(0, 10).map(t => {

      let color = t.score >= 4 ? 'var(--accent)' : t.score >= 3 ? 'var(--warn)' : 'var(--err)';

      return '<div style="margin:4px 0;padding:8px;background:var(--srf);border-radius:4px;border-left:3px solid ' + color + '">' +

        '<b>Score ' + t.score + '/5</b> · ' + (t.timestamp || '').slice(0, 10) + '<br>' +

        '<span style="color:var(--dim);font-size:12px">' + escHtml(t.task || '').slice(0, 80) + '</span><br>' +

        '<span style="font-size:11px">' + escHtml(t.feedback || '').slice(0, 100) + '</span></div>';

    }).join('');

  }

  document.getElementById('d-content').innerHTML = h;

}

async function loadEpistemic() {
  let el = document.getElementById('d-content');
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载认识论状态...</div>';
  try {
    let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/epistemic/pending');
    let d = await r.json();
    let ep = d.epistemic_summary || {};
    let pending = d.pending_claims || [];
    let h = '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    h += _kpi('已验证', ep.verified || 0, 'var(--accent)', '已确认声明');
    h += _kpi('待确认', ep.pending || 0, 'var(--warn)', '经验/证据级');
    h += _kpi('总计', ep.total_claims || 0, 'var(--info)', '提取的声明数');
    h += '</div>';

    let simR = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/similar');
    let simD = await simR.json();
    if (simD.similar && simD.similar.length) {
      h += '<div style="background:var(--surface2);border:1px solid var(--warn);border-radius:8px;padding:12px;margin-bottom:16px">';
      h += '<div style="font-size:12px;font-weight:600;color:var(--warn);margin-bottom:8px">⚠️ 相似技能（去重提示）</div>';
      simD.similar.forEach(function (s) {
        h += '<div style="font-size:12px;color:var(--text2);padding:4px 0;cursor:pointer" onclick="showDetail(' + JSON.stringify(s.name) + ')">' +
          escHtml(s.name) + ' · 相似度 ' + Math.round((s.score || 0) * 100) + '%（' + dedupReasonLabel(s.reason) + '）</div>';
      });
      h += '</div>';
    }

    if (!pending.length) {
      h += '<div class="empty-state"><div class="icon">✅</div><div class="title">无待确认声明</div>';
      h += '<div class="hint">所有声明已验证，或尚未运行认识论提取。</div></div>';
      el.innerHTML = h;
      return;
    }

    h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">待确认声明</div>';
    h += '<div id="epistemic-pending-list">';
    pending.forEach(function (c, i) {
      h += '<label style="display:flex;gap:10px;align-items:flex-start;padding:10px;margin-bottom:6px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px">';
      h += '<input type="checkbox" class="ep-claim-cb" value="' + escHtml(c.claim_id) + '" checked style="margin-top:3px">';
      h += '<span><span style="color:var(--text3)">#' + (i + 1) + ' · ' + escHtml(c.level || '') + '</span><br>';
      h += escHtml((c.content || '').slice(0, 240)) + '</span></label>';
    });
    h += '</div>';
    h += '<div style="display:flex;gap:8px;margin-top:12px">';
    h += '<button class="btn a" style="font-size:12px;padding:8px 16px" onclick="confirmEpistemicSelected(false)">确认选中</button>';
    h += '<button class="btn" style="font-size:12px;padding:8px 16px;background:var(--surface2);border:1px solid var(--border);color:var(--text2)" onclick="confirmEpistemicSelected(true)">全部确认</button>';
    h += '</div>';
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>';
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
  var el = document.getElementById('d-content');
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载 DNA 血缘...</div>';
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

    var h = '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    h += _kpi('哲学 DNA', String(philo.length), 'var(--info)', '层 0 方法论');
    h += _kpi('领域 DNA', String(domain.length), 'var(--accent)', '层 1 模板');
    h += _kpi('版本过期', String(staleCount), staleCount ? 'var(--warn)' : 'var(--accent)', '需刷新血缘');
    h += '</div>';

    if (meta.domain_label || meta.methodology_label) {
      h += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">';
      if (meta.domain_label) h += '<span class="dna-tag">' + escHtml(meta.domain_label) + '</span>';
      if (meta.philosophical_dna_label) h += '<span class="dna-tag">' + escHtml(meta.philosophical_dna_label) + '</span>';
      if (meta.methodology_label) h += '<span class="dna-tag">' + escHtml(meta.methodology_label) + '</span>';
      (meta.bench_categories || []).forEach(function (c) {
        h += '<span class="dna-tag">' + escHtml(c) + '</span>';
      });
      h += '</div>';
    }

    if (lineage.conflicts && lineage.conflicts.length) {
      h += '<div class="dna-conflict"><div style="font-weight:600;color:var(--warn);margin-bottom:6px">⚠️ 方法论 / 领域冲突</div>';
      lineage.conflicts.forEach(function (c) {
        h += '<div style="margin-top:4px">' + escHtml(c) + '</div>';
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
        h += _dnaWeightBar(p.weight, 'var(--info)');
        h += '<span style="font-size:10px;color:var(--text3)">' + escHtml(p.id) + hint + '</span></div>';
      });
    } else {
      h += '<div style="color:var(--text3);font-size:12px">暂无哲学 DNA 检测记录</div>';
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
      h += '<div style="color:var(--text3);font-size:12px">暂无领域模板匹配</div>';
    }
    h += '</div>';

    if (dnaCheck && dnaCheck.dna_compliance) {
      var dc = dnaCheck.dna_compliance;
      var dcOk = dc.all_passed || (dc.passed >= 5);
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>DNA 合规</span><span class="dna-layer-badge">' + escHtml(dc.score || '') + '</span></div>';
      h += '<div style="font-size:12px;color:' + (dcOk ? 'var(--accent)' : 'var(--warn)') + ';margin-bottom:8px">';
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
      h += '<div style="font-size:12px;color:var(--text2)">';
      h += '通过 ' + (moe.passed ? '✓' : '✗');
      if (moe.confidence != null) h += ' · 置信度 ' + Math.round(moe.confidence * 100) + '%';
      if (moe.boost_rounds && moe.boost_rounds.length) h += ' · 补强 ' + moe.boost_rounds.length + ' 轮';
      h += '</div></div>';
    }

    if (smoke && smoke.suite && smoke.suite.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>域内烟测</span><span class="dna-layer-badge">Save Gate</span></div>';
      h += '<div style="font-size:12px;color:' + (smoke.smoke_pass ? 'var(--accent)' : 'var(--err)') + ';margin-bottom:8px">';
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
      h += '<div style="font-size:12px;color:' + (g.smoke_pass ? 'var(--accent)' : 'var(--err)') + '">';
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
      h += '<div style="font-size:11px;color:var(--text3);margin-bottom:12px">检测时间 ' + escHtml(lineage.detected_at) + '</div>';
    }

    h += '<div style="display:flex;gap:8px;flex-wrap:wrap">';
    h += '<button class="btn a" style="font-size:12px;padding:8px 16px" onclick="refreshDnaLineage()">刷新血缘版本</button>';
    if (staleCount) {
      h += '<span style="font-size:11px;color:var(--warn);align-self:center">有 ' + staleCount + ' 个领域模板版本落后于当前 DNA</span>';
    }
    h += '</div>';

    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>';
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
  var el = document.getElementById('d-content');
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载官方 SkillsBench…</div>';
  try {
    var r = await api('/api/bench/official/skills/' + encodeURIComponent(_currentSkill));
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var plan = d.plan || {};
    var h = '<div style="margin-bottom:12px;font-size:13px;color:var(--text2)">';
    h += '对接 <a href="https://github.com/benchflow-ai/skillsbench" target="_blank" rel="noopener" style="color:var(--accent)">官方 SkillsBench</a>（BenchFlow + Docker）。';
    h += ' 本地快速分为自建 88 题；此处为<strong>官方沙箱 pass rate</strong>评测计划。</div>';

    h += '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    h += _kpi('推荐 task', String((plan.suggested_official_tasks || []).length), 'var(--info)', '官方任务');
    h += _kpi('预设', String((plan.matching_presets || []).length), 'var(--accent)', '一键对比');
    var q8 = d.latest_quick8;
    if (q8 && q8.improvement_pct) {
      var q8color = String(q8.improvement_pct).indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)';
      h += _kpi('Quick8 Δ', escHtml(q8.improvement_pct), q8color, '自建8题');
    }
    if (q8 && q8.domain_improvement_pct) {
      var dcolor = String(q8.domain_improvement_pct).indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)';
      var dlabel = q8.domain_only || q8.mode === 'skill_domain_quick8' ? (q8.tasks || 1) + '题域内' : (q8.skills_injected || 0) + '题注入';
      h += _kpi('域内 Δ', escHtml(q8.domain_improvement_pct), dcolor, dlabel);
    }
    h += '</div>';

    if (q8) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>最近本地 Quick8</span></div>';
      h += '<div style="padding:10px;background:var(--surface2);border-radius:6px;font-size:12px">';
      h += '<div style="color:var(--text3);font-size:11px">' + escHtml(q8.file || '') + '</div>';
      h += '有技能 <b>' + escHtml(String(q8.with_skill_score)) + '/' + escHtml(String(q8.max_score || q8.domain_max_score || (q8.tasks || 8) * 100)) + '</b> [' + escHtml(q8.with_skill_grade || '') + ']';
      h += ' · 无技能 ' + escHtml(String(q8.without_skill_score)) + ' · Δ <b style="color:' + (String(q8.improvement_pct || '').indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)') + '">' + escHtml(q8.improvement_pct || '') + '</b>';
      if (q8.skills_injected != null) h += '<div style="margin-top:6px;color:var(--text2)">技能注入 ' + q8.skills_injected + '/' + (q8.tasks || 8) + ' 题</div>';
      if (q8.domain_improvement_pct) h += '<div style="margin-top:4px;color:var(--text2)">域内提升 <b>' + escHtml(q8.domain_improvement_pct) + '</b>' + (q8.harm_tasks && q8.harm_tasks.length ? ' · ⚠伤害题 ' + escHtml(q8.harm_tasks.join(', ')) : '') + '</div>';
      if (q8.task_ids && q8.task_ids.length) {
        h += '<div style="margin-top:6px;font-size:11px;color:var(--text3)">题目: ' + q8.task_ids.map(function (id) { return '<code>' + escHtml(id) + '</code>'; }).join(' ') + '</div>';
      }
      if (q8.per_task && q8.per_task.length) {
        h += '<table style="width:100%;font-size:10px;margin-top:8px;border-collapse:collapse">';
        h += '<tr style="color:var(--text3)"><th style="text-align:left;padding:2px">题目</th><th>有</th><th>无</th><th>注入</th></tr>';
        q8.per_task.forEach(function (pt) {
          var delta = (pt.with_score || 0) - (pt.without_score || 0);
          var dc = delta > 0 ? 'var(--accent)' : (delta < 0 ? 'var(--err)' : 'var(--text3)');
          h += '<tr><td style="padding:2px"><code>' + escHtml(pt.task_id) + '</code></td>';
          h += '<td style="text-align:center">' + pt.with_score + '</td><td style="text-align:center">' + pt.without_score + '</td>';
          h += '<td style="text-align:center;color:' + dc + '">' + (pt.skill_used ? '✓' : '—') + '</td></tr>';
        });
        h += '</table>';
      }
      h += '<pre style="margin-top:8px;padding:8px;background:var(--surface);border-radius:6px;font-size:11px;overflow:auto">python scripts/run_new3skills_bench_quick8.py</pre>';
      h += '<button class="btn btn-sm" style="margin-top:8px" onclick="runLocalQuick8()">运行 Quick8 评测</button>';
      h += '<button class="btn btn-sm" style="margin-top:8px;margin-left:6px" onclick="runLocalQuick8(true)">域内 Quick8</button>';
      h += '<span id="local-quick8-status" style="margin-left:8px;font-size:11px;color:var(--text3)"></span>';
      h += '</div></div>';
    } else {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>本地 Quick8</span></div>';
      h += '<div style="padding:10px;background:var(--surface2);border-radius:6px;font-size:12px;color:var(--text2)">';
      h += '尚未运行自建 8 题评测。';
      h += '<button class="btn btn-sm" style="margin-left:8px" onclick="runLocalQuick8()">运行 Quick8</button>';
      h += '<button class="btn btn-sm" style="margin-left:6px" onclick="runLocalQuick8(true)">域内</button>';
      h += '<span id="local-quick8-status" style="margin-left:8px;font-size:11px;color:var(--text3)"></span>';
      h += '</div></div>';
    }

    var hist = d.quick8_history || [];
    if (hist.length > 1) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>Quick8 历史趋势</span></div>';
      h += '<table style="width:100%;font-size:11px;border-collapse:collapse;margin-top:6px">';
      h += '<tr style="color:var(--text3)"><th style="text-align:left;padding:4px">时间</th><th>Δ</th><th>域内</th><th>注入</th></tr>';
      hist.slice(0, 6).forEach(function (row) {
        var ts = row.timestamp ? new Date(row.timestamp * 1000).toLocaleString() : '';
        var pct = row.improvement_pct || '';
        var dpct = row.domain_improvement_pct || '';
        var col = String(pct).indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)';
        var dcol = String(dpct).indexOf('-') === 0 ? 'var(--err)' : 'var(--accent)';
        h += '<tr><td style="padding:4px;color:var(--text3)">' + escHtml(ts) + '</td>';
        h += '<td style="text-align:center;color:' + col + '"><b>' + escHtml(pct) + '</b></td>';
        h += '<td style="text-align:center;color:' + dcol + '">' + escHtml(dpct || '—') + '</td>';
        h += '<td style="text-align:center">' + escHtml(String(row.skills_injected != null ? row.skills_injected : '-')) + '/' + escHtml(String(row.tasks || 8)) + '</td></tr>';
      });
      h += '</table></div>';
    }

    if (plan.windows_note) {
      h += '<div class="dna-conflict" style="margin-bottom:12px">💻 ' + escHtml(plan.windows_note) + '</div>';
    }

    if (plan.suggested_official_tasks && plan.suggested_official_tasks.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>推荐官方 Task</span></div><ul style="margin:8px 0 0 18px;font-size:12px;color:var(--text2)">';
      plan.suggested_official_tasks.forEach(function (tid) {
        h += '<li><code>' + escHtml(tid) + '</code></li>';
      });
      h += '</ul></div>';
    }

    if (plan.matching_presets && plan.matching_presets.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>Agent 对比预设</span></div>';
      plan.matching_presets.forEach(function (p) {
        h += '<div class="dna-domain-card" style="margin-top:8px"><div style="font-weight:600;font-size:13px">' + escHtml(p.id) + '</div>';
        h += '<div style="font-size:11px;color:var(--text3);margin:4px 0">' + escHtml(p.description || '') + '</div>';
        h += '<div style="font-size:11px;color:var(--text2)">task: <code>' + escHtml(p.task) + '</code></div>';
        h += '<pre style="margin-top:8px;padding:8px;background:var(--surface2);border-radius:6px;font-size:11px;overflow:auto">python scripts/run_official_skill_compare.py --preset ' + escHtml(p.id) + '</pre></div>';
      });
      h += '<div style="margin-top:10px"><button class="btn btn-sm" onclick="triggerOfficialCi()">请求 GitHub CI 评测</button>';
      h += '<span id="official-ci-status" style="margin-left:8px;font-size:11px;color:var(--text3)"></span></div>';
      h += '</div>';
    }

    if (plan.commands) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>CLI 命令（Linux / CI）</span></div>';
      Object.keys(plan.commands).forEach(function (k) {
        if (!plan.commands[k]) return;
        h += '<div style="margin-top:8px;font-size:11px;color:var(--text3)">' + escHtml(k) + '</div>';
        h += '<pre style="padding:8px;background:var(--surface2);border-radius:6px;font-size:11px;overflow:auto">' + escHtml(plan.commands[k]) + '</pre>';
      });
      h += '</div>';
    }

    var latest = d.latest_official || {};
    var latestCompare = (latest.compare || []).slice(0, 2);
    var latestSmoke = (latest.smoke || []).slice(0, 1);
    if (latestCompare.length || latestSmoke.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>最近官方 CI 结果</span></div>';
      latestCompare.forEach(function (item) {
        var cmp = item.comparison || {};
        h += '<div style="margin-top:8px;padding:10px;background:var(--surface2);border-radius:6px;font-size:12px">';
        h += '<div style="color:var(--text3);font-size:11px">' + escHtml(item._file || '') + '</div>';
        if (cmp.improvement) h += 'Agent 对比 Δ: <b>' + escHtml(cmp.improvement) + '</b>';
        if (item.preset) h += ' · preset: <code>' + escHtml(item.preset) + '</code>';
        h += '</div>';
      });
      latestSmoke.forEach(function (item) {
        h += '<div style="margin-top:8px;padding:10px;background:var(--surface2);border-radius:6px;font-size:12px">';
        h += '<div style="color:var(--text3);font-size:11px">' + escHtml(item._file || '') + ' · oracle smoke</div>';
        if (item.reward != null) h += 'reward: <b>' + escHtml(String(item.reward)) + '</b>';
        h += '</div>';
      });
      h += '</div>';
    }

    var related = d.related_benchmarks || [];
    if (related.length) {
      h += '<div class="dna-layer"><div class="dna-layer-title"><span>本地历史评测</span></div>';
      related.forEach(function (item) {
        var data = item.data || {};
        h += '<div style="margin-top:8px;padding:10px;background:var(--surface2);border-radius:6px;font-size:12px">';
        h += '<div style="color:var(--text3);font-size:11px">' + escHtml(item.file) + '</div>';
        if (data.comparison) {
          h += '官方对比 Δ: <b>' + escHtml(data.comparison.improvement || '') + '</b>';
        } else if (data.task_compare) {
          data.task_compare.forEach(function (tc) {
            if (tc.label || tc.skill === _currentSkill || (tc.skill && tc.skill.indexOf(_currentSkill) >= 0)) {
              h += '<div>' + escHtml(tc.label || tc.skill || '') + ' · Δ ' + escHtml(tc.improvement_pct || '') + '</div>';
            }
          });
        } else if (data.structural) {
          data.structural.forEach(function (s) {
            if (s.skill === _currentSkill) {
              h += '结构分 ' + s.total + '/100 [' + escHtml(s.grade || '') + ']';
            }
          });
        }
        h += '</div>';
      });
      h += '</div>';
    } else {
      h += '<div style="margin-top:16px;font-size:12px;color:var(--text3)">暂无本地官方/快速评测记录。配置 GitHub <code>DEEPSEEK_API_KEY</code> 后可在 Actions 运行 Official SkillsBench。</div>';
    }

    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>';
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
    loadBenchDashboard();
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
  var el = document.getElementById('d-content');
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载 MetaSkill 流水线…</div>';
  try {
    var r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/metaskill');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var h = '<div style="margin-bottom:12px"><div style="font-weight:600;font-size:15px">🔗 ' + escHtml(d.name || _currentSkill) + '</div>';
    h += '<div style="font-size:12px;color:var(--text3);margin-top:4px">' + escHtml(d.goal || '') + '</div></div>';
    h += '<div style="font-size:12px;margin-bottom:12px">风险等级: <b>' + escHtml(d.risk_level || 'low') + '</b> · ';
    h += d.valid ? '<span style="color:var(--accent)">✓ 结构有效</span>' : '<span style="color:var(--err)">✗ ' + escHtml(d.validation_message || '') + '</span>';
    h += '</div>';

    var dagId = '';
    if (d.mermaid) {
      dagId = 'meta-dag-' + Date.now();
      h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">流水线 DAG</div>';
      h += '<div style="overflow:auto;background:var(--srf);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:16px">';
      h += '<pre class="mermaid" id="' + dagId + '" style="margin:0;background:transparent"></pre></div>';
    }

    h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">流水线步骤</div>';
    if (d.steps && d.steps.length) {
      d.steps.forEach(function (s, i) {
        h += '<div style="padding:10px;margin-bottom:6px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;font-size:12px">';
        h += '<div style="font-weight:600">' + (i + 1) + '. ' + escHtml(s.name) + ' → ' + escHtml(s.skill_name) + '</div>';
        if (s.depends_on && s.depends_on.length) {
          h += '<div style="color:var(--text3);margin-top:4px">依赖: ' + escHtml(s.depends_on.join(', ')) + '</div>';
        }
        if (s.output_key) h += '<div style="color:var(--text3)">输出键: ' + escHtml(s.output_key) + '</div>';
        h += '</div>';
      });
    } else {
      h += '<div style="color:var(--text3);font-size:12px">无步骤</div>';
    }
    h += '<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">';
    h += '<button class="btn a" style="font-size:12px;padding:8px 16px" onclick="runMetaSkill(_currentSkill, false)">▶ 完整运行</button>';
    h += '<button class="btn" style="font-size:12px;padding:8px 16px;background:var(--surface2);border:1px solid var(--border);color:var(--text2)" onclick="runMetaSkill(_currentSkill, true)">试运行（无 LLM）</button>';
    h += '</div>';
    h += '<div id="meta-run-result" style="margin-top:16px"></div>';
    el.innerHTML = h;
    if (d.mermaid && typeof renderMermaidInto === 'function') {
      setTimeout(function () { renderMermaidInto(dagId, d.mermaid); }, 30);
    }
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);padding:20px">MetaSkill 加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function runMetaSkill(name, dryRun) {
  if (!name) return;
  if (dryRun === undefined) dryRun = true;
  var resultEl = document.getElementById('meta-run-result');
  if (resultEl) resultEl.innerHTML = '<div style="color:var(--text3);font-size:12px">运行中…</div>';
  toast(dryRun ? 'MetaSkill 试运行…' : 'MetaSkill 完整运行…');
  try {
    var r = await api('/api/skills/' + encodeURIComponent(name) + '/metaskill/run', {
      method: 'POST',
      body: JSON.stringify({ user_input: '', dry_run: !!dryRun }),
    });
    var d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'run failed');
    var h = '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:12px">';
    h += '<div style="font-weight:600;margin-bottom:8px">' + (d.success ? '✅ 运行成功' : '⚠ 运行未完成') + '</div>';
    if (d.trace && d.trace.length) {
      h += '<pre style="white-space:pre-wrap;font:11px monospace;color:var(--text2);margin:0 0 10px">' + escHtml(d.trace.join('\n')) + '</pre>';
    }
    if (d.errors && d.errors.length) {
      h += '<div style="color:var(--err)">' + escHtml(d.errors.join('; ')) + '</div>';
    }
    h += '</div>';
    if (resultEl) resultEl.innerHTML = h;
    else toast(d.success ? 'MetaSkill 运行完成' : 'MetaSkill 运行失败', d.success ? 'success' : 'error');
  } catch (e) {
    if (resultEl) resultEl.innerHTML = '<div style="color:var(--err);font-size:12px">' + escHtml(e.message) + '</div>';
    toast('MetaSkill 运行失败: ' + e.message, 'error');
  }
}

async function loadEvo() {

  let el = document.getElementById('d-content');
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载进化状态…</div>';

  try {
    let [stateR, routeR, tracesR] = await Promise.all([
      api('/api/evolution/' + encodeURIComponent(_currentSkill) + '/state'),
      api('/api/evolution/' + encodeURIComponent(_currentSkill) + '/route', { method: 'POST' }),
      api('/api/skills/' + encodeURIComponent(_currentSkill) + '/traces'),
    ]);

    let state = stateR.ok ? await stateR.json() : {};
    let route = routeR.ok ? await routeR.json() : {};
    let traces = tracesR.ok ? await tracesR.json() : [];

    let scores = traces.map(t => t.score).filter(s => s > 0);
    let avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 'N/A';
    let routing = route.routing || {};

    let h = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px">';
    h += _kpi('Trace 数', state.trace_count || 0, 'var(--info)', '执行记录');
    h += _kpi('平均分', avg + '/5', avg >= 3 ? 'var(--accent)' : 'var(--err)', '验证得分');
    h += _kpi('成熟度', (state.maturity_days || 0) + ' 天', 'var(--text2)', '技能年龄');
    h += _kpi('推荐专家', routing.primary || state.recommended_expert || '—', 'var(--warn)', 'MoE 路由');
    h += '</div>';

    if (routing.reason) {
      h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:16px;font-size:12px;color:var(--text2)">';
      h += '<div style="font-weight:600;margin-bottom:6px">MoE 路由 · 置信度 ' + Math.round((routing.confidence || 0) * 100) + '%</div>';
      h += escHtml(routing.reason);
      h += '</div>';
    }

    h += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">';
    h += '<button class="btn a" style="font-size:12px;padding:8px 16px" onclick="runEvolutionOptimize(_currentSkill)">⚡ MoE 优化一轮</button>';
    h += '<button class="btn" style="font-size:12px;padding:8px 16px;background:var(--surface2);border:1px solid var(--border);color:var(--text2)" onclick="exportSkillOpt(_currentSkill)">📦 导出 SkillOpt</button>';
    h += '<button class="btn" style="font-size:12px;padding:8px 16px;background:var(--surface2);border:1px solid var(--border);color:var(--text2)" onclick="runSkillOptCli(_currentSkill)">🖥 SkillOpt CLI</button>';
    h += '</div>';

    h += '<div id="evo-cli-block"></div>';

    h += '<div id="evo-result" style="margin-bottom:16px"></div>';

    if (traces.length) {
      h += '<div style="font-size:12px;color:var(--dim);margin-bottom:8px">最近 Trace</div>';
      h += traces.slice(0, 8).map(t => {
        let color = t.score >= 4 ? 'var(--accent)' : t.score >= 3 ? 'var(--warn)' : 'var(--err)';
        return '<div style="margin:4px 0;padding:8px;background:var(--srf);border-radius:4px;border-left:3px solid ' + color + '">' +
          '<b>Score ' + t.score + '/5</b> · ' + escHtml((t.timestamp || '').slice(0, 10)) + '<br>' +
          '<span style="color:var(--dim);font-size:12px">' + escHtml((t.task || '').slice(0, 80)) + '</span></div>';
      }).join('');
    } else {
      h += '<div style="color:var(--text3);font-size:12px">暂无 Trace — 在「验证」Tab 运行测试后可触发 SkillOpt 优化。</div>';
    }

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
    el.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

async function runEvolutionOptimize(name) {
  if (!name) return;
  var resultEl = document.getElementById('evo-result');
  if (resultEl) resultEl.innerHTML = '<div style="color:var(--text3);font-size:12px">MoE 优化中…</div>';
  toast('MoE 优化运行中…');
  try {
    var r = await api('/api/evolution/' + encodeURIComponent(name) + '/optimize', {
      method: 'POST',
      body: JSON.stringify({ feedback: '' }),
    });
    var d = await r.json();
    var msg = (d.accepted ? '✅ 优化已接受' : '⚠ 未接受变更') + ' · 专家 ' + (d.expert || '—') + ' · ' + escHtml(d.detail || d.improvement || '');
    if (resultEl) resultEl.innerHTML = '<div style="font-size:12px;padding:10px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">' + msg + '</div>';
    toast(d.accepted ? '优化已接受' : '优化未接受变更', d.accepted ? 'success' : 'warn');
    loadEvo();
  } catch (e) {
    if (resultEl) resultEl.innerHTML = '<div style="color:var(--err);font-size:12px">' + escHtml(e.message) + '</div>';
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
    if (cliEl) cliEl.innerHTML = '<div style="font-size:12px;padding:10px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">' + msg + '</div>';
    toast(d.ok ? 'CLI dry-run 完成' : 'CLI 失败', d.ok ? 'success' : 'error');
  } catch (e) {
    toast('CLI 失败: ' + e.message, 'error');
  }
}

async function loadKB() {

  let h = '<div style="display:flex;gap:8px;margin-bottom:12px">' +

    '<button class="btn a" style="font-size:12px;padding:5px 14px" onclick="compareTemplate()">📄 对比模板</button>' +

    '<input type="file" id="tpl-upload" style="display:none" accept=".txt,.md" onchange="uploadTemplate(event)">' +

    '</div>' +

    '<div style="margin-bottom:12px"><label style="color:var(--text3);font-size:11px">添加到知识库</label>' +

    '<div style="display:flex;gap:8px"><input id="kb-url" placeholder="粘贴 URL…" style="flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px;color:var(--text);font-size:13px">' +

    '<button class="btn ghost" style="font-size:12px" onclick="addToKB()">添加 URL</button></div></div>' +

    '<div id="kb-status" style="font-size:12px;color:var(--text3)">在对话中发送 URL，或使用「对比模板」检查文档与已存模板的差异。</div>';

  document.getElementById('d-content').innerHTML = h;

}

async function loadDecisions() {

  let el = document.getElementById('d-content');

  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载决策历史…</div>';

  try {

    let r = await api('/api/skills/' + encodeURIComponent(_currentSkill) + '/decisions');

    let d = await r.json();

    let decisions = d.decisions || [];

    if (!decisions.length) {

      el.innerHTML = '<div class="empty-state"><div class="icon">🧠</div><div class="title">暂无决策记录</div><div class="hint">技能优化轮次完成后会在此显示决策历史，记录「为什么改」而不仅是「改了什么」。</div></div>';

      return;

    }

    let h = '<div style="font-size:13px;color:var(--text3);margin-bottom:12px">' + decisions.length + ' decision records — the WHY chain</div>';

    decisions.reverse().forEach(r => {

      let icon = {accepted:'✅', rejected:'❌', partially_accepted:'⚠️'}[r.outcome] || '❓';

      let oc = r.outcome==='accepted'?'var(--accent)':r.outcome==='rejected'?'var(--err)':'var(--warn)';

      h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;border-left:3px solid ' + oc + '">';

      h += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">';

      h += '<span style="font-weight:600;color:var(--text)">' + icon + ' Round ' + r.round_num + '</span>';

      h += '<span style="font-size:10px;color:var(--text3)">v' + r.version_from + '→v' + r.version_to + '</span>';

      h += '<span style="font-size:10px;color:' + oc + '">' + r.outcome + '</span>';

      h += '</div>';

      h += '<div style="font-size:12px;color:var(--text);margin-bottom:4px"><b>诊断:</b> ' + escHtml((r.diagnosis||'').slice(0, 200)) + '</div>';

      h += '<div style="font-size:12px;color:var(--text2)"><b>结果:</b> ' + escHtml((r.outcome_detail||'').slice(0, 200)) + '</div>';

      if (r.candidate_revisions && r.candidate_revisions.length) {

        h += '<div style="margin-top:4px;font-size:11px;color:var(--text3)">修改: ' + r.candidate_revisions.map(function(e){return e.type+' '+e.detail;}).join(', ').slice(0, 150) + '</div>';

      }

      if (r.rejected_alternatives && r.rejected_alternatives.length) {

        h += '<div style="margin-top:4px;font-size:11px;color:var(--err)">拒绝的方案: ' + r.rejected_alternatives.join('; ').slice(0, 150) + '</div>';

      }

      if (r.evaluation_evidence && r.evaluation_evidence.old_score !== undefined) {

        h += '<div style="margin-top:4px;font-size:10px;color:var(--text3)">评估: ' + r.evaluation_evidence.old_score + '→' + r.evaluation_evidence.new_score + ' (执行:' + r.evaluation_evidence.old_execution + '→' + r.evaluation_evidence.new_execution + ' 审计:' + r.evaluation_evidence.old_audit + '→' + r.evaluation_evidence.new_audit + ')</div>';

      }

      h += '</div>';

    });

    el.innerHTML = h;

  } catch(e) { el.innerHTML = '<div style="color:var(--err)">Failed to load: ' + e.message + '</div>'; }

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
      if (el) el.innerHTML = '<pre style="white-space:pre-wrap;font-size:12px;color:var(--text)">' + escHtml(JSON.stringify(d, null, 2)) + '</pre>';
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

  btn.className = 'btn a'; btn.textContent = '对比'; btn.style.cssText = 'font-size:12px;padding:5px 14px';

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

      document.getElementById('kb-status').innerHTML = '<pre style=\"white-space:pre-wrap;font-size:12px;color:var(--text)\">' + JSON.stringify(d,null,2) + '</pre>';

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
      h += '<div style="display:flex;justify-content:space-between;gap:6px;margin:3px 0;cursor:pointer" onclick="showDetail(' + JSON.stringify(row.skill) + ');switchTab(\'official\')">';
      h += '<span style="color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px">' + escHtml(row.skill) + '</span>';
      h += '<span style="color:' + col + ';flex-shrink:0">' + escHtml(pct) + '</span></div>';
    });
    el.innerHTML = h;
  } catch (e) {
    el.textContent = '评测概览不可用';
  }
}

function refreshSkillList() {

  loadBenchDashboard();

  api('/api/skills/').then(r => r.json()).then(skills => {

    _allSkillsCache = skills;

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
        let metaLine = 'v' + s.version + ' · ' + s.avg_score + '/5';

        return '<div class="skill-tree-node">' +

        '<div class="tree-row" data-tree="' + treeId + '" data-skill="' + s.name + '" onclick="toggleTreeNode(this.dataset.tree)">' +

        '<span class="tree-toggle" id="tgl-' + treeId + '">▸</span>' +

        '<span class="health ' + health + '"></span>' +

        '<span class="tree-name">' + icon + s.name.replace('[Meta] ', '') + '</span>' +

        '<span class="tree-meta">' + metaLine + '</span>' +

        (_skillListTab === 'mine' ? '<button class="opt-btn" style="margin-left:auto" onclick="event.stopPropagation();optimizeSkill(this.dataset.skill)" data-skill="' + s.name + '">⚡</button>' : '') +

        '</div>' +

        '<div class="tree-children" id="' + treeId + '">' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="showDetail(this.dataset.skill)">📄 SKILL.md</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill);switchTab(\'kb\')">📚 KB</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill);switchTab(\'verify\')">🧪 验证</div>' +

        '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill);switchTab(\'evo\')">🔄 进化</div>' +

        (isMeta ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showDetail(this.dataset.skill);switchTab(\'meta\')">🔗 流水线</div>' : '') +

        (isMeta ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();runMetaSkill(this.dataset.skill)">▶ Run</div>' : '') +

        (_skillListTab === 'mine' ? '<div class="tree-child" data-skill="' + s.name + '" onclick="event.stopPropagation();showPublishForm(this.dataset.skill)" style="color:var(--warn);font-weight:600">📡 发布到市场</div>' : '') +

        '</div></div>';

      }).join('')

      || '<div class="empty-state"><div class="icon">📁</div><div class="title">' +

        (_skillListTab === 'mine' ? 'No skills yet' : 'System skills') +

        '</div><div class="hint">' +

        (_skillListTab === 'mine' ? 'Create one in Create mode or paste a URL' : 'Agent skills appear here') +

        '</div></div>';

    document.getElementById('skill-count').textContent = skills.length;

}

function toggleTreeNode(id) {

  let el = document.getElementById(id);

  let tgl = document.getElementById('tgl-' + id);

  if (!el || !tgl) return;

  let open = el.classList.toggle('open');

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

  if (tab === 'knowledge') { showKnowledgeView(); return; }

  if (tab === 'journal') { showJournalView(); return; }

  if (tab === 'lineage') { showLineageView(); return; }

  refreshSkillList();

}

function exportSkill() {
  downloadSkillExportZip(_currentSkill);
}

async function downloadSkillExportZip(name) {
  if (!name) return;
  var url = '/api/skills/' + encodeURIComponent(name) + '/export/zip';
  try {
    var r = await api(url);
    if (!r.ok) {
      var body = await r.json().catch(function() { return {}; });
      toast(typeof body.detail === 'string' ? body.detail : '导出失败', 'error');
      return;
    }
    var blob = await r.blob();
    var disp = r.headers.get('Content-Disposition') || '';
    var m = disp.match(/filename="([^"]+)"/);
    var filename = (m && m[1]) || (name + '-skill.zip');
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    toast('已导出安装包: ' + filename);
  } catch (e) {
    toast('导出失败: ' + e.message, 'error');
  }
}

function exportMarkdown() {
  downloadSkillExport(_currentSkill, 'markdown');
}

function exportUniversal() {
  downloadSkillExport(_currentSkill, 'universal');
}

async function downloadSkillExport(name, format) {
  if (!name) return;
  format = format || 'markdown';
  var url = '/api/skills/' + encodeURIComponent(name) + '/export';
  if (format === 'universal') url += '?format=universal';
  try {
    var r = await api(url);
    if (!r.ok) {
      var body = await r.json().catch(function() { return {}; });
      toast(typeof body.detail === 'string' ? body.detail : '导出失败', 'error');
      return;
    }
    var d = await r.json();
    var filename, content, mime;
    if (format === 'universal') {
      filename = name + '.json';
      content = JSON.stringify(d, null, 2);
      mime = 'application/json';
    } else {
      filename = (d.portable_slug || name) + '-SKILL.md';
      content = d.portable_content || d.content || '';
      mime = 'text/markdown';
    }
    var blob = new Blob([content], { type: mime });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    toast('已导出: ' + filename);
  } catch (e) {
    toast('导出失败: ' + e.message, 'error');
  }
}

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

  let history = [];

  document.querySelectorAll('#msgs .msg.user, #msgs .msg.ai').forEach(el => {

    let role = el.classList.contains('user') ? 'user' : 'assistant';

    let txt = el.textContent.trim();

    if (txt) history.push({ role, content: txt });

  });

  showChat();

  document.getElementById('msgs').innerHTML = '';

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

function switchSettings(t) {

  _settingsTab = t;

  document.querySelectorAll('#settings-view .tab').forEach(b =>

    b.classList.toggle('active', b.getAttribute('data-tab') === t)

  );

  let el = document.getElementById('s-content');

  if (t === 'model') loadModelSettings(el);

  else if (t === 'usage') loadUsageSettings(el);

  else if (t === 'skills') loadSkillSettings(el);

  else if (t === 'voice') loadVoiceSettings(el);

}


function showSettings() {
  switchMainView("settings-view");
  document.getElementById("bar").style.display = "none";
  switchSettings("model");
}
