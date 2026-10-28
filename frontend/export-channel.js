/* export-channel.js — 多 Harness 安装引导（Cursor / agents / dsh）+ 统一导出 */

var _PLATFORM_LABELS = {
  cursor: 'Cursor',
  claude_code: 'Claude Code',
  codex: 'Codex CLI',
  gemini_cli: 'Gemini CLI',
  trae: 'Trae',
  copilot: 'GitHub Copilot',
  agents_user: 'Agents（用户）',
  agents_project: 'Agents（项目）',
  dsh_user: 'DeepSeek Harness（用户）',
  dsh_project: 'DeepSeek Harness（项目）',
};

function buildInstallPaths(slug) {
  if (!slug) return {};
  return {
    cursor: '~/.cursor/skills/' + slug + '/',
    claude_code: '~/.claude/skills/' + slug + '/',
    codex: '~/.codex/skills/' + slug + '/',
    gemini_cli: '~/.gemini/skills/' + slug + '/',
    trae: '~/.trae/skills/' + slug + '/',
    copilot: '~/.github/copilot/skills/' + slug + '/',
    agents_user: '~/.agents/skills/' + slug + '/',
    agents_project: '.agents/skills/' + slug + '/',
    dsh_user: '~/.dsh/skills/' + slug + '/',
    dsh_project: '.dsh/skills/' + slug + '/',
  };
}

function _escAttr(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function _ecBtn(label, action, extra, cls) {
  extra = extra || {};
  var html = '<button type="button" class="' + (cls || 'btn-secondary btn-sm') + '" data-ec-action="' + _escAttr(action) + '"';
  if (extra.skill) html += ' data-ec-skill="' + _escAttr(extra.skill) + '"';
  if (extra.path) html += ' data-ec-path="' + _escAttr(extra.path) + '"';
  if (extra.slug) html += ' data-ec-slug="' + _escAttr(extra.slug) + '"';
  if (extra.target) html += ' data-ec-target="' + _escAttr(extra.target) + '"';
  if (extra.project) html += ' data-ec-project="1"';
  html += '>' + (typeof escHtml === 'function' ? escHtml(label) : label) + '</button>';
  return html;
}

function installSkillLocal(skillName, target, project) {
  if (!skillName) return Promise.reject(new Error('no skill'));
  target = target || 'cursor';
  var headers = Object.assign(
    { 'Content-Type': 'application/json' },
    typeof authHeaders === 'function' ? authHeaders() : {}
  );
  var base = typeof API !== 'undefined' ? API : '';
  return fetch(base + '/api/skills/' + encodeURIComponent(skillName) + '/install-local', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ target: target, project: !!project }),
  }).then(function(r) {
    return r.json().then(function(d) {
      if (!r.ok) throw new Error((d && d.detail) || ('HTTP ' + r.status));
      return d;
    });
  }).then(function(d) {
    var msg = '已装到本机：' + (d.path || target);
    if (d.trust_tier) msg += ' · ' + d.trust_tier;
    if (typeof toast === 'function') toast(msg, 'success');
    return d;
  }).catch(function(err) {
    if (typeof toast === 'function') toast('本机安装失败：' + err.message, 'error');
    throw err;
  });
}

