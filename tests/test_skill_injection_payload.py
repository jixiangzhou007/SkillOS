"""Skill injection payload for bench eval."""

from skillos.knowledge.skill_routing import skill_body_from_file, skill_injection_payload


def test_injection_payload_strips_frontmatter():
    raw = "---\nname: x\ndna_lineage:\n  philosophical: []\n" + "x: 1\n" * 200 + "---\n\n## S_body\nN+1 select_related\n"
    payload = skill_injection_payload(raw)
    assert "dna_lineage" not in payload
    assert "N+1" in payload


def test_body_from_file():
    raw = "---\na: 1\n---\n\n# Title\n"
    assert skill_body_from_file(raw).startswith("# Title")
