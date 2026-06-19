/* SkillOS — Admin Console (Alpine.js)
 * Phase 7 migration. Org admin dashboard.
 */

function adminView() {
  return {
    orgId: '',
    loading: true,
    error: '',
    overview: null,
    governance: null,
    departments: [],
    skillSearch: '',
    skillResults: [],
    selectedSkills: [],
    selectAll: false,
    quotaDept: '',
    quotaSkills: '',
    quotaLLM: '',
    newDeptName: '',

    async init() {
      this.loading = true;
      this.orgId = await resolveAdminOrgId();
      if (!this.orgId) {
        this.error = 'no_org';
        this.loading = false;
        return;
      }
      await this.loadAll();
    },

    get hasOrg() { return !!this.orgId && this.error !== 'no_org'; },

    async loadAll() {
      this.error = '';
      try {
        const [overviewR, govR, deptsR] = await Promise.all([
          api('/api/orgs/' + encodeURIComponent(this.orgId) + '/admin/overview'),
          api('/api/orgs/' + encodeURIComponent(this.orgId) + '/admin/governance'),
          api('/api/orgs/' + encodeURIComponent(this.orgId) + '/departments'),
        ]);
        if (!overviewR.ok) throw new Error('overview ' + overviewR.status);
        this.overview = await overviewR.json();
        this.governance = govR.ok ? await govR.json() : null;
        this.departments = deptsR.ok ? (await deptsR.json()).departments || [] : [];
      } catch (e) {
        this.error = e.message;
      }
      this.loading = false;
    },

    get complianceRates() {
      if (!this.governance) return [];
      const g = this.governance;
      return [
        { label: 'S_route 覆盖率', pct: Math.round((g.route_coverage || 0) * 100) },
        { label: 'S_trigger 覆盖率', pct: Math.round((g.trigger_coverage || 0) * 100) },
        { label: 'S_params 覆盖率', pct: Math.round((g.params_coverage || 0) * 100) },
        { label: 'DNA 合规率', pct: Math.round((g.dna_compliance || 0) * 100) },
      ];
    },

    async saveQuota() {
      const r = await api('/api/orgs/' + encodeURIComponent(this.orgId) + '/admin/quota', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dept_id: this.quotaDept,
          skills: parseInt(this.quotaSkills) || 0,
          llm_calls: parseInt(this.quotaLLM) || 0,
        }),
      });
      if (!r.ok) { toast('保存失败', 'error'); return; }
      toast('配额已保存', 'success');
      this.quotaDept = ''; this.quotaSkills = ''; this.quotaLLM = '';
    },

    async addDepartment() {
      const name = this.newDeptName.trim();
      if (!name) { toast('输入部门名称', 'warn'); return; }
      const r = await api('/api/orgs/' + encodeURIComponent(this.orgId) + '/departments', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!r.ok) { toast('添加失败', 'error'); return; }
      toast('部门已添加', 'success');
      this.newDeptName = '';
      await this.loadAll();
    },

    async searchOrgSkills() {
      if (!this.skillSearch.trim()) return;
      const r = await api('/api/orgs/' + encodeURIComponent(this.orgId) + '/admin/skills?q=' + encodeURIComponent(this.skillSearch.trim()));
      if (!r.ok) return;
      this.skillResults = (await r.json()).skills || [];
    },

    async copyToOrg(skillName) {
      const r = await api('/api/skills/' + encodeURIComponent(skillName) + '/copy-to-org', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_id: this.orgId }),
      });
      if (!r.ok) { toast('复制失败', 'error'); return; }
      toast('已复制: ' + skillName, 'success');
      refreshSkillList();
    },

    toggleSelectAll() {
      this.selectAll = !this.selectAll;
      this.selectedSkills = this.selectAll ? this.skillResults.map(function(s){ return s.name; }) : [];
    },
    toggleSelect(name) {
      var idx = this.selectedSkills.indexOf(name);
      if (idx >= 0) { this.selectedSkills.splice(idx, 1); }
      else { this.selectedSkills.push(name); }
    },
    async batchCopyToOrg() {
      if (!this.selectedSkills.length) { toast('请先选择技能', 'warn'); return; }
      var count = 0;
      for (var i = 0; i < this.selectedSkills.length; i++) {
        try {
          var r = await api('/api/skills/' + encodeURIComponent(this.selectedSkills[i]) + '/copy-to-org', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ org_id: this.orgId }),
          });
          if (r.ok) count++;
        } catch(e) {}
      }
      toast('已复制 ' + count + '/' + this.selectedSkills.length + ' 个技能', 'success');
      this.selectedSkills = [];
      this.selectAll = false;
      refreshSkillList();
    },

    async exportAuditCsv() {
      const r = await api('/api/orgs/' + encodeURIComponent(this.orgId) + '/admin/audit/export');
      if (!r.ok) { toast('导出失败', 'error'); return; }
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'audit-' + this.orgId + '.csv';
      a.click(); a.remove();
      toast('审计 CSV 已导出');
    },

    showSkill(name) { showDetail(name); }
  };
}

// ── Shared helper ─────────────────────────────────────

async function resolveAdminOrgId() {
  try {
    const ws = JSON.parse(localStorage.getItem('sd_workspace') || '{}');
    if (ws.org_id) return ws.org_id;
    if (ws.tenant_id && ws.tenant_id.indexOf('org:') === 0) return ws.tenant_id.split(':')[1];
    const r = await api('/api/orgs');
    if (!r.ok) return '';
    const orgs = (await r.json()).organizations || [];
    const adminOrg = orgs.find(o => o.role === 'org_admin');
    return adminOrg ? adminOrg.org_id : (orgs[0] ? orgs[0].org_id : '');
  } catch (e) { return ''; }
}

// ── Backward-compatible wrappers ─────────────────────

function showAdmin() {
  if (window.__alpineReady) {
    Alpine.store('nav').navigate('admin-view');
    document.getElementById('bar').style.display = 'none';
  } else {
    switchMainView('admin-view');
    document.getElementById('bar').style.display = 'none';
  }
}

function loadAdminConsole() {
  const el = document.querySelector('[x-data="adminView()"]');
  if (el && el.__x) { el.__x.$data.loadAll(); }
}

function exportAuditCsv() {
  const el = document.querySelector('[x-data="adminView()"]');
  if (el && el.__x) { el.__x.$data.exportAuditCsv(); }
}

// Legacy globals kept for backward compat
var _adminOrgId = '';

function updateAdminNavVisibility() {
  // Called from auth.js after login. Admin nav already renders via Alpine.
}
