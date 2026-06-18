/* admin.js — Org admin console (Sprint 6) */

var _adminOrgId = '';

async function showAdmin() {
  switchMainView('admin-view');
  document.getElementById('bar').style.display = 'none';
  await loadAdminConsole();
}

async function resolveAdminOrgId() {
  try {
    var ws = JSON.parse(localStorage.getItem('sd_workspace') || '{}');
    if (ws.org_id) return ws.org_id;
    if (ws.tenant_id && ws.tenant_id.indexOf('org:') === 0)
      return ws.tenant_id.split(':')[1];
    var r = await api('/api/orgs');
    if (!r.ok) return '';
    var orgs = (await r.json()).organizations || [];
    var adminOrg = orgs.find(function (o) { return o.role === 'org_admin'; });
    return adminOrg ? adminOrg.org_id : (orgs[0] ? orgs[0].org_id : '');
  } catch (e) {
    return '';
  }
}

async function loadAdminConsole() {
  var el = document.getElementById('admin-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载管理控制台…</div>';

  _adminOrgId = await resolveAdminOrgId();
  if (!_adminOrgId) {
    el.innerHTML = '<div style="padding:20px;color:var(--warn)">请先创建或切换至组织工作区。</div>' +
      '<button class="btn a" onclick="createTeam()">创建团队</button>';
    return;
  }

  try {
    var overviewR = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/admin/overview');
    if (!overviewR.ok) throw new Error('overview ' + overviewR.status);
    var ov = await overviewR.json();
    var govR = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/admin/governance');
    var gov = govR.ok ? await govR.json() : null;
    var deptsR = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/departments');
    var depts = deptsR.ok ? (await deptsR.json()).departments || [] : [];

    var h = '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">' +
      '<div><div style="font-size:18px;font-weight:600">' + escHtml(ov.org.display_name) + '</div>' +
      '<div style="font-size:12px;color:var(--text3)">' + escHtml(ov.org.tenant_id) + '</div></div>' +
      '<button class="btn a" style="font-size:12px" onclick="loadAdminConsole()">刷新</button>' +
      '<button class="btn" style="font-size:12px;margin-left:8px" onclick="exportAuditCsv()">导出审计 CSV</button></div>';

    h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px">';
    h += _adminKpi('成员', ov.members_count);
    h += _adminKpi('部门', ov.departments_count);
    h += _adminKpi('技能', ov.skills_count);
    h += _adminKpi('LLM 本月', (ov.usage.llm_calls.used || 0) + '/' + (ov.usage.llm_calls.limit || '∞'));
    h += '</div>';

    if (gov) {
      var ratePct = gov.org_verified_rate != null ? Math.round(gov.org_verified_rate * 100) : '—';
      var targetPct = Math.round((gov.target_verified_rate || 0.7) * 100);
      var govOk = gov.meets_target;
      h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
      h += '<div style="font-weight:600;margin-bottom:10px">治理合规 · 认识论 verified 率</div>';
      h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:12px">';
      h += _adminKpi('verified 率', ratePct + '%');
      h += _adminKpi('目标', targetPct + '%');
      h += _adminKpi('达标技能', (gov.skills_meeting_target || 0) + '/' + (gov.skills_with_claims || 0));
      h += _adminKpi('状态', govOk ? '✅ 达标' : '⚠ 未达标');
      h += '</div>';
      if (gov.at_risk_skills && gov.at_risk_skills.length) {
        h += '<div style="font-size:12px;color:var(--text3);margin-bottom:6px">待提升技能（verified 率低于目标）</div>';
        h += '<ul style="margin:0;padding-left:18px;font-size:12px;color:var(--text2)">';
        gov.at_risk_skills.slice(0, 8).forEach(function (s) {
          h += '<li>' + escHtml(s.name) + ' — ' + Math.round(s.verified_rate * 100) + '% (' +
            s.verified + '/' + s.total_claims + ')</li>';
        });
        h += '</ul>';
      } else if ((gov.skills_with_claims || 0) === 0) {
        h += '<div style="font-size:12px;color:var(--text3)">暂无含认识论声明的技能数据</div>';
      }
      h += '</div>';
    }

    h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
    h += '<div style="font-weight:600;margin-bottom:10px">配额设置</div>';
    h += '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:end">';
    h += '<label style="font-size:12px">技能上限<br><input id="adm-max-skills" type="number" value="' + (ov.quota.max_skills || 9999) + '" style="width:100px;padding:6px;background:var(--srf);border:1px solid #333;border-radius:4px;color:var(--text)"></label>';
    h += '<label style="font-size:12px">LLM/月<br><input id="adm-max-llm" type="number" value="' + (ov.quota.max_llm_monthly || 9999) + '" style="width:100px;padding:6px;background:var(--srf);border:1px solid #333;border-radius:4px;color:var(--text)"></label>';
    h += '<button class="btn a" style="font-size:12px;padding:6px 14px" onclick="saveOrgQuota()">保存配额</button>';
    h += '</div></div>';

    h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px">';
    h += '<div style="font-weight:600;margin-bottom:10px">部门</div>';
    if (depts.length) {
      h += '<ul style="margin:0;padding-left:18px;font-size:13px">';
      depts.forEach(function (d) {
        h += '<li>' + escHtml(d.name) + ' <span style="color:var(--text3);font-size:11px">' + escHtml(d.dept_id) + '</span></li>';
      });
      h += '</ul>';
    } else {
      h += '<div style="color:var(--text3);font-size:12px">暂无部门</div>';
    }
    h += '<div style="display:flex;gap:8px;margin-top:12px">';
    h += '<input id="new-dept-name" placeholder="新部门名称" style="flex:1;padding:8px;background:var(--srf);border:1px solid #333;border-radius:6px;color:var(--text)">';
    h += '<button class="btn a" style="font-size:12px" onclick="addDepartment()">添加</button>';
    h += '</div></div>';

    h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px">';
    h += '<div style="font-weight:600;margin-bottom:10px">组织技能库</div>';
    h += '<input id="org-skill-search" placeholder="搜索技能…" oninput="searchOrgSkills(this.value)" style="width:100%;padding:8px;margin-bottom:10px;background:var(--srf);border:1px solid #333;border-radius:6px;color:var(--text)">';
    h += '<div id="org-skill-list" style="font-size:13px;color:var(--text2)">加载中…</div>';
    h += '</div>';

    el.innerHTML = h;
    searchOrgSkills('');
  } catch (e) {
    el.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>';
  }
}

function _adminKpi(label, val) {
  return '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;text-align:center">' +
    '<div style="font-size:22px;font-weight:700">' + val + '</div>' +
    '<div style="font-size:11px;color:var(--text3);margin-top:4px">' + label + '</div></div>';
}

async function saveOrgQuota() {
  if (!_adminOrgId) return;
  var skills = parseInt(document.getElementById('adm-max-skills').value, 10);
  var llm = parseInt(document.getElementById('adm-max-llm').value, 10);
  var r = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/admin/quota', {
    method: 'PATCH',
    body: JSON.stringify({ max_skills: skills, max_llm_monthly: llm }),
  });
  if (r.ok) toast('配额已保存'); else toast('保存失败', 'error');
}

