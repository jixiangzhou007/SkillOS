# SkillOS 架构优化与原型验证计划（2026-10）

> **角色视角**：产品总规划 / 系统架构
> **背景**：SkillOS 设计较早；2025–2026 Agent Skills 已成标准供给链，学术侧集体转向「验证门槛 + 自进化」。本计划在**不推翻核心哲学**的前提下，对齐最新环境并尽快做出可演示、可证伪的原型闭环。
> **原则**：先证明「双门禁可信」，再扩「通道与进化」；少叙事、多可复现数字。

---

## 0. 形势判断（一句话）

| 当时判断 | 2026 现状 | 架构含义 |
|----------|-----------|----------|
| Experience ≠ Knowledge | 已被 EVISKILL / CoEvoSkills / OpenSkill / SoK 验证为赛道中轴 | **保留**，但改为「claim 层」而非「全球唯一」 |
| 人机苏格拉底萃取 | 主流冲全自动自进化 | **差异化主航道**，不要跟卷全自动 |
| AgentSkills 分发 | 已解决；正确性/供应链成痛点 | 产品卖点从「造 skill」→「**验货 + 安装**」 |
| Bench / 烟测 | 论文用 SkillsBench pass rate 说话 | Outcome gate 必须与认识论**平级**，不能当附属 |

**产品一句话（更新）**

> SkillOS：让 AI 像学徒一样向人学习，把经验炼成 **AgentSkills.io 可安装技能**，并经 **声明级认识论 + 任务级 bench 双门禁** 后标为 Verified。
>  canonical 叙事见根目录 [`DESIGN.md`](../DESIGN.md)（2026-10 重订）。

---

## 1. 思维层重构：从「三创新堆叠」→「一条黄金路径」

### 1.1 旧思维风险

早期规划把三件事并列（认识论 / 苏格拉底 / MoE 进化），工程上容易变成：

- 模块多、故事厚、**一条可演示闭环不稳**
- Related Work 易说成「唯一」，被 2026 论文打脸
- 用户感知停在「又一个聊天写 SKILL.md」

### 1.2 新思维模型：Dual Verification Stack（双门禁栈）

```
输入（对话 / 链接 / 文件）
        ↓
   Socratic Draft（人机共创，默会知识）
        ↓
   ┌──────────────── Dual Gate ────────────────┐
   │  Gate A  Claim Epistemology               │
   │          Experience → Knowledge 晋升      │
   │  Gate B  Outcome Verification             │
   │          Quick8 / smoke / (官方 SkillsBench)│
   └────────────────────┬──────────────────────┘
                        ↓
              Trust Tier 标注
         Draft | Provisional | Verified
                        ↓
         Export（Cursor / Claude / Zip）
```

对齐外部工作的精确说法：

- **Gate A** ≈ 你们独有的 claim-level 认识论（对比 EVISKILL 的 evidence cards：你们更偏哲学分层）
- **Gate B** ≈ CoEvoSkills / VeriSkill 的「只接纳提升任务表现的修订」
- **Trust Tier** ≈ SoK 呼吁的 marketplace 信任分级（产品可先做本地三级，不做支付）

### 1.3 刻意收缩（架构纪律）

| 保留 / 升格 | 降级为可选 / 延后 |
|-------------|-------------------|
| 苏格拉底三路径沉淀 | MoE 全量自进化（跟 SkillOpt 论文对齐后再开） |
| Dual Gate + Trust Tier UI | Marketplace 支付 / 大规模租户 |
| AgentSkills.io 严格导出 + 安装引导 | 「全球唯一认识论」话术 |
| 可版本化 domain pack（`configs/`） | 更多 domain 模板数量竞赛 |
| 本地 Quick8 回归 + 官方 CI 口径分离 | 用本地代理指标对外宣称「官方 pass」 |

---

## 2. 架构层优化（系统怎么切）

### 2.1 目标架构（逻辑视图）

