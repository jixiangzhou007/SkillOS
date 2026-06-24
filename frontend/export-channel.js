/* export-channel.js — M4 输出/通道：Cursor 优先安装引导 + 统一导出 */

var _PLATFORM_LABELS = {
  cursor: 'Cursor',
  claude_code: 'Claude Code',
  codex: 'Codex CLI',
  gemini_cli: 'Gemini CLI',
  trae: 'Trae',
  copilot: 'GitHub Copilot',
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
  html += '>' + (typeof escHtml === 'function' ? escHtml(label) : label) + '</button>';
  return html;
}

function renderExportChannelPanel(opts) {
  opts = opts || {};
  var slug = opts.slug || '';
  var name = opts.skill_name || opts.name || '';
  var paths = opts.install_paths || buildInstallPaths(slug);
  var cursorPath = paths.cursor || '';
  var compact = !!opts.compact;

  if (!slug && !name) return '';

  var html = '<div class="export-channel' + (compact ? ' export-channel-compact' : '') + '">';
  html += '<div class="export-channel-head"><span class="export-channel-icon" aria-hidden="true">⬡</span>';
  html += '<div><div class="export-channel-title">装进 Cursor</div>';
  html += '<div class="export-channel-sub">AgentSkills.io 标准 · 在 Cursor 验货，在这里导出</div></div></div>';

  html += '<ol class="export-channel-steps">';
  html += '<li>下载 Zip 或复制安装路径</li>';
  html += '<li>将 <code>' + escHtml(slug || name) + '/</code> 放入 Cursor skills 目录</li>';
  html += '<li>在 Cursor 对话中 <code>@' + escHtml(slug || name) + '</code> 验证</li>';
  html += '</ol>';

  if (cursorPath) {
    html += '<div class="export-channel-path"><code class="pr-path-code">' + escHtml(cursorPath) + '</code></div>';
  }

  html += '<div class="export-channel-actions">';
  if (cursorPath) {
    html += _ecBtn('复制 Cursor 路径', 'copy-path', { path: cursorPath }, 'btn-primary btn-sm export-channel-primary');
  }
  if (name) {
    html += _ecBtn('下载 Zip', 'zip', { skill: name });
    html += _ecBtn('复制 SKILL.md', 'copy-md', { skill: name, slug: slug });
  }
  if (name && typeof showDetail === 'function') {
    html += _ecBtn('查看详情', 'detail', { skill: name });
  }
  html += '</div>';

  if (slug && !compact) {
    var other = ['claude_code', 'codex', 'gemini_cli', 'copilot'].filter(function(k) { return paths[k]; });
    if (other.length) {
      html += '<details class="export-channel-more"><summary>其他平台路径</summary><ul class="export-channel-platforms">';
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
  } else if (action === 'zip') {
    downloadExportZip(btn.getAttribute('data-ec-skill'));
  } else if (action === 'copy-md') {
    copySkillMarkdown(btn.getAttribute('data-ec-skill'));
  } else if (action === 'detail') {
    if (typeof showDetail === 'function') showDetail(btn.getAttribute('data-ec-skill'));
  }
});
