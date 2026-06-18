"""Rebuild skillsbench_tasks.py from scratch — 88 tasks + complete grader."""
from pathlib import Path
SRC = Path(__file__).resolve().parent.parent / "skillos" / "skillsbench_tasks.py"

tasks = []
tid = 0
def add(cat, desc, inp, grading, exp, fb=None):
    global tid; tid += 1
    fb_s = f", forbidden={fb!r}" if fb else ""
    tasks.append(
        f'    SkillBenchTask(\n'
        f'        task_id="{cat}-{tid:03d}",\n'
        f'        category="{cat}",\n'
        f'        description="{desc}",\n'
        f'        input_data={inp!r},\n'
        f'        grading={grading!r},\n'
        f'        expected={exp!r}{fb_s},\n'
        f'    )'
    )

# ── 88 tasks (same as before, tested working) ──
# Code Review (12)
add("code-review","审查null指针风险",{"code":"def f(uid):\n u=db.query('SELECT email FROM users WHERE id=?',uid)\n return u.email.upper()","lang":"python"},{"correctness":{"weight":40,"must_match":True},"completeness":{"weight":20,"must_match":True},"actionability":{"weight":20,"must_match":True},"security":{"weight":20,"must_match":True}},["null|None|Optional","db.query.*None","email.*None|email.*null"])
add("code-review","审查SQL注入风险",{"code":"def search(kw):\n sql=\"SELECT * FROM users WHERE name LIKE '%'+kw+'%'\"\n return db.execute(sql)","lang":"python"},{"correctness":{"weight":40,"must_match":True},"security":{"weight":30,"must_match":True},"completeness":{"weight":30,"must_match":True}},["注入|injection|参数化|parameterized|prepared","placeholder|占位符"])
add("code-review","审查XSS漏洞",{"code":"<div onclick=\"alert(1)\">{x}</div>","lang":"javascript"},{"security":{"weight":50,"must_match":True},"actionability":{"weight":50,"must_match":True}},["XSS|xss|跨站","转义|escape|sanitize|过滤","innerHTML|textContent|createElement"])
add("code-review","审查竞态条件",{"code":"def t(a,b,amt):\n a.balance-=amt\n b.balance+=amt","lang":"python"},{"correctness":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}},["锁|lock|mutex|加锁","事务|transaction|atomic","并发|concurrent|race"])
add("code-review","审查资源泄漏",{"code":"def read_file(p):\n f=open(p)\n return f.read()","lang":"python"},{"correctness":{"weight":50,"must_match":True},"actionability":{"weight":50,"must_match":True}},["with|close|finally|context manager","泄漏|leak"])
add("code-review","审查硬编码密钥",{"code":"KEY='sk-abc'\ndef call():\n h={'Auth':f'Bearer {KEY}'}","lang":"python"},{"security":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}},["硬编码|hardcoded","环境变量|env|os.environ|secret","泄露|leak|移除|删除"])
add("code-review","审查缺少错误处理",{"code":"def process(o):\n p=o['items'][0]['price']\n return p*1.1","lang":"python"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["KeyError|TypeError|异常|try|except","None|null.*检查","default|默认|fallback"])
add("code-review","审查N+1查询",{"code":"for u in User.objects.all():\n print(u.profile.avatar)","lang":"python"},{"correctness":{"weight":50,"must_match":True},"performance":{"weight":50,"must_match":True}},["select_related|prefetch|join|N\\+1","性能|performance|优化|批量查询"])
add("code-review","审查无限循环",{"code":"while d:=fetch():\n if not d.valid:continue\n process(d)","lang":"python"},{"correctness":{"weight":60,"must_match":True},"robustness":{"weight":40,"must_match":True}},["无限循环|infinite loop|死循环","超时|timeout|max_iter|break"])
add("code-review","审查缓冲区溢出",{"code":"void copy(char*d,char*s){strcpy(d,s);}","lang":"c"},{"security":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}},["strncpy|strlcpy|边界|长度|overflow","sizeof|strlen|n"])
add("code-review","审查不安全反序列化",{"code":"import pickle\nd=pickle.loads(u)","lang":"python"},{"security":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}},["pickle|unsafe|json|替代","反序列化|deserializ","validate|输入.*检查"])
add("code-review","审查时间复杂度",{"code":"def dup(a):\n return[x for i,x in enumerate(a)if x in a[:i]]","lang":"python"},{"correctness":{"weight":50,"must_match":True},"performance":{"weight":50,"must_match":True}},["O\\(n\\^2\\)|O\\(n\\)|set|hash|字典|dict","优化|性能|complexity"])

