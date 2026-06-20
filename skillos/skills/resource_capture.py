"""Resource capture — populate AgentSkills.io standard directories from dialogue.

Extracts scripts, references, and assets from user messages during the
Socratic skill extraction dialogue and writes them to the appropriate
standard subdirectories (scripts/, references/, assets/).

All writes are fire-and-forget: failures are logged but never block the dialogue.
"""

import logging
import re
from pathlib import Path

_log = logging.getLogger(__name__)

# Minimum content length to be worth saving as a resource
_MIN_CONTENT_LENGTH = 30

# Patterns that signal a script mention
_SCRIPT_SIGNALS = [
    r"(?:我|我们)(?:平时|经常|会|一般)?(?:用|跑|执行|调用).{0,10}(?:脚本|script|程序|工具|命令)",
    r"(?:python|bash|shell|curl|wget|node|npm|pip)\s+",
    r"```(?:python|bash|shell|sql|javascript|js)\s",
    r"(?:脚本|命令|工具)是[：:]",
    r"\.(?:py|sh|bash|sql|js|ts)\b",
]

# Patterns that signal the user is sharing a template or structured output
_ASSET_SIGNALS = [
    r"(?:模板|模版|template)\s*(?:如下|是[：:]|：)",
    r"(?:话术|回复语|应答|文案)\s*(?:如下|是[：:]|：)",
    r"(?:格式|format)\s*(?:如下|是[：:]|：|固定)",
    r"(?:邮件|短信|通知)\s*(?:模板|内容|正文)[：:]",
    r"(?:检查清单|checklist|check.?list)[：:]",
    r"亲爱的\{.*?\}",
    r"(?:你好|亲爱的)\s*(?:客户|用户|先生|女士)",
    r"\{\{.*?\}\}",
    r"(?:报告|记录|报表|表格|登记表).{0,5}(?:格式|样式|模板|固定)",
    r"(?:固定|统一|标准).{0,5}(?:格式|模板|样式|报告)",
    r"App.{0,5}(?:拍照|上传|生成|自动).{0,5}(?:报告|记录|报表)",  # App自动生成报告
]

# Patterns that signal the user is describing a rule, policy, or reference
_REFERENCE_SIGNALS = [
    r"(?:我们|公司|团队)(?:的|规定|政策|流程|标准|规范)(?:是|：)",
    r"(?:根据|按照|参考).{0,10}(?:政策|规定|法规|标准|文件)",
    r"(?:退款|审批|报销|审核)(?:政策|规则|标准|流程)[：:]",
    r"(?:金额|超过|大于|小于|不低于).{0,10}(?:元|块|万).{0,10}(?:需要|必须|应该|自动)",
    r"https?://[^\s]{5,}",
    r"(?:参见|详见|参考|查阅).{0,5}(?:文档|手册|指南|链接)",
    # Simple substring patterns for Chinese text (more reliable than complex regex)
    r"有本.{0,5}(?:手册|指南|规范|标准|文档|文件|资料)",
    r"(?:手册|指南|规范|标准).{0,5}(?:里|里面|上|中).{0,5}(?:写|规定|列|要求|说明)",
    r"(?:法定|法律|法规|国标|行标|ISO|GB|JGJ).{0,10}(?:要求|规定|标准|规范|必须)",
    r"(?:证|操作证|资格证|许可证|执照).{0,10}(?:上岗|要求|必须|需要|复审|有效|持有)",
    r"(?:归档|保存|留存|备案).{0,10}(?:年|月|天|日)",
    r"(?:第三方|有资质).{0,10}(?:检测|审计|审核|检查|评估|认证)",
    r"(?:安全生产法|消防法|环保法|劳动法|合同法|建筑法|食品安全法).{0,10}(?:规定|要求|必须)",
    r"(?:法条|条款|条例|法规).{0,10}(?:规定|要求|必须|明确|说明)",
]


