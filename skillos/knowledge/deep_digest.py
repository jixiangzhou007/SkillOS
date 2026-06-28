"""Deep Document Digestion — structured knowledge extraction from reference content.

Inspired by book-to-skill's multi-artifact output model. Instead of flattening
a rich document into individual facts, this produces a structured knowledge
package: overview, glossary, patterns, cheatsheet, and per-section summaries.

Philosophy: "Not every document is a skill. Some are terrain maps — they describe
WHAT is true about a domain, not HOW to do a specific task. Treat them accordingly."

Pipeline (6 stages):
  1. Scan & Classify    — What kind of document is this? Worth deep analysis?
  2. Thesis & Structure — Core argument, section map, key claims
  3. Glossary Extraction— Terms, definitions, relationships
  4. Pattern Mining     — Reusable mental models, heuristics, anti-patterns
  5. Cheatsheet Build   — Actionable quick-reference rules
  6. Cross-Reference    — Link to existing skills and knowledge graph
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

# ── Data Models ──────────────────────────────────────────────────

@dataclass
class DigestResult:
    """The complete output of a deep digestion run."""

    slug: str                          # kebab-case identifier
    title: str                         # human-readable title
    source_url: str = ""
    doc_type: str = "article"          # article | paper | tutorial | reference | book_chapter

    # Artifacts
    overview: str = ""                 # core thesis + key arguments
    glossary: list[dict] = field(default_factory=list)  # [{term, definition, related}]
    patterns: list[dict] = field(default_factory=list)  # [{name, description, when_to_use}]
    cheatsheet: str = ""               # quick-reference rules
    sections: list[dict] = field(default_factory=list)  # [{heading, summary, key_points}]

    # Knowledge graph integration
    knowledge_items: list[dict] = field(default_factory=list)
    cross_references: list[dict] = field(default_factory=list)  # [{skill_name, relevance}]

    # Stats
    content_length: int = 0
    elapsed_s: float = 0.0


# ── Core Pipeline ─────────────────────────────────────────────────

def deep_digest(
    content: str,
    source_url: str = "",
    existing_skills: list[str] | None = None,
    llm_args: tuple | None = None,
    *,
    chat_id: str = "",
    session_id: str = "",
) -> DigestResult:
    """Run the full deep digestion pipeline on a document.

    Args:
        content: The full text content to digest
        source_url: Original source URL (for attribution)
        existing_skills: List of existing skill names for cross-referencing
        llm_args: (api_key, base_url, model, chat_kwargs)

    Returns:
        DigestResult with all extracted artifacts
    """
    if existing_skills is None:
        existing_skills = []
    if llm_args is None:
        from skillos.config import get_config
        cfg = get_config()
        llm_args = (cfg.api_key, cfg.base_url, cfg.model, cfg.to_llm_args()[3])

    from skillos.knowledge.knowledge_context import get_ingest_context

    t_start = time.time()
    content_preview = content[:8000] if len(content) > 8000 else content
    ingest_ctx = get_ingest_context(chat_id=chat_id, session_id=session_id)

    result = DigestResult(
        slug="",
        title="",
        source_url=source_url,
        content_length=len(content),
    )

    # ── Stage 1: Scan & Classify ─────────────────────────────
    doc_type, title, is_worth = _stage_scan(content_preview, source_url, llm_args, ingest_ctx)
    result.doc_type = doc_type
    result.title = title
    result.slug = _slugify(title) if title else f"digest-{int(time.time())}"

    if not is_worth:
        _log.info("Deep digest: content classified as not worth deep analysis")
        result.overview = "内容经初步扫描判断为信息密度不足，不进行深度分析。"
        result.elapsed_s = time.time() - t_start
        return result

    # ── Stage 2: Thesis & Structure ──────────────────────────
    overview, sections = _stage_thesis_structure(content_preview, doc_type, llm_args, ingest_ctx)
    result.overview = overview
    result.sections = sections

    # ── Stage 3: Glossary Extraction ─────────────────────────
    glossary = _stage_glossary(content_preview, overview, llm_args, ingest_ctx)
    result.glossary = glossary

    # ── Stage 4: Pattern Mining ──────────────────────────────
    patterns = _stage_patterns(content_preview, overview, glossary, llm_args, ingest_ctx)
    result.patterns = patterns

    # ── Stage 5: Cheatsheet ──────────────────────────────────
    cheatsheet = _stage_cheatsheet(content_preview, overview, glossary, patterns, llm_args, ingest_ctx)
    result.cheatsheet = cheatsheet

    # ── Stage 6: Cross-Reference ─────────────────────────────
    if existing_skills:
        xrefs = _stage_crossref(content_preview, overview, glossary, existing_skills, llm_args, ingest_ctx)
        result.cross_references = xrefs

    # ── Build knowledge items for knowledge graph ────────────
    result.knowledge_items = _build_knowledge_items(result)

    result.elapsed_s = round(time.time() - t_start, 1)
    _log.info("Deep digest complete: slug=%s type=%s glossary=%d patterns=%d sections=%d (%.1fs)",
              result.slug, result.doc_type, len(result.glossary),
              len(result.patterns), len(result.sections), result.elapsed_s)

    return result


# ── Save & Load ───────────────────────────────────────────────────

def save_digest(result: DigestResult) -> Path:
    """Save a digest result to the skills directory as a structured knowledge package.

    Directory structure:
        skills/<slug>/
        ├── SKILL.md         # Manifest (type: knowledge-package)
        ├── overview.md       # Core thesis
        ├── glossary.md       # Terminology
        ├── patterns.md       # Patterns & heuristics
        ├── cheatsheet.md     # Quick reference
        └── sections/         # Per-section summaries
            └── 01-xxx.md
    """
    slug_dir = SKILLS_DIR / result.slug
    slug_dir.mkdir(parents=True, exist_ok=True)

    # ── SKILL.md (manifest) ──
    manifest = _build_manifest_md(result)
    (slug_dir / "SKILL.md").write_text(manifest, encoding="utf-8")

    # ── overview.md ──
    overview_md = f"# {result.title}\n\n**来源**: {result.source_url}\n**类型**: {result.doc_type}\n\n{result.overview}"
    (slug_dir / "overview.md").write_text(overview_md, encoding="utf-8")

    # ── glossary.md ──
    gloss_lines = [f"# 术语表: {result.title}", ""]
    for g in result.glossary:
        gloss_lines.append(f"## {g['term']}")
        gloss_lines.append(f"{g.get('definition', '')}")
        if g.get("related"):
            gloss_lines.append(f"\n关联: {', '.join(g['related'][:5])}")
        gloss_lines.append("")
    (slug_dir / "glossary.md").write_text("\n".join(gloss_lines), encoding="utf-8")

    # ── patterns.md ──
    pat_lines = [f"# 模式与启发式: {result.title}", ""]
    for p in result.patterns:
        pat_lines.append(f"## {p.get('name', 'Pattern')}")
        pat_lines.append(f"{p.get('description', '')}")
        if p.get("when_to_use"):
            pat_lines.append(f"\n**适用场景**: {p['when_to_use']}")
        pat_lines.append("")
    (slug_dir / "patterns.md").write_text("\n".join(pat_lines), encoding="utf-8")

    # ── cheatsheet.md ──
    (slug_dir / "cheatsheet.md").write_text(
        f"# 速查表: {result.title}\n\n{result.cheatsheet}", encoding="utf-8"
    )

    # ── sections/ ──
    if result.sections:
        sec_dir = slug_dir / "sections"
        sec_dir.mkdir(exist_ok=True)
        for i, s in enumerate(result.sections):
            safe_name = _slugify(s.get("heading", f"section-{i+1}"))[:40]
            sec_md = f"# {s.get('heading', f'Section {i+1}')}\n\n"
            sec_md += s.get("summary", "")
            if s.get("key_points"):
                sec_md += "\n\n## 要点\n"
                for kp in s["key_points"]:
                    sec_md += f"- {kp}\n"
            (sec_dir / f"{i+1:02d}-{safe_name}.md").write_text(sec_md, encoding="utf-8")

    # ── Also save knowledge items to skill KB ──
    try:
        from skillos.knowledge import skill_kb
        for ki in result.knowledge_items:
            item = skill_kb.KBItem(
                content=ki.get("content", ""),
                type=ki.get("type", "fact"),
                source=result.source_url,
                confidence=ki.get("confidence", 0.7),
                tags=ki.get("tags", []),
                created_at=time.time(),
            )
            skill_kb.save_item(result.slug, item)
    except Exception as e:
        _log.warning("Failed to save KB items for %s: %s", result.slug, e)

    return slug_dir


def load_digest(slug: str) -> DigestResult | None:
    """Load a previously saved digest."""
    slug_dir = SKILLS_DIR / slug
    manifest_path = slug_dir / "SKILL.md"
    if not manifest_path.exists():
        return None

    content = manifest_path.read_text(encoding="utf-8")
    # Parse manifest YAML frontmatter
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    meta: dict[str, str] = {}
    if m:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}

    result = DigestResult(
        slug=slug,
        title=meta.get("title", slug),
        source_url=meta.get("source_url", ""),
        doc_type=meta.get("doc_type", "article"),
    )

    # Load individual files
    for fname, attr in [("overview.md", "overview"), ("cheatsheet.md", "cheatsheet")]:
        fp = slug_dir / fname
        if fp.exists():
            setattr(result, attr, _strip_h1(fp.read_text(encoding="utf-8")))

    return result


# ── Stage Implementations ─────────────────────────────────────────

def _call_llm(
    prompt: str,
    llm_args: tuple,
    max_tokens: int = 600,
    temperature: float = 0.2,
    *,
    ingest_ctx: str = "",
) -> str:
    from skillos.llm_client import call
    if ingest_ctx:
        prompt = f"{ingest_ctx.rstrip()}\n\n---\n\n{prompt}"
    try:
        return call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                    max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        _log.warning("LLM call failed: %s", e)
        return ""


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences."""
    text = text.strip()
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    json_str = m.group(1) if m else text
    # Try to find a JSON object
    m2 = re.search(r'\{.*\}', json_str, re.DOTALL)
    if m2:
        json_str = m2.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}


