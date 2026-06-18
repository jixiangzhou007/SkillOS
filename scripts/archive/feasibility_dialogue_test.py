#!/usr/bin/env python3
"""Simulate real-user dialogue → skill precipitation → quality evaluation.

Usage:
  python scripts/feasibility_dialogue_test.py              # taobao scenario
  python scripts/feasibility_dialogue_test.py --scenario feishu
  python scripts/feasibility_dialogue_test.py --compare-mcp  # dialogue vs MCP single-shot
"""


import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCENARIOS = {
    "taobao": {
        "label": "淘宝数码店退款流程",
        "opening": "帮我沉淀一下电商客服处理退款的标准流程",
        "turns": [
            "都不太像，我自己说。我们是淘宝小店，主营数码配件，日单量大概200单。",
            (
                "触发场景：买家在旺旺或订单页申请「仅退款」或「退货退款」。"
                "第一步必须核对订单号、实付金额、付款渠道（支付宝/微信），在 ERP 里查发货状态和物流签收时间。"
            ),
            (
                "政策规则：未发货可以秒退；已发货未签收先联系快递拦截；已签收走七天无理由但要检查商品完好。"
                "超过七天一律转主管审批，金额超过500元也要主管审批，并在飞书群里留截图。"
            ),
            (
                "边界情况：买家威胁差评的可以升级但不代表必须全额退；"
                "虚拟商品（下载链接类）发货后不支持退款；"
                "换货不算退款，走另一个工单类型。"
            ),
            (
                "输出物：在 ERP 标记退款原因分类（质量问题/不喜欢/发错货），"
                "退款完成后24小时内发一条旺旺模板消息确认，并同步更新 CRM 备注。"
            ),
        ],
        "facts": ["订单", "ERP", "七天", "主管", "500", "旺旺", "拦截", "签收", "CRM", "虚拟"],
        "drive": ["可以了，按我说的生成", "确认，生成最终版本"],
    },
    "feishu": {
        "label": "飞书报销审批流程",
        "opening": "帮我沉淀一套飞书报销审批的处理流程",
        "turns": [
            "都不太像。我们是50人左右的创业公司，财务用飞书审批，员工报销走「费用报销」模板。",
            (
                "触发：员工在飞书提交报销单，附件必须包含发票 PDF 和付款截图。"
                "第一步核对申请人部门、费用类型（差旅/办公/招待）、金额和发票抬头是否为公司全称。"
            ),
            (
                "规则：500元以下部门负责人审批即可；500到5000元需 CFO 审批；"
                "超过5000元要 CEO 加签。差旅费必须附带行程单，招待费必须写清楚客户名称。"
            ),
            (
                "边界：缺发票的先驳回让员工补材料；"
                "重复报销（同一发票号）系统自动拦截并通知财务；"
                "紧急采购可以先走「预付款」流程，事后补发票。"
            ),
            (
                "输出：审批通过后自动生成付款台账 Excel，同步到用友云，"
                "并在飞书群「财务通知」发一条已打款提醒，含报销单号和金额。"
            ),
        ],
        "facts": ["飞书", "发票", "500", "CFO", "CEO", "差旅", "驳回", "用友", "台账", "预付款"],
        "drive": ["可以了，生成吧", "确认，生成"],
    },
    "codereview": {
        "label": "GitHub PR 代码审查流程",
        "opening": "帮我沉淀一套 GitHub Pull Request 代码审查流程",
        "turns": [
            "都不太像。我们后端团队用 Python + FastAPI，PR 必须链 Jira 工单号，CI 跑 pytest 和 ruff。",
            (
                "触发：开发者在 GitHub 提 PR，target 分支是 main。"
                "审查者第一步看 PR 描述是否写清变更动机、测试方式、是否 breaking change。"
            ),
            (
                "规则：改动超过 500 行必须拆 PR；"
                "涉及数据库 migration 必须双人 approve；"
                "安全相关（auth/权限）必须 @security 组 review。"
            ),
            (
                "边界：CI 红灯不允许 merge，允许 draft PR 先讨论；"
                "hotfix 可走 fast-track，但 merge 后 24h 内补测试；"
                "依赖升级单独 PR，不和其他功能混提。"
            ),
            (
                "输出：merge 后在 Jira 工单评论 PR 链接，"
                "发 Slack #eng-releases 通知版本号，并在 CHANGELOG 对应章节追加条目。"
            ),
        ],
        "facts": ["GitHub", "Pull Request", "Jira", "pytest", "ruff", "main", "security", "Slack", "CHANGELOG", "500"],
        "drive": ["可以了，生成", "确认，生成"],
    },
}