def classify_resource_type(text: str) -> str | None:
    """Identify the resource type hinted at in a user message.

    Returns:
        'script' | 'reference' | 'asset' | None
    """
    if not text or len(text.strip()) < 10:
        return None

    # Check for embedded code blocks first (strongest script signal)
    if re.search(r"```(?:python|bash|shell|sql|javascript|js|sh)\s", text):
        return "script"

    # Check for template/boilerplate markers (strongest asset signal)
    if re.search(r"(?:亲爱的|尊敬的)\{", text) or re.search(r"\{\{.*?\}\}", text):
        return "asset"

    # Score-based classification for ambiguous cases
    script_score = sum(1 for p in _SCRIPT_SIGNALS if re.search(p, text, re.IGNORECASE))
    asset_score = sum(1 for p in _ASSET_SIGNALS if re.search(p, text, re.IGNORECASE))
    ref_score = sum(1 for p in _REFERENCE_SIGNALS if re.search(p, text, re.IGNORECASE))

    if script_score > max(asset_score, ref_score):
        return "script"
    if asset_score > max(script_score, ref_score):
        return "asset"
    if ref_score > 0:
        return "reference"

    return None


def extract_script(text: str, skill_dir: Path, *, filename: str = "") -> Path | None:
    """Extract executable script content and save to {skill_dir}/scripts/.

    Handles:
    - Inline code blocks (```python ... ```)
    - Descriptions without code (generates skeleton)
    - Command-line invocations (curl, python -c, etc.)

    Returns the path to the saved file, or None if nothing was extracted.
    """
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Strategy 1: Extract code blocks
    code_blocks = re.findall(
        r"```(?:python|bash|shell|sql|javascript|js|sh)?\s*\n(.*?)```",
        text, re.DOTALL | re.IGNORECASE,
    )
    if code_blocks:
        for i, block in enumerate(code_blocks):
            block = block.strip()
            if len(block) < 20:
                continue
            fname = filename or _generate_filename(text, "script", i, ".py")
            fpath = scripts_dir / fname
            fpath.write_text(block + "\n", encoding="utf-8")
            _log.info("Saved script: %s (%d chars)", fpath.name, len(block))
            return fpath

    # Strategy 2: Extract command-line invocation
    cmd_match = re.search(
        r"(?:python|bash|curl|wget|node)\s+[^\n]{10,200}",
        text, re.IGNORECASE,
    )
    if cmd_match:
        cmd = cmd_match.group(0).strip()
        fname = filename or _generate_filename(text, "command", 0, ".sh")
        fpath = scripts_dir / fname
        fpath.write_text(f"#!/bin/bash\n# Auto-generated from SkillOS dialogue\n{cmd}\n", encoding="utf-8")
        _log.info("Saved command: %s", fpath.name)
        return fpath

    # Strategy 3: Script mentioned but no code — generate skeleton
    if re.search(r"(?:脚本|script|工具|tool)\b.{0,30}(?:是|叫|用)", text, re.IGNORECASE):
        fname = filename or _generate_filename(text, "skeleton", 0, ".py")
        fpath = scripts_dir / fname
        desc = _extract_script_description(text)
        fpath.write_text(
            f"# [待补充] {desc}\n"
            f"# 用户描述了此脚本但未提供代码。\n"
            f"# 请在下方填入实际脚本内容。\n\n",
            encoding="utf-8",
        )
        _log.info("Saved skeleton: %s", fpath.name)
        return fpath

    return None


def extract_reference(text: str, skill_dir: Path, *, source_url: str = "", filename: str = "") -> Path | None:
    """Extract reference material and save to {skill_dir}/references/.

    Captures:
    - Policy statements (>200 chars)
    - Decision rules (amount thresholds, condition-action pairs)
    - Procedural descriptions

    Returns the path to the saved file, or None.
    """
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Strip conversational framing to extract the core reference content
    content = _strip_conversation_framing(text)
    if not content or len(content) < _MIN_CONTENT_LENGTH:
        return None

    # Detect reference type for better filename
    if re.search(r"(?:政策|规定|规则|policy)", content):
        fname = filename or "policy.md"
    elif re.search(r"(?:流程|步骤|procedure|workflow)", content):
        fname = filename or "procedure.md"
    elif re.search(r"(?:API|接口|endpoint)", content) or source_url:
        fname = filename or "api_reference.md"
    else:
        fname = filename or "REFERENCE.md"

    # Append source URL if provided
    header = f"# {fname.replace('.md', '').replace('_', ' ').title()}\n\n"
    if source_url:
        header += f"**来源**: {source_url}\n\n"
    header += "*从 SkillOS 对话中自动提取*\n\n"

    fpath = refs_dir / fname
    fpath.write_text(header + content + "\n", encoding="utf-8")
    _log.info("Saved reference: %s (%d chars)", fpath.name, len(content))
    return fpath


