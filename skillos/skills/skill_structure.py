"""Skill body structure helpers — S_body normalization and heritage section merge."""


import re
from pathlib import Path
from typing import Any

# Sections treated as executable body for DNA compliance (first match wins).
BODY_SECTION_ALIASES: tuple[str, ...] = (
    "S_body",
    "Instructions",
    "执行步骤",
    "操作流程",
    "操作步骤",
)

TRIGGER_ALIASES: tuple[str, ...] = ("S_trigger", "When to use")
ROUTE_ALIASES: tuple[str, ...] = ("S_route", "Decision routes", "决策路由")

# High-value blocks preserved across re-extraction (regex on ## heading text).
PROTECTED_SECTION_PATTERNS: tuple[str, ...] = (
    r"应答速查",
    r"快速应答",
    r"标准应答模板",
    r"审查应答速查",
    r"清洗应答速查",
)

DOMAIN_PROTECTED_PATTERNS: dict[str, tuple[str, ...]] = {
    "workflow-refund": (r"应答速查", r"快速应答"),
    "code-review-pr": (r"审查应答速查", r"依赖.*审查"),
    "data-csv-clean": (r"清洗应答速查", r"去重.*异常"),
}

DOMAIN_HERITAGE_TEMPLATES: dict[str, tuple[str, str]] = {
    "workflow-refund": (
        "应答速查（单条回复、可执行）",
        """收到「处理客户退款」类请求时，**在同一条回复中**给出完整可执行方案，不要只追问、也不要跳过核实就写「已发起退款」。

**硬性规则**
- 必须先核实订单号、金额、售后期与身份，再进入执行步骤。
- **禁止**在未完成核实时写「已为您发起退款」「直接为您处理退款」。
- 金额 >500 元或疑似欺诈 → 转人工，不自动退款。

**标准应答模板**
1. **核实**：查询订单发货/签收状态与售后期；请客户确认身份。
2. **方案**：未发货→仅退款；可拦截→拦截后仅退款；已签收→按原因匹配退货退款。
3. **执行**：核实通过后原路退回（微信/支付宝自动；银行卡对公需人工确认）。
4. **通知**：退款完成后短信通知，并同步 ERP 订单状态。
""",
    ),
    "code-review-pr": (
        "审查应答速查（单条回复、可执行）",
        """收到 PR 审查、代码 review 或 **software-dependency-audit（依赖审计）** 请求时，在同一条回复给出可执行结论，不要只列泛泛原则。

**硬性规则**
- 先点明审查维度（动机/diff 规模/安全/性能/依赖/测试/CI），再引用具体代码行或依赖包名。
- 阻塞问题 → request changes；风格问题 → suggestion；CI 未全绿不得 approve。

**性能审查（含 N+1 / 时间复杂度）**
- ORM 循环访问关联字段 → 指出 **N+1**，建议 `select_related` / `prefetch_related` / join / 批量查询。
- 嵌套循环或 `x in list` 导致 **O(n²)** → 建议 set/dict 优化并说明复杂度。

**安全审查（含反序列化 / pickle）**
- `pickle.loads` / **unsafe deserialization** → 标记 **blocking**；建议 **JSON** 替代 pickle。
- 用 **validate** / schema 对不可信输入做**输入检查**后再反序列化（deserialization）。
- 无限循环风险 → 建议 `timeout` / `max_iter` / 明确 break 条件。

**依赖与供应链（dependency audit）**
- 检查 lockfile（package-lock / yarn.lock / poetry.lock）是否纳入版本管理。
- 标注 **CVE**、过期 major、未 pin 的宽松版本范围（^/~）。
- 传递依赖风险：说明影响面与建议升级/pin 路径。

**标准应答结构**：PR 动机 → diff 规模 → 安全 → 性能 → 依赖 → 测试与 CI → 合并建议。
""",
    ),
    "data-csv-clean": (
        "清洗应答速查（单条回复、可执行）",
        """收到 CSV/表格清洗请求时，在同一条回复给出完整可执行方案（含去重、空值、金额、日期、报告），不要只追问。

**硬性规则**
- 必须说明：主键去重策略、异常行如何处理（单独导出，不静默删除）、输出物（清洗表 + 异常表 + 报告）。
- 金额列：去掉货币符号和千分位逗号，转为 decimal；负数单独标出。
- 日期列：统一为 YYYY-MM-DD；无法解析的进异常表。

**标准步骤模板**
1. 按主键 id **去重**（duplicate/dedup），保留最早一条。
2. email 为空或格式非法 → 导出**异常表**，不静默删除。
3. 金额/日期规范化后输出**清洗报告**（总行数、去重数、异常数、字段填充率）。
""",
    ),
}

