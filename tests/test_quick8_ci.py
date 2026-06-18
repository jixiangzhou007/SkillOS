"""Quick8 CI script helpers (no LLM)."""

import importlib.util
from pathlib import Path


def _load_ci_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_quick8_ci.py"
    spec = importlib.util.spec_from_file_location("run_quick8_ci", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_parse_pct():
    mod = _load_ci_module()
    assert mod._parse_pct("+17.4%") == 17.4
    assert mod._parse_pct("-5.0%") == -5.0
