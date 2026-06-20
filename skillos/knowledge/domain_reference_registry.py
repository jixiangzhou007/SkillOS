"""Domain Reference Registry — authoritative data sources for each discipline.

Maps 12 disciplines to known authoritative references (laws, standards,
guidelines, key publications). These are pre-loaded during extraction
so the Socratic questioning can reference specific statutes/criteria.

Data directory: data/domain_references/{discipline_key}/
Each discipline gets a REFERENCES.md listing sources and their URLs.
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
REF_DIR = ROOT / "data" / "domain_references"


@dataclass
class AuthoritySource:
    """A known authoritative reference source for a discipline."""
    title: str
    url: str = ""
    category: str = ""  # "law" | "standard" | "guideline" | "textbook"
    language: str = "zh"
    notes: str = ""


# ── 12-Discipline Authoritative Source Registry ─────────

DOMAIN_REFERENCES: dict[str, list[AuthoritySource]] = {
    "computer-science": [
        AuthoritySource("ISO/IEC 25010 软件质量模型", "https://www.iso.org/standard/35733.html", "standard"),
        AuthoritySource("IEEE 829 测试文档标准", "https://standards.ieee.org/standard/829-2008.html", "standard"),
        AuthoritySource("ACM 伦理准则", "https://www.acm.org/code-of-ethics", "guideline"),
        AuthoritySource("OWASP Top 10 安全风险", "https://owasp.org/www-project-top-ten/", "guideline"),
        AuthoritySource("Google 工程实践指南", "https://google.github.io/eng-practices/", "guideline"),
    ],
    "medicine-health": [
        AuthoritySource("NICE 临床指南 (UK)", "https://www.nice.org.uk/guidance", "guideline"),
        AuthoritySource("WHO 基本药物清单", "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023", "guideline"),
        AuthoritySource("JCI 医院认证标准", "https://www.jointcommissioninternational.org/", "standard"),
        AuthoritySource("中华人民共和国药典", "https://www.chp.org.cn/", "standard", "zh"),
        AuthoritySource("临床诊疗指南 (中华医学会)", "https://www.cma.org.cn/", "guideline", "zh"),
    ],
    "management-science": [
        AuthoritySource("ISO 9001 质量管理体系", "https://www.iso.org/standard/62085.html", "standard"),
        AuthoritySource("PMBOK 项目管理指南 (PMI)", "https://www.pmi.org/pmbok-guide-standards", "standard"),
        AuthoritySource("ISO 31000 风险管理", "https://www.iso.org/standard/65694.html", "standard"),
        AuthoritySource("平衡计分卡 (Kaplan & Norton)", "", "textbook"),
        AuthoritySource("精益六西格玛 (Lean Six Sigma)", "", "guideline"),
    ],
    "law": [
        AuthoritySource("中华人民共和国民法典", "https://flk.npc.gov.cn/", "law", "zh"),
        AuthoritySource("中华人民共和国公司法", "https://flk.npc.gov.cn/", "law", "zh"),
        AuthoritySource("中华人民共和国劳动合同法", "https://flk.npc.gov.cn/", "law", "zh"),
        AuthoritySource("最高人民法院司法解释", "https://www.court.gov.cn/", "law", "zh"),
        AuthoritySource("ISO 37301 合规管理体系", "https://www.iso.org/standard/75080.html", "standard"),
        AuthoritySource("GDPR (EU 通用数据保护条例)", "https://gdpr.eu/", "law"),
    ],
    "economics-finance": [
        AuthoritySource("IFRS 国际财务报告准则", "https://www.ifrs.org/", "standard"),
        AuthoritySource("中国会计准则 (CAS)", "https://www.casc.org.cn/", "standard", "zh"),
        AuthoritySource("中国注册会计师审计准则", "https://www.cicpa.org.cn/", "standard", "zh"),
        AuthoritySource("SOX 萨班斯法案 (US)", "https://www.sec.gov/spotlight/sarbanes-oxley.htm", "law"),
        AuthoritySource("Basel III 银行监管框架", "https://www.bis.org/bcbs/basel3.htm", "standard"),
    ],
    "education": [
        AuthoritySource("Bloom 教育目标分类学", "", "textbook"),
        AuthoritySource("Kirkpatrick 四级评估模型", "", "textbook"),
        AuthoritySource("UNESCO 教育2030框架", "https://www.unesco.org/en/education2030", "guideline"),
        AuthoritySource("中国教师教育课程标准", "https://www.moe.gov.cn/", "standard", "zh"),
        AuthoritySource("ADDIE 教学设计模型", "", "guideline"),
    ],
    "design": [
        AuthoritySource("WCAG 2.2 无障碍标准", "https://www.w3.org/TR/WCAG22/", "standard"),
        AuthoritySource("Nielsen 十大可用性启发式", "https://www.nngroup.com/articles/ten-usability-heuristics/", "guideline"),
        AuthoritySource("ISO 9241 人机交互标准", "https://www.iso.org/standard/77520.html", "standard"),
        AuthoritySource("Material Design 3 (Google)", "https://m3.material.io/", "guideline"),
        AuthoritySource("Human Interface Guidelines (Apple)", "https://developer.apple.com/design/human-interface-guidelines/", "guideline"),
    ],
    "engineering": [
        AuthoritySource("ISO 9001 质量管理", "https://www.iso.org/standard/62085.html", "standard"),
        AuthoritySource("ISO 45001 职业健康安全", "https://www.iso.org/standard/63787.html", "standard"),
        AuthoritySource("GB 50656 施工安全标准", "https://www.mohurd.gov.cn/", "standard", "zh"),
        AuthoritySource("JGJ 59 建筑施工安全检查标准", "https://www.mohurd.gov.cn/", "standard", "zh"),
        AuthoritySource("安全生产法 (2021修订)", "https://flk.npc.gov.cn/", "law", "zh"),
        AuthoritySource("AQL 抽样检验标准 (ANSI/ASQ Z1.4)", "", "standard"),
    ],
    "natural-science": [
        AuthoritySource("ISO 17025 实验室能力通用要求", "https://www.iso.org/standard/66912.html", "standard"),
        AuthoritySource("CONSORT 随机试验报告规范", "https://www.consort-statement.org/", "guideline"),
        AuthoritySource("ARRIVE 动物实验报告指南", "https://arriveguidelines.org/", "guideline"),
        AuthoritySource("CODATA 数据引用标准", "https://www.codata.org/", "standard"),
        AuthoritySource("PRISMA 系统综述指南", "https://www.prisma-statement.org/", "guideline"),
    ],
    "social-science": [
        AuthoritySource("AAPOR 调研标准", "https://aapor.org/standards-and-ethics/", "standard"),
        AuthoritySource("APA 心理学出版手册 (第7版)", "https://apastyle.apa.org/", "standard"),
        AuthoritySource("ESOMAR 市场研究准则", "https://esomar.org/codes-and-guidelines", "guideline"),
        AuthoritySource("OECD 社会指标框架", "https://www.oecd.org/social/", "guideline"),
        AuthoritySource("中国社会调查标准 (CSSC)", "", "standard", "zh"),
    ],
    "journalism-communication": [
        AuthoritySource("AP Stylebook", "https://www.apstylebook.com/", "standard"),
        AuthoritySource("SPJ 职业记者伦理准则", "https://www.spj.org/ethicscode.asp", "guideline"),
        AuthoritySource("路透社新闻手册", "https://www.reuters.com/handbook-of-journalism/", "guideline"),
        AuthoritySource("BBC 编辑指南", "https://www.bbc.co.uk/editorialguidelines/", "guideline"),
        AuthoritySource("中国新闻工作者职业道德准则", "", "guideline", "zh"),
    ],
    "agriculture": [
        AuthoritySource("GlobalG.A.P. 良好农业规范", "https://www.globalgap.org/", "standard"),
        AuthoritySource("USDA Organic 有机认证标准", "https://www.usda.gov/topics/organic", "standard"),
        AuthoritySource("EU Organic 有机认证 (EC 834/2007)", "https://ec.europa.eu/agriculture/organic/", "standard"),
        AuthoritySource("GB 15618 土壤环境质量标准", "https://www.mee.gov.cn/", "standard", "zh"),
        AuthoritySource("GB 2763 食品中农药残留限量", "https://www.nhc.gov.cn/", "standard", "zh"),
        AuthoritySource("FAO 食品安全指南", "https://www.fao.org/food-safety/", "guideline"),
    ],
}


def get_domain_references(discipline_key: str) -> list[AuthoritySource]:
    """Get authoritative references for a discipline."""
    return DOMAIN_REFERENCES.get(discipline_key, [])


def build_reference_context(discipline_key: str) -> str:
    """Build a context string of authoritative references for extraction prompts."""
    refs = get_domain_references(discipline_key)
    if not refs:
        return ""

    lines = ["\n## 📚 领域权威参考资料\n"]
    lines.append("在萃取过程中，可以引用以下权威来源来验证步骤的合规性：\n")
    for r in refs:
        cat_icon = {"law": "⚖️", "standard": "📐", "guideline": "📋", "textbook": "📖"}.get(r.category, "📌")
        url = f" ({r.url})" if r.url else ""
        lines.append(f"- {cat_icon} **{r.title}**{url}")
    return "\n".join(lines)


def ensure_reference_dirs() -> None:
    """Create data/domain_references/ directory structure for all 12 disciplines."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    for key in DOMAIN_REFERENCES:
        (REF_DIR / key).mkdir(exist_ok=True)
        refs_md = REF_DIR / key / "REFERENCES.md"
        if not refs_md.exists():
            lines = [f"# {key} — 权威参考资料\n"]
            for r in DOMAIN_REFERENCES[key]:
                url = f" ({r.url})" if r.url else ""
                lines.append(f"- {r.title}{url} [{r.category}]")
            refs_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _log.info("Domain reference directories ready: %d disciplines", len(DOMAIN_REFERENCES))
