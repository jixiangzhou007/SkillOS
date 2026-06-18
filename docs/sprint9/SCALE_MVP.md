# Sprint 9–12 · 规模化

> **DoD**：Pro 内测可用；审计 CSV；只读公共市场；200 技能进度可观测

---

## 交付清单

| 能力 | 入口 |
|------|------|
| **Personal Pro 内测** | `POST /api/billing/enable-pro`（邀请码 `SKILLOS_PRO_BETA_CODE`） |
| **计划查询** | `GET /api/billing/plan` |
| **审计 CSV** | `GET /api/orgs/{id}/admin/audit/export` |
| **SLA 监控** | `GET /api/analytics/sla` |
| **规模化进度** | `GET /api/analytics/platform` |
| **只读公共市场** | `GET /api/marketplace/catalog` |
| **UGC 发布关闭** | `SKILLHUB_READONLY=true`（默认） |

---

## Personal Pro 限额

| 项 | Free | Pro（内测） |
|----|------|-------------|
| 技能 | 10 | 9999 |
| LLM/月 | 50 | 500 |

内测码环境变量：`SKILLOS_PRO_BETA_CODE=skillos-pro-beta`

---

## 计费集成（预留）

见 [`BILLING_RESEARCH.md`](BILLING_RESEARCH.md) — Stripe / 微信支付调研，未接生产。

---

## 验证

```bash
pytest tests/test_sprint9_scale.py -q
curl http://localhost:8765/api/analytics/sla
curl http://localhost:8765/api/marketplace/catalog
```
