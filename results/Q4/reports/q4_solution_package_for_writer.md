# Q4 论文写手材料包（solution-package-builder）

> 论文写作的唯一数据源：`results/Q4/reports/frozen_numbers.json`（`q4_package_signoff` = keep）。本包聚合最终方法、结果论断、图表与决策溯源，写手无需翻找散落文件。

## 1. 最终方法与基线

- 主模型 M4：完全继承 Q2(round4)/Q3(round3) 最终模型，仅电价 `p_t → p_{d,t}`。
  - result4-2 = Q2 模型（逐日滚动 LP + 附件2 历史净负荷自预报 7 天加权 + 按星期分桶 80 分位修正 + 日闭合）。
  - result4-3 = Q3 模型（滚动 MPC 0/6/12/18 + 分段计费 + issue 分桶 80 分位光伏修正 + 日闭合）。
- 基线：B4（无储能自预报）、R4（规则套利）可执行；B4_ref（无储能完美）、A/B（储能完美）为**诊断基准，非可执行策略**。
- 完整说明：`methods/Q4/q4_final_method_explanation.md`。

## 2. 顶层论断（value / 源 / 稳健性 / 决策 / 置信度）

| 论断 | 值 | 单位 | 冻结 claim_id | 稳健性 | 决策 | 置信 |
|---|---|---|---|---|---|---|
| result4-2 总购电费 | 15,231,785.59 | 元 | q4_result4_2_total_cost | q 扫描、波动扫描 | q4_package_signoff | 高 |
| result4-3 总购电费 | 15,759,231.74 | 元 | q4_result4_3_total_cost | q 扫描 | q4_package_signoff | 高 |
| 储能价值（波动） | 3,642,268.60 | 元 | q4_storage_value | 与恒定价对比 +0.8% | q4_baseline_choice_r2 | 高 |
| 优化价值 | 2,193,710.73 | 元 | q4_optimization_value | 基线对比 | q4_baseline_choice_r2 | 高 |
| 预报误差成本（储能侧） | 2,401,299.20 | 元 | q4_forecast_error_cost_storage | 诊断 A 对照 | q4_baseline_choice_r2 | 高 |
| 预报误差成本（无储能侧） | 1,847,271.34 | 元 | q4_forecast_error_cost_no_storage | 诊断 B4_ref 对照 | q4_baseline_choice_r2 | 高 |
| 日闭合约束成本 | 49,603.10 | 元 | q4_day_closure_cost | — | q4_package_signoff | 高 |
| 完美预见总价值（储能侧） | 2,450,902.30 | 元 | q4_perfect_foresight_total_value | — | q4_package_signoff | 高 |
| 紧急购电 4-2 / 4-3 | 396,996.49 / 245,553.35 | kWh | q4_emergency_energy_42/43 | — | q4_package_signoff | 高 |
| 弃光率 4-2 / 4-3 | 13.40% / 14.80% | — | q4_curtailment_rate_42/43 | — | q4_package_signoff | 高 |
| q 最优分位（4-2/4-3） | 90 / 80 | % | q4_quantile_argmin_42/43 | R1 扫描 | q4_quantile_choice_r2 | 高 |
| 恒定价 result4-2（=Q2） | 14,559,104.58 | 元 | q4_result4_2_constant | 复现 Q2 冻结 | q4_method_choice_r2 | 高 |
| 储能套利空间 恒定/波动 | 5,927,080.51 / 6,043,567.81 | 元 | q4_storage_arbitrage_space_* | R3 | q4_package_signoff | 高 |

## 3. 关键定性结论（claim scope 由决策锁定）

1. **完美预见仅作诊断基准**（非策略）：`q4_method_choice_r2` 已纠正 round1 误用完美预见作策略的错误。
2. **储能对预报精度更敏感**：储能侧预报误差损失（240.1 万）比无储能侧（184.7 万）高 30%；预报优化收益上限 ≈ 240 万。
3. **波动电价放大储能套利（+2.0%）但更放大预报误差损失（+3.8%）并抬升基础用电成本（+3.8%）**，净总成本 +4.6%。
4. **q=80 设计值稳健**：result4-2 偏离最优 0.69%，result4-3 恰最优。

## 4. 图与表

- 图：`paper/figures/fig_q4_1_cost_comparison.png`、`fig_q4_2_cost_decomposition.png`、`fig_q4_3_quantile_sensitivity.png`（计划见 `methods/Q4/q4_figure_table_plan.md`）。
- 表：见 figure_table_plan 的 tab_q4_* 四项（值全部在冻结文件）。

## 5. 局限（写手须如实声明）

- 完美预见参照不可执行；电价视为已知（未建模电价不确定性）；自预报不含附件3（属 MPC 路径）。
- 结论适用场景：含储能微网从外部电网购电、日内 10 分钟滚动。

## 6. 决策溯源（JSONL）

`methods/Q4/q4_decisions.jsonl`：`q4_method_choice_r2`、`q4_quantile_choice_r2`、`q4_baseline_choice_r2`、`q4_package_signoff`。

## 7. 文件清单

- 主结果：`results/Q4/experiments/round2/run_summary.json`
- 稳健性：`robustness/Q4/q4_robustness_summary.json`
- 冻结：`results/Q4/reports/frozen_numbers.json`
- 方法说明：`methods/Q4/q4_final_method_explanation.md`
- 结果分析：`results/Q4/reports/q4_final_result_analysis.md`
