/* precipitation-result.js — M1 Verified Skill 完成态卡片（三路径共用） */

function _escAttr(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;');
}

function _epFromPayload(opts) {
  return opts.epistemic_summary || opts.epistemic || {};
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

  return {
    skill_name: name,
    source: opts.source || ep.source || '',
    source_kind: opts.source_kind || ep.source_type || '',
    verified: ep.verified != null ? ep.verified : 0,
    pending: ep.pending != null ? ep.pending : 0,
    total_claims: ep.total_claims != null ? ep.total_claims : 0,
    moe: moe,
    slug: slug,
    cursor_path: cursorPath,
    zip_url: opts.export_zip_url || (name ? '/api/skills/' + encodeURIComponent(name) + '/export/zip' : ''),
    variant: opts.variant || 'skill',
    digest_title: opts.digest_title || opts.title || '',
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

function renderTrustLine(payload) {
  var v = payload.verified || 0;
  var p = payload.pending || 0;
  var html = '<div class="pr-trust">';
  html += '<span class="trust-badge trust-verified">已验证 ' + v + '</span>';
  if (p > 0) {
    html += '<span class="trust-badge trust-pending">待审 ' + p + '</span>';
    html += '<span class="pr-trust-hint">待确认项不影响安装，可在详情页审核</span>';
  } else if (payload.total_claims > 0) {
    html += '<span class="trust-badge trust-ok">可安装使用</span>';
  }
  html += '</div>';
  return html;
}

function renderPrecipitationResultCard(payload) {
  var p = normalizePrecipitationPayload(typeof payload === 'object' ? payload : { skill_name: payload });
  if (p.variant === 'digest') return renderDigestResultCard(p);
  if (!p.skill_name) return '';

  var html = '<div class="precipitation-result">';
  html += '<div class="pr-header"><span class="pr-icon pr-icon-ok" aria-hidden="true">'+(typeof Icons !== 'undefined' ? Icons.svg('check') : '✓')+'</span>';
  html += '<div><div class="pr-title">Verified Skill 已沉淀</div>';
  html += '<div class="pr-skill-name">' + escHtml(p.skill_name) + '</div></div></div>';
  html += '<div class="pr-meta"><span class="pr-meta-label">来源</span>' + escHtml(_sourceLabel(p.source_kind, p.source)) + '</div>';
  html += renderTrustLine(p);
  if (p.moe != null) {
    html += '<div class="pr-meta pr-meta-fold"><span class="pr-meta-label">质量</span>MoE ' + escHtml(String(p.moe)) + ' · ';
    html += _prActionBtn('展开详情', 'detail', { skill: p.skill_name, tab: 'quality' }, 'pr-link-btn');
    html += '</div>';
  }
  if (typeof renderExportChannelPanel === 'function') {
    html += renderExportChannelPanel({
      skill_name: p.skill_name,
      slug: p.slug,
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
    if (typeof toast === 'function') toast('技能「' + ep.skill_name + '」已沉淀', 'success');
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
    showPrecipitationResult({
      skill_name: d.skill_saved,
      epistemic_summary: d.epistemic_summary,
      moe_evaluation: d.moe_evaluation,
      export_zip_url: d.export_zip_url,
      portable_slug: d.portable_slug,
      install_paths: d.install_paths,
      source_kind: sourceKind || (d.epistemic_summary && d.epistemic_summary.source_type) || 'conversation',
      source: (d.epistemic_summary && d.epistemic_summary.source) || '',
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

function renderOverviewTrustCard(skill) {
  var ep = skill.epistemic_summary || {};
  var v = ep.verified || 0;
  var p = ep.pending || 0;
  var inner = '<div class="overview-trust-row">';
  inner += '<span class="trust-badge trust-verified">已验证 ' + v + '</span>';
  if (p > 0) inner += '<span class="trust-badge trust-pending">待审 ' + p + '</span>';
  inner += '</div>';
  if (p > 0) {
    inner += '<p class="detail-muted">有 ' + p + ' 条声明待确认，不影响安装与使用。</p>';
    inner += _prActionBtn('去审核', 'switch-tab', { tab: 'epistemic' });
  }
  return '<div class="content-card detail-panel overview-trust-card"><div class="content-card-header">认识论状态</div>' + inner + '</div>';
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
    return '<div class="content-card detail-panel overview-source-card"><div class="content-card-header">输出与安装</div>' +
      renderExportChannelPanel({
        skill_name: skill.name,
        slug: slug,
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
  }
});
