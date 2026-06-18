# 计费集成调研（Sprint 9 预留）

## 目标

Personal Pro / Team 计划付费，M10+ 上线。

## 方案对比

| 渠道 | 适用 | 集成复杂度 | 备注 |
|------|------|------------|------|
| **Stripe** | 海外 / 信用卡 | 中 | Checkout Session + Webhook |
| **微信支付** | 国内 C 端 | 高 | 需商户号 + 企业资质 |
| **支付宝** | 国内 | 高 | 同上 |
| **飞书/isv 账单** | B 端 org | 中 | 与 org 商用对齐 |

## 建议数据模型（已预留）

- `user_plans(user_id, plan, expires_at)` — 当前计划
- Webhook  handler 占位：`skillos/billing/webhooks.py`（未实现）

## Stripe 伪流程

1. `POST /api/billing/checkout` → Stripe Checkout URL
2. Webhook `checkout.session.completed` → `set_user_plan(user, personal_pro)`
3. `customer.subscription.deleted` → 降级 `personal_free`

## 环境变量（未来）

| 变量 | 用途 |
|------|------|
| `STRIPE_SECRET_KEY` | API |
| `STRIPE_WEBHOOK_SECRET` | 签名校验 |
| `SKILLOS_PRO_PRICE_ID` | Pro 月付 Price |

## 当前状态

**仅内测码启用 Pro**，无真实支付。生产前需 PCI/合规评审。