def _slugify(text: str) -> str:
    """Convert text to a kebab-case slug."""
    slug = re.sub(r'[^\w一-鿿\-]+', '-', text.strip(), flags=re.UNICODE)
    slug = re.sub(r'-+', '-', slug).strip('-').lower()
    return slug[:64] or f"digest-{int(time.time())}"


def _strip_h1(text: str) -> str:
    """Remove the H1 title line from markdown content."""
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text.strip()


# ── Stage 1: Scan & Classify ──────────────────────────────────────

_SCAN_PROMPT = """快速浏览以下文档内容，回答三个问题。

## 文档来源
{source_url}

## 内容片段
{content_preview}

## 问题（用中文回答）
1. 这是什么类型的文档？（技术教程/学术论文/参考手册/行业报告/博客文章/其他）→ 选一个
2. 这篇文章的核心主题是什么？（一句话标题，20字以内）
3. 信息密度评估：这篇文章是否包含丰富的术语、概念、模式或可操作的知识？
   - "值得" = 包含大量可被提取和组织的知识
   - "不值得" = 主要是新闻、观点、营销内容、或信息密度太低

输出格式（严格三行）：
类型: <类型>
标题: <标题>
判定: <值得|不值得>"""


def _stage_scan(
    content_preview: str, source_url: str, llm_args: tuple, ingest_ctx: str = "",
) -> tuple[str, str, bool]:
    prompt = _SCAN_PROMPT.format(
        source_url=source_url or "用户粘贴内容",
        content_preview=content_preview[:2000],
    )
    raw = _call_llm(prompt, llm_args, max_tokens=150, temperature=0.1, ingest_ctx=ingest_ctx)
    doc_type = "article"
    title = ""
    is_worth = True

    for line in raw.strip().split("\n"):
        line = line.strip()
        if line.startswith("类型:") or line.startswith("类型："):
            doc_type = line.split(":", 1)[-1].split("：", 1)[-1].strip() or "article"
        elif line.startswith("标题:") or line.startswith("标题："):
            title = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif "不值得" in line:
            is_worth = False

    return doc_type, title, is_worth


