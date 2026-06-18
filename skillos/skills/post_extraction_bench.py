"""Repair skill structure and refresh bench_quality after save/extraction."""


import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

from skillos.skills.bench_cohorts import GENERALIZE_SKILLS, REFERENCE_SKILL_NAMES

REFERENCE_SKILLS: frozenset[str] = REFERENCE_SKILL_NAMES
REGRESSION_SKILLS: frozenset[str] = REFERENCE_SKILL_NAMES | frozenset(
    s["name"] for s in GENERALIZE_SKILLS
)


def repair_skill(name: str, *, preserve_moe: bool = True) -> dict[str, Any]:
    """Sanitize body, run structure pipeline, refresh bench_quality on disk."""
    from skillos.skills.bench_quality import build_bench_quality_meta
    from skillos.skills.skill_store import (
        _compose,
        _skill_path,
        load_skill_raw,
        resolve_skills_root,
    )
    from skillos.skills.skill_structure import apply_structure_pipeline

    path = _skill_path(name, root=resolve_skills_root())
    raw = load_skill_raw(name)
    meta = dict(raw.get("meta") or {})
    body = raw.get("body", "")
    domain_tpl = meta.get("domain_template") or meta.get("domain_template_id")
    existing_moe = (meta.get("bench_quality") or {}).get("moe") if preserve_moe else None

    cold_start_meta: dict[str, Any] = {}
    try:
        from skillos.skills.cold_start import maybe_run_cold_start

        gate_hint = (meta.get("bench_quality") or {}).get("save_gate")
        body, cold_start_meta = maybe_run_cold_start(name, body, meta, gate_meta=gate_hint)
    except Exception as exc:
        _log.debug("Cold start in repair skipped for %s: %s", name, exc)

    body, pipe_meta = apply_structure_pipeline(
        name,
        body,
        skill_md_path=path,
        old_body=body,
        domain_template=domain_tpl,
    )
    meta["bench_quality"] = build_bench_quality_meta(
        name,
        body,
        meta=meta,
        moe=existing_moe,
    )
    path.write_text(_compose(meta, body), encoding="utf-8")

    from skillos.skills.pattern_miner import check_dna_compliance

    dna = check_dna_compliance(body)
    out = {
        "skill": name,
        "path": str(path),
        "pipeline": pipe_meta,
        "dna_score": dna.get("score"),
        "bench_quality": meta["bench_quality"],
    }
    if cold_start_meta and not cold_start_meta.get("skipped"):
        out["cold_start"] = cold_start_meta
    return out


def _regression_enabled() -> bool:
    if os.environ.get("SKILLOS_SKIP_BENCH_REGRESSION", "").strip().lower() in ("1", "true", "yes"):
        return False
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def run_regression_sync() -> dict[str, Any]:
    """Run full Quick8 + smoke regression (blocking)."""
    from scripts.run_bench_regression import main as regression_main

    ts = int(time.time())
    code = regression_main()
    root = Path(__file__).resolve().parents[2]
    latest = sorted(
        (root / "data" / "benchmarks").glob("bench_regression_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    payload: dict[str, Any] = {"timestamp": ts, "exit_code": code, "all_pass": code == 0}
    if latest:
        try:
            payload["report"] = json.loads(latest[0].read_text(encoding="utf-8"))
            payload["file"] = latest[0].name
        except Exception:
            pass
    return payload


def _run_regression_background(skill_name: str) -> None:
    try:
        result = run_regression_sync()
        result["trigger_skill"] = skill_name
        out_dir = Path(__file__).resolve().parents[2] / "data" / "benchmarks"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"post_extract_regression_{int(time.time())}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info(
            "Post-extract regression for %s: %s (pass=%s)",
            skill_name,
            out_path.name,
            result.get("all_pass"),
        )
    except Exception as exc:
        _log.warning("Post-extract regression failed for %s: %s", skill_name, exc)


def after_skill_persist(
    name: str,
    *,
    llm_args: tuple = (),
    run_regression: bool | None = None,
    background_regression: bool = True,
) -> dict[str, Any]:
    """Repair skill on disk; optionally schedule regression for reference skills."""
    _ = llm_args
    out: dict[str, Any] = {"skill": name}
    try:
        out["repair"] = repair_skill(name, preserve_moe=True)
    except Exception as exc:
        _log.warning("Post-extract repair failed for %s: %s", name, exc)
        out["repair_error"] = str(exc)
        return out

    if run_regression is None:
        run_regression = name in REGRESSION_SKILLS
    if not run_regression or not _regression_enabled():
        out["regression_scheduled"] = False
        return out

    if background_regression:
        threading.Thread(
            target=_run_regression_background,
            args=(name,),
            daemon=True,
        ).start()
        out["regression_scheduled"] = True
    else:
        out["regression"] = run_regression_sync()
    return out
