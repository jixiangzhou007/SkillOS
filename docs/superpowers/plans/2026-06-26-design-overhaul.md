# Design Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面升级 SkillOS UI 设计语言——精准专业风，冷灰配色、DM Sans 统一、组件规范、混合布局。

**Architecture:** 仅修改 `frontend/style.css` 和 `frontend/index.html` 中的字体加载。不动 HTML 结构、不动 JS。四阶段 15 个任务。

**Tech Stack:** CSS variables, Google Fonts, 现有 Alpine.js + vanilla JS

---

## 文件映射

| 文件 | 职责 | 改动范围 |
|------|------|------|
| `frontend/style.css` | 全部样式 | 中性色 `:root`、组件规则、布局规则 |
| `frontend/index.html` | 字体加载 | `<link>` 标签中 Google Fonts URL |

---

### Task 1: 升级中性色为 12 档冷灰

**Files:**
- Modify: `frontend/style.css:7-19`

- [ ] **Step 1: 替换 :root 中的中性色变量**

将当前暖炭灰替换为冷灰 12 档：

```css
/* Neutral — cool gray */
--n0:#fafafa;--n1:#f5f5f5;--n2:#e5e5e5;--n3:#a3a3a3;
--n4:#737373;--n5:#525252;--n6:#404040;--n7:#262626;
--n8:#171717;--n9:#0d0d0d;--n10:#0a0a0a;--n11:#050505;
```

- [ ] **Step 2: 调整表面色映射**

```css
/* App surfaces — shift down one shade for deeper bg */
--bg:var(--n11);--bg2:var(--n10);--surface:var(--n8);--surface2:var(--n7);
```

- [ ] **Step 3: 调整 RGB 分量同步**

```css
--surface-rgb:23,23,23;  /* was 26,25,23 */
```

- [ ] **Step 4: 验证 CSS 编译**

Run: `python -c "with open('frontend/style.css') as f: f.read(); print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): upgrade neutral palette to 12-stop cool gray, deepen bg"
```

---

### Task 2: 调整铜色 accent 使用频率

**Files:**
- Modify: `frontend/style.css` — 搜索铜色相关规则

- [ ] **Step 1: 卡片边框去掉铜色，改用中性色**

找到所有 `.content-card:hover{border-color:rgba(var(--accent-rgb),...)}` 替换为 `border-color:var(--border2)`：

```css
.content-card:hover{border-color:var(--border2);box-shadow:0 0 0 1px rgba(var(--text-rgb),.04)}
.hub-list-card:hover{border-color:var(--border2)}
.skill-card:hover{border-color:var(--border2)}
```

- [ ] **Step 2: 导航项 hover 去掉铜色背景**

找到 `rgba(var(--accent-rgb),.06)` 和类似的 accent hover 背景，替换为表面色：

```css
.sb-nav-item:hover{background:var(--surface2)}
```

- [ ] **Step 3: badge 默认中性色**

找到 `.sb-count`、`.model-card-badge` 等 badge 类，确保默认不显示铜色背景。

- [ ] **Step 4: 保留主按钮、链接、active 状态的铜色**