# ── Stage 2: Thesis & Structure ───────────────────────────────────

_THESIS_PROMPT = """你是文档分析专家。深入阅读以下内容，提取核心论点并划分章节结构。

## 内容
{content_preview}

## 文档类型
{doc_type}

## 要求
1. **核心论点**：用3-5段话总结这篇文章的核心论点。不是列要点——是叙述性的总结。
   回答：作者的核心主张是什么？用什么论据支撑？结论是什么？
2. **章节划分**：将内容按主题划分为3-8个章节。每个章节给出：
   - 标题
   - 一段话总结（100字以内）
   - 3-5个关键要点

输出 JSON：
```json
{{
  "overview": "核心论点的叙述性总结...",
  "sections": [
    {{"heading": "章节标题", "summary": "章节总结", "key_points": ["要点1", "要点2"]}}
  ]
}}
```"""


def _stage_thesis_structure(
    content_preview: str, doc_type: str, llm_args: tuple, ingest_ctx: str = "",
) -> tuple[str, list[dict]]:
    prompt = _THESIS_PROMPT.format(content_preview=content_preview[:6000], doc_type=doc_type)
    raw = _call_llm(prompt, llm_args, max_tokens=1500, temperature=0.3, ingest_ctx=ingest_ctx)
    data = _parse_json(raw)
    overview = data.get("overview", "无法提取核心论点。")
    sections = data.get("sections", [])
    return overview, sections


