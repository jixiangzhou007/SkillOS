/* docs.js — in-app documentation (Sprint 7) */

var _DOC_SOURCES = {
  quickstart: {
    title: '快速开始',
    api: '/api/docs/quickstart',
    static: '/docs/quickstart.md'
  },
  guide: {
    title: 'SkillOS 用户指南',
    api: '/api/docs/guide',
    static: '/docs/user_guide.md'
  }
};

function showDocs() {
  switchMainView('docs-view');
  document.getElementById('bar').style.display = 'none';
  loadDocs('quickstart');
}

function renderDocMarkdown(text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text || '');
  }
  return '<pre class="doc-fallback">' + escHtml(text || '') + '</pre>';
}

function bindDocLinks(container) {
  if (!container) return;
  container.querySelectorAll('a[href]').forEach(function(a) {
    var href = a.getAttribute('href') || '';
    if (href.indexOf('/api/docs/guide') !== -1 || href.indexOf('user_guide') !== -1) {
      a.href = '#';
      a.onclick = function(e) { e.preventDefault(); loadDocs('guide'); };
    } else if (href.indexOf('/api/docs/quickstart') !== -1 || href.indexOf('quickstart') !== -1) {
      a.href = '#';
      a.onclick = function(e) { e.preventDefault(); loadDocs('quickstart'); };
    } else if (href.startsWith('/api/docs/')) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
  });
}

async function _fetchDocContent(section) {
  var spec = _DOC_SOURCES[section] || _DOC_SOURCES.quickstart;
  var content = '';
  var title = spec.title;
  var source = '';

  try {
    var r = typeof api === 'function' ? await api(spec.api) : await fetch(spec.api);
    if (r.ok) {
      var d = await r.json();
      content = d.content || '';
      title = d.title || title;
      source = 'api';
    }
  } catch (_) {}

  if (!content) {
    var sr = await fetch(spec.static);
    if (!sr.ok) throw new Error('HTTP ' + sr.status);
    content = await sr.text();
    source = 'static';
  }

  return { content: content, title: title, source: source };
}

async function loadDocs(section) {
  var el = document.getElementById('docs-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);padding:20px">加载文档…</div>';

  try {
    var doc = await _fetchDocContent(section);
    el.innerHTML =
      '<article class="doc-content">' + renderDocMarkdown(doc.content) + '</article>' +
      (doc.source === 'static'
        ? '<div style="font-size:11px;color:var(--text3);margin-top:12px">（离线文档副本）</div>'
        : '');
    bindDocLinks(el);
  } catch (e) {
    el.innerHTML =
      '<div style="color:var(--err);padding:20px">' +
      '文档加载失败：' + escHtml(e.message) +
      '<div style="margin-top:12px;font-size:12px;color:var(--text3)">请通过 SkillOS 服务访问（如 <code>http://127.0.0.1:8765</code>），不要单独打开 HTML 文件。</div>' +
      '<button class="nav-sm" style="margin-top:12px" onclick="loadDocs(' + JSON.stringify(section) + ')">重试</button></div>';
  }

  document.querySelectorAll('#docs-view .tab').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-doc') === section);
  });
}
