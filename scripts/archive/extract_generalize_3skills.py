#!/usr/bin/env python3
"""Cold-start extract 3 skills in NEW domains (generalization experiment)."""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if val and key not in os.environ:
            os.environ[key] = val

from skillos.config import get_config
from skillos.skills.agent import SkillExtractionAgent
from skillos.skills.skill_store import list_skills
from skillos.skills.pattern_miner import ensure_bootstrap_skill_dna, check_dna_compliance
from skillos.api.skills import _persist_created_skill, _persist_meta_from_agent

TS = int(time.time())
RUN_ID = f"generalize_{TS}"

# New domains — NOT refund / PR / CSV
SCENARIOS = [
    {
        "name": "财务报销审计助手",
        "expected_domain_template": "finance-expense-audit",
        "session_id": f"{RUN_ID}-finance",
        "turns": [
            "我想做一个财务报销审计的技能，给财务和审批人用",
            "触发：员工在飞书或OA提交差旅、招待、办公类报销单时",
            "先校验发票真伪和抬头，增值税发票要在查验平台核对",
            "对照公司费用标准：差旅酒店每晚上限400元，招待费按部门预算",
            "金额分级审批：5000以下部门负责人，5万到20万财务总监，超过20万总经理",
            "发现超标项比如五星酒店、假发票、重复报销要退回并注明原因",
            "审批通过后生成凭证号，同步ERP，通知申请人",
            "可以了，生成技能文档",
        ],
    },
    {
        "name": "合同法务审核助手",
        "expected_domain_template": "law-contract-review",
        "session_id": f"{RUN_ID}-law",
        "turns": [
            "帮我沉淀一个合同法务审核流程技能",
            "触发：业务部门提交采购、销售、劳动或NDA合同需要法务审核",
            "收稿先检查双方信息、标的、金额、期限是否完整",
            "对照公司合同模板库比对条款，标记偏离项",
            "红线：无限责任、单方随意解约、不利管辖权、免责安全漏洞条款必须修改",
            "合同金额超过100万要法务总监加外部律师双审",
            "输出逐条修改建议和法律依据，通过后走用印归档",
            "够了，生成技能吧",
        ],
    },
    {
        "name": "安全合规审计助手",
        "expected_domain_template": "security-audit",
        "session_id": f"{RUN_ID}-security",
        "turns": [
            "我要一个安全合规审计技能，用于等保和内部基线检查",
            "触发：收到安全审计、合规检查或季度权限审计任务时",
            "先明确审计范围和标准（等保二级/SOC2/内部基线）",
            "收集证据：访问日志、配置快照、漏洞扫描报告、账号权限清单",
            "权限审计要检查 AWS、GitHub、Slack 等系统的最小权限和离职账号",
            "发现高危漏洞或过度授权要分级：critical 24h内整改，high 7天内",
            "输出审计报告：发现项、风险等级、整改建议、复测计划",
            "好了，帮我生成技能",
        ],
    },
]


def extract_one(scenario: dict, llm_args: tuple, existing: list[str]) -> dict:
    name = scenario["name"]
    agent = SkillExtractionAgent()
    agent.set_team_context(session_id=scenario["session_id"])
    print(f"\n{'='*60}\n泛化萃取: {name}\n{'='*60}")

    saved = None
    dna_report = None
    lineage_summary = None
    post_bench = None
    bench_quality = None

    for i, turn in enumerate(scenario["turns"], 1):
        if i == 1:
            agent._lock_skill_name(name, force=True)
            agent.start(turn)
            agent._lock_skill_name(name, force=True)
        print(f"  [{i}/{len(scenario['turns'])}] {turn[:70]}{'…' if len(turn) > 70 else ''}")
        reply, doc = agent.handle(turn, existing, llm_args)
        if doc:
            ep = _persist_created_skill(
                name,
                doc["content"],
                llm_args,
                source=f"session:{scenario['session_id']}",
                source_type="conversation",
                meta=_persist_meta_from_agent(agent),
                team_context={"session_id": scenario["session_id"]},
            )
            saved = name
            lineage_summary = ep.get("dna_lineage") or {}
            post_bench = ep.get("post_bench")
            bench_quality = ep.get("bench_quality")
            skill_path = ROOT / "skills" / saved / "SKILL.md"
            if skill_path.exists():
                dna_report = check_dna_compliance(skill_path.read_text(encoding="utf-8"))
            domain_tpl = getattr(agent, "_domain_template_id", "") or ""
            print(f"  ✓ 已保存: {saved}  DNA={dna_report.get('score') if dna_report else '?'}  模板={domain_tpl}")
            if lineage_summary:
                philo = [p.get("id") for p in lineage_summary.get("philosophical", [])]
                domain = [d.get("id") for d in lineage_summary.get("domain", [])]
                print(f"    lineage: philo={philo} domain={domain}")
            break

    if not saved:
        print("  ⚠ 未生成，尝试强制 finalize…")
        reply, doc = agent.handle("请直接生成最终技能文档并保存", existing, llm_args)
        if doc:
            ep = _persist_created_skill(
                name,
                doc["content"],
                llm_args,
                source=f"session:{scenario['session_id']}-force",
                source_type="conversation",
                meta=_persist_meta_from_agent(agent),
                team_context={"session_id": scenario["session_id"]},
            )
            saved = name
            lineage_summary = ep.get("dna_lineage") or {}
            post_bench = ep.get("post_bench")
            bench_quality = ep.get("bench_quality")

    actual_tpl = getattr(agent, "_domain_template_id", "") if saved else ""
    return {
        "name": name,
        "saved": saved,
        "expected_domain_template": scenario.get("expected_domain_template"),
        "actual_domain_template": actual_tpl,
        "template_match": actual_tpl == scenario.get("expected_domain_template"),
        "dna_compliance": dna_report,
        "dna_lineage": lineage_summary,
        "bench_quality": bench_quality,
        "post_bench": post_bench,
        "error": None if saved else "generation_failed",
    }


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("ERROR: DEEPSEEK_API_KEY required")
        return 1

    os.environ.setdefault("SKILLOS_SKIP_BENCH_REGRESSION", "1")

    cfg = get_config()
    llm_args = cfg.to_llm_args()
    ensure_bootstrap_skill_dna()

    existing = list_skills()
    results = []
    for scenario in SCENARIOS:
        row = extract_one(scenario, llm_args, existing)
        results.append(row)
        if row.get("saved"):
            existing = list_skills()

    out = ROOT / "data" / "benchmarks" / f"generalize_extract_{TS}.json"
    payload = {
        "run_id": RUN_ID,
        "timestamp": TS,
        "experiment": "cold_start_new_domains",
        "domains": [s["expected_domain_template"] for s in SCENARIOS],
        "results": results,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n报告: {out}")
    ok = sum(1 for r in results if r.get("saved"))
    print(f"完成: {ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
