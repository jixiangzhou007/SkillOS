---
name: Customer Refund Processing
created_at: '2026-06-13T03:04:22Z'
updated_at: '2026-06-16T15:43:26Z'
diffused_from: 电商客服退款处理
epistemic:
  source: Customer Refund Processing
  source_type: llm_generated
  total_claims: 15
  verified: 0
  pending: 15
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781624606_f87bfd
  - ec_1781624606_115423
  - ec_1781624606_387ab9
  - ec_1781624606_1cd030
  - ec_1781624607_385680
  - ec_1781624607_a985e2
  - ec_1781624607_b9f366
  - ec_1781624607_526de6
  - ec_1781624607_0910ee
  - ec_1781624607_4a23ac
  - ec_1781624607_f2ff75
  - ec_1781624608_c79cf5
  - ec_1781624608_f2020f
  - ec_1781624608_5d0df7
  - ec_1781624608_3bf43f
  pending_ids:
  - ec_1781624606_f87bfd
  - ec_1781624606_115423
  - ec_1781624606_387ab9
  - ec_1781624606_1cd030
  - ec_1781624607_385680
  - ec_1781624607_a985e2
  - ec_1781624607_b9f366
  - ec_1781624607_526de6
  - ec_1781624607_0910ee
  - ec_1781624607_4a23ac
  - ec_1781624607_f2ff75
  - ec_1781624608_c79cf5
  - ec_1781624608_f2020f
  - ec_1781624608_5d0df7
  - ec_1781624608_3bf43f
  processed_at: 1781624608.6184242
version: 7
---

根据您的改进建议，我对技能文档进行了精准改进，主要补充了身份核实、订单状态判断、退款原因分类对应的凭证要求，以及“仅退款”与“退货退款”的区分条件，并增加了转人工处理的异常触发条件。以下是改进后的完整技能文档：

---

# Skill Name: Customer Refund Processing
## Core Problem
Process a customer refund by verifying the order, checking policy, calculating the amount, and issuing payment.
## S_route
| Intent | Action | Resource |
| Initiate refund | **Verify customer identity (order owner match)** | Customer account system |
| Initiate refund | **Check order status: (a) not shipped; (b) shipped but not received; (c) received** | Order management system |
| Initiate refund | Verify order ID and purchase date | Order management system |
| Initiate refund | Check refund policy (30-day window) | Refund policy database |
| Initiate refund | **Classify refund reason: (1) 7-day no-reason return; (2) product damaged; (3) wrong item shipped; (4) other** | Refund reason taxonomy |
| Initiate refund | **If reason = product damaged or wrong item: require photo/video evidence from customer** | Evidence upload system |
| Initiate refund | **If reason = 7-day no-reason return: no evidence required** | — |
| Initiate refund | **If reason = other: require detailed description and optional evidence** | Evidence upload system |
| Initiate refund | **Determine refund type: (A) only refund (order not shipped or not received); (B) return and refund (order received)** | Order status + refund policy |
| Initiate refund | **If refund type = return and refund: issue return label and wait for item return** | Return logistics system |
| Initiate refund | **If refund type = only refund: proceed to amount calculation** | — |
| Initiate refund | **If order is outside 30-day window OR reason is not covered by policy: escalate to human agent** | Escalation system |
| Initiate refund | Calculate refund amount (full or partial based on policy) | Pricing engine |
| Initiate refund | Issue payment to original payment method | Payment gateway |

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 待确认
- ⏳ [待验证] Intent → Action (`ec_1781624606_f87bfd`)
- ⏳ [待验证] Initiate refund → **Verify customer identity (order owner match)** (`ec_1781624606_115423`)
- ⏳ [待验证] Initiate refund → **Check order status: (a) not shipped; (b) shipped but not received; (c) received** (`ec_1781624606_387ab9`)
- ⏳ [待验证] Initiate refund → Verify order ID and purchase date (`ec_1781624606_1cd030`)
- ⏳ [待验证] Initiate refund → Check refund policy (30-day window) (`ec_1781624607_385680`)
- ⏳ [待验证] Initiate refund → **Classify refund reason: (1) 7-day no-reason return; (2) product damaged; (3) wrong item shipped; (4) (`ec_1781624607_a985e2`)
- ⏳ [待验证] Initiate refund → **If reason = product damaged or wrong item: require photo/video evidence from customer** (`ec_1781624607_b9f366`)
- ⏳ [待验证] Initiate refund → **If reason = 7-day no-reason return: no evidence required** (`ec_1781624607_526de6`)
- ⏳ [待验证] Initiate refund → **If reason = other: require detailed description and optional evidence** (`ec_1781624607_0910ee`)
- ⏳ [待验证] Initiate refund → **Determine refund type: (A) only refund (order not shipped or not received); (B) return and refund (o (`ec_1781624607_4a23ac`)
- ⏳ [待验证] Initiate refund → **If refund type = return and refund: issue return label and wait for item return** (`ec_1781624607_f2ff75`)
- ⏳ [待验证] Initiate refund → **If refund type = only refund: proceed to amount calculation** (`ec_1781624608_c79cf5`)
- ⏳ [待验证] Initiate refund → **If order is outside 30-day window OR reason is not covered by policy: escalate to human agent** (`ec_1781624608_f2020f`)
- ⏳ [待验证] Initiate refund → Calculate refund amount (full or partial based on policy) (`ec_1781624608_5d0df7`)
- ⏳ [待验证] Initiate refund → Issue payment to original payment method (`ec_1781624608_3bf43f`)