确认以下保持不变：`.btn-primary`、`a`、`.active` 状态元素。

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): reduce copper accent frequency — borders/badges → neutral, keep only primary/active"
```

---

### Task 3: 统一字体为 DM Sans，添加 DM Mono

**Files:**
- Modify: `frontend/index.html` — Google Fonts link
- Modify: `frontend/style.css` — 字体变量和引用

- [ ] **Step 1: 更新 Google Fonts 加载**

在 `index.html` 中替换字体 link：

```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:ital,wght@0,400;0,500&display=swap" rel="stylesheet">
```

- [ ] **Step 2: 更新 CSS 字体变量**

```css
--font-display:'DM Sans',system-ui,sans-serif;  /* was 'Syne' */
--font:'DM Sans',system-ui,-apple-system,'Segoe UI','PingFang SC','HarmonyOS Sans','Microsoft YaHei',sans-serif;
--font-number:'DM Sans',system-ui,-apple-system,sans-serif;
--mono:'DM Mono','IBM Plex Mono',ui-monospace,monospace;
```

- [ ] **Step 3: 移除 Syne 所有引用**

搜索 `var(--font-display)` → 全部改为 `var(--font)`：

```bash
sed -i 's/var(--font-display)/var(--font)/g' frontend/style.css
```

- [ ] **Step 4: 标题字重增加以补偿**

由于 DM Sans 不如 Syne 有视觉冲击力，标题增粗：

```css
h1{font:700 var(--t-2xl)/1.12 var(--font);letter-spacing:-.02em}
h2{font:600 var(--t-xl)/1.2 var(--font);letter-spacing:-.015em}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/style.css
git commit -m "feat(ui): switch font to DM Sans family, add DM Mono for code"
```

---

### Task 4: 精调字号 scale

**Files:**
- Modify: `frontend/style.css` — 字号变量和关键文本规则

- [ ] **Step 1: 微调字号变量**

```css
--t-xs:11px;--t-sm:12px;--t-base:13.5px;--t-md:14px;--t-lg:17px;
--t-xl:20px;--t-2xl:26px;--t-3xl:32px;--t-display:36px;
```

- [ ] **Step 2: 添加 --t-4xl**

```css
--t-4xl:48px;
```

- [ ] **Step 3: 欢迎页标题字号降级**

`.welcome-title` 不再需要 `clamp(28px,5vw,...)`：

```css
.welcome-title{font:700 var(--t-display)/1.05 var(--font);...}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): refine type scale — --t-xs 11px, --t-base 13.5px, add --t-4xl 48px"
```

---

### Task 5: 统一 blur 值

**Files:**
- Modify: `frontend/style.css` — 所有 `backdrop-filter: blur(...)` 出现

- [ ] **Step 1: 统一卡片 blur 为 12px**

搜索替换：
- `backdrop-filter:blur(8px)` → `backdrop-filter:blur(12px)`（卡片）
- `backdrop-filter:blur(20px)` → `backdrop-filter:blur(20px)`（保持不变，弹窗）
- `backdrop-filter:blur(16px)` → `backdrop-filter:blur(16px)`（保持不变，侧栏/顶栏）

- [ ] **Step 2: 统一卡片背景透明度**

卡片背景统一为 `rgba(var(--surface-rgb),.5)`：

```css
.dash-card{background:rgba(var(--surface-rgb),.5)}
.admin-card{background:rgba(var(--surface-rgb),.5)}
```

- [ ] **Step 3: 输入框不加 blur**

```css
input,textarea,select{backdrop-filter:none}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): unify backdrop-filter — cards 12px, modals 20px, inputs none"
```

---

### Task 6: 统一按钮规范

**Files:**
- Modify: `frontend/style.css` — 所有按钮相关规则

- [ ] **Step 1: 定义按钮高度 token**

```css
.btn{height:36px}.btn-sm{height:32px}.btn-lg{height:40px}
```

- [ ] **Step 2: 统一按钮圆角**

```css
.btn{border-radius:var(--r)}  /* 10px */
.btn-sm,.btn-lg{border-radius:var(--r)}  /* 10px */
```

- [ ] **Step 3: 统一 hover 效果**

所有按钮 hover 时 `transform:translateY(-1px)`：

```css
.btn:hover,.btn-primary:hover,.btn-secondary:hover,.btn-ghost:hover{transform:translateY(-1px)}
```

- [ ] **Step 4: 统一 focus 环**

```css
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): button specs — heights 32/36/40px, radius 10px, hover lift, focus ring"
```

---

### Task 7: 统一卡片规范

**Files:**
- Modify: `frontend/style.css` — 所有卡片相关规则

- [ ] **Step 1: 统一卡片圆角**

```css
.dash-card,.content-card,.admin-card,.skill-card,.hub-list-card,.hub-review-card,.model-card
{border-radius:var(--r-lg)}  /* 14px */
```

- [ ] **Step 2: 统一卡片边框**

```css
.dash-card,.content-card,.admin-card,.hub-list-card{border:1px solid var(--border)}
```

- [ ] **Step 3: 统一卡片 hover**

```css
.dash-card:hover,.content-card:hover,.hub-list-card:hover{border-color:var(--border2)}
```

去除铜色边框 glow 效果（之前有的 `box-shadow:0 0 0 1px rgba(accent-rgb,...)`）。

- [ ] **Step 4: 统一卡片内边距**

```css
.dash-card{padding:var(--s-6)}
.content-card,.admin-card,.hub-list-card{padding:var(--s-5)}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): card specs — radius 14px, border neutral, padding unified"
```

---

### Task 8: 统一输入框规范

**Files:**
- Modify: `frontend/style.css` — 所有输入框相关规则

- [ ] **Step 1: 统一输入框背景**

```css
input,textarea,select{background:rgba(var(--surface-rgb),.6);border:1px solid var(--border)}
```

- [ ] **Step 2: 统一 focus 状态**

```css
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.12)}
```

- [ ] **Step 3: 统一圆角**

```css
input,textarea,select{border-radius:var(--r)}  /* 10px */
```

- [ ] **Step 4: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): input specs — bg surface .6, focus ring accent, radius 10px"
```

