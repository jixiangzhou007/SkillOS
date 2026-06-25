/* hub.js — Skill Marketplace (Alpine.js)
 * Route B: reactive market with catalog/detail/review/admin/revenue modes.
 */

var _hubReadOnly = true;

function hubScoreTone(score) {
  if (score >= 70) return 'good';
  if (score >= 50) return 'mid';
  return 'low';
}

function hubScoreColor(score) {
  var t = hubScoreTone(score);
  return t === 'good' ? 'var(--accent)' : t === 'mid' ? 'var(--warn)' : 'var(--err)';
}

function hubRoleLabel(role) {
  var map = { member: '成员', publisher: '发布者', reviewer: '审核员', admin: '管理员' };
  return map[role] || role;
}

function hubAuditActionLabel(action) {
  var map = { login: '登录', publish: '发布', review: '审核', install: '安装', user_create: '创建用户', user_delete: '删除用户' };
  return map[action] || action;
}

function hubDelegate(method) {
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x && el.__x.$data && typeof el.__x.$data[method] === 'function') {
    el.__x.$data[method].apply(el.__x.$data, Array.prototype.slice.call(arguments, 1));
    return true;
  }
  return false;
}

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

    // Pricing modal
    pricingFormOpen: false,
    pricingSkillId: '',
    pricingModel: 'free',
    pricingPrice: 0,
    pricingLoading: false,
    pricingSaving: false,

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
        this.categories = (d.categories || []).map(function(c) {
          return typeof c === 'string' ? c : (c.name || String(c));
        });
        if (this.page === 0) {
          try {
            var statsR = await api('/api/marketplace/stats');
            if (statsR.ok) this.stats = await statsR.json();
          } catch (e) { /* optional */ }
          try {
            var recR = await api('/api/marketplace/recommendations?limit=6');
            if (recR.ok) {
              var recD = await recR.json();
              this.recommendations = recD.recommendations || [];
            } else {
              this.recommendations = [];
            }
          } catch (e) { this.recommendations = []; }
        }
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
      var r = await api('/api/marketplace/subscribe?skill_id=' + encodeURIComponent(skillId) + '&auto_update=true', { method: 'POST' });
      if (!r.ok) { toast('订阅失败', 'error'); return; }
      toast('已订阅', 'success');
      this.showDetail(skillId);
    },
    async unsubscribe(skillId) {
      var r = await api('/api/marketplace/unsubscribe?skill_id=' + encodeURIComponent(skillId), { method: 'POST' });
      if (!r.ok) { toast('取消订阅失败', 'error'); return; }
      toast('已取消订阅', 'success');
      this.showDetail(skillId);
    },
    async install(skillId) {
      setStatus('安装中…');
      try {
        var sr = await api('/api/marketplace/skill/' + encodeURIComponent(skillId));
        if (!sr.ok) { toast('安装失败', 'error'); setStatus(''); return; }
        var s = await sr.json();
        var name = (s.name || 'hub-skill').replace(/[^a-zA-Z0-9\u4e00-\u9fff-]/g, '-').substring(0, 50);
        var cr = await api('/api/skills/create', {
          method: 'POST',
          body: JSON.stringify({ text: '保存技能: ' + name, content: s.content }),
        });
        if (!cr.ok) { toast('安装失败', 'error'); setStatus(''); return; }
        addMsg('sys', '已安装: ' + name);
        refreshSkillList();
        var installed = JSON.parse(localStorage.getItem(StorageKeys.INSTALLED_SKILLS) || '{}');
        installed[s.slug || skillId] = { skill_id: s.skill_id, name: s.name, version: s.version, installed_at: Date.now() / 1000 };
        localStorage.setItem(StorageKeys.INSTALLED_SKILLS, JSON.stringify(installed));
        checkHubUpdates();
        setStatus('已安装: ' + name);
      } catch (e) {
        toast('安装失败: ' + e.message, 'error');
        setStatus('');
      }
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

    // Review queue
    reviewItems: [],
    reviewLoading: false,

    // Admin panel
    adminLoading: false,
    adminUsers: [],
    adminEntries: [],
    adminStats: null,
    adminError: null,
    adminNewUser: '',
    adminNewPw: '',
    adminNewRole: 'member',

    // Revenue
    revenueLoading: false,
    revenueData: null,
    revenueError: null,

    roleLabel(role) { return hubRoleLabel(role); },
    auditLabel(action) { return hubAuditActionLabel(action); },
    formatTs(ts) {
      if (!ts) return '';
      try { return new Date(ts * 1000).toLocaleString(); } catch (e) { return ''; }
    },
    revenueModelLabel(model) {
      var map = { free: '免费', one_time: '一次性', subscription: '订阅' };
      return map[model] || model || '—';
    },
    pricingCommission() {
      return Math.round((parseFloat(this.pricingPrice) || 0) * 0.2 * 100) / 100;
    },
    pricingEarnings() {
      return Math.round((parseFloat(this.pricingPrice) || 0) * 0.8 * 100) / 100;
    },

    async openPricing(skillId) {
      if (this.readOnly) { toast('只读市场暂不支持修改定价', 'warn'); return; }
      this.pricingSkillId = skillId;
      this.pricingFormOpen = true;
      this.pricingLoading = true;
      this.pricingModel = 'free';
      this.pricingPrice = 0;
      try {
        var r = await api('/api/marketplace/pricing/get?skill_id=' + encodeURIComponent(skillId));
        if (r.ok) {
          var p = await r.json();
          this.pricingModel = p.model || 'free';
          this.pricingPrice = p.price || 0;
        }
      } catch (e) { /* keep defaults */ }
      this.pricingLoading = false;
    },
    closePricing() {
      this.pricingFormOpen = false;
      this.pricingSkillId = '';
      this.pricingSaving = false;
    },
    async savePricing() {
      if (!this.pricingSkillId || this.pricingSaving) return;
      this.pricingSaving = true;
      try {
        var r = await api('/api/marketplace/pricing/set', {
          method: 'POST',
          body: JSON.stringify({
            skill_id: this.pricingSkillId,
            model: this.pricingModel,
            price: parseFloat(this.pricingPrice) || 0,
          }),
        });
        if (!r.ok) {
          var err = await r.json().catch(function() { return {}; });
          toast(typeof err.detail === 'string' ? err.detail : '保存失败', 'error');
          return;
        }
        var d = await r.json();
        toast('定价已更新: ' + (d.pricing && d.pricing.formatted ? d.pricing.formatted : ''), 'success');
        this.closePricing();
      } catch (e) {
        toast('保存失败: ' + e.message, 'error');
      }
      this.pricingSaving = false;
    },

    async showReview() {
      this.mode = 'review';
      this.reviewLoading = true;
      try {
        var r = await api('/api/marketplace/pending-reviews');
        if (r.ok) { var d = await r.json(); this.reviewItems = d.pending || d.items || []; }
      } catch(e) { this.reviewItems = []; }
      this.reviewLoading = false;
    },
    async reviewSkill(skillId, approved) {
      var r = await api('/api/marketplace/review?skill_id=' + encodeURIComponent(skillId) + '&approved=' + (approved ? 'true' : 'false'), { method: 'POST' });
      if (!r.ok) { toast('审核失败', 'error'); return; }
      toast(approved ? '已通过' : '已拒绝', 'success');
      this.showReview();
    },

    async showAdmin() {
      this.mode = 'admin';
      this.adminLoading = true;
      this.adminError = null;
      try {
        var results = await Promise.all([
          api('/api/auth/users').then(function(r) { return r.json(); }),
          api('/api/auth/audit-log?limit=50').then(function(r) { return r.json(); }),
        ]);
        this.adminUsers = results[0].users || [];
        this.adminEntries = results[1].entries || [];
        this.adminStats = results[1].stats || null;
      } catch (e) {
        this.adminError = (e && e.message) ? e.message : '需要管理员权限';
        this.adminUsers = [];
        this.adminEntries = [];
      }
      this.adminLoading = false;
    },

    async adminCreateUser() {
      var username = (this.adminNewUser || '').trim();
      var password = (this.adminNewPw || '').trim();
      if (!username || !password) { toast('请填写用户名和密码', 'error'); return; }
      try {
        var r = await api('/api/auth/admin/register', {
          method: 'POST',
          body: JSON.stringify({ username: username, password: password, role: this.adminNewRole }),
        });
        var d = await r.json();
        if (d.error) { toast(d.error, 'error'); return; }
        this.adminNewUser = '';
        this.adminNewPw = '';
        toast('用户已创建', 'success');
        await this.showAdmin();
      } catch (e) { toast('创建失败: ' + e.message, 'error'); }
    },

    async adminChangeRole(userId, newRole) {
      try {
        await api('/api/auth/admin/update-user', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId, role: newRole }),
        });
        await this.showAdmin();
      } catch (e) { toast('更新角色失败', 'error'); }
    },

    async adminDeleteUser(userId) {
      if (!confirm('确定删除此用户？')) return;
      try {
        await api('/api/auth/admin/delete-user', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId }),
        });
        await this.showAdmin();
      } catch (e) { toast('删除失败', 'error'); }
    },

    async showRevenue() {
      if (this.readOnly) {
        toast('只读市场暂不支持收益面板', 'warn');
        return;
      }
      this.mode = 'revenue';
      this.revenueLoading = true;
      this.revenueError = null;
      this.revenueData = null;
      var user = localStorage.getItem(StorageKeys.USER) || 'anonymous';
      try {
        var r = await api('/api/marketplace/revenue/author?author_id=' + encodeURIComponent(user));
        if (!r.ok) throw new Error('需要登录');
        this.revenueData = await r.json();
      } catch (e) {
        this.revenueError = e.message || '加载失败';
      }
      this.revenueLoading = false;
    },

    showAdminLegacy() { this.showAdmin(); },
    showRevenueLegacy() { this.showRevenue(); },
    backToCatalog() { this.mode = 'catalog'; this.loadCatalog(true); },
  };
}

