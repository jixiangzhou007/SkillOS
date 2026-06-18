"""Simulate a normal user creating 3 skills via chat, then run SkillsBench."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = "http://127.0.0.1:8765"
OUT = Path(__file__).resolve().parent / "user_sim_3skills_bench_output.txt"
TS = int(time.time())

SKILL_SCENARIOS = [
    {
        "label": "电商退款处理",
        "session_id": f"user-sim-refund-{TS}",
        "turns": [
            "我想做一个电商客服退款处理的技能",
            "触发条件是客户在飞书或工单里说退款、退货、要退钱",
            "先查订单号，确认支付状态和是否已发货，未发货直接走极速退款",
            "已发货要先确认收货或拦截物流，超过7天无理由要检查商品完好",
            "金额超过500元或疑似欺诈要转人工复核，不能自动通过",
            "退款成功后同步更新 ERP 和发送短信通知，备注退款原因",
            "如果支付渠道是微信要原路退回，支付宝同理，银行卡走对公打款",
            "你还缺什么信息？",
            "没有了，可以生成技能文档",
        ],
    },
    {
        "label": "GitHub PR 审查",
        "session_id": f"user-sim-prreview-{TS}",
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
        "label": "CSV 数据清洗",
        "session_id": f"user-sim-dataclean-{TS}",
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


def log(msg: str, fh) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    fh.write(msg + "\n")
    fh.flush()


def health() -> dict:
    with urllib.request.urlopen(f"{BASE}/health", timeout=10) as r:
        return json.loads(r.read())


def dispatch(msg: str, session_id: str) -> dict:
    body = json.dumps(
        {"message": msg, "session_id": session_id, "mode": "create", "history": []}
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/api/skills/dispatch",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def create_skill(scenario: dict, fh) -> dict:
    log(f"\n{'='*60}\n创建技能: {scenario['label']}\n{'='*60}", fh)
    saved_name = None
    last_reply = ""
    for i, turn in enumerate(scenario["turns"], 1):
        log(f"\n[{i}/{len(scenario['turns'])}] 用户: {turn[:80]}{'…' if len(turn)>80 else ''}", fh)
        try:
            resp = dispatch(turn, scenario["session_id"])
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            log(f"  HTTP {e.code}: {body[:200]}", fh)
            return {"label": scenario["label"], "error": f"HTTP {e.code}", "saved": None}
        except Exception as e:
            log(f"  错误: {e}", fh)
            return {"label": scenario["label"], "error": str(e), "saved": None}

        last_reply = (resp.get("reply") or "")[:300]
        log(f"  助手: {last_reply}{'…' if len(resp.get('reply',''))>300 else ''}", fh)
        if resp.get("skill_saved"):
            saved_name = resp["skill_saved"]
            log(f"  ✓ 技能已保存: {saved_name}", fh)
            if resp.get("quality"):
                q = resp["quality"]
                log(
                    f"  质量: official={q.get('official_score')} grade={q.get('official_grade')} "
                    f"passed={q.get('official_passed')}",
                    fh,
                )
            break
        if resp.get("draft_saved") and not resp.get("skill_active"):
            log(f"  (草稿: {resp.get('draft_saved')})", fh)

    if not saved_name:
        # retry final generation nudge
        log("  未自动保存，尝试最终生成…", fh)
        try:
            resp = dispatch("请现在生成完整技能文档并保存，不要 draft", scenario["session_id"])
            saved_name = resp.get("skill_saved")
            if saved_name:
                log(f"  ✓ 补救保存: {saved_name}", fh)
        except Exception as e:
            log(f"  补救失败: {e}", fh)

    return {
        "label": scenario["label"],
        "session_id": scenario["session_id"],
        "saved": saved_name,
        "last_reply": last_reply,
    }


def run_structural_bench(skill_name: str) -> dict:
    from skillos.skills_bench import SkillBenchScore, SKILLS_DIR

    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"SKILL.md not found for {skill_name}"}
    score = SkillBenchScore.from_skill(skill_md)
    return {
        "skill": score.skill_name,
        "total": score.total,
        "grade": score.grade,
        "correctness": score.correctness,
        "security": score.security,
        "completeness": score.completeness,
        "robustness": score.robustness,
        "details": score.details,
    }


def run_task_bench_compare(skill_name: str) -> dict:
    from skillos.skills_bench import SKILLS_DIR
    from skillos.skillsbench_tasks import compare_with_without

    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"SKILL.md not found for {skill_name}"}
    return compare_with_without(str(skill_md))


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        log("=== 普通用户模拟：创建 3 技能 + SkillsBench ===", fh)
        log(f"时间: {TS}", fh)

        try:
            h = health()
            log(f"Health: {h}", fh)
        except Exception as e:
            log(f"API 不可用: {e}", fh)
            return 1

        created = []
        for scenario in SKILL_SCENARIOS:
            created.append(create_skill(scenario, fh))
            time.sleep(1)

        log(f"\n{'='*60}\nSkillsBench 结构评分 (100分制)\n{'='*60}", fh)
        structural = []
        for item in created:
            name = item.get("saved")
            if not name:
                log(f"\n[{item['label']}] 跳过 — 未保存技能", fh)
                continue
            log(f"\n--- {item['label']} → {name} ---", fh)
            try:
                sb = run_structural_bench(name)
                structural.append(sb)
                log(
                    f"  总分 {sb.get('total')}/100 [{sb.get('grade')}] "
                    f"C={sb.get('correctness')} S={sb.get('security')} "
                    f"Cp={sb.get('completeness')} R={sb.get('robustness')}",
                    fh,
                )
            except Exception as e:
                log(f"  结构评分失败: {e}", fh)

        log(f"\n{'='*60}\nSkillsBench 任务集对比 (with vs without skill)\n{'='*60}", fh)
        task_results = []
        for item in created:
            name = item.get("saved")
            if not name:
                continue
            log(f"\n--- {item['label']} → {name} ---", fh)
            try:
                cmp = run_task_bench_compare(name)
                task_results.append({"label": item["label"], "skill": name, **cmp})
                log(
                    f"  有技能: {cmp.get('with_skill_score')}/{cmp.get('tasks', '?')} tasks [{cmp.get('with_skill_grade')}]",
                    fh,
                )
                log(
                    f"  无技能: {cmp.get('without_skill_score')} [{cmp.get('without_skill_grade')}]",
                    fh,
                )
                log(f"  提升: {cmp.get('delta')} ({cmp.get('improvement_pct')})", fh)
            except Exception as e:
                log(f"  任务集对比失败: {e}", fh)

        summary = {
            "timestamp": TS,
            "created": created,
            "structural_bench": structural,
            "task_bench_compare": task_results,
        }
        summary_path = ROOT / "data" / "benchmarks" / f"user_sim_3skills_{TS}.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"\n完整结果: {summary_path}", fh)
        log(f"日志: {OUT}", fh)

        ok = sum(1 for c in created if c.get("saved"))
        log(f"\n=== 完成: {ok}/3 技能创建成功 ===", fh)
        return 0 if ok >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
