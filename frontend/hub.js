/* hub.js — Skill Marketplace (Alpine.js)
 * Route B: reactive market with catalog/detail/review/admin/revenue modes.
 */

var _hubReadOnly = true;

// ── Alpine component ──────────────────────────────────

function hubView() {
  return {
    mode: 'catalog',        // catalog | detail | review | admin | revenue
    readOnly: true,
    skills: [],
    categories: [],
    searchQuery: '',
    selectedCategory: '',
    sortBy: 'score',        // score | name | recent
    page: 0,
    pageSize: 20,
    hasMore: false,
    totalCount: 0,
    stats: null,
    recommendations: [],
    detailSkill: null,
    detailScore: null,
    loading: false,
    publishing: false,
    publishFormOpen: false,
    publishName: '',
    publishDesc: '',
    publishCat: 'automation',
    publishContent: '',

    async init() {
      this.loading = true;
      await this.loadCatalog(true);
      this.loading = false;
    },

    async loadCatalog(reset) {
      if (reset) { this.page = 0; this.skills = []; }
      this.mode = 'catalog';
      this.loading = true;
      try {
        var q = encodeURIComponent(this.searchQuery || '');
        var cat = encodeURIComponent(this.selectedCategory || '');
        var url = '/api/marketplace/catalog?q=' + q + '&category=' + cat +
          '&sort=' + this.sortBy + '&offset=' + (this.page * this.pageSize) + '&limit=' + this.pageSize;
        var r = await api(url);
        if (!r.ok) { this.loading = false; return; }
        var d = await r.json();
        var newSkills = d.skills || [];
        if (this.page === 0) {
          this.skills = newSkills;
        } else {
          this.skills = this.skills.concat(newSkills);
        }
        this.categories = d.categories || [];
        this.stats = d.stats || null;
        this.recommendations = this.page === 0 ? (d.recommendations || []) : [];
        this.hasMore = newSkills.length >= this.pageSize;
        this.totalCount = d.total || this.skills.length;
        applyMarketplaceMode(d);
        this.readOnly = _hubReadOnly;
      } catch (e) { this.skills = []; }
      this.loading = false;
    },

    loadMore() {
      if (!this.hasMore || this.loading) return;
      this.page++;
      this.loadCatalog(false);
    },

    search() { this.loadCatalog(true); },
    setSort(sort) { this.sortBy = sort; this.loadCatalog(true); },
    filterCat(cat) {
      this.selectedCategory = (this.selectedCategory === cat) ? '' : cat;
      this.loadCatalog(true);
    },

    async showDetail(skillId) {
      this.mode = 'detail';
      this.loading = true;
      try {
        var r = await api('/api/marketplace/skill/' + encodeURIComponent(skillId));
        if (!r.ok) { this.loading = false; return; }
        var s = await r.json();
        this.detailSkill = s;
        // Fetch score separately
        try {
          var sr = await api('/api/marketplace/skill/' + encodeURIComponent(skillId) + '/score');
          if (sr.ok) this.detailScore = await sr.json();
        } catch (e) { this.detailScore = null; }
      } catch (e) { this.detailSkill = null; }
      this.loading = false;
    },

    scoreColor(score) {
      return score >= 70 ? 'var(--accent)' : score >= 50 ? 'var(--warn)' : 'var(--err)';
    },
    gateLabel(status) {
      var m = { approved: '已通过', pending: '待审核', rejected: '已拒绝' };
      return m[status] || status || '?';
    },

    async subscribe(skillId) {
      await api('/api/marketplace/subscribe/' + encodeURIComponent(skillId), { method: 'POST' });
      this.showDetail(skillId);
    },
    async unsubscribe(skillId) {
      await api('/api/marketplace/unsubscribe/' + encodeURIComponent(skillId), { method: 'POST' });
      this.showDetail(skillId);
    },
    async install(skillId) {
      var r = await api('/api/marketplace/install/' + encodeURIComponent(skillId), { method: 'POST' });
      if (!r.ok) { toast('Install failed', 'error'); return; }
      var d = await r.json();
      addMsg('sys', 'Installed: ' + (d.name || skillId));
      refreshSkillList();
      checkHubUpdates();
    },

    openPublish(skillName) {
      this.publishFormOpen = true;
      this.publishName = skillName || '';
    },
    closePublish() { this.publishFormOpen = false; },
    async publish() {
      var r = await api('/api/marketplace/publish', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: this.publishName, description: this.publishDesc,
          category: this.publishCat, content: this.publishContent,
        }),
      });
      if (!r.ok) { var e = await r.json().catch(function(){return{}}); toast(e.detail||'发布失败', 'error'); return; }
      toast('已发布', 'success');
      this.closePublish();
      showHub();
    },

    showReview() { this.mode = 'review'; /* load handled by old function */ },
    showAdmin() { this.mode = 'admin'; },
    showRevenue() { this.mode = 'revenue'; },
    backToCatalog() { this.mode = 'catalog'; this.loadCatalog(); },
  };
}

