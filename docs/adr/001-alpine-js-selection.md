# ADR 001: Alpine.js 前端框架选型

**日期**：2026-06-19
**状态**：已采纳
**决策者**：Claude Code（基于架构分析）

## 上下文

SkillOS 前端为 14 个 vanilla JS 文件（6,265 行），全局变量散落（`_mode`、`_currentSkill`、`_currentTab` 等 42 个）、命令式 DOM 操作（`innerHTML` 字符串拼接）、无响应式、无组件化。需要引入轻量框架改善可维护性。

候选方案：

| 方案 | 体积 | 构建步骤 | 迁移成本 | 响应式 | 生态 |
|------|------|----------|----------|--------|------|
| Alpine.js | 15KB | 零（CDN） | 渐进式，逐页替换 | Proxy-based | 小 |
| Vue 3 + Vite | ~40KB | 需要 | 全量重写 | Proxy-based | 大 |
| 原生 ES Modules | 0KB | 零 | 渐进式 | 无 | 无 |

## 决策

**选择 Alpine.js v3**，通过 CDN 加载（`<script defer src="alpinejs@3.14">`），零构建步骤。

## 理由

1. **pywebview 桌面环境**：非大型 Web 应用，不需要 SPA 路由、虚拟 DOM diffing 或构建工具链。Alpine 的 15KB 体量匹配当前架构。

2. **渐进迁移可行**：Alpine 通过 `x-data`、`x-show`、`:class` 等属性与现有 HTML 共存。Vue 需要将 `index.html` 改为构建入口，会破坏现有 14 个脚本标签的加载顺序。

3. **全局变量过渡平滑**：通过 `Object.defineProperty` 创建 getter/setter 别名，旧代码继续读写 `_mode`/`_currentSkill` 等全局变量，底层由 Alpine store 代理。Vue 无法做到这种透明过渡。

4. **团队规模**：单人团队，Vue 的全量重写成本（估计 2-3 周）远超 Alpine 渐进迁移（实际 13 Phase，约 4 小时）。

## 后果

### 正面
- 13 个 view 的导航从 CSS class 切换改为响应式 `$store.nav.currentView`
- 4 个 Alpine store（nav/chat/auth/skill）替代 10 个全局变量
- 7 个新 Alpine 组件（accountWatcher、docsView 等）替换命令式 DOM 构建

### 负面
- 核心交互（chat.js 消息渲染、skills.js 详情、hub.js 市场）仍用 innerHTML——需要后续深度 Alpine 化
- Alpine 生态小，复杂场景需回退 vanilla JS
- 额外 CDN 依赖（离线环境需本地缓存）

### 不选 Vue 的理由
- 需要构建工具链（Vite/webpack），破坏现有零构建架构
- 重写 14 个 JS 文件为 SFC 格式，成本高、风险大
- 桌面 app 不需要 SPA 路由和状态管理库（Pinia/Vuex）

### 不选 ES Modules 的理由
- 浏览器原生 import/export 只是组织方式改进，不解决响应式和 DOM 操作问题
- 仍需手动操作 DOM，无法减少代码量
