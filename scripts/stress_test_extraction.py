"""50+ round extraction stress test — continuous refinement + mixed content."""
import urllib.request, json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
API = 'http://127.0.0.1:8765/api/skills/dispatch'
FINALIZE = 'http://127.0.0.1:8765/api/skills/finalize'

rounds = [
    "帮我沉淀一个门诊分诊流程。病人来挂号后先测体温血压，然后问主诉和病史，判断紧急程度分级，安排对应科室。",
    "如果是发热病人要先做流行病学调查看有没有传染病接触史",
    "急诊分四级：一级生命体征不稳直接送抢救室；二级可能有危险15分内必须看到医生；三四级候诊区等",
    "问病史除了主诉还要问既往史用药史过敏史。过敏史标红",
    "有时候病人说不清楚什么毛病就靠经验判断。比如捂着肚子腰直不起来多半是急腹症",
    "发热超39度除了核酸还要血常规和CRP。查流行病学史——有没有去过疫区",
    "小孩和老人分诊标准不一样。老人血压偏高可能没事小孩偏高就要警惕了",
    "科室分得细：内科外科妇科儿科五官科皮肤科。肚子疼可能是内科胃肠炎或外科阑尾炎或妇科宫外孕",
    "所以有快速判断套路：问部位问性质问持续时间问伴随症状。右下腹痛加反跳痛八成阑尾炎。女性下腹痛加停经史查HCG",
    "儿科最头疼发烧。有个五步判断法：大于3个月先看精神状态——精神好可在家观察；精神萎靡必须留院。小于3个月不管多少度一律高危处理。这是国外儿科学会指南",
    "归纳为一测二问三判断四安排。一测生命体征：体温血压心率血氧四个必须测",
    "体温超38.5加测血氧。血氧低于95升级处理",
    "二问问病史。过敏史和用药史必须问其他看情况。三判断核心：根据生命体征和症状对照分诊标准表",
    "四安排：根据分级安排。一级直接抢救室二级优先安排三四级排队。特殊人群孕妇不管什么症状优先处理。精神科必须有陪同",
    "还有个特殊情况：暴力倾向或自伤倾向启动应急预案。通知保安通知值班医生安排独立房间专人看护",
    "传染病人在分诊台就发口罩安排单独隔离候诊区不和别人混。发热门诊有单独的分诊流程不走综合分诊台",
    "发热门诊分诊简单：测体温做核酸等结果。综合急诊复杂了啥病都有",
    "转院流程：烧伤手外伤这种建议转院。但重症必须先稳定生命体征——不稳定转出去路上出事也有责任",
    "转院前做三件事：联系接收医院确认有床、安排转运车辆、准备病历摘要",
    "所有分诊记录录入系统：生命体征数据分诊级别安排科室。以后有纠纷都是证据",
    "每4小时汇总分诊数据：各级病人比例平均等待时间转科率。这个给医务科和质量控制科",
    "对了，疫情期间我们加了一个预检分诊环节，在进大门的时候就先测体温和行程码",
    "预检发现的发热病人直接引导到发热门诊，不用经过综合分诊台——这样减少交叉感染",
    "还有，我们医院去年开始用电子分诊系统了。护士在平板勾选症状系统自动建议分诊级别",
    "不过系统只是辅助，最终决策还是护士拍板。机器说三级但护士觉得不对劲可以手动升级",
    "这个电子分诊系统的逻辑其实挺有意思：它是基于决策树的。比如选了发热+咳嗽会自动勾选呼吸道相关的问题",
    "用了半年发现一个规律：电子分诊的建议级别比人工偏保守，但误判率反而更低",
    "人工分诊有时候会因为经验足看出来病人不对劲，机器看不出来——机器只看数据",
    "所以我们现在的流程是机器建议+人工复核。两者不一致时走人工判断但要备注原因",
    "系统还会记录每次人工覆盖机器的情况，每周做一次差异分析，看哪些类型的病人机器容易误判",
    "这个数据积累下来以后可以优化决策树",
    "我觉得聊得挺全了。不过还有一个细节：分诊台要备急救箱",
    "急救箱里至少要有：血压计、血糖仪、心电图机、除颤仪。病人如果突然情况恶化分诊台能顶一下",
    "还有，分诊台的护士必须每两年复训一次急救技能，考核不过关不能独立分诊",
    "好了，这些就是完整的门诊分诊流程",
]

start = time.time()
sid = ''
stats = {'total': 0, 'generations': 0}

for i, msg in enumerate(rounds):
    body = {'message': msg, 'session_id': sid, 'mode': 'create'}
    r = json.loads(urllib.request.urlopen(
        urllib.request.Request(API, data=json.dumps(body).encode(),
                              headers={'Content-Type': 'application/json'}),
        timeout=180).read().decode())
    sid = r.get('session_id', sid)
    active = r.get('skill_active', False)
    saved = r.get('skill_saved', '')
    reply = r.get('reply', '')[:80].replace('\n', ' ')
    stats['total'] += 1
    if saved: stats['generations'] += 1
    elapsed = time.time() - start
    flag = '⚡' if saved else ('A' if active else ' ')
    print(f'R{i+1:02d} ({elapsed:5.0f}s) {flag} saved={saved[:25] if saved else "-":25s} | {reply[:55]}')
    if i > 0 and i % 20 == 0:
        try:
            rs = json.loads(urllib.request.urlopen(
                f'http://127.0.0.1:8765/api/skills/status?session_id={sid}').read().decode())
            print(f'  [STATUS] turn={rs.get("turn")} phase={rs.get("phase")} '
                  f'ctx={rs.get("context_turns")} draft={rs.get("draft_length")} chars')
        except: pass

# Finalize
print('\n=== FINALIZE v1 ===')
fr = json.loads(urllib.request.urlopen(
    urllib.request.Request(FINALIZE + '?session_id=' + sid, method='POST'),
    timeout=300).read().decode())
print(f"Saved: {fr.get('skill_saved', 'NO')}")
print(f"Reply: {fr.get('reply', '')[:250]}")

# Post-generation refinement
print('\n=== POST-GEN REFINEMENT ===')
for msg in [
    "等一下，发热门诊漏了一个环节——复诊病人要先查上次就诊记录和上次的检验结果",
    "还有疫情期间发热门诊还要加测抗原，这个也是必须的步骤",
]:
    body = {'message': msg, 'session_id': sid, 'mode': 'create'}
    r = json.loads(urllib.request.urlopen(
        urllib.request.Request(API, data=json.dumps(body).encode(),
                              headers={'Content-Type': 'application/json'}),
        timeout=180).read().decode())
    saved = r.get('skill_saved', '')
    print(f"  active={r.get('skill_active')} saved={saved[:30] if saved else '-'} | {r.get('reply','')[:70]}")

# Re-finalize
print('\n=== FINALIZE v2 (with refinements) ===')
fr2 = json.loads(urllib.request.urlopen(
    urllib.request.Request(FINALIZE + '?session_id=' + sid, method='POST'),
    timeout=300).read().decode())
print(f"Saved: {fr2.get('skill_saved', 'NO')}")

total = time.time() - start
print(f'\n=== SUMMARY: {stats["total"]} rounds in {total:.0f}s, {stats["generations"]} generations ===')