// ── Legacy wrappers (delegate to Alpine) ──────────────

function showHub() {
  switchMainView('hub-view');
  document.getElementById('bar').style.display = 'none';
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x) { el.__x.$data.loadCatalog(); return; }
  loadHub();
}

function searchHub() {
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x) { el.__x.$data.search(); }
}

function filterHubCat(cat) {
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x) { el.__x.$data.filterCat(cat); }
}

function showHubSkill(skillId) {
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x) { el.__x.$data.showDetail(skillId); return; }
  // Legacy fallback
  switchMainView('hub-view');
  var content = document.getElementById('hub-content');
  content.innerHTML = '<div style="color:var(--text3);padding:20px">加载中…</div>';
  api('/api/marketplace/skill/' + encodeURIComponent(skillId)).then(function(r){return r.json()}).then(function(s){
    var scoreColor = s.score >= 70 ? 'var(--accent)' : s.score >= 50 ? 'var(--warn)' : 'var(--err)';
    content.innerHTML = '<div style="padding:12px"><button class="nav-sm" onclick="showHub()">← 返回</button>' +
      '<div style="font-size:18px;font-weight:600;margin:12px 0">' + escHtml(s.name||skillId) + '</div>' +
      '<div style="display:flex;gap:12px;margin-bottom:12px"><span style="color:'+scoreColor+';font-weight:600">'+(s.score||'?')+'</span></div>' +
      '<div style="font-size:12px;color:var(--text3)">' + escHtml(s.description||'') + '</div></div>';
  });
}

function hubStatusLabel(status) {
  var map = { approved: '已通过', pending: '待审核', rejected: '已拒绝' };
  return map[status] || status;
}

function hubRoleLabel(role) {
  var map = { member: '成员', publisher: '发布者', reviewer: '审核员', admin: '管理员' };
  return map[role] || role;
}

function applyMarketplaceMode(data) {
  _hubReadOnly = !!(data && data.read_only);
  ['hub-publish-btn', 'detail-publish-btn', 'hub-revenue-btn'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = _hubReadOnly ? 'none' : '';
  });
}

// Legacy showHub removed — Alpine hubView() handles all rendering
function _showHub_legacy_removed() {

  switchMainView('hub-view');
  document.getElementById('bar').style.display = 'none';

  loadHub();

}

