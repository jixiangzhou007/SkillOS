---
name: REST API 设计流程专家
created_at: '2026-06-15T13:21:46Z'
updated_at: '2026-06-15T13:21:46Z'
description: 如何从需求评审到上线，标准化地完成REST API设计全流程，确保前后端并行开发、规范统一、联调高效。
portable_slug: rest-api
draft: false
epistemic:
  source: session:72280fc12730
  source_type: conversation
  total_claims: 39
  verified: 33
  pending: 6
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781529707_e89fe0
  - ec_1781529708_b80b6b
  - ec_1781529708_24a003
  - ec_1781529709_2494ea
  - ec_1781529710_161767
  - ec_1781529711_f75415
  - ec_1781529713_f23529
  - ec_1781529714_5380d1
  - ec_1781529715_b65d1f
  - ec_1781529715_db7726
  - ec_1781529715_d66e64
  - ec_1781529716_4cec5b
  - ec_1781529716_dc5717
  - ec_1781529717_397d15
  - ec_1781529718_432f00
  - ec_1781529719_c8752e
  - ec_1781529719_72d2c5
  - ec_1781529720_dbe1c6
  - ec_1781529721_e05022
  - ec_1781529722_9af493
  - ec_1781529723_ecbc9a
  - ec_1781529724_21abc8
  - ec_1781529725_0e58dc
  - ec_1781529725_2dc769
  - ec_1781529726_940036
  - ec_1781529727_82d42f
  - ec_1781529728_2dbfa5
  - ec_1781529729_5435bf
  - ec_1781529730_34a05d
  - ec_1781529731_3ce9a3
  - ec_1781529732_24828d
  - ec_1781529733_b41895
  - ec_1781529734_7bbfe0
  - ec_1781529734_15ea9e
  - ec_1781529735_95b677
  - ec_1781529736_2ed292
  - ec_1781529737_768ff5
  - ec_1781529738_ba0239
  - ec_1781529739_134e53
  pending_ids:
  - ec_1781529708_24a003
  - ec_1781529715_b65d1f
  - ec_1781529715_d66e64
  - ec_1781529716_dc5717
  - ec_1781529725_2dc769
  - ec_1781529728_2dbfa5
  processed_at: 1781529741.5888908
version: 1
---

# REST API 设计流程专家

## 核心问题
如何从需求评审到上线，标准化地完成REST API设计全流程，确保前后端并行开发、规范统一、联调高效。

## When to use
- keywords: API设计, 接口规范, 需求评审, 联调测试, RESTful, OpenAPI, Swagger, Mock, Prism
- context: 产品经理在Jira创建API需求后触发；后端/前端/测试需要对齐API规范时；需要沉淀API设计文档或进行技术评审时
- excludes: 用户仅讨论前端UI设计、数据库表结构设计、非HTTP协议的接口设计

## Instructions
Follow these steps in order. Ask the user if anything is marked [待确认].

1. **需求评审（触发条件：Jira需求创建 + PRD/前端原型就绪）**
   - 检查需求描述中的模糊点、边界条件、角色权限、数据格式争议
   - 明确API的使用方（买家/卖家/管理员）
   - 确认排序字段、分页规范（page起始值、size上限、是否需要total）
   - 确认枚举值的存储与展示分离策略（后端存code，前端展示label）
   - 确认是否涉及多语言/多时区
   - **确认数据格式与单位**：例如价格是“元”还是“分”，时间戳是“秒”还是“毫秒”
   - 输出：需求评审结论（澄清/驳回/通过）

2. **接口设计**
   - 遵循RESTful规范，URL使用kebab-case（小写字母+连字符）
   - 返回格式统一为JSON
   - 定义资源路径、HTTP方法、请求参数、响应结构
   - 设计错误响应格式（统一错误码、错误消息字段）
   - 输出：接口设计草稿（待评审）

