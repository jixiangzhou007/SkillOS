/* SkillOS — Account Watcher (Alpine.js)
 * Phase 1 migration — first Alpine component.
 * Old global functions kept as backward-compat wrappers.
 */

function accountWatcherView() {
  return {
    loading: true,
    accounts: [],
    loginStatus: null,  // { logged_in, qr_url }

    async init() {
      this.loading = true;
      try {
        const r = await fetch(API + '/api/knowledge/accounts');
        const d = await r.json();
        this.accounts = d.accounts || [];
      } catch (e) {
        this.accounts = [];
      }
      try {
        const r = await fetch(API + '/api/knowledge/accounts/login-status');
        const s = await r.json();
        this.loginStatus = s;
      } catch (e) {
        this.loginStatus = { logged_in: false };
      }
      this.loading = false;
    },

    async addAccount() {
      const name = this.$refs.awName.value.trim();
      const interval = parseFloat(this.$refs.awInterval.value) || 6;
      if (!name) { toast('输入公众号名称', 'warn'); return; }
      toast('抓取中...', 'info');
      try {
        const r = await fetch(API + '/api/knowledge/accounts/add?name=' + encodeURIComponent(name) + '&interval_hours=' + interval, { method: 'POST' });
        const d = await r.json();
        toast('发现 ' + (d.articles_found || 0) + ' 篇文章，已摄入 ' + (d.ingested || 0), 'success');
      } catch (e) {
        toast('添加失败: ' + e.message, 'error');
      }
      await this.init();
    },

    async removeAccount(name) {
      await fetch(API + '/api/knowledge/accounts/remove?name=' + encodeURIComponent(name), { method: 'POST' });
      await this.init();
    },

    async checkNow(name) {
      toast('检查中 ' + name + '...', 'info');
      try {
        const r = await fetch(API + '/api/knowledge/accounts/check', { method: 'POST' });
        const d = await r.json();
        const found = d[name] ? d[name].new_articles : 0;
        toast(found + ' 篇新文章', found > 0 ? 'success' : 'info');
      } catch (e) {
        toast('检查失败: ' + e.message, 'error');
      }
      await this.init();
    },

    async showQR() {
      toast('获取二维码…', 'info');
      try {
        const r = await fetch(API + '/api/knowledge/accounts/login-qr');
        const d = await r.json();
        if (d.qr_url) {
          const w = window.open('', 'wechat_qr', 'width=400,height=500');
          w.document.write('<html><body style="background:#000;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><div style="text-align:center"><h3 style="color:#fff;margin-bottom:16px">微信扫码登录</h3><img src="'+d.qr_url+'" style="max-width:300px"><p style="color:#888;margin-top:12px;font-size:12px">用微信扫描二维码登录</p></div></body></html>');
          toast('二维码已打开，扫码后刷新本页', 'success');
        } else {
          toast('已登录', 'success');
        }
      } catch (e) {
        toast('获取二维码失败: ' + e.message, 'error');
      }
    }
  };
}

// ── Backward-compatible wrappers ─────────────────────

function showAccountWatcher() {
  if (window.__alpineReady) {
    Alpine.store('nav').navigate('account-watcher-view');
  } else {
    switchMainView('account-watcher-view');
    document.getElementById('bar').style.display = 'none';
  }
}

function addWatchedAccount() {
  // Legacy onclick — find active Alpine component or fallback
  const el = document.querySelector('[x-data="accountWatcherView()"]');
  if (el && el.__x) {
    el.__x.$data.addAccount();
  }
}

function removeAccount(name) {
  const el = document.querySelector('[x-data="accountWatcherView()"]');
  if (el && el.__x) {
    el.__x.$data.removeAccount(name);
  } else {
    fetch(API + '/api/knowledge/accounts/remove?name=' + encodeURIComponent(name), { method: 'POST' }).then(function () { showAccountWatcher(); });
  }
}

function checkAccountNow(name) {
  const el = document.querySelector('[x-data="accountWatcherView()"]');
  if (el && el.__x) {
    el.__x.$data.checkNow(name);
  } else {
    toast('检查中 ' + name + '...', 'info');
    fetch(API + '/api/knowledge/accounts/check', { method: 'POST' }).then(function (r) { return r.json(); }).then(function (d) {
      var found = d[name] ? d[name].new_articles : 0;
      toast(found + ' 篇新文章', found > 0 ? 'success' : 'info');
      showAccountWatcher();
    });
  }
}

function showWeChatQR() {
  const el = document.querySelector('[x-data="accountWatcherView()"]');
  if (el && el.__x) {
    el.__x.$data.showQR();
  }
}
