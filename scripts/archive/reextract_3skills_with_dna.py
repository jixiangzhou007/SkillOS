#!/usr/bin/env python3
"""Re-extract 3 benchmark skills with full DNA pipeline (no HTTP server)."""

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

SCENARIOS = [
    {
        "name": "电商客服退款处理",
        "session_id": f"dna-reextract-refund-{TS}",
        "turns": [
            "我想做一个电商客服退款处理的技能",
            "触发条件是客户在飞书或工单里说退款、退货、要退钱",
            "先查订单号，确认支付状态和是否已发货，未发货直接走极速退款",
            "已发货要先确认收货或拦截物流，超过7天无理由要检查商品完好",
            "金额超过500元或疑似欺诈要转人工复核，不能自动通过",
            "退款成功后同步更新 ERP 和发送短信通知，备注退款原因",
            "如果支付渠道是微信要原路退回，支付宝同理，银行卡走对公打款",
            "没有了，可以生成技能文档",
        ],
    },
    {
        "name": "GitHub Pull",
        "session_id": f"dna-reextract-pr-{TS}",
        "turns": [
            "帮我沉淀一个 GitHub Pull Request 代码审查流程",
            "打开 PR 后先看标题和描述是否说明变更动机，没有就要求作者补充",
            "检查 diff 规模，超过500行建议拆分 PR",
            "重点看安全：SQL 注入、硬编码密钥、未校验的用户输入",
            "看 null/空指针、异常处理、是否有单元测试覆盖新逻辑",
            "风格问题用 suggestion 而不是 request changes，阻塞性问题才 request changes",
            "approve 前确认 CI 全绿，有 breaking change 要标注 migration 说明",
            "够了，生成技能吧",
        ],
    },
    {
        "name": "CSV数据清洗助手",
        "session_id": f"dna-reextract-csv-{TS}",
        "turns": [
            "我要一个 CSV 数据清洗的技能，给运营同学用",
            "输入是销售导出的 CSV，常见问题是重复行、空邮箱、金额格式不对",
            "第一步按主键 id 去重，保留最早一条",
            "email 为空或格式不合法的行单独导出到异常表，不要静默删除",
            "金额列去掉货币符号和逗号，转成 decimal，负数标红",
            "日期统一成 YYYY-MM-DD，无法解析的进异常表",
            "输出清洗报告：总行数、去重数、异常数、各字段填充率",
            "可以了，帮我生成技能",
        ],
    },
]


def extract_one(scenario: dict, llm_args: tuple, existing: list[str]) -> dict:
    name = scenario["name"]
    agent = SkillExtractionAgent()
    agent.set_team_context(session_id=scenario["session_id"])
    print(f"\n{'='*60}\nDNA 萃取: {name}\n{'='*60}")

    saved = None
    dna_report = None
    lineage_summary = None

    for i, turn in enumerate(scenario["turns"], 1):
        if i == 1:
            agent._lock_skill_name(name, force=True)
            agent.start(turn)
            agent._lock_skill_name(name, force=True)
        print(f"  [{i}/{len(scenario['turns'])}] {turn[:70]}{'…' if len(turn) > 70 else ''}")
        reply, doc = agent.handle(turn, existing, llm_args)
        if doc:
            save_name = name
            ep = _persist_created_skill(
                save_name,
                doc["content"],
                llm_args,
                source=f"session:{scenario['session_id']}",
                source_type="conversation",
                meta=_persist_meta_from_agent(agent),
                team_context={"session_id": scenario["session_id"]},
            )
            saved = save_name
            lineage_summary = ep.get("dna_lineage") or {}
            skill_path = ROOT / "skills" / saved / "SKILL.md"
            if skill_path.exists():
                dna_report = check_dna_compliance(skill_path.read_text(encoding="utf-8"))
            print(f"  ✓ 已保存: {saved}  DNA合规={dna_report.get('score') if dna_report else '?'}")
            if lineage_summary:
                philo = [p.get("id") for p in lineage_summary.get("philosophical", [])]
                domain = [d.get("id") for d in lineage_summary.get("domain", [])]
                print(f"    lineage: philo={philo} domain={domain}")
            break

    if not saved:
        print("  ⚠ 未生成文档，尝试强制 finalize…")
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

    return {
        "label": name,
        "saved": saved,
        "domain_template": getattr(agent, "_domain_template_id", ""),
        "dna_compliance": dna_report,
        "dna_lineage": lineage_summary,
        "error": None if saved else "generation_failed",
    }


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("ERROR: DEEPSEEK_API_KEY required in .env")
        return 1

    cfg = get_config()
    llm_args = cfg.to_llm_args()
    ensure_bootstrap_skill_dna()
    print(f"Skill DNA bootstrap: {ROOT / 'skillos/skills/knowledge/skill_dna.json'}")

    existing = list_skills()
    results = []
    for scenario in SCENARIOS:
        row = extract_one(scenario, llm_args, existing)
        results.append(row)
        if row.get("saved"):
            existing = list_skills()

    out = ROOT / "data" / "benchmarks" / f"dna_reextract_3skills_{TS}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": TS, "results": results}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n报告: {out}")
    ok = sum(1 for r in results if r.get("saved"))
    print(f"完成: {ok}/{len(results)} 技能已重新萃取")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
