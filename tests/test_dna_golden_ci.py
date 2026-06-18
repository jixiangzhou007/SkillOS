"""Phase 5 — DNA golden set CI (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillos.knowledge.dna_golden import (
    GOLDEN_SET_PATH,
    assert_golden_set,
    load_golden_set,
    run_golden_set,
)


class TestGoldenSetManifest:
    def test_manifest_loads(self):
        data = load_golden_set()
        assert data["version"]
        assert len(data["dna_detection"]) >= 3
        assert len(data["domain_templates"]) >= 4
        assert len(data["reference_skills"]) >= 3

    def test_manifest_path_exists(self):
        assert GOLDEN_SET_PATH.exists()


class TestGoldenSetRunner:
    def test_full_golden_passes(self):
        report = assert_golden_set()
        assert report.ok
        assert report.passed >= 10

    def test_report_serializable(self):
        report = run_golden_set()
        blob = json.dumps(report.to_dict())
        assert "pass_rate" in blob


class TestGoldenCiScript:
    def test_script_exit_zero(self):
        import subprocess
        import sys

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "run_dna_golden_ci.py")],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
