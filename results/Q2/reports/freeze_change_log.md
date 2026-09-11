# Q2 冻结变更日志 (freeze_change_log.md)

> 规则：冻结后任何规范源变更须先记录于此，再走 rerun→refreeze 流程。

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
