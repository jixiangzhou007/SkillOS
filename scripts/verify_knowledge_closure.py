#!/usr/bin/env python3
"""Verify SD knowledge closure (L1 lineage + L2 PURPOSE + L3 incremental).

Runs offline checks without requiring a live API server.
Exit 0 = all checks passed.
"""

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "verify_knowledge_closure_output.txt"


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def check_imports(fh) -> bool:
    modules = [
        "skillos.knowledge.incremental_store",
        "skillos.knowledge.ingest_pipeline",
        "skillos.knowledge.knowledge_context",
        "skillos.knowledge.lineage",
        "skillos.knowledge.cycle_tasks",
        "skillos.knowledge.ingest_metrics",
    ]
    ok = True
    for mod in modules:
        try:
            __import__(mod)
            log(f"  [OK] import {mod}", fh)
        except Exception as exc:
            log(f"  [FAIL] import {mod}: {exc}", fh)
            ok = False
    return ok


def check_incremental_store(fh) -> bool:
    from skillos.knowledge.incremental_store import IncrementalStore

    with tempfile.TemporaryDirectory() as td:
        store = IncrementalStore(Path(td))
        store.put_file_ingest("a" * 64, {"filename": "x.txt"})
        assert store.get_file_ingest("a" * 64) is not None
        assert store.check_source_changed("https://t", "h1") is False
        assert store.check_source_changed("https://t", "h2") is True
    log("  [OK] IncrementalStore file + source hash", fh)
    return True


def check_lineage_crossref(fh) -> bool:
    from skillos.knowledge.lineage import KnowledgeItem, SourceChunk, build_cross_references

    chunk = SourceChunk(source_url="https://same")
    items = [
        KnowledgeItem(item_id="ki_1", content="alpha beta gamma delta", source_chunk=chunk),
        KnowledgeItem(item_id="ki_2", content="alpha beta epsilon zeta", source_chunk=chunk),
    ]
    edges = build_cross_references(items)
    assert edges == 1
    assert items[0].related_items[0]["relation_type"] == "same_source"
    log("  [OK] 4-signal build_cross_references", fh)
    return True


def check_post_ingest(fh) -> bool:
    with tempfile.TemporaryDirectory() as td:
        lineage_dir = Path(td) / "lineage"
        lineage_dir.mkdir()
        inc_dir = Path(td) / "incremental"
        mock_dd = MagicMock()
        mock_dd.title = "Verify Doc"
        mock_dd.glossary = [{"term": "T", "definition": "D"}]
        mock_dd.patterns = []
        mock_dd.sections = []
        mock_dd.cross_references = []

        with patch("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir), \
             patch("skillos.knowledge.incremental_store.INCREMENTAL_DIR", inc_dir), \
             patch("skillos.knowledge.incremental_store._store", None), \
             patch("skillos.knowledge.lineage.sync_lineage_to_graph", return_value={"synced": False}):
            from skillos.knowledge.ingest_pipeline import post_ingest
            result = post_ingest("x" * 300, "https://verify.test/doc", digest_result=mock_dd)
            assert result.get("lineage_applied") is True
            assert list(lineage_dir.glob("*.json"))
    log("  [OK] post_ingest → lineage persistence", fh)
    return True


def check_purpose_context(fh) -> bool:
    from skillos.knowledge.knowledge_context import get_ingest_context
    ctx = get_ingest_context()
    assert isinstance(ctx, str)
    log("  [OK] get_ingest_context (empty or populated)", fh)
    return True


def check_learn_knowledge(fh) -> bool:
    from skillos.knowledge.extractor import learn_knowledge

    with patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]):
        result = learn_knowledge("x", "https://verify.test/learn")
    assert result["extracted"] == 0
    log("  [OK] learn_knowledge import + empty path", fh)
    return True


def check_full_cycle_entry(fh) -> bool:
    from skillos.knowledge.ingest_pipeline import run_full_knowledge_cycle

    with patch(
        "skillos.knowledge.lineage.full_knowledge_cycle",
        return_value={"session_id": "verify_cycle", "lineage": {"lineage_applied": True}},
    ):
        out = run_full_knowledge_cycle("body", "https://verify.test/cycle", ("k",))
    assert out["session_id"] == "verify_cycle"
    log("  [OK] run_full_knowledge_cycle wrapper", fh)
    return True


def run_pytest_subset(fh) -> bool:
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_incremental_store.py",
        "tests/test_ingest_pipeline.py",
        "tests/test_lineage_crossref.py",
        "tests/test_purpose_injection.py",
        "tests/test_ingest_cache.py",
        "tests/test_incremental_closure.py",
        "tests/test_learn_knowledge_cycle.py",
        "tests/test_cycle_tasks.py",
        "tests/test_p1_knowledge.py",
        "tests/test_p2_metrics.py",
        "tests/test_ingestion_queue.py",
        "tests/test_ingest_dedup.py",
        "-q", "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    fh.write(proc.stdout)
    fh.write(proc.stderr)
    if proc.returncode != 0:
        log(f"  [FAIL] pytest subset exit={proc.returncode}", fh)
        return False
    log("  [OK] pytest knowledge-closure subset", fh)
    return True


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        log("=== SkillOS SD Knowledge Closure Verification ===", fh)
        checks = [
            ("Imports", check_imports),
            ("IncrementalStore", check_incremental_store),
            ("Lineage 4-signal", check_lineage_crossref),
            ("post_ingest", check_post_ingest),
            ("PURPOSE context", check_purpose_context),
            ("learn_knowledge", check_learn_knowledge),
            ("full_knowledge_cycle", check_full_cycle_entry),
            ("pytest subset", run_pytest_subset),
        ]
        failed = 0
        for name, fn in checks:
            log(f"\n--- {name} ---", fh)
            try:
                if not fn(fh):
                    failed += 1
            except Exception as exc:
                log(f"  [FAIL] {name}: {exc}", fh)
                failed += 1
        log(f"\n=== RESULT: {len(checks) - failed}/{len(checks)} passed ===", fh)
        if failed:
            log("FAIL", fh)
            return 1
        log("PASS", fh)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