function renderExportChannelPanel(opts) {
  opts = opts || {};
  var slug = opts.slug || '';
  var name = opts.skill_name || opts.name || '';
  var paths = opts.install_paths || buildInstallPaths(slug);
  var cursorPath = paths.cursor || '';
  var agentsPath = paths.agents_project || '';
  var dshPath = paths.dsh_user || paths.dsh_project || '';
  var compact = !!opts.compact;
  var tier = String(opts.trust_tier || '').toLowerCase();
  var modelOk = opts.model_invocable;
  if (modelOk == null) {
    modelOk = tier === 'verified' || tier === 'provisional';
  }

  if (!slug && !name) return '';

  var html = '<div class="export-channel' + (compact ? ' export-channel-compact' : '') + '">';
  html += '<div class="export-channel-head"><span class="export-channel-icon" aria-hidden="true">⬡</span>';
  html += '<div><div class="export-channel-title">装进 Harness</div>';
  html += '<div class="export-channel-sub">AgentSkills.io · Cursor / .agents / DeepSeek Harness</div></div></div>';

  html += '<ol class="export-channel-steps">';
  html += '<li>复制路径或下载 Zip（优先 Verified；Draft 不对模型目录暴露）</li>';
  html += '<li>解压到 Cursor <code>~/.cursor/skills/' + escHtml(slug || name) + '/</code>，或项目 <code>.agents/skills/</code> / <code>.dsh/skills/</code></li>';
  html += '<li>新开对话用 <code>@' + escHtml(slug || name) + '</code>；或运行 <code>npx @deepseek-ai/dsh web</code> 试用</li>';
  html += '</ol>';
  html += '<p class="export-channel-tip">Skill（可验证说明书）≠ Plugin（运行时能力）。学徒态可试用；双门禁齐才标 Verified。</p>';
  if (!modelOk) {
    html += '<p class="export-channel-tip export-channel-warn">当前 Draft：可安装给人看，默认不进模型可调用 catalog。</p>';
  }

  if (cursorPath) {
    html += '<div class="export-channel-path"><code class="pr-path-code">' + escHtml(cursorPath) + '</code></div>';
  }

  html += '<div class="export-channel-actions">';
  if (name) {
    html += _ecBtn('装到 Cursor', 'install-local', { skill: name, target: 'cursor' }, 'btn-primary btn-sm export-channel-primary');
    html += _ecBtn('装到 dsh', 'install-local', { skill: name, target: 'dsh' }, 'btn-secondary btn-sm');
    html += _ecBtn('装到 .agents', 'install-local', { skill: name, target: 'agents', project: true }, 'btn-secondary btn-sm');
  }
  if (cursorPath) {
    html += _ecBtn('复制 Cursor 路径', 'copy-path', { path: cursorPath }, 'btn-secondary btn-sm');
  }
  if (agentsPath) {
    html += _ecBtn('复制 .agents 路径', 'copy-path', { path: agentsPath }, 'btn-secondary btn-sm');
  }
  if (dshPath) {
    html += _ecBtn('复制 dsh 路径', 'copy-path', { path: dshPath }, 'btn-secondary btn-sm');
  }
  html += _ecBtn('复制 dsh 命令', 'copy-path', { path: 'npx @deepseek-ai/dsh web' }, 'btn-secondary btn-sm');
  if (name) {
    var cli = 'python scripts/install_skill_to_harness.py "' + name + '" --target cursor';
    html += _ecBtn('复制安装 CLI', 'copy-path', { path: cli }, 'btn-secondary btn-sm');
    html += _ecBtn('下载 Zip', 'zip', { skill: name });
    html += _ecBtn('复制 SKILL.md', 'copy-md', { skill: name, slug: slug });
  }
  if (name && typeof showDetail === 'function') {
    html += _ecBtn('查看详情', 'detail', { skill: name });
  }
  html += '</div>';

  if (slug && !compact) {
    var other = ['claude_code', 'codex', 'gemini_cli', 'copilot', 'agents_user', 'dsh_project'].filter(function(k) {
      return paths[k];
    });
    if (other.length) {
      html += '<details class="export-channel-more"><summary>其他平台 / Harness 路径</summary><ul class="export-channel-platforms">';
      other.forEach(function(k) {
        html += '<li><span class="export-channel-plat">' + escHtml(_PLATFORM_LABELS[k] || k) + '</span>';
        html += '<code>' + escHtml(paths[k]) + '</code>';
        html += _ecBtn('复制', 'copy-path', { path: paths[k] }, 'btn-ghost btn-xs');
        html += '</li>';
      });
      html += '</ul></details>';
    }
  }

  html += '</div>';
  return html;
}

function fetchFullExportMeta(name) {
  var base = typeof API !== 'undefined' ? API : '';
  var headers = typeof authHeaders === 'function' ? authHeaders() : {};
  return fetch(base + '/api/skills/' + encodeURIComponent(name) + '/export?format=markdown', { headers: headers })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      var slug = d.portable_slug || '';
      return {
        portable_slug: slug,
        slug: slug,
        description: d.description || '',
        install_paths: buildInstallPaths(slug),
        portable_content: d.portable_content || d.content || '',
        trust_tier: d.trust_tier || '',
      };
    });
}

function copyTextToClipboard(text, okMsg) {
  if (!text) return;
  var done = function() {
    if (typeof toast === 'function') toast(okMsg || '已复制', 'success');
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function() {
      if (typeof toast === 'function') toast('复制失败，请手动复制', 'warn');
    });
  } else if (typeof toast === 'function') {
    toast(text, 'info');
  }
}

function copySkillMarkdown(skillName) {
  if (!skillName) return;
  fetchFullExportMeta(skillName)
    .then(function(meta) {
      var content = meta.portable_content || '';
      if (!content) throw new Error('无 SKILL.md 内容');
      copyTextToClipboard(content, '已复制 SKILL.md 到剪贴板');
    })
    .catch(function(e) {
      if (typeof toast === 'function') toast('复制失败：' + e.message, 'error');
    });
}

function downloadExportZip(skillName) {
  if (!skillName) return;
  if (typeof downloadSkillExportZip === 'function') {
    downloadSkillExportZip(skillName);
    return;
  }
  if (typeof downloadPrecipitationZip === 'function') {
    downloadPrecipitationZip('/api/skills/' + encodeURIComponent(skillName) + '/export/zip', skillName);
  }
}

document.addEventListener('click', function(e) {
  var btn = e.target.closest('[data-ec-action]');
  if (!btn) return;
  e.preventDefault();
  var action = btn.getAttribute('data-ec-action');
  if (action === 'copy-path') {
    copyTextToClipboard(btn.getAttribute('data-ec-path'), '已复制安装路径');
  } else if (action === 'install-local') {
    installSkillLocal(
      btn.getAttribute('data-ec-skill'),
      btn.getAttribute('data-ec-target') || 'cursor',
      btn.getAttribute('data-ec-project') === '1'
    );
  } else if (action === 'zip') {
    downloadExportZip(btn.getAttribute('data-ec-skill'));
  } else if (action === 'copy-md') {
    copySkillMarkdown(btn.getAttribute('data-ec-skill'));
  } else if (action === 'detail') {
    if (typeof showDetail === 'function') showDetail(btn.getAttribute('data-ec-skill'));
  }
});
