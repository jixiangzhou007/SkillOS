/* error-boundary.js — Global error handling, fetch interception, SSE reconnect */

// ── Connection error UI ──────────────────────────────

function showConnectionError() {
  if (typeof addMsg === 'function') {
    addMsg('sys', '⚠️ 连接中断，正在重试… <button class="nav-sm" style="font-size:11px;margin-left:6px" onclick="retryLastRequest()">重试</button>');
  }
  if (typeof setDot === 'function') setDot('');
  if (typeof setStatus === 'function') setStatus('离线');
}

function showConnectionRestored() {
  if (typeof setDot === 'function') setDot('on');
  if (typeof setStatus === 'function') setStatus('就绪');
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
    (retryFn ? '<button class="action-btn" onclick="(' + retryFn.toString() + ')()" style="font-size:var(--t-sm);padding:8px 20px;margin-top:12px">重试</button>' : '') +
    '</div>';
}

// ── Global error handler ──────────────────────────────

window.addEventListener('error', function(e) {
  // Only handle network/script errors, not React/Alpine internal errors
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