def extract_asset(text: str, skill_dir: Path, *, filename: str = "") -> Path | None:
    """Extract templates, boilerplate, and structured outputs to {skill_dir}/assets/.

    Captures:
    - Email/notification templates
    - Response scripts
    - Configuration samples
    - Checklists

    Returns the path to the saved file, or None.
    """
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Strip framing and extract the core asset content
    content = _strip_conversation_framing(text)
    if not content or len(content) < 30:
        return None

    # Detect asset type
    if re.search(r"(?:邮件|email|通知|短信)", content):
        fname = filename or "email_template.txt"
    elif re.search(r"(?:话术|回复|应答|response)", content):
        fname = filename or "response_script.md"
    elif re.search(r"(?:检查清单|checklist)", content):
        fname = filename or "checklist.md"
    elif re.search(r"(?:配置|config|\.json|\.yaml|\.toml)", content):
        fname = filename or "config_sample.txt"
    else:
        fname = filename or "asset.txt"

    header = f"# {fname.replace('.txt', '').replace('.md', '').replace('_', ' ').title()}\n"
    header += "*从 SkillOS 对话中自动提取*\n\n"

    fpath = assets_dir / fname
    fpath.write_text(header + content + "\n", encoding="utf-8")
    _log.info("Saved asset: %s (%d chars)", fpath.name, len(content))
    return fpath


def capture_all_resources(text: str, skill_dir: Path, *, source_url: str = "") -> list[Path]:
    """Classify and capture all resource types from a message.

    Convenience function that runs classification + extraction in one call.
    Returns list of saved file paths.
    """
    saved: list[Path] = []

    rtype = classify_resource_type(text)
    if not rtype:
        return saved

    if rtype == "script":
        result = extract_script(text, skill_dir)
    elif rtype == "reference":
        result = extract_reference(text, skill_dir, source_url=source_url)
    elif rtype == "asset":
        result = extract_asset(text, skill_dir)
    else:
        return saved

    if result:
        saved.append(result)
    return saved


# ── Helpers ──────────────────────────────────────────────

def _strip_conversation_framing(text: str) -> str:
    """Remove conversational prefixes to extract the core content."""
    # Remove leading conversational fluff: "我们公司政策是：..." → "..."
    content = re.sub(
        r"^.{0,50}?(?:如下[：:]?\s*|这样[：:]?\s*|是这样的[：:]?\s*)",
        "", text, count=1, flags=re.IGNORECASE,
    )
    # Remove specific framing patterns but keep the core content
    content = re.sub(
        r"^(?:模板|话术|政策|规则|流程|邮件|通知)[：:]?\s*",
        "", content, count=1, flags=re.IGNORECASE,
    )
    return content.strip()


def _extract_script_description(text: str) -> str:
    """Extract a short description of what the script does."""
    m = re.search(r"(?:脚本|script|工具)(?:是|叫|用来?|用[于来])\s*(.{5,80}?)(?:[。，,\.]|$)", text, re.IGNORECASE)
    return m.group(1).strip() if m else "用户描述的脚本"


def _generate_filename(text: str, prefix: str, index: int, suffix: str) -> str:
    """Generate a filename based on text content."""
    # Try to extract a meaningful name
    m = re.search(r"(?:脚本|script|命令|command|模板|template)[：:\s]*[\"']?(\w{2,20})", text, re.IGNORECASE)
    if m:
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", m.group(1).lower())[:30]
        return f"{name}{suffix}"

    # Fallback: use prefix + index
    return f"{prefix}_{index + 1}{suffix}"
