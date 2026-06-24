/* source_material.js — 从资料沉淀（链接 / 文件），复用 dispatch + ingest */

function isLikelyUrl(text) {
  var t = (text || '').trim();
  if (!t) return false;
  if (/^https?:\/\/\S+/i.test(t)) return true;
  if (/^github\.com\/[\w.-]+\/[\w.-]+/i.test(t)) return true;
  return false;
}

function normalizeSourceUrl(text) {
  var t = (text || '').trim();
  if (!t) return '';
  if (/^github\.com\//i.test(t)) return 'https://' + t.replace(/^https?:\/\//i, '');
  if (!/^https?:\/\//i.test(t) && t.indexOf('.') > 0 && !/\s/.test(t)) return 'https://' + t;
  return t;
}

function showPipelineWait(label) {
  if (typeof showIngestStrip === 'function') {
    showIngestStrip(label, _extractionSource || 'url');
  }
}

function hidePipelineWait() {
  if (typeof hideIngestStrip === 'function') hideIngestStrip();
}

function openSourceMaterialModal() {
  showChat();
  var bar = document.getElementById('bar');
  if (bar) bar.style.display = 'flex';
  var modal = document.getElementById('source-material-modal');
  if (modal) modal.classList.add('open');
  var inp = document.getElementById('source-url-input');
  if (inp) {
    inp.value = '';
    setTimeout(function() { inp.focus(); }, 80);
  }
}

function closeSourceMaterialModal() {
  var modal = document.getElementById('source-material-modal');
  if (modal) modal.classList.remove('open');
}

function startFromLink() {
  openSourceMaterialModal();
}

function startFromFile() {
  showChat();
  var bar = document.getElementById('bar');
  if (bar) bar.style.display = 'flex';
  var fi = document.getElementById('file-input');
  if (fi) fi.click();
}

function submitSourceUrl() {
  var inp = document.getElementById('source-url-input');
  var url = normalizeSourceUrl(inp && inp.value);
  if (!url || !isLikelyUrl(url)) {
    if (typeof toast === 'function') toast('请输入有效的网页或 GitHub 链接', 'warn');
    return;
  }
  closeSourceMaterialModal();
  var chatInp = document.getElementById('input');
  if (chatInp) {
    chatInp.value = url;
    if (typeof sendText === 'function') sendText();
  }
}

function onSourceUrlKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    submitSourceUrl();
  }
  if (e.key === 'Escape') closeSourceMaterialModal();
}

function maybeBeginSourceProgress(text, kind) {
  if (kind === 'file') {
    if (typeof setExtractionSource === 'function') setExtractionSource('file');
    showPipelineWait('正在解析文件并沉淀技能…');
    return true;
  }
  if (text && isLikelyUrl(text)) {
    if (typeof setExtractionSource === 'function') setExtractionSource('url');
    showPipelineWait('正在拉取链接并沉淀技能…');
    return true;
  }
  if (typeof setExtractionSource === 'function') setExtractionSource('conversation');
  return false;
}

function hideSourceProgress() {
  hidePipelineWait();
}
