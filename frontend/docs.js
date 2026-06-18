/* SkillOS — In-App Documentation (Alpine.js)
 * Phase 2 migration. Markdown rendering via marked CDN global.
 */

const _DOC_SOURCES = {
  quickstart: { title: '快速开始', api: '/api/docs/quickstart', static: '/docs/quickstart.md' },
  guide: { title: 'SkillOS 用户指南', api: '/api/docs/guide', static: '/docs/user_guide.md' }
};

function docsView() {
  return {
    section: 'quickstart',
    content: '',
    title: '',
    source: '',
    loading: false,
    error: '',

    async init() {
      this.section = 'quickstart';
      await this.loadSection('quickstart');
    },

    async loadSection(section) {
      this.section = section;
      this.loading = true;
      this.error = '';
      const spec = _DOC_SOURCES[section] || _DOC_SOURCES.quickstart;

      try {
        // Try API first
        let content = '';
        let source = '';
        try {
          const r = typeof api === 'function' ? await api(spec.api) : await fetch(spec.api);
          if (r.ok) {
            const d = await r.json();
            content = d.content || '';
            this.title = d.title || spec.title;
            source = 'api';
          }
        } catch (_) { /* fall through to static */ }

        // Fallback to static file
        if (!content) {
          const sr = await fetch(spec.static);
          if (!sr.ok) throw new Error('HTTP ' + sr.status);
          content = await sr.text();
          this.title = spec.title;
          source = 'static';
        }

        this.content = renderDocMarkdown(content);
        this.source = source;
        this.error = '';

        // Re-bind internal links after render
        this.$nextTick(() => bindDocLinks(this.$refs.docBody));
      } catch (e) {
        this.error = e.message || '未知错误';
        this.content = '';
      }
      this.loading = false;
    }
  };
}

// ── Utility (shared with old code) ────────────────────

function renderDocMarkdown(text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text || '');
  }
  return '<pre class="doc-fallback">' + escHtml(text || '') + '</pre>';
}

function bindDocLinks(container) {
  if (!container) return;
  container.querySelectorAll('a[href]').forEach(function (a) {
    const href = a.getAttribute('href') || '';
    if (href.indexOf('/api/docs/guide') !== -1 || href.indexOf('user_guide') !== -1) {
      a.href = '#';
      a.onclick = function (e) { e.preventDefault(); loadDocs('guide'); };
    } else if (href.indexOf('/api/docs/quickstart') !== -1 || href.indexOf('quickstart') !== -1) {
      a.href = '#';
      a.onclick = function (e) { e.preventDefault(); loadDocs('quickstart'); };
    } else if (href.startsWith('/api/docs/')) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
  });
}

// ── Backward-compatible wrappers ─────────────────────

function showDocs() {
  if (window.__alpineReady) {
    Alpine.store('nav').navigate('docs-view');
  } else {
    switchMainView('docs-view');
    document.getElementById('bar').style.display = 'none';
  }
}

function loadDocs(section) {
  // Delegate to Alpine component if available
  const el = document.querySelector('[x-data="docsView()"]');
  if (el && el.__x) {
    el.__x.$data.loadSection(section);
    return;
  }
  // Legacy fallback
  const el2 = document.getElementById('docs-content');
  if (!el2) return;
  el2.innerHTML = '<div style="color:var(--text3);padding:20px">加载文档…</div>';
  const spec = _DOC_SOURCES[section] || _DOC_SOURCES.quickstart;
  fetch(typeof api === 'function' ? '/api/docs/' + section : spec.static)
    .then(r => typeof api === 'function' ? r.json().then(d => d.content || spec.title) : r.text())
    .then(content => {
      el2.innerHTML = '<article class="doc-content">' + renderDocMarkdown(typeof content === 'string' ? content : '') + '</article>';
      bindDocLinks(el2);
    })
    .catch(e => { el2.innerHTML = '<div style="color:var(--err);padding:20px">加载失败: ' + escHtml(e.message) + '</div>'; });
  document.querySelectorAll('#docs-view .tab').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-doc') === section);
  });
}
