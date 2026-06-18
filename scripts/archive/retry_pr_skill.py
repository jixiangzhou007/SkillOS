import json, time, urllib.request
BASE = "http://127.0.0.1:8765"
SID = f"user-sim-prreview-retry-{int(time.time())}"
turns = [
    "帮我做一个 GitHub PR 代码审查技能",
    "触发：收到 PR review 请求时；先看标题描述有没有说明动机",
    "diff 超500行建议拆分；查 SQL 注入、硬编码密钥、null 和异常处理",
    "风格用 suggestion，阻塞才 request changes；approve 前 CI 全绿",
    "请直接生成并保存技能文档，不要再提问",
]
for i, t in enumerate(turns, 1):
    body = json.dumps({"message": t, "session_id": SID, "mode": "create", "history": []}).encode()
    req = urllib.request.Request(
        BASE + "/api/skills/dispatch", data=body, headers={"Content-Type": "application/json"}
    )
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    print(f"[{i}] saved={r.get('skill_saved')} reply={ (r.get('reply') or '')[:120]}")
    if r.get("skill_saved"):
        print("NAME:", r["skill_saved"])
        q = r.get("quality") or {}
        print("QUALITY:", q.get("official_score"), q.get("official_grade"))
        break