async function loadHub() {

  let el = document.getElementById('hub-content');
  let q = (document.getElementById('hub-search') || {}).value || '';
  let cat = (document.getElementById('hub-category') || {}).value || '';

  el.innerHTML = '<div style="color:var(--text3);text-align:center;padding:40px">加载市场目录…</div>';

  try {

    let catalogUrl = '/api/marketplace/catalog?q=' + encodeURIComponent(q) +
      '&category=' + encodeURIComponent(cat);
    let [sr, rr, recR] = await Promise.all([
      api('/api/marketplace/stats'),
      api(catalogUrl),
      api('/api/marketplace/recommendations?limit=4'),
    ]);
    if (!sr.ok || !rr.ok) throw new Error('加载失败');
    let stats = await sr.json();
    let data = await rr.json();
    let recData = recR.ok ? await recR.json() : { recommendations: [] };
    applyMarketplaceMode(data);

    let cats = data.categories || [];
    let selCat = cat;
    let h = '';
    if (data.read_only) {
      h += '<div style="padding:8px 12px;margin-bottom:12px;background:#1a2a1a;border:1px solid var(--accent);border-radius:8px;font-size:12px;color:var(--accent)">📖 只读目录 · 浏览官方/已审核技能，暂不支持 UGC 发布</div>';
    }

    h += '<div class="dash-grid" style="margin-bottom:16px">';

    h += '<div class="dash-card"><div class="value" style="color:var(--warn)">' + (data.total || stats.total || 0) + '</div><div class="label">目录</div></div>';

    h += '<div class="dash-card"><div class="value" style="color:var(--accent)">' + (stats.avg_score || 0) + '</div><div class="label">平均分</div></div>';

    h += '<div class="dash-card"><div class="value" style="color:var(--info)">' + (stats.pending_review || 0) + '</div><div class="label">待审核</div></div>';

    h += '</div>';

    h += '<div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap">';

    cats.forEach(c => {

      h += '<span class="kb-filter" data-cat="' + c.name + '" onclick="filterHubCat(\'' + c.name + '\')" style="padding:3px 10px;font-size:10px;border-radius:12px;cursor:pointer;background:' + (selCat===c.name?'var(--accent)':'var(--surface2)') + ';color:' + (selCat===c.name?'#fff':'var(--text2)') + ';border:1px solid var(--border)">' + c.name + ' (' + c.count + ')</span>';

    });

    h += '</div>';

    if (recData.recommendations && recData.recommendations.length && !q && !cat) {
      h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin:8px 0">✨ 为你推荐</div>';
      h += '<div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">';
      recData.recommendations.forEach(function(s) {
        h += '<div class="skill-card" style="flex:1;min-width:180px;max-width:240px;cursor:pointer;margin-bottom:0" onclick="showHubSkill(\'' + s.skill_id + '\')">';
        h += '<div class="name">' + escHtml(s.name) + '</div>';
        h += '<div class="meta"><span style="color:var(--accent)">' + (s.recommend_reason || '推荐') + '</span> · ' + s.score + ' 分</div>';
        h += '</div>';
      });
      h += '</div>';
    }

    if (!q && !cat && typeof fetchHubRoleTemplatesHtml === 'function') {
      h += await fetchHubRoleTemplatesHtml();
    }

    // Skill cards

    if (!data.skills || !data.skills.length) {

      h += '<div class="empty-state"><div class="icon">📦</div><div class="title">目录暂无技能</div><div class="hint">只读公共目录 — 后续将收录官方精选技能</div></div>';

    } else {

      data.skills.forEach(s => {

        let scoreColor = s.score >= 70 ? 'var(--accent)' : s.score >= 50 ? 'var(--warn)' : 'var(--err)';

        h += '<div class="skill-card" style="margin-bottom:8px;cursor:pointer" onclick="showHubSkill(\'' + s.skill_id + '\')">';

        h += '<div class="name">' + escHtml(s.name) + ' <span style="font-size:10px;color:var(--text3)">' + escHtml(s.author) + '</span></div>';

        h += '<div class="meta">';

        h += '<span style="color:' + scoreColor + ';font-weight:700">' + s.score + '</span> · ';

        h += '<span>' + s.category + '</span> · ';

        h += 'v' + s.version + ' · ';

        h += s.subscriptions + ' 订阅';

        if (s.subscribed) h += ' · <span style="color:var(--accent)">已订阅</span>';

        h += '</div>';

        h += '<div style="font-size:11px;color:var(--text3);margin-top:2px">' + escHtml(s.description || '').slice(0, 120) + '</div>';

        h += '</div>';

      });

    }

    el.innerHTML = h;

    // Update category dropdown

    let sel = document.getElementById('hub-category');

    sel.innerHTML = '<option value="">全部分类</option>' + cats.map(c => '<option value="' + c.name + '">' + c.name + ' (' + c.count + ')</option>').join('');
    if (cat) sel.value = cat;

  } catch(e) { el.innerHTML = '<div style="color:var(--err)">加载失败: ' + e.message + '</div>'; }

}

function searchHub() {
  loadHub();
}

function filterHubCat(cat) {

  document.getElementById('hub-category').value = cat;

  searchHub();

}

