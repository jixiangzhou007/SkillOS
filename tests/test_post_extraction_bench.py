"""Post-extraction repair + regression scheduling."""

from skillos.skills.post_extraction_bench import REFERENCE_SKILLS, after_skill_persist, repair_skill


def test_repair_skill_github_pull():
    from pathlib import Path

    if not Path("skills/GitHub Pull/SKILL.md").exists():
        return
    r = repair_skill("GitHub Pull")
    assert r["skill"] == "GitHub Pull"
    assert "bench_quality" in r
    payload = Path("skills/GitHub Pull/SKILL.md").read_text(encoding="utf-8")
    assert "输入检查" in payload
    assert "validate" in payload.lower()


def test_after_skill_persist_non_reference_skips_regression(monkeypatch):
    called = {"n": 0}

    def fake_bg(name):
        called["n"] += 1

    import skillos.skills.post_extraction_bench as mod

    monkeypatch.setattr(mod, "repair_skill", lambda name, **kw: {"skill": name, "bench_quality": {}})
    monkeypatch.setattr(mod, "_run_regression_background", fake_bg)
    out = after_skill_persist("非参考技能XYZ", run_regression=False)
    assert out.get("regression_scheduled") is False
    assert called["n"] == 0


def test_after_skill_persist_schedules_for_reference(monkeypatch):
    import skillos.skills.post_extraction_bench as mod

    monkeypatch.setattr(mod, "repair_skill", lambda name, **kw: {"skill": name, "bench_quality": {}})
    monkeypatch.setattr(mod, "_regression_enabled", lambda: True)
    scheduled = {}

    def fake_bg(name):
        scheduled["name"] = name

    monkeypatch.setattr(mod, "_run_regression_background", fake_bg)
    out = after_skill_persist("GitHub Pull", run_regression=True, background_regression=True)
    assert out.get("regression_scheduled") is True


def test_reference_skills_set():
    assert "GitHub Pull" in REFERENCE_SKILLS
