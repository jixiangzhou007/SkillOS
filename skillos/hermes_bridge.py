"""Hermes Agent Integration Layer.

SkillOS ↔ Hermes interoperability:
  - Skill format: SkillOS skills exported as agentskills.io format (Hermes-native)
  - Execution: Hermes runs skills, SkillOS collects traces for evolution
  - Memory: Shared knowledge base between Hermes (FTS5) and SkillOS (ChromaDB)
  - Marketplace: SkillOS Hub skills installable into Hermes

Requires Hermes Agent to be installed alongside SkillOS.
All imports are guarded — SkillOS works without Hermes (degraded mode).
"""

import logging
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

HERMES_INSTALLED = False
HERMES_SKILLS_DIR: Optional[Path] = None

try:
    # Hermes stores skills in ~/.hermes/skills/
    hermes_home = Path.home() / ".hermes"
    if hermes_home.exists():
        HERMES_SKILLS_DIR = hermes_home / "skills"
        HERMES_INSTALLED = HERMES_SKILLS_DIR.exists()
except Exception:
    pass


def is_hermes_available() -> bool:
    """Check if Hermes Agent is installed."""
    return HERMES_INSTALLED


# ═══════════════════════════════════════════════════════════════
# Compatibility Check & Update Lock
# ═══════════════════════════════════════════════════════════════

# Known-compatible Hermes version range: [MIN, MAX]
# SkillOS was built and tested against this range.
# Outside this range → warn but don't crash (interfaces are stable).
HERMES_MIN_VERSION = (0, 15, 0)   # First version with MCP add support
HERMES_MAX_VERSION = (0, 18, 0)   # Upper bound — warn above this

# Update lock file: records the last verified-compatible Hermes version.
# Stored in SkillOS data dir, NOT in Hermes directory.
LOCK_PATH = Path(__file__).parent.parent / "data" / ".hermes_compat_lock"


