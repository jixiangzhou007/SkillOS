"""Discovery layers + invocation policy (harness-inspired)."""

from skillos.skills.discovery import (
    catalog_summary,
    invocation_policy,
    plugin_vs_skill_hint,
    resolve_skill_source,
    source_rank,
)
from skillos.skills.portable_skill import install_paths


def test_source_system_vs_hub_vs_workspace():
    assert resolve_skill_source("brainstorming", {}) == "system"
    assert resolve_skill_source("Foo", {"source_type": "marketplace"}) == "hub"
    assert resolve_skill_source("Foo", {}) == "workspace"
    assert source_rank("system") < source_rank("workspace") < source_rank("hub")


def test_invocation_policy_draft_hidden_from_model():
    d = invocation_policy("draft")
    assert d["model_invocable"] is False
    assert d["user_invocable"] is True
    v = invocation_policy("verified")
    assert v["model_invocable"] is True
    p = invocation_policy("provisional")
    assert p["model_invocable"] is True
    sys_p = invocation_policy("draft", source="system")
    assert sys_p["model_invocable"] is True


def test_catalog_summary_progressive():
    c = catalog_summary(
        name="Demo",
        description="x" * 300,
        trust_tier="draft",
        meta={},
        portable_slug="demo",
    )
    assert len(c["description"]) <= 240
    assert c["model_invocable"] is False
    assert c["source"] == "workspace"
    assert "Skill" in plugin_vs_skill_hint()


def test_install_paths_include_agents_and_dsh():
    paths = install_paths("my-skill")
    assert paths["cursor"].endswith("my-skill/")
    assert paths["agents_project"] == ".agents/skills/my-skill/"
    assert paths["dsh_user"] == "~/.dsh/skills/my-skill/"
    assert paths["dsh_project"] == ".dsh/skills/my-skill/"


def test_skill_response_discovery_fields():
    from skillos.api.skills import SkillResponse

    s = SkillResponse(
        name="x",
        trust_tier="verified",
        source="workspace",
        model_invocable=True,
        user_invocable=True,
    )
    d = s.model_dump()
    assert d["model_invocable"] is True
    assert d["source"] == "workspace"


def test_harness_install_writes_skill_md(tmp_path, monkeypatch):
    import skillos.skills.harness_install as hi

    fake = {
        "display_name": "Local Demo",
        "slug": "local-demo",
        "portable_md": "---\nname: local-demo\n---\n\n# Hi\n",
        "trust_tier": "provisional",
        "catalog": {
            "model_invocable": True,
            "source": "workspace",
            "source_label": "工作区",
        },
    }
    dest = tmp_path / "cursor-skills" / "local-demo"
    monkeypatch.setattr(hi, "build_portable_skill_md", lambda name, tenant=None: fake)
    monkeypatch.setattr(
        hi,
        "resolve_harness_dest",
        lambda target, slug, *, project=False, cwd=None: dest,
    )
    result = hi.install_skill_to_harness("Local Demo", target="cursor")
    assert result["ok"] is True
    assert (dest / "SKILL.md").is_file()
    assert "provisional" in (dest / "SKILLOS_TRUST.txt").read_text(encoding="utf-8")


def test_resolve_harness_dest_rejects_bad_slug():
    import pytest

    from skillos.skills.harness_install import resolve_harness_dest

    with pytest.raises(ValueError):
        resolve_harness_dest("cursor", "../evil")
    with pytest.raises(ValueError):
        resolve_harness_dest("cursor", "evil/../../tmp")
    with pytest.raises(ValueError):
        resolve_harness_dest("nope", "ok-slug")


def test_resolve_harness_dest_stays_under_root(tmp_path):
    from skillos.skills.harness_install import resolve_harness_dest

    dest = resolve_harness_dest("agents", "safe-slug", project=True, cwd=tmp_path)
    assert dest == (tmp_path / ".agents" / "skills" / "safe-slug").resolve()
    assert str(tmp_path.resolve()) in str(dest)


def test_install_zip_includes_trust_and_harness_paths(monkeypatch):
    import io
    import zipfile

    from skillos.skills import portable_export
    from skillos.skills.discovery import catalog_summary
    from skillos.skills.portable_skill import install_paths

    fake = {
        "display_name": "Zip Demo",
        "slug": "zip-demo",
        "description": "demo",
        "portable_md": "---\nname: zip-demo\n---\n\n# Body\n",
        "meta": {"source_type": "marketplace", "trust_tier": "provisional"},
        "trust_tier": "provisional",
        "catalog": catalog_summary(
            name="Zip Demo",
            description="demo",
            trust_tier="provisional",
            meta={"source_type": "marketplace"},
            portable_slug="zip-demo",
        ),
        "paths": install_paths("zip-demo"),
    }
    monkeypatch.setattr(portable_export, "build_portable_skill_md", lambda name, tenant=None: fake)
    data, filename = portable_export.build_install_zip("Zip Demo")
    assert filename == "zip-demo-skill.zip"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert "zip-demo/SKILL.md" in names
        assert "INSTALL.txt" in names
        assert "TRUST.txt" in names
        install = zf.read("INSTALL.txt").decode("utf-8")
        assert ".dsh/skills" in install
        assert "npx @deepseek-ai/dsh web" in install
        trust = zf.read("TRUST.txt").decode("utf-8")
        assert "Trust Tier" in trust
        assert "model_invocable" in trust
        assert fake["catalog"]["source"] == "hub"
