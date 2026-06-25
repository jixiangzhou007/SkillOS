# SkillOS Frontend Audit

## Product Manager Assessment

### 信息架构（🔴 高优先级）

| 问题 | 现状 | 建议 |
|------|------|------|
| 导航混乱 | 7 个独立按钮平铺：Create/Chat/Pipeline/Hub/Dashboard/Settings/Logout | 合并为 3 个主入口：**对话**（Create+Chat+Pipeline）、**市场**（Hub）、**工作台**（Dashboard+Settings） |
| 模式概念用户不懂 | Create/Agent/Meta 三种模式对新手无意义 | 统一为"对话"，系统自动判断意图 |
| Hub 入口太弱 | 一个橙色小按钮 | 提升到一级导航，和市场定位匹配 |
| 知识包和技能混在一起 | 侧栏同一个列表 | 已分离到 Knowledge 区 ✅ |
| 首次使用无引导 | 空白状态只有文字提示 | 加 3 步 onboarding：配 API key → 创建第一个 Skill → 发布到市场 |

### 功能完整性（🟡 中优先级）

| 问题 | 现状 | 建议 |
|------|------|------|
| 全局搜索缺失 | 只能搜技能名 | 加顶栏搜索，搜技能+知识+市场 |
| 通知系统无 | Hub badge 是手动轮询 | 加 WebSocket 推送 |
| 批量操作无 | 技能只能逐个操作 | 加批量导出/删除/发布 |
| 用户头像/昵称无 | 只显示用户名文字 | 加头像和下拉菜单 |

---

## UI Designer Assessment

### 布局（🔴 高优先级）

| 问题 | 现状 | 建议 |
|------|------|------|
| 底栏固定占用空间 | 输入框+按钮始终在底部，浏览 Dashboard 时浪费 60px | 只在对话视图显示输入栏 |
| 侧栏太窄 | 264px 固定宽度，技能名长的被截断 | 改为可拖拽宽度 (240-400px) |
| 卡片密度过高 | Dashboard 卡片无间距 | 统一 12px gap，加 hover 效果 |
| 空白状态不友好 | 文字提示太技术化 | 加图标+引导按钮 |

### 视觉（🟡 中优先级）

| 问题 | 现状 | 建议 |
|------|------|------|
| 配色单调 | 全黑+绿 accent | 加语义色：蓝(info)、黄(warn)、红(err) 用于状态 |
| 字体层级不明显 | H1/H2/H3 差异小 | 标题加大，正文缩小到 13px |
| 图标依赖 emoji | 📁🧠📊 在不同 OS 显示不一致 | 改为 SVG 图标 |
| 过渡动画缺失 | 视图切换生硬 | 加 200ms fade |
| Mermaid 图在暗色主题下看不清 | 连接线颜色太暗 | 加大对比度 |
| 按钮状态不全 | 缺 disabled/loading 状态 | 统一按钮组件 |
| 滚动条丑陋 | 5px 无样式滚动条 | 加圆角+颜色 |

### 交互（🟡 中优先级）

| 问题 | 现状 | 建议 |
|------|------|------|
| 无加载骨架屏 | 所有异步操作用 "Loading..." 文字 | 加 pulse 动画占位块 |
| 无错误 Toast | 错误用 alert() 弹窗 | 加右上角 toast 通知 |
| 无确认对话框 | 删除/发布用 confirm() 浏览器弹窗 | 自定义 Modal |
| 键盘快捷键无 | 纯鼠标操作 | 加 Ctrl+K 搜索，Ctrl+N 新建 |

---

## 2026-06-14 全面排查修复记录

### 已修复（高优先级 Bug）