// ── Legacy wrappers (delegate to Alpine) ──────────────

function showHub() {
  if (window.__alpineReady && typeof Alpine !== 'undefined' && Alpine.store('nav')) {
    Alpine.store('nav').goTo('hub-view');
  } else {
    switchMainView('hub-view');
    document.getElementById('bar').style.display = 'none';
  }
  var el = document.querySelector('[x-data="hubView()"]');
  if (el && el.__x) { el.__x.$data.loadCatalog(); return; }
  loadHub();
}

function showHubSkill(skillId) {
  if (hubDelegate('showDetail', skillId)) return;
  showHub();
  setTimeout(function() { hubDelegate('showDetail', skillId); }, 150);
}

function hubStatusLabel(status) {
  var map = { approved: '已通过', pending: '待审核', rejected: '已拒绝' };
  return map[status] || status;
}

function applyMarketplaceMode(data) {
  _hubReadOnly = !!(data && data.read_only);
  ['hub-publish-btn', 'detail-publish-btn', 'hub-revenue-btn'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = _hubReadOnly ? 'none' : '';
  });
}

// Legacy catalog loader — delegates to Alpine hubView
async function loadHub() {
  if (hubDelegate('loadCatalog', true)) return;
  showHub();
}

function searchHub() {
  if (hubDelegate('search')) return;
  loadHub();
}

