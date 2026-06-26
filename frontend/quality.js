/* quality.js — Quality badge rendering: DNA, MoE, smoke, bench scores */

function qualityColor(score, type) {
  if (score == null) return 'var(--text3)';
  if (type === 'dna') { score = (typeof score === 'string' ? parseInt(score) : score) || 0; return score >= 5 ? 'var(--a3)' : score >= 3 ? 'var(--amber)' : 'var(--red)'; }
  if (type === 'moe') return score >= 80 ? 'var(--a3)' : score >= 60 ? 'var(--amber)' : 'var(--red)';
  if (type === 'avg') return score >= 4 ? 'var(--a3)' : score >= 2 ? 'var(--amber)' : 'var(--red)';
  if (type === 'smoke') return score === true ? 'var(--a3)' : score === false ? 'var(--red)' : 'var(--text3)';
  return 'var(--text3)';
}

function qualityLabel(type, score) {
  if (type === 'dna') return 'DNA ' + (score || '—');
  if (type === 'moe') return 'MoE ' + (score != null ? score : '—');
  if (type === 'avg') return (score != null ? score + '/5' : '—');
  if (type === 'smoke') return score === true ? '烟测 ✓' : score === false ? '烟测 ✗' : '烟测 —';
  if (type === 'bench') return score === true ? '回归 ✓' : score === false ? '回归 ✗' : '回归 —';
  return '';
}

/* size: 'sm' (sidebar card) | 'md' (phase bar) | 'lg' (detail strip) */
function renderQualityBadge(type, score, size) {
  size = size || 'sm';
  var color = qualityColor(score, type);
  var label = qualityLabel(type, score);
  var fontSize = size === 'sm' ? '9px' : size === 'md' ? '10px' : '11px';
  var padding = size === 'sm' ? '1px 5px' : size === 'md' ? '2px 6px' : '3px 8px';
  return '<span style="font-size:' + fontSize + ';padding:' + padding + ';border-radius:3px;' +
    'color:' + color + ';background:' + color.replace(')', ',.1)').replace('rgb', 'rgba').replace('var(--a3)', 'rgba(52,211,153,.12)').replace('var(--amber)', 'rgba(245,158,11,.12)').replace('var(--red)', 'rgba(239,68,68,.12)').replace('var(--text3)', 'rgba(255,255,255,.06)') + ';' +
    'white-space:nowrap;font-weight:600;font-family:var(--font)">' + label + '</span>';
}

function renderQualityMiniBadges(meta, size) {
  size = size || 'sm';
  var h = '';
  if (meta.avg_score != null) h += renderQualityBadge('avg', meta.avg_score, size) + ' ';
  if (meta.dna_score) h += renderQualityBadge('dna', meta.dna_score, size) + ' ';
  if (meta.moe_score != null) h += renderQualityBadge('moe', meta.moe_score, size) + ' ';
  if (meta.smoke_pass != null) h += renderQualityBadge('smoke', meta.smoke_pass, size);
  return h;
}

/* Skill evaluation — 5 dimension framework (SkillsBench paper) */
function renderEvalFramework() {
  return '<div class="content-card" style="margin-top:var(--s-3)"><div class="content-card-header">📋 技能评估五维度（SkillsBench）</div>' +
    '<div class="content-row"><span class="content-row-label">边界</span><span class="content-row-value">任务边界清晰？触发条件明确？</span></div>' +
    '<div class="content-row"><span class="content-row-label">过程</span><span class="content-row-value">提供检查点、示例、工具和中间格式？</span></div>' +
    '<div class="content-row"><span class="content-row-label">增益</span><span class="content-row-value">相对无 skill 基线有稳定提升？（参考官方评测 tab）</span></div>' +
    '<div class="content-row"><span class="content-row-label">稳定性</span><span class="content-row-value">换模型/环境后仍有效？</span></div>' +
    '<div class="content-row"><span class="content-row-label">成本</span><span class="content-row-value">上下文占用+审核成本+维护成本是否值得？</span></div>' +
    '<div style="font-size:var(--t-xs);color:var(--text3);margin-top:var(--s-2)">参考：SkillsBench 论文 — 人工整理 skill +16.2pp，模型自生成 -1.3pp。2-3 个 skill 最优。</div>' +
    '</div>';
}

/* Quality strip for detail view — renders below tabs */
function renderQualityStrip(ep) {
  if (!ep) return '';
  var items = [];
  // DNA compliance
  var bq = ep.bench_quality || {};
  var dc = bq.dna_compliance || {};
  if (dc.score) items.push({ type: 'dna', score: dc.score, label: 'DNA 合规', tab: 'dna' });
  // MoE
  var moe = bq.moe || ep.moe_evaluation || {};
  if (moe.overall_score != null) items.push({ type: 'moe', score: moe.overall_score, label: 'MoE 评分', tab: 'official' });
  // Smoke test
  var sg = bq.save_gate || {};
  if (sg.smoke_pass != null) items.push({ type: 'smoke', score: sg.smoke_pass, label: '保存门禁', tab: 'dna' });
  // Benchmark
  if (ep.post_bench && ep.post_bench.regression_scheduled !== undefined) {
    items.push({ type: 'bench', score: ep.post_bench.all_pass, label: '回归评测', tab: 'official' });
  }

  if (!items.length) return '';

  var h = '<div class="quality-strip">';
  h += '<span style="font-size:10px;color:var(--text3);margin-right:8px;text-transform:uppercase;letter-spacing:.06em">质量</span>';
  items.forEach(function(item) {
    var color = qualityColor(item.score, item.type);
    var label = qualityLabel(item.type, item.score);
    h += '<span class="quality-strip-item" onclick="switchDetailTab(' + JSON.stringify(item.tab) + ')" title="点击查看详情" style="cursor:pointer;font-size:11px;padding:3px 8px;border-radius:4px;color:' + color + ';background:' + color.replace(')', ',.1)').replace('rgb', 'rgba').replace('var(--a3)', 'rgba(52,211,153,.12)').replace('var(--amber)', 'rgba(245,158,11,.12)').replace('var(--red)', 'rgba(239,68,68,.12)').replace('var(--text3)', 'rgba(255,255,255,.06)') + ';white-space:nowrap;font-weight:600;margin-right:4px">' + label + '</span>';
  });
  h += '</div>';
  return h;
}

function switchDetailTab(tab) {
  if (typeof switchTab === 'function') switchTab(tab);
}