STRUCTURE_CHECKS = ("S_body", "S_trigger", "S_route", "S_params", "核心问题")


def evaluate(body: str, ep: dict, log: list[dict], facts: list[str]) -> dict:
    body_lower = body.lower()
    facts_hit = [f for f in facts if f.lower() in body_lower or f in body]
    structure = {k: (k in body or k.replace("_", " ") in body) for k in STRUCTURE_CHECKS}
    steps = len(re.findall(r"^\d+\.", body, re.MULTILINE))
    has_route_table = "|" in body and ("意图" in body or "Intent" in body or "用户" in body or "条件" in body)
    if has_route_table and "S_route" not in body:
        structure["S_route"] = True
    elif has_route_table:
        structure["S_route"] = True
    hallucination_probes = ["Kubernetes", "Vue.js", "React Native"]
    user_text = " ".join(e.get("content", "") for e in log if e.get("role") == "user")
    hallucinated = [h for h in hallucination_probes if h in body and h not in user_text]
    fidelity = len(facts_hit) / max(len(facts), 1)

    scores = {
        "structure_complete": all(
            structure.get(k) for k in ("S_body", "S_trigger", "S_params", "核心问题", "S_route")
        ),
        "structure_detail": structure,
        "step_count": steps,
        "has_route_table": has_route_table,
        "fact_fidelity": round(fidelity, 2),
        "facts_found": facts_hit,
        "facts_missing": [f for f in facts if f not in facts_hit],
        "hallucination_flags": hallucinated,
        "epistemic_verified": ep.get("verified", 0),
        "epistemic_pending": ep.get("pending", 0),
        "epistemic_total": ep.get("total_claims", 0),
    }
    rubric = 0
    rubric += 1 if scores["structure_complete"] else 0
    rubric += 1 if steps >= 4 else 0
    rubric += 1 if fidelity >= 0.6 else (0.5 if fidelity >= 0.4 else 0)
    rubric += 1 if not hallucinated else 0
    rubric += 1 if ep.get("total_claims", 0) > 0 else 0
    scores["quality_score_1_to_5"] = rubric
    scores["feasible"] = rubric >= 3 and fidelity >= 0.5 and not hallucinated
    return scores


def run_dialogue(scenario: dict) -> dict:
    from skillos.config import get_config
    from skillos.skills.agent import Phase, SkillExtractionAgent
    from skillos.skills import skill_store
    from skillos.api.skills import _persist_created_skill

    cfg = get_config()
    llm_args = cfg.to_llm_args()
    agent = SkillExtractionAgent()
    existing = skill_store.list_skills()
    opening = scenario["opening"]
    user_turns = scenario["turns"]
    drive_msgs = scenario.get("drive", ["确认，生成"])

    log: list[dict] = []
    t0 = time.time()

    reply = agent.start(opening)
    log.append({"role": "assistant", "phase": str(agent._phase), "content": reply[:800]})

    doc = None
    for i, msg in enumerate(user_turns):
        reply, doc = agent.handle(msg, existing, llm_args)
        log.append({"role": "user", "turn": i + 1, "content": msg[:300]})
        log.append({
            "role": "assistant",
            "phase": str(agent._phase),
            "has_doc": doc is not None,
            "content": reply[:1200],
        })
        if doc:
            break

    for j, msg in enumerate(drive_msgs):
        if doc or agent._phase == Phase.DONE:
            break
        reply, doc = agent.handle(msg, existing, llm_args)
        log.append({"role": "user", "turn": f"drive-{j+1}", "content": msg})
        log.append({
            "role": "assistant",
            "phase": str(agent._phase),
            "has_doc": doc is not None,
            "content": reply[:1200],
        })

    elapsed = round(time.time() - t0, 1)
    result = {"log": log, "elapsed_s": elapsed, "doc": doc, "method": "dialogue", "scenario": scenario["label"]}

    if not doc and agent._draft_content:
        doc = {"name": agent._draft_name or "extracted-skill", "content": agent._draft_content}
        result["doc"] = doc
        result["doc_source"] = "draft_fallback"

    if doc:
        team_ctx = {"session_id": "feasibility-test", "channel": "cursor", "chat_id": "test-chat", "user_id": "sim-user"}
        ep = _persist_created_skill(
            doc["name"],
            doc["content"],
            llm_args,
            source="feasibility-dialogue-test",
            source_type="conversation",
            team_context=team_ctx,
        )
        raw = skill_store.load_skill_raw(doc["name"])
        result["skill_name"] = doc["name"]
        result["skill_path"] = raw.get("path")
        result["epistemic"] = ep
        result["body"] = doc["content"]

    return result


