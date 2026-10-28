# SkillOS 后续发布路线图（产品经理 / 总规划）

> **日期**：2026-10-28
> **定位**：从「本地能用的学徒 IDE」走到「可交给外部用户」
> **原则**：先证明可信交付，再扩通道；不宣称官方 SkillsBench SOTA
> **对照**：[`ARCH_OPTIMIZATION_PLAN.md`](ARCH_OPTIMIZATION_PLAN.md) · [`DEMO_VERIFIED_SPINE.md`](DEMO_VERIFIED_SPINE.md) · [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md)

---

## 1. 北极星与对外承诺

**北极星（90 天）**
Closed Alpha → Private Beta：陌生人能自助完成「沉淀 → 看清 Trust Tier → 装进 Cursor」。

**对外只承诺这一句**（其余一律 Known Limitations）：

> 在对话中把经验炼成 **Draft / 学徒 / Verified** 的 AgentSkills.io 技能，并安装到 Cursor（或兼容 harness）。

**明确不承诺（本路线图全程）**

- 支付 / 公开 UGC 市场
- 飞书·微信生产级通道
- 官方 SkillsBench 排行榜 SOTA
- 「装上就会自己越用越强」的无人值守进化

---

## 2. 发布阶梯（唯一主轴）

```
W0–W1   Ship Freeze          冻结可交付物 + 干净机黄金路径证据
   │
W1–W3   Closed Alpha         5–20 熟人 · BYOK · 你值班
   │
W3–W6   Private Beta         自助安装说明 + v0.3.6 + 支持渠道
   │
W6+     Public（可选）        安全评审 + 多租户硬验收 + 诚实 Hub 叙事
```

| 阶段 | 谁可以用 | Go 条件（全过才晋级） |
|------|----------|------------------------|
| **Ship Freeze** | 仅维护者 | 干净机走通 DEMO；Known Issues 成文；发布物 tag 可复现 |
| **Closed Alpha** | 邀请用户 | ≥70% 在 30 分钟内完成黄金路径；无 Key/安装类致命差评 |
| **Private Beta** | 申请制自助 | 安装文档无人值守；支持渠道；回滚说明；安全底线检查单签字 |
| **Public** | 公开 | 密钥策略、租户隔离、配额/成本文案、审计日志达标 |

---

## 3. 工作流（按优先级，不是按模块堆功能）

### Stream A — 交付冻结（W0–W1）· **最高优先**

| # | 事项 | 验收 |
|---|------|------|
| A1 | 合入未提交产品化改动，打 **`v0.3.6`**（勿复用历史 v0.3.5 叙事） | tag + CHANGELOG 对外可读 |
| A2 | 干净机 / 干净用户按 [`DEMO_VERIFIED_SPINE.md`](DEMO_VERIFIED_SPINE.md) 全路径走通并**录像** | 分镜 6 镜齐；失败步骤进 blocker 表 |
| A3 | 写 `docs/KNOWN_ISSUES.md`：Key 必配、Quick8≠官方 Bench、Hub 只读、install-local 写本机目录 | 登录页 / 引导可链到 |
| A4 | 清理或隔离未跟踪实验 `skills/`，避免脏库当默认体验 | 新用户列表可理解 |
| A5 | 默认密钥 / 弱口令 / 文档端口（8765）核对 | 发布说明写清改密 |

**产出**：可交给 Alpha 用户的「这一版」+ 3–5 分钟视频。

### Stream B — 陌生人可用性（W1–W3）· Alpha 成败关键

| # | 事项 | 验收 |
|---|------|------|
| B1 | 首次运行：无 Key / 额度用尽的**可行动**错误态（设置入口、BYOK 指引） | 故意不配 Key 测一遍 |
| B2 | 「为什么不是 Verified」一页说明（Gate A/B + 未跑 smoke）挂 Overview | 新人不求问你 |
| B3 | 参考技能一键打开（如 GitHub Pull）对照自己萃取 | 冷启动有锚点 |
| B4 | Draft 装本机前确认弹窗（避免误进模型目录） | 文案含 model_invocable |
| B5 | Alpha 反馈表：卡点步骤、是否装进 Cursor、是否理解 Tier | 回收 ≥5 份 |

**产出**：Alpha 成功标准可量化（见 §5）。

### Stream C — 安全与运营底线（W2–W4）· Beta 门槛

| # | 事项 | 验收 |
|---|------|------|
| C1 | 安全检查单：`install-local` 路径校验、JWT/租户二次用户冒烟、无明文 Key 进仓库 | checklist 签字 |
| C2 | 支持：Issues 模板 +「如何备份/清空 skills 数据」半页 | 用户可自助 |
| C3 | 回滚：上一 tag 启动方式写进 README 发布节 | 出问题能退 |
| C4 | 配额文案与 Personal Free / BYOK 一致（设置页已有则对齐文档） | 无「无限」暗示 |
| C5 | Hub：对外写死「本地目录 / seed，非应用商店」 | 预期管理 |

**产出**：Private Beta Go/No-Go 材料包。

### Stream D — 信任与评测诚实（贯穿，轻量）

