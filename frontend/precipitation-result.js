/* precipitation-result.js — Verified Skill 完成态卡片 + Trust Tier（三路径共用） */

function _escAttr(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;');
}

function _epFromPayload(opts) {
  return opts.epistemic_summary || opts.epistemic || {};
}

function _resolveTrustTier(opts, ep) {
  var tier = opts.trust_tier || ep.trust_tier || '';
  var gates = opts.gates || ep.gates || null;
  if (!tier && gates) {
    var epOk = gates.epistemic && gates.epistemic.passed;
    var outOk = gates.outcome && gates.outcome.passed;
    tier = (epOk && outOk) ? 'verified' : 'provisional';
  }
  if (!tier) {
    // Legacy fallback: never claim verified without outcome signal
    var sg = ep.save_gate || (ep.bench_quality && ep.bench_quality.save_gate) || {};
    var smokeOk = sg.smoke_pass === true;
    var hasVerified = (ep.verified || 0) >= 1;
    if (smokeOk && hasVerified) tier = 'verified';
    else tier = 'provisional';
  }
  return { trust_tier: tier, gates: gates };
}

function _sourceLabel(kind, source) {
  if (source) {
    if (source.indexOf('file://') === 0) return '文件 · ' + source.replace('file://', '');
    if (source.indexOf('http') === 0) return '链接 · ' + source.slice(0, 72) + (source.length > 72 ? '…' : '');
    return source.slice(0, 80);
  }
  if (kind === 'file') return '本地上传';
  if (kind === 'url') return '网页链接';
  if (kind === 'conversation') return '对话萃取';
  return '未知来源';
}

function normalizePrecipitationPayload(opts) {
  opts = opts || {};
  var ep = _epFromPayload(opts);
  var name = opts.skill_name || opts.skill_saved || '';
  var slug = ep.portable_slug || opts.portable_slug || '';
  var installPaths = ep.install_paths || opts.install_paths || {};
  if ((!installPaths.cursor) && slug && typeof buildInstallPaths === 'function') {
    installPaths = buildInstallPaths(slug);
  }
  var cursorPath = installPaths.cursor || (slug ? '~/.cursor/skills/' + slug + '/' : '');

  var moe = null;
  var moeObj = ep.moe_evaluation || opts.moe_evaluation || (ep.bench_quality && ep.bench_quality.moe);
  if (moeObj && moeObj.overall_score != null) moe = moeObj.overall_score;

  var trust = _resolveTrustTier(opts, ep);
  var evidence = opts.evidence || ep.evidence || null;
  var outG = (trust.gates && trust.gates.outcome) || {};
  return {
    skill_name: name,
    source: opts.source || ep.source || '',
    source_kind: opts.source_kind || ep.source_type || '',
    verified: ep.verified != null ? ep.verified : 0,
    pending: ep.pending != null ? ep.pending : 0,
    total_claims: ep.total_claims != null ? ep.total_claims : 0,
    errors: ep.errors != null ? ep.errors : 0,
    moe: moe,
    slug: slug,
    cursor_path: cursorPath,
    zip_url: opts.export_zip_url || (name ? '/api/skills/' + encodeURIComponent(name) + '/export/zip' : ''),
    variant: opts.variant || 'skill',
    digest_title: opts.digest_title || opts.title || '',
    trust_tier: trust.trust_tier,
    gates: trust.gates,
    trust_reasons: opts.trust_reasons || ep.trust_reasons || [],
    evidence: evidence,
    smoke_tasks: (evidence && evidence.outcome && evidence.outcome.tasks) || outG.tasks || [],
    min_with_score: outG.min_with_score,
  };
}

function _prActionBtn(label, action, extra, cls) {
  extra = extra || {};
  var html = '<button type="button" class="' + (cls || 'btn-secondary btn-sm') + '" data-pr-action="' + _escAttr(action) + '"';
  if (extra.skill) html += ' data-pr-skill="' + _escAttr(extra.skill) + '"';
  if (extra.path) html += ' data-pr-path="' + _escAttr(extra.path) + '"';
  if (extra.url) html += ' data-pr-url="' + _escAttr(extra.url) + '"';
  if (extra.tab) html += ' data-pr-tab="' + _escAttr(extra.tab) + '"';
  html += '>' + (typeof escHtml === 'function' ? escHtml(label) : label) + '</button>';
  return html;
}