# ── Stage 3: Glossary ─────────────────────────────────────────────

_GLOSSARY_PROMPT = """从以下文档中提取所有值得定义的术语、概念和缩写。

## 文档摘要
{overview}

## 内容
{content_preview}

## 要求
对每个术语：
1. 提取术语本身
2. 给出清晰的定义（基于原文，不要编造）
3. 标注与其他术语的关系（如果原文中有明确关联）

输出 JSON 数组：
```json
[
  {{"term": "术语名", "definition": "定义内容", "related": ["相关术语1"]}}
]
```

只提取有实质内容的术语（至少5个，最多20个）。如果文档中确实没有值得定义的术语，返回空数组。"""


def _stage_glossary(
    content_preview: str, overview: str, llm_args: tuple, ingest_ctx: str = "",
) -> list[dict]:
    prompt = _GLOSSARY_PROMPT.format(overview=overview[:1000], content_preview=content_preview[:4000])
    raw = _call_llm(prompt, llm_args, max_tokens=1200, temperature=0.2, ingest_ctx=ingest_ctx)
    try:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        json_str = m.group(1) if m else raw
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


# ── Stage 4: Pattern Mining ───────────────────────────────────────

_PATTERNS_PROMPT = """从以下文档中提取可复用的思维模型、设计模式、启发式规则和反模式。

## 文档摘要
{overview}

## 术语
{glossary_summary}

## 内容
{content_preview}

## 提取标准
- **模式**：跨场景可复用的结构或方法
- **启发式**：经验法则（"当X出现时，优先考虑Y"）
- **反模式**：文中明确提到的常见错误或应该避免的做法

输出 JSON 数组：
```json
[
  {{"name": "模式名称", "type": "pattern|heuristic|anti_pattern",
    "description": "模式描述", "when_to_use": "适用场景或触发条件"}}
]
```

如果没有可提取的模式，返回空数组。最多提取10个。"""


