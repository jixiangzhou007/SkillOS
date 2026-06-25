"""Seed knowledge data for UI testing. Run after server starts."""
import requests
import json
import time

BASE = 'http://127.0.0.1:8765'

def post(path, data):
    r = requests.post(f'{BASE}{path}', json=data, headers={'Content-Type':'application/json'})
    return r.json() if r.ok else {'error': r.status_code, 'detail': r.text[:100]}

def get(path):
    r = requests.get(f'{BASE}{path}')
    return r.json() if r.ok else {}

# 1. Ingest knowledge items
items = [
    {"content": "合同审核流程中，仲裁条款检查是最关键的步骤——地域差异直接影响执行难度", "category": "合同审核", "source": "企业法务手册"},
    {"content": "采购合同第7条经常悄悄修改仲裁地，从北京改为上海，风险等级为高风险", "category": "合同审核", "source": "实战案例"},
    {"content": "退款处理中，staging环境返回200不代表退款真正成功，需要检查payment_events表", "category": "退款处理", "source": "技术文档"},
    {"content": "客户投诉分级：Level1(可即时解决)、Level2(需升级)、Level3(涉及合规)", "category": "投诉处理", "source": "客服SOP"},
    {"content": "代码审查清单：先看测试覆盖，再看逻辑变更，最后检查代码风格", "category": "代码审查", "source": "团队规范"},
    {"content": "数据分析报告标准结构：摘要→数据来源→分析方法→关键发现→建议", "category": "数据分析", "source": "行业最佳实践"},
    {"content": "API接口设计中，版本号必须放在URL路径中而非header——这是RESTful规范要求", "category": "API设计", "source": "REST API设计指南"},
    {"content": "request_id和trace_id在日志系统中是同一个东西，不要重复记录", "category": "故障排查", "source": "运维手册"},
]

print('=== Seeding knowledge items ===')
for item in items:
    result = post('/api/knowledge/ingest', {
        "content": item["content"],
        "category": item["category"],
        "source": item["source"],
        "level": "experience"
    })
    print(f'  {item["category"]}: {result.get("status","?")}')

# 2. Verify some knowledge (promote to verified)
print('\n=== Verifying knowledge ===')
kb = get('/api/knowledge/?limit=20')
for item in (kb.get('items', []) or [])[:3]:
    r = post(f'/api/knowledge/review/{item.get("id","")}', {"approved": True})
    print(f'  {item.get("content","")[:50]}... → approved')

# 3. Create a review queue item
print('\n=== Creating review items ===')
post('/api/knowledge/ingest', {
    "content": "发票报销审批中，超过5000元的单据需要二级审批——财务主管+部门总监",
    "category": "报销审批", "source": "财务制度", "level": "experience"
})

# 4. Trigger a knowledge cycle
print('\n=== Triggering knowledge cycle ===')
r = post('/api/knowledge/cycle', {})
print(f'  Cycle: {r.get("task_id","?")}')

# 5. Seed journal events
print('\n=== Seeding journal events ===')
journal_events = [
    {"type": "skill_created", "summary": "创建技能「合同审核流程」", "content": "合同审核标准流程 v1"},
    {"type": "knowledge_ingested", "summary": "摄入知识：仲裁条款检查指南", "content": "仲裁条款检查是合同审核核心"},
    {"type": "claim_verified", "summary": "验证声明：退款处理staging检查", "content": "staging 200不代表成功"},
    {"type": "skill_optimized", "summary": "优化技能「退款处理」v2", "content": "增加payment_events检查步骤"},
    {"type": "cycle_completed", "summary": "知识沉淀循环完成", "content": "处理3条新知识，验证1条"},
]
for evt in journal_events:
    post('/api/knowledge/journal', evt)
    print(f'  {evt["type"]}: {evt["summary"][:40]}')

print('\n=== Seed complete ===')
print('Knowledge views should now have data.')
