"""Phase A — core loop: system skills, dispatch modes, portable zip export."""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


class TestSystemSkillsOnDisk:
    @pytest.mark.parametrize(
        "name",
        ["brainstorming", "skill-creator", "deep-digest", "cold-start-interview"],
    )
    def test_system_skill_md_exists(self, name: str):
        path = SKILLS_ROOT / name / "SKILL.md"
        assert path.is_file(), f"missing system skill: {path}"
        assert len(path.read_text(encoding="utf-8")) > 100


class TestSystemSkillsHelpers:
    def test_create_mode_injects_skill_creator(self):
        from skillos.skills.system_skills import create_mode_skills

        out = create_mode_skills(["合同审核", "brainstorming"])
        assert "skill-creator" in out
        assert "brainstorming" not in out
        assert "合同审核" in out

    def test_agent_mode_only_brainstorming(self):
        from skillos.skills.system_skills import agent_mode_skills

        assert agent_mode_skills(["合同审核", "skill-creator", "brainstorming"]) == [
            "brainstorming"
        ]


class TestPortableZipExport:
    def test_install_zip_structure(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store
        from skillos.skills.portable_export import build_install_zip

        body = (
            "# 技能名称：测试导出\n## S_body\n1. 步骤一\n\n"
            "## S_trigger\n- keywords: test\n- context: 测试\n"
        )
        skill_store.save_skill("phase-a-export-test", body, meta={"draft": False}, epistemic=False)

        data, filename = build_install_zip("phase-a-export-test")
        assert filename.endswith("-skill.zip")

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            assert any(n.endswith("/SKILL.md") for n in names)
            assert "README.txt" in names
            assert "INSTALL.txt" in names
            skill_md = [n for n in names if n.endswith("SKILL.md")][0]
            content = zf.read(skill_md).decode("utf-8")
            assert content.startswith("---")
            assert "name:" in content
            assert "description:" in content


class TestAgentDispatchMode:
    def test_agent_mode_uses_dispatcher_not_extraction(self):
        from skillos.api.server import app
        from skillos.skills.dispatcher import DispatchResult
        from skillos.skills.session_manager import get_session_manager

        get_session_manager().delete("phase-a-agent")

        mock_result = DispatchResult(reply="头脑风暴回复", skill_used="brainstorming")
        with patch("skillos.skills.dispatcher.dispatch", return_value=mock_result) as mock_dispatch:
            client = TestClient(app)
            resp = client.post(
                "/api/skills/dispatch",
                json={
                    "message": "怎么优化 agent 响应速度",
                    "history": [],
                    "mode": "agent",
                    "session_id": "phase-a-agent",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("mode") == "agent"
        assert "头脑风暴" in data.get("reply", "")
        assert data.get("skill_active") is not True
        mock_dispatch.assert_called_once()
        args = mock_dispatch.call_args
        assert args[0][2] == ["brainstorming"]


class TestCreateModeSkillsList:
    def test_create_dispatch_passes_skill_creator_context(self):
        from skillos.api.skills_extract import _create_mode_skills_list

        with patch("skillos.api.skills_extract._skills_list", return_value=["合同审核"]):
            skills = _create_mode_skills_list(None)
        assert "skill-creator" in skills
        assert "合同审核" in skills
