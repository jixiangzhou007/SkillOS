/* onboarding.js — first-run guide (M0 narrative) */

var ONBOARDING_KEY = typeof StorageKeys !== 'undefined' ? StorageKeys.ONBOARDING_DONE : 'skillos_onboarding_done';
var _ONBOARDING_STEPS = [
  {
    title: '① 配置模型',
    body: '在「设置 → 模型」确认 LLM 已选；API Key 写在服务端 .env（DEEPSEEK_API_KEY）。',
    action: function() {
      if (typeof showSettings === 'function') showSettings();
    },
    actionLabel: '打开设置'
  },
  {
    title: '② 三种方式沉淀',
    body: '对话萃取（苏格拉底追问）、粘贴链接、或上传 PDF/Word。三种输入，同一种 Verified Skill 终点。',
    action: function() {
      if (typeof showChat === 'function') showChat();
    },
    actionLabel: '开始'
  },
  {
    title: '③ 验货并装进 Cursor',
    body: '沉淀完成后会看到「已验证 / 待审」摘要。复制 Cursor 安装路径或下载 Zip — 在 Cursor 里验货，在这里导出。',
    action: function() {
      if (typeof showChat === 'function') showChat();
    },
    actionLabel: '知道了'
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