---

### Task 9: 混合布局策略

**Files:**
- Modify: `frontend/style.css` — `.page-body` 及相关页面布局

- [ ] **Step 1: 仪表盘/市场页去掉 max-width**

确认 `.knowledge-content`、`.hub-catalog` 无限宽。

- [ ] **Step 2: 文档/管理页加 centering**

```css
.docs-page{max-width:780px;margin:0 auto}
.admin-page{max-width:900px;margin:0 auto}
```

- [ ] **Step 3: 聊天消息列居中**

```css
#chat-msgs-list{max-width:720px;margin:0 auto;width:100%}
```

- [ ] **Step 4: 详情页加 max-width**

```css
.detail-body{max-width:900px}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): hybrid layout — chat/doc center, dashboard/market fluid, detail 900px"
```

---

### Task 10: 间距审核

**Files:**
- Modify: `frontend/style.css` — 所有间距规则

- [ ] **Step 1: 统一卡片间距为 16px**

搜索 `gap:12px`、`gap:var(--s-3)` → 改为 `gap:var(--s-4)`：

```css
.dash-grid{gap:var(--s-4)}
.knowledge-kpi-grid{gap:var(--s-4)}
.hub-rec-grid{gap:var(--s-4)}
.admin-grid{gap:var(--s-4)}
```

- [ ] **Step 2: 页头间距统一**

```css
.page-header{margin-bottom:var(--s-5)}  /* 20px */
```

- [ ] **Step 3: 表单行间距**

```css
.form-row,.admin-form-row{gap:var(--s-3)}  /* 12px */
```

- [ ] **Step 4: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): spacing audit — uniform card gap 16px, header margin 20px"
```

---

### Task 11: 统一过渡动画

**Files:**
- Modify: `frontend/style.css` — 过渡和动画规则

- [ ] **Step 1: 全局过渡变量保留**

`--t:220ms cubic-bezier(.4,0,.2,1)` 已存在，保持不变。

- [ ] **Step 2: 统一 hover lift**

所有可交互元素 hover 时 `transform:translateY(-1px)` for 按钮、`translateY(-2px)` for 卡片：

```css
.btn:hover,.nav-sm:hover,.bar-action:hover{transform:translateY(-1px)}
.dash-card:hover,.hub-list-card:hover{transform:translateY(-2px)}
```

- [ ] **Step 3: 统一 active press**

```css
.btn:active{transform:translateY(0);transition:transform .05s}
```

- [ ] **Step 4: 页面切换动画统一**

已有 `.main-view.active{animation:view-in .2s ease}`，调整为：

```css
.main-view.active{animation:view-in .2s ease}
@keyframes view-in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "feat(ui): animation specs — hover lift -1/-2px, active press, page fade-in .2s"
```

---

### Task 12: 全量测试

**Files:**
- Verify: `frontend/style.css` 编译正确

- [ ] **Step 1: CSS 语法验证**

```bash
python -c "
with open('frontend/style.css') as f:
    c = f.read()
opens = c.count('{')
closes = c.count('}')
assert opens == closes, f'Unbalanced braces: {opens} vs {closes}'
print(f'CSS OK — {opens} rule blocks, {len(c)} chars')
"
```

- [ ] **Step 2: 验证所有页面可访问**

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/ && echo " index OK"
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/style.css && echo " CSS OK"
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/login.html && echo " login OK"
```

- [ ] **Step 3: 运行全量测试**

```bash
python -m pytest tests/ -v --tb=line -q 2>&1 | tail -5
```

Expected: 605+ passed

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore: design overhaul — all tests passed, CSS validated"
```

---

### Task 13: 更新设计文档

**Files:**
- Modify: `DESIGN.md` — 更新快照行

- [ ] **Step 1: 更新 DESIGN.md 快照**

将 `v0.3.5`、`121 commits` 等更新为当前状态，添加设计升级标注。

- [ ] **Step 2: Commit**

```bash
git add DESIGN.md
git commit -m "docs: update DESIGN.md snapshot post-overhaul"
```
