"""Feishu notification helpers (Sprint 3 — approval cards)."""


import json
import urllib.request


def send_approval_card(
    webhook_url: str,
    *,
    action: str,
    skill_name: str,
    notes: str = "",
) -> bool:
    """Post interactive card to Feishu group webhook (optional)."""
    titles = {
        "submit": "📋 技能待审批",
        "approve": "✅ 技能已发布",
        "reject": "↩️ 技能已驳回",
    }
    title = titles.get(action, "SkillOS 审批")
    text = f"**{skill_name}**"
    if notes:
        text += f"\n备注：{notes}"

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}},
            "elements": [{"tag": "markdown", "content": text}],
        },
    }
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status == 200
