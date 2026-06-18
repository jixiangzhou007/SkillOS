"""Tests for official SkillsBench metrics."""
from skillos.official_skillsbench.metrics import compare_pass_rates


def test_compare_pass_rates():
    base = {"pass_rate_pct": 40.0}
    with_s = {"pass_rate_pct": 56.2}
    c = compare_pass_rates(base, with_s)
    assert c["delta_pp"] == 16.2
    assert c["improvement"] == "+16.2pp"