| 项 | 修复 |
|----|------|
| `auth.py` GitHub 登录 | 补全 `return`，`FeishuAuthRequest` 移出函数体 |
| 管理面板 API 路径 | `hub.js` 改为 `/api/auth/users`、`/audit-log`、`/admin/*` |
| 管理 API 缺失 | 新增 `GET /api/auth/users`、`/audit-log`，`POST /admin/register|update-user|delete-user` |
| Tab 高亮失效 | `index.html` + `skills.js` 使用 `data-tab` 属性 |
| `settings.js` 语法错误 | 删除孤立的 `el.appendChild(note)` 片段 |
| `toggleSkill` 404 | 改为 localStorage 本地启用/禁用（无后端路由） |
| 市场搜索无效 | `searchHub()` 改为带 query 调用 `catalog` API |
| 分类筛选为空 | 后端 `catalog` 返回 `categories` 聚合 |
| 只读市场 UI | 隐藏发布按钮，`showPublishForm` / `publishSkill` 处理 403 |
| `account_watcher.js` | 函数名乱码修复为 `showAccountWatcher` / `addWatchedAccount` |
| 对话 402/403 | `chat.js` 增加 `apiErrorMessage` + toast |
| 文件上传配额 | `uploadFile` 同样解析 402 错误 |
| 语音识别 fallback | `voice.js` 404 时提示使用浏览器麦克风 |
| 定价 API | 新增 `/api/marketplace/pricing/get|set`，只读模式下 403 |
| 技能导出 JWT | `downloadSkillExport` fetch + blob 下载，后端 export 支持 tenant |
| 收益/定价 UI | 只读模式隐藏收益按钮，中文化面板 |
| 模型 Modal | 中文化 settings.js + index.html |
| Hub 详情/审核/管理 | 全面中文化 hub.js |
| 语音 ASR API | `POST /voice/transcribe`（无 OPENAI_API_KEY 时 501，有 Key 时 Whisper） |
| knowledge.js | 加载/返回按钮中文化 |
| settings 语音/模型 | TTS/ASR 设置、模型卡片全面中文化 |
| knowledge 工作台 | 工作台/图谱/日志/知识/溯源视图中文化 |

### 2026-06-14 前端全面功能检查（Sprint 13 后）

#### 已修复（阻断级 / 功能缺失）

| 模块 | 问题 | 修复 |
|------|------|------|
| 技能详情 Tab | `_kpi()` 未定义，概览/认识论/进化 Tab 白屏 | `skills.js` 新增 `_kpi` helper |
| 技能 API | `GET /skills/{name}` 缺 version/runs/avg_score | 扩展 `get_skill` 返回 stats + versions |
| 技能 API | `DELETE /skills/{name}` 缺失 | 新增删除端点（JWT 租户隔离） |
| 技能 API | `GET /skills/{name}/kb` 缺失 | 新增 KB 摘要端点 |
| 技能 API | compare-template / import-and-adapt 缺失 | 新增 zip 导入与模板对比 |
| 技能 API | 列表缺 `kb_items` | `SkillResponse` 增加字段，知识工作台可区分知识包 |
| 血缘 | API 路径 `/lineage/list` 错误 | `knowledge.js` → `/lineage` |
| Hub | 订阅/审核 query 参数格式错误 | `hub.js` 修正 |
| 技能 KB Tab | `uploadTemplate` 未定义 | `skills.js` 实现上传与对比 |
| 对话 | 麦克风按钮无 id | `index.html` 加 `id="mic-btn"` |
| 对话 | `toggleAuto` 英文文案 | `chat.js` 中文化（自动/手动） |
| 技能 KB Tab | Compare Template 等英文 | `skills.js` loadKB 中文化 |
| Hub 发布 | 评分 toast 英文 | `hub.js` 中文化 |

#### 测试验证

- `tests/test_portal_e2e.py` + Sprint 11/12/13：**22 passed**

#### 仍待改进（非阻断）

| 优先级 | 项 | 说明 |
|--------|-----|------|
| 中 | 全局搜索 | ✅ 已修复 | 下拉结果面板，支持技能/知识/市场跳转 |
| 低 | 英文残留 | ✅ 大部分已修复 | chat/voice/DNA 已中文化；内部事件标识符仍为英文 |
| 低 | UX | 见上方 PM/UI 评估（导航合并、骨架屏、Modal 确认等） |

### 2026-06-14 文档 & 工作台修复

| 问题 | 修复 |
|------|------|
| 文档页纯文本 `<pre>` 无排版 | `marked.js` + `.doc-content` 样式，内链跳转 Tab |
| 工作台/子页无法滚动 | `.view-scroll` 容器 |
| 图谱 API 字段错误 (`name`/`size`) | 后端返回 `label`/`nodes`/`cohesion` |
| 图谱簇始终为空 | 修复 API 后前端正确展示 |
| 知识条目 NaN%/Invalid Date | API 返回 confidence/created_at/needs_review |
| 工作台无导航/返回 | 统一 `_viewHeader` + `_quickNav` |
| KPI 面板 ID 冲突 | 改用 `kpi-*-panel` + `.kpi-panel` |
| 技能名含引号点击崩溃 | `JSON.stringify` 安全 onclick |
| 日志事件英文标识 | `_eventLabel` 中文映射 |