```
┌─────────────── Product Surface ───────────────┐
│  Workspace（对话/链接/文件）· Verified 结果卡  │
│  Trust Tier · Export Channel（Cursor 优先）   │
└─────────────────────┬─────────────────────────┘
                      │ precipitation API
┌─────────────────────▼─────────────────────────┐
│  Extraction Core（Socratic Agent · 七步 URL）  │
└─────────────────────┬─────────────────────────┘
          ┌───────────┴───────────┐
┌─────────▼─────────┐   ┌─────────▼─────────┐
│ Epistemic Kernel  │   │ Outcome Kernel    │
│ classify/falsify  │   │ smoke + Quick8    │
│ promote/lineage   │   │ pack sync + Δ门禁 │
└─────────┬─────────┘   └─────────┬─────────┘
          └───────────┬───────────┘
┌─────────────────────▼─────────────────────────┐
│  Skill Artifact（SKILL.md · DNA · pack meta）  │
│  TrustTier + bench_quality + epistemic YAML │
└───────────────────────────────────────────────┘
```

### 2.2 五条架构决策（ADR 级）

1. **Outcome Gate 与 Epistemic Gate 同级**
   `apply_save_gate` / Quick8 不再是「发版附属」，而是沉淀完成态的硬条件；UI 上 Verified 必须两闸都过（或显式降级为 Provisional）。

2. **Evidence Card 统一证据模型（借鉴 EVISKILL，不照搬）**
   每条晋升/拒绝绑定可回放证据：`source_id` · `falsify_result` · `bench_task_id` · `delta_pp`。详情页「认识论」Tab 以证据卡为主，少空泛 ✅。

3. **Pack 配置可复现**
   运行时 `data/domain_packs/` 保持 ignore；权威快照在 `configs/reference_domain_packs/`；回归脚本强制 sync（已起步，需泛化 cohort 同样入库）。

4. **Injection 服从 Progressive Disclosure**
   `skill_injection_payload` 优先 S_body / 应答速查 / S_route，控制 token；对齐 Anthropic skill authoring 最佳实践，避免整份 YAML+认识论灌进 prompt。

5. **Trust Tier 成为对外契约**
   - `draft`：萃取中
   - `provisional`：结构完整，仅过 Gate A 或仅过 smoke
   - `verified`：Gate A 达标 **且** Gate B（smoke≥80 + 域内 Quick8 Δ≥门槛）
   导出物 frontmatter 写入 `trust_tier` + `verified_at`。

### 2.3 模块边界清理（防膨胀）

| 层 | 允许依赖 | 禁止 |
|----|----------|------|
| frontend | API 契约、Trust Tier 展示 | 直接读 epistemology 内部结构 |
| extraction | epistemic + outcome kernels | 绕过 gate 写「已验证」 |
| evolution/skillopt | 只消费 verified 技能 | 在未过 Gate B 时扩散到其他技能 |
| marketplace/hub | 展示 trust_tier | Phase 内不做支付 |

---

## 3. 产品总规划：两阶段（不是再开 Phase 0–7）

### Phase V — Verified Spine（验证脊梁）· **优先 · 本周–10 天**

**目标**：任何人 15 分钟内可走通「对话 → Verified → Cursor 安装」，并看到双门禁证据。

**非目标**：新通道、新进化算法、论文定稿。

### Phase T — Trust & Reproducibility（信任与可复现）· **随后 2–3 周**

**目标**：官方 SkillsBench CI 口径、Evidence Card、trust_tier 写进标准导出、Related Work 改写、可选 arXiv 短文。

---

## 4. 尽快完成原型更新与验证（Phase V 冲刺清单）

### 4.1 验收标准（DoD）

