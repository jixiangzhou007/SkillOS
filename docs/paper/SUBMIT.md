# arXiv 投稿 Checklist — Paper 1

> **标题**：*Experience ≠ Knowledge: An Epistemology Engine for Agent Skill Quality*  
> **源文件**：[`paper.tex`](paper.tex) · **实验数据**：[`experiments/epistemic_results.md`](experiments/epistemic_results.md)
> **状态**：2026-06-20 更新（84 commits baseline）

---

## 投稿前

- [ ] 本地编译 PDF 通过（需 MiKTeX/TeX Live）
- [x] 摘要含最新数据（235 runs, 4,400+ claims, 100% S_route）
- [x] Domain DNA (§3) + Gate semantics + 12 disciplines 章节
- [x] Evaluation 数据与 experiments/ 一致
- [x] Limitations 记录 audit JSON parsing fix
- [ ] 作者列表、邮箱、机构确认
- [ ] 代码可用性 URL 有效（或改为实际仓库地址）
- [ ] 引用 AgentSkills.io、SkillOpt、Popper 等 bibitem 完整

## 编译

```bash
cd docs/paper
pdflatex paper.tex
pdflatex paper.tex   # 第二次解决交叉引用
# 输出: paper.pdf
```

Windows（需安装 TeX Live / MiKTeX）：

```powershell
cd D:\SkillOS\docs\paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

## arXiv 元数据（建议）

| 字段 | 值 |
|------|-----|
| Primary category | cs.AI |
| Cross-list | cs.SE, cs.CL |
| Comments | 8 pages, code available |
| ACM class | I.2.7; I.2.11 |

## 提交材料

1. `paper.pdf`（主文）
2. `paper.tex` + figures（若 arXiv 要求 source）
3. 可选 supplementary：`data/benchmarks/epistemic/claims.jsonl`

## 投稿后

- [ ] 更新 README 论文链接
- [ ] CHANGELOG 注明 preprint URL
- [ ] 产品 demo 视频链到 Phase 4 脚本（`docs/demo/PHASE4_DEMO_SCRIPT.md`）

## 已知限制（须在 rebuttal 准备）

- 离线 ablation 使用启发式证伪；`--with-llm` 结果可附录补充
- 100 条标注为单人 v0，无 inter-rater
- 结构 benchmark 仅 3 个 skill case

## 证据链（产品叙事对齐）

- 学术：Table~\ref{tab:epistemic-ablation} + 结构 S_route 100% vs 0%
- 产品：Cursor MCP + 飞书 Hermes checklist + USER_GUIDE 话术
