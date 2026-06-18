"""MCP skill extraction — 7-step pipeline with structured result + pipeline_log."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ExtractResult:
    ok: bool
    name: str = ""
    content: str = ""
    summary: str = ""
    pipeline_log: list[str] = field(default_factory=list)
    epistemic_summary: dict = field(default_factory=dict)
    skill_path: str = ""
    workspace_path: str = ""
    error: str = ""
    mode: str = "skill"

    def format_mcp_response(self, *, content_max: int = 3000) -> str:
        """Human-readable MCP tool return string."""
        if not self.ok:
            lines = [f"❌ Extraction failed: {self.error}"]
            if self.pipeline_log:
                lines.append("\n## Pipeline log")
                lines.extend(f"- {step}" for step in self.pipeline_log)
            return "\n".join(lines)

        lines = [self.summary or f"✅ Skill '{self.name}' extracted and saved."]
        if self.skill_path:
            lines.append(f"📁 Skill path: {self.skill_path}")
        if self.workspace_path:
            lines.append(f"📂 Workspace copy: {self.workspace_path}")
        ep = self.epistemic_summary
        if ep.get("total_claims", 0):
            lines.append(
                f"📊 认识论：已验证 {ep.get('verified', 0)} · "
                f"待确认 {ep.get('pending', 0)} · 共 {ep.get('total_claims', 0)} 条"
            )
        if self.pipeline_log:
            lines.append("\n## Pipeline log")
            lines.extend(f"- {step}" for step in self.pipeline_log)
        preview = self.content[:content_max] if self.content else ""
        if preview:
            lines.append(f"\n## SKILL.md preview\n{preview}")
        return "\n".join(lines)


def _classify_mode(content: str, mode: str, llm_call) -> str:
    if mode != "auto":
        return mode if mode in ("skill", "knowledge") else "skill"
    preview = content[:1500]
    scan_prompt = f"""Scan this content and decide: is it an actionable methodology (skill), or reference knowledge?

Content: {preview}

Reply with just one word: "skill" or "knowledge"."""
    result = llm_call(scan_prompt, max_tokens=10, temperature=0.1).strip().lower()
    return "skill" if "skill" in result else "knowledge"


def run_mcp_extract(
    content: str,
    source_url: str = "",
    mode: str = "auto",
) -> ExtractResult:
    """Run extraction pipeline for MCP ``extract_skill``."""
    from skillos.config import get_config
    from skillos.llm_client import call

    if not content or not content.strip():
        return ExtractResult(ok=False, error="content is empty")

    preview = content[:6000] if len(content) > 6000 else content
    cfg = get_config()
    llm_args = cfg.to_llm_args()

    try:
        resolved_mode = _classify_mode(preview, mode, call)
    except Exception as e:
        return ExtractResult(ok=False, error=f"mode classification failed: {e}")

    if resolved_mode == "knowledge":
        return _extract_knowledge_package(preview, source_url, llm_args, call)

    return _extract_skill_pipeline(preview, source_url, llm_args)


def _extract_skill_pipeline(preview: str, source_url: str, llm_args: tuple) -> ExtractResult:
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
    from skillos.skills.agent import SkillExtractionAgent
    from skillos.skills import skill_store

    agent = SkillExtractionAgent()
    try:
        summary, doc = agent.learn_from_url(
            source_url or "mcp://extract",
            preview,
            skill_store.list_skills(),
            llm_args,
        )
    except Exception as e:
        return ExtractResult(ok=False, error=str(e), mode="skill")

    pipeline_log = list(doc.get("pipeline_log") or []) if doc else []

    if not doc:
        return ExtractResult(
            ok=False,
            summary=summary,
            pipeline_log=pipeline_log,
            error=summary or "pipeline produced no skill document",
            mode="skill",
        )

    name = doc["name"]
    body = doc["content"]
    try:
        path = skill_store.save_skill(
            name,
            body,
            source=source_url or "mcp-extract",
            source_type="url_content" if source_url else "llm_generated",
            llm_args=llm_args,
        )
        raw = skill_store.load_skill_raw(name)
        ep = format_epistemic_api_payload(raw.get("meta", {}))
        ws_path = skill_store.mirror_skill_to_workspace(name, path)

        try:
            from skillos.hermes_bridge import install_to_hermes, is_hermes_available
            if is_hermes_available():
                install_to_hermes(name, body)
        except Exception:
            pass

        return ExtractResult(
            ok=True,
            name=name,
            content=body,
            summary=summary,
            pipeline_log=pipeline_log,
            epistemic_summary=ep,
            skill_path=str(path),
            workspace_path=str(ws_path) if ws_path else "",
            mode="skill",
        )
    except Exception as e:
        return ExtractResult(
            ok=False,
            name=name,
            content=body,
            summary=summary,
            pipeline_log=pipeline_log,
            error=f"save failed: {e}",
            mode="skill",
        )


def _extract_knowledge_package(preview: str, source_url: str, llm_args: tuple, call) -> ExtractResult:
    prompt = f"""Deep-digest this reference content into a structured knowledge package.

## Source
{source_url or "user-provided content"}

## Content
{preview}

## Output Format
```skill_doc
# Knowledge Package: <title>
## Core Thesis
<narrative summary>
## Glossary
- <term>: <definition>
## Patterns
- <pattern name>: <description>
## Cheatsheet
- <quick reference rules>
```"""
    try:
        raw = call(prompt, max_tokens=1500, temperature=0.2)
        m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        result = m.group(1).strip() if m else raw.strip()
        nm = re.search(
            r"^#\s*(?:Skill Name|Knowledge Package|技能名称)[：:]\s*(.+?)\s*$",
            result,
            re.MULTILINE,
        )
        name = nm.group(1).strip() if nm else "mcp-knowledge"
        from skillos.knowledge.deep_digest import deep_digest, save_digest

        dd = deep_digest(preview, source_url or "mcp://extract", llm_args=llm_args)
        if dd.glossary or dd.patterns:
            save_digest(dd)
        from skillos.knowledge.ingest_pipeline import finalize_ingest
        finalize_ingest(
            preview,
            source_url or "mcp://extract",
            source_title=dd.title,
            digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
            channel="mcp_extract",
        )
        return ExtractResult(
            ok=True,
            name=name,
            content=result,
            summary=f"📦 Knowledge package「{dd.title}」({len(dd.glossary)} terms, {len(dd.patterns)} patterns)",
            pipeline_log=["knowledge: deep_digest completed"],
            mode="knowledge",
        )
    except Exception as e:
        return ExtractResult(ok=False, error=str(e), mode="knowledge")