function _tierTitle(tier) {
  if (tier === 'verified') return 'Verified Skill 已出师';
  if (tier === 'draft') return 'Draft · 萃取中';
  return 'Provisional Skill 已沉淀';
}

function _tierBadgeClass(tier) {
  if (tier === 'verified') return 'trust-tier trust-tier-verified';
  if (tier === 'draft') return 'trust-tier trust-tier-draft';
  return 'trust-tier trust-tier-provisional';
}

function _tierBadgeLabel(tier) {
  if (tier === 'verified') return 'Verified';
  if (tier === 'draft') return 'Draft';
  return 'Provisional';
}

function renderTrustLine(payload) {
  var v = payload.verified || 0;
  var p = payload.pending || 0;
  var tier = payload.trust_tier || 'draft';
  var gates = payload.gates || {};
  var html = '<div class="pr-trust">';
  html += '<span class="' + _tierBadgeClass(tier) + '">' + _tierBadgeLabel(tier) + '</span>';
  html += '<span class="trust-badge trust-verified">声明已验证 ' + v + '</span>';
  if (p > 0) {
    html += '<span class="trust-badge trust-pending">待审 ' + p + '</span>';
  }
  var epG = gates.epistemic || {};
  var outG = gates.outcome || {};
  if (gates.epistemic || gates.outcome) {
    html += '<span class="trust-badge ' + (epG.passed ? 'trust-ok' : 'trust-pending') + '">Gate A 认识论 ' + (epG.passed ? '过' : '未过') + '</span>';
    html += '<span class="trust-badge ' + (outG.passed ? 'trust-ok' : 'trust-pending') + '">Gate B 烟测 ' + (outG.passed ? '过' : '未过') + '</span>';
  }
  if (tier === 'provisional') {
    html += '<span class="pr-trust-hint">学徒态：可安装试用，双门禁未齐则不标 Verified。本地 Quick8 ≠ 官方 SkillsBench。</span>';
  } else if (tier === 'verified') {
    html += '<span class="pr-trust-hint">出师态：声明级 + 任务级门禁均已通过，可导出安装。</span>';
  } else if (p > 0) {
    html += '<span class="pr-trust-hint">待确认项可在详情页审核</span>';
  }
  html += '</div>';
  return html;
}

function renderEvidenceBlock(payload) {
  var v = payload.verified || 0;
  var pend = payload.pending || 0;
  var err = payload.errors || 0;
  var total = payload.total_claims || (v + pend + err);
  var tasks = payload.smoke_tasks || [];
  var minScore = payload.min_with_score;
  var html = '<div class="pr-evidence">';
  html += '<div class="pr-evidence-title">证据（Evidence）</div>';
  html += '<div class="pr-evidence-claims">声明：已验证 ' + v + ' · 待审 ' + pend;
  if (err) html += ' · 错误 ' + err;
  html += ' · 合计 ' + total + '</div>';
  if (minScore != null && minScore !== '') {
    html += '<div class="pr-evidence-smoke">Gate B 最低分：' + escHtml(String(minScore));
    html += '（门槛 80）</div>';
  }
  if (tasks && tasks.length) {
    html += '<ul class="pr-evidence-tasks">';
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      var tid = typeof t === 'string' ? t : (t.task_id || t);
      var score = (typeof t === 'object' && t.with_score != null) ? (' · ' + t.with_score) : '';
      html += '<li><code>' + escHtml(String(tid)) + '</code>' + escHtml(score) + '</li>';
    }
    html += '</ul>';
  } else {
    html += '<div class="pr-evidence-smoke pr-evidence-muted">尚无域内烟测明细（可能未跑 Gate B 或无 domain pack）</div>';
  }
  html += '<div class="pr-evidence-muted">口径：本地 smoke/Quick8，非官方 SkillsBench。</div>';
  html += '</div>';
  return html;
}