def _stage_patterns(
    content_preview: str, overview: str, glossary: list[dict], llm_args: tuple,
    ingest_ctx: str = "",
) -> list[dict]:
    gloss_summary = "\n".join(
        f"- {g.get('term', '')}: {g.get('definition', '')[:80]}" for g in glossary[:10]
    ) if glossary else "（未提取术语）"

    prompt = _PATTERNS_PROMPT.format(
        overview=overview[:800], glossary_summary=gloss_summary,
        content_preview=content_preview[:4000],
    )
    raw = _call_llm(prompt, llm_args, max_tokens=1200, temperature=0.3, ingest_ctx=ingest_ctx)
    try:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        json_str = m.group(1) if m else raw
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


# ── Stage 5: Cheatsheet ───────────────────────────────────────────

_CHEATSHEET_PROMPT = """基于以下文档内容，制作一张速查表。速查表应该让读者在30秒内找到关键信息。

## 文档摘要
{overview}

## 模式与启发式
{patterns_summary}

## 术语
{glossary_summary}

## 要求
用 Markdown 格式组织：
1. **核心公式/规则**（如果有的话，用代码块或引用格式）
2. **决策流程**（if-then 分支，帮助快速判断）
3. **常见陷阱**（应该避免的事）
4. **关键数字/阈值**（如果文档中提到）
5. **一句话总结**（这篇文章最该记住的是什么）

直接输出 Markdown，不要 JSON。保持简洁——目标是真正能当速查表用的东西。"""


def _stage_cheatsheet(
    content_preview: str, overview: str, glossary: list[dict],
    patterns: list[dict], llm_args: tuple, ingest_ctx: str = "",
) -> str:
    patterns_summary = "\n".join(
        f"- {p.get('name', '')}: {p.get('description', '')[:100]}" for p in patterns[:8]
    ) if patterns else "（未提取模式）"
    gloss_summary = ", ".join(g.get("term", "") for g in glossary[:10]) if glossary else "（未提取术语）"

    prompt = _CHEATSHEET_PROMPT.format(
        overview=overview[:1000], patterns_summary=patterns_summary,
        glossary_summary=gloss_summary,
    )
    raw = _call_llm(prompt, llm_args, max_tokens=800, temperature=0.3, ingest_ctx=ingest_ctx)
    return raw.strip()


# ── Stage 6: Cross-Reference ──────────────────────────────────────

_CROSSREF_PROMPT = """检查这份文档的内容与已有技能的相关性。

## 文档摘要
{overview}

## 术语
{glossary_summary}

## 已有技能列表
{skills_list}

## 要求
对每个可能相关的技能，说明：
1. 关联类型（补充知识/矛盾/可类比/提供案例）
2. 关联说明（一句话）

输出 JSON 数组：
```json
[
  {{"skill_name": "技能名", "relation": "补充知识|矛盾|可类比|提供案例", "note": "说明"}}
]
```

最多列出5个最相关的。如果没有明显关联，返回空数组。"""


