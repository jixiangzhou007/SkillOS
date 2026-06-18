"""SkillOS MCP Server — expose skill engineering tools via Model Context Protocol.

Usage:
  # Standalone
  python -m skillos.mcp_server

  # Via Claude Code config
  {
    "mcpServers": {
      "skillos": {
        "command": "python",
        "args": ["-m", "skillos.mcp_server"]
      }
    }
  }

  # Via Hermes
  hermes mcp add skillos --url http://localhost:9876/mcp

Tools exposed:
  extract_skill     — Extract a skill from URL or text via 7-step pipeline
  search_knowledge  — Search the knowledge base
  digest_document   — Deep document digestion (glossary, patterns, cheatsheet)
  query_lineage     — Query knowledge lineage (where did this fact come from?)
  list_skills       — List all available skills
  get_skill         — Get a skill's full content
  evolve_skill      — Trigger skill optimization
  confirm_pending_claims — Promote pending Experience claims to Knowledge
  export_for_skillopt   — Export best_skill.md + traces for external SkillOpt
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

_log = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("SkillOS")


# ═══════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
def extract_skill(
    content: str,
    source_url: str = "",
    mode: str = "auto",
) -> str:
    """Extract a structured skill document from text content or URL.

    Uses the 7-step cognitive learning pipeline (初识→理解→拆解→重构→验证→内化→沉淀).
    Returns pipeline_log steps, epistemic summary, and saved SKILL.md path.

    Args:
        content: The text to extract from, or URL content if source_url is set
        source_url: Original URL for attribution
        mode: "auto", "skill" (procedural), or "knowledge" (reference material)

    Returns:
        Summary, pipeline log, epistemic counts, paths, and SKILL.md preview
    """
    from skillos.mcp_extract import run_mcp_extract
    from skillos.identity.mcp_context import mcp_tenant_context

    with mcp_tenant_context():
        result = run_mcp_extract(content, source_url=source_url, mode=mode)
    return result.format_mcp_response()


@mcp.tool()
def search_knowledge(
    query: str,
    top_k: int = 5,
    skill_name: str = "",
) -> str:
    """Search the knowledge base. Finds facts, concepts, and heuristics.

    Args:
        query: What to search for
        top_k: Max results (default 5)
        skill_name: Optional skill to scope the search to

    Returns:
        Matching knowledge items with confidence scores
    """
    try:
        from skillos.knowledge.extractor import load_all_knowledge
        items = load_all_knowledge()
        if not items:
            return "No knowledge items found. Feed some content first."

        # Simple keyword scoring
        qwords = set(re.findall(r'[\w一-鿿]{2,}', query.lower()))
        scored = []
        for item in items:
            iwords = set(re.findall(r'[\w一-鿿]{2,}', item.content.lower()))
            score = len(qwords & iwords) / max(len(qwords), 1)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return "No matching knowledge found."

        lines = [f"Found {len(scored)} matches for '{query}':"]
        for score, item in scored[:top_k]:
            conf = item.confidence
            valid = "✓" if item.invalid_at == 0 else "✗"
            lines.append(f"\n{valid} [{item.category}] (confidence: {conf:.0%})")
            lines.append(f"  {item.content[:200]}")
            if item.source_url:
                lines.append(f"  Source: {item.source_url[:80]}")

        return "\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


@mcp.tool()
def list_skills(query: str = "") -> str:
    """List all available skills.

    Args:
        query: Optional search term to filter skills

    Returns:
        List of skill names with basic metadata
    """
    try:
        from skillos.skills.skill_store import list_skills, load_skill, get_skill_body
        from skillos.identity.mcp_context import mcp_tenant_context

        with mcp_tenant_context():
            skills = list_skills()
            if query:
                skills = [s for s in skills if query.lower() in s.lower()]

            if not skills:
                return "No skills found."

            lines = [f"Skills ({len(skills)} total):"]
            for name in sorted(skills)[:20]:
                try:
                    doc = load_skill(name)
                    body = get_skill_body(doc)
                    lines.append(f"\n## {name}")
                    for line in body.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            lines.append(f"  {line[:120]}")
                            break
                except Exception:
                    lines.append(f"\n## {name}")
            return "\n".join(lines)
    except Exception as e:
        return f"List failed: {e}"


@mcp.tool()
def get_skill(name: str) -> str:
    """Get the full content of a specific skill.

    Args:
        name: Skill name

    Returns:
        Full skill document in Markdown
    """
    try:
        from skillos.skills.skill_store import load_skill, load_skill_raw
        from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
        content = load_skill(name)
        raw = load_skill_raw(name)
        ep = format_epistemic_api_payload(raw.get("meta", {}))
        footer = ""
        if ep.get("total_claims", 0):
            footer = (
                f"\n\n---\n📊 Epistemic: verified={ep['verified']} "
                f"pending={ep['pending']} total={ep['total_claims']}"
            )
        return content[:5000] + footer
    except FileNotFoundError:
        return f"Skill '{name}' not found."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def query_lineage(question: str, skill_name: str = "") -> str:
    """Query the knowledge lineage — trace where knowledge came from.

    Ask questions like:
    - "How did this skill evolve over time?"
    - "What knowledge items were extracted from article X?"
    - "Has anyone tried changing the threshold before?"

    Args:
        question: Natural language question about knowledge history
        skill_name: Optional skill to scope the query to

    Returns:
        Answer based on decision history and knowledge lineage
    """
    try:
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        knowledge = store.get_knowledge()

        if not knowledge:
            return "No verified knowledge in the system yet."

        # Find relevant claims
        qwords = set(re.findall(r'[\w一-鿿]{2,}', question.lower()))
        relevant = []
        for claim in knowledge[:50]:
            cwords = set(re.findall(r'[\w一-鿿]{2,}', claim.content.lower()))
            if qwords & cwords:
                relevant.append(claim)

        if not relevant:
            return f"No knowledge lineage matches '{question}'. Try rephrasing."

        lines = [f"Knowledge lineage for: {question}"]
        for claim in relevant[:5]:
            lines.append(f"\n[{claim.level.value}] (confidence: {claim.confidence:.0%})")
            lines.append(f"  {claim.content[:200]}")
            if claim.source:
                lines.append(f"  Source: {claim.source}")
            if claim.corroborated_by:
                lines.append(f"  Corroborated by: {len(claim.corroborated_by)} other claims")
            if claim.contradicted_by:
                lines.append(f"  ⚠️ Contradicted by: {len(claim.contradicted_by)} claims")

        return "\n".join(lines)
    except Exception as e:
        return f"Lineage query failed: {e}"


@mcp.tool()
def digest_document(content: str, source_url: str = "") -> str:
    """Deep document digestion — extract glossary, patterns, and cheatsheet.

    Use this for reference material that isn't a procedural skill.
    Produces a structured knowledge package.

    Args:
        content: The document text
        source_url: Original URL for attribution

    Returns:
        Structured knowledge package with glossary, patterns, cheatsheet
    """
    preview = content[:8000] if len(content) > 8000 else content

    from skillos.llm_client import call

    prompt = f"""Deep-digest this document into a structured knowledge package.