function renderPrecipitationResultCard(payload) {
  var p = normalizePrecipitationPayload(typeof payload === 'object' ? payload : { skill_name: payload });
  if (p.variant === 'digest') return renderDigestResultCard(p);
  if (!p.skill_name) return '';

  var tier = p.trust_tier || 'draft';
  var html = '<div class="precipitation-result precipitation-result-' + _escAttr(tier) + '">';
  html += '<div class="pr-header"><span class="pr-icon pr-icon-ok" aria-hidden="true">'+(typeof Icons !== 'undefined' ? Icons.svg('check') : '✓')+'</span>';
  html += '<div><div class="pr-title">' + escHtml(_tierTitle(tier)) + '</div>';
  html += '<div class="pr-skill-name">' + escHtml(p.skill_name) + '</div></div></div>';
  html += '<div class="pr-meta"><span class="pr-meta-label">来源</span>' + escHtml(_sourceLabel(p.source_kind, p.source)) + '</div>';
  html += renderTrustLine(p);
  html += renderEvidenceBlock(p);
  if (p.moe != null) {
    html += '<div class="pr-meta pr-meta-fold"><span class="pr-meta-label">质量</span>MoE ' + escHtml(String(p.moe)) + ' · ';
    html += _prActionBtn('展开详情', 'detail', { skill: p.skill_name, tab: 'quality' }, 'pr-link-btn');
    html += '</div>';
  }
  if (typeof renderExportChannelPanel === 'function') {
    html += renderExportChannelPanel({
      skill_name: p.skill_name,
      slug: p.slug,
      trust_tier: p.trust_tier,
      model_invocable: p.trust_tier === 'verified' || p.trust_tier === 'provisional',
      install_paths: typeof buildInstallPaths === 'function' ? buildInstallPaths(p.slug) : { cursor: p.cursor_path },
    });
  } else {
    html += '<div class="pr-actions">';
    if (p.cursor_path) {
      html += _prActionBtn('复制 Cursor 安装路径', 'copy-path', { path: p.cursor_path }, 'btn-primary btn-sm pr-action-primary');
    }
    if (p.zip_url) {
      html += _prActionBtn('下载 Zip', 'zip', { url: p.zip_url, skill: p.skill_name });
    }
    html += _prActionBtn('查看详情', 'detail', { skill: p.skill_name });
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function renderDigestResultCard(payload) {
  var p = payload || {};
  var html = '<div class="precipitation-result precipitation-result-digest">';
  html += '<div class="pr-header"><span class="pr-icon pr-icon-digest" aria-hidden="true">'+(typeof Icons !== 'undefined' ? Icons.svg('book') : '📖')+'</span>';
  html += '<div><div class="pr-title">已写入知识库</div>';
  html += '<div class="pr-skill-name">' + escHtml(p.digest_title || '知识包') + '</div></div></div>';
  html += '<p class="pr-digest-note">内容为参考/概念型资料，未生成可执行 Skill。可在知识库中查阅。</p>';
  html += '<div class="pr-actions">' + _prActionBtn('打开知识仪表盘', 'knowledge') + '</div>';
  html += '</div>';
  return html;
}

function fetchSkillExportMeta(name) {
  if (typeof fetchFullExportMeta === 'function') {
    return fetchFullExportMeta(name).then(function(meta) {
      return {
        portable_slug: meta.portable_slug,
        install_paths: meta.install_paths,
      };
    });
  }
  var base = typeof API !== 'undefined' ? API : '';
  var headers = typeof authHeaders === 'function' ? authHeaders() : {};
  return fetch(base + '/api/skills/' + encodeURIComponent(name) + '/export?format=markdown', { headers: headers })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      var slug = d.portable_slug || '';
      var paths = typeof buildInstallPaths === 'function' ? buildInstallPaths(slug) : { cursor: '~/.cursor/skills/' + slug + '/' };
      return { portable_slug: slug, install_paths: paths };
    });
}

