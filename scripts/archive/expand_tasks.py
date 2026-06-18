"""Expand skillsbench_tasks.py from 22 to 100 tasks."""
import re

with open("skillos/skillsbench_tasks.py", "r", encoding="utf-8") as f:
    content = f.read()

# 78 new tasks as Python code string
new_tasks = []

def t(task_id, category, description, input_data, grading, expected, forbidden=None):
    """Generate one SkillBenchTask entry."""
    fb = forbidden or []
    fb_str = ", " + repr(fb) if fb else ""
    return f'    SkillBenchTask(\n        task_id="{task_id}",\n        category="{category}",\n        description="{description}",\n        input_data={repr(input_data)},\n        grading={repr(grading)},\n        expected={repr(expected)}{fb_str},\n    )'

# ── Code Review (10 new) ──
new_tasks.append(t("code-review-xss", "code-review", "审查一段有XSS漏洞的前端代码", {"code": '<div onclick="alert(1)">{userInput}</div>', "language": "javascript"}, {"security": {"weight": 50, "must_match": True}, "actionability": {"weight": 50, "must_match": True}}, ["XSS|xss|跨站", "转义|escape|sanitize|过滤", "innerHTML|textContent|createElement"]))
new_tasks.append(t("code-review-race-condition", "code-review", "审查一段有竞态条件的并发代码", {"code": "def transfer(a,b,amt):\n  a.balance-=amt\n  b.balance+=amt", "language": "python"}, {"correctness": {"weight": 60, "must_match": True}, "actionability": {"weight": 40, "must_match": True}}, ["锁|lock|mutex|加锁", "事务|transaction|atomic", "并发|concurrent|race"]))
new_tasks.append(t("code-review-resource-leak", "code-review", "审查一段资源泄漏的代码", {"code": "def read_file(path):\n  f=open(path)\n  return f.read()", "language": "python"}, {"correctness": {"weight": 50, "must_match": True}, "actionability": {"weight": 50, "must_match": True}}, ["with|close|finally|上下文管理|context manager", "泄漏|leak"]))
new_tasks.append(t("code-review-hardcoded-secret", "code-review", "审查一段包含硬编码密钥的代码", {"code": "API_KEY='sk-abc123xyz456'\ndef call_api():\n  headers={'Authorization':f'Bearer {API_KEY}'}", "language": "python"}, {"security": {"weight": 60, "must_match": True}, "actionability": {"weight": 40, "must_match": True}}, ["硬编码|hardcoded", "环境变量|env|os.environ|secret", "泄露|leak|移除|删除"]))
new_tasks.append(t("code-review-unhandled-error", "code-review", "审查一段缺少错误处理的代码", {"code": "def process(order):\n  price=order['items'][0]['price']\n  return price*1.1", "language": "python"}, {"correctness": {"weight": 50, "must_match": True}, "completeness": {"weight": 50, "must_match": True}}, ["KeyError|TypeError|异常|try|except", "空|None|null.*检查", "default|默认|fallback"]))
new_tasks.append(t("code-review-nplus1", "code-review", "审查一段有N+1查询问题的ORM代码", {"code": "for user in User.objects.all():\n  print(user.profile.avatar)", "language": "python"}, {"correctness": {"weight": 50, "must_match": True}, "performance": {"weight": 50, "must_match": True}}, ["select_related|prefetch|join|N\\+1|n\\+1", "性能|performance|优化|批量查询"]))
new_tasks.append(t("code-review-infinite-loop", "code-review", "审查一段可能导致无限循环的代码", {"code": "while data:=fetch():\n  if not data.valid:\n    continue\n  process(data)", "language": "python"}, {"correctness": {"weight": 60, "must_match": True}, "robustness": {"weight": 40, "must_match": True}}, ["无限循环|infinite loop|死循环", "超时|timeout|max_iter|重试.*上限|break"]))
new_tasks.append(t("code-review-buffer-overflow", "code-review", "审查一段缓冲区溢出的C代码", {"code": "void copy_name(char* dest, char* src) { strcpy(dest, src); }", "language": "c"}, {"security": {"weight": 60, "must_match": True}, "actionability": {"weight": 40, "must_match": True}}, ["strncpy|strlcpy|边界|长度.*检查|overflow", "sizeof|strlen.*限制|n"]))
new_tasks.append(t("code-review-unsafe-deserialize", "code-review", "审查一段不安全的反序列化代码", {"code": "import pickle; data=pickle.loads(user_input)", "language": "python"}, {"security": {"weight": 60, "must_match": True}, "actionability": {"weight": 40, "must_match": True}}, ["pickle.*不安全|unsafe|json|替代", "反序列化|deserializ", "验证|validate|输入.*检查"]))
new_tasks.append(t("code-review-time-complexity", "code-review", "审查一段可优化时间复杂度的算法", {"code": "def find_duplicates(arr):\n  return [x for i,x in enumerate(arr) if x in arr[:i]]", "language": "python"}, {"correctness": {"weight": 50, "must_match": True}, "performance": {"weight": 50, "must_match": True}}, ["O\\(n\\^2\\)|O\\(n\\)|set|hash|字典|dict", "优化|性能|complexity"]))

