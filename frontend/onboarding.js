/* onboarding.js — first-run guide (M0 narrative) */

var ONBOARDING_KEY = typeof StorageKeys !== 'undefined' ? StorageKeys.ONBOARDING_DONE : 'skillos_onboarding_done';
var _ONBOARDING_STEPS = [
  {
    title: '可验证的技能工厂',
    body: 'SkillOS 不是又一个 AI 工具。它帮你把工作经验萃取成 Verified Skill——经过认识论验证、可以持续进化的技能文档。输出 AgentSkills.io 标准，Claude Code / Cursor 直接加载。',
    action: function() {},
    actionLabel: '开始了解'
  },
  {
    title: '三种输入，一种输出',
    body: '在对话中描述流程（苏格拉底式追问帮你理清思路）、粘贴网页链接自动学习、上传 PDF/Word 自动消化——最终都输出为标准 SKILL.md，附带验证数据和进化轨迹。',
    action: function() {
      if (typeof showChat === 'function') showChat();
    },
    actionLabel: '试一下'
  },
  {
    title: '越用越好',
    body: '每个 skill 都有版本历史、MoE 质量评分、SkillsBench 回归测试。改进了某个 skill，相关 skill 会自动受益。在 Cursor / Codex 里用得越多，SkillOS 后台进化得越好。',
    action: function() {
      closeOnboarding(true);
      if (typeof toast === 'function') toast('开始萃取你的第一个 Verified Skill', 'success');
    },
    actionLabel: '开始使用'
  }
];

var _onboardingStep = 0;

function shouldShowOnboarding() {
  return !localStorage.getItem(ONBOARDING_KEY);
}

function renderOnboardingStep() {
  var step = _ONBOARDING_STEPS[_onboardingStep];
  var title = document.getElementById('onboarding-title');
  var body = document.getElementById('onboarding-body');
  var next = document.getElementById('onboarding-next');
  var dots = document.getElementById('onboarding-dots');
  if (!step || !title) return;
  title.textContent = step.title;
  body.textContent = step.body;
  if (next) next.textContent = _onboardingStep < _ONBOARDING_STEPS.length - 1 ? '下一步' : '完成';
  if (dots) {
    dots.innerHTML = _ONBOARDING_STEPS.map(function(_, i) {
      return '<span class="onboarding-dot' + (i === _onboardingStep ? ' active' : '') + '"></span>';
    }).join('');
  }
}

function closeOnboarding(persist) {
  var el = document.getElementById('onboarding-overlay');
  if (el) el.style.display = 'none';
  if (persist) localStorage.setItem(ONBOARDING_KEY, '1');
}

function openOnboarding() {
  if (!shouldShowOnboarding()) return;
  _onboardingStep = 0;
  renderOnboardingStep();
  var el = document.getElementById('onboarding-overlay');
  if (el) el.style.display = 'flex';
}

function onboardingNext() {
  var step = _ONBOARDING_STEPS[_onboardingStep];
  if (step && typeof step.action === 'function') step.action();
  if (_onboardingStep >= _ONBOARDING_STEPS.length - 1) {
    closeOnboarding(true);
    if (typeof toast === 'function') toast('欢迎使用 SkillOS · 可验证的技能工厂', 'success');
    return;
  }
  _onboardingStep++;
  renderOnboardingStep();
}

function initOnboarding() {
  var skip = document.getElementById('onboarding-skip');
  var next = document.getElementById('onboarding-next');
  if (skip) skip.onclick = function() { closeOnboarding(true); };
  if (next) next.onclick = onboardingNext;
  setTimeout(openOnboarding, 800);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initOnboarding);
} else {
  initOnboarding();
}
