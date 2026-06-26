"""Playbook Manager — shared team context for all skills.

Inspired by Claude for Legal's cold-start-interview pattern:
  Before any skill is created, spend 10-15 minutes capturing the team's
  playbook, templates, style preferences, and terminology into a shared
  CLAUDE.md-style file. All subsequent skill extraction and optimization
  reads from this context.

This ensures AI output sounds like YOUR team wrote it — not like a generic template.
"""


import logging
from pathlib import Path

_log = logging.getLogger(__name__)

PLAYBOOK_PATH = Path(__file__).parent.parent.parent / "skills" / ".claude" / "PLAYBOOK.md"
PURPOSE_PATH = Path(__file__).parent.parent.parent / "skills" / ".claude" / "PURPOSE.md"
BINDINGS_PATH = Path(__file__).parent.parent.parent / "data" / "playbook_bindings.json"
PLAYBOOKS_DIR = Path(__file__).parent.parent.parent / "data" / "playbooks"


# ═══════════════════════════════════════════════════════════════
# Load / Save
# ═══════════════════════════════════════════════════════════════

def load_playbook() -> str:
    """Load the team playbook. Returns empty string if not found."""
    if not PLAYBOOK_PATH.exists():
        return ""
    try:
        return PLAYBOOK_PATH.read_text(encoding="utf-8")
    except Exception as e:
        _log.warning("Failed to load playbook: %s", e)
        return ""


def save_playbook(content: str) -> Path:
    """Save or update the team playbook."""
    PLAYBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYBOOK_PATH.write_text(content, encoding="utf-8")
    _log.info("Playbook saved: %s (%d chars)", PLAYBOOK_PATH, len(content))
    return PLAYBOOK_PATH


def has_playbook() -> bool:
    """Check if a playbook has been created."""
    return PLAYBOOK_PATH.exists() and PLAYBOOK_PATH.stat().st_size > 100


# ═══════════════════════════════════════════════════════════════
# chat_id → Playbook bindings (Phase 5)
# ═══════════════════════════════════════════════════════════════