DOMAIN_S_PARAMS_TEMPLATES: dict[str, str] = {
    "workflow-refund": """| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| order_id | string | 必填 | 订单号 |
| refund_type | enum | 仅退款 | 仅退款 / 退货退款 |
| amount | decimal | — | 申请退款金额（元） |
| risk_level | enum | normal | normal / medium / high |
| no_reason_return_days | int | 7 | 无理由退货时效（天） |
| auto_refund_max | int | 500 | 超过此金额转人工（元） |
""",
    "code-review-pr": """| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| pr_url | string | 必填 | PR/MR 链接或 diff 内容 |
| max_diff_lines | int | 500 | 建议拆分 PR 的行数阈值 |
| block_max_lines | int | 1000 | 直接打回的行数阈值 |
| require_ci_green | bool | true | CI 未全绿不得 approve |
""",
    "data-csv-clean": """| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| file_path | string | 必填 | CSV 文件路径 |
| primary_key | string | id | 去重主键列 |
| email_column | string | email | 邮箱列名 |
| encoding | string | utf-8 | 优先 UTF-8，失败尝试 GBK |
| output_date_format | string | YYYY-MM-DD | 统一日期格式 |
""",
}

_PARAM_SECTION_ALIASES: tuple[str, ...] = ("S_params", "Inputs", "Input", "Parameters")

_JUNK_SECTION_PATTERNS: tuple[str, ...] = (
    r"参数抽象度评委",
    r"当前问题诊断",
    r"改进目标",
    r"改进后.*S_params",
    r"业务规则配置",
    r"参数使用说明",
    r"^#+\s*#",  # broken headings like ## ##
    r"^#\s+参数",
)

_CANONICAL_TAIL_SECTIONS: frozenset[str] = frozenset({
    "认识论状态",
    "epistemic",
    "质量审核",
})

