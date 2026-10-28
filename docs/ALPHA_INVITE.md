# Closed Alpha — 邀请与反馈

> 配套：[`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md) · [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) · [`DEMO_VERIFIED_SPINE.md`](DEMO_VERIFIED_SPINE.md)

## 1. 邀请文案（可直接转发）

你好，想请你试用 **SkillOS Closed Alpha**（学徒 IDE）。

**你要验证的只有一件事（约 30 分钟）：**
登录 → 打开参考技能（如 GitHub Pull）看清 Trust Tier →（可选）对话沉淀一次 → 导出/「装到 Cursor」。

**请先读**（5 分钟）：
- Known Issues：仓库内 `docs/KNOWN_ISSUES.md`
- 黄金路径：`docs/DEMO_VERIFIED_SPINE.md`

**环境**：本机 Python、`.env` 里配置 `DEEPSEEK_API_KEY`，然后：

```bash
pip install -e .
skillos --server-only
# 浏览器打开 http://127.0.0.1:8765
```

**我们不承诺**：官方 Bench SOTA、应用商店、飞书/微信生产通道。

试用后请回下面三问（任意渠道）。

---

## 2. 反馈三问（必收）

1. **路径**：卡在哪一步？（登录 / Key / 列表 Tier / 沉淀 / 导出安装 / 其他）
2. **Tier**：是否理解 Verified ≠ 官方 SkillsBench？用一句话复述。
3. **安装**：是否成功装进 Cursor（或 `.agents` / `.dsh`）？若否，报错原文？

可选：最想砍掉的功能、最想补的一句文案。

---

## 3. 邀请名单模板（维护者填写）

目标：**5–20** 人。状态：`待邀` / `已邀` / `已反馈` / `弃用`。

| # | 称呼 | 渠道 | 角色（开发/PM/普通） | 状态 | 反馈摘要 | 日期 |
|---|------|------|----------------------|------|----------|------|
| 1 | （填写） | | | 待邀 | | |
| 2 | | | | 待邀 | | |
| 3 | | | | 待邀 | | |
| 4 | | | | 待邀 | | |
| 5 | | | | 待邀 | | |
| 6 | | | | 待邀 | | |
| 7 | | | | 待邀 | | |
| 8 | | | | 待邀 | | |
| 9 | | | | 待邀 | | |
| 10 | | | | 待邀 | | |

> 名单含个人联系方式时 **勿提交公开仓库**；可复制本表到私密笔记填写。本文件只保留模板。

---

## 4. Alpha 成功门槛（回顾）

| 指标 | 目标 |
|------|------|
| 30 分钟内完成黄金路径 | ≥ 70% |
| 理解 Verified ≠ 官方 Bench | ≥ 80% |
| 因安装/Key 放弃 | ≤ 20% |
