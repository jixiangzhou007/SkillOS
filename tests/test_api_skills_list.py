"""Tests for _list_skills_impl API helper."""

from skillos.api.skills import SkillResponse, _list_skills_impl


def test_list_skills_impl_returns_list():
    result = _list_skills_impl()
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, SkillResponse)
        assert item.name