async function addDepartment() {
  if (!_adminOrgId) return;
  var name = (document.getElementById('new-dept-name').value || '').trim();
  if (!name) { toast('请输入部门名称', 'error'); return; }
  var r = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/departments', {
    method: 'POST',
    body: JSON.stringify({ name: name }),
  });
  if (r.ok) { toast('部门已创建'); loadAdminConsole(); }
  else toast('创建失败', 'error');
}

async function searchOrgSkills(q) {
  var el = document.getElementById('org-skill-list');
  if (!el) return;
  var path = '/api/skills/' + (q ? '?q=' + encodeURIComponent(q) : '');
  try {
    var r = await api(path);
    var skills = r.ok ? await r.json() : [];
    if (!skills.length) {
      el.innerHTML = '<div style="color:var(--text3)">无匹配技能</div>';
      return;
    }
    el.innerHTML = skills.map(function (s) {
      return '<div style="padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="showDetail(\'' + s.name.replace(/'/g, "\\'") + '\')">' +
        escHtml(s.name) + ' <span style="color:var(--text3);font-size:11px">v' + s.version + '</span></div>';
    }).join('');
  } catch (e) {
    el.innerHTML = '搜索失败';
  }
}

async function copySkillToOrg(skillName) {
  var orgId = await resolveAdminOrgId();
  if (!orgId) {
    var name = prompt('组织名称（将创建新团队）');
    if (!name) return;
    await createTeam(name);
    orgId = await resolveAdminOrgId();
    if (!orgId) return;
  }
  var r = await api('/api/skills/' + encodeURIComponent(skillName) + '/copy-to-org', {
    method: 'POST',
    body: JSON.stringify({ org_id: orgId }),
  });
  if (!r.ok) {
    var err = await r.json().catch(function () { return {}; });
    toast(err.detail || '复制失败', 'error');
    return;
  }
  var d = await r.json();
  toast('已复制至组织: ' + d.skill_saved);
}

async function exportAuditCsv() {
  if (!_adminOrgId) return;
  try {
    var r = await api('/api/orgs/' + encodeURIComponent(_adminOrgId) + '/admin/audit/export');
    var text = await r.text();
    var blob = new Blob([text], { type: 'text/csv' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'audit_' + _adminOrgId + '.csv';
    a.click();
    toast('审计 CSV 已下载');
  } catch (e) {
    toast('导出失败', 'error');
  }
}

async function updateAdminNavVisibility() {
  var btn = document.getElementById('admin-nav-btn');
  if (!btn) return;
  try {
    var r = await api('/api/orgs');
    if (!r.ok) { btn.style.display = 'none'; return; }
    var orgs = (await r.json()).organizations || [];
    var isAdmin = orgs.some(function (o) { return o.role === 'org_admin'; });
    btn.style.display = isAdmin ? '' : 'none';
  } catch (e) {
    btn.style.display = 'none';
  }
}
