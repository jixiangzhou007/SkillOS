/* SkillOS — Skill Export / Import
   Extracted from skills.js. Depends on globals: api, toast (from app.js).
   All functions are called at user-interaction time, not parse time,
   so cross-file references are safe as long as all scripts load first.
*/

// ── Export (ZIP) ─────────────────────────────────────────────

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

// ── Export (Markdown / Universal) ────────────────────────────

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
