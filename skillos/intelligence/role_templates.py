"""Role-based skill & MetaSkill template recommendations (Phase 4 extension)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetaSkillBlueprint:
    name: str
    goal: str
    steps: list[dict] = field(default_factory=list)

    def to_mermaid(self) -> str:
        from skillos.skills.metaskill import PipelineStep, pipeline_to_mermaid

        parsed = [
            PipelineStep(
                name=s["name"],
                skill_name=s["skill_name"],
                depends_on=s.get("depends_on", []),
                output_key=s.get("output_key", ""),
            )
            for s in self.steps
        ]
        return pipeline_to_mermaid(parsed)


@dataclass
class RoleTemplate:
    role_id: str
    title: str
    description: str
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    metaskill: MetaSkillBlueprint | None = None


ROLE_TEMPLATES: list[RoleTemplate] = [
    RoleTemplate(
        role_id="customer_service",
        title="客服 / 售后",
        description="退款、工单、CRM 查询与回复类技能组合",
        categories=["customer-service", "operations", "other"],
        keywords=["退款", "工单", "客服", "CRM", "售后", "投诉"],
        metaskill=MetaSkillBlueprint(
            name="客服标准流水线",
            goal="从工单接入到回复客户的完整流程",
            steps=[
                {"name": "ticket_intake", "skill_name": "工单接入", "output_key": "ticket"},
                {"name": "policy_check", "skill_name": "退款政策核查", "depends_on": ["ticket_intake"]},
                {"name": "crm_lookup", "skill_name": "CRM 查询", "depends_on": ["ticket_intake"], "output_key": "customer"},
                {"name": "reply_draft", "skill_name": "回复生成", "depends_on": ["policy_check", "crm_lookup"]},
            ],
        ),
    ),
    RoleTemplate(
        role_id="engineering",
        title="研发 / 工程",
        description="代码审查、发布检查、 incident 响应",
        categories=["development", "devops", "other"],
        keywords=["代码", "审查", "发布", "CI", "测试", "安全"],
        metaskill=MetaSkillBlueprint(
            name="研发交付流水线",
            goal="从代码变更到可发布验证",
            steps=[
                {"name": "code_scan", "skill_name": "代码安全扫描", "output_key": "scan_result"},
                {"name": "review", "skill_name": "代码审查", "depends_on": ["code_scan"]},
                {"name": "release_check", "skill_name": "发布检查清单", "depends_on": ["review"]},
            ],
        ),
    ),
    RoleTemplate(
        role_id="operations",
        title="运营",
        description="活动配置、数据报表、内容审核",
        categories=["operations", "marketing", "other"],
        keywords=["运营", "活动", "报表", "审核", "投放"],
        metaskill=MetaSkillBlueprint(
            name="运营活动流水线",
            goal="活动策划到上线前检查",
            steps=[
                {"name": "brief", "skill_name": "活动需求整理", "output_key": "brief"},
                {"name": "compliance", "skill_name": "合规审核", "depends_on": ["brief"]},
                {"name": "launch", "skill_name": "上线检查", "depends_on": ["compliance"]},
            ],
        ),
    ),
    RoleTemplate(
        role_id="legal",
        title="法务 / 合规",
        description="合同审核、条款比对、合规检查",
        categories=["legal", "operations", "other"],
        keywords=["合同", "法务", "合规", "条款", "审核", "协议", "风险"],
        metaskill=MetaSkillBlueprint(
            name="合同审核流水线",
            goal="从收稿到出具审核意见",
            steps=[
                {"name": "intake", "skill_name": "合同收稿登记", "output_key": "contract"},
                {"name": "clause_check", "skill_name": "条款比对", "depends_on": ["intake"]},
                {"name": "risk_scan", "skill_name": "风险识别", "depends_on": ["clause_check"], "output_key": "risks"},
                {"name": "revise", "skill_name": "修改建议", "depends_on": ["risk_scan"]},
            ],
        ),
    ),
    RoleTemplate(
        role_id="finance",
        title="财务",
        description="对账、报销审核、发票处理",
        categories=["finance", "operations", "other"],
        keywords=["财务", "报销", "发票", "对账", "审批"],
    ),
    RoleTemplate(
        role_id="sales",
        title="销售",
        description="线索跟进、报价、合同要点核查",
        categories=["sales", "customer-service", "other"],
        keywords=["销售", "线索", "报价", "合同", "客户"],
    ),
]


def list_role_templates() -> list[dict]:
    return [
        {
            "role_id": r.role_id,
            "title": r.title,
            "description": r.description,
            "categories": r.categories,
            "keywords": r.keywords,
            "has_metaskill_blueprint": r.metaskill is not None,
        }
        for r in ROLE_TEMPLATES
    ]


def _score_skill_for_role(skill_name: str, skill_category: str, role: RoleTemplate) -> float:
    score = 0.0
    name_lower = skill_name.lower()
    cat = (skill_category or "other").lower()
    if cat in [c.lower() for c in role.categories]:
        score += 2.0
    for kw in role.keywords:
        if kw.lower() in name_lower or kw in skill_name:
            score += 1.5
    return score


def recommend_for_role(role_id: str, *, tenant=None, limit: int = 8) -> dict:
    """Match marketplace catalog + tenant MetaSkills to a role template."""
    role = next((r for r in ROLE_TEMPLATES if r.role_id == role_id), None)
    if not role:
        raise LookupError(role_id)

    from skillos.marketplace.registry import list_skills as list_market
    from skillos.skills.skill_store import list_skills as list_tenant, load_skill_raw

    catalog: list[dict] = []
    for skill in list_market(status="approved", sort_by="score"):
        pts = _score_skill_for_role(skill.name, skill.category, role)
        if pts <= 0 and skill.score < 60:
            continue
        pts += skill.score / 100.0
        d = skill.to_dict()
        d.pop("content", None)
        d["match_score"] = round(pts, 2)
        d["source"] = "marketplace"
        catalog.append(d)

    catalog.sort(key=lambda x: x["match_score"], reverse=True)

    tenant_items: list[dict] = []
    if tenant is not None:
        for name in list_tenant(tenant=tenant):
            try:
                raw = load_skill_raw(name, tenant=tenant)
            except FileNotFoundError:
                continue
            meta = raw.get("meta") or {}
            body = raw.get("body") or ""
            is_meta = meta.get("type") == "metaskill" or "type: metaskill" in body[:200]
            pts = _score_skill_for_role(name, meta.get("category", "other"), role)
            if is_meta:
                pts += 3.0
            if pts <= 0:
                continue
            tenant_items.append(
                {
                    "name": name,
                    "type": "metaskill" if is_meta else "skill",
                    "match_score": round(pts, 2),
                    "source": "tenant",
                }
            )
        tenant_items.sort(key=lambda x: x["match_score"], reverse=True)

    blueprint = None
    if role.metaskill:
        blueprint = {
            "name": role.metaskill.name,
            "goal": role.metaskill.goal,
            "steps": role.metaskill.steps,
            "mermaid": role.metaskill.to_mermaid(),
        }

    return {
        "role_id": role.role_id,
        "title": role.title,
        "description": role.description,
        "catalog_skills": catalog[:limit],
        "tenant_skills": tenant_items[:limit],
        "metaskill_blueprint": blueprint,
    }
