"""SkillsBench-compatible deterministic task set — 88 tasks, 5 categories, 8 domains.

Exceeds official SkillsBench 84-task count.
Deterministic regex-based grading. No LLM judge needed.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillBenchTask:
    task_id: str
    category: str
    description: str
    input_data: dict
    grading: dict
    expected: list[str]
    forbidden: list[str] = field(default_factory=list)
    # When set, forbidden regex penalty applies only to these grading dimension keys.
    forbidden_dimensions: tuple[str, ...] | None = None

SKILLSBENCH_TASKS: list[SkillBenchTask] = [
    SkillBenchTask(
        task_id="code-review-001",
        category="code-review",
        description="审查null指针风险",
        input_data={'code': "def f(uid):\n u=db.query('SELECT email FROM users WHERE id=?',uid)\n return u.email.upper()", 'lang': 'python'},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 20, 'must_match': True}, 'actionability': {'weight': 20, 'must_match': True}, 'security': {'weight': 20, 'must_match': True}},
        expected=['null|None|Optional', 'db.query.*None', 'email.*None|email.*null'],
    ),
    SkillBenchTask(
        task_id="code-review-002",
        category="code-review",
        description="审查SQL注入风险",
        input_data={'code': 'def search(kw):\n sql="SELECT * FROM users WHERE name LIKE \'%\'+kw+\'%\'"\n return db.execute(sql)', 'lang': 'python'},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'security': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['注入|injection|SQL.*注入|拼接', '参数化|parameterized|prepared|placeholder|占位符|占位'],
    ),
    SkillBenchTask(
        task_id="code-review-003",
        category="code-review",
        description="审查XSS漏洞",
        input_data={'code': '<div onclick="alert(1)">{x}</div>', 'lang': 'javascript'},
        grading={'security': {'weight': 50, 'must_match': True}, 'actionability': {'weight': 50, 'must_match': True}},
        expected=['XSS|xss|跨站', '转义|escape|sanitize|过滤', 'innerHTML|textContent|createElement'],
    ),
    SkillBenchTask(
        task_id="code-review-004",
        category="code-review",
        description="审查竞态条件",
        input_data={'code': 'def t(a,b,amt):\n a.balance-=amt\n b.balance+=amt', 'lang': 'python'},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['锁|lock|mutex|加锁', '事务|transaction|atomic', '并发|concurrent|race'],
    ),
    SkillBenchTask(
        task_id="code-review-005",
        category="code-review",
        description="审查资源泄漏",
        input_data={'code': 'def read_file(p):\n f=open(p)\n return f.read()', 'lang': 'python'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'actionability': {'weight': 50, 'must_match': True}},
        expected=['with|close|finally|context manager', '泄漏|leak'],
    ),
    SkillBenchTask(
        task_id="code-review-006",
        category="code-review",
        description="审查硬编码密钥",
        input_data={'code': "KEY='sk-abc'\ndef call():\n h={'Auth':f'Bearer {KEY}'}", 'lang': 'python'},
        grading={'security': {'weight': 60, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['硬编码|hardcoded', '环境变量|env|os.environ|secret', '泄露|leak|移除|删除'],
    ),
    SkillBenchTask(
        task_id="code-review-007",
        category="code-review",
        description="审查缺少错误处理",
        input_data={'code': "def process(o):\n p=o['items'][0]['price']\n return p*1.1", 'lang': 'python'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['KeyError|TypeError|异常|try|except', 'None|null.*检查', 'default|默认|fallback'],
    ),
    SkillBenchTask(
        task_id="code-review-008",
        category="code-review",
        description="审查N+1查询",
        input_data={'code': 'for u in User.objects.all():\n print(u.profile.avatar)', 'lang': 'python'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'performance': {'weight': 50, 'must_match': True}},
        expected=['select_related|prefetch|join|N\\+1', '性能|performance|优化|批量查询'],
    ),
    SkillBenchTask(
        task_id="code-review-009",
        category="code-review",
        description="审查无限循环",
        input_data={'code': 'while d:=fetch():\n if not d.valid:continue\n process(d)', 'lang': 'python'},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'robustness': {'weight': 40, 'must_match': True}},
        expected=['无限循环|infinite loop|死循环', '超时|timeout|max_iter|break'],
    ),
    SkillBenchTask(
        task_id="code-review-010",
        category="code-review",
        description="审查缓冲区溢出",
        input_data={'code': 'void copy(char*d,char*s){strcpy(d,s);}', 'lang': 'c'},
        grading={'security': {'weight': 60, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['strncpy|strlcpy|边界|长度|overflow', 'sizeof|strlen|n'],
    ),
    SkillBenchTask(
        task_id="code-review-011",
        category="code-review",
        description="审查不安全反序列化",
        input_data={'code': 'import pickle\nd=pickle.loads(u)', 'lang': 'python'},
        grading={'security': {'weight': 60, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['pickle|unsafe|json|替代', '反序列化|deserializ', 'validate|输入.*检查'],
    ),
    SkillBenchTask(
        task_id="code-review-012",
        category="code-review",
        description="审查时间复杂度",
        input_data={'code': 'def dup(a):\n return[x for i,x in enumerate(a)if x in a[:i]]', 'lang': 'python'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'performance': {'weight': 50, 'must_match': True}},
        expected=['O\\(n\\^2\\)|O\\(n\\)|set|hash|字典|dict', '优化|性能|complexity'],
    ),
    SkillBenchTask(
        task_id="software-dependency-audit",
        category="code-review",
        description="审查软件依赖与供应链风险 dependency audit CVE lockfile semver",
        input_data={
            "manifest": "package.json",
            "deps": ["lodash@4.17.15", "left-pad@1.0.0"],
            "lockfile": "missing",
        },
        grading={
            "security": {"weight": 50, "must_match": True},
            "actionability": {"weight": 50, "must_match": True},
        },
        expected=[
            "CVE|漏洞|cve|安全",
            "lockfile|package-lock|yarn.lock|poetry.lock|锁定",
            "semver|版本|升级|pin",
            "传递依赖|transitive|供应链",
        ],
    ),
    SkillBenchTask(
        task_id="data-processing-013",
        category="data-processing",
        description="合并CSV按key去重",
        input_data={'a': 'id,name\n1,A\n2,B', 'b': 'id,score\n1,95\n3,88', 'key': 'id'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['merge|join|合并|连接', '去重|重复|drop_duplicate'],
    ),
    SkillBenchTask(
        task_id="data-processing-014",
        category="data-processing",
        description="按部门分组计算平均工资",
        input_data={'data': [{'dept': 'ENG', 'salary': 15000}, {'dept': 'ENG', 'salary': 18000}, {'dept': 'SALES', 'salary': 12000}]},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['groupby|分组|group by', 'mean|avg|平均', 'count|人数|sum'],
    ),
    SkillBenchTask(
        task_id="data-processing-015",
        category="data-processing",
        description="IQR检测异常值",
        input_data={'values': [10, 12, 11, 13, 10, 100, 9, 11, 12, 10]},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['IQR|四分位|quartile|箱线|boxplot', 'Q1|Q3|异常|outlier|100'],
    ),
    SkillBenchTask(
        task_id="data-processing-016",
        category="data-processing",
        description="缺失值中位数填充",
        input_data={'data': [{'age': 25}, {'age': None}, {'age': 30}]},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['中位数|median', '填充|fillna|impute|fill', '缺失|null|None|NaN'],
    ),
    SkillBenchTask(
        task_id="data-processing-017",
        category="data-processing",
        description="数据归一化0-1",
        input_data={'values': [10, 20, 30, 40, 50], 'method': 'min-max'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['归一|normalize|min.max|0.*1', 'standard|z.score|标准化'],
    ),
    SkillBenchTask(
        task_id="data-processing-018",
        category="data-processing",
        description="文本清洗去标点停用词",
        input_data={'texts': ['Hello, World!', 'This is TEST.']},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'method': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['lower|小写|标点|punctuation|regex', 'stopword|停用词', 'strip|清洗|clean'],
    ),
    SkillBenchTask(
        task_id="data-processing-019",
        category="data-processing",
        description="解析多种日期格式ISO8601",
        input_data={'dates': ['2024/01/15', '01-15-2024', 'Jan 15, 2024']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'robustness': {'weight': 50, 'must_match': True}},
        expected=['ISO|8601|parse|解析|datetime', '统一|normalize|标准化'],
    ),
    SkillBenchTask(
        task_id="data-processing-020",
        category="data-processing",
        description="展平嵌套JSON为表格",
        input_data={'json': '{"user":{"name":"Alice","address":{"city":"Beijing"}}}'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['展平|flatten|嵌套|nested|json_normalize', 'user.name|address.city'],
    ),
    SkillBenchTask(
        task_id="data-processing-021",
        category="data-processing",
        description="验证数据Schema类型",
        input_data={'schema': {'name': 'str', 'age': 'int'}, 'data': [{'name': 'Alice', 'age': '25'}, {'name': 'Bob', 'age': 30}]},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['类型|type.*check|validate|schema|校验'],
    ),
    SkillBenchTask(
        task_id="data-processing-022",
        category="data-processing",
        description="时间序列按周重采样",
        input_data={'data': '2024-01-01:100, 2024-01-03:120, 2024-01-08:150', 'freq': 'W'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['resample|重采样|采样', 'mean|均值|平均', 'weekly|周|W'],
    ),
    SkillBenchTask(
        task_id="data-processing-023",
        category="data-processing",
        description="皮尔逊相关系数",
        input_data={'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'interpretation': {'weight': 40, 'must_match': True}},
        expected=['pearson|皮尔逊|correlation|相关系数|corr'],
    ),
    SkillBenchTask(
        task_id="data-processing-024",
        category="data-processing",
        description="One-Hot编码",
        input_data={'categories': ['red', 'blue', 'green', 'red', 'blue']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['one.hot|onehot|独热|get_dummies|encode'],
    ),
    SkillBenchTask(
        task_id="data-processing-025",
        category="data-processing",
        description="数据集训练测试分割",
        input_data={'total': 1000, 'split_ratio': 0.8, 'seed': 42},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['split|分割|划分|train.*test', 'random_state|seed|随机'],
    ),
    SkillBenchTask(
        task_id="data-processing-026",
        category="data-processing",
        description="日期特征提取年月日星期",
        input_data={'date_column': ['2024-01-15', '2024-06-30', '2024-12-25']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['year|年|month|月|day|日|weekday|星期', '特征|feature|extract'],
    ),
    SkillBenchTask(
        task_id="data-processing-027",
        category="data-processing",
        description="滑动窗口移动平均值",
        input_data={'values': [10, 15, 12, 18, 20, 14, 16], 'window': 3},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['滑动|rolling|窗口|window', 'moving.*average|mean'],
    ),
    SkillBenchTask(
        task_id="data-processing-028",
        category="data-processing",
        description="纵向拼接DataFrame",
        input_data={'df1_cols': ['name', 'age'], 'df2_cols': ['name', 'age'], 'df1_rows': 100, 'df2_rows': 50},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['concat|拼接|append|union', 'axis.*0|纵向|垂直|行.*合并'],
    ),
    SkillBenchTask(
        task_id="data-processing-029",
        category="data-processing",
        description="模糊去重相似度匹配",
        input_data={'names': ['Beijing', 'Bejing', 'Shanghai', 'Shanghi']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['模糊|fuzzy|similarity|相似|levenshtein', 'Bejing.*Beijing|Shanghi.*Shanghai'],
    ),
    SkillBenchTask(
        task_id="data-processing-030",
        category="data-processing",
        description="解析Apache日志",
        input_data={'log_line': '192.168.1.1 - - [15/Jan/2024:13:55:36 +0800] "GET /api/users HTTP/1.1" 200 1234'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['parse|解析|regex|split', 'IP|192\\.168|status|200', '时间|timestamp|datetime'],
    ),
    SkillBenchTask(
        task_id="data-processing-031",
        category="data-processing",
        description="Excel多Sheet合并",
        input_data={'file': 'report.xlsx', 'sheets': ['Q1', 'Q2', 'Q3', 'Q4']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'method': {'weight': 50, 'must_match': True}},
        expected=['Excel|excel|xlsx|sheet|read_excel', 'concat|合并|merge'],
    ),
    SkillBenchTask(
        task_id="data-processing-032",
        category="data-processing",
        description="预算执行偏差分析",
        input_data={'budget': {'Q1': 100, 'Q2': 120, 'Q3': 110, 'Q4': 150}, 'actual': {'Q1': 95, 'Q2': 130, 'Q3': 105, 'Q4': 140}},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'interpretation': {'weight': 40, 'must_match': True}},
        expected=['偏差|variance|差异|实际.*预算', 'Q2.*超|Q4.*不足', '百分'],
    ),
    SkillBenchTask(
        task_id="data-processing-033",
        category="data-processing",
        description="计算含税价格税额",
        input_data={'amounts': [100, 200, 300], 'tax_rate': 0.13},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'method': {'weight': 40, 'must_match': True}},
        expected=['13%|0\\.13|增值税|VAT|tax', '含税|不含税|net|gross'],
    ),
    SkillBenchTask(
        task_id="data-processing-034",
        category="data-processing",
        description="固定资产直线折旧",
        input_data={'asset_cost': 100000, 'salvage': 5000, 'years': 5, 'method': 'straight-line'},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}},
        expected=['折旧|depreciation|straight', '残值|salvage|useful.*life'],
    ),
    SkillBenchTask(
        task_id="data-processing-035",
        category="data-processing",
        description="ROI和回收期计算",
        input_data={'investment': 500000, 'annual_return': 120000, 'years': 5},
        grading={'correctness': {'weight': 60, 'must_match': True}, 'interpretation': {'weight': 40, 'must_match': True}},
        expected=['ROI|回报率|return.*investment', '24%|0\\.24', 'payback|回收期'],
    ),
    SkillBenchTask(
        task_id="data-processing-036",
        category="data-processing",
        description="数据清洗去重补空",
        input_data={'data': 'id,name,email\n1,A,a@t.com\n2,B,\n1,A,a@t.com', 'format': 'csv'},
        grading={'correctness': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['去重|重复|duplicate|dedup', '空值|缺失|null|missing|补空|填空|fillna|空邮箱|空.*email'],
    ),
    SkillBenchTask(
        task_id="data-processing-037",
        category="data-processing",
        description="数据透视表区域季度销售",
        input_data={'data': [{'r': 'N', 'q': 'Q1', 's': 100}, {'r': 'N', 'q': 'Q2', 's': 150}, {'r': 'S', 'q': 'Q1', 's': 200}]},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'structure': {'weight': 50, 'must_match': True}},
        expected=['pivot|透视|crosstab'],
    ),
    SkillBenchTask(
        task_id="api-design-038",
        category="api-design",
        description="列表分页参数设计",
        input_data={'resource': 'articles', 'total': 1500},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['page|offset|cursor|游标', 'limit|size|per_page'],
    ),
    SkillBenchTask(
        task_id="api-design-039",
        category="api-design",
        description="统一错误响应格式",
        input_data={'scenarios': ['参数失败', '不存在', '权限不足', '服务器错误']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['400|404|403|500', 'error.*code|status'],
    ),
    SkillBenchTask(
        task_id="api-design-040",
        category="api-design",
        description="API认证方案设计",
        input_data={'auth_type': 'Bearer JWT'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'security': {'weight': 50, 'must_match': True}},
        expected=['Bearer|Authorization|JWT', 'refresh|刷新|expire|过期', '401|unauthorized'],
    ),
    SkillBenchTask(
        task_id="api-design-041",
        category="api-design",
        description="API限流方案",
        input_data={'limit': '100次/分钟'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['429|rate.*limit|限流|频率', 'Retry-After|X-RateLimit'],
    ),
    SkillBenchTask(
        task_id="api-design-042",
        category="api-design",
        description="API版本管理",
        input_data={'current': 'v1'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['v1|v2|version|版本', 'deprecat|废弃|兼容|compat'],
    ),
    SkillBenchTask(
        task_id="api-design-043",
        category="api-design",
        description="列表筛选排序参数",
        input_data={'resource': 'products', 'filters': ['category', 'price'], 'sorts': ['price', 'date']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['filter|筛选|过滤|sort|排序', 'asc|desc|order'],
    ),
    SkillBenchTask(
        task_id="api-design-044",
        category="api-design",
        description="文件上传API",
        input_data={'file_types': ['image', 'doc'], 'max_size': '10MB'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['multipart|upload|上传|POST', '分片|chunk|resumable'],
    ),
    SkillBenchTask(
        task_id="api-design-045",
        category="api-design",
        description="Webhook回调签名验证",
        input_data={'events': ['order.created', 'order.paid']},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'security': {'weight': 60, 'must_match': True}},
        expected=['webhook|回调|callback', '签名|signature|HMAC|SHA'],
    ),
    SkillBenchTask(
        task_id="api-design-046",
        category="api-design",
        description="批量操作API",
        input_data={'ops': ['批量创建', '批量更新', '批量删除']},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['batch|批量|bulk', 'partial|atomic|事务'],
    ),
    SkillBenchTask(
        task_id="api-design-047",
        category="api-design",
        description="全文搜索API",
        input_data={'resource': 'articles'},
        grading={'correctness': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['search|搜索|query|全文', 'highlight|高亮'],
    ),
    SkillBenchTask(
        task_id="api-design-048",
        category="api-design",
        description="RESTful用户CRUD",
        input_data={'resource': 'users'},
        grading={'correctness': {'weight': 35, 'must_match': True}, 'restfulness': {'weight': 35, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['GET.*users', 'POST.*users', 'PUT.*users|DELETE.*users', '200', '201', '204', '404'], forbidden=['GET.*delete', 'POST.*delete'],
    ),
    SkillBenchTask(
        task_id="documentation-049",
        category="documentation",
        description="README标准结构",
        input_data={'project': 'SkillOS', 'lang': 'Python'},
        grading={'structure': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 60, 'must_match': True}},
        expected=['安装|install|pip|clone', '使用|usage|quickstart', 'API|文档|documentation', 'License|license'],
    ),
    SkillBenchTask(
        task_id="documentation-050",
        category="documentation",
        description="Keep a Changelog版本变更",
        input_data={'ver': '2.0.0', 'changes': ['新增MoE', '修复SQL注入']},
        grading={'structure': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['Added|新增|添加', 'Fixed|修复|修正', 'Deprecated|废弃|弃用'],
    ),
    SkillBenchTask(
        task_id="documentation-051",
        category="documentation",
        description="REST端点API参考",
        input_data={'endpoint': 'POST /api/users', 'req': {'name': 'str'}, 'resp': {'id': 'uuid'}},
        grading={'structure': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 60, 'must_match': True}},
        expected=['Method|方法|POST', 'Parameters|参数', 'Response|响应', 'Example|示例|curl', 'Error|错误|Status Code'],
    ),
    SkillBenchTask(
        task_id="documentation-052",
        category="documentation",
        description="新员工技术环境搭建",
        input_data={'tools': ['Git', 'Docker', 'VS Code', 'Python']},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['Git|Docker|VS Code|Python', '安装|install|配置|setup', '验证|verify|check'],
    ),
    SkillBenchTask(
        task_id="documentation-053",
        category="documentation",
        description="架构决策记录ADR",
        input_data={'decision': '选PostgreSQL替代MongoDB'},
        grading={'structure': {'weight': 50, 'must_match': True}, 'completeness': {'weight': 50, 'must_match': True}},
        expected=['ADR|架构决策', 'context|背景', 'decision|决定', 'consequence|后果|影响', 'alternatives|替代'],
    ),
    SkillBenchTask(
        task_id="documentation-054",
        category="documentation",
        description="生产发布检查清单",
        input_data={'release': 'major', 'services': ['api', 'worker', 'frontend']},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['checklist|检查清单', '回滚|rollback|回退', '监控|monitor|告警|alert', '数据库.*迁移|migration|备份|backup'],
    ),
    SkillBenchTask(
        task_id="documentation-055",
        category="documentation",
        description="常见问题排查指南",
        input_data={'system': '电商平台', 'issues': ['支付超时', '登录失败']},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['症状|symptom|现象', '原因|root.*cause', '解决方案|solution|fix', '验证|verify|确认'],
    ),
    SkillBenchTask(
        task_id="documentation-056",
        category="documentation",
        description="代码注释规范",
        input_data={'lang': 'Python', 'style': 'Google docstring'},
        grading={'completeness': {'weight': 60, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['docstring|文档字符串', 'Args|参数|Parameters|Returns', 'Example|示例|用法', 'typing'],
    ),
    SkillBenchTask(
        task_id="documentation-057",
        category="documentation",
        description="数据库迁移手册",
        input_data={'from': 'MySQL5.7', 'to': 'MySQL8.0', 'size': '500GB'},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['备份|backup|dump|mysqldump', '迁移|migration|升级|upgrade', '验证|verify|compat', '回滚|rollback|回退'],
    ),
    SkillBenchTask(
        task_id="documentation-058",
        category="documentation",
        description="团队代码风格指南",
        input_data={'lang': 'TypeScript', 'tools': ['ESLint', 'Prettier']},
        grading={'completeness': {'weight': 50, 'must_match': True}, 'actionability': {'weight': 50, 'must_match': True}},
        expected=['缩进|indent|空格|tab', '引号|quotes|分号|semicolon', '行宽|line.*width', '命名|naming|camelCase'],
    ),
    SkillBenchTask(
        task_id="documentation-059",
        category="documentation",
        description="应用部署操作手册",
        input_data={'app': 'microservice', 'platform': 'Kubernetes'},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['build|构建|docker', 'push|推送|registry', 'deploy|部署|kubectl|helm', 'verify|验证|health|curl', '回滚|rollback'],
    ),
    SkillBenchTask(
        task_id="documentation-060",
        category="documentation",
        description="隐私政策必备章节",
        input_data={'regulation': '个人信息保护法+GDPR'},
        grading={'structure': {'weight': 30, 'must_match': True}, 'compliance': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['收集|collect|信息', '目的|purpose|用途', '第三方|third.*party|共享', '删除|delete|权利|撤回', '同意|consent|授权'],
    ),
    SkillBenchTask(
        task_id="documentation-061",
        category="documentation",
        description="服务条款核心章节",
        input_data={'service': 'SaaS', 'clauses': ['服务等级', '费用支付', '知识产权']},
        grading={'structure': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 60, 'must_match': True}},
        expected=['服务|service|SLA', '费用|fee|payment', '知识产权|IP|版权', '责任.*限制|liability', '管辖|jurisdiction|仲裁'],
    ),
    SkillBenchTask(
        task_id="documentation-062",
        category="documentation",
        description="保密协议关键条款",
        input_data={'parties': '甲方乙方', 'info': '代码+商业计划', 'term': '3年'},
        grading={'structure': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 60, 'must_match': True}},
        expected=['保密|confidential|NDA', '定义|definition', '义务|obligation|限制', '例外|exception|除外', '期限|term|年'],
    ),
    SkillBenchTask(
        task_id="documentation-063",
        category="documentation",
        description="事故应急响应runbook",
        input_data={'scenario': 'API超时>5s', 'team': 'infra'},
        grading={'structure': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['触发', '诊断', '恢复', '复盘', '回滚|rollback', '告警|alert|监控'],
    ),
    SkillBenchTask(
        task_id="workflow-064",
        category="workflow",
        description="处理客户退款",
        input_data={'order': {'id': 'ORD-12345', 'amount': 299}, 'customer': {'name': '张三'}},
        grading={'correctness': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}},
        expected=['验证|核实|检查.*订单|订单号', '退款政策|return policy|售后期|流程|规则', '金额|amount|299', '通知|邮件|确认|短信', '步骤|清单|执行'],
        forbidden=[
            r'未经.{0,12}核实.{0,12}退款',
            r'跳过.{0,8}验证.{0,8}退款',
            r'已为您发起.{0,12}退款',
            r'直接为您处理.{0,12}退款',
        ],
        forbidden_dimensions=("policy",),
    ),
    SkillBenchTask(
        task_id="workflow-065",
        category="workflow",
        description="新员工入职IT准备",
        input_data={'employee': {'name': '李四', 'dept': 'engineering', 'role': 'backend'}, 'start': '2026-07-01'},
        grading={'completeness': {'weight': 40, 'must_match': True}, 'ordering': {'weight': 30, 'must_match': True}, 'coverage': {'weight': 30, 'must_match': True}},
        expected=['账号|account|邮箱|email', '权限|permission|access', '设备|device|laptop', 'VPN|网络', '文档|wiki'],
    ),
    SkillBenchTask(
        task_id="workflow-066",
        category="workflow",
        description="员工请假审批",
        input_data={'leave': '年假病假事假', 'chain': '上级-部门-HR'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['申请|提交', '审批|approve|批准', '规则|policy', '通知|notify|HR'],
    ),
    SkillBenchTask(
        task_id="workflow-067",
        category="workflow",
        description="员工离职IT回收",
        input_data={'assets': ['笔记本', '手机', 'VPN', 'GitHub', 'Slack'], 'timeline': '最后工作日'},
        grading={'completeness': {'weight': 40, 'must_match': True}, 'ordering': {'weight': 30, 'must_match': True}, 'coverage': {'weight': 30, 'must_match': True}},
        expected=['回收|revoke|disable|删除', '设备|device|laptop', '账号|account|权限|token', '备份|backup', '检查清单|checklist'],
    ),
    SkillBenchTask(
        task_id="workflow-068",
        category="workflow",
        description="Bug工单分诊",
        input_data={'severity': ['P0-崩溃', 'P1-严重', 'P2-一般', 'P3-建议'], 'sla': 'P0:1h,P1:4h'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['分级|分诊|triage|severity', 'P0|P1|崩溃|严重', 'SLA|时效|响应|assign', '升级|escalat|通知'],
    ),
    SkillBenchTask(
        task_id="workflow-069",
        category="workflow",
        description="内容发布审核",
        input_data={'type': '公众号文章', 'stages': ['撰稿', '初审', '合规', '排版', '发布']},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 35, 'must_match': True}, 'ordering': {'weight': 35, 'must_match': True}},
        expected=['审核|review|approval', '合规|compliance', '发布|publish', '回退|reject|驳回'],
    ),
    SkillBenchTask(
        task_id="workflow-070",
        category="workflow",
        description="发票处理流程",
        input_data={'type': '增值税专用发票', 'stages': ['收票', '验真', '认证', '入账', '归档']},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['验真|查验|verify', '认证|certif', '入账|book|记账', '归档|archive', '发票.*号'],
    ),
    SkillBenchTask(
        task_id="workflow-071",
        category="workflow",
        description="销售成交订单处理",
        input_data={'stages': ['合同确认', '收款核销', '开通服务', '发票', '交接'], 'handoff': '销售-财务-运营-CSM'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['合同|contract|确认', '收款|payment|核销', '开通|activate|provision', '发票|invoice', '交接|handoff|CSM'],
    ),
    SkillBenchTask(
        task_id="workflow-072",
        category="workflow",
        description="财务月结流程",
        input_data={'period': '月末最后3工作日', 'tasks': ['关账', '计提折旧', '结转损益', '报表']},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'ordering': {'weight': 30, 'must_match': True}},
        expected=['关账|close|结算', '计提|accrual|折旧', '损益|P&L|利润', '报表|report|对账'],
    ),
    SkillBenchTask(
        task_id="workflow-073",
        category="workflow",
        description="新客户项目启动",
        input_data={'project': '软件实施', 'stages': ['签约', 'kickoff', '需求', '方案', '排期', '资源']},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}, 'coverage': {'weight': 30, 'must_match': True}},
        expected=['kickoff|启动', '需求|requirement|SOW', '排期|timeline|甘特', '资源|resource|分配', 'stakeholder'],
    ),
    SkillBenchTask(
        task_id="workflow-074",
        category="workflow",
        description="数据库定期备份",
        input_data={'dbs': ['MySQL', 'PostgreSQL'], 'schedule': '每日全量+每小时增量', 'retention': '30天'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['备份|backup|dump|snapshot', '增量|incremental|全量|full', '保留|retention', '恢复|restore|verify', '加密|encrypt'],
    ),
    SkillBenchTask(
        task_id="workflow-075",
        category="workflow",
        description="SSL证书续期",
        input_data={'cert': '通配符', 'validity': '90天', 'domains': 15},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'ordering': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 40, 'must_match': True}},
        expected=['证书|certificate|SSL|TLS', '续期|renew|expir', '自动|automate|certbot', '部署|deploy|nginx', 'verify'],
    ),
    SkillBenchTask(
        task_id="workflow-076",
        category="workflow",
        description="季度权限审计",
        input_data={'systems': ['AWS', 'GitHub', 'Slack'], 'compliance': 'SOC2'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 40, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['权限|access|audit|审计', '清理|revoke|最小权限', '合规|compliance|SOC2', '报告|report|记录'],
    ),
    SkillBenchTask(
        task_id="workflow-077",
        category="workflow",
        description="供应商付款审批",
        input_data={'methods': ['银行转账', '承兑汇票'], 'thresholds': '10万->50万->CEO'},
        grading={'completeness': {'weight': 25, 'must_match': True}, 'policy': {'weight': 50, 'must_match': True}, 'actionability': {'weight': 25, 'must_match': True}},
        expected=['付款|payment|支付', '审批|approval|threshold', '三单|合同.*发票.*验收', '账期|schedule'],
    ),
    SkillBenchTask(
        task_id="workflow-078",
        category="workflow",
        description="仓库月度盘点",
        input_data={'type': '成品仓+原料仓', 'method': '盲盘+复盘', 'tolerance': 'A类0%B类1%C类3%'},
        grading={'completeness': {'weight': 30, 'must_match': True}, 'policy': {'weight': 35, 'must_match': True}, 'actionability': {'weight': 35, 'must_match': True}},
        expected=['盘点|count|stocktake', '盲盘|复盘|差异', '容差|tolerance|ABC', '调整|adjust'],
    ),
    SkillBenchTask(
        task_id="workflow-079",
        category="workflow",
        description="安全演练流程",
        input_data={'drill': '红蓝对抗', 'scope': '生产模拟', 'freq': '每季度'},
        grading={'completeness': {'weight': 25, 'must_match': True}, 'ordering': {'weight': 25, 'must_match': True}, 'coverage': {'weight': 25, 'must_match': True}, 'actionability': {'weight': 25, 'must_match': True}},
        expected=['演练|drill|红蓝|对抗', '授权|规则|scope|ROE', '复盘|postmortem|改进', '通知|升级|escalation'],
    ),
    SkillBenchTask(
        task_id="workflow-080",
        category="workflow",
        description="合同签署流程",
        input_data={'types': ['采购', '销售', 'NDA', '劳动'], 'method': '电子签章', 'compliance': '法务审核+双人见证'},
        grading={'completeness': {'weight': 25, 'must_match': True}, 'policy': {'weight': 50, 'must_match': True}, 'ordering': {'weight': 25, 'must_match': True}},
        expected=['签署|签订|sign|签章', '法务.*审核|legal', '见证|双人|counterpart', '归档|存档|filing'],
    ),
    SkillBenchTask(
        task_id="workflow-081",
        category="workflow",
        description="销售数据关键指标",
        input_data={'sales': [1200, 3400, 2100, 8900, 1500], 'context': 'Q2销售万元'},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}, 'format': {'weight': 30, 'must_match': True}},
        expected=['总额', '平均', '最大', '最小'],
    ),
    SkillBenchTask(
        task_id="workflow-082",
        category="workflow",
        description="差旅报销审计",
        input_data={'expense': {'amount': 3500, 'items': [{'desc': '机票', 'amount': 2800}, {'desc': '酒店', 'amount': 700, 'note': '五星超标'}]}, 'policy': '酒店<=400/晚'},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'policy': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['超标|超出|超过', '酒店.*400', '不合规', '拒绝|退回'],
    ),
    SkillBenchTask(
        task_id="workflow-083",
        category="workflow",
        description="发票数据合规验证",
        input_data={'invoices': [{'no': 'FP-001', 'amount': 5000, 'tax_id': '91110XXX'}, {'no': 'FP-002', 'amount': 12000, 'tax_id': ''}, {'no': 'FP-001', 'amount': 5000, 'tax_id': '91110XXX'}]},
        grading={'correctness': {'weight': 35, 'must_match': True}, 'completeness': {'weight': 35, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['重复', 'duplicate', '税号', '缺失', '空'],
    ),
    SkillBenchTask(
        task_id="workflow-084",
        category="workflow",
        description="合同关键条款风险审查",
        input_data={'contract': {'parties': ['A公司', 'B公司'], 'key': '乙方不承担安全漏洞责任'}},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'risk_awareness': {'weight': 30, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['风险', '责任', '免责', '漏洞|安全', '不承担', '建议.*修改'], forbidden=['这合同没问题', '条款完善'],
    ),
    SkillBenchTask(
        task_id="workflow-085",
        category="workflow",
        description="用户数据隐私合规检查",
        input_data={'plan': '收集姓名手机号存储AWS。与第三方广告共享浏览记录。用户无法删除。永久保留。'},
        grading={'correctness': {'weight': 35, 'must_match': True}, 'compliance': {'weight': 35, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['同意|consent|授权', '删除|delete|撤回', '第三方.*共享', '保留.*期限|retention', '不合规|违规'],
    ),
    SkillBenchTask(
        task_id="workflow-086",
        category="workflow",
        description="课程大纲完整性评价",
        input_data={'course': {'title': 'Python入门', 'duration': '2天', 'audience': '零基础', 'assessment': '笔试'}},
        grading={'structure': {'weight': 30, 'must_match': True}, 'pedagogy': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['目标|objective', '练习|exercise|实践', '互动', '反馈|feedback|评估'],
    ),
    SkillBenchTask(
        task_id="workflow-087",
        category="workflow",
        description="库存补货分析",
        input_data={'inv': [{'sku': 'SKU-001', 'name': '鼠标', 'stock': 5, 'min': 20, 'daily': 8}, {'sku': 'SKU-003', 'name': '显示器', 'stock': 0, 'min': 10, 'daily': 5}]},
        grading={'correctness': {'weight': 40, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}, 'actionability': {'weight': 30, 'must_match': True}},
        expected=['补货|采购|进货', 'SKU-001|鼠标', 'SKU-003|显示器', '缺货|不足|库存.*低'],
    ),
    SkillBenchTask(
        task_id="workflow-088",
        category="workflow",
        description="运维排班方案",
        input_data={'req': '7x24值班每班2人5员工每周40h夜班每人每周<=2次', 'staff': ['A', 'B', 'C', 'D', 'E']},
        grading={'correctness': {'weight': 35, 'must_match': True}, 'fairness': {'weight': 35, 'must_match': True}, 'completeness': {'weight': 30, 'must_match': True}},
        expected=['排班|schedule|轮班|shift', '40.*小时|上限', '夜班.*2|2.*夜班', '7.*24|全天|覆盖'],
    ),
]

def _grade(score: int, max_score: int) -> str:
    """Map 0-100 total to letter grade."""
    pct = score / max_score if max_score > 0 else 0
    if pct >= 0.85: return "A"
    if pct >= 0.70: return "B"
    if pct >= 0.55: return "C"
    if pct >= 0.40: return "D"
    return "F"


def grade_task_response(task: SkillBenchTask, response: str) -> dict[str, Any]:
    """Grade an agent response against a deterministic task."""
    dimensions = {}
    total_score = 0
    total_max = 0
    for dim, config in task.grading.items():
        weight = config.get("weight", 20)
        must_match = config.get("must_match", True)
        patterns = task.expected
        forbidden = task.forbidden or []
        matched = sum(1 for pat in patterns if re.search(pat, response, re.IGNORECASE))
        missed = [pat for pat in patterns if must_match and not re.search(pat, response, re.IGNORECASE)]
        forbidden_hits = sum(1 for pat in forbidden if re.search(pat, response, re.IGNORECASE))
        coverage = matched / len(patterns) if patterns else 1.0
        apply_forbidden = (
            forbidden_hits > 0
            and (task.forbidden_dimensions is None or dim in task.forbidden_dimensions)
        )
        penalty = max(0, forbidden_hits / max(1, len(forbidden))) if apply_forbidden else 0
        dim_score = max(0, int(weight * coverage * (1.0 - penalty)))
        dimensions[dim] = {"score": dim_score, "max": weight, "passed": dim_score >= weight * 0.5, "matched": matched, "total_patterns": len(patterns), "missed": missed[:5], "forbidden_hits": forbidden_hits}
        total_score += dim_score
        total_max += weight
    return {"score": total_score, "max_score": total_max, "grade": _grade(total_score, total_max), "dimensions": dimensions}


def run_task_evaluation(
    task_id: str,
    *,
    skill_content: str = "",
    model: str = "",
    inject_skill: bool | None = None,
    bench_categories: list[str] | None = None,
    route_by_category: bool = False,
    skill_name: str = "",
    force_skill_inject: bool = False,
    domain_template: str | None = None,
    pack_scoped_inject: bool = True,
) -> dict:
    """Run a single SkillsBench task with optional skill augmentation."""
    from skillos.config import get_config
    from skillos.knowledge.skill_routing import resolve_skill_injection
    from skillos.llm_client import call

    task = next((t for t in SKILLSBENCH_TASKS if t.task_id == task_id), None)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    content_for_prompt = skill_content
    use_skill = bool(skill_content) if inject_skill is None else (inject_skill and bool(skill_content))
    if force_skill_inject and skill_content:
        use_skill = True
        content_for_prompt = skill_content
    elif route_by_category and skill_content:
        inject, content_for_prompt = resolve_skill_injection(
            task.category, skill_content, bench_categories, skill_name=skill_name, task=task,
            domain_template=domain_template, pack_scoped_inject=pack_scoped_inject,
        )
        use_skill = inject and bool(content_for_prompt) if inject_skill is None else use_skill and inject

    cfg = get_config()
    model_name = model or cfg.model
    system = ""
    if use_skill and content_for_prompt:
        from skillos.knowledge.skill_routing import skill_injection_payload

        inject_body = skill_injection_payload(content_for_prompt)
        system = (
            "You have the following skill available. Follow its instructions strictly.\n\n"
            f"{inject_body}"
        )
    user = (
        f"{task.description}\n\nInput:\n{json.dumps(task.input_data, ensure_ascii=False, indent=2)}\n\n"
        "Give a direct, actionable answer in one response (do not only ask clarifying questions)."
    )
    from skillos.skillsbench_cache import get_cached_response, store_cached_response
    response = get_cached_response(model=model_name, system=system, user=user)
    if response is None:
        response = call(prompt=user, system=system, model=model_name, max_tokens=600, temperature=0.2)
        store_cached_response(model=model_name, system=system, user=user, text=response)
    result = grade_task_response(task, response)
    result["task_id"] = task_id
    result["category"] = task.category
    result["skill_used"] = use_skill
    result["skill_injected"] = use_skill
    result["category_matched"] = use_skill if route_by_category else None
    result["response_preview"] = response[:300]
    return result


def _aggregate_results(results: list[dict]) -> dict[str, Any]:
    scores = [r["score"] for r in results if "score" in r]
    maxes = [r["max_score"] for r in results if "max_score" in r]
    total = sum(scores)
    max_total = sum(maxes)
    return {
        "tasks_run": len(results),
        "total_score": total,
        "max_score": max_total,
        "grade": _grade(total, max_total) if max_total else "F",
        "results": results,
    }


def run_skillsbench_suite(
    skill_content: str = "",
    model: str = "",
    *,
    bench_categories: list[str] | None = None,
    route_by_category: bool = False,
) -> dict:
    """Run all SkillsBench tasks; optionally inject skill only on matched categories."""
    from skillos.knowledge.skill_routing import should_inject_skill

    results = []
    for task in SKILLSBENCH_TASKS:
        inject = True
        if route_by_category and skill_content:
            inject = should_inject_skill(bench_categories or [], task.category)
        try:
            r = run_task_evaluation(
                task.task_id,
                skill_content=skill_content if inject else "",
                model=model,
                inject_skill=inject if skill_content else False,
                bench_categories=bench_categories,
                route_by_category=route_by_category,
            )
            r["category_matched"] = inject if route_by_category else None
            results.append(r)
        except Exception as e:
            results.append({"task_id": task.task_id, "error": str(e)})

    agg = _aggregate_results(results)
    return {
        "suite": "SkillsBench-compatible",
        "skill_used": bool(skill_content),
        "route_by_category": route_by_category,
        "bench_categories": bench_categories or [],
        **agg,
    }


def compare_with_without(skill_path: str, model: str = "", *, routed: bool = True) -> dict:
    """SkillsBench comparison: with-skill vs without-skill (category-routed by default).

    Routed mode contract:
      - matched_delta: domain-matched tasks only (with skill vs baseline)
      - harm_score: sum(forced_inject_score - baseline) on cross-domain tasks
      - cross_domain: per-task harm breakdown
    """
    from skillos.knowledge.skill_routing import (
        load_skill_routing_info,
        should_inject_skill,
    )

    info = load_skill_routing_info(skill_path) if (
        isinstance(skill_path, str) and ("/" in skill_path or "\\" in skill_path)
    ) else {
        "name": skill_path[:60],
        "content": skill_path,
        "bench_categories": [],
        "path": skill_path[:80] if isinstance(skill_path, str) else "",
    }
    content = info["content"]
    categories = info["bench_categories"]
    skill_label = info["name"]

    if not routed:
        with_skill = run_skillsbench_suite(skill_content=content, model=model)
        without_skill = run_skillsbench_suite(skill_content="", model=model)
        delta = with_skill["total_score"] - without_skill["total_score"]
        return {
            "skill": skill_label,
            "skill_path": info.get("path", "")[:80],
            "bench_categories": categories,
            "routed": False,
            "with_skill_score": with_skill["total_score"],
            "with_skill_grade": with_skill["grade"],
            "without_skill_score": without_skill["total_score"],
            "without_skill_grade": without_skill["grade"],
            "delta": delta,
            "improvement_pct": f"{delta / max(1, without_skill['total_score']) * 100:+.1f}%",
            "tasks": with_skill["tasks_run"],
        }

    matched_with: list[dict] = []
    matched_without: list[dict] = []
    cross_domain: list[dict] = []

    for task in SKILLSBENCH_TASKS:
        matched = should_inject_skill(categories, task.category)
        try:
            r_without = run_task_evaluation(task.task_id, skill_content="", model=model)
            if matched:
                r_with = run_task_evaluation(
                    task.task_id,
                    skill_content=content,
                    model=model,
                    route_by_category=True,
                    bench_categories=categories,
                    skill_name=skill_label,
                )
                matched_with.append(r_with)
                matched_without.append(r_without)
            else:
                r_forced = run_task_evaluation(
                    task.task_id, skill_content=content, model=model,
                    inject_skill=True,
                )
                harm = r_forced.get("score", 0) - r_without.get("score", 0)
                cross_domain.append({
                    "task_id": task.task_id,
                    "category": task.category,
                    "baseline_score": r_without.get("score", 0),
                    "forced_skill_score": r_forced.get("score", 0),
                    "harm_delta": harm,
                })
        except Exception as e:
            if matched:
                matched_with.append({"task_id": task.task_id, "error": str(e)})
            else:
                cross_domain.append({"task_id": task.task_id, "error": str(e)})

    mw = _aggregate_results(matched_with)
    mwo = _aggregate_results(matched_without)
    matched_delta = mw["total_score"] - mwo["total_score"]
    harm_score = sum(h.get("harm_delta", 0) for h in cross_domain if "harm_delta" in h)

    return {
        "skill": skill_label,
        "skill_path": info.get("path", "")[:80],
        "bench_categories": categories,
        "routed": True,
        "matched_tasks": mw["tasks_run"],
        "matched_with_score": mw["total_score"],
        "matched_without_score": mwo["total_score"],
        "matched_delta": matched_delta,
        "matched_improvement_pct": (
            f"{matched_delta / max(1, mwo['total_score']) * 100:+.1f}%"
            if mwo["total_score"] else "N/A"
        ),
        "matched_grade_with": mw["grade"],
        "matched_grade_without": mwo["grade"],
        "harm_score": harm_score,
        "cross_domain": cross_domain,
        # Legacy-compatible fields (matched subset only)
        "with_skill_score": mw["total_score"],
        "with_skill_grade": mw["grade"],
        "without_skill_score": mwo["total_score"],
        "without_skill_grade": mwo["grade"],
        "delta": matched_delta,
        "improvement_pct": (
            f"{matched_delta / max(1, mwo['total_score']) * 100:+.1f}%"
            if mwo["total_score"] else "N/A"
        ),
        "tasks": mw["tasks_run"],
        "matched_results": mw["results"],
    }


# ── CLI ──
if __name__ == "__main__":
    import sys
    if "--compare" in sys.argv:
        idx = sys.argv.index("--compare") + 1
        skill_path = sys.argv[idx] if idx < len(sys.argv) else ""
        if not skill_path:
            print(json.dumps({"error": "Usage: --compare <skill_path>"}, ensure_ascii=False))
            sys.exit(1)
        result = compare_with_without(skill_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--task" in sys.argv:
        idx = sys.argv.index("--task") + 1
        task_id = sys.argv[idx] if idx < len(sys.argv) else ""
        result = run_task_evaluation(task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Running SkillsBench baseline (no skill)...")
        result = run_skillsbench_suite()
        for r in result["results"]:
            if "score" in r:
                print(f"  {r['task_id']:35s} {r['score']:>4d}/{r['max_score']} [{r['grade']}]  ({r['category']})")
            else:
                print(f"  {r['task_id']:35s} ERROR: {r.get('error','')}")
        print(f"\nTotal: {result['total_score']}/{result['max_score']} [{result['grade']}]")
