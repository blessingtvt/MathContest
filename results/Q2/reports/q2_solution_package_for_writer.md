# Q2 论文写作材料包（solution-package-builder）

> 本包是 Q2 论文写作的单一来源。数值一律引用 `frozen_numbers.json`，禁止散落引用。
> 冻结状态：**待人类确认**（q2_package_signoff）。确认后本包与冻结文件即为定稿。

## 1. 最终方法（一句话）

逐日滚动线性规划（LP）+ 附件2历史净负荷自预报（7天加权）+ 80分位风险修正（报童临界比 0.8），每天 0:00 制定当日计划，缺口按 5 倍价紧急购电兜底。

- 方法底稿：`methods/Q2/q2_final_method_explanation.md`
- 决策溯源：`q2_method_choice_r3` / `q2_information_set_r3` / `q2_baseline_choice_r3`

## 2. 顶层数值声明（全部来自 frozen_numbers.json）

| claim_id | 值 | 单位 | 稳健性支撑 |
|---|---|---|---|
| q2_main_total_cost | 17,741,097.14 | 元 | R1/R3/R4/R5 PASS |
| q2_main_plan_cost | 15,739,922.23 | 元 | — |
| q2_main_emergency_cost | 2,001,174.91 | 元 | — |
| q2_emergency_energy_kwh | 493,945.0 | kWh | — |
| q2_emergency_share | 0.025903（2.59%） | 无量纲 | — |
| q2_baseline_B2 | 21,337,033.56 | 元 | 同信息集基线 |
| q2_baseline_R2 | 19,161,505.44 | 元 | 同信息集基线 |
| q2_baseline_B2_ref | 16,407,319.63 | 元 | 诊断下界 |
| q2_storage_value | 3,595,936.42（16.85%） | 元 | R3 效率口径下仍 >400 万 |
| q2_optimization_value | 1,420,408.30 | 元 | — |
| q2_forecast_error_cost | 4,929,713.93 | 元 | — |
| q2_optimal_quantile | 80 | 分位 | R1 argmin=80 |

## 3. 图表清单

| 图/表 | 路径 | 类型 |
|---|---|---|
| 分位敏感性 | `paper/figures/fig_q2_1_quantile_sensitivity.png` | 论文正式(3) |
| 基线对比 | `paper/figures/fig_q2_2_baseline_comparison.png` | 论文正式(3) |
| 典型日调度 | `paper/figures/fig_q2_3_representative_day.png` | 论文正式(3) |
| 月度费用 | `paper/figures/fig_q2_4_monthly_cost.png` | 附录(4) |
| 主结果表 | `results/Q2/reports/frozen_numbers.json` | 论文正式(3) |

## 4. 结论声明与边界

- **支持**：储能价值 16.85%、优化价值 8.0%、风险修正使费用从无修正的 57.57M 降至 17.74M。
- **局限**：预报窗口为 ±2% 可调超参数（R2 CONDITIONAL）；效率口径影响绝对费用 −3%（HD2）；风险修正为逐区间独立分位，未建模日内自相关。
- **不适用**：Q3/Q4（需附件3 滚动预报与分段计费 β_pen/γ_pre）。

## 5. 决策溯源

- `q2_method_choice_r3`：主模型选型（逐日滚动 LP + 自预报 + 80分位）。
- `q2_information_set_r3`：信息集修正（附件3 属 Q3/Q4，Q2 用附件2历史）。
- `q2_baseline_choice_r3`：双基线同信息集。
- `q2_package_signoff`：**待人类确认**（keep/downgrade/drop）。
