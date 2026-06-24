/* socratic-ui.js — M3 苏格拉底 IDE：选项 chip + 回复清洗 */

var _OPTION_LINE_RE = /\[选项\]\s*(.+?)\s*\|\s*(\S+)/g;

function stripOptionLines(text) {
  if (!text) return '';
  return text.split('\n').filter(function(line) {
    return line.indexOf('[选项]') < 0;
  }).join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

function parseOptionActions(reply) {
  if (!reply || reply.indexOf('[选项]') < 0) return [];
  var actions = [];
  var seen = {};
  var re = new RegExp(_OPTION_LINE_RE.source, 'g');
  var m;
  while ((m = re.exec(reply))) {
    var label = m[1].trim();
    var action = m[2].trim();
    if (!label || !action || seen[action]) continue;
    seen[action] = true;
    actions.push({ label: label, action: action });
  }
  return actions;
}

function _escAttr(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function attachSocraticChips(msg, actions, opts) {
  opts = opts || {};
  if (!msg || !actions || !actions.length) return;
  var list = document.getElementById('chat-msgs-list');
  if (!list) return;
  var row = list.querySelector('[data-msg-id="' + msg.id.replace(/"/g, '\\"') + '"]');
  if (!row) return;
  var bubble = row.querySelector('.msg-bubble');
  if (!bubble) return;

  var old = bubble.querySelector('.socratic-chips');
  if (old) old.remove();

  var wrap = document.createElement('div');
  wrap.className = 'socratic-chips';
  wrap.setAttribute('role', 'group');
  wrap.setAttribute('aria-label', '快捷选项');

  if (opts.multi) {
    var selected = {};
    actions.forEach(function(a, i) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'socratic-chip';
      chip.textContent = a.label;
      chip.setAttribute('data-idx', String(i));
      chip.onclick = function() {
        if (selected[i]) {
          delete selected[i];
          chip.classList.remove('selected');
        } else {
          selected[i] = true;
          chip.classList.add('selected');
        }
      };
      wrap.appendChild(chip);
    });
    var confirm = document.createElement('button');
    confirm.type = 'button';
    confirm.className = 'socratic-chip socratic-chip-confirm';
    confirm.textContent = '确认选择';
    confirm.onclick = function() {
      var picked = actions.filter(function(_, i) { return selected[i]; });
      if (!picked.length) {
        if (typeof addMsg === 'function') addMsg('sys', '请至少选择一项');
        return;
      }
      if (typeof doAction === 'function') {
        doAction({
          action: opts.actionKey || 'multi_select',
          skills: picked.map(function(a) { return a.action; }).join(','),
          label: picked.map(function(a) { return a.label; }).join(' + '),
        });
      }
    };
    wrap.appendChild(confirm);
  } else {
    actions.forEach(function(a) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'socratic-chip';
      chip.textContent = a.label;
      chip.onclick = function() {
        if (typeof doAction === 'function') doAction(a);
      };
      wrap.appendChild(chip);
    });
  }

  bubble.appendChild(wrap);
  if (typeof scrollMsgs === 'function') scrollMsgs();
}

function formatAiReplyHtml(reply) {
  var clean = stripOptionLines(reply || '');
  if (!clean) return '<span style="color:var(--text3)">（请选择下方选项继续）</span>';
  return '<span>' + clean.replace(/\n/g, '<br>') + '</span>';
}

function applySocraticReply(msgEl, reply, actions, opts) {
  opts = opts || {};
  var html = formatAiReplyHtml(reply);
  if (msgEl && msgEl._msg) {
    if (typeof patchChatMsg === 'function') patchChatMsg(msgEl._msg, html);
    attachSocraticChips(msgEl._msg, actions, opts);
  } else if (msgEl && msgEl.innerHTML !== undefined) {
    msgEl.innerHTML = html;
  }
}

function resolveExtractionActions(d, reply) {
  var actions = (d && d.actions && d.actions.length) ? d.actions : parseOptionActions(reply || (d && d.reply) || '');
  return actions;
}