_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def split_h2_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Split markdown body into preamble (# title) and ## sections."""
    matches = list(_SECTION_HEADING_RE.finditer(body))
    if not matches:
        return body.strip(), []
    preamble = body[: matches[0].start()].strip()
    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((match.group(1).strip(), body[start:end].strip()))
    return preamble, sections


def strip_heritage_sections(body: str) -> str:
    """Remove HERITAGE / 应答速查 blocks for ablation (keep S_body, S_route, etc.)."""
    preamble, sections = split_h2_sections(body)
    kept = [
        (h, t) for h, t in sections
        if not any(heading_matches_pattern(h, pat) for pat in PROTECTED_SECTION_PATTERNS)
    ]
    parts = [preamble] if preamble else []
    for h, t in kept:
        parts.append(f"## {h}\n{t}")
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def compose_skill_markdown(meta: dict[str, Any], body: str) -> str:
    """Rebuild SKILL.md frontmatter + body."""
    from skillos.skills.skill_store import _compose
    return _compose(meta, body)

def _section_text(content: str, names: list[str] | tuple[str, ...]) -> str:
    """Extract first matching ## section by exact heading name."""
    for name in names:
        pattern = rf"##\s*{re.escape(name)}\s*\n(.*?)(?=\n##\s+|\Z)"
        m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


def extract_executable_body(content: str) -> str:
    """Body text for DNA compliance — S_body or portable aliases."""
    return _section_text(content, BODY_SECTION_ALIASES)


def heading_matches_pattern(heading: str, pattern: str) -> bool:
    return bool(re.search(pattern, heading, re.IGNORECASE))


def protected_patterns_for_domain(domain_template: str | None) -> tuple[str, ...]:
    extra = DOMAIN_PROTECTED_PATTERNS.get(domain_template or "", ())
    return PROTECTED_SECTION_PATTERNS + extra


def extract_protected_sections(
    body: str,
    *,
    domain_template: str | None = None,
) -> list[tuple[str, str]]:
    patterns = protected_patterns_for_domain(domain_template)
    _, sections = split_h2_sections(body)
    out: list[tuple[str, str]] = []
    for heading, text in sections:
        if any(heading_matches_pattern(heading, p) for p in patterns):
            out.append((heading, text))
    return out


def _has_protected_heading(body: str, heading: str, patterns: tuple[str, ...]) -> bool:
    _, sections = split_h2_sections(body)
    for h, _ in sections:
        if h == heading:
            return True
        if any(heading_matches_pattern(h, p) for p in patterns if heading_matches_pattern(heading, p)):
            return True
    return False


def _trigger_insert_index(sections: list[tuple[str, str]]) -> int:
    """Insert protected blocks after trigger / before body."""
    trigger_keys = {a.lower() for a in TRIGGER_ALIASES}
    body_keys = {a.lower() for a in BODY_SECTION_ALIASES}
    last_trigger = -1
    first_body = len(sections)
    for i, (heading, _) in enumerate(sections):
        hl = heading.lower()
        if hl in trigger_keys or "trigger" in hl or "when to use" in hl:
            last_trigger = i
        if hl in body_keys or heading in BODY_SECTION_ALIASES:
            first_body = min(first_body, i)
    if last_trigger >= 0:
        return last_trigger + 1
    return min(first_body, len(sections))


def merge_protected_sections(
    old_body: str,
    new_body: str,
    *,
    domain_template: str | None = None,
) -> tuple[str, list[str]]:
    """Copy protected sections from old_body into new_body when missing."""
    patterns = protected_patterns_for_domain(domain_template)
    protected = extract_protected_sections(old_body, domain_template=domain_template)
    if not protected:
        return new_body, []

    preamble, sections = split_h2_sections(new_body)
    merged_names: list[str] = []
    insert_at = _trigger_insert_index(sections)

    for heading, text in protected:
        already = any(
            h == heading or (
                any(heading_matches_pattern(heading, p) for p in patterns)
                and any(heading_matches_pattern(h, p) for p in patterns)
            )
            for h, _ in sections
        )
        if already:
            continue
        block = (heading, text)
        sections.insert(insert_at, block)
        insert_at += 1
        merged_names.append(heading)

    if not merged_names:
        return new_body, []

    parts = [preamble] if preamble else []
    for heading, text in sections:
        parts.append(f"## {heading}\n{text}")
    return "\n\n".join(parts).strip() + "\n", merged_names


def apply_domain_heritage_templates(
    body: str,
    *,
    domain_template: str | None = None,
) -> tuple[str, list[str]]:
    """Insert canonical domain blocks when missing (e.g. PR 审查应答速查)."""
    patterns = protected_patterns_for_domain(domain_template)
    entry = DOMAIN_HERITAGE_TEMPLATES.get(domain_template or "")
    if not entry:
        try:
            from skillos.skills.domain_pack import get_heritage_entry

            entry = get_heritage_entry(domain_template)
        except Exception:
            entry = None
    if not entry:
        return body, []
    heading, text = entry
    preamble, sections = split_h2_sections(body)
    if any(
        heading_matches_pattern(h, heading) or any(heading_matches_pattern(h, p) for p in patterns)
        for h, _ in sections
    ):
        return body, []

    insert_at = _trigger_insert_index(sections)
    sections.insert(insert_at, (heading, text.strip()))
    parts = [preamble] if preamble else []
    for h, t in sections:
        parts.append(f"## {h}\n{t}")
    return "\n\n".join(parts).strip() + "\n", [heading]


def merge_from_version_archives(
    skill_name: str,
    body: str,
    skill_md_path: Path,
    *,
    domain_template: str | None = None,
) -> tuple[str, list[str]]:
    """Pull protected sections from skills/<name>/v*.md if still missing."""
    all_merged: list[str] = []
    version_dir = skill_md_path.parent
    if not version_dir.is_dir():
        return body, all_merged
    for vpath in sorted(version_dir.glob("v*.md"), reverse=True):
        try:
            raw = vpath.read_text(encoding="utf-8")
            old_body = raw.split("---", 2)[-1].strip() if raw.startswith("---") else raw
            body, names = merge_protected_sections(
                old_body, body, domain_template=domain_template,
            )
            all_merged.extend(names)
        except Exception:
            continue
    return body, all_merged


def _is_junk_section(heading: str, text: str) -> bool:
    if heading.lower() in {a.lower() for a in _PARAM_SECTION_ALIASES}:
        if "参数抽象度评委" in text or "改进后 `S_params`" in text:
            return True
    for pattern in _JUNK_SECTION_PATTERNS:
        if re.search(pattern, heading, re.IGNORECASE):
            return True
    if heading.startswith("#") and not heading.startswith("##"):
        return True
    return False


def _dedupe_s_body_intro(text: str) -> str:
    return re.sub(
        r"(Follow these steps in order\. Ask the user if anything is marked \[待确认\]\.\s*)+",
        "Follow these steps in order. Ask the user if anything is marked [待确认].\n\n",
        text,
    )


def _has_params_section(sections: list[tuple[str, str]]) -> bool:
    return any(h.lower() == "s_params" for h, t in sections if len(t.strip()) >= 40)


def sanitize_skill_body(
    body: str,
    *,
    domain_template: str | None = None,
) -> tuple[str, list[str]]:
    """Remove junk sections, ensure S_params, dedupe S_body boilerplate."""
    actions: list[str] = []
    preamble, sections = split_h2_sections(body)
    if not sections:
        return body, actions

    kept: list[tuple[str, str]] = []
    for heading, text in sections:
        if _is_junk_section(heading, text):
            actions.append(f"removed:{heading[:40]}")
            continue
        hl = heading.lower()
        if hl in {a.lower() for a in _PARAM_SECTION_ALIASES}:
            if "参数抽象度评委" in text:
                actions.append("removed:junk_inputs")
                continue
            if hl != "s_params":
                kept.append(("S_params", text))
                actions.append(f"renamed:{heading}->S_params")
                continue
        if hl == "s_body":
            text = _dedupe_s_body_intro(text)
        kept.append((heading, text))

    if not _has_params_section(kept):
        tpl = DOMAIN_S_PARAMS_TEMPLATES.get(domain_template or "")
        if tpl:
            insert_at = _trigger_insert_index(kept)
            kept.insert(insert_at, ("S_params", tpl.strip()))
            actions.append("inserted:S_params_template")

    parts = [preamble] if preamble else []
    for heading, text in kept:
        parts.append(f"## {heading}\n{text}")
    return "\n\n".join(parts).strip() + "\n", actions


def ensure_domain_s_params(body: str, *, domain_template: str | None = None) -> tuple[str, bool]:
    """Insert domain S_params table when section missing or too short."""
    _, sections = split_h2_sections(body)
    if _has_params_section(sections):
        return body, False
    tpl = DOMAIN_S_PARAMS_TEMPLATES.get(domain_template or "")
    if not tpl:
        return body, False
    preamble, sections = split_h2_sections(body)
    insert_at = _trigger_insert_index(sections)
    sections.insert(insert_at, ("S_params", tpl.strip()))
    parts = [preamble] if preamble else []
    for heading, text in sections:
        parts.append(f"## {heading}\n{text}")
    return "\n\n".join(parts).strip() + "\n", True


def normalize_skill_body(body: str) -> str:
    """Ensure canonical S_body / S_route / S_trigger headings for DNA compliance."""
    preamble, sections = split_h2_sections(body)
    if not sections:
        return body

    headings = [h for h, _ in sections]
    heading_lower = {h.lower(): h for h in headings}

    def _rename_section(old_names: tuple[str, ...], new_name: str) -> None:
        nonlocal sections
        if any(h.lower() == new_name.lower() for h, _ in sections):
            return
        for old in old_names:
            ol = old.lower()
            if ol in heading_lower:
                sections = [
                    (new_name if h.lower() == ol else h, text)
                    for h, text in sections
                ]
                return

    _rename_section(("Instructions", "执行步骤", "操作流程", "操作步骤"), "S_body")
    _rename_section(("Decision routes", "决策路由"), "S_route")
    _rename_section(("When to use",), "S_trigger")
    _rename_section(("Inputs", "Input", "Parameters"), "S_params")

    # Collapse duplicate S_params headings (keep first substantive block).
    seen_params = False
    deduped: list[tuple[str, str]] = []
    for heading, text in sections:
        if heading.lower() == "s_params":
            if seen_params and len(text) < 80:
                continue
            seen_params = True
        deduped.append((heading, text))
    sections = deduped

    parts = [preamble] if preamble else []
    for heading, text in sections:
        parts.append(f"## {heading}\n{text}")
    return "\n\n".join(parts).strip() + "\n"


def apply_structure_pipeline(
    name: str,
    body: str,
    *,
    skill_md_path: Path | None = None,
    old_body: str | None = None,
    domain_template: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Normalize structure and merge heritage blocks before save."""
    meta: dict[str, Any] = {"heritage_merged": []}
    body, sanitized = sanitize_skill_body(body, domain_template=domain_template)
    if sanitized:
        meta["sanitized"] = sanitized
    if old_body:
        body, merged = merge_protected_sections(
            old_body, body, domain_template=domain_template,
        )
        meta["heritage_merged"].extend(merged)
    if skill_md_path is not None:
        body, archived = merge_from_version_archives(
            name, body, skill_md_path, domain_template=domain_template,
        )
        meta["heritage_merged"].extend(archived)
    body, templated = apply_domain_heritage_templates(body, domain_template=domain_template)
    meta["heritage_merged"].extend(templated)
    body, params_added = ensure_domain_s_params(body, domain_template=domain_template)
    if params_added:
        meta["heritage_merged"].append("S_params")
    body = normalize_skill_body(body)
    meta["normalized"] = True
    return body, meta
