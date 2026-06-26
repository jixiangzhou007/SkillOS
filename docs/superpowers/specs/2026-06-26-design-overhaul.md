# SkillOS 设计全面升级规格书

> 2026-06-26 · 基于用户确认的五维度设计方向

## 总则

### 设计气质：精准专业

冷静克制、信息密度高、铜色仅做点缀。参考 Linear / Vercel 的产品气质——让内容说话，UI 退居背景。

### 五维度选定

| 维度 | 选择 | 核心原则 |
|------|:--:|------|
| 气质 | 精准专业 | 冷静克制、高信息密度 |
| 配色 | 冷灰 + 暖灰交融 | Linear 暗色基调，铜色 accent 保留 |
| 字体 | DM Sans 全家桶 | 标题正文统一，中文系统 fallback |
| 布局 | 混合策略 | 仪表盘/市场自适应、文档/设置固定宽 |
| 组件 | 统一玻璃 | blur 12px 卡片、20px 弹窗、8px 输入 |

---

## 一、配色体系

### 1.1 中性色升级（12 档灰阶）

```
--n0:#fafafa  --n1:#f5f5f5  --n2:#e5e5e5  --n3:#a3a3a3
--n4:#737373  --n5:#525252  --n6:#404040  --n7:#262626
--n8:#171717  --n9:#0d0d0d  --n10:#0a0a0a  --n11:#050505
```

**变更**：从暖炭（红褐底色）切换到中性冷灰。`--bg` 从 `var(--n9)` (#0a0a09) 改为 `var(--n11)` (#050505)。

### 1.2 铜色 accent 保留但降频

```
--a1:#fef3ee  --a2:#f0c4a8  --a3:#d4845f
--a4:#b86848  --a5:#8a4a32  --a6:#633525
```

**使用规则**：
- 仅主按钮、active 状态、链接使用铜色
- 普通卡片边框、hover 背景使用中性灰，不再用铜色
- 图标、badge 默认中性色，hover 时变铜色

### 1.3 RGB 分量保留

`--accent-rgb`、`--surface-rgb`、`--text-rgb`、`--blue-rgb`、`--amber-rgb`、`--red-rgb` 保留，支持透明度变体。

---

## 二、字体体系

### 2.1 统一为 DM Sans

移除 Syne 显示字体。全部使用 DM Sans（已加载 400/500/600/700 字重）。

```
--font: 'DM Sans', -apple-system, 'Segoe UI', 'PingFang SC', ...;
--font-number: 'DM Sans', 'Inter', -apple-system, ...;  // 数字用 DM Sans + tabular-nums
--mono: 'DM Mono', 'IBM Plex Mono', ui-monospace, ...;  // 代码用 DM Mono（新增 Google Fonts 加载）
```

### 2.2 字号 scale 精调

保留当前 `--t-xs` 到 `--t-display`，增加 `--t-4xl:48px`。

### 2.3 数字处理

全局 `font-feature-settings: 'tnum' 1`。KPI、评分、统计数字使用 `--font-number`。

---

## 三、布局体系

### 3.1 混合策略

| 页面类型 | 布局 | 最大宽度 | 居中对齐 |
|---------|------|:--:|:--:|
| 仪表盘（知识页） | 自适应 grid | 无限制 | 无 |
| 市场页 | 自适应 grid | 无限制 | 无 |
| 文档页 | 固定宽 | 780px | margin:0 auto |
| 管理页 | 固定宽 | 900px | margin:0 auto |
| 详情页 | 自适应 | 900px 最大 | 无 |
| 聊天页 | 全宽 | 720px 消息列 | margin:0 auto |

### 3.2 间距统一

```
卡片间距：16px (--s-4)
段落间距：20px (--s-5)
页面内边距：24px-32px (--s-6 ~ --s-8)
```

### 3.3 圆角统一

```
卡片：--r-lg (14px)
按钮/输入框：--r (10px)
标签/badge：--r-sm (8px)
弹窗：--r-lg (14px)
```

---

## 四、组件体系

### 4.1 玻璃效果统一

| 组件 | blur | 背景透明度 |
|------|:--:|:--:|
| 卡片 | 12px | rgba(surface-rgb, .45) |
| 弹窗 | 20px | rgba(surface-rgb, .94) |
| 下拉菜单 | 20px | rgba(surface-rgb, .96) |
| 顶栏/底栏 | 16px | rgba(surface-rgb, .88) |
| 输入框 | 无 blur | rgba(surface-rgb, .6) |

### 4.2 按钮规范

| 变体 | 背景 | 边框 | 用途 |
|------|------|------|------|
| primary | 铜色渐变 a3→a5 | 无 | 主操作 |
| secondary | surface | border | 次要操作 |
| ghost | transparent | transparent | 导航/菜单 |
| danger | red-rgb .06 | red | 危险操作 |

所有按钮：`height:36px`（标准）、`height:32px`（紧凑）、`height:40px`（输入栏）。

### 4.3 卡片规范

- 边框：`1px solid var(--border)`，hover 时 `border-color: var(--border2)`
- 不主动使用铜色边框，hover 时也不加
- 阴影仅弹窗和悬浮卡片使用

### 4.4 输入框规范

- 背景：`rgba(var(--surface-rgb), .6)`
- 边框：`1px solid var(--border)`，focus 时 `border-color: var(--accent)` + `box-shadow: 0 0 0 3px var(--accent-bg)`
- 圆角：`var(--r)`

---

## 五、实施范围

### 第一阶段：配色+字体（1-2h）

1. 更新 `:root` 中的中性色为 12 档冷灰
2. 移除 Syne 引用，统一为 DM Sans
3. 添加 DM Mono 到 Google Fonts 加载
4. 减少铜色出现频率：border → 中性灰，hover bg → surface2

### 第二阶段：组件统一（2-3h）

1. 统一 blur 值
2. 统一按钮高度和圆角
3. 统一卡片边框和 hover 行为
4. 移除多余的铜色点缀

### 第三阶段：布局规范（1-2h）

1. 知识/市场页去掉 max-width
2. 文档/管理/设置页加 centering
3. 间距审核，统一为 4px 基准

### 第四阶段：动画和微交互（1h）

1. 统一过渡时间 `--t: 220ms`
2. hover lift 效果统一（卡片 -2px，按钮 -1px）
3. 页面切换动画统一 200ms fade

---

## 六、不变项（保持现有）

- CSS 变量体系结构
- Alpine.js + vanilla JS 架构
- 磨砂玻璃方向（保留但统一 blur 值）
- icon 系统（icons.js）
- 键盘快捷键
- 响应式断点
- 现有 HTML 结构（只改 CSS 类的内容，不改类名）
