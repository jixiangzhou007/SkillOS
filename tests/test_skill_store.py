"""Smoke test for the ported skill_store module."""

import pytest
from skillos.skills.skill_store import save_skill, load_skill, list_skills, delete_skill, skill_exists, get_skill_body


def test_save_and_load():
    name = "__test_skillos_store__"
    body = "# Test\n## S_body\n1. Step one\n## S_trigger\n- keywords: test"
    save_skill(name, body)
    assert skill_exists(name)

    content = load_skill(name)
    assert "Step one" in content

    extracted = get_skill_body(content)
    assert "## S_body" in extracted

    delete_skill(name)
    assert not skill_exists(name)


def test_list_skills():
    skills = list_skills()
    assert isinstance(skills, list)
