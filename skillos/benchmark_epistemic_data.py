"""Curated claim dataset for epistemic ablation (Phase 2).

Labels:
  true                 — factual methodology, should trust in skill hard rules
  false                — incorrect / misleading, should NOT trust
  opinion              — subjective preference, classify as preference
  needs_corroboration  — valid only with ≥2 independent sources
"""

from __future__ import annotations

DOMAINS = ("code_review", "incident", "onboarding", "security", "data", "general")


def build_claims_dataset() -> list[dict]:
    """Build 100 labeled claims (30/30/20/20 split)."""
    claims: list[dict] = []
    n = 0

    def add(content: str, label: str, domain: str, source_type: str = "url_content") -> None:
        nonlocal n
        n += 1
        claims.append({
            "id": f"bench_{n:03d}",
            "content": content,
            "label": label,
            "domain": domain,
            "source_type": source_type,
        })

    true_templates = [
        ("代码审查前必须先阅读 PR 描述和关联 Issue，缺少上下文不应开始审查", "code_review"),
        ("生产事故响应应先止血恢复服务，再进行根因分析", "incident"),
        ("客户入职流程应包含身份验证、需求收集和培训跟进三个阶段", "onboarding"),
        ("发现安全漏洞时代码审查应标记为阻塞并立即通知负责人", "code_review"),
        ("事故复盘报告应在恢复后 24 小时内完成并记录时间线", "incident"),
        ("代码审查必须检查边界条件、空值处理和异常分支", "code_review"),
        ("P0 事故定义为面向用户的核心功能完全不可用", "incident"),
        ("新用户验证邮件 48 小时未响应应转入人工跟进队列", "onboarding"),
        ("审查反馈应具体说明问题、原因和建议修改方式", "code_review"),
        ("回滚是线上故障最常见的低风险止血手段之一", "incident"),
        ("SQL 查询必须使用参数化语句以防止注入攻击", "security"),
        ("密钥和密码不得硬编码在源代码或技能文档中", "security"),
        ("数据导入失败时应保留已成功部分并通知客户失败详情", "onboarding"),
        ("审查大型 PR 超过 400 行时应要求作者拆分变更", "code_review"),
        ("监控错误率、延迟和吞吐量是验证恢复的有效指标", "incident"),
        ("2FA 设置超时应发送提醒并在用户跳过后记录审计日志", "onboarding"),
        ("变更部署后应持续监控至少 15 分钟确认无新问题", "incident"),
        ("测试必须覆盖 happy path、边界条件和错误路径", "code_review"),
        ("权限最小化原则要求按角色分配最小必要访问权限", "security"),
        ("客户培训拒绝时应提供录播教程并标记自助学习", "onboarding"),
        ("日志中不得记录完整信用卡号或明文密码", "security"),
        ("审查结论应区分阻塞问题、建议修改和风格问题", "code_review"),
        ("事故期间禁止在未备份状态下执行未知风险的止血操作", "incident"),
        ("需求未收集完成时不应开始账户默认配置", "onboarding"),
        ("依赖项漏洞扫描应纳入发布前检查清单", "security"),
        ("Postmortem 必须包含影响范围、根因和可执行改进项", "incident"),
        ("代码审查不应由作者本人对自己变更做最终批准", "code_review"),
        ("数据导出应提供字段映射说明和格式样例文件", "data"),
        ("敏感操作应记录操作者、时间和变更内容用于审计", "security"),
        ("第 7 天客户跟进无回复时 24 小时后应再次联系", "onboarding"),
    ]
    for text, domain in true_templates:
        add(text, "true", domain)

    false_templates = [
        ("代码审查时可以直接跳过测试检查以节省时间", "code_review"),
        ("生产事故第一时间应深入调试根因而不是先恢复服务", "incident"),
        ("所有 PR 都可以由作者自己审查并合并无需他人参与", "code_review"),
        ("P2 小故障可以等下周再处理即使客户完全无法使用", "incident"),
        ("新用户无需身份验证即可开通完整生产权限", "onboarding"),
        ("SQL 拼接字符串在内部系统中绝对安全无需参数化", "security"),
        ("密钥写在配置文件并提交到 Git 是团队标准做法", "security"),
        ("事故恢复后无需复盘因为问题已经解决", "incident"),
        ("代码审查只需看 happy path 边界条件可以忽略", "code_review"),
        ("数据导入失败时应静默忽略不通知客户", "onboarding"),
        ("监控指标在事故期间不重要可以事后补看", "incident"),
        ("2FA 应强制所有用户启用且不允许任何例外", "onboarding"),
        ("审查反馈写「这里不对」就足够无需具体建议", "code_review"),
        ("回滚总是比重启服务风险更高应避免使用", "incident"),
        ("所有依赖项漏洞都可以等到年度统一升级", "security"),
        ("培训必须线下进行录播教程完全无效", "onboarding"),
        ("日志应记录用户完整密码以便客服协助排查", "security"),
        ("大型 PR 审查时越快越好无需拆分", "code_review"),
        ("部署后无需监控因为 CI 已通过", "incident"),
        ("客户未回答需求问卷时随机配置即可无需跟进", "onboarding"),
        ("代码风格问题与逻辑错误严重性相同都应阻塞合并", "code_review"),
        ("事故期间可以同时尝试三种未验证止血方案以加快速度", "incident"),
        ("公开 API 无需鉴权只要内网调用即可", "security"),
        ("数据迁移失败应删除已导入部分重新开始", "data"),
        ("审查时只需看 diff 不必阅读关联需求文档", "code_review"),
        ("Postmortem 应找出责任人并处罚以杜绝再犯", "incident"),
        ("新用户注册后应立即授予管理员权限以提升体验", "onboarding"),
        ("所有第三方库都可直接使用无需许可证审查", "security"),
        ("测试覆盖率 100% 意味着代码绝对没有逻辑 bug", "code_review"),
        ("客户反馈差评可忽略因为只是个别用户意见", "onboarding"),
    ]
    for text, domain in false_templates:
        add(text, "false", domain)

    opinion_templates = [
        ("我觉得代码审查应该先看风格再看逻辑因为可读性最重要", "code_review"),
        ("我个人偏好事故响应时先打电话再查监控", "incident"),
        ("我习惯用英文写审查评论因为看起来更专业", "code_review"),
        ("I prefer concise postmortem documents under one page", "incident"),
        ("我喜欢客户培训用轻松口语而不是正式文档", "onboarding"),
        ("我认为 P1 和 P2 可以合并处理以简化流程", "incident"),
        ("我偏好审查时先运行自动化工具再看人工逻辑", "code_review"),
        ("我觉得 2FA 可选因为会降低注册转化率", "onboarding"),
        ("个人习惯把密钥放在 .env 并分享给团队成员", "security"),
        ("我更喜欢 Slack 通知而不是邮件发送验证链接", "onboarding"),
        ("我认为代码审查不需要写原因只要指出错误即可", "code_review"),
        ("我习惯事故期间同时修改代码和配置以加快修复", "incident"),
        ("I like onboarding calls to be 60 minutes instead of 30", "onboarding"),
        ("我觉得数据导入错误可以留给客户自己修复", "data"),
        ("个人偏好审查时跳过单元测试只看集成测试", "code_review"),
        ("我认为复盘文档越长越好细节越多越好", "incident"),
        ("我喜欢用红色标记所有审查意见以引起注意", "code_review"),
        ("我觉得新用户培训可以省略直接看文档", "onboarding"),
        ("I prefer to disable security scans for faster builds", "security"),
        ("我认为客户预算问题不必在入职阶段询问", "onboarding"),
    ]
    for text, domain in opinion_templates:
        add(text, "opinion", domain)

    corroboration_templates = [
        ("在 Google SRE 实践中事故应先恢复服务再排查根因", "incident"),
        ("OWASP 建议对所有 SQL 查询使用参数化绑定", "security"),
        ("IEEE 软件审查标准强调审查前需理解需求上下文", "code_review"),
        ("NIST 建议多因素认证用于高敏感账户访问", "security"),
        ("DevOps 手册推荐部署后持续监控关键 SLI 指标", "incident"),
        ("ISO 27001 要求对敏感数据访问保留审计日志", "security"),
        ("代码审查最佳实践要求测试覆盖边界和异常路径", "code_review"),
        ("SaaS 入职研究指出第 7 天跟进显著降低早期流失", "onboarding"),
        ("Kubernetes 运维指南建议变更失败时优先回滚", "incident"),
        ("PCI DSS 禁止在日志中存储完整持卡人数据", "security"),
        ("Blameless postmortem 文化强调改进而非追责", "incident"),
        ("敏捷团队通常要求他人审查后才能合并主分支", "code_review"),
        ("GDPR 相关流程要求验证用户身份后再开通数据访问", "onboarding"),
        ("依赖项安全扫描应集成到 CI 而非仅年度检查", "security"),
        ("大型变更审查建议拆分为小于 400 行的 PR", "code_review"),
        ("事故分级 P0 通常定义为核心用户功能完全不可用", "incident"),
        ("客户数据导入应支持部分成功并报告失败行", "data"),
        ("审查反馈应包含可执行的具体修改建议", "code_review"),
        ("生产变更应在低峰期部署并保留快速回滚能力", "incident"),
        ("新用户验证超时后应进入人工审核而非自动开通", "onboarding"),
    ]
    for text, domain in corroboration_templates:
        add(text, "needs_corroboration", domain)

    assert len(claims) == 100, f"expected 100 claims, got {len(claims)}"
    return claims