def _parse_hermes_version() -> tuple[int, int, int] | None:
    """Get installed Hermes version as (major, minor, patch)."""
    try:
        import subprocess, re
        out = subprocess.run(
            ["hermes", "version"], capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", out.stdout)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Try pip
        out2 = subprocess.run(
            ["pip", "show", "hermes-agent"], capture_output=True, text=True, timeout=10
        )
        m2 = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", out2.stdout)
        if m2:
            return int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
    except Exception:
        pass
    return None


def check_compatibility() -> dict:
    """Check Hermes compatibility. Returns {compatible, hermes_version, warnings, lock_updated}.

    Call this at startup. It:
      1. Detects installed Hermes version
      2. Checks against known-compatible range
      3. Updates the lock file if version changed
      4. Returns warnings if outside tested range (but does NOT crash)

    SkillOS interfaces with Hermes through PUBLIC APIs only:
      - ~/.hermes/skills/ directory
      - MCP stdio protocol
      - config.yaml
      - 'hermes mcp' CLI subcommand

    These are stable across versions. Version mismatch is a warning, not an error.
    """
    import json

    result = {
        "compatible": True,
        "hermes_installed": HERMES_INSTALLED,
        "hermes_version": None,
        "warnings": [],
        "lock_updated": False,
    }

    if not HERMES_INSTALLED:
        result["compatible"] = True  # SkillOS works without Hermes
        result["warnings"].append("Hermes not installed — bridge disabled, SkillOS runs standalone")
        return result

    version = _parse_hermes_version()
    result["hermes_version"] = f"{version[0]}.{version[1]}.{version[2]}" if version else "unknown"

    if not version:
        result["warnings"].append("Cannot determine Hermes version — continuing with degraded check")
        return result

    major, minor, patch = version
    ver_tuple = (major, minor, patch)

    # Check range
    if ver_tuple < HERMES_MIN_VERSION:
        result["compatible"] = False
        result["warnings"].append(
            f"Hermes {major}.{minor}.{patch} is below minimum ({HERMES_MIN_VERSION[0]}.{HERMES_MIN_VERSION[1]}). "
            f"SkillOS MCP integration may not work. Upgrade: pip install --upgrade hermes-agent"
        )
    elif ver_tuple >= HERMES_MAX_VERSION:
        result["compatible"] = True  # Still assume compatible
        result["warnings"].append(
            f"Hermes {major}.{minor}.{patch} is above tested range (<{HERMES_MAX_VERSION[0]}.{HERMES_MAX_VERSION[1]}). "
            f"SkillOS should still work (public APIs are stable), but hasn't been tested yet. "
            f"Report any issues."
        )
    else:
        result["compatible"] = True

    # Update lock file
    lock_data = {
        "hermes_version": f"{major}.{minor}.{patch}",
        "skillos_version": "0.1.0",
        "last_checked": __import__('time').time(),
        "compatible": result["compatible"],
    }

    # Only write if version changed (avoids unnecessary disk writes)
    if LOCK_PATH.exists():
        try:
            old = json.loads(LOCK_PATH.read_text())
            if old.get("hermes_version") == lock_data["hermes_version"]:
                return result  # No change, skip write
        except Exception:
            pass

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(json.dumps(lock_data, indent=2))
    result["lock_updated"] = True
    return result


def get_lock_info() -> dict | None:
    """Read the compatibility lock file."""
    if not LOCK_PATH.exists():
        return None
    try:
        import json
        return json.loads(LOCK_PATH.read_text())
    except Exception:
        return None


def detect_hermes() -> dict:
    """Detect Hermes installation and capabilities."""
    info = {
        "installed": HERMES_INSTALLED,
        "home": str(hermes_home) if HERMES_INSTALLED else None,
        "skills_count": len(list(HERMES_SKILLS_DIR.glob("*/SKILL.md"))) if HERMES_SKILLS_DIR and HERMES_SKILLS_DIR.exists() else 0,
        "skills_dir": str(HERMES_SKILLS_DIR) if HERMES_SKILLS_DIR and HERMES_SKILLS_DIR.exists() else None,
    }
    return info


# ═══════════════════════════════════════════════════════════════
# Skill format conversion: SkillOS ↔ Hermes (agentskills.io)
# ═══════════════════════════════════════════════════════════════

def skillos_to_hermes(skill_name: str, skill_content: str) -> str:
    """Convert a SkillOS skill to Hermes's agentskills.io format.

    SkillOS format:
      ---
      name: <name>
      ---
      # Skill Name
      ## S_trigger ...
      ## S_route ...
      ## S_body ...

    Hermes format:
      ---
      name: <name>
      description: |
        ...
      ---
      # Skill Name
      ## Instructions
      ...
    """
    import re

    # Extract metadata
    trigger = ""
    body = ""
    description = ""

    # Parse existing sections
    trigger_match = re.search(r'##\s*S_trigger\s*\n(.*?)(?=\n##|\Z)', skill_content, re.DOTALL)
    body_match = re.search(r'##\s*S_body\s*\n(.*?)(?=\n##|\Z)', skill_content, re.DOTALL)

    if trigger_match:
        trigger = trigger_match.group(1).strip()
    if body_match:
        body = body_match.group(1).strip()

    if trigger:
        description = trigger[:500]
    elif body:
        description = body[:200]

    # Build Hermes-compatible frontmatter
    lines = ["---", f"name: {skill_name}"]
    if description:
        lines.append(f"description: |")
        for desc_line in description.split("\n")[:5]:
            lines.append(f"  {desc_line.strip()}")
    lines.extend(["---", "", f"# {skill_name}", ""])

    if body:
        lines.append("## Instructions")
        lines.append(body)

    return "\n".join(lines)


def install_to_hermes(skill_name: str, skill_content: str) -> bool:
    """Install a SkillOS skill into Hermes's skills directory."""
    if not HERMES_INSTALLED or not HERMES_SKILLS_DIR:
        _log.warning("Hermes not available — skill not installed")
        return False

    hermes_content = skillos_to_hermes(skill_name, skill_content)

    safe_name = skill_name.replace(" ", "-").lower()[:50]
    skill_dir = HERMES_SKILLS_DIR / safe_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(hermes_content, encoding="utf-8")

    _log.info("Installed %s to Hermes at %s", skill_name, skill_dir)
    return True


def import_from_hermes(skill_name: str) -> Optional[str]:
    """Import a skill from Hermes into SkillOS format."""
    if not HERMES_INSTALLED or not HERMES_SKILLS_DIR:
        return None

    hermes_skill = HERMES_SKILLS_DIR / skill_name / "SKILL.md"
    if not hermes_skill.exists():
        return None

    # Hermes format is already Markdown — convert to SkillOS sections
    content = hermes_skill.read_text(encoding="utf-8")

    # Add S_route and S_params if missing
    if "## S_route" not in content:
        route_section = "\n\n## S_route\n| Intent | Action | Resource |\n|--------|--------|----------|\n| Default | Execute | references/guide.md |"
        content += route_section

    if "## S_params" not in content:
        content += "\n\n## S_params\n- model: auto\n- output_format: markdown"

    return content
