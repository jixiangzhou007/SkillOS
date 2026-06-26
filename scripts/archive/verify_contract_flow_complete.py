"""Full contract-review extraction: explore through final skill generation."""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765"
SID = f"verify-contract-complete-{int(time.time())}"
SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"


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
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def check_skill_on_disk(name: str) -> dict:
    path = SKILLS_ROOT / name / "SKILL.md"
    if not path.exists():
        return {"exists": False, "path": str(path)}
    text = path.read_text(encoding="utf-8")
    is_draft = "draft: true" in text.split("---")[1] if text.startswith("---") else False
    has_skill_doc = "Core Problem" in text or "S_route" in text or "## " in text
    return {
        "exists": True,
        "path": str(path),
        "is_draft": is_draft,
        "has_body": has_skill_doc,
        "size": len(text),
    }


def main() -> int:
    print("=== HEALTH ===")
    try:
        print(json.dumps(health(), ensure_ascii=False, indent=2))
    except urllib.error.URLError as e:
        print(f"FAIL: server not reachable: {e}")
        return 1

    turns = [
        ("U1", "我想创建一个合同审核的技能"),
        ("U2", "销售合同，对方发来文件时触发，第一步先看内容和价格"),
        ("U3", "还要关注质保条款、免责条款、知识产权归属、对等违约金"),
        ("U4", "销售一般是软件集成类项目"),
        ("U5", "你还需什么信息？"),
        ("U6", "可以了，生成技能文档吧"),
    ]

    last = {}
    for tag, msg in turns:
        print(f"\n=== {tag} USER ===")
        print(msg)
        try:
            d = dispatch(msg)
        except urllib.error.HTTPError as e:
            print(f"FAIL HTTP {e.code}: {e.read().decode()[:800]}")
            return 1
        last = d
        reply = d.get("reply", "")
        actions = d.get("actions", [])
        print(
            f"--- AI skill_active={d.get('skill_active')} "
            f"draft_saved={d.get('draft_saved')} "
            f"skill_saved={d.get('skill_saved')} "
            f"actions={len(actions)} ---"
        )
        print(reply[:2000])
        if actions:
            print("BUTTONS:", [a["label"] for a in actions])

    skill_name = last.get("skill_saved") or last.get("draft_saved")
    print("\n=== DISK CHECK ===")
    if not skill_name:
        print("FAIL: no skill_saved or draft_saved in final response")
        return 1

    disk = check_skill_on_disk(skill_name)
    print(json.dumps({"skill_name": skill_name, **disk}, ensure_ascii=False, indent=2))

    ok = bool(last.get("skill_saved")) and disk.get("exists") and not disk.get("is_draft")
    if ok:
        print("\n=== RESULT: PASS — skill finalized and saved ===")
        return 0

    partial = disk.get("exists") and disk.get("has_body")
    if last.get("skill_saved") or partial:
        print("\n=== RESULT: PARTIAL — saved but check draft/final status ===")
    else:
        print("\n=== RESULT: FAIL — skill not finalized ===")
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(main())