function showPrecipitationResult(opts) {
  opts = opts || {};
  var p = normalizePrecipitationPayload(opts);
  if (p.variant === 'digest') {
    addMsg('sys', renderDigestResultCard(p));
    if (typeof hideExtractionStrip === 'function') hideExtractionStrip();
    if (typeof toast === 'function') toast('知识包已入库', 'success');
    return;
  }
  if (!p.skill_name) return;

  function display(enriched) {
    var card = renderPrecipitationResultCard(enriched);
    addMsg('sys', card);
    var ep = normalizePrecipitationPayload(enriched);
    if (typeof hideExtractionStrip === 'function') hideExtractionStrip();
    if (typeof updateWorkspace === 'function') {
      updateWorkspace({
        skill_active: false,
        extraction_phase: 'IDLE',
        draft_preview: ep.skill_name,
        skill_saved: ep.skill_name,
        epistemic_summary: _epFromPayload(enriched),
      });
    }
    if (typeof refreshSkillList === 'function') refreshSkillList();
    if (typeof toast === 'function') {
      var t = ep.trust_tier || 'draft';
      var msg = t === 'verified'
        ? '技能「' + ep.skill_name + '」已出师（Verified）'
        : t === 'provisional'
          ? '技能「' + ep.skill_name + '」已沉淀（学徒 / Provisional）'
          : '技能「' + ep.skill_name + '」已保存（Draft）';
      toast(msg, t === 'verified' ? 'success' : 'info');
    }
  }

  if (!p.cursor_path) {
    fetchSkillExportMeta(p.skill_name)
      .then(function(meta) {
        display(Object.assign({}, opts, {
          portable_slug: meta.portable_slug,
          install_paths: meta.install_paths,
        }));
      })
      .catch(function() { display(opts); });
  } else {
    display(opts);
  }
}

function precipitateFromResponse(d, sourceKind) {
  if (!d) return;
  if (d.skill_saved) {
    var epSum = d.epistemic_summary || {};
    showPrecipitationResult({
      skill_name: d.skill_saved,
      epistemic_summary: epSum,
      moe_evaluation: d.moe_evaluation,
      export_zip_url: d.export_zip_url,
      portable_slug: d.portable_slug,
      install_paths: d.install_paths,
      trust_tier: d.trust_tier || epSum.trust_tier,
      gates: d.gates || epSum.gates,
      trust_reasons: d.trust_reasons || epSum.trust_reasons,
      source_kind: sourceKind || epSum.source_type || 'conversation',
      source: epSum.source || '',
    });
    return;
  }
  if (d.title && !d.skill_saved) {
    showPrecipitationResult({
      variant: 'digest',
      digest_title: d.title,
      glossary_terms: d.glossary_terms,
    });
  }
}

function copyCursorInstallPath(path) {
  if (!path) return;
  var done = function() {
    if (typeof toast === 'function') toast('已复制：' + path, 'success');
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(path).then(done).catch(function() {
      if (typeof toast === 'function') toast('复制失败，请手动复制：' + path, 'warn');
    });
  } else if (typeof toast === 'function') {
    toast(path, 'info');
  }
}

function downloadPrecipitationZip(url, name) {
  if (name && typeof downloadSkillExportZip === 'function') {
    downloadSkillExportZip(name);
    return;
  }
  if (!url) return;
  var headers = typeof authHeaders === 'function' ? authHeaders() : {};
  fetch((typeof API !== 'undefined' ? API : '') + url, { headers: headers })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.blob();
    })
    .then(function(blob) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (name || 'skill') + '.zip';
      a.click();
      URL.revokeObjectURL(a.href);
      if (typeof toast === 'function') toast('已开始下载', 'success');
    })
    .catch(function(e) {
      if (typeof toast === 'function') toast('下载失败：' + e.message, 'error');
    });
}

