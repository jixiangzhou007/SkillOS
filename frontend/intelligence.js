/* intelligence.js — role templates, SkillOpt CLI hints */

function renderMermaidInto(elId, code) {
  if (window._mermaidFailed || typeof mermaid === 'undefined') {
    var el = document.getElementById(elId);
    if (el) el.textContent = code || '';
    return;
  }
  if (typeof mermaid === 'undefined' || !code) return;
  var el = document.getElementById(elId);
  if (!el) return;
  el.textContent = code.trim();
  try {
    mermaid.run({ querySelector: '#' + elId });
  } catch (e) {
    console.warn('mermaid render failed', e);
  }
}

async function fetchHubRoleTemplatesHtml() {
  try {
    var r = await api('/api/intelligence/role-templates');
    if (!r.ok) return '';
    var data = await r.json();
    var templates = data.templates || [];
    if (!templates.length) return '';

    var h = '<div style="margin:20px 0 12px;font-size:13px;font-weight:600;color:var(--text2)">🏢 岗位技能模板</div>';
    h += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">';
    templates.forEach(function (t) {
      h += '<button class="btn" style="font-size:12px;padding:6px 12px;background:var(--surface2);border:1px solid var(--border);color:var(--text2)" ';
      h += 'onclick="showRoleTemplate(\'' + t.role_id.replace(/'/g, "\\'") + '\')">' + escHtml(t.title) + '</button>';
    });
    h += '</div>';
    h += '<div id="role-template-detail"></div>';
    return h;
  } catch (e) {
    return '';
  }
}

async function showRoleTemplate(roleId) {
  var el = document.getElementById('role-template-detail');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);font-size:12px;padding:8px">加载岗位推荐…</div>';
  try {
    var r = await api('/api/intelligence/role-templates/' + encodeURIComponent(roleId) + '/recommendations?limit=6');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    var h = '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px">';
    h += '<div style="font-weight:600;margin-bottom:6px">' + escHtml(d.title) + '</div>';
    h += '<div style="font-size:12px;color:var(--text3);margin-bottom:12px">' + escHtml(d.description) + '</div>';

    if (d.metaskill_blueprint && d.metaskill_blueprint.mermaid) {
      var mid = 'role-dag-' + roleId.replace(/[^a-z0-9]/gi, '');
      h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px">MetaSkill 蓝图 · ' + escHtml(d.metaskill_blueprint.name) + '</div>';
      h += '<div style="overflow:auto;background:var(--surface2);border-radius:8px;padding:12px;margin-bottom:12px">';
      h += '<pre class="mermaid" id="' + mid + '" style="margin:0;background:transparent"></pre></div>';
    }

    if (d.catalog_skills && d.catalog_skills.length) {
      h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px">市场推荐</div>';
      d.catalog_skills.forEach(function (s) {
        h += '<div style="font-size:12px;padding:4px 0;color:var(--text2);cursor:pointer" onclick="showHubSkill(\'' + (s.skill_id || s.name || '').replace(/'/g, "\\'") + '\')">';
        h += escHtml(s.name || s.skill_id) + ' · ' + (s.match_score || '') + '</div>';
      });
    }
    if (d.tenant_skills && d.tenant_skills.length) {
      h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin:10px 0 6px">工作区已有</div>';
      d.tenant_skills.forEach(function (s) {
        h += '<div style="font-size:12px;padding:4px 0;color:var(--accent);cursor:pointer" onclick="showDetail(\'' + s.name.replace(/'/g, "\\'") + '\')">';
        h += escHtml(s.name) + (s.type === 'metaskill' ? ' 🔗' : '') + '</div>';
      });
    }
    h += '</div>';
    el.innerHTML = h;

    if (d.metaskill_blueprint && d.metaskill_blueprint.mermaid) {
      var mid2 = 'role-dag-' + roleId.replace(/[^a-z0-9]/gi, '');
      setTimeout(function () { renderMermaidInto(mid2, d.metaskill_blueprint.mermaid); }, 30);
    }
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);font-size:12px">' + escHtml(e.message) + '</div>';
  }
}

async function fetchSkillOptCliHelp() {
  try {
    var r = await api('/api/evolution/skillopt/cli');
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    return null;
  }
}

function skillOptCliBlock(commands) {
  if (!commands) return '';
  var h = '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:12px;font-size:11px">';
  h += '<div style="font-weight:600;color:var(--text2);margin-bottom:8px">SkillOpt CLI</div>';
  if (commands.export) h += '<div style="color:var(--text3);margin-bottom:4px"><code style="color:var(--accent)">' + escHtml(commands.export) + '</code></div>';
  if (commands.validate) h += '<div style="color:var(--text3);margin-bottom:4px"><code style="color:var(--accent)">' + escHtml(commands.validate) + '</code></div>';
  if (commands.run_dry) h += '<div style="color:var(--text3)"><code style="color:var(--accent)">' + escHtml(commands.run_dry) + '</code></div>';
  h += '</div>';
  return h;
}
