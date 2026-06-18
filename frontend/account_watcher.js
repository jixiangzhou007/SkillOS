function showAccountWatcher() {
  switchMainView('account-watcher-view');
  document.getElementById('bar').style.display = 'none';
  var el = document.getElementById('aw-content');
  el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text3)">加载中…</div>';
  fetch(API + '/api/knowledge/accounts').then(function(r){ return r.json(); }).then(function(d){
    var accounts = d.accounts || [];
    var h = '<div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:16px">公众号监控</div>';
  // Check WeChat login status
  fetch(API + '/api/knowledge/accounts/login-status').then(function(r){ return r.json(); }).then(function(s){
    var statusEl = document.getElementById('aw-login-status');
    if (statusEl) {
      if (s.logged_in) {
        statusEl.innerHTML = '<span style="color:var(--accent)">微信：已登录</span>';
      } else {
        statusEl.innerHTML = '<span style="color:var(--warn)">微信：未登录</span> <button class="nav-sm" onclick="showWeChatQR()" style="font-size:10px">登录</button>';
      }
    }
  });
    h += '<div id="aw-login-status" style="font-size:12px;color:var(--text3);margin-bottom:12px">检查微信登录状态…</div>';
    h += '<div style="display:flex;gap:8px;margin-bottom:16px"><input id="aw-name" placeholder="公众号名称" style="flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px 12px;color:var(--text);font-size:13px;outline:none"><input id="aw-interval" type="number" value="6" min="1" max="72" style="width:60px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px;color:var(--text);font-size:13px;outline:none" title="Hours"><button class="btn a" style="font-size:12px;padding:8px 16px" onclick="addWatchedAccount()">关注</button></div>';
    if (!accounts.length) {
      h += '<div class="empty-state"><div class="icon">X</div><div class="title">未关注任何公众号</div><div class="hint">添加公众号名称，自动抓取文章</div></div>';
    } else {
      accounts.forEach(function(a){
        var color = a.active ? 'var(--accent)' : 'var(--text3)';
        h += '<div class="skill-card" style="margin-bottom:6px"><div class="name">' + escHtml(a.name) + ' <span style="font-size:10px;color:' + color + '">' + (a.active ? '运行中' : '已暂停') + '</span></div><div class="meta">' + a.articles_seen + ' 篇文章，每 ' + (a.interval_hours||6) + 'h</div><div style="margin-top:4px;display:flex;gap:6px"><button class="nav-sm" data-name="'+escHtml(a.name)+'" onclick="checkAccountNow(this.dataset.name)" style="font-size:10px">检查</button><button class="nav-sm" data-name="'+escHtml(a.name)+'" onclick="removeAccount(this.dataset.name)" style="font-size:10px;color:var(--err)">移除</button></div></div>';
      });
    }
    el.innerHTML = h;
  });
}
function addWatchedAccount() {
  var name = document.getElementById('aw-name').value.trim();
  var interval = parseFloat(document.getElementById('aw-interval').value) || 6;
  if (!name) { toast('输入公众号名称', 'warn'); return; }
  toast('抓取中...', 'info');
  fetch(API + '/api/knowledge/accounts/add?name=' + encodeURIComponent(name) + '&interval_hours=' + interval, {method:'POST'}).then(function(r){ return r.json(); }).then(function(d){
    toast('发现 ' + (d.articles_found||0) + ' 篇文章，已摄入 ' + (d.ingested||0), 'success');
    showAccountWatcher();
  });
}
function removeAccount(name) { fetch(API + '/api/knowledge/accounts/remove?name=' + encodeURIComponent(name), {method:'POST'}).then(function(){ showAccountWatcher(); }); }
function checkAccountNow(name) { toast('检查中 ' + name + '...', 'info'); fetch(API + '/api/knowledge/accounts/check', {method:'POST'}).then(function(r){ return r.json(); }).then(function(d){ var found = d[name] ? d[name].new_articles : 0; toast(found + ' 篇新文章', found>0?'success':'info'); showAccountWatcher(); }); }

function showWeChatQR() {
  toast('获取二维码…', 'info');
  fetch(API + '/api/knowledge/accounts/login-qr').then(function(r){ return r.json(); }).then(function(d){
    if (d.qr_url) {
      var w = window.open('', 'wechat_qr', 'width=400,height=500');
      w.document.write('<html><body style="background:#000;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><div style="text-align:center"><h3 style="color:#fff;margin-bottom:16px">微信扫码登录</h3><img src="'+d.qr_url+'" style="max-width:300px"><p style="color:#888;margin-top:12px;font-size:12px">用微信扫描二维码登录</p></div></body></html>');
      toast('二维码已打开，扫码后刷新本页', 'success');
    } else {
      toast('已登录', 'success');
    }
  });
}