3. **OpenAPI文档编写**
   - 使用Swagger（OpenAPI规范）编写接口文档
   - 包含：路径、参数、请求体、响应体、错误码
   - 文档自动生成，作为前后端契约
   - 输出：OpenAPI规范文档（YAML/JSON）

4. **Mock并行**
   - 使用Prism搭建Mock Server
   - 基于OpenAPI文档自动生成Mock接口
   - 前端/测试可立即调用Mock接口进行开发与测试
   - 输出：可访问的Mock Server地址

5. **联调测试**
   - 前端连接后端真实服务进行联调
   - 对比Mock响应与真实响应的一致性
   - 修复接口差异与bug
   - 输出：联调通过确认

6. **上线**
   - 部署后端服务到生产环境
   - 更新OpenAPI文档指向生产环境地址
   - 关闭或保留Mock Server（[待确认]）
   - 输出：上线完成通知

## Decision routes
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 用户说“需要评审API需求”或“需求评审” | 执行步骤1：需求评审 | 需确认PRD和前端原型已就绪 |
| 用户说“设计接口”或“API设计” | 执行步骤2：接口设计 | 需先完成需求评审 |
| 用户说“写文档”或“OpenAPI”或“Swagger” | 执行步骤3：OpenAPI文档编写 | 需先完成接口设计 |
| 用户说“Mock”或“并行开发” | 执行步骤4：Mock并行 | 需先完成OpenAPI文档 |
| 用户说“联调”或“测试” | 执行步骤5：联调测试 | 需后端服务已部署 |
| 用户说“上线”或“发布” | 执行步骤6：上线 | 需联调测试通过 |

## Inputs
- prd_url: string, 必填, PRD文档链接或文件路径
- prototype_url: string, 必填, 前端原型链接或文件路径
- jira_ticket: string, 可选, Jira需求编号
- existing_openapi_spec: string, 可选, 已有OpenAPI规范文件路径（如有）
- mock_server_base_url: string, 默认"http://localhost:4010", Mock Server的基础URL

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: API设计, 接口规范, 需求评审, 联调测试, RESTful, OpenAPI, Swagger, Mock, Prism
- ✅ context: 产品经理在Jira创建API需求后触发；后端/前端/测试需要对齐API规范时；需要沉淀API设计文档或进行技术评审时
- ✅ 需求评审（触发条件：Jira需求创建 + PRD/前端原型就绪）
- ✅ 检查需求描述中的模糊点、边界条件、角色权限、数据格式争议
- ✅ 明确API的使用方（买家/卖家/管理员）
- ✅ 确认排序字段、分页规范（page起始值、size上限、是否需要total）
- ✅ 确认枚举值的存储与展示分离策略（后端存code，前端展示label）
- ✅ 确认数据格式与单位：例如价格是“元”还是“分”，时间戳是“秒”还是“毫秒”
- ✅ 遵循RESTful规范，URL使用kebab-case（小写字母+连字符）
- ✅ 设计错误响应格式（统一错误码、错误消息字段）
- ✅ 输出：接口设计草稿（待评审）
- ✅ 使用Swagger（OpenAPI规范）编写接口文档
- ✅ 包含：路径、参数、请求体、响应体、错误码
- ✅ 文档自动生成，作为前后端契约
- ✅ 输出：OpenAPI规范文档（YAML/JSON）

### 待确认
- 📋 [evidence] excludes: 用户仅讨论前端UI设计、数据库表结构设计、非HTTP协议的接口设计 (`ec_1781529708_24a003`)
- ⏳ [待验证] 确认是否涉及多语言/多时区 (`ec_1781529715_b65d1f`)
- 📋 [evidence] 输出：需求评审结论（澄清/驳回/通过） (`ec_1781529715_d66e64`)
- 📋 [evidence] 定义资源路径、HTTP方法、请求参数、响应结构 (`ec_1781529716_dc5717`)
- 📋 [evidence] 前端连接后端真实服务进行联调 (`ec_1781529725_2dc769`)
- ⏳ [待验证] 关闭或保留Mock Server（[待确认]） (`ec_1781529728_2dbfa5`)