def _load_bindings_doc() -> dict:
    if not BINDINGS_PATH.exists():
        return {"bindings": []}
    try:
        import json
        return json.loads(BINDINGS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning("Failed to load playbook bindings: %s", e)
        return {"bindings": []}


def _save_bindings_doc(doc: dict) -> None:
    import json
    BINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BINDINGS_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def list_playbook_bindings() -> list[dict]:
    """Return all chat_id → playbook file bindings."""
    return list(_load_bindings_doc().get("bindings", []))


def bind_chat_playbook(chat_id: str, playbook_file: str, *, label: str = "") -> dict:
    """Bind a chat/group to a playbook file under ``data/playbooks/``."""
    doc = _load_bindings_doc()
    bindings = doc.setdefault("bindings", [])
    entry = {
        "chat_id": chat_id.strip(),
        "playbook_file": playbook_file.strip(),
        "label": label or chat_id,
    }
    bindings = [b for b in bindings if b.get("chat_id") != entry["chat_id"]]
    bindings.append(entry)
    doc["bindings"] = bindings
    _save_bindings_doc(doc)
    return entry


def resolve_chat_id(chat_id: str = "", session_id: str = "") -> str:
    """Resolve chat_id from explicit value or ``feishu:chat:user`` session."""
    if chat_id.strip():
        return chat_id.strip()
    if session_id.strip():
        try:
            from skillos.channels.session_ids import parse_channel_session
            parsed = parse_channel_session(session_id)
            if parsed:
                return parsed.get("chat_id", "")
        except Exception:
            pass
    return ""


def load_playbook_for_chat(chat_id: str = "", session_id: str = "") -> str:
    """Load playbook content for a chat; fall back to global PLAYBOOK.md."""
    cid = resolve_chat_id(chat_id, session_id)
    if cid:
        for binding in list_playbook_bindings():
            if binding.get("chat_id") == cid:
                rel = binding.get("playbook_file", "")
                if rel:
                    path = PLAYBOOKS_DIR / rel if not Path(rel).is_absolute() else Path(rel)
                    if path.exists():
                        try:
                            return path.read_text(encoding="utf-8")
                        except Exception as e:
                            _log.warning("Failed to load bound playbook %s: %s", path, e)
    return load_playbook()


def has_playbook_for_chat(chat_id: str = "", session_id: str = "") -> bool:
    content = load_playbook_for_chat(chat_id, session_id)
    return len(content.strip()) > 50


# ═══════════════════════════════════════════════════════════════
# PURPOSE.md — the "soul" of the knowledge system (LLM Wiki inspired)
# ═══════════════════════════════════════════════════════════════

def load_purpose() -> str:
    """Load the purpose definition. Returns empty string if not found."""
    if not PURPOSE_PATH.exists():
        return ""
    try:
        return PURPOSE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        _log.warning("Failed to load purpose: %s", e)
        return ""


def save_purpose(content: str) -> Path:
    """Save or update the purpose."""
    PURPOSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PURPOSE_PATH.write_text(content, encoding="utf-8")
    _log.info("Purpose saved: %s (%d chars)", PURPOSE_PATH, len(content))
    return PURPOSE_PATH


def has_purpose() -> bool:
    """Check if a purpose has been defined."""
    return PURPOSE_PATH.exists() and PURPOSE_PATH.stat().st_size > 50


def get_purpose_context() -> str:
    """Get the purpose for injection into LLM prompts (LLM Wiki: read on every ingest/query)."""
    content = load_purpose()
    if not content:
        return ""
    return f"\n## 🎯 知识体系目标 (PURPOSE.md)\n\n{content[:1000]}\n"


# ═══════════════════════════════════════════════════════════════
# Context builders — what to inject into skill extraction prompts
# ═══════════════════════════════════════════════════════════════

def get_playbook_context(max_chars: int = 2000, chat_id: str = "", session_id: str = "") -> str:
    """Get condensed playbook context for LLM prompts (per-chat or global)."""
    content = load_playbook_for_chat(chat_id, session_id)
    if not content:
        return ""

    # If short enough, return full playbook
    if len(content) <= max_chars:
        return f"\n## 🏢 团队 Playbook（共享上下文）\n\n{content}\n"

    # Otherwise extract key sections
    sections = _extract_sections(content)
    condensed = []

    priority_sections = ["团队画像", "文档标准", "风格偏好", "术语表", "工作流"]
    for sec_name in priority_sections:
        if sec_name in sections:
            condensed.append(f"### {sec_name}\n{sections[sec_name][:400]}")

    result = "\n".join(condensed)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n...(truncated)"

    return f"\n## 🏢 团队 Playbook（共享上下文）\n\n{result}\n"


def get_style_guide() -> str:
    """Extract just the style guide from the playbook."""
    sections = _extract_sections(load_playbook())
    return sections.get("风格偏好", "")


def get_glossary() -> dict[str, str]:
    """Extract the term glossary as a dict."""
    sections = _extract_sections(load_playbook())
    glossary_text = sections.get("术语表", "")
    if not glossary_text:
        return {}

    result = {}
    # Parse markdown table or bullet list
    for line in glossary_text.split("\n"):
        line = line.strip()
        # Table format: | term | definition |
        if line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 2 and parts[0] and not parts[0].startswith("-"):
                term = parts[0].strip()
                definition = parts[1].strip()
                if term and definition and term not in ("术语", "Term"):
                    result[term] = definition
        # Bullet format: - term: definition
        elif line.startswith("-") and ":" in line:
            term, _, definition = line[1:].partition(":")
            term = term.strip()
            definition = definition.strip()
            if term and definition:
                result[term] = definition

    return result


def get_document_standards() -> list[str]:
    """Extract document format requirements."""
    sections = _extract_sections(load_playbook())
    standards = sections.get("文档标准", "")
    if not standards:
        return []

    # Extract bullet points
    items = []
    for line in standards.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            items.append(line[1:].strip())
    return items


# ═══════════════════════════════════════════════════════════════
# Playbook check — validate skill output against team standards
# ═══════════════════════════════════════════════════════════════

def check_against_playbook(skill_content: str) -> list[dict]:
    """Check if a generated skill complies with the team playbook.

    Returns a list of compliance checks: [{check, passed, detail}]
    """
    if not has_playbook():
        return [{"check": "playbook_exists", "passed": False,
                 "detail": "No playbook found. Run cold-start interview first."}]

    checks = []

    # Check 1: Terminology consistency
    glossary = get_glossary()
    if glossary:
        used_terms = 0
        for term in glossary:
            if term in skill_content:
                used_terms += 1
        checks.append({
            "check": "terminology_consistency",
            "passed": used_terms > 0,
            "detail": f"{used_terms}/{len(glossary)} playbook terms found in skill" if used_terms > 0
                      else "No playbook terms used — skill may not align with team language",
        })

    # Check 2: Document format alignment
    standards = get_document_standards()
    if standards:
        checks.append({
            "check": "document_standards",
            "passed": True,  # Can't fully auto-check, flag for human
            "detail": f"Team requires: {'; '.join(standards[:3])}",
        })

    # Check 3: Style alignment (heuristic)
    style = get_style_guide()
    if style:
        # Heuristic: check if the skill is in the right language
        checks.append({
            "check": "style_alignment",
            "passed": True,
            "detail": "Style guide loaded — human review recommended for tone matching",
        })

    return checks


def build_playbook_check_prompt() -> str:
    """Build a prompt snippet for the skill generation step that checks playbook compliance."""
    if not has_playbook():
        return ""

    return f"""
## 🏢 团队 Playbook 合规检查

以下是你团队的共享上下文（PLAYBOOK.md）。生成的技能必须符合这些标准。

{get_playbook_context(max_chars=1500)}

### 检查清单
在输出最终技能文档前，逐条对照：
1. ✅ 输出格式是否符合文档标准？
2. ✅ 用语是否匹配风格偏好？
3. ✅ 术语是否使用了团队定义（而非通用定义）？
4. ✅ 是否引用了团队已有的工具和系统？
5. ✅ 命名规范是否一致？

如果某项不符合，请在技能文档中标注 `<!-- PLAYBOOK: 此项待人工确认 -->`。
"""


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _extract_sections(content: str) -> dict[str, str]:
    """Parse a markdown document into ##-headed sections."""
    sections = {}
    current_name = ""
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            if current_name and current_lines:
                sections[current_name] = "\n".join(current_lines).strip()
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_name and current_lines:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections
