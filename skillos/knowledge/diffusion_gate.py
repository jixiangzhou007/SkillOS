"""Epistemic gate for knowledge diffusion (Phase 7).

Blocks or downgrades cross-skill edits when the source skill has unverified
or erroneous claims — prevents Experience-level content from polluting other skills.
"""


from dataclasses import dataclass


@dataclass
class DiffusionGateResult:
    allowed: bool
    auto_apply: bool
    reason: str = ""


def check_diffusion_gate(
    source_skill_name: str,
    source_body: str = "",
) -> DiffusionGateResult:
    """Decide whether diffusion from *source_skill_name* may modify other skills.

    Rules (conservative):
    - ERROR claims in epistemic meta → block entirely
    - pending > 0 and verified == 0 → block auto-apply (suggest only)
    - otherwise → allow auto-apply
    """
    try:
        from skillos.skills.skill_store import load_skill_raw

        raw = load_skill_raw(source_skill_name)
        meta = raw.get("meta") or {}
    except FileNotFoundError:
        if not source_body.strip():
            return DiffusionGateResult(
                allowed=False,
                auto_apply=False,
                reason="源技能不存在",
            )
        meta = {}

    ep = meta.get("epistemic") or {}
    errors = int(ep.get("errors", 0))
    pending = int(ep.get("pending", 0))
    verified = int(ep.get("verified", 0))

    if errors > 0:
        return DiffusionGateResult(
            allowed=False,
            auto_apply=False,
            reason=f"源技能含 {errors} 条 ERROR 声明，禁止扩散",
        )

    if pending > 0 and verified == 0:
        return DiffusionGateResult(
            allowed=True,
            auto_apply=False,
            reason="源技能尚无已验证声明，仅建议不自动改写",
        )

    if pending > verified and verified > 0:
        return DiffusionGateResult(
            allowed=True,
            auto_apply=False,
            reason=f"待确认({pending})多于已验证({verified})，仅建议",
        )

    return DiffusionGateResult(allowed=True, auto_apply=True, reason="")