| # | 验收项 | 度量 |
|---|--------|------|
| V1 | 黄金路径 E2E | 登录 → 对话沉淀一项参考技能 → 结果卡显示 Trust Tier → Zip/路径导出 |
| V2 | 双门禁可见 | UI 同时展示：认识论摘要 + smoke/Quick8 Δ（或「未跑 bench」诚实状态） |
| V3 | 回归绿 | `python scripts/run_bench_regression.py` → ALL PASS |
| V4 | 可复现 pack | `configs/reference_domain_packs` 含 reference；`repair_reference_packs` 可重建 |
| V5 | 单页 Demo 脚本 | `docs/DEMO_VERIFIED_SPINE.md`：3 步操作 + 预期截图点 |

### 4.2 执行顺序（建议严格按序，避免并行发散）

```
Day 1–2   Trust Tier 契约 + 结果卡接线
Day 2–3   Gate B 完成态硬规则（未过 smoke 不得标 Verified）
Day 3–4   Evidence 最小集（claim 计数 + 最近 smoke 行）挂到结果卡/详情
Day 4–5   浏览器 E2E + 回归 ALL PASS 固化
Day 5–7   Demo 脚本 + 录像素材；remote/push；可选 v0.3.5 tag
```

### 4.3 任务拆解

#### V-A · Trust Tier（产品契约）

- [x] 后端：沉淀完成响应增加 `trust_tier` / `gates: {epistemic, outcome}`
- [x] `precipitation-result.js`：Verified / Provisional / Draft 三态（已有卡片则改标签语义）
- [x] 禁止：smoke 失败仍展示「已验证」文案

#### V-B · Outcome Gate 升格

- [x] 保存路径：`apply_save_gate` 失败 → `provisional`，不写 verified（`compute_trust_tier`）
- [x] 参考三技能回归：`bench_regression_1793072689` **ALL PASS**（+28 / +18.6 / +22）
- [x] 文档：本地 Quick8 ≠ 官方 BenchFlow（结果卡 hint + DEMO 页）

#### V-C · 可复现与回归

- [x] 泛化 cohort pack → `configs/generalize_domain_packs/`
- [x] `repair_reference_packs.py --all` + 回归前 `sync_all_packs`
- [ ] 配置 `origin` 并 push（仓库仍无 remote —— 环境阻塞）

#### V-D · 原型验证剧本

- [x] `docs/DEMO_VERIFIED_SPINE.md`
- [x] 浏览器：注册登录 OK；`GET .../evidence` → GitHub Pull **verified**
- [x] `run_bench_regression.py` ALL PASS
- [x] `backfill_trust_tier.py` 全库回填

### 4.4 明确不做（本冲刺）

- MoE / SkillOpt 新算法
- 飞书/微信通道新功能
- 支付与公开 marketplace
- 大范围前端视觉重构
- 宣称「官方 SkillsBench SOTA」
- git push（无 origin）

---

## 5. Phase T 提纲

1. [x] **Evidence Card API**（最小）：`GET /api/skills/{name}/evidence` + 结果卡证据块
2. [x] 官方 SkillsBench CI 与本地 Quick8 分栏产品化（技能详情「评测」Tab）
3. [x] Related Work 改写起步：`docs/PAPERS.md` 去掉「全球唯一」、对齐 Dual Gate
4. [x] `trust_tier` → export `metadata.skillos_trust_tier`
5. [ ] 短文 / Demo Day 录像

---

## 6. 成功标准（规划师视角）

| 层级 | 通过信号 |
|------|----------|
| 思维 | 团队统一说「双门禁 + Trust Tier」，不再说「三创新并列」 |
| 架构 | 萃取不能绕过 Outcome/Epistemic kernel 写 verified |
| 原型 | V1–V5 清单全勾；外人可按 Demo 脚本复现 |
| 学术 | 叙事改为 claim×outcome 组合贡献，Related Work 对齐 2026 |

---

## 7. 状态与下一步

**Phase V 已交付**；**Phase T 分栏 UI 已交付**（2026-10-27）。

**下一步**：

1. 提交并 `git push origin main`（含 `v0.3.4`；可选打 `v0.3.5`）——需你明确授权
2. Demo Day 录像（主技能：**GitHub Pull**）