function evidenceApiToBlockPayload(card) {
  card = card || {};
  var c = card.claims || {};
  var o = card.outcome || {};
  return {
    verified: c.verified || 0,
    pending: c.pending || 0,
    errors: c.errors || 0,
    total_claims: c.total || 0,
    smoke_tasks: o.tasks || [],
    min_with_score: o.min_with_score,
    trust_tier: card.trust_tier || 'draft',
  };
}

function renderOverviewTrustCard(skill, evidenceCard) {
  var ep = skill.epistemic_summary || {};
  var meta = skill.meta || {};
  var tier = skill.trust_tier || ep.trust_tier || meta.trust_tier || 'draft';
  var gates = skill.gates || ep.gates || meta.gates || (evidenceCard && evidenceCard.gates) || {};
  var v = ep.verified || (evidenceCard && evidenceCard.claims && evidenceCard.claims.verified) || 0;
  var p = ep.pending || (evidenceCard && evidenceCard.claims && evidenceCard.claims.pending) || 0;
  var inner = '<div class="overview-trust-row">';
  inner += '<span class="' + _tierBadgeClass(tier) + '">' + _tierBadgeLabel(tier) + '</span>';
  inner += '<span class="trust-badge trust-verified">声明已验证 ' + v + '</span>';
  if (p > 0) inner += '<span class="trust-badge trust-pending">待审 ' + p + '</span>';
  if (gates.epistemic || gates.outcome) {
    var epG = gates.epistemic || {};
    var outG = gates.outcome || {};
    inner += '<span class="trust-badge ' + (epG.passed ? 'trust-ok' : 'trust-pending') + '">Gate A ' + (epG.passed ? '过' : '未过') + '</span>';
    inner += '<span class="trust-badge ' + (outG.passed ? 'trust-ok' : 'trust-pending') + '">Gate B ' + (outG.passed ? '过' : '未过') + '</span>';
  }
  inner += '</div>';
  if (tier === 'provisional') {
    inner += '<p class="detail-muted">学徒态（Provisional）：可安装试用；Verified 需认识论与域内烟测双过。</p>';
  } else if (tier === 'draft') {
    inner += '<p class="detail-muted">Draft：草稿未完成或双门禁未评估。</p>';
  }
  var outG2 = gates.outcome || {};
  if (outG2.min_with_score != null) {
    inner += '<p class="detail-muted">Gate B 最低分 ' + escHtml(String(outG2.min_with_score)) + '（门槛 80）</p>';
  }
  if (outG2.tasks && outG2.tasks.length) {
    inner += '<ul class="pr-evidence-tasks overview-smoke-tasks">';
    for (var i = 0; i < outG2.tasks.length; i++) {
      var t = outG2.tasks[i];
      var tid = typeof t === 'string' ? t : (t.task_id || t);
      inner += '<li><code>' + escHtml(String(tid)) + '</code></li>';
    }
    inner += '</ul>';
  }
  if (p > 0) {
    inner += '<p class="detail-muted">有 ' + p + ' 条声明待确认。</p>';
    inner += _prActionBtn('去审核', 'switch-tab', { tab: 'epistemic' });
  }
  if (evidenceCard) {
    inner += renderEvidenceBlock(evidenceApiToBlockPayload(evidenceCard));
  } else {
    inner += '<div id="overview-evidence-live" class="overview-evidence-live"></div>';
    if (skill.name) {
      inner += ' ' + _prActionBtn('加载证据', 'evidence', { skill: skill.name }, 'btn-secondary btn-sm');
    }
  }
  return '<div class="content-card detail-panel overview-trust-card"><div class="content-card-header">Trust Tier · 认识论 · 证据</div>' + inner + '</div>';
}

