# Q2 论文写作材料支撑表单（G5）

> 用途：撰写「问题二：全年逐日滚动购电策略」论文所需的全部材料清单、数值来源与写作约束。
> 配套：`results/Q2/reports/q2_paper_draft.md`（论文初稿，同目录）。
> 硬约束：论文正文所有**数值声明**一律引用 `results/Q2/reports/frozen_numbers.json`（40 项 claim），严禁手工编辑；**题目要求的输出表**（购电/充放电/紧急购电）直接引用 `results/Q2/result2.xlsx` 与 `results/Q2/q2_answer_tables.md`（求解产出的权威答案，非手工编辑）。

## 1. 题目与输出要求（问题二）

- **条件**：电价每天相同（附件 1）；负载与光伏逐日变化（附件 2 实际值）；供电 < 负载时以紧急购电补齐，紧急购电价 = 交易时刻电价 × 5（$\alpha_{em}=5$）；其余按计划购电量计费。
- **信息集**：每天 0:00 依据当日已有信息制定当日计划（附件 3 光伏预报属 Q3/Q4，Q2 只能由附件 2 历史自预报）。
- **决策**：每天计划购电量、储能充放电量、紧急购电量。
- **目标**：最小化报告期（2025-02-01 ~ 12-31，共 334 天）总购电费（计划 + 紧急）。
- **输出**：表 1（购电量/全天购电费）、表 2（充放电量/0:00 与 24:00 储电量）、表 3（紧急购电量）共指定 4 个日期（2025.3.20 / 6.21 / 9.23 / 12.21）；`result2.xlsx`（2025.2.1–12.31）。

## 2. 数值权威来源

| 材料 | 路径 | 用途 |
|---|---|---|
| 冻结数值 | `results/Q2/reports/frozen_numbers.json` | 论文正文全部数值声明的唯一来源（40 项 claim） |
| 答案表 | `results/Q2/result2.xlsx`、`results/Q2/q2_answer_tables.md` | 题目要求的表 1/2/3 逐项值 |
| 稳健性 | `robustness/Q2/q2_robustness_summary.json` | R1–R5 数值（已纳入 frozen） |
| 扩展对照 | `results/Q2/experiments/optimization/causal_scenario_summary.json`、`c_risk_comparison.json` | 随机模型（已纳入 frozen `q2_ext_*`） |

## 3. 符号表复用清单（严格沿用 `planning/symbol_table.md`）

| 符号 | 含义 | 单位 |
|---|---|---|
| $d,t,T,\Delta t$ | 日期序号、日内区间序号（$t=1..T$，$T=144$，$\Delta t=1/6$ h） | — |
| $p_t$ | 恒定日电价（附件 1） | 元/kWh |
| $L_{d,t},G_{d,t}$ | 第 $d$ 天区间 $t$ 实际负载、光伏实际功率（附件 2） | kW |
| $N_{d,t}$ | 净负荷 $=L_{d,t}-G_{d,t}$ | kW |
| $\hat N_{d,t}$ | 净负荷自预报（前 7 天加权） | kW |
| $e^q_{d,t}$ | 历史**同星期**误差 $q$ 分位风险修正（$q=80$） | kW |
| $x_{d,t},z_{d,t}$ | 计划购电量、紧急购电量 | kWh |
| $c_{d,t},q_{d,t}$ | 充电电量、放电电量 | kWh |
| $E_{d,t}$ | 区间 $t$ 末储电量 | kWh |
| $E_{\min},E_{\max}$ | 储电量下/上限 $=1200/10800$ | kWh |
| $P^c_{\max}=P^d_{\max}$ | 最大充/放电功率 $=5000$ | kW |
| $\eta_c,\eta_d$ | 充/放电效率 $=0.9$ | — |
| $E_0$ | 初始储电量 $=6000$ | kWh |
| $\alpha_{em}$ | 紧急购电系数 $=5$ | — |
| $C_2$ | 报告期总购电费 $=\sum_{d,t}p_t(x_{d,t}+\alpha_{em}z_{d,t})$ | 元 |

> 复用规则：不新增符号；`e^q_{d,t}` 的分桶口径（仅用同星期几历史）在正文文字说明，不改符号。扩展模型的局部记号（场景概率 $\pi_s$、CVaR 权重 $\rho=0.2$、置信水平 0.9）仅在扩展章节内局部定义，与主模型符号不冲突。

## 4. 方法底稿（一句话）

