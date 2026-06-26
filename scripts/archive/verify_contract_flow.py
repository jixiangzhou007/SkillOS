"""Multi-turn contract-review extraction verification against live dispatch API."""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
SID = f"verify-contract-review-{int(time.time())}"


def health() -> dict:
    with urllib.request.urlopen(f"{BASE}/health", timeout=10) as r:
        return json.loads(r.read())


def dispatch(msg: str) -> dict:
    body = json.dumps(
        {"message": msg, "session_id": SID, "mode": "create", "history": []}
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/api/skills/dispatch",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main() -> int:
    print("=== HEALTH ===")
    try:
        h = health()
    except urllib.error.URLError as e:
        print(f"FAIL: server not reachable: {e}")
        return 1
    print(json.dumps(h, ensure_ascii=False, indent=2))

    turns = [
        ("U1", "我想创建一个合同审核的技能"),
        ("U2", "销售合同，对方发来文件时触发，第一步先看内容和价格"),
        ("U3", "还要关注质保条款、免责条款、知识产权归属、对等违约金"),
        ("U4", "销售一般是软件集成类项目"),
        ("U5", "你还需什么信息？"),
        ("U6", "你目前技能沉淀成功了吗"),
    ]

    results = []
    for tag, msg in turns:
        print(f"\n=== {tag} USER ===")
        print(msg)
        try:
            d = dispatch(msg)
        except urllib.error.HTTPError as e:
            print(f"FAIL HTTP {e.code}: {e.read().decode()[:500]}")
            return 1
        reply = d.get("reply", "")
        actions = d.get("actions", [])
        print(
            f"--- AI (skill_active={d.get('skill_active')}, "
            f"draft={d.get('draft_saved')}, actions={len(actions)}) ---"
        )
        print(reply[:1200])
        if actions:
            print("BUTTONS:", [a["label"] for a in actions])
        results.append(
            {
                "tag": tag,
                "skill_active": d.get("skill_active"),
                "actions": len(actions),
                "bad_restart": msg in reply or reply.startswith("好的，我们来沉淀「**你目前"),
                "meta_ok": tag != "U6" or ("合同" in reply and msg not in reply),
            }
        )

    print("\n=== SUMMARY ===")
    failed = False
    for r in results:
        ok = r["skill_active"] and not r["bad_restart"] and r["meta_ok"]
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed = True
        print(
            f"{r['tag']}: {status} active={r['skill_active']} "
            f"actions={r['actions']} bad_restart={r['bad_restart']} meta_ok={r['meta_ok']}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