## Source
{source_url or "provided content"}

## Content
{preview}

## Output
```markdown
# Knowledge Package: <title>

## Core Thesis
<3-5 sentence narrative summary>

## Glossary
| Term | Definition | Related |
|------|-----------|---------|
| ... | ... | ... |

## Patterns & Heuristics
| Name | Description | When to Use |
|------|------------|-------------|
| ... | ... | ... |

## Cheatsheet
- <key rule or formula>
- <decision flow>

## Cross-References
- <related skills or knowledge items>
```"""

    try:
        raw = call(prompt, max_tokens=2000, temperature=0.2)
        m = re.search(r"```(?:markdown)?\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        result = m.group(1).strip() if m else raw.strip()

        # Save as knowledge package
        from skillos.skills.skill_store import save_skill
        nm = re.search(r"^#\s*Knowledge Package[：:]\s*(.+?)\s*$", result, re.MULTILINE)
        name = nm.group(1).strip() if nm else "digested-doc"
        save_skill(name, result)
        return f"✅ Knowledge package '{name}' created.\n\n{result[:3000]}"
    except Exception as e:
        return f"Digestion failed: {e}"


@mcp.tool()
def evolve_skill(name: str, feedback: str = "") -> str:
    """Trigger skill optimization based on usage feedback.

    Uses the MoE (Mixture of Experts) router to choose the best
    optimization strategy: SkillOpt (bounded edits), Trace2Skill (batch diagnosis),
    or EvoSkill (tournament selection).

    Runs the independent Auditor (8-dim check) and records the decision
    in the persistent decision history (WHY chain).

    Args:
        name: Skill name to optimize
        feedback: Optional user feedback about what needs improvement

    Returns:
        Optimization result with before/after scores, audit report, and decision ID
    """
    import time

    try:
        from skillos.skills.skill_store import load_skill, get_skill_body
        from skillos.config import get_config
        from skillos.evolution.skillopt import OptimizationSession, compute_skill_state, route
        from skillos.evolution.skillhone import build_decision_context, isolated_evaluate

        content = load_skill(name)
        body = get_skill_body(content)
        cfg = get_config()
        llm_args = cfg.to_llm_args()

        # Compute skill state for MoE routing
        state = compute_skill_state(name, content)
        decision = route(state)

        # Run optimization
        session = OptimizationSession(skill_name=name, original_content=body, current_content=body)

        from skillos.evolution.skillopt import run_optimization_round
        t0 = time.time()
        result = run_optimization_round(session, llm_args, feedback)

        lines = [
            f"Skill: {name}",
            f"State: {state.trace_count} traces, score={state.score_mean:.1f}±{state.score_variance:.1f}, {state.days_since_creation:.0f}d old",
            f"Router: {decision.primary.name} (confidence: {decision.confidence:.0%})",
            f"Reasoning: {decision.reasoning}",
            f"",
            f"Result: {'ACCEPTED' if result.get('accepted') else 'REJECTED'}",
            f"Score: {result.get('old_score', 0):.1f} → {result.get('new_score', 0):.1f}",
            f"Budget: {result.get('budget', 0)} edits",
        ]

        if result.get("audit"):
            audit = result["audit"]
            lines.append(f"Audit: {audit['score']}/100 ({'PASS' if audit.get('passed') else 'FAIL'})")
            for c in audit.get("checks", [])[:3]:
                lines.append(f"  {c['check']}: {c.get('severity', '?')}")

        lines.append(f"Time: {result.get('elapsed_s', 0):.1f}s")
        return "\n".join(lines)

    except FileNotFoundError:
        return f"Skill '{name}' not found."
    except Exception as e:
        import traceback
        return f"Evolution failed: {e}\n{traceback.format_exc()}"


@mcp.tool()
def confirm_pending_claims(
    claim_ids: str = "",
    skill_name: str = "",
    confirm_all: bool = False,
) -> str:
    """Promote pending Experience claims to verified Knowledge.

    Use after ``extract_skill`` when epistemic summary shows pending claims.
    Matches the IM dispatch phrase table in ``docs/USER_GUIDE.md``.

    Args:
        claim_ids: Comma-separated claim IDs or 1-based indices (e.g. "1,2,3")
        skill_name: Limit pending scope to one skill (optional)
        confirm_all: Confirm all pending claims for skill_name (or globally if empty)

    Returns:
        Promotion summary with synced skill names
    """
    try:
        from skillos.knowledge.epistemic_bridge import confirm_claims_detailed
        from skillos.skills.intent_router import (
            list_pending_for_confirm,
            parse_confirm_claim_selection,
        )

        pending = list_pending_for_confirm(skill_name)
        if confirm_all:
            selected = pending
        elif claim_ids.strip():
            synthetic = claim_ids if claim_ids.startswith("确认") else f"确认 {claim_ids}"
            if claim_ids.strip().startswith("claim_"):
                synthetic = claim_ids
            selected = parse_confirm_claim_selection(synthetic, pending)
            if not selected and "," in claim_ids:
                selected = [c.strip() for c in claim_ids.split(",") if c.strip()]
        else:
            return "No claim_ids provided. Use confirm_all=true or claim_ids='1,2' / claim IDs."

        if not selected:
            return f"No pending claims matched (pending={len(pending)})."

        result = confirm_claims_detailed(selected)
        lines = [
            f"Promoted: {result.promoted} claim(s)",
            f"Claim IDs: {', '.join(result.claim_ids) or 'none'}",
        ]
        if result.synced_skills:
            lines.append(f"Synced skills: {', '.join(result.synced_skills)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def export_for_skillopt(skill_name: str, output_dir: str = "") -> str:
    """Export a skill bundle for Microsoft SkillOpt-style optimization.

    Creates ``best_skill.md``, ``skill.md``, optional ``traces.jsonl``, and
    ``manifest.json`` under ``data/exports/skillopt/{skill}-skillopt/``.

    Args:
        skill_name: Skill to export
        output_dir: Optional absolute output root (default: data/exports/skillopt)

    Returns:
        Export paths and epistemic summary
    """
    try:
        from skillos.evolution.skillopt_export import export_for_skillopt as _export

        out = Path(output_dir) if output_dir.strip() else None
        result = _export(skill_name, output_dir=out)
        lines = [
            f"Exported: {result.skill_name}",
            f"Directory: {result.export_dir}",
            f"best_skill.md: {result.best_skill_path}",
        ]
        if result.traces_path:
            lines.append(f"traces.jsonl: {result.traces_path}")
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        ep = manifest.get("epistemic_summary", {})
        if ep.get("total_claims"):
            lines.append(
                f"Epistemic: verified={ep.get('verified', 0)} pending={ep.get('pending', 0)}"
            )
        return "\n".join(lines)
    except FileNotFoundError:
        return f"Skill '{skill_name}' not found."
    except Exception as e:
        return f"Export failed: {e}"


@mcp.tool()
def get_epistemic_context() -> str:
    """Get the current verified knowledge context.

    Returns all knowledge claims that have been verified and are currently valid.
    This is useful for providing background context to an AI agent.
    """
    try:
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        knowledge = store.get_knowledge()

        if not knowledge:
            return "No verified knowledge yet."

        lines = [f"Verified Knowledge ({len(knowledge)} claims):"]
        for claim in knowledge[:15]:
            lines.append(f"- [{claim.level.value}] ({claim.confidence:.0%}) {claim.content[:200]}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def ingest_file(file_path: str) -> str:
    """Ingest a local file (PDF, DOCX, XLSX, PPTX, etc.) and convert to knowledge.

    Uses MarkItDown to convert any file format to Markdown, then runs
    deep document digestion (glossary, patterns, cheatsheet).

    Args:
        file_path: Absolute path to the file

    Returns:
        Digestion result with extracted knowledge
    """
    from pathlib import Path
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"

    try:
        from skillos.utils.file_ingest import ingest_and_learn
        from skillos.config import get_config

        cfg = get_config()
        result = ingest_and_learn(
            str(p), p.name, llm_args=cfg.to_llm_args()
        )

        lines = [f"File: {p.name} ({result.get('file_category', '?')})"]
        if result.get("error"):
            lines.append(f"Error: {result['error']}")
        elif result.get("digest"):
            d = result["digest"]
            lines.append(f"Knowledge Package: {d['title']} ({d['slug']})")
            lines.append(f"  Glossary: {d['glossary_terms']} terms")
            lines.append(f"  Patterns: {d['patterns']} patterns")
            lines.append(f"  Sections: {d['sections']} sections")
            lines.append(f"  Cross-refs: {d['cross_references']} references")
        else:
            lines.append(f"Markdown: {result.get('markdown_length', 0)} chars")
        return "\n".join(lines)
    except Exception as e:
        return f"Ingestion failed: {e}"


@mcp.tool()
def fetch_url(url: str) -> str:
    """Fetch and digest content from a URL (web page, article, WeChat article).

    Automatically uses CDP browser for anti-crawl platforms (WeChat, Xiaohongshu, Weibo)
    and standard HTTP for regular sites.

    Args:
        url: The URL to fetch

    Returns:
        Extracted content and knowledge
    """
    try:
        from skillos.utils.wechat_fetch import needs_cdp

        if needs_cdp(url):
            from skillos.utils.wechat_fetch import fetch
        else:
            from skillos.utils.web_fetch import fetch

        content = fetch(url)
        if not content or len(content) < 100:
            return f"Could not fetch meaningful content from {url}"

        # Run deep digest
        from skillos.config import get_config
        from skillos.knowledge.deep_digest import deep_digest, save_digest

        cfg = get_config()
        result = deep_digest(content, url, llm_args=cfg.to_llm_args())

        lines = [f"URL: {url}"]
        lines.append(f"Content: {len(content)} chars")
        if result.glossary or result.patterns:
            save_digest(result)
            lines.append(f"Knowledge Package: {result.title}")
            lines.append(f"  Glossary: {len(result.glossary)} terms")
            lines.append(f"  Patterns: {len(result.patterns)} patterns")
            lines.append(f"  Sections: {len(result.sections)} sections")
            # Also extract individual facts to the global knowledge base
            extracted_items: list = []
            try:
                from skillos.knowledge.extractor import extract_knowledge, save_knowledge
                extracted_items = extract_knowledge(content, url)
                if extracted_items:
                    saved = save_knowledge(extracted_items)
                    lines.append(f"  Knowledge items: {saved} stored in global KB")
            except Exception as e:
                lines.append(f"  Knowledge extraction: skipped ({e})")
            try:
                from skillos.knowledge.ingest_pipeline import finalize_ingest
                fin = finalize_ingest(
                    content,
                    url,
                    source_title=result.title,
                    digest_result=result,
                    extractor_items=extracted_items,
                    channel="mcp_fetch",
                )
                lineage = fin.get("lineage") or {}
                if lineage.get("lineage_applied"):
                    lines.append(f"  Lineage: {lineage.get('edges_created', 0)} edges, session={lineage.get('session_id', '')[:16]}")
            except Exception:
                pass
        else:
            lines.append(f"Content preview: {content[:500]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Fetch failed: {e}"


@mcp.tool()
def ask_user(question: str, options: str = "") -> str:
    """Ask the user a question with selectable options. Works on ANY platform.

    Generates numbered options that work on WeChat, Feishu, Hermes TUI, etc.
    For platforms supporting buttons (Feishu), the caller can render as buttons.

    Args:
        question: The question to ask
        options: Comma-separated options, e.g. "Option A, Option B, Option C"

    Returns:
        Formatted question with numbered options
    """
    if not options:
        return f"❓ {question}"

    opts = [o.strip() for o in options.split(",") if o.strip()]
    lines = [f"❓ {question}", ""]
    for i, opt in enumerate(opts, 1):
        lines.append(f"{i}. {opt}")
    lines.append("")
    lines.append("Reply with the number.")
    return "\n".join(lines)


@mcp.tool()
def watch_account(account_name: str) -> str:
    """Add a WeChat official account to watch. Auto-fetches its recent articles
    and ingests them into the knowledge base.

    Args:
        account_name: The WeChat official account name (e.g. "腾讯云开发者")

    Returns:
        Summary of articles found and ingested
    """
    try:
        from skillos.utils.account_watcher import add_account
        result = add_account(account_name)
        return (
            f"Account: {result['account']}\n"
            f"Articles found: {result['articles_found']}\n"
            f"New articles: {result['new_articles']}\n"
            f"Ingested: {result['ingested']}\n"
            f"Auto-check enabled: every 6 hours"
        )
    except Exception as e:
        return f"Failed: {e}. Make sure CDP browser is running (Edge with remote debugging on port 9222)."


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

def main():
    """Run the MCP server (stdio transport for Claude Code / Cursor)."""
    mcp.run()


if __name__ == "__main__":
    main()