function _showHubSkill_legacy(skillId) {

  switchMainView('hub-view');

  let el = document.getElementById('hub-content');

  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载中…</div>';

  api('/api/marketplace/skill/' + encodeURIComponent(skillId)).then(r => r.json()).then(s => {

    let scoreColor = s.score >= 70 ? 'var(--accent)' : s.score >= 50 ? 'var(--warn)' : 'var(--err)';

    let h = '<button class="nav-sm" onclick="loadHub()">← 返回</button>';

    h += '<div style="margin-top:12px"><span style="font-size:18px;font-weight:700;color:var(--text)">' + escHtml(s.name) + '</span>';

    h += ' <span style="font-size:12px;color:var(--text3)">' + escHtml(s.author) + '</span></div>';



    h += '<div class="dash-grid" style="margin:12px 0">';

    h += '<div class="dash-card"><div class="value" style="color:' + scoreColor + '">' + s.score + '</div><div class="label">综合 /100</div></div>';

    h += '<div class="dash-card"><div class="value" style="color:var(--info)">' + s.execution_score + '</div><div class="label">执行分 (60%)</div></div>';

    h += '<div class="dash-card"><div class="value" style="color:var(--text2)">' + s.audit_score + '</div><div class="label">审计分 (40%)</div></div>';

    h += '</div>';



    let gateColor = s.status === 'approved' ? 'var(--accent)' : s.status === 'pending' ? 'var(--warn)' : 'var(--err)';

    h += '<div style="font-size:12px;padding:8px 12px;border-radius:6px;background:' + gateColor + '15;border:1px solid ' + gateColor + ';color:' + gateColor + ';margin-bottom:12px">';

    h += hubStatusLabel(s.status) + ': ' + escHtml(s.review_notes || '') + '</div>';



    // Cross-model info

    if (s.audit_json) {

      try {

        let audit = JSON.parse(s.audit_json);

        if (audit.execution_detail && audit.execution_detail.cross_model) {

          let cm = audit.execution_detail.cross_model;

          h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px">';

          h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px">跨模型验证</div>';

          if (cm.scores) {

            Object.entries(cm.scores).forEach(([model, sc]) => {

              h += '<div style="font-size:11px;color:var(--text3)">' + model + ': <span style="color:var(--text)">' + sc + '</span></div>';

            });

          }

          if (cm.variance !== undefined) {

            h += '<div style="font-size:11px;color:var(--text3);margin-top:4px">方差: ' + cm.variance + ' (' + (cm.confidence || '?') + ' 置信度)</div>';

          }

          if (cm.review) {

            h += '<div style="font-size:11px;color:var(--text3);margin-top:4px;font-style:italic">自评: ' + escHtml(cm.review) + '</div>';

          }

          h += '</div>';

        }

        // Test tasks used

        if (audit.test_tasks && audit.test_tasks.length) {

          h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px">';

          h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px">测试任务 (' + audit.test_tasks.length + ' 项用于评分)</div>';

          audit.test_tasks.forEach((t, i) => {

            h += '<div style="font-size:11px;color:var(--text3);padding:2px 0">' + (i+1) + '. ' + escHtml(t) + '</div>';

          });

          // Execution detail per task

          if (audit.execution_detail && audit.execution_detail.detail) {

            h += '<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">';

            audit.execution_detail.detail.forEach(d => {

              let sc = d.score >= 4 ? 'var(--accent)' : d.score >= 3 ? 'var(--warn)' : 'var(--err)';

              h += '<div style="font-size:11px;margin:4px 0;padding:4px 8px;background:var(--surface);border-radius:4px;border-left:2px solid ' + sc + '">';

              h += '<span style="color:' + sc + ';font-weight:600">' + d.score + '/5</span> ';

              h += '<span style="color:var(--text3)">' + escHtml(d.task || '').slice(0, 100) + '</span>';

              if (d.invoked !== undefined) h += ' <span style="font-size:10px;color:' + (d.invoked?'var(--accent)':'var(--err)') + '">' + (d.invoked?'已调用':'未调用') + '</span>';

              h += '</div>';

            });

            h += '</div>';

          }

          h += '</div>';

        }

      } catch(e) {}

    }



    // Audit checks

    if (s.audit_json) {

      try {

        let audit = JSON.parse(s.audit_json);

        if (audit.audit_checks && audit.audit_checks.length) {

          h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px">';

          h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px">八维审计</div>';

          audit.audit_checks.forEach(c => {

            let icon = c.severity === 'FAIL' ? '❌' : c.severity === 'WARN' ? '⚠️' : '✅';

            let color = c.severity==='FAIL' ? 'var(--err)' : c.severity==='WARN' ? 'var(--warn)' : 'var(--text3)';

            h += '<div style="font-size:11px;padding:3px 0;color:' + color + '">' + icon + ' <b>' + c.check + '</b>: ' + (c.detail||'').slice(0, 150) + '</div>';

            if (c.suggestion) h += '<div style="font-size:10px;color:var(--text3);padding-left:20px;margin-bottom:2px">💡 ' + escHtml(c.suggestion).slice(0, 120) + '</div>';

          });

          h += '</div>';

        }

      } catch(e) {}

    }



    // Meta

    h += '<div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;align-items:center">';

    h += '<span style="font-size:10px;padding:2px 8px;border-radius:8px;background:var(--surface2);color:var(--text3);border:1px solid var(--border)">' + s.category + '</span>';

    h += '<span style="font-size:10px;color:var(--text3)">v' + s.version + '</span>';

    h += '<span style="font-size:10px;color:var(--text3)">' + s.subscriptions + ' 订阅者</span>';

    h += '</div>';



    // Actions

    h += '<div style="display:flex;gap:8px;margin-bottom:12px">';

    if (s.subscribed) {

      h += '<button class="btn" style="background:var(--surface2);border:1px solid var(--warn);color:var(--warn);font-size:12px;padding:6px 14px" onclick="unsubscribeSkill(\'' + s.skill_id + '\')">取消订阅</button>';

    } else {

      h += '<button class="btn a" style="font-size:12px;padding:6px 14px" onclick="subscribeSkill(\'' + s.skill_id + '\')">订阅</button>';

    }

    h += '<button class="btn" style="background:var(--surface2);border:1px solid var(--accent);color:var(--accent);font-size:12px;padding:6px 14px" onclick="installSkill(\'' + s.skill_id + '\')">安装</button>';

    if (!_hubReadOnly) {
      h += '<button class="nav-sm" style="font-size:10px" onclick="showPricingModal(\'' + s.skill_id + '\')">定价</button>';
    }

    h += '</div>';



    // Content preview

    h += '<details style="margin-bottom:12px"><summary style="cursor:pointer;font-size:12px;color:var(--text3)">查看 SKILL.md</summary>';

    h += '<pre style="white-space:pre-wrap;font:11px var(--mono);color:var(--text3);background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:300px;overflow-y:auto;margin-top:8px">' + escHtml((s.content||'').slice(0, 2000)) + '</pre>';

    h += '</details>';



    el.innerHTML = h;

  });

}