逐日滚动线性规划（LP）+ 附件 2 历史净负荷自预报（7 天加权 $w=[0.3,0.2,0.15,0.12,0.1,0.08,0.05]$）+ 80 分位**按星期分桶**风险修正（报童临界比 0.8），每天 0:00 制定当日计划，缺口按 5 倍价紧急购电兜底。

- 底稿：`methods/Q2/q2_final_method_explanation.md`
- 溯源：`q2_method_choice_r3` / `q2_information_set_r3` / `q2_baseline_choice_r3`；签核 `q2_package_signoff=confirmed_keep`（round4）。

## 5. 图表清单（10 图 + 7 表）

### 5.1 图（显示编号 ↔ 文件 ↔ 结论 ↔ 章节）

| 图 | 文件 | 支撑结论 | 章节 |
|---|---|---|---|
| 图 1 | `fig_q2_6_netload_acf.png` | 净负荷滞后 7 天自相关 ≈0.945 远大于滞后 1 天 ≈0.467 → 强星期周期 | §3.1 |
| 图 2 | `fig_q2_7_dow_bucket_effect.png` | 按星期分桶消除周日尖峰、各星期趋于均衡 | §3.2 |
| 图 3 | `fig_q2_3_representative_day.png` | 典型日"低谷充电、高峰放电"时移策略 | §4.2 |
| 图 4 | `fig_q2_4_monthly_cost.png` | 逐月费用构成（计划 vs 紧急） | §4.2 |
| 图 5 | `fig_q2_5_seasonal_emergency.png` | 紧急购电"梅雨高、冬季低"季节特征 | §4.2 |
| 图 6 | `fig_q2_8_storage_daily.png` | 储能逐日充放电与日末储电量 | §4.2（附录） |
| 图 7 | `fig_q2_2_baseline_comparison.png` | 主模型相对双基线的降费与储能价值 | §4.3 |
| 图 8 | `fig_q2_1_quantile_sensitivity.png` | 经验 argmin=90、q=80 仅高 0.67%（目标平坦） | §5 R1 |
| 图 9 | `fig_q2_9_stochastic_risk.png` | 随机模型降低紧急购电主体分布与尾部生存曲线 | §5 扩展 |
| 图 10 | `fig_q2_10_stochastic_timeseries.png` | 随机模型在夏季尖峰日削峰 | §5 扩展 |

### 5.2 表（显示编号 ↔ 内容 ↔ 来源）

| 表 | 内容 | 来源 |
|---|---|---|
| 表 1 | 主模型结果汇总 | `frozen_numbers.json`（`q2_main_*`、`q2_emergency_*`、`q2_curtailment_rate`） |
| 表 2 | 主模型/双基线/派生价值对比 | `frozen_numbers.json`（`q2_baseline_*`、`q2_storage_value` 等） |
| 表 3 | 指定日期购电量/全天购电费（题目表 1） | `q2_answer_tables.md` 表 1 |
| 表 4 | 指定日期充放电量/储电量（题目表 2） | `q2_answer_tables.md` 表 2 |
| 表 5 | 指定日期紧急购电量汇总（题目表 3，完整逐区间见 result2.xlsx） | `q2_answer_tables.md` 表 3 |
| 表 6 | 稳健性五检验 R1–R5 | `frozen_numbers.json`（`q2_rob_*`） |
| 表 7 | 确定性模型 vs 随机模型尾部风险对照 | `frozen_numbers.json`（`q2_ext_*`、`q2_ext_B_*`） |

## 6. 顶层数值声明（全部来自 frozen_numbers.json）

| claim_id | 值 | 单位 |
|---|---|---|
| q2_main_total_cost | 14,559,104.58 | 元 |
| q2_main_plan_cost | 13,008,179.66 | 元 |
| q2_main_emergency_cost | 1,550,924.93 | 元 |
| q2_emergency_energy_kwh | 396,939.32 | kWh |
| q2_emergency_intervals | 11,977 | 区间 |
| q2_emergency_share | 0.020816（2.08%） | 无量纲 |
| q2_baseline_B2 | 18,172,127.42 | 元 |
| q2_baseline_R2 | 16,572,068.47 | 元 |
| q2_baseline_B2_ref | 16,407,319.63 | 元 |
| q2_storage_value | 3,613,022.84（19.88%） | 元 |
| q2_optimization_value | 2,012,963.89 | 元 |
| q2_forecast_error_cost | 1,764,807.79 | 元 |
| q2_curtailment_rate | 0.133985（13.40%） | 无量纲 |
| q2_optimal_quantile | 80 | 分位 |