def _stage_crossref(
    content_preview: str, overview: str, glossary: list[dict],
    existing_skills: list[str], llm_args: tuple, ingest_ctx: str = "",
) -> list[dict]:
    gloss_summary = ", ".join(g.get("term", "") for g in glossary[:8]) if glossary else ""
    skill_names = [s if isinstance(s, str) else (s.get(\"name\", \"\") if isinstance(s, dict) else str(s)) for s in existing_skills[:20]]
    prompt = _CROSSREF_PROMPT.format(
        overview=overview[:800], glossary_summary=gloss_summary,
        skills_list=", ".join(skill_names),
    )
    raw = _call_llm(prompt, llm_args, max_tokens=500, temperature=0.2, ingest_ctx=ingest_ctx)
    try:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        json_str = m.group(1) if m else raw
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


# ── Build Knowledge Items ─────────────────────────────────────────

def _build_knowledge_items(result: DigestResult) -> list[dict]:
    """Convert digest artifacts into knowledge items for the knowledge graph."""
    items = []

    # Add glossary terms as concept items
    for g in result.glossary:
        items.append({
            "content": f"{g['term']}: {g.get('definition', '')}",
            "type": "concept",
            "confidence": 0.8,
            "tags": ["glossary"] + g.get("related", [])[:3],
        })

    # Add patterns as heuristic items
    for p in result.patterns:
        items.append({
            "content": f"{p.get('name', '')}: {p.get('description', '')}",
            "type": "heuristic",
            "confidence": 0.7,
            "tags": [p.get("type", "pattern")],
        })

    # Add key points from sections as fact items
    for s in result.sections:
        for kp in s.get("key_points", [])[:3]:
            items.append({
                "content": kp,
                "type": "fact",
                "confidence": 0.6,
                "tags": [s.get("heading", "")],
            })

    return items


# ── Manifest Builder ──────────────────────────────────────────────

def _build_manifest_md(result: DigestResult) -> str:
    """Build the SKILL.md manifest for a knowledge package."""
    import yaml

    frontmatter = {
        "name": result.slug,
        "type": "knowledge-package",
        "title": result.title,
        "source_url": result.source_url,
        "doc_type": result.doc_type,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stats": {
            "glossary_terms": len(result.glossary),
            "patterns": len(result.patterns),
            "sections": len(result.sections),
            "knowledge_items": len(result.knowledge_items),
            "cross_references": len(result.cross_references),
        },
    }

    header = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()

    lines = [
        "---",
        header,
        "---",
        "",
        f"# {result.title}",
        "",
        "> 📦 Knowledge Package — 这不是一个可执行的技能，而是一个结构化的知识包。",
        "> 它包含从原始文档中提取的术语、模式、速查表和章节摘要。",
        f"> 来源: {result.source_url}",
        "",
        "## 使用方式",
        "",
        "- 对话中提到相关主题时，Agent 会自动检索此知识包中的相关内容",
        "- 你也可以直接询问：「关于{title}，XX是怎么说的？」",
        "- 查看 `overview.md` 了解核心论点",
        "- 查看 `glossary.md` 了解术语定义",
        "- 查看 `patterns.md` 了解可复用的思维模型",
        "- 查看 `cheatsheet.md` 快速查阅关键规则",
        "",
        "## 文件索引",
        "",
        "| 文件 | 内容 |",
        "|------|------|",
        "| overview.md | 核心论点与关键论证 |",
        f"| glossary.md | {len(result.glossary)} 个术语定义 |",
        f"| patterns.md | {len(result.patterns)} 个模式与启发式 |",
        "| cheatsheet.md | 速查表 |",
    ]

    if result.sections:
        lines.append(f"| sections/ | {len(result.sections)} 个章节摘要 |")

    if result.cross_references:
        lines.append("")
        lines.append("## 知识关联")
        lines.append("")
        for xr in result.cross_references:
            icon = {"补充知识": "📚", "矛盾": "⚠️", "可类比": "🔍", "提供案例": "📖"}.get(
                xr.get("relation", ""), "🔗"
            )
            lines.append(f"- {icon} **{xr.get('skill_name', '')}**: {xr.get('note', '')}")

    lines.append("")
    lines.append("---")
    lines.append(f"*由 Deep Digest 引擎自动生成 · {result.elapsed_s}s*")

    return "\n".join(lines)


# ── Quick Check ───────────────────────────────────────────────────

def is_worth_deep_digest(content: str, llm_args: tuple | None = None) -> tuple[bool, str]:
    """Quick pre-check: is this content worth deep digestion?

    Returns (is_worth, reason).
    Can be called before the full pipeline to avoid wasting tokens.
    """
    if len(content) < 300:
        return False, "内容太短（<300字符），不适合深度分析"

    if llm_args is None:
        return True, "内容长度足够，建议进行深度分析（跳过LLM预检）"

    doc_type, title, is_worth = _stage_scan(content[:2000], "", llm_args)
    if not is_worth:
        return False, f"预检判定：信息密度不足（类型={doc_type}）"
    return True, f"预检通过：{doc_type}「{title}」"
