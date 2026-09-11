# Q2 冻结变更日志 (freeze_change_log.md)

> 规则：冻结后任何规范源变更须先记录于此，再走 rerun→refreeze 流程。

## 2026-09-11 — round4 采纳：80分位改为按星期分桶 e80[dow]（模型变更，全部重算）

- **原因**：round3 全局 80 分位风险修正导致紧急购电量呈虚假 7 天周期（周日系统性低估尖峰、周五高估）。根因是负载/光伏强星期周期（lag-7 自相关 0.943 > lag-1 0.445）与预报加权衰减方向错配；全局分位把不同星期几误差混在一起。
- **变更**：`code/Q2/q2_main.py` 将风险修正由 `np.percentile(Eerr[7:d], 80)` 改为按星期分桶 `error_quantile_dow`（第 d 天仅用 d 之前同星期几的历史误差求 80 分位）。`code/Q2/q2_robustness.py` 同步改为分桶口径并重跑。
- **影响（round3 → round4）**：
  - 总费用 17,741,097.14 → **14,559,104.58 元（−17.9%）**；
  - 紧急购电 493,945 → 396,939 kWh（−19.6%）；紧急区间 10,842 → 11,977；
  - 弃光率 33.60% → 13.40%；
  - 储能价值 16.85% → 19.88%；优化价值 1,420,408.30 → 2,012,963.89；
  - 主模型总费用现已**低于**"无储能·完美预见"下界（14.56M < 16.41M）；
  - R1 经验 argmin 由 80 移至 90（q=80 仅高 0.67%，目标平坦）。
- **性质**：模型变更，top-line 全部重算。原 round3 数值作废；robustness R1–R5 一并按分桶口径重跑。主结果表 `q2_answer_tables.md`、方法说明、结果分析、图 `fig_q2_1..5` 同步更新。

## 2026-09-11 — 扩展冻结：补充稳健性敏感性数值（纯新增）

- **原因**：G5 论文稳健性章节需引用 R2（预报窗口）、R3（效率口径）、R5（日末约束）的敏感性数值；按"论文所有数值必须来源于冻结文件"的硬约束，将这些数值并入冻结。
- **来源**：`robustness/Q2/q2_robustness_summary.json`（已产出的规范源，非新计算）。
- **新增 6 项 claim**：`q2_rob_R2_window_3day/5day/7day_uniform/14day`、`q2_rob_R3_eta_roundtrip90`、`q2_rob_R5_free_terminal`。
- **性质**：纯新增，未修改任何既有冻结值；top-line 结果 `q2_package_signoff=keep` 结论不变。

## 2026-09-11 — 再补充 3 项：R3/R5 变化量与占比（纯新增）

- **原因**：论文稳健性章节直接引用 R3 效率口径变化占比（−3.0%）、R5 日末约束费用增量（22,728.82 元，+0.13%），按"所有数值来源于冻结文件"并入。
- **来源**：`robustness/Q2/q2_robustness_summary.json`（`$.checks[2].observed.delta_pct`、`$.checks[4].observed.delta`、`$.checks[4].observed.delta_pct`）。
- **新增 3 项 claim**：`q2_rob_R3_eta_delta_pct`、`q2_rob_R5_delta`、`q2_rob_R5_delta_pct`。
- **性质**：纯新增，未修改既有冻结值。