# ── Data Processing (21 new) ──
new_tasks.append(t("data-merge-join", "data-processing", "合并两个CSV数据集并按key去重", {"table_a": "id,name\n1,Alice\n2,Bob", "table_b": "id,score\n1,95\n3,88", "key": "id"}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["merge|join|合并|连接", "inner|outer|left.*join|how", "去重|重复|drop_duplicate"]))
new_tasks.append(t("data-groupby-agg", "data-processing", "按部门分组计算平均工资和总人数", {"data": [{"dept":"ENG","salary":15000},{"dept":"ENG","salary":18000},{"dept":"SALES","salary":12000}]}, {"correctness": {"weight": 50, "must_match": True}, "completeness": {"weight": 50, "must_match": True}}, ["groupby|分组|group by", "mean|avg|平均", "count|人数|sum", "ENG.*16500|SALES.*12000"]))
new_tasks.append(t("data-pivot-table", "data-processing", "用数据透视表统计各区域各季度的销售额", {"data": [{"region":"North","q":"Q1","sales":100},{"region":"North","q":"Q2","sales":150},{"region":"South","q":"Q1","sales":200}]}, {"correctness": {"weight": 50, "must_match": True}, "structure": {"weight": 50, "must_match": True}}, ["pivot|透视|crosstab", "行.*列|index.*columns", "North.*Q1|South.*Q1"]))
new_tasks.append(t("data-outlier-detect", "data-processing", "用IQR方法检测异常值", {"values": [10,12,11,13,10,100,9,11,12,10]}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["IQR|四分位|quartile|箱线|boxplot", "Q1|Q3|25%|75%", "异常|outlier|100"]))
new_tasks.append(t("data-missing-impute", "data-processing", "对缺失值用中位数填充", {"data": [{"age":25},{"age":None},{"age":30},{"age":None},{"age":28}]}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["中位数|median", "填充|fillna|impute|fill", "缺失|null|None|NaN"]))
new_tasks.append(t("data-normalize", "data-processing", "将数据归一化到0-1区间", {"values": [10,20,30,40,50], "method": "min-max"}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["归一|normalize|min.max|0.*1", "standard|z.score|标准化", "sklearn|preprocessing"]))
new_tasks.append(t("data-text-cleaning", "data-processing", "清洗文本数据：去标点、统一小写、去停用词", {"texts": ["Hello, World!", "This is a TEST.", "Data-Science 101!"]}, {"correctness": {"weight": 40, "must_match": True}, "method": {"weight": 30, "must_match": True}, "completeness": {"weight": 30, "must_match": True}}, ["lower|小写|标点|punctuation|正则|regex|replace", "stopword|停用词", "strip|清洗|clean"]))
new_tasks.append(t("data-date-parsing", "data-processing", "解析多种日期格式并统一为ISO 8601", {"dates": ["2024/01/15", "01-15-2024", "2024-01-15", "Jan 15, 2024"]}, {"correctness": {"weight": 50, "must_match": True}, "robustness": {"weight": 50, "must_match": True}}, ["ISO|8601|parse|解析|datetime", "多种|multiple.*format", "统一|normalize|标准化"]))
new_tasks.append(t("data-json-flatten", "data-processing", "展平嵌套JSON为表格", {"json": '{"user":{"name":"Alice","address":{"city":"Beijing","zip":"100000"}},"orders":[{"id":1},{"id":2}]}'}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["展平|flatten|嵌套|nested|json_normalize", "user.name|user_address|address.city"]))
new_tasks.append(t("data-validate-schema", "data-processing", "验证数据是否符合指定Schema类型", {"schema": {"name":"str","age":"int","email":"str"}, "data": [{"name":"Alice","age":"25","email":"a@t.com"},{"name":"Bob","age":30,"email":""}]}, {"correctness": {"weight": 50, "must_match": True}, "completeness": {"weight": 50, "must_match": True}}, ["类型|type.*check|validate|schema|校验", "int.*str|str.*int|类型.*错", "25.*不是.*int|30.*是.*int"]))
new_tasks.append(t("data-timeseries-resample", "data-processing", "对时间序列数据按周重采样并计算均值", {"data": "2024-01-01:100, 2024-01-03:120, 2024-01-08:150", "freq": "W"}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["resample|重采样|采样", "mean|均值|平均", "weekly|周|W"]))
new_tasks.append(t("data-correlation", "data-processing", "计算两个变量的皮尔逊相关系数", {"x": [1,2,3,4,5], "y": [2,4,6,8,10]}, {"correctness": {"weight": 60, "must_match": True}, "interpretation": {"weight": 40, "must_match": True}}, ["pearson|皮尔逊|correlation|相关系数|corr", "1\\.0|完全正相关|强.*相关|perfect"]))
new_tasks.append(t("data-encode-categorical", "data-processing", "对分类变量进行One-Hot编码", {"categories": ["red","blue","green","red","blue"]}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["one.hot|onehot|独热|get_dummies|编码|encode", "red.*blue.*green|3.*列|3.*column"]))
new_tasks.append(t("data-train-test-split", "data-processing", "将数据集按8:2分割为训练集和测试集", {"total": 1000, "split_ratio": 0.8, "seed": 42}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["split|分割|划分|train.*test", "800.*200|80%.*20%", "random_state|seed|随机"]))
new_tasks.append(t("data-feature-engineering", "data-processing", "从日期列提取年、月、日、星期几特征", {"date_column": ["2024-01-15","2024-06-30","2024-12-25"]}, {"correctness": {"weight": 50, "must_match": True}, "completeness": {"weight": 50, "must_match": True}}, ["year|年|month|月|day|日|weekday|星期", "特征|feature|extract", "dt\\.|datetime|parse"]))
new_tasks.append(t("data-aggregate-window", "data-processing", "计算滑动窗口的移动平均值", {"values": [10,15,12,18,20,14,16], "window": 3}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["滑动|rolling|窗口|window", "移动平均|moving.*average|mean", "NaN|空.*前"]))
new_tasks.append(t("data-concat-vertical", "data-processing", "纵向拼接两个相同结构的DataFrame", {"df1_cols": ["name","age"], "df2_cols": ["name","age"], "df1_rows": 100, "df2_rows": 50}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["concat|拼接|append|union", "axis.*0|纵向|垂直|行.*合并", "150.*行|150.*row"]))
new_tasks.append(t("data-fuzzy-dedup", "data-processing", "模糊去重：用相似度匹配找近似重复", {"names": ["Beijing","Bejing","Shanghai","Shanghi","Guangzhou"]}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["模糊|fuzzy|similarity|相似|levenshtein|编辑距离", "Bejing.*Beijing|Shanghi.*Shanghai", "阈值|threshold"]))
new_tasks.append(t("data-parse-log", "data-processing", "解析Apache日志提取IP、时间、状态码", {"log_line": '192.168.1.1 - - [15/Jan/2024:13:55:36 +0800] "GET /api/users HTTP/1.1" 200 1234'}, {"correctness": {"weight": 50, "must_match": True}, "completeness": {"weight": 50, "must_match": True}}, ["parse|解析|正则|regex|split", "IP|192\\.168|status|状态码|200", "时间|timestamp|datetime"]))
new_tasks.append(t("data-excel-multi-sheet", "data-processing", "读取Excel多Sheet并合并为一个DataFrame", {"file": "report.xlsx", "sheets": ["Q1","Q2","Q3","Q4"]}, {"correctness": {"weight": 50, "must_match": True}, "method": {"weight": 50, "must_match": True}}, ["Excel|excel|xlsx|sheet|read_excel", "concat|合并|merge.*sheet", "sheet_name|None.*all"]))
new_tasks.append(t("data-budget-variance", "data-processing", "计算预算执行偏差分析", {"budget": {"Q1":100,"Q2":120,"Q3":110,"Q4":150}, "actual": {"Q1":95,"Q2":130,"Q3":105,"Q4":140}}, {"correctness": {"weight": 60, "must_match": True}, "interpretation": {"weight": 40, "must_match": True}}, ["偏差|variance|差异|实际.*预算", "Q2.*超|Q2.*over|Q4.*不足|Q4.*under", "百分比|percent|%"]))
new_tasks.append(t("data-tax-calc", "data-processing", "计算含税价格和税额", {"amounts": [100,200,300], "tax_rate": 0.13}, {"correctness": {"weight": 60, "must_match": True}, "method": {"weight": 40, "must_match": True}}, ["13%|0\\.13|增值税|VAT|tax", "含税|不含税|net|gross", "113|226|339|13|26|39"]))
new_tasks.append(t("data-depreciation", "data-processing", "计算固定资产直线折旧表", {"asset_cost": 100000, "salvage": 5000, "years": 5, "method": "straight-line"}, {"correctness": {"weight": 60, "must_match": True}, "completeness": {"weight": 40, "must_match": True}}, ["折旧|depreciation|straight", "100000|5000|95000|19000", "残值|salvage|期限|useful.*life"]))
new_tasks.append(t("data-roi-calc", "data-processing", "计算ROI和回收期", {"investment": 500000, "annual_return": 120000, "years": 5}, {"correctness": {"weight": 60, "must_match": True}, "interpretation": {"weight": 40, "must_match": True}}, ["ROI|回报率|return.*investment", "24%|0\\.24", "回收期|payback|4\\.17|4\\.2"]))