function showPublishForm(skillName) {

  if (_hubReadOnly) {
    toast('公共市场当前为只读目录，暂不支持发布', 'warn');
    return;
  }

  document.getElementById('publish-modal').classList.add('open');

  // If a skill name is provided, pre-fill from local skill

  if (skillName) {

    fetch(API + '/api/skills/' + encodeURIComponent(skillName)).then(r => r.json()).then(s => {

      document.getElementById('pub-name').value = s.name || skillName;

      document.getElementById('pub-desc').value = '';

      document.getElementById('pub-content').value = s.content || '';

    }).catch(() => {});

  }

}

function closePublishModal() {

  document.getElementById('publish-modal').classList.remove('open');

}

async function publishSkill() {

  let name = document.getElementById('pub-name').value.trim();

  let desc = document.getElementById('pub-desc').value.trim();

  let cat = document.getElementById('pub-cat').value;

  let content = document.getElementById('pub-content').value.trim();

  if (!name || !content) { toast('请填写名称与内容', 'error'); return; }

  let btn = document.querySelector('#publish-modal .modal-btn-primary');

  btn.textContent = '评分中…'; btn.disabled = true;

  try {

    let r = await api('/api/marketplace/publish', {

      method: 'POST',

      body: JSON.stringify({ name, description: desc, category: cat, content, author: localStorage.getItem('sd_user') || 'anonymous' })

    });

    if (!r.ok) {
      let err = await r.json().catch(function() { return {}; });
      toast(typeof err.detail === 'string' ? err.detail : '发布失败', 'error');
      return;
    }

    let d = await r.json();

    closePublishModal();

    addMsg('sys', '📦 已发布: ' + name + ' — 评分: ' + (d.score ? d.score.overall : '?') + '/100, ' + d.gate);

    showHub();

  } catch(e) {

    toast('发布失败: ' + e.message, 'error');

  }

  btn.textContent = '发布并评分'; btn.disabled = false;

}

function subscribeSkill(skillId) {

  api('/api/marketplace/subscribe?skill_id=' + encodeURIComponent(skillId) + '&auto_update=true', { method: 'POST' })

    .then(r => r.json()).then(d => { showHubSkill(skillId); toast('已订阅'); });

}

function unsubscribeSkill(skillId) {

  api('/api/marketplace/unsubscribe?skill_id=' + encodeURIComponent(skillId), { method: 'POST' })

    .then(r => r.json()).then(d => { showHubSkill(skillId); toast('已取消订阅'); });

}

