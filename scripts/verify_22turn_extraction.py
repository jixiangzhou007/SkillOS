"""22+ turn skill extraction verification with quality scoring."""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = "http://127.0.0.1:8765"
SID = f"verify-22turn-{int(time.time())}"
SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"
OUT = Path(__file__).resolve().parent / "verify_22turn_output.txt"

# Topics we inject across turns — used for coverage scoring
EXPECTED_TOPICS = [
    "故障", "咨询", "功能请求", "知识库", "升级", "SLA", "P1",
    "Zendesk", "Confluence", "关单", "备注", "合规", "Jira",
]

TURNS = [
    ("U01", "我想创建一个技术支持工单处理的技能"),
    ("U02", "当客户通过邮件或 Zendesk 工单系统提交问题时触发"),
    ("U03", "第一步识别工单类型：故障、咨询、功能请求三类"),
    ("U04", "故障类先查 Confluence 知识库，30分钟内无方案就升级二线工程师"),
    ("U05", "咨询类先匹配 FAQ，匹配度低于80%就转人工客服"),
    ("U06", "功能请求要记录需求并转产品团队，不计入故障 SLA"),
    ("U07", "SLA：P1 四小时内首次响应，P2 当天，P3 三个工作日内"),
    ("U08", "信息不全时用模板邮件索取日志、截图、产品版本号"),
    ("U09", "关单前必须获得客户确认问题已解决，否则保持 open"),
    ("U10", "严重故障要同步通知客户经理和客户成功团队"),
    ("U11", "工单号格式是 INC- 开头，和 Jira 缺陷单可以双向关联"),
    ("U12", "知识库搜索要按产品线和版本号过滤"),
    ("U13", "升级二线必须附带完整对话、已尝试步骤、环境信息"),
    ("U14", "重复工单合并到母单，保留所有时间线"),
    ("U15", "客户情绪激动时先安抚，暂缓深入技术排查"),
    ("U16", "工单备注固定格式：问题摘要 / 处理步骤 / 结论 / 待办"),
    ("U17", "涉及数据安全或合规的问题走专门通道，禁止口头承诺修复时间"),
    ("U18", "周末只有值班工程师，P1 可以电话联系客户"),
    ("U19", "多语言工单优先用客户使用的语言回复"),
    ("U20", "和研发协作用 Jira 创建 bug，关联原 Zendesk 工单"),
    ("U21", "你还需什么信息？"),
    ("U22", "可以了，生成技能文档吧"),
]


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")
    fh.flush()


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
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def fetch_zip(skill_name: str) -> dict:
    url = f"{BASE}/api/skills/{urllib.request.quote(skill_name)}/export/zip"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        skill_md = next((n for n in names if n.endswith("SKILL.md")), "")
        content = zf.read(skill_md).decode("utf-8") if skill_md else ""
    return {"files": names, "skill_md": content, "size": len(data)}


def evaluate_skill(text: str, skill_name: str) -> dict:
    """Score 0-100 with dimension breakdown (heuristic layer — CI only)."""
    from skillos.evaluation.quality import evaluate_heuristic
    return evaluate_heuristic(text, skill_name, expected_topics=EXPECTED_TOPICS)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        log(f"session_id={SID}", fh)
        log("=== HEALTH ===", fh)
        try:
            h = health()
            log(json.dumps(h, ensure_ascii=False, indent=2), fh)
        except urllib.error.URLError as e:
            log(f"FAIL: server down: {e}", fh)
            return 1

        last: dict = {}
        errors = 0
        save_count = 0
        for tag, msg in TURNS:
            log(f"\n=== {tag} USER ===\n{msg}", fh)
            t0 = time.time()
            try:
                d = dispatch(msg)
            except urllib.error.HTTPError as e:
                log(f"FAIL HTTP {e.code}: {e.read().decode()[:500]}", fh)
                errors += 1
                continue
            except Exception as e:
                log(f"FAIL: {e}", fh)
                errors += 1
                continue
            elapsed = time.time() - t0
            last = d
            if d.get("skill_saved"):
                save_count += 1
            reply = d.get("reply", "")
            log(
                f"--- AI ({elapsed:.1f}s) active={d.get('skill_active')} "
                f"saved={d.get('skill_saved')} draft={d.get('draft_saved')} "
                f"in_session={d.get('draft_in_session')} "
                f"actions={len(d.get('actions', []))} ---",
                fh,
            )
            log(reply[:2500], fh)
            if d.get("actions"):
                log("BUTTONS: " + str([a["label"][:40] for a in d["actions"]]), fh)

        skill_name = last.get("skill_saved") or last.get("draft_saved")
        log("\n=== DISK ===", fh)
        if not skill_name:
            log("FAIL: no skill saved", fh)
            return 1

        path = SKILLS_ROOT / skill_name / "SKILL.md"
        if not path.exists():
            log(f"FAIL: missing {path}", fh)
            return 1

        text = path.read_text(encoding="utf-8")
        log(f"path={path} size={len(text)} draft={'draft: true' in text}", fh)

        log("\n=== ZIP EXPORT ===", fh)
        try:
            z = fetch_zip(skill_name)
            log(f"files={z['files']} zip_skill_md_size={len(z['skill_md'])}", fh)
            has_fm = z["skill_md"].startswith("---") and "description:" in z["skill_md"]
            log(f"portable_frontmatter={'OK' if has_fm else 'MISSING'}", fh)
        except Exception as e:
            log(f"ZIP FAIL: {e}", fh)
            z = {"skill_md": text}

        eval_src = z.get("skill_md") or text
        from skillos.evaluation.quality import evaluate_heuristic, OFFICIAL_LAYER, SCORE_LAYERS
        ev = evaluate_heuristic(eval_src, skill_name, expected_topics=EXPECTED_TOPICS)
        log(f"\n质量口径: official={OFFICIAL_LAYER}, layers={list(SCORE_LAYERS.keys())}", fh)
        log("\n=== QUALITY EVALUATION ===", fh)
        log(json.dumps(ev, ensure_ascii=False, indent=2), fh)
        log(f"\nOVERALL: {ev['total']}/{ev['max']} Grade {ev['grade']}", fh)

        ok = (
            save_count == 1
            and last.get("skill_saved")
            and "draft: true" not in text
            and ev["total"] >= 55
            and errors == 0
        )
        log(f"\nSAVE_COUNT: {save_count} (expect 1)", fh)
        log(f"\n=== RESULT: {'PASS' if ok else 'FAIL'} ===", fh)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