# ── API Design (10 new) ──
for a_name, a_desc, a_input, a_grading, a_exp in [
    ("api-design-pagination", "为列表接口设计分页参数和响应格式", {"resource": "articles", "total": 1500}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["page|offset|cursor|游标","limit|size|per_page","next|previous|has_more|total"]),
    ("api-design-error-response", "设计统一的API错误响应格式", {"scenarios":["参数校验失败","资源不存在","权限不足","服务器内部错误"]}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["400|404|403|500","error.*code|error_code|status","message|detail|description"]),
    ("api-design-auth-header", "设计API认证方案和请求头规范", {"auth_type":"Bearer JWT","requirements":"支持token刷新和过期处理"}, {"correctness":{"weight":50,"must_match":True},"security":{"weight":50,"must_match":True}}, ["Bearer|Authorization|JWT","refresh|刷新|expire|过期","401|unauthorized"]),
    ("api-design-rate-limit", "设计API限流方案和响应头", {"limit":"100次/分钟","requirements":"超限返回429并带Retry-After头"}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["429|rate.*limit|限流|频率","Retry-After|X-RateLimit","100|窗口|window|sliding"]),
    ("api-design-versioning", "设计API版本管理策略", {"current_version":"v1","requirements":"URL路径版本 vs Header版本"}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["v1|v2|version|版本","URL.*版本|header.*版本|Accept","deprecat|废弃|兼容|compat"]),
    ("api-design-filter-sort", "设计列表接口的筛选排序参数", {"resource":"products","filters":["category","price_range","in_stock"],"sorts":["price","created_at","rating"]}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["filter|筛选|过滤|sort|排序","query.*param|查询参数|?.*=","asc|desc|order"]),
    ("api-design-file-upload", "设计文件上传API端点", {"file_types":["image","document"],"max_size":"10MB"}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["multipart|upload|上传|POST.*file","分片|chunk|resumable","进度|progress|Content-Type"]),
    ("api-design-webhook", "设计Webhook回调端点与签名验证", {"events":["order.created","order.paid","order.shipped"]}, {"correctness":{"weight":40,"must_match":True},"security":{"weight":60,"must_match":True}}, ["webhook|回调|callback","签名|signature|HMAC|SHA","secret|密钥|验证|verify"]),
    ("api-design-batch", "设计批量操作API端点", {"operations":["批量创建","批量更新","批量删除"]}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["batch|批量|bulk","partial|部分.*成功|原子|atomic","transaction|事务"]),
    ("api-design-search", "设计全文搜索API端点", {"resource":"articles","requirements":"关键词搜索+高亮+相关性排序+分面筛选"}, {"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["search|搜索|query|全文","highlight|高亮|facet|aggregation|聚合","relevance|score|相关性|排序"]),
]:
    new_tasks.append(t(a_name, "api-design", a_desc, a_input, a_grading, a_exp))

# ── Documentation (11 new) ──
for d_name, d_desc, d_input, d_grading, d_exp in [
    ("doc-readme-template", "为开源项目写README.md的标准章节结构", {"project":"SkillOS","language":"Python","audience":"AI developers"}, {"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}}, ["安装|install|pip|clone","使用|usage|quickstart|快速开始","API|文档|documentation","License|license|许可"]),
    ("doc-changelog-format", "按Keep a Changelog规范写版本变更记录", {"version":"2.0.0","changes":["新增MoE评价系统","修复SQL注入","废弃Python 3.8支持"]}, {"structure":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["Added|新增|添加","Fixed|修复|修正","Deprecated|废弃|弃用","Semantic Versioning|语义版本"]),
    ("doc-api-reference", "为一个REST端点写API参考文档", {"endpoint":"POST /api/users","request":{"name":"string","email":"email","role":"enum"},"response":{"id":"uuid","created_at":"iso8601"}}, {"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}}, ["Method|方法|POST","Parameters|参数|Request Body","Response|响应|返回","Example|示例|curl|请求示例","Error|错误|Status Code"]),
    ("doc-onboarding-guide", "写一份新员工入职的技术环境搭建指南", {"tools":["Git","Docker","VS Code","Python 3.12","PostgreSQL"],"os":["macOS","Windows","Linux"]}, {"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["Git|Docker|VS Code|Python","安装|install|配置|setup","验证|verify|检查.*版本|check","FAQ|问题|troubleshoot"]),
    ("doc-architecture-decision", "写一份架构决策记录(ADR)", {"decision":"选择PostgreSQL替代MongoDB作为主数据库","context":"需要强一致性事务支持和复杂查询","alternatives":["MongoDB","MySQL","CockroachDB"]}, {"structure":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}}, ["ADR|架构决策|decision","context|背景|上下文","decision|决定|选择","consequence|后果|影响|结果","alternatives|替代|备选"]),
    ("doc-release-checklist", "写一份生产发布检查清单", {"release_type":"major","services":["api-server","worker","frontend"],"stages":["staging","canary","production"]}, {"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["checklist|检查清单|checklist","回滚|rollback|回退","监控|monitor|告警|alert","数据库.*迁移|migration|备份|backup","staging|canary|灰度"]),
    ("doc-troubleshoot-guide", "写一份常见问题排查指南的目录", {"system":"电商平台","common_issues":["支付超时","库存不一致","用户登录失败","订单状态卡住"]}, {"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["症状|symptom|现象","原因|root.*cause|根因","解决方案|solution|fix|修复","验证|verify|确认"]),
    ("doc-code-comment-standard", "制定代码注释规范文档", {"language":"Python","style":"Google docstring","requirements":"函数/类/模块三级注释标准"}, {"completeness":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}}, ["docstring|文档字符串|注释","Args|参数|Parameters|Returns|返回","Example|示例|用法|usage","类型|type.*hint|typing"]),
    ("doc-migration-guide", "写一份数据库迁移操作手册", {"from":"MySQL 5.7","to":"MySQL 8.0","data_size":"500GB","downtime_limit":"30分钟"}, {"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["备份|backup|dump|mysqldump","迁移|migration|升级|upgrade","验证|verify|检查.*兼容|compat","回滚|rollback|回退","停机|downtime|窗口"]),
    ("doc-style-guide", "制定团队代码风格指南", {"language":"TypeScript","tools":["ESLint","Prettier"],"rules":"2空格缩进/单引号/分号必须/行宽100"}, {"completeness":{"weight":50,"must_match":True},"actionability":{"weight":50,"must_match":True}}, ["缩进|indent|空格|tab","引号|quotes|分号|semicolon","行宽|line.*width|max.*len","命名|naming|camelCase|PascalCase"]),
    ("doc-deploy-runbook", "写一份应用部署操作手册", {"app":"microservice","platform":"Kubernetes","stages":["build","push","deploy","verify"]}, {"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["build|构建|docker.*build","push|推送|registry","deploy|部署|kubectl|helm","verify|验证|health|readiness|curl","回滚|rollback|undo"]),
    ("doc-privacy-policy", "撰写隐私政策文档的必备章节", {"regulation":"个人信息保护法+GDPR","data_types":["姓名","手机号","浏览记录","位置"],"third_party":"广告SDK"}, {"structure":{"weight":30,"must_match":True},"compliance":{"weight":40,"must_match":True},"completeness":{"weight":30,"must_match":True}}, ["收集|collect|信息.*类型","目的|purpose|用途|使用","第三方|third.*party|共享|share","删除|delete|权利|right|撤回|withdraw","存储|storage|保留|retention","同意|consent|授权"]),
    ("doc-tos-template", "撰写服务条款的核心章节", {"service_type":"SaaS平台","key_clauses":["服务等级","费用与支付","知识产权","责任限制","争议解决"]}, {"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}}, ["服务|service|SLA|等级","费用|fee|payment|支付|价格","知识产权|IP|intellectual|版权|copyright","责任.*限制|liability|disclaimer|免责","管辖|jurisdiction|仲裁|arbitration"]),
    ("doc-nda-template", "撰写保密协议关键条款", {"parties":"甲方(披露方)与乙方(接收方)","confidential_info":"源代码+商业计划+客户名单","term":"3年保密期"}, {"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}}, ["保密|confidential|NDA","定义|definition|范围.*信息","义务|obligation|不得.*披露|限制","例外|exception|除外|公开.*信息","期限|term|3.*年|终止.*后"]),
]:
    new_tasks.append(t(d_name, "documentation", d_desc, d_input, d_grading, d_exp))

# ── Workflow (15 new) ──
for w_name, w_desc, w_input, w_grading, w_exp in [
    ("workflow-leave-approval", "描述员工请假审批的标准流程", {"leave_type":"年假/病假/事假","approval_chain":"直属上级-部门负责人-HR","rules":"年假>=3天需提前一周申请；病假需附医院证明"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["申请|提交","审批|approve|批准","年假.*3.*天|病假.*证明|规则|policy","通知|notify|HR"]),
    ("workflow-it-offboarding", "描述员工离职IT资产回收流程", {"assets":["笔记本电脑","手机","门禁卡","VPN","GitHub","Slack","邮箱"],"timeline":"最后工作日当天完成"}, {"completeness":{"weight":40,"must_match":True},"ordering":{"weight":30,"must_match":True},"coverage":{"weight":30,"must_match":True}}, ["回收|revoke|disable|删除|deactivate","设备|device|laptop|电脑","账号|account|权限|access|token","备份|backup|数据.*转移","确认|confirm|清单|checklist"]),
    ("workflow-bug-triage", "描述Bug工单分诊的标准流程", {"severity_levels":["P0-崩溃","P1-严重","P2-一般","P3-建议"],"sla":"P0:1h, P1:4h, P2:24h, P3:下周迭代"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["分级|分诊|triage|severity","P0|P1|崩溃|严重","SLA|时效|响应|分配|assign","升级|escalat|通知"]),
    ("workflow-content-publish", "描述内容发布审核流程", {"content_type":"微信公众号文章","stages":["撰稿","编辑初审","合规审查","排版","终审发布"]}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":35,"must_match":True},"ordering":{"weight":35,"must_match":True}}, ["审核|review|approval|审批","合规|compliance","发布|publish|上线","回退|reject|驳回|修改"]),
    ("workflow-invoice-processing", "描述发票处理流程", {"invoice_type":"增值税专用发票","stages":["收票","验真","认证","入账","归档"]}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["验真|查验|verify","认证|certif","入账|book|记账","归档|archive|保存","发票.*号码|发票.*代码"]),
    ("workflow-deal-close", "描述销售成交后的订单处理流程", {"stages":["合同确认","收款核销","开通服务","发票开具","客户交接"],"handoff":"销售-财务-运营-CSM"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True}}, ["合同|contract|确认|核实","收款|payment|核销|到账","开通|activate|provision","发票|invoice","交接|handoff|CSM|客户成功"]),
    ("workflow-monthly-close", "描述财务月结流程", {"period":"月末最后3个工作日","tasks":["关账","计提折旧","结转损益","生成报表","审计调整"]}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"ordering":{"weight":30,"must_match":True}}, ["关账|close|结算","计提|accrual|折旧|depreciation","损益|P&L|利润|loss","报表|report|对账|reconciliation","审计|audit"]),
    ("workflow-client-kickoff", "描述新客户项目启动流程", {"project_type":"软件实施","stages":["签约","kickoff会议","需求调研","方案确认","项目排期","资源分配"]}, {"completeness":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True},"coverage":{"weight":30,"must_match":True}}, ["kickoff|启动|启动会","需求|requirement|调研|SOW","排期|timeline|甘特|Gantt","资源|resource|分配|assign","干系人|stakeholder"]),
    ("workflow-data-backup", "描述数据库定期备份操作流程", {"databases":["MySQL","PostgreSQL","MongoDB"],"schedule":"每日全量+每小时增量","retention":"30天"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["备份|backup|dump|snapshot","增量|incremental|全量|full","保留|retention|30.*天","恢复|restore|验证|verify","加密|encrypt|异地|offsite"]),
    ("workflow-ssl-renewal", "描述SSL证书续期流程", {"cert_type":"通配符证书","validity":"90天","domains":15,"requirements":"零停机续期+自动部署"}, {"completeness":{"weight":30,"must_match":True},"ordering":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True}}, ["证书|certificate|cert|SSL|TLS","续期|renew|更新|过期|expir","自动|automate|certbot|acme","部署|deploy|重启|reload|nginx","验证|verify|检查.*证书"]),
    ("workflow-access-review", "描述季度权限审计流程", {"systems":["AWS","GitHub","Slack","Jira","数据库"],"reviewers":"部门负责人+安全团队","compliance":"SOC2"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}}, ["权限|access|audit|审计|review","清理|revoke|删除.*权限|最小权限","合规|compliance|SOC2","报告|report|记录|evidence"]),
    ("workflow-vendor-payment", "描述供应商付款审批流程", {"payment_methods":["银行转账","承兑汇票"],"approval_thresholds":"<=10万财务-><=50万CFO->>50万CEO+董事会","required_docs":"合同+发票+验收单"}, {"completeness":{"weight":25,"must_match":True},"policy":{"weight":50,"must_match":True},"actionability":{"weight":25,"must_match":True}}, ["付款|payment|支付|打款","审批|approval|threshold|阈值.*万","三单|合同.*发票.*验收|doc","排期|schedule|账期"]),
    ("workflow-inventory-count", "描述仓库月度盘点流程", {"inventory_type":"成品仓+原料仓","method":"盲盘+复盘","tolerance":"A类0%, B类1%, C类3%"}, {"completeness":{"weight":30,"must_match":True},"policy":{"weight":35,"must_match":True},"actionability":{"weight":35,"must_match":True}}, ["盘点|count|stocktake|库存","盲盘|复盘|初盘|差异|difference","tolerance|容差|ABC|分类","调整|adjust|盘盈|盘亏|损耗"]),
    ("workflow-security-drill", "描述安全演练流程", {"drill_type":"红蓝对抗","scope":"生产环境模拟攻击","participants":"安全团队+运维+开发代表","frequency":"每季度一次"}, {"completeness":{"weight":25,"must_match":True},"ordering":{"weight":25,"must_match":True},"coverage":{"weight":25,"must_match":True},"actionability":{"weight":25,"must_match":True}}, ["演练|drill|红蓝|对抗|scenario","授权|规则|scope|范围|ROE","复盘|postmortem|lesson.*learn|改进","通知|stakeholder|升级|escalation"]),
    ("workflow-contract-signing", "描述合同签署流程", {"contract_types":["采购","销售","NDA","劳动"],"signing_method":"电子签章+实体章","compliance":"必须法务审核+双人见证"}, {"completeness":{"weight":25,"must_match":True},"policy":{"weight":50,"must_match":True},"ordering":{"weight":25,"must_match":True}}, ["签署|签订|sign|签章|盖章","法务.*审核|legal.*review","见证|双人|counterpart","归档|存档|filing|原件"]),
]:
    new_tasks.append(t(w_name, "workflow", w_desc, w_input, w_grading, w_exp))

# Extract grader + runner code (everything after the task list ends)
# Find the pattern: ]\n\n# --- Grading Engine
import re
m = re.search(r'\n]\s*\n(# ── Grading Engine.+)', content, re.DOTALL)
if not m:
    m = re.search(r'\n]\s*\n(def grade_task.+)', content, re.DOTALL)
if not m:
    print("ERROR: cannot find grader code")
    exit(1)
grader_code = m.group(1)

# Build header + all tasks
header = '''"""SkillsBench-compatible deterministic task set — 100 tasks, 5 categories, 8 domains.

Deterministic regex-based grading. No LLM judge needed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import re

@dataclass
class SkillBenchTask:
    task_id: str
    category: str
    description: str
    input_data: dict
    grading: dict
    expected: list[str]
    forbidden: list[str] = field(default_factory=list)

SKILLSBENCH_TASKS: list[SkillBenchTask] = [
'''

with open("skillos/skillsbench_tasks.py", "w", encoding="utf-8") as f:
    f.write(header)
    f.write(",\n".join(new_tasks))
    f.write(",\n]\n\n")
    f.write(grader_code)

count = len(new_tasks) + 22  # original 22 + new
print(f"Written: {count} tasks total")