function installSkill(skillId) {

  setStatus('安装中…');

  api('/api/marketplace/skill/' + encodeURIComponent(skillId)).then(r => r.json()).then(s => {

    let name = (s.name || 'hub-skill').replace(/[^a-zA-Z0-9一-鿿-]/g, '-').substring(0, 50);

    api('/api/skills/create', {

      method: 'POST',

      body: JSON.stringify({ text: '保存技能: ' + name, content: s.content })

    }).then(r => r.json()).then(d => {

      addMsg('sys', '已安装: ' + name);

      refreshSkillList();

      // Track for update badge

      let installed = JSON.parse(localStorage.getItem('sd_installed_skills') || '{}');

      installed[s.slug] = { skill_id: s.skill_id, name: s.name, version: s.version, installed_at: Date.now()/1000 };

      localStorage.setItem('sd_installed_skills', JSON.stringify(installed));

      checkHubUpdates();

      setStatus('已安装: ' + name);

    });

  });

}

function showReviewQueue() {

  let el = document.getElementById('hub-content');

  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载审核队列…</div>';

  api('/api/marketplace/pending-reviews').then(r => r.json()).then(d => {

    let pending = d.pending || [];

    let h = '<button class="nav-sm" onclick="loadHub()">← 返回</button>';

    h += '<div style="font-size:16px;font-weight:700;color:var(--warn);margin:12px 0">审核队列 (' + pending.length + ' 待审)</div>';

    if (!pending.length) {

      h += '<div class="empty-state"><div class="icon">✅</div><div class="title">全部完成</div><div class="hint">暂无待人工审核的技能</div></div>';

    } else {

      pending.forEach(s => {

        let scoreColor = s.score >= 70 ? 'var(--accent)' : s.score >= 50 ? 'var(--warn)' : 'var(--err)';

        h += '<div class="skill-card" style="margin-bottom:8px">';

        h += '<div class="name">' + escHtml(s.name) + ' <span style="font-size:10px;color:var(--text3)">' + escHtml(s.author) + '</span></div>';

        h += '<div class="meta"><span style="color:' + scoreColor + ';font-weight:700">' + s.score + '/100</span> · ' + s.category + ' · v' + s.version + '</div>';

        h += '<div style="font-size:11px;color:var(--text2);margin:4px 0">' + escHtml(s.review_notes || '') + '</div>';

        h += '<div style="display:flex;gap:6px;margin-top:6px">';

        h += '<button class="btn a" style="font-size:11px;padding:4px 14px" onclick="reviewSkill(\'' + s.skill_id + '\',true)">通过</button>';

        h += '<button class="btn" style="background:var(--err);color:#fff;font-size:11px;padding:4px 14px;border:none" onclick="reviewSkill(\'' + s.skill_id + '\',false)">拒绝</button>';

        h += '<button class="nav-sm" style="font-size:10px" onclick="showHubSkill(\'' + s.skill_id + '\')">详情</button>';

        h += '</div></div>';

      });

    }

    el.innerHTML = h;

  });

}

function reviewSkill(skillId, approved) {

  let notes = approved ? '人工通过' : prompt('拒绝原因:');

  if (notes === null) return;

  api('/api/marketplace/review?skill_id=' + encodeURIComponent(skillId) + '&approved=' + (approved ? 'true' : 'false') + '&notes=' + encodeURIComponent(notes || '人工审核'), {

    method: 'POST',

  }).then(r => r.json()).then(d => {

    toast(approved ? '已通过' : '已拒绝');

    showReviewQueue();

  });

}

function checkHubUpdates() {

  let cfg = JSON.parse(localStorage.getItem('sd_installed_skills') || '{}');

  let skills = Object.entries(cfg).map(([slug, info]) => ({ skill_id: info.skill_id, version: info.version || 1 }));

  if (!skills.length) return;

  fetch(API + '/api/marketplace/check-updates?skills=' + encodeURIComponent(JSON.stringify(skills)))

    .then(r => r.json()).then(d => {

      let badge = document.getElementById('hub-badge');

      let count = d.updates_available || 0;

      if (count > 0) {

        badge.style.display = 'block';

        badge.textContent = count;

      } else {

        badge.style.display = 'none';

      }

    }).catch(() => {});

}

