"""Official SkillsBench service — plans, exports, latest results (no Docker in-process)."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from skillos.benchmark_local import latest_quick8_for_skill, quick8_history_for_skill
from skillos.official_skillsbench.export import export_skill_for_official, SKILLS_ROOT
from skillos.official_skillsbench.presets import AGENT_COMPARE_PRESETS, DEFAULT_AGENT, DEFAULT_MODEL
from skillos.official_skillsbench.tasks import SMOKE_TASK, suggest_tasks_for_skill

BENCHMARKS_DIR = Path(__file__).resolve().parents[2] / "data" / "benchmarks"


def list_presets() -> list[dict[str, str]]:
    return list(AGENT_COMPARE_PRESETS)


def latest_official_results(limit: int = 5) -> dict[str, list[dict]]:
    """Return recent official_eval / official_compare / official_smoke JSON files."""
    out: dict[str, list[dict]] = {"eval": [], "compare": [], "smoke": []}
    patterns = {
        "eval": "official_eval_*.json",
        "compare": "official_compare_*.json",
        "smoke": "official_smoke_*.json",
    }
    for key, pat in patterns.items():
        files = sorted(BENCHMARKS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_file"] = f.name
                out[key].append(data)
            except Exception:
                out[key].append({"_file": f.name, "error": "parse_failed"})
    return out


def plan_for_skill(skill_name: str) -> dict[str, Any]:
    """Suggest official tasks and CLI commands for a SkillOS skill."""
    skill_md = SKILLS_ROOT / skill_name / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(skill_name)

    tasks = suggest_tasks_for_skill(skill_name)
    matching_presets = [p for p in AGENT_COMPARE_PRESETS if p.get("skill") == skill_name]

    compare_cmd = ""
    if matching_presets:
        compare_cmd = f"python scripts/run_official_skill_compare.py --preset {matching_presets[0]['id']}"
    elif tasks:
        compare_cmd = (
            f'python scripts/run_official_skill_compare.py --task {tasks[0]} --skill "{skill_name}"'
        )

    return {
        "skill": skill_name,
        "suggested_official_tasks": tasks,
        "matching_presets": matching_presets,
        "smoke_task": SMOKE_TASK,
        "default_agent": DEFAULT_AGENT,
        "default_model": DEFAULT_MODEL,
        "commands": {
            "oracle_smoke": f"python scripts/run_official_skillsbench_eval.py --task {SMOKE_TASK} --oracle-only",
            "agent_compare": compare_cmd,
            "full_suite": "python scripts/run_official_skillsbench_suite.py",
        },
        "requirements": ["Linux or GitHub Actions", "Docker", "DEEPSEEK_API_KEY (agent compare)"],
        "windows_note": "Oracle/agent eval fails on native Windows; use CI or WSL2.",
    }


def latest_for_skill(skill_name: str) -> dict[str, Any]:
    """Latest official + local bench artifacts mentioning this skill."""
    local_quick: list[dict] = []
    for pat in ("new3skills_quick8_*.json", "skill_quick8_*.json", "quick8_ci_*.json", "official_compare_*.json", "user_sim_3skills_*.json"):
        for f in sorted(BENCHMARKS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            text = json.dumps(data, ensure_ascii=False)
            if skill_name in text:
                local_quick.append({"file": f.name, "data": data})
            if len(local_quick) >= 3:
                break

    plan = plan_for_skill(skill_name)
    return {
        "skill": skill_name,
        "plan": plan,
        "latest_official": latest_official_results(limit=3),
        "latest_quick8": latest_quick8_for_skill(skill_name),
        "quick8_history": quick8_history_for_skill(skill_name),
        "related_benchmarks": local_quick,
    }


def export_skill_to_dir(skill_name: str, dest: Path | None = None) -> dict[str, Any]:
    """Export a SkillOS skill into BenchFlow --skills-dir layout."""
    skill_md = SKILLS_ROOT / skill_name / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(skill_name)

    root = dest or Path(tempfile.mkdtemp(prefix="skillos-official-export-"))
    skills_dir = root / "skills"
    exported = export_skill_for_official(skill_name, skills_dir)
    return {
        "skill": skill_name,
        "skills_dir": str(skills_dir),
        "exported_path": str(exported),
        "slug": exported.name,
    }


def preset_for_skill(skill_name: str) -> str | None:
    for p in AGENT_COMPARE_PRESETS:
        if p.get("skill") == skill_name:
            return p["id"]
    return None


def trigger_official_ci(
    skill_name: str,
    *,
    preset: str | None = None,
    run_oracle: bool = False,
) -> dict[str, Any]:
    """Fire GitHub repository_dispatch for Official SkillsBench workflow."""
    plan = plan_for_skill(skill_name)
    chosen = preset or preset_for_skill(skill_name)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()

    manual = {
        "workflow": ".github/workflows/official-skillsbench.yml",
        "run_agent_compare": True,
        "compare_preset": chosen or "citation-curated",
        "skill": skill_name,
        "suggested_tasks": plan["suggested_official_tasks"],
    }

    if not token or not repo:
        return {
            "ok": False,
            "skill": skill_name,
            "preset": chosen,
            "reason": "GITHUB_TOKEN or GITHUB_REPOSITORY not configured",
            "manual": manual,
        }

    payload = {
        "event_type": "skill-official-bench",
        "client_payload": {
            "skill": skill_name,
            "preset": chosen or "",
            "run_oracle": run_oracle,
            "run_agent_compare": bool(chosen),
        },
    }
    url = f"https://api.github.com/repos/{repo}/dispatches"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "SkillOS-official-bench",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "ok": resp.status in (204, 200),
                "skill": skill_name,
                "preset": chosen,
                "repository": repo,
                "status": resp.status,
                "manual": manual,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        return {
            "ok": False,
            "skill": skill_name,
            "preset": chosen,
            "reason": f"GitHub API {exc.code}",
            "detail": body,
            "manual": manual,
        }
    except Exception as exc:
        return {
            "ok": False,
            "skill": skill_name,
            "preset": chosen,
            "reason": str(exc),
            "manual": manual,
        }