## 7. 稳健性五检验（frozen `q2_rob_*`）

| 检验 | 结果 |
|---|---|
| R1 分位最优性 | 经验 argmin=90（14,461,289.17），q=80 仅高 0.67%；q=0 达 25,093,998.32 |
| R2 预报窗口 | 3/5/7 天均匀 +0.27%/+0.21%/+0.69%，14 天 +4.76%；7 天加权最低 → CONDITIONAL |
| R3 效率口径 | 往返 0.9 口径 14,092,449.45（−3.2%） |
| R4 电价线性 | 精确线性缩放（无放大） |
| R5 日末循环 | 自由终态 14,567,758.84（+8,654.26，+0.06%） |

## 8. 扩展对照（随机模型，frozen `q2_ext_*`）

| claim_id | 值 | 相对确定性模型 |
|---|---|---|
| q2_ext_C_total_cost | 14,565,811.29 元 | +0.046% |
| q2_ext_C_emergency_cost | 1,145,005.50 元 | −26.2% |
| q2_ext_C_emergency_energy_kwh | 293,193.98 kWh | −26.1% |
| q2_ext_C_max_daily_emergency | 55,443.06 元 | −6.4% |
| q2_ext_C_CVaR90_emergency | 17,705.46 元 | −2.4% |
| q2_ext_C_days_emg_gt5000 | 54 日 | −41%（B 92 日） |
| q2_ext_C_curtailment_rate | 0.179154（17.92%） | +4.5pp（B 13.40%） |

> **诚实表述要点（务必写进论文）**：随机模型的"总费用相当"由其更优的星期分桶预报（blend25）驱动，而非随机规划本身；若随机模型改用与确定性模型相同的 7 天加权预报，总费用升至约 17.44M，显著劣于确定性模型。故随机模型是"扩展对照"而非"更优替代"。

## 9. 结论声明与边界

- **支持**：储能价值 19.88%、优化价值 13.8%、预报误差成本 1,764,807.79；主模型总费用低于"无储能·完美预见"下界 16,407,319.63。
- **季节规律**（定性，由图 5 支撑，不引未冻结的月度 kWh 数值）：紧急购电由预报误差波动驱动，梅雨期（6 月）高、冬季（12 月）低。
- **局限**：预报窗口为可调超参数（R2 CONDITIONAL）；效率口径影响绝对费用 −3%（HD2）；风险修正为逐区间独立分位，未建模日内自相关。
- **不适用**：Q3/Q4（需附件 3 滚动预报与分段计费 $\beta_{pen}/\gamma_{pre}$）。

## 10. 参考文献（全部真实可查证）

[1] 2026 年全国大学生数学建模竞赛 C 题《微网与外部电网电力调控策略》题目与附件 1–5。
[2] 姜启源, 谢金星, 叶俊. 数学模型（第四版）[M]. 北京: 高等教育出版社, 2011.
[3] Dantzig G B. Linear Programming and Extensions[M]. Princeton: Princeton University Press, 1963.
[4] Huangfu Q, Hall J A J. Parallelizing the dual revised simplex method[J]. Mathematical Programming Computation, 2018, 10(1): 119–142.
[5] Silver E A, Pyke D F, Peterson R. Inventory Management and Production Planning and Scheduling[M]. 3rd ed. New York: John Wiley & Sons, 1998.

## 11. 写作硬约束与润色要点（paper-polisher）

1. **冻结纪律**：正文数值一律引用 `frozen_numbers.json`，不引 `run_summary.json`/`q2_final_result_analysis.md` 中未冻结的月度 kWh、弃光 kWh 等中间量；派生比例仅由冻结绝对数值相除并注明。
2. **符号一致**：严格复用 `planning/symbol_table.md`，同一符号全文同义，不前后矛盾；`q` 的放电量义（$q_{d,t}$）与分位义（$e^q_{d,t}$ 上标）不混淆。
3. **杜绝夸大**：不写"最优/大幅/显著优于"等无冻结数值支撑的措辞；"总费用相当"如实归因于预报口径差异。
4. **时态统一**：建模与结果用一般现在时陈述；求解过程叙述（"我们构造/求解/得"）用完成时；不混用。
5. **公式行文一致**：正文公式与符号表核心关系式（能量平衡、储能动态、购电费用）逐字一致；净负荷口径 $N=L-G$ 与符号表 $\hat N$、$e^q$ 一致。
6. **图表齐全**：图 1–10 全部插入并在正文解释；表 1–7 全部给出且格式统一（数值右对齐、单位标注、表题在上）。