function showRevenueDashboard() {

  if (_hubReadOnly) {
    toast('只读市场暂不支持收益面板', 'warn');
    return;
  }

  let user = localStorage.getItem('sd_user') || 'anonymous';

  let el = document.getElementById('hub-content');

  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载收益数据…</div>';

  api('/api/marketplace/revenue/author?author_id=' + encodeURIComponent(user))

    .then(r => r.ok ? r.json() : Promise.reject(new Error('需要登录'))).then(d => {

      let h = '<button class="nav-sm" onclick="loadHub()">← 返回</button>';

      h += '<div style="font-size:16px;font-weight:700;color:var(--accent);margin:12px 0">收益面板</div>';

      h += '<div class="dash-grid" style="margin-bottom:16px">';

      h += '<div class="dash-card"><div class="value" style="color:var(--accent)">' + d.total_sales + '</div><div class="label">总销量</div></div>';

      h += '<div class="dash-card"><div class="value" style="color:var(--info)">$' + d.total_revenue + '</div><div class="label">总流水</div></div>';

      h += '<div class="dash-card"><div class="value" style="color:var(--warn)">$' + d.total_earnings + '</div><div class="label">你的收益 (' + Math.round((1-d.commission_rate)*100) + '%)</div></div>';

      h += '</div>';

      if (d.recent_purchases && d.recent_purchases.length) {

        h += '<div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px">最近购买</div>';

        d.recent_purchases.forEach(p => {

          let dt = new Date(p.created_at*1000).toLocaleString();

          h += '<div style="font-size:11px;padding:2px 0;color:var(--text3)">' + p.purchase_id + ' — $' + p.amount + ' (' + p.model + ') — ' + dt + '</div>';

        });

      }

      el.innerHTML = h;

    }).catch(e => { el.innerHTML = '<div style="color:var(--err)">' + e.message + '</div>'; });

}

function showPricingModal(skillId) {

  if (_hubReadOnly) {
    toast('只读市场暂不支持修改定价', 'warn');
    return;
  }

  api('/api/marketplace/pricing/get?skill_id=' + encodeURIComponent(skillId)).then(r => r.json()).then(p => {

    let h = '<div id="pricing-modal-inner" style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:101;background:rgba(0,0,0,.65)">';

    h += '<div class="modal-box" style="max-width:400px"><h3>设置定价</h3>';

    h += '<label>模式</label><select id="price-model" style="width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:9px 12px;color:var(--text);font-size:13px;outline:none;margin-top:4px"><option value="free"' + (p.model==='free'?' selected':'') + '>免费</option><option value="one_time"' + (p.model==='one_time'?' selected':'') + '>一次性购买</option><option value="subscription"' + (p.model==='subscription'?' selected':'') + '>按月订阅</option></select>';

    h += '<label>价格 ($)</label><input id="price-amount" type="number" min="0" step="1" value="' + p.price + '" style="width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:9px 12px;color:var(--text);font-size:13px;outline:none;margin-top:4px">';

    h += '<div style="font-size:11px;color:var(--text3);margin-top:4px">平台抽成: $' + Math.round((p.price||0)*0.2*100)/100 + ' (20%) — 你的收益: $' + Math.round((p.price||0)*0.8*100)/100 + '</div>';

    h += '<div class="modal-actions">';

    h += '<button class="modal-btn-cancel" onclick="document.getElementById(\'pricing-modal-inner\').remove()">取消</button>';

    h += '<button class="modal-btn-primary" onclick="savePricing(\'' + skillId + '\')">保存</button>';

    h += '</div></div></div>';

    document.body.insertAdjacentHTML('beforeend', h);

    document.getElementById('pricing-modal-inner').addEventListener('click', function(e) { if (e.target===this) this.remove(); });

  });

}

function savePricing(skillId) {

  let model = document.getElementById('price-model').value;

  let price = parseFloat(document.getElementById('price-amount').value) || 0;

  api('/api/marketplace/pricing/set', {

    method: 'POST',

    body: JSON.stringify({ skill_id: skillId, model, price })

  }).then(async r => {
    if (!r.ok) {
      let err = await r.json().catch(function() { return {}; });
      toast(typeof err.detail === 'string' ? err.detail : '保存失败', 'error');
      return;
    }
    return r.json();
  }).then(d => {
    if (!d) return;
    document.getElementById('pricing-modal-inner').remove();
    toast('定价已更新: ' + d.pricing.formatted);
  });

}