function filterHubCat(cat) {
  if (hubDelegate('filterCat', cat)) return;
  var sel = document.getElementById('hub-category');
  if (sel) sel.value = cat;
  searchHub();
}

function showReviewQueue() {
  if (hubDelegate('showReview')) return;
  showHub();
  setTimeout(function() { hubDelegate('showReview'); }, 150);
}

function showRevenueDashboard() {
  if (hubDelegate('showRevenue')) return;
  showHub();
  setTimeout(function() { hubDelegate('showRevenue'); }, 150);
}

function showAdminPanel() {
  if (hubDelegate('showAdmin')) return;
  showHub();
  setTimeout(function() { hubDelegate('showAdmin'); }, 150);
}

function showPublishForm(skillName) {
  if (_hubReadOnly) { toast('只读目录暂不支持发布', 'warn'); return; }
  // Navigate to hub-view first to ensure Alpine component is initialized
  showHub();
  setTimeout(function() {
    var el = document.querySelector('[x-data=\"hubView()\"]');
    if (el && el.__x) { el.__x.$data.openPublish(skillName); }
  }, 150);
}

function closePublishModal() {
  if (hubDelegate('closePublish')) return;
}

async function publishSkill() {
  if (hubDelegate('publish')) return;
  showPublishForm();
}

function subscribeSkill(skillId) {
  if (hubDelegate('subscribe', skillId)) return;
  showHubSkill(skillId);
}

function unsubscribeSkill(skillId) {
  if (hubDelegate('unsubscribe', skillId)) return;
  showHubSkill(skillId);
}

function installSkill(skillId) {
  if (hubDelegate('install', skillId)) return;
  showHub();
  setTimeout(function() { hubDelegate('install', skillId); }, 150);
}

function reviewSkill(skillId, approved) {
  if (hubDelegate('reviewSkill', skillId, approved)) return;
  showReviewQueue();
}

function checkHubUpdates() {

  let cfg = JSON.parse(localStorage.getItem(StorageKeys.INSTALLED_SKILLS) || '{}');

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

function showPricingModal(skillId) {
  if (_hubReadOnly) { toast('只读市场暂不支持修改定价', 'warn'); return; }
  if (hubDelegate('openPricing', skillId)) return;
  showHub();
  setTimeout(function() { hubDelegate('openPricing', skillId); }, 150);
}

function savePricing(skillId) {
  if (hubDelegate('savePricing')) return;
}

function adminCreateUser() {
  if (hubDelegate('adminCreateUser')) return;
}

function adminChangeRole(userId, newRole) {
  if (hubDelegate('adminChangeRole', userId, newRole)) return;
}

function adminDeleteUser(userId) {
  if (hubDelegate('adminDeleteUser', userId)) return;
}
