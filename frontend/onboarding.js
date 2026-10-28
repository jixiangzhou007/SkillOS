/* onboarding.js — first-run guide (M0 narrative) */

var ONBOARDING_KEY = typeof StorageKeys !== 'undefined' ? StorageKeys.ONBOARDING_DONE : 'skillos_onboarding_done';
var _ONBOARDING_STEPS = [
  {
    title: 'AI 是学徒，不是点云执行器',
    body: 'SkillOS 把你的工作经验炼成可验证的 Agent Skills。学徒先问清楚再动手；出师要过双门禁：Gate A 认识论声明 + Gate B 域内烟测。',
    action: function() {},
    actionLabel: '开始了解'
  },
  {
    title: '三种输入，一种出师态',
    body: '对话（苏格拉底追问）、链接沉淀、上传资料——都走向同一完成态：Draft → Provisional → Verified，并导出 AgentSkills.io 标准 SKILL.md。',
    action: function() {
      if (typeof showChat === 'function') showChat();
    },
    actionLabel: '试一下'
  },
  {
    title: 'Trust Tier 看得见',
    body: '列表与详情展示 Trust Tier；本地 Quick8 是日常门禁，官方 SkillsBench 是权威轨——两者分栏，勿混为一谈。在 Cursor 里装上 Verified Skill 即用。',
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
    if (typeof toast === 'function') toast('欢迎使用 SkillOS · 学徒出师', 'success');
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