function showAdminPanel() {

  let el = document.getElementById('hub-content');

  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载管理面板…</div>';

  Promise.all([

    api('/api/auth/users').then(r => r.json()),

    api('/api/auth/audit-log?limit=50').then(r => r.json()),

  ]).then(([ud, ad]) => {

    let users = ud.users || [];

    let entries = ad.entries || [];

    let h = '<button class="nav-sm" onclick="loadHub()">← 返回</button>';

    h += '<div style="font-size:16px;font-weight:700;color:var(--info);margin:12px 0">管理面板</div>';



    h += '<div class="dash-grid" style="margin-bottom:16px">';

    h += '<div class="dash-card"><div class="value" style="color:var(--info)">' + users.length + '</div><div class="label">用户</div></div>';

    h += '<div class="dash-card"><div class="value" style="color:var(--text2)">' + (ad.stats ? ad.stats.total_events : entries.length) + '</div><div class="label">审计事件</div></div>';

    h += '</div>';



    h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px">用户管理</div>';

    h += '<div style="display:flex;gap:6px;margin-bottom:12px">';

    h += '<input id="admin-new-user" placeholder="用户名" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:4px 8px;color:var(--text);font-size:11px;width:100px">';

    h += '<input id="admin-new-pw" placeholder="密码" type="password" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:4px 8px;color:var(--text);font-size:11px;width:100px">';

    h += '<select id="admin-new-role" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:4px;color:var(--text);font-size:11px"><option value="member">成员</option><option value="publisher">发布者</option><option value="reviewer">审核员</option><option value="admin">管理员</option></select>';

    h += '<button class="nav-sm" onclick="adminCreateUser()" style="font-size:10px">+ 创建</button>';

    h += '</div>';



    users.forEach(u => {

      let roleColor = u.role==='admin'?'var(--warn)':u.role==='reviewer'?'var(--info)':'var(--text3)';

      h += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px 12px;margin-bottom:4px;display:flex;align-items:center;gap:8px">';

      h += '<span style="font-weight:600;color:var(--text);font-size:12px">' + escHtml(u.username) + '</span>';

      h += '<span style="font-size:10px;color:' + roleColor + ';padding:1px 6px;border-radius:4px;background:' + roleColor + '15">' + hubRoleLabel(u.role) + '</span>';

      h += '<span style="font-size:10px;color:var(--text3)">' + (u.email||'') + '</span>';

      h += '<span style="flex:1"></span>';

      if (u.role !== 'admin') {

        h += '<select onchange="adminChangeRole(\'' + u.user_id + '\',this.value)" style="background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:2px 4px;color:var(--text);font-size:10px">';

        ['member','publisher','reviewer','admin'].forEach(r => { h += '<option value="' + r + '"' + (u.role===r?' selected':'') + '>' + hubRoleLabel(r) + '</option>'; });

        h += '</select>';

        h += '<button class="nav-sm" onclick="adminDeleteUser(\'' + u.user_id + '\')" style="font-size:10px;color:var(--err)">✕</button>';

      }

      h += '</div>';

    });



    // Audit log

    h += '<div style="font-size:13px;font-weight:600;color:var(--text2);margin:20px 0 8px">最近活动</div>';

    if (!entries.length) {

      h += '<div style="color:var(--text3);font-size:12px">暂无审计记录</div>';

    } else {

      entries.slice(0, 30).forEach(e => {

        let icon = {login:'🔑',publish:'📦',review:'✅',install:'📥',user_create:'👤',user_delete:'🗑️'}[e.action]||'📌';

        let dt = new Date(e.created_at*1000).toLocaleString();

        h += '<div style="font-size:11px;padding:3px 0;color:var(--text3);border-bottom:1px solid var(--border)">';

        h += icon + ' <b>' + e.username + '</b> ' + e.action + ' — ' + (e.detail||e.target) + ' <span style="float:right">' + dt + '</span></div>';

      });

    }



    el.innerHTML = h;

  }).catch(e => { el.innerHTML = '<div style="color:var(--err)">需要管理员权限 (' + e.message + ')</div>'; });

}

function adminCreateUser() {

  let username = document.getElementById('admin-new-user').value.trim();

  let password = document.getElementById('admin-new-pw').value.trim();

  let role = document.getElementById('admin-new-role').value;

  if (!username || !password) { toast('请填写用户名和密码', 'error'); return; }

  fetch(API + '/api/auth/admin/register', {

    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },

    body: JSON.stringify({ username, password, role })

  }).then(r => r.json()).then(d => {

    if (d.error) { alert(d.error); return; }

    showAdminPanel();

  });

}

function adminChangeRole(userId, newRole) {

  fetch(API + '/api/auth/admin/update-user', {

    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },

    body: JSON.stringify({ user_id: userId, role: newRole })

  }).then(r => r.json()).then(d => { showAdminPanel(); });

}

function adminDeleteUser(userId) {

  if (!confirm('确定删除此用户？')) return;

  fetch(API + '/api/auth/admin/delete-user', {

    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },

    body: JSON.stringify({ user_id: userId })

  }).then(r => r.json()).then(d => { showAdminPanel(); });

}

