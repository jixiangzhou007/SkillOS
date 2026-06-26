/* error-boundary.js — Global error handling, fetch interception, SSE reconnect */

// ── Offline banner ────────────────────────────────────
var _offlineBannerEl = null;
var _isOffline = false;

function _ensureBanner() {
  if (_offlineBannerEl) return _offlineBannerEl;
  _offlineBannerEl = document.createElement('div');
  _offlineBannerEl.className = 'offline-banner';
  _offlineBannerEl.innerHTML = '<span>⚡ 连接中断</span><button class="nav-sm" onclick="location.reload()">刷新</button>';
  _offlineBannerEl.style.display = 'none';
  document.body.appendChild(_offlineBannerEl);
  return _offlineBannerEl;
}

function showConnectionError() {
  _isOffline = true;
  var b = _ensureBanner();
  b.style.display = 'flex';
  if (typeof setDot === 'function') setDot('');
  if (typeof setStatus === 'function') setStatus('离线 · 重连中');
  _startReconnectPoll();
}

function showConnectionRestored() {
  _isOffline = false;
  var b = _offlineBannerEl;
  if (b) { b.style.display = 'none'; }
  if (typeof setDot === 'function') setDot('on');
  if (typeof setStatus === 'function') setStatus('就绪');
}

var _reconnectTimer = null;
function _startReconnectPoll() {
  if (_reconnectTimer) return;
  _reconnectTimer = setInterval(function() {
    fetch('/api/auth/me').then(function(r) {
      if (r.ok) { clearInterval(_reconnectTimer); _reconnectTimer = null; showConnectionRestored(); }
    }).catch(function() {});
  }, 5000);
}

// ── SSE reconnect ─────────────────────────────────────
var _sseRetryCount = 0;
var _sseMaxRetries = 3;

function resetSSERetry() { _sseRetryCount = 0; }

function sseRetryDelay() {
  var delays = [2000, 4000, 8000];
  return delays[Math.min(_sseRetryCount, delays.length - 1)];
}

// ── View-level error state ────────────────────────────

function renderErrorState(message, retryFn) {
  return '<div class="error-state">' +
    '<div class="error-state-icon">⚠️</div>' +
    '<div class="error-state-title">加载失败</div>' +
    '<div class="error-state-hint">' + (message || '请检查网络连接后重试') + '</div>' +
    (retryFn ? '<button class="action-btn" style="margin-top:var(--s-4)" onclick="(' + retryFn.toString() + ')()">重试</button>' : '') +
    '</div>';
}

// ── Global error handler ──────────────────────────────

window.addEventListener('error', function(e) {
  if (e.target && e.target.tagName === 'SCRIPT') {
    console.warn('Script load failed:', e.target.src);
  }
});

window.addEventListener('unhandledrejection', function(e) {
  console.warn('Unhandled promise rejection:', e.reason);
  if (e.reason && e.reason.message === 'Failed to fetch') {
    showConnectionError();
  }
});