def run_mcp_single_shot(scenario: dict) -> dict:
    """Single-shot extraction: concatenate all user knowledge into one blob."""
    from skillos.mcp_extract import run_mcp_extract

    blob = scenario["opening"] + "\n\n" + "\n\n".join(scenario["turns"])
    t0 = time.time()
    r = run_mcp_extract(blob, source_url="feasibility://single-shot", mode="skill")
    elapsed = round(time.time() - t0, 1)
    return {
        "method": "mcp_single_shot",
        "scenario": scenario["label"],
        "elapsed_s": elapsed,
        "ok": r.ok,
        "skill_name": r.name,
        "skill_path": r.skill_path,
        "body": r.content,
        "epistemic": r.epistemic_summary,
        "error": r.error,
        "pipeline_log": r.pipeline_log,
    }


def print_report(out: dict, ev: dict):
    name = out.get("skill_name", "?")
    print(f"\n[OK] 技能: {name} ({out.get('method', 'dialogue')})")
    print(f"   路径: {out.get('skill_path', 'N/A')}")
    ep = out.get("epistemic", {})
    print(f"   耗时: {out.get('elapsed_s')}s")
    print(f"   认识论: 已验证 {ep.get('verified', 0)} | 待确认 {ep.get('pending', 0)} | 共 {ep.get('total_claims', 0)}")
    print(f"   质量 (1-5): {ev['quality_score_1_to_5']}/5 | 事实覆盖 {ev['fact_fidelity']*100:.0f}%")
    print(f"   命中: {', '.join(ev['facts_found'])}")
    if ev["facts_missing"]:
        print(f"   遗漏: {', '.join(ev['facts_missing'])}")
    print(f"   结论: {'可行' if ev['feasible'] else '需改进'}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()) + ["all"], default="taobao")
    parser.add_argument("--compare-mcp", action="store_true", help="Also run MCP single-shot and compare")
    args = parser.parse_args()

    keys = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    report_dir = ROOT / "data" / "feasibility"
    report_dir.mkdir(parents=True, exist_ok=True)
    all_results = []

    print("=" * 60)
    print("SkillOS 可行性验证 — 对话沉淀 vs 单轮抽取")
    print("=" * 60)

    for key in keys:
        scenario = SCENARIOS[key]
        facts = scenario["facts"]
        print(f"\n>>> 场景: {scenario['label']}")

        out = run_dialogue(scenario)
        if not out.get("doc"):
            fail_path = report_dir / f"FAIL_{key}_{int(time.time())}.json"
            fail_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[FAIL] 对话未生成 skill，日志: {fail_path}")
            all_results.append({"scenario": key, "dialogue": out, "dialogue_eval": None})
            continue

        ev_d = evaluate(out["body"], out.get("epistemic", {}), out["log"], facts)
        print_report(out, ev_d)

        mcp_out = None
        ev_m = None
        if args.compare_mcp:
            print(f"\n--- MCP 单轮抽取对比 ---")
            mcp_out = run_mcp_single_shot(scenario)
            if mcp_out.get("ok") and mcp_out.get("body"):
                ev_m = evaluate(mcp_out["body"], mcp_out.get("epistemic", {}), [], facts)
                print_report(mcp_out, ev_m)
                print(f"\n   对比: 对话 {ev_d['quality_score_1_to_5']}/5 vs MCP {ev_m['quality_score_1_to_5']}/5")
                print(f"         事实覆盖 对话 {ev_d['fact_fidelity']*100:.0f}% vs MCP {ev_m['fact_fidelity']*100:.0f}%")
            else:
                print(f"[FAIL] MCP: {mcp_out.get('error')}")

        ts = int(time.time())
        report_path = report_dir / f"{key}_{ts}.json"
        payload = {
            "scenario": scenario["label"],
            "dialogue": {"log": out["log"], "evaluation": ev_d, "epistemic": out.get("epistemic"), "skill_name": out["skill_name"]},
        }
        if mcp_out:
            payload["mcp_single_shot"] = {"result": {k: mcp_out[k] for k in mcp_out if k != "body"}, "evaluation": ev_m, "body_preview": (mcp_out.get("body") or "")[:2000]}
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n报告: {report_path}")
        all_results.append({"scenario": key, "dialogue_eval": ev_d, "mcp_eval": ev_m})

    return 0 if all(r.get("dialogue_eval") and r["dialogue_eval"].get("feasible") for r in all_results if r.get("dialogue_eval")) else 1


if __name__ == "__main__":
    sys.exit(main())