function _parsePortableSlugFromContent(content) {
  if (!content || content.indexOf('---') !== 0) return '';
  var end = content.indexOf('\n---', 4);
  if (end < 0) return '';
  var block = content.slice(4, end);
  var m = block.match(/^portable_slug:\s*['"]?([^\s'"]+)/m);
  if (m) return m[1].trim();
  m = block.match(/^name:\s*['"]?([^\s'"]+)/m);
  return m ? m[1].trim() : '';
}

function renderOverviewSourceCard(skill, exportMeta) {
  exportMeta = exportMeta || {};
  var slug = _parsePortableSlugFromContent(skill.content || '') || exportMeta.portable_slug || '';
  if (typeof renderExportChannelPanel === 'function') {
    return '<div class="content-card detail-panel overview-source-card"><div class="content-card-header">输出与安装 · Harness</div>' +
      renderExportChannelPanel({
        skill_name: skill.name,
        slug: slug,
        trust_tier: skill.trust_tier || (skill.epistemic_summary || {}).trust_tier,
        model_invocable: skill.model_invocable,
        install_paths: exportMeta.install_paths || (typeof buildInstallPaths === 'function' ? buildInstallPaths(slug) : {}),
        compact: true,
      }) + '</div>';
  }
  var ep = skill.epistemic_summary || {};
  var srcType = ep.source_type || '—';
  var inner = '<div class="detail-row"><span class="detail-row-label">来源类型</span><span>' + escHtml(srcType || '—') + '</span></div>';
  if (slug) {
    var cursorPath = '~/.cursor/skills/' + slug + '/';
    inner += '<div class="detail-row"><span class="detail-row-label">Cursor</span><code class="pr-path-code">' + escHtml(cursorPath) + '</code></div>';
    inner += _prActionBtn('复制安装路径', 'copy-path', { path: cursorPath }, 'btn-primary btn-sm') + ' ';
  }
  inner += _prActionBtn('下载 Zip', 'export-zip');
  return '<div class="content-card detail-panel overview-source-card"><div class="content-card-header">来源与安装</div>' + inner + '</div>';
}

document.addEventListener('click', function(e) {
  var btn = e.target.closest('[data-pr-action]');
  if (!btn) return;
  var action = btn.getAttribute('data-pr-action');
  if (action === 'detail') {
    e.preventDefault();
    if (typeof showDetail === 'function') {
      showDetail(btn.getAttribute('data-pr-skill'), btn.getAttribute('data-pr-tab') || undefined);
    }
  } else if (action === 'copy-path') {
    e.preventDefault();
    copyCursorInstallPath(btn.getAttribute('data-pr-path'));
  } else if (action === 'zip') {
    e.preventDefault();
    downloadPrecipitationZip(btn.getAttribute('data-pr-url'), btn.getAttribute('data-pr-skill'));
  } else if (action === 'knowledge') {
    e.preventDefault();
    if (typeof showUnifiedKnowledge === 'function') showUnifiedKnowledge('dashboard');
  } else if (action === 'switch-tab') {
    e.preventDefault();
    if (typeof switchTab === 'function') switchTab(btn.getAttribute('data-pr-tab'));
  } else if (action === 'export-zip') {
    e.preventDefault();
    if (typeof exportSkill === 'function') exportSkill();
  } else if (action === 'evidence') {
    e.preventDefault();
    var sk = btn.getAttribute('data-pr-skill');
    var base = typeof API !== 'undefined' ? API : '';
    var headers = typeof authHeaders === 'function' ? authHeaders() : {};
    fetch(base + '/api/skills/' + encodeURIComponent(sk) + '/evidence', { headers: headers })
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(card) {
        var host = document.getElementById('overview-evidence-live');
        if (!host) {
          host = document.createElement('div');
          host.id = 'overview-evidence-live';
          var cardEl = document.querySelector('.overview-trust-card');
          if (cardEl) cardEl.appendChild(host);
        }
        if (host) host.innerHTML = renderEvidenceBlock(evidenceApiToBlockPayload(card));
        if (typeof toast === 'function') {
          toast(sk + ' · ' + (card.trust_tier || 'draft') + ' · 已验证 ' + ((card.claims && card.claims.verified) || 0), 'info');
        }
      })
      .catch(function(err) {
        if (typeof toast === 'function') toast('证据加载失败：' + err.message, 'error');
      });
  }
});
