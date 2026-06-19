"""Normalize extracted skill_doc into installable SKILL.md for Cursor / Claude Code / Trae."""


import hashlib
import re
from pathlib import Path
from typing import Any

_SPEC_PATH = Path(__file__).parent / "templates" / "PORTABLE_SKILL_SPEC.md"


def load_portable_spec() -> str:
    try:
        return _SPEC_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def tool_slug(name: str, body: str = "") -> str:
    """ASCII slug for tool install paths (Cursor/Claude require kebab-case name)."""
    meta_slug = _extract_meta_line(body, "tool_name")
    if meta_slug and _valid_tool_name(meta_slug):
        return meta_slug[:64]

    ascii_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if len(ascii_slug) >= 3 and re.fullmatch(r"[a-z0-9-]+", ascii_slug):
        return ascii_slug[:64]

    # Keyword-based fallback from S_trigger
    keywords = _parse_trigger_keywords(body)
    if keywords:
        slug = re.sub(r"[^a-z0-9]+", "-", "-".join(keywords[:3]).lower()).strip("-")
        if len(slug) >= 3:
            return slug[:64]

    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"skill-{digest}"


def _valid_tool_name(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", slug))


def _extract_meta_line(body: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.+?)\s*$", body, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def _parse_trigger_keywords(body: str) -> list[str]:
    block = _extract_section(body, "S_trigger")
    if not block:
        return []
    m = re.search(r"keywords?\s*[:：]\s*(.+)", block, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1).split("\n")[0]
    parts = re.split(r"[,，、\s]+", raw)
    out: list[str] = []
    for p in parts:
        p = re.sub(r"[^\w\u4e00-\u9fff-]", "", p.strip())
        if p and p.isascii() and len(p) >= 2:
            out.append(p.lower())
    return out


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^##\s*{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, body, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


_PARAM_HINTS: list[tuple[str, str]] = [
    (r"订单号|order_id|订单编号", "order_id: string — 订单编号"),
    (r"工单|ticket|INC-", "ticket_id: string — 工单/事件编号"),
    (r"PR|pull request|合并请求", "pr_url: string — Pull Request 链接或编号"),
    (r"CSV|csv|表格文件", "file_path: string — 待清洗 CSV 文件路径"),
    (r"邮箱|email", "email: string — 邮箱地址（用于校验或通知）"),
    (r"金额|退款|支付", "amount: number — 金额（原币种）"),
    (r"URL|链接|http", "source_url: string — 来源链接（可选）"),
]


def ensure_skill_params(body: str) -> str:
    """Fill S_params / S_outputs when missing or too thin (P0 completeness)."""
    s_params = _extract_section(body, "S_params")
    inputs_block = _extract_section(body, "Inputs")
    existing = (s_params or inputs_block).strip()
    if existing and len(existing) > 30 and existing.count("[待确认]") <= 1:
        if _extract_section(body, "S_outputs") or _extract_section(body, "Outputs"):
            return body

    found: list[str] = []
    seen: set[str] = set()
    for pattern, line in _PARAM_HINTS:
        if re.search(pattern, body, re.IGNORECASE):
            key = line.split(":")[0].strip()
            if key not in seen:
                seen.add(key)
                found.append(f"- {line}")

    if not found:
        found.append("- user_message: string — 用户请求或对话上下文")
    if _extract_section(body, "S_route") or "Decision routes" in body:
        found.append("- route_intent: string — 用户意图或分支条件（由 S_route 判定）")

    params_lines = "\n".join(found)
    outputs_lines = (
        "- status: enum — 执行结果（success / pending / rejected / escalated）\n"
        "- message: string — 给用户或下游系统的摘要说明\n"
        "- audit_notes: string — 关键操作记录（可选）"
    )

    if s_params and len(s_params.strip()) < 30:
        body = re.sub(
            r"^##\s*S_params\s*\n.*?(?=^##\s|\Z)",
            f"## S_params\n{params_lines}\n\n",
            body,
            count=1,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
    elif not s_params and not inputs_block:
        body = body.rstrip() + f"\n\n## S_params\n{params_lines}\n"

    if not _extract_section(body, "S_outputs") and "Outputs" not in body:
        body = body.rstrip() + f"\n\n## S_outputs\n{outputs_lines}\n"

    return body

def build_description(display_name: str, body: str) -> str:
    """Third-person description for YAML frontmatter (AgentSkills / Cursor)."""
    explicit = _extract_meta_line(body, "tool_description")
    if explicit:
        return explicit[:1024]

    trigger = _extract_section(body, "S_trigger")
    core = _extract_section(body, "核心问题") or _extract_section(body, "Core Problem")
    keywords = _parse_trigger_keywords(body)

    parts: list[str] = []
    if core:
        parts.append(re.sub(r"\s+", " ", core.split("\n")[0].strip()))
    else:
        parts.append(f"Executes the {display_name} workflow step by step.")

    ctx_m = re.search(r"context\s*[:：]\s*(.+)", trigger, re.IGNORECASE | re.DOTALL)
    if ctx_m:
        ctx = re.sub(r"\s+", " ", ctx_m.group(1).split("\n")[0].strip())
        if ctx:
            parts.append(ctx)

    if keywords:
        parts.append(f"Trigger terms: {', '.join(keywords[:8])}.")

    desc = " ".join(parts).strip()
    if len(desc) < 40:
        desc = (
            f"Handles {display_name} workflows with clear step-by-step instructions. "
            f"Use when the user mentions {display_name} or related tasks."
        )
    return desc[:1024]


def _strip_internal_meta(body: str) -> str:
    """Remove tool_name / tool_description lines from body (they live in YAML)."""
    return re.sub(
        r"^tool_(?:name|description)\s*:.+\n?",
        "",
        body,
        flags=re.MULTILINE | re.IGNORECASE,
    ).strip()


def normalize_body(display_name: str, body: str) -> str:
    """Ensure portable sections exist for non-technical users and tool runtimes."""
    body = _strip_internal_meta(body)

    if any(
        marker in body
        for marker in (
            "## When to use", "## 何时使用",
            "## Instructions", "## Decision routes",
        )
    ):
        return body

    trigger = _extract_section(body, "S_trigger")
    s_body = _extract_section(body, "S_body")
    s_route = _extract_section(body, "S_route")
    s_params = _extract_section(body, "S_params")
    s_outputs = _extract_section(body, "S_outputs")
    core = _extract_section(body, "核心问题") or _extract_section(body, "Core Problem")

    title_m = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", body, re.MULTILINE)
    title = display_name
    if title_m:
        title = title_m.group(1).strip()

    sections: list[str] = [f"# {title}"]

    if core:
        sections.append(f"\n## 核心问题\n{core.strip()}")

    when_lines: list[str] = []
    if trigger:
        when_lines.append(trigger.strip())
    if when_lines:
        sections.append("\n## When to use\n" + "\n".join(when_lines))

    if s_body:
        sections.append(
            "\n## Instructions\n"
            "Follow these steps in order. Ask the user if anything is marked [待确认].\n\n"
            + s_body.strip()
        )

    if s_route:
        sections.append(f"\n## Decision routes\n{s_route.strip()}")

    if s_params:
        sections.append(f"\n## Inputs\n{s_params.strip()}")

    if s_outputs:
        sections.append(f"\n## Outputs\n{s_outputs.strip()}")

    # Preserve any extra sections not mapped above
    known = {"技能名称", "核心问题", "Core Problem", "S_trigger", "S_body", "S_route", "S_params", "S_outputs"}
    for m in re.finditer(r"^##\s*(.+?)\s*$", body, re.MULTILINE):
        h = m.group(1).strip()
        if h in known or h in ("When to use", "Instructions", "Decision routes", "Inputs", "Outputs"):
            continue
        sec = _extract_section(body, h)
        if sec:
            sections.append(f"\n## {h}\n{sec.strip()}")

    return "\n".join(sections).strip() + "\n"


def install_paths(slug: str) -> dict[str, str]:
    return {
        "cursor": f"~/.cursor/skills/{slug}/SKILL.md",
        "claude_code": f"~/.claude/skills/{slug}/SKILL.md",
        "trae": f"~/.trae/skills/{slug}/SKILL.md",
    }


def format_install_guide(display_name: str, slug: str, saved_path: str = "") -> str:
    paths = install_paths(slug)
    lines = [
        "\n\n---\n",
        "### 安装到 Cursor / Claude Code / Trae",
        "把下面文件夹里的 `SKILL.md` 复制到对应路径即可使用（无需懂什么是 Skill）：",
        "",
        f"1. **Cursor**：`{paths['cursor']}`",
        f"2. **Claude Code**：`{paths['claude_code']}`",
        f"3. **Trae**：`{paths['trae']}`",
        "",
        f"工具内标识名（name）：`{slug}`",
    ]
    if saved_path:
        lines.append(f"\nSkillOS 已保存：`{saved_path}`")
    lines.append("\n在 SkillOS 技能详情页可点「导出 Zip」一键下载。")
    return "\n".join(lines)


def finalize_portable_skill(display_name: str, body: str) -> dict[str, Any]:
    """Prepare name, slug, description, and normalized body for save + install."""
    slug = tool_slug(display_name, body)
    body = ensure_skill_params(body)
    normalized = normalize_body(display_name, body)
    description = build_description(display_name, body)
    return {
        "name": display_name,
        "slug": slug,
        "description": description,
        "body": normalized,
        "install_paths": install_paths(slug),
    }


def to_agent_skills_format(
    display_name: str,
    body: str,
    *,
    license_name: str = "",
    compatibility: str = "",
    metadata: dict[str, str] | None = None,
) -> str:
    """Wrap a normalized skill body in AgentSkills.io standard YAML frontmatter.

    Produces output compatible with Claude Code, Cursor, Codex CLI, Gemini CLI,
    and all other AgentSkills.io-compliant platforms (30+ as of 2026).
    """
    slug = tool_slug(display_name, body)
    description = build_description(display_name, body)
    normalized = normalize_body(display_name, body)

    meta: dict[str, Any] = {
        "name": slug,
        "description": description,
    }
    if license_name:
        meta["license"] = license_name
    if compatibility:
        meta["compatibility"] = compatibility
    if metadata:
        meta["metadata"] = metadata
    # Always include display_name in metadata for SkillOS compatibility
    if "metadata" not in meta:
        meta["metadata"] = {}
    meta["metadata"]["display_name"] = display_name
    meta["metadata"]["generated_by"] = "SkillOS"
    meta["metadata"]["skillos_slug"] = slug

    import yaml
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{header}\n---\n\n{normalized.lstrip()}"


def standard_skill_dir_structure(slug: str) -> dict[str, str]:
    """Return the standard AgentSkills.io directory structure for a skill.

    Creates the canonical layout:
      {slug}/
      ├── SKILL.md
      ├── scripts/          (empty, ready for user scripts)
      ├── references/       (empty, ready for user docs)
      ├── assets/           (empty, ready for user templates)
      └── .skillos/         (SkillOS private data)
          └── versions/     (version history)
          └── memory.json   (epistemology records)
    """
    return {
        "root": slug,
        "skill_md": f"{slug}/SKILL.md",
        "scripts_dir": f"{slug}/scripts/",
        "references_dir": f"{slug}/references/",
        "assets_dir": f"{slug}/assets/",
        "skillos_dir": f"{slug}/.skillos/",
        "versions_dir": f"{slug}/.skillos/versions/",
    }