# Data Processing (25)
dps=[("合并CSV按key去重",{"a":"id,name\n1,A\n2,B","b":"id,score\n1,95\n3,88","key":"id"},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["merge|join|合并|连接","去重|重复|drop_duplicate"]),("按部门分组计算平均工资",{"data":[{"dept":"ENG","salary":15000},{"dept":"ENG","salary":18000},{"dept":"SALES","salary":12000}]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["groupby|分组|group by","mean|avg|平均","count|人数|sum"]),("IQR检测异常值",{"values":[10,12,11,13,10,100,9,11,12,10]},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["IQR|四分位|quartile|箱线|boxplot","Q1|Q3|异常|outlier|100"]),("缺失值中位数填充",{"data":[{"age":25},{"age":None},{"age":30}]},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["中位数|median","填充|fillna|impute|fill","缺失|null|None|NaN"]),("数据归一化0-1",{"values":[10,20,30,40,50],"method":"min-max"},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["归一|normalize|min.max|0.*1","standard|z.score|标准化"]),("文本清洗去标点停用词",{"texts":["Hello, World!","This is TEST."]},{"correctness":{"weight":40,"must_match":True},"method":{"weight":30,"must_match":True},"completeness":{"weight":30,"must_match":True}},["lower|小写|标点|punctuation|regex","stopword|停用词","strip|清洗|clean"]),("解析多种日期格式ISO8601",{"dates":["2024/01/15","01-15-2024","Jan 15, 2024"]},{"correctness":{"weight":50,"must_match":True},"robustness":{"weight":50,"must_match":True}},["ISO|8601|parse|解析|datetime","统一|normalize|标准化"]),("展平嵌套JSON为表格",{"json":"{\"user\":{\"name\":\"Alice\",\"address\":{\"city\":\"Beijing\"}}}"},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["展平|flatten|嵌套|nested|json_normalize","user.name|address.city"]),("验证数据Schema类型",{"schema":{"name":"str","age":"int"},"data":[{"name":"Alice","age":"25"},{"name":"Bob","age":30}]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["类型|type.*check|validate|schema|校验"]),("时间序列按周重采样",{"data":"2024-01-01:100, 2024-01-03:120, 2024-01-08:150","freq":"W"},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["resample|重采样|采样","mean|均值|平均","weekly|周|W"]),("皮尔逊相关系数",{"x":[1,2,3,4,5],"y":[2,4,6,8,10]},{"correctness":{"weight":60,"must_match":True},"interpretation":{"weight":40,"must_match":True}},["pearson|皮尔逊|correlation|相关系数|corr"]),("One-Hot编码",{"categories":["red","blue","green","red","blue"]},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["one.hot|onehot|独热|get_dummies|encode"]),("数据集训练测试分割",{"total":1000,"split_ratio":0.8,"seed":42},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["split|分割|划分|train.*test","random_state|seed|随机"]),("日期特征提取年月日星期",{"date_column":["2024-01-15","2024-06-30","2024-12-25"]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["year|年|month|月|day|日|weekday|星期","特征|feature|extract"]),("滑动窗口移动平均值",{"values":[10,15,12,18,20,14,16],"window":3},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["滑动|rolling|窗口|window","moving.*average|mean"]),("纵向拼接DataFrame",{"df1_cols":["name","age"],"df2_cols":["name","age"],"df1_rows":100,"df2_rows":50},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["concat|拼接|append|union","axis.*0|纵向|垂直|行.*合并"]),("模糊去重相似度匹配",{"names":["Beijing","Bejing","Shanghai","Shanghi"]},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["模糊|fuzzy|similarity|相似|levenshtein","Bejing.*Beijing|Shanghi.*Shanghai"]),("解析Apache日志",{"log_line":"192.168.1.1 - - [15/Jan/2024:13:55:36 +0800] \"GET /api/users HTTP/1.1\" 200 1234"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["parse|解析|regex|split","IP|192\\.168|status|200","时间|timestamp|datetime"]),("Excel多Sheet合并",{"file":"report.xlsx","sheets":["Q1","Q2","Q3","Q4"]},{"correctness":{"weight":50,"must_match":True},"method":{"weight":50,"must_match":True}},["Excel|excel|xlsx|sheet|read_excel","concat|合并|merge"]),("预算执行偏差分析",{"budget":{"Q1":100,"Q2":120,"Q3":110,"Q4":150},"actual":{"Q1":95,"Q2":130,"Q3":105,"Q4":140}},{"correctness":{"weight":60,"must_match":True},"interpretation":{"weight":40,"must_match":True}},["偏差|variance|差异|实际.*预算","Q2.*超|Q4.*不足","百分"]),("计算含税价格税额",{"amounts":[100,200,300],"tax_rate":0.13},{"correctness":{"weight":60,"must_match":True},"method":{"weight":40,"must_match":True}},["13%|0\\.13|增值税|VAT|tax","含税|不含税|net|gross"]),("固定资产直线折旧",{"asset_cost":100000,"salvage":5000,"years":5,"method":"straight-line"},{"correctness":{"weight":60,"must_match":True},"completeness":{"weight":40,"must_match":True}},["折旧|depreciation|straight","残值|salvage|useful.*life"]),("ROI和回收期计算",{"investment":500000,"annual_return":120000,"years":5},{"correctness":{"weight":60,"must_match":True},"interpretation":{"weight":40,"must_match":True}},["ROI|回报率|return.*investment","24%|0\\.24","payback|回收期"]),("数据清洗去重补空",{"data":"id,name,email\n1,A,a@t.com\n2,B,\n1,A,a@t.com","format":"csv"},{"correctness":{"weight":30,"must_match":True},"completeness":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True}},["去重|重复|duplicate","空值|缺失|null|missing"]),("数据透视表区域季度销售",{"data":[{"r":"N","q":"Q1","s":100},{"r":"N","q":"Q2","s":150},{"r":"S","q":"Q1","s":200}]},{"correctness":{"weight":50,"must_match":True},"structure":{"weight":50,"must_match":True}},["pivot|透视|crosstab"])]
for d in dps: add("data-processing",d[0],d[1],d[2],d[3])

# API Design (11)
for ad in [("列表分页参数设计",{"resource":"articles","total":1500},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["page|offset|cursor|游标","limit|size|per_page"]),("统一错误响应格式",{"scenarios":["参数失败","不存在","权限不足","服务器错误"]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["400|404|403|500","error.*code|status"]),("API认证方案设计",{"auth_type":"Bearer JWT"},{"correctness":{"weight":50,"must_match":True},"security":{"weight":50,"must_match":True}},["Bearer|Authorization|JWT","refresh|刷新|expire|过期","401|unauthorized"]),("API限流方案",{"limit":"100次/分钟"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["429|rate.*limit|限流|频率","Retry-After|X-RateLimit"]),("API版本管理",{"current":"v1"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["v1|v2|version|版本","deprecat|废弃|兼容|compat"]),("列表筛选排序参数",{"resource":"products","filters":["category","price"],"sorts":["price","date"]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["filter|筛选|过滤|sort|排序","asc|desc|order"]),("文件上传API",{"file_types":["image","doc"],"max_size":"10MB"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["multipart|upload|上传|POST","分片|chunk|resumable"]),("Webhook回调签名验证",{"events":["order.created","order.paid"]},{"correctness":{"weight":40,"must_match":True},"security":{"weight":60,"must_match":True}},["webhook|回调|callback","签名|signature|HMAC|SHA"]),("批量操作API",{"ops":["批量创建","批量更新","批量删除"]},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["batch|批量|bulk","partial|atomic|事务"]),("全文搜索API",{"resource":"articles"},{"correctness":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["search|搜索|query|全文","highlight|高亮"]),("RESTful用户CRUD",{"resource":"users"},{"correctness":{"weight":35,"must_match":True},"restfulness":{"weight":35,"must_match":True},"completeness":{"weight":30,"must_match":True}},["GET.*users","POST.*users","PUT.*users|DELETE.*users","200","201","204","404"],["GET.*delete","POST.*delete"])]:
    add("api-design",ad[0],ad[1],ad[2],ad[3],ad[4] if len(ad)>4 else None)

# Documentation (15)
for dc in [("README标准结构",{"project":"SkillOS","lang":"Python"},{"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}},["安装|install|pip|clone","使用|usage|quickstart","API|文档|documentation","License|license"]),("Keep a Changelog版本变更",{"ver":"2.0.0","changes":["新增MoE","修复SQL注入"]},{"structure":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["Added|新增|添加","Fixed|修复|修正","Deprecated|废弃|弃用"]),("REST端点API参考",{"endpoint":"POST /api/users","req":{"name":"str"},"resp":{"id":"uuid"}},{"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}},["Method|方法|POST","Parameters|参数","Response|响应","Example|示例|curl","Error|错误|Status Code"]),("新员工技术环境搭建",{"tools":["Git","Docker","VS Code","Python"]},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["Git|Docker|VS Code|Python","安装|install|配置|setup","验证|verify|check"]),("架构决策记录ADR",{"decision":"选PostgreSQL替代MongoDB"},{"structure":{"weight":50,"must_match":True},"completeness":{"weight":50,"must_match":True}},["ADR|架构决策","context|背景","decision|决定","consequence|后果|影响","alternatives|替代"]),("生产发布检查清单",{"release":"major","services":["api","worker","frontend"]},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["checklist|检查清单","回滚|rollback|回退","监控|monitor|告警|alert","数据库.*迁移|migration|备份|backup"]),("常见问题排查指南",{"system":"电商平台","issues":["支付超时","登录失败"]},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["症状|symptom|现象","原因|root.*cause","解决方案|solution|fix","验证|verify|确认"]),("代码注释规范",{"lang":"Python","style":"Google docstring"},{"completeness":{"weight":60,"must_match":True},"actionability":{"weight":40,"must_match":True}},["docstring|文档字符串","Args|参数|Parameters|Returns","Example|示例|用法","typing"]),("数据库迁移手册",{"from":"MySQL5.7","to":"MySQL8.0","size":"500GB"},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["备份|backup|dump|mysqldump","迁移|migration|升级|upgrade","验证|verify|compat","回滚|rollback|回退"]),("团队代码风格指南",{"lang":"TypeScript","tools":["ESLint","Prettier"]},{"completeness":{"weight":50,"must_match":True},"actionability":{"weight":50,"must_match":True}},["缩进|indent|空格|tab","引号|quotes|分号|semicolon","行宽|line.*width","命名|naming|camelCase"]),("应用部署操作手册",{"app":"microservice","platform":"Kubernetes"},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["build|构建|docker","push|推送|registry","deploy|部署|kubectl|helm","verify|验证|health|curl","回滚|rollback"]),("隐私政策必备章节",{"regulation":"个人信息保护法+GDPR"},{"structure":{"weight":30,"must_match":True},"compliance":{"weight":40,"must_match":True},"completeness":{"weight":30,"must_match":True}},["收集|collect|信息","目的|purpose|用途","第三方|third.*party|共享","删除|delete|权利|撤回","同意|consent|授权"]),("服务条款核心章节",{"service":"SaaS","clauses":["服务等级","费用支付","知识产权"]},{"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}},["服务|service|SLA","费用|fee|payment","知识产权|IP|版权","责任.*限制|liability","管辖|jurisdiction|仲裁"]),("保密协议关键条款",{"parties":"甲方乙方","info":"代码+商业计划","term":"3年"},{"structure":{"weight":40,"must_match":True},"completeness":{"weight":60,"must_match":True}},["保密|confidential|NDA","定义|definition","义务|obligation|限制","例外|exception|除外","期限|term|年"]),("事故应急响应runbook",{"scenario":"API超时>5s","team":"infra"},{"structure":{"weight":30,"must_match":True},"completeness":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["触发","诊断","恢复","复盘","回滚|rollback","告警|alert|监控"])]:
    add("documentation",dc[0],dc[1],dc[2],dc[3])

# Workflow (25)
for wf in [("处理客户退款",{"order":{"id":"ORD-12345","amount":299},"customer":{"name":"张三"}},{"correctness":{"weight":30,"must_match":True},"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True}},["验证|核实|检查.*订单","退款政策|return policy","金额|amount","通知|邮件|确认"],["直接退款"]),("新员工入职IT准备",{"employee":{"name":"李四","dept":"engineering","role":"backend"},"start":"2026-07-01"},{"completeness":{"weight":40,"must_match":True},"ordering":{"weight":30,"must_match":True},"coverage":{"weight":30,"must_match":True}},["账号|account|邮箱|email","权限|permission|access","设备|device|laptop","VPN|网络","文档|wiki"]),("员工请假审批",{"leave":"年假病假事假","chain":"上级-部门-HR"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["申请|提交","审批|approve|批准","规则|policy","通知|notify|HR"]),("员工离职IT回收",{"assets":["笔记本","手机","VPN","GitHub","Slack"],"timeline":"最后工作日"},{"completeness":{"weight":40,"must_match":True},"ordering":{"weight":30,"must_match":True},"coverage":{"weight":30,"must_match":True}},["回收|revoke|disable|删除","设备|device|laptop","账号|account|权限|token","备份|backup","检查清单|checklist"]),("Bug工单分诊",{"severity":["P0-崩溃","P1-严重","P2-一般","P3-建议"],"sla":"P0:1h,P1:4h"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["分级|分诊|triage|severity","P0|P1|崩溃|严重","SLA|时效|响应|assign","升级|escalat|通知"]),("内容发布审核",{"type":"公众号文章","stages":["撰稿","初审","合规","排版","发布"]},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":35,"must_match":True},"ordering":{"weight":35,"must_match":True}},["审核|review|approval","合规|compliance","发布|publish","回退|reject|驳回"]),("发票处理流程",{"type":"增值税专用发票","stages":["收票","验真","认证","入账","归档"]},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["验真|查验|verify","认证|certif","入账|book|记账","归档|archive","发票.*号"]),("销售成交订单处理",{"stages":["合同确认","收款核销","开通服务","发票","交接"],"handoff":"销售-财务-运营-CSM"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True}},["合同|contract|确认","收款|payment|核销","开通|activate|provision","发票|invoice","交接|handoff|CSM"]),("财务月结流程",{"period":"月末最后3工作日","tasks":["关账","计提折旧","结转损益","报表"]},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"ordering":{"weight":30,"must_match":True}},["关账|close|结算","计提|accrual|折旧","损益|P&L|利润","报表|report|对账"]),("新客户项目启动",{"project":"软件实施","stages":["签约","kickoff","需求","方案","排期","资源"]},{"completeness":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True},"coverage":{"weight":30,"must_match":True}},["kickoff|启动","需求|requirement|SOW","排期|timeline|甘特","资源|resource|分配","stakeholder"]),("数据库定期备份",{"dbs":["MySQL","PostgreSQL"],"schedule":"每日全量+每小时增量","retention":"30天"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["备份|backup|dump|snapshot","增量|incremental|全量|full","保留|retention","恢复|restore|verify","加密|encrypt"]),("SSL证书续期",{"cert":"通配符","validity":"90天","domains":15},{"completeness":{"weight":30,"must_match":True},"ordering":{"weight":30,"must_match":True},"actionability":{"weight":40,"must_match":True}},["证书|certificate|SSL|TLS","续期|renew|expir","自动|automate|certbot","部署|deploy|nginx","verify"]),("季度权限审计",{"systems":["AWS","GitHub","Slack"],"compliance":"SOC2"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":40,"must_match":True},"actionability":{"weight":30,"must_match":True}},["权限|access|audit|审计","清理|revoke|最小权限","合规|compliance|SOC2","报告|report|记录"]),("供应商付款审批",{"methods":["银行转账","承兑汇票"],"thresholds":"10万->50万->CEO"} ,{"completeness":{"weight":25,"must_match":True},"policy":{"weight":50,"must_match":True},"actionability":{"weight":25,"must_match":True}},["付款|payment|支付","审批|approval|threshold","三单|合同.*发票.*验收","账期|schedule"]),("仓库月度盘点",{"type":"成品仓+原料仓","method":"盲盘+复盘","tolerance":"A类0%B类1%C类3%"},{"completeness":{"weight":30,"must_match":True},"policy":{"weight":35,"must_match":True},"actionability":{"weight":35,"must_match":True}},["盘点|count|stocktake","盲盘|复盘|差异","容差|tolerance|ABC","调整|adjust"]),("安全演练流程",{"drill":"红蓝对抗","scope":"生产模拟","freq":"每季度"},{"completeness":{"weight":25,"must_match":True},"ordering":{"weight":25,"must_match":True},"coverage":{"weight":25,"must_match":True},"actionability":{"weight":25,"must_match":True}},["演练|drill|红蓝|对抗","授权|规则|scope|ROE","复盘|postmortem|改进","通知|升级|escalation"]),("合同签署流程",{"types":["采购","销售","NDA","劳动"],"method":"电子签章","compliance":"法务审核+双人见证"},{"completeness":{"weight":25,"must_match":True},"policy":{"weight":50,"must_match":True},"ordering":{"weight":25,"must_match":True}},["签署|签订|sign|签章","法务.*审核|legal","见证|双人|counterpart","归档|存档|filing"]),("销售数据关键指标",{"sales":[1200,3400,2100,8900,1500],"context":"Q2销售万元"},{"correctness":{"weight":40,"must_match":True},"completeness":{"weight":30,"must_match":True},"format":{"weight":30,"must_match":True}},["总额","平均","最大","最小"]),("差旅报销审计",{"expense":{"amount":3500,"items":[{"desc":"机票","amount":2800},{"desc":"酒店","amount":700,"note":"五星超标"}]},"policy":"酒店<=400/晚"},{"correctness":{"weight":40,"must_match":True},"policy":{"weight":30,"must_match":True},"actionability":{"weight":30,"must_match":True}},["超标|超出|超过","酒店.*400","不合规","拒绝|退回"]),("发票数据合规验证",{"invoices":[{"no":"FP-001","amount":5000,"tax_id":"91110XXX"},{"no":"FP-002","amount":12000,"tax_id":""},{"no":"FP-001","amount":5000,"tax_id":"91110XXX"}]},{"correctness":{"weight":35,"must_match":True},"completeness":{"weight":35,"must_match":True},"actionability":{"weight":30,"must_match":True}},["重复","duplicate","税号","缺失","空"]),("合同关键条款风险审查",{"contract":{"parties":["A公司","B公司"],"key":"乙方不承担安全漏洞责任"}},{"correctness":{"weight":40,"must_match":True},"risk_awareness":{"weight":30,"must_match":True},"completeness":{"weight":30,"must_match":True}},["风险","责任","免责","漏洞|安全","不承担","建议.*修改"],["这合同没问题","条款完善"]),("用户数据隐私合规检查",{"plan":"收集姓名手机号存储AWS。与第三方广告共享浏览记录。用户无法删除。永久保留。"},{"correctness":{"weight":35,"must_match":True},"compliance":{"weight":35,"must_match":True},"actionability":{"weight":30,"must_match":True}},["同意|consent|授权","删除|delete|撤回","第三方.*共享","保留.*期限|retention","不合规|违规"]),("课程大纲完整性评价",{"course":{"title":"Python入门","duration":"2天","audience":"零基础","assessment":"笔试"}},{"structure":{"weight":30,"must_match":True},"pedagogy":{"weight":40,"must_match":True},"completeness":{"weight":30,"must_match":True}},["目标|objective","练习|exercise|实践","互动","反馈|feedback|评估"]),("库存补货分析",{"inv":[{"sku":"SKU-001","name":"鼠标","stock":5,"min":20,"daily":8},{"sku":"SKU-003","name":"显示器","stock":0,"min":10,"daily":5}]},{"correctness":{"weight":40,"must_match":True},"completeness":{"weight":30,"must_match":True},"actionability":{"weight":30,"must_match":True}},["补货|采购|进货","SKU-001|鼠标","SKU-003|显示器","缺货|不足|库存.*低"]),("运维排班方案",{"req":"7x24值班每班2人5员工每周40h夜班每人每周<=2次","staff":["A","B","C","D","E"]},{"correctness":{"weight":35,"must_match":True},"fairness":{"weight":35,"must_match":True},"completeness":{"weight":30,"must_match":True}},["排班|schedule|轮班|shift","40.*小时|上限","夜班.*2|2.*夜班","7.*24|全天|覆盖"])]:
    add("workflow",wf[0],wf[1],wf[2],wf[3],wf[4] if len(wf)>4 else None)

# ── Write complete file with full grader ──
grader_code = r'''
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
        penalty = max(0, forbidden_hits / max(1, len(forbidden))) if forbidden else 0
        dim_score = max(0, int(weight * coverage * (1.0 - penalty)))
        dimensions[dim] = {"score": dim_score, "max": weight, "passed": dim_score >= weight * 0.5, "matched": matched, "total_patterns": len(patterns), "missed": missed[:5], "forbidden_hits": forbidden_hits}
        total_score += dim_score
        total_max += weight
    return {"score": total_score, "max_score": total_max, "grade": _grade(total_score, total_max), "dimensions": dimensions}


def run_task_evaluation(task_id: str, *, skill_content: str = "", model: str = "") -> dict:
    """Run a single SkillsBench task with optional skill augmentation."""
    task = next((t for t in SKILLSBENCH_TASKS if t.task_id == task_id), None)
    if not task:
        return {"error": f"Task not found: {task_id}"}
    from skillos.llm_client import call
    from skillos.config import get_config
    cfg = get_config()
    model_name = model or cfg.model
    system = ""
    if skill_content:
        system = f"You have the following skill available. Follow its instructions strictly.\n\n{skill_content[:3000]}"
    user = f"{task.description}\n\nInput:\n{json.dumps(task.input_data, ensure_ascii=False, indent=2)}"
    response = call(prompt=user, system=system, model=model_name, max_tokens=600, temperature=0.2)
    result = grade_task_response(task, response)
    result["task_id"] = task_id
    result["category"] = task.category
    result["skill_used"] = bool(skill_content)
    result["response_preview"] = response[:300]
    return result


def _aggregate_results(results: list[dict]) -> dict[str, Any]:
    scores = [r["score"] for r in results if "score" in r]
    maxes = [r["max_score"] for r in results if "max_score" in r]
    return {"total_score": sum(scores), "max_score": sum(maxes), "grade": _grade(sum(scores), sum(maxes)), "tasks_run": len(results)}


def run_skillsbench_suite(skill_content: str = "", model: str = "") -> dict:
    """Run all SkillsBench tasks and return aggregated results."""
    results = []
    for task in SKILLSBENCH_TASKS:
        try:
            r = run_task_evaluation(task.task_id, skill_content=skill_content, model=model)
            results.append(r)
        except Exception as e:
            results.append({"task_id": task.task_id, "error": str(e)})
    agg = _aggregate_results(results)
    agg["suite"] = "SkillsBench-compatible"
    agg["skill_used"] = bool(skill_content)
    agg["results"] = results
    return agg


def compare_with_without(skill_path: str, model: str = "", *, routed: bool = True) -> dict:
    """SkillsBench comparison: with-skill vs without-skill (category-routed)."""
    content = ""
    try:
        content = Path(skill_path).read_text(encoding="utf-8") if isinstance(skill_path, str) and "/" in skill_path else skill_path
    except Exception:
        content = skill_path
    from skillos.knowledge.skill_routing import resolve_skill_injection, load_skill_routing_info
    if isinstance(skill_path, str) and ("/" in skill_path or "\\" in skill_path):
        try:
            info = load_skill_routing_info(skill_path)
            categories = info.get("bench_categories", [])
            skill_name = info.get("name", skill_path)
            content = info.get("content", content)
        except Exception:
            categories = []
            skill_name = skill_path
    else:
        categories = []
        skill_name = skill_path[:60]
    if not routed:
        with_skill = run_skillsbench_suite(skill_content=content, model=model)
        without_skill = run_skillsbench_suite(skill_content="", model=model)
        delta = with_skill["total_score"] - without_skill["total_score"]
        return {"skill": skill_name, "with_skill_score": with_skill["total_score"], "with_skill_grade": with_skill["grade"], "without_skill_score": without_skill["total_score"], "without_skill_grade": without_skill["grade"], "delta": delta, "routed": False, "tasks": with_skill["tasks_run"]}
    matched_with = []
    matched_without = []
    cross_domain_harm = []
    for task in SKILLSBENCH_TASKS:
        inject, skill_for_task = resolve_skill_injection(task.category, content, bench_categories=categories, skill_name=skill_name)
        try:
            rw = run_task_evaluation(task.task_id, skill_content=skill_for_task)
            matched_with.append(rw)
        except Exception as e:
            matched_with.append({"task_id": task.task_id, "error": str(e)})
        try:
            rwo = run_task_evaluation(task.task_id, skill_content="")
            matched_without.append(rwo)
        except Exception as e:
            matched_without.append({"task_id": task.task_id, "error": str(e)})
        if not inject and content:
            rw_ns = matched_with[-1]
            rwo_ns = matched_without[-1]
            if "score" in rw_ns and "score" in rwo_ns:
                cross_domain_harm.append({"task_id": task.task_id, "with": rw_ns["score"], "without": rwo_ns["score"]})
    mw = _aggregate_results(matched_with)
    mwo = _aggregate_results(matched_without)
    matched_delta = mw["total_score"] - mwo["total_score"]
    harm_delta = sum(h["with"] - h["without"] for h in cross_domain_harm) if cross_domain_harm else 0
    return {"skill": skill_name, "with_skill_score": mw["total_score"], "with_skill_grade": mw["grade"], "without_skill_score": mwo["total_score"], "without_skill_grade": mwo["grade"], "matched_delta": matched_delta, "routed": True, "matched_tasks": len(matched_with), "harm_score": harm_delta, "delta": matched_delta, "tasks": len(SKILLSBENCH_TASKS)}


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
'''

header = '''"""SkillsBench-compatible deterministic task set — 88 tasks, 5 categories, 8 domains.

Exceeds official SkillsBench 84-task count.
Deterministic regex-based grading. No LLM judge needed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
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

with open(SRC, "w", encoding="utf-8") as f:
    f.write(header)
    f.write(",\n".join(tasks))
    f.write(",\n]\n")
    f.write(grader_code)

print(f"DONE: {tid} tasks + complete grader written to {SRC}")
