# 参考文献审计报告（reference-manager）

> 时间：2026-09-11
> 结论：4 条参考文献全部真实、可溯源，无虚构文献。

## 1. 引用清单与状态

| # | 引用键 | 论文位置 | 支撑论点 | 状态 |
|---|---|---|---|---|
| [1] | Kaur2024LP | 参考文献 | 微网能量管理的 LP 优化建模 | ✅ 已核验 |
| [2] | Lautert2024MILP | 参考文献 | 微网最优功率调度 MILP（含光伏/储能/实时电价） | ✅ 已核验 |
| [3] | Alguhi2025BESS | 参考文献 | 并网微网电池储能最优运行（SoC 约束/充放调度） | ✅ 已核验 |
| [4] | CUMCM2026C | 参考文献 | 竞赛试题来源 | ✅ 已核验 |

## 2. 核验来源（元数据经 Web 检索确认）

| # | 文献 | 核验到的元数据 |
|---|---|---|
| [1] | Energy Management in Microgrid using Linear programming Optimization | Kaur, S. & Surbhi；2024 15th ICCC NT（IEEE）；DOI 10.1109/ICCCNT61001.2024.10726110 |
| [2] | Optimal power dispatch in microgrids using mixed-integer linear programming | Lautert, R. R., Cambambi, C. A. C., Ortiz, M. S., Wolter, M., Canha, L. N.；Automatisierungstechnik 72(11):1030–1040, 2024；DOI 10.1515/auto-2024-0094 |
| [3] | Optimal Operation of Battery Energy Storage Systems in Microgrid-Connected Distribution Networks... | Alguhi, A. A. & Alotaibi, M. A.；Energies 18(23):6335, 2025；DOI 10.3390/en18236335 |
| [4] | 2026 年高教社杯全国大学生数学建模竞赛 C 题 | 竞赛组委会（试题） |

## 3. 虚构风险

- 无占位符作者（如 "Someone"）、无伪造 DOI、无"装饰性"引用。✅
- 所有文献均支撑 Q1 的 LP/MILP 微网调度方法论，与论文方法（线性规划 + 储能充放电调度）直接相关。✅

## 4. 建议

- 提交前可按 DOI 到 CrossRef / IEEE Xplore / MDPI 复核卷期页码（当前元数据已由 Web 检索确认，风险低）。
- 若需强化，可在"模型评价/结论"处补充引用 [2] 或 [3] 的对比说明；当前引用密度对单问论文已足够。

## 5. 产出文件

- `papers/Q1_refs.bib` — 4 条 BibTeX 条目（@inproceedings / @article / @article / @misc）
