# Q2 论文写作材料包（solution-package-builder）

> 本包是 Q2 论文写作的单一来源。数值一律引用 `frozen_numbers.json`，禁止散落引用。
> 冻结状态：**已确认 keep（round4：按星期分桶 80 分位）**。round3 数值作废。round4 为唯一主模型；随机规划扩展（C）为纯新增的稳健性/对照章节，不改动主结果。

## 1. 最终方法（一句话）

逐日滚动线性规划（LP）+ 附件2历史净负荷自预报（7天加权）+ 80分位**按星期分桶**风险修正（报童临界比 0.8），每天 0:00 制定当日计划，缺口按 5 倍价紧急购电兜底。

- 方法底稿：`methods/Q2/q2_final_method_explanation.md`
- 决策溯源：`q2_method_choice_r3` / `q2_information_set_r3` / `q2_baseline_choice_r3`

## 2. 顶层数值声明（全部来自 frozen_numbers.json）

| claim_id | 值 | 单位 | 稳健性支撑 |
|---|---|---|---|
| q2_main_total_cost | 14,559,104.58 | 元 | R1/R2/R3/R4/R5 PASS |
| q2_main_plan_cost | 13,008,179.66 | 元 | — |
| q2_main_emergency_cost | 1,550,924.93 | 元 | — |
| q2_emergency_energy_kwh | 396,939.32 | kWh | — |
| q2_emergency_share | 0.020816（2.08%） | 无量纲 | — |
| q2_baseline_B2 | 18,172,127.42 | 元 | 同信息集基线 |
| q2_baseline_R2 | 16,572,068.47 | 元 | 同信息集基线 |
| q2_baseline_B2_ref | 16,407,319.63 | 元 | 诊断下界（M2 已低于此界） |
| q2_storage_value | 3,613,022.84（19.88%） | 元 | R3 效率口径下仍 >330 万 |
| q2_optimization_value | 2,012,963.89 | 元 | — |
| q2_forecast_error_cost | 1,764,807.79 | 元 | — |
| q2_optimal_quantile | 80 | 分位 | 报童理论；经验 argmin=90（仅高 0.67%） |

## 3. 图表清单

| 图/表 | 路径 | 类型 |
|---|---|---|
| 分位敏感性 | `paper/figures/fig_q2_1_quantile_sensitivity.png` | 论文正式(3) |
| 基线对比 | `paper/figures/fig_q2_2_baseline_comparison.png` | 论文正式(3) |
| 典型日调度 | `paper/figures/fig_q2_3_representative_day.png` | 论文正式(3) |
| 月度费用 | `paper/figures/fig_q2_4_monthly_cost.png` | 附录(4) |
| 紧急购电季节性 | `paper/figures/fig_q2_5_seasonal_emergency.png` | 论文正式(3) |
| 净负荷周周期(ACF) | `paper/figures/fig_q2_6_netload_acf.png` | 论文正式(3) |
| 分桶前后对比 | `paper/figures/fig_q2_7_dow_bucket_effect.png` | 论文正式(3) |
| 储能日充放 | `paper/figures/fig_q2_8_storage_daily.png` | 附录(4) |
| 随机规划尾部风险 | `paper/figures/fig_q2_9_stochastic_risk.png` | 论文正式(3) |
| 指定日期结果表 | `results/Q2/q2_answer_tables.md` | 论文正式(3) |
| 主结果表 | `results/Q2/reports/frozen_numbers.json` | 论文正式(3) |

## 4. 结论声明与边界

- **支持**：储能价值 19.88%、优化价值 13.8%、星期分桶风险修正使费用从无修正的 25.09M 降至 14.56M；主模型总费用低于"无储能·完美预见"下界 16.41M。
- **季节规律**：紧急购电由预报误差波动驱动，6 月梅雨期最高（72,144 kWh）、12 月冬季最低（20,780 kWh）——非"冬高夏低"；净负荷水平（冬高）只推高计划购电、不推高紧急购电。
- **局限**：预报窗口为 ±2% 可调超参数（R2 CONDITIONAL）；效率口径影响绝对费用 −3%（HD2）；风险修正为逐区间独立分位，未建模日内自相关。
- **不适用**：Q3/Q4（需附件3 滚动预报与分段计费 β_pen/γ_pre）。

## 5. 随机规划扩展（C，纯新增）

> 定位：round4 主模型不变；C 作为"同一因果信息集下的显式不确定性建模 + CVaR 尾部风险约束"的**扩展对照**，写入稳健性/讨论章节。

- 代码：`code/Q2/Q2new_methods/q2_causal_scenario.py`（多场景随机规划 + CVaR）、`code/Q2/Q2new_methods/q2_c_risk_compare.py`（B/C 尾部风险对照）。
- 来源：`results/Q2/experiments/optimization/causal_scenario_summary.json`、`c_risk_comparison.json`。

| claim_id | 值 | 单位 | 对照（B=round4） |
|---|---|---|---|
| q2_ext_C_total_cost | 14,565,811.29 | 元 | B 14,559,104.58（+0.046%） |
| q2_ext_C_plan_cost | 13,420,805.79 | 元 | B 13,008,179.66 |
| q2_ext_C_emergency_cost | 1,145,005.50 | 元 | B 1,550,924.93（−26.2%） |
| q2_ext_C_emergency_energy_kwh | 293,193.98 | kWh | B 396,939.32 |
| q2_ext_C_curtailment_rate | 0.179154（17.92%） | 无量纲 | B 13.40% |
| q2_ext_C_max_daily_emergency | 55,443.06 | 元 | B 59,224.31（−6.4%） |
| q2_ext_C_CVaR90_emergency | 17,705.46 | 元 | B 18,134.56（−2.4%） |
| q2_ext_C_days_emg_gt5000 | 54 | 日 | B 92（−41%） |

**诚实表述要点（务必写进论文）**：C 的"总费用相当"由 blend25 预报（weekday4 星期分量）驱动；随机规划 + CVaR 本身在此恒定价设定下不降低 total，而是把尾部风险部分转移为计划多购/弃光（弃光率 +4.5pp）。若 C 改用与 B 相同的 weighted7 预报（ρ=0.2），总费用升至 17.44M，显著劣于 B。故 C 是"扩展对照"而非"更优替代"。

## 6. 决策溯源

- `q2_method_choice_r3`：主模型选型（逐日滚动 LP + 自预报 + 80分位）。
- `q2_information_set_r3`：信息集修正（附件3 属 Q3/Q4，Q2 用附件2历史）。
- `q2_baseline_choice_r3`：双基线同信息集。
- `q2_package_signoff`：**confirmed_keep（round4，按星期分桶 80 分位，2026-09-11 采纳）**。
