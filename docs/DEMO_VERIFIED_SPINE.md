# Demo：Verified Spine（学徒出师黄金路径）

> Phase V 验收剧本 · 约 15 分钟 · 2026-10 更新（Trust Tier + Evidence）

## 前置

```bash
pip install -e .
# .env 含 DEEPSEEK_API_KEY
python scripts/repair_reference_packs.py --all
skillos --server-only
# 浏览器 http://127.0.0.1:8765
```

## 三步

1. **登录**（文案：学徒 / 双门禁出师）→ 欢迎页「学徒出师 · Verified Spine」
2. **技能库**：Trust Tier 徽章 + 筛选芯片（全部 / Verified / 学徒 / Draft）；打开 `GitHub Pull`
3. **验收完成态**
   - Overview：**Trust Tier** + Gate A/B + 证据；质量条含 Tier
   - 「评测」Tab：本地 Quick8 | 官方 SkillsBench 分栏
   - 导出：「装进 Cursor」三步 + 复制路径 / Zip
   - 可选：`GET /api/skills/GitHub%20Pull/evidence`

## 预期

| 状态 | 含义 |
|------|------|
| **Verified** | 声明已验证 ≥1 **且** 域内 smoke min≥80 |
| **Provisional** | 可安装试用；双门禁未齐（学徒态） |
| **Draft** | 草稿 / 未完成 |

诚实口径：本地 Quick8 / smoke **≠** 官方 SkillsBench pass rate。

## 评测双轨（技能详情 →「评测」Tab）

打开 `GitHub Pull` → 更多 → **评测**，应看到左右分栏：

| 左栏 · 本地 Quick8 | 右栏 · 官方 SkillsBench |
|--------------------|-------------------------|
| 日常快检 / Gate B | BenchFlow 权威 pass rate |
| 本机可跑 | 需 Linux + Docker CI |
| 运行 Quick8 / 域内 | 请求 GitHub CI / CLI |

## 回归

```bash
python scripts/run_bench_regression.py
# 期望 ALL PASS（Reference + Generalize + Smoke 6/6）
```

## 批量回填 Trust Tier（可选）

```bash
python scripts/backfill_trust_tier.py
```
