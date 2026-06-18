"""Tests for SD-style extraction option parsing."""

from skillos.skills.extraction_helpers import attach_extraction_actions, parse_option_actions


def test_parse_option_actions():
    reply = (
        "假设合同第7条改了仲裁地——你第一步做什么？\n"
        "[选项] 高风险，必须修改 | risk_high\n"
        "[选项] 中风险，建议修改 | risk_mid"
    )
    actions = parse_option_actions(reply)
    assert len(actions) == 2
    assert actions[0]["label"] == "高风险，必须修改"
    assert actions[0]["action"] == "risk_high"


def test_attach_extraction_actions():
    result = attach_extraction_actions({"reply": "[选项] A | a"}, "[选项] A | a")
    assert result["actions"][0]["action"] == "a"