| # | 事项 | 验收 |
|---|------|------|
| D1 | 保持评测 Tab 双轨文案；禁止对外口播「官方 SOTA」 | 评审口播稿 |
| D2 | 可选：`run_bench_regression.py` 在发版前再跑一次 ALL PASS | 日志归档 |
| D3 | 一页纸 [`paper/DUAL_GATE_NOTE.md`](paper/DUAL_GATE_NOTE.md) 链到 README / Demo | 叙事一致 |

**产出**：信任叙事不自爆。

### Stream E — 刻意延后（排期外，除非 Alpha 证明必须）

- 飞书 / 微信通道深化
- 支付与公开 marketplace
- Cordis / dsh 运行时深度集成、沙箱审批执行链
- MoE / SkillOpt 新算法、论文全文 arXiv
- 大范围 UI 视觉重构

---

## 4. 建议周计划（可执行日历）

### 本周（W0）— Freeze

1. [x] Commit + 本地 annotated tag **`v0.3.6`**；[x] `main` / tag 已 push
2. [x] 自动黄金路径 pytest；[ ] 人工 6 镜录像仍待录
3. [x] 起草 `KNOWN_ISSUES.md`
4. [x] Alpha 邀请/反馈模板 `ALPHA_INVITE.md`（名单私密填写）

### 下周（W1）— Alpha 开门

1. [ ] 发邀请 + 视频 + Known Issues（名单私密填写；录像仍待）
2. [x] 修 B1/B2/B4 + B3 参考技能入口（无 Key 横幅、为何非 Verified、Draft 安装确认、GitHub Pull 芯片）
2b. [x] UI 打磨（欢迎品牌层级、导出降噪、Alpha 须知抽屉）；`GET /api/docs/known-issues`
3. 每日收集卡点，只修 P0

### W2–W3 — Alpha 收敛 / Stream C

1. 达成 §5 Alpha 指标或写明未达标原因
2. [x] Stream C 材料落地：`SECURITY_CHECKLIST` / Issue 模板 / `BACKUP_AND_RESET` / README 回滚 / Hub 非商店叙事 / install-local 路径加固（签字与冒烟仍待人工）
3. 决定：延长 Alpha / 进 Private Beta / 缩 scope

### W4–W6 — Private Beta（若 Go）

1. 自助安装文档（Windows / macOS 各一）
2. tag 冻结 + 支持渠道值班约定
3. 申请制放量，仍不公开营销「商店」

---

## 5. 成功标准（数字优先）

### Closed Alpha（必须）

| 指标 | 目标 |
|------|------|
| 邀请用户完成黄金路径（30 min 内） | ≥ 70% |
| 理解「Verified ≠ 官方 Bench」 | ≥ 80%（问卷或访谈） |
| 因安装/Key 放弃 | ≤ 20% |
| 你们复盘出的 Top3 卡点 | 全部进下一迭代或标为 Wontfix |

### Private Beta（必须）

| 指标 | 目标 |
|------|------|
| 无值班协助下完成安装+一次沉淀 | ≥ 50% |
| P0 安全项 | 100% 关闭或有书面残留风险 |
| 支持响应 | 工作日 48h 内有回复约定 |

### 不作为本阶段 KPI

- Hub GMV、技能数量爆炸、论文引用、官方 leaderboard 名次

---

## 6. Go / No-Go（发布决策表）

每次晋级只问四句：

1. **承诺**：这一版对外那句话是否仍成立？
2. **证据**：干净机路径 + 录像是否在本周内？
3. **伤害**：最坏情况（写错目录、Key 泄露、误标 Verified）是否可接受且可回滚？
4. **支持**：谁值班、用户找谁？

任一「否」→ **HOLD**，不许靠加功能强行过门。

---

## 7. 角色与决策

| 角色 | 职责 |
|------|------|
| 总规划 / PM | 守承诺边界、晋级 Go/No-Go、排 Stream 优先级 |
| 工程 | A/B/C 落地；发版前回归；不擅自开 Stream E |
| 你（产品负责人） | Alpha 邀请、录像拍板、tag 是否公开 |

**冲突裁决**：体验争议服从「黄金路径完成率」；叙事争议服从 Dual Gate 诚实口径。

---

## 8. 与旧计划的关系

| 旧文档 | 关系 |
|--------|------|
| Phase 0–7 [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md) | 能力已大体交付；**不再作为发布主轴** |
| Phase V/T [`ARCH_OPTIMIZATION_PLAN.md`](ARCH_OPTIMIZATION_PLAN.md) | 脊梁已齐；后续以**本发布阶梯**为准 |
| Demo / 一页纸 | 继续服务 Alpha 获客与叙事，不替代可用性证据 |

---

## 9. 立即下一动作（今日可开干）

1. **冻结**：整理并提交当前产品化 diff，起草 `v0.3.6` 说明
2. **取证**：按 DEMO 分镜录一条完整路径（失败也录）
3. **边界**：新建 `KNOWN_ISSUES.md` 初稿
4. **邀约**：列 10 个 Alpha 候选人 + 反馈三问（路径卡在哪 / Tier 懂不懂 / 装进 Cursor 了没）

做完 1–3，才进入「继续写功能」；否则功能只是在延长 demo。
