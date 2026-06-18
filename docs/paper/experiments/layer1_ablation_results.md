# Layer 1 Ablation — HERITAGE × Pack-Scoped Inject

> **日期**：2026-06-18  
> **产物**：`data/benchmarks/ablation_1781759573.json`  
> **代码**：`skillos/evaluation/ablation.py` · `python scripts/archive/run_ablation.py`

## 设计

2×2 factorial（domain-only Quick8，pack 注册任务）：

| 条件 | HERITAGE（应答速查） | Pack-scoped inject |
|------|:-------------------:|:------------------:|
| **full** | ✓ | ✓ |
| **no_heritage** | ✗ | ✓ |
| **no_pack_scope** | ✓ | ✗ |
| **baseline** | ✗ | ✗ |

- **HERITAGE off**：`strip_heritage_sections()` 移除应答速查段，保留 S_body/S_route
- **Pack off**：`pack_scoped_inject=False`，关闭 pack 强制注入与非 pack 题屏蔽

## 泛化 cohort 中位 domain Δ

| 条件 | Median Δ |
|------|----------|
| HERITAGE+pack | **+45** |
| −HERITAGE | 0 |
| −pack | 0 |
| baseline | 0 |

**平均边际（3 技能）**：heritage **+23.3** · pack **+24.7** · 交互 **+23.3**

## 分技能矩阵

| 技能 | full | −HERITAGE | −pack | baseline |
|------|------|-----------|-------|----------|
| 财务报销审计 | +46 | −24 | 0 | 0 |
| 安全合规审计 | +45 | +45 | +17 | +17 |
| 合同法务审核 | 0 | 0 | 0 | 0 |
| 电商退款（参考） | +28 | +28 | +28 | +28 |

## 结论（论文可用）

1. **层 1 提分可量化**：去掉 HERITAGE 或 pack 路由，泛化 cohort 中位 Δ 从 +45 归零。
2. **两因子互补**：财务技能需 HERITAGE+pack 同时开启；安全技能 pack 路由贡献更大，HERITAGE 边际接近 0（S_body 已够用）。
3. **参考技能对照**：电商退款四组均为 +28——规则已写入 S_body，静态/动态应答速查段对 bench 边际为 0。
4. **哲学 DNA（Layer 0）不直接参与 bench 注入打分**；它塑造萃取结构，提分主因在 Layer 1 HERITAGE + 路由。

## 复现

```powershell
# 需 DEEPSEEK_API_KEY
python scripts/archive/run_ablation.py
# 跳过参考技能
$env:SKILLOS_ABLATION_SKIP_REF='1'
python scripts/archive/run_ablation.py
```
