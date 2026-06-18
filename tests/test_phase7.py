"""Phase 7 — SkillOpt export + diffusion epistemic gate."""

from unittest.mock import patch

import pytest


class TestSkillOptExport:
    def test_export_creates_best_skill(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store
        from skillos.evolution.skillopt_export import export_for_skillopt

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        name = "phase7-export-test"
        body = "# Skill Name: phase7-export-test\n## S_body\n1. 导出测试步骤必须完整可执行"
        skill_store.save_skill(name, body, epistemic=False)

        result = export_for_skillopt(name, output_dir=tmp_path / "exports")
        assert result.best_skill_path.exists()
        assert result.skill_path.exists()
        assert result.manifest_path.exists()
        text = result.best_skill_path.read_text(encoding="utf-8")
        assert "phase7-export-test" in text
        manifest = result.manifest_path.read_text(encoding="utf-8")
        assert "skillos.export_for_skillopt" in manifest


class TestDiffusionGate:
    def test_blocks_when_no_verified(self, tmp_path, monkeypatch):
        from skillos.knowledge.diffusion_gate import check_diffusion_gate
        from skillos.skills import skill_store

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        name = "gate-pending-only"
        meta = {
            "epistemic": {
                "verified": 0,
                "pending": 3,
                "total_claims": 3,
                "errors": 0,
            }
        }
        skill_store.save_skill(name, "## S_body\n1. 待验证步骤", meta=meta, epistemic=False)

        gate = check_diffusion_gate(name)
        assert gate.allowed is True
        assert gate.auto_apply is False

    def test_blocks_on_errors(self, tmp_path, monkeypatch):
        from skillos.knowledge.diffusion_gate import check_diffusion_gate
        from skillos.skills import skill_store

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        name = "gate-error"
        meta = {"epistemic": {"verified": 1, "pending": 0, "errors": 2}}
        skill_store.save_skill(name, "## S_body\n1. x", meta=meta, epistemic=False)

        gate = check_diffusion_gate(name)
        assert gate.allowed is False

    def test_agent_diffusion_respects_gate(self, tmp_path, monkeypatch):
        from skillos.skills.agent import SkillExtractionAgent
        from skillos.skills import skill_store

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        skill_store.save_skill(
            "target-skill",
            "## S_body\n1. 已有步骤",
            epistemic=False,
        )
        skill_store.save_skill(
            "gate-pending-only",
            "## S_body\n1. 新步骤待验证",
            meta={"epistemic": {"verified": 0, "pending": 2, "errors": 0}},
            epistemic=False,
        )
        agent = SkillExtractionAgent()
        with patch("skillos.llm_client.call", return_value="相关度: 高\n可改进: 是\n具体改什么: 补充边界检查"):
            results = agent._diffuse_knowledge(
                "gate-pending-only",
                "## S_body\n1. 新步骤",
                ["target-skill"],
                ("k", "http://x", "m", {}),
            )
        assert any("建议" in r and "未自动应用" in r for r in results)


class TestMcpExportTool:
    def test_mcp_export_for_skillopt(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store
        from skillos.mcp_server import export_for_skillopt

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        skill_store.save_skill("mcp-export", "## S_body\n1. test", epistemic=False)

        with patch("skillos.evolution.skillopt_export.DEFAULT_EXPORT_ROOT", tmp_path / "exp"):
            out = export_for_skillopt("mcp-export")
        assert "Exported: mcp-export" in out
        assert "best_skill.md" in out
