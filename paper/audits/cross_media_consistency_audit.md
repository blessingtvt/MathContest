# Q2 跨媒介一致性审计（consistency-auditor）

> 审计对象：`paper/sections/q2.md`（论文）
> 比对基准：`results/Q2/reports/frozen_numbers.json`（冻结数值）、`planning/symbol_table.md`（符号表）、`paper/figures/`（图表）、`code/common.py` / `methods/Q2/q2_final_method_explanation.md`（参数与公式）。

> ⚠️ **本快照对应 round3（2026-09-11 round4 采纳之前）。** round4 已将 80 分位改为按星期分桶 e80[dow]，`paper/sections/q2.md` 与 `frozen_numbers.json` 均已更新为 round4 数值（主结果总费用 14,559,104.58 元、储能价值 19.88% 等）。本文 §1 的数值表为 round3 历史记录，§5 的 F1/F2 亦针对 round3 稳健性报告；round4 下的最新一致状态见 `frozen_numbers.json` 与 `robustness/Q2/q2_robustness_report.md`（已按 round4 重生成）。建议在 final_assembly 前按 round4 重跑本审计。

## 1. 数值一致性（论文 ↔ frozen_numbers.json）

结论：**论文中出现的每一个绝对结果数值均可在 frozen_numbers.json 中找到对应 claim，无一越界。**

| 论文数值 | 冻结 claim | 一致 |
|---|---|---|
| 17,741,097.14（总费用 C2） | q2_main_total_cost | ✅ |
| 15,739,922.23（计划费） | q2_main_plan_cost | ✅ |
| 2,001,174.91（紧急费） | q2_main_emergency_cost | ✅ |
| 493,945 kWh（紧急电量） | q2_emergency_energy_kwh | ✅ |
| 2.59%（电量占比） | q2_emergency_share | ✅ |
| 10,842（紧急区间数） | q2_emergency_intervals | ✅ |
| 33.60%（弃光率） | q2_curtailment_rate | ✅ |
| 19,161,505.44 / 21,337,033.56 / 16,407,319.63（三基线） | q2_baseline_R2 / B2 / B2_ref | ✅ |
| 3,595,936.42、16.85%（储能价值） | q2_storage_value / _pct | ✅ |
| 1,420,408.30（优化价值） | q2_optimization_value | ✅ |
| 4,929,713.93（预报误差成本） | q2_forecast_error_cost | ✅ |
| 80（最优分位） | q2_optimal_quantile | ✅ |
| 57,567,252.07 / 17,793,134.79（q=0/90） | q2_quantile_q0 / q90_total | ✅ |
| 20,226,034.85 / 17,979,113.74 / 16,875,313.78 / 17,388,171.48（R2 窗口） | q2_rob_R2_window_3day/5day/7day_uniform/14day | ✅ |
| 17,203,867.05（R3 往返0.9） | q2_rob_R3_eta_roundtrip90 | ✅ |
| 17,763,825.96（R5 自由终态） | q2_rob_R5_free_terminal | ✅ |
| 22,728.82 元（R5 增量） | q2_rob_R5_delta | ✅ |
| −3.0%（R3 占比）、+0.13%（R5 占比） | q2_rob_R3_eta_delta_pct / q2_rob_R5_delta_pct | ✅ |

**相对变化说明**：R1 的"3.2 倍 / 0.3%"、R2 的"+14.0% / +1.3% / −4.9% / −2.0%"为**冻结绝对数值相除得到**的派生比例，论文已在表 5-1 前注明"相对变化由冻结值相除得到"，且 R3/R5 的占比已直接冻结，故不构成"未冻结新数字"。

**非结果类数字**（参数/描述，非冻结对象，逐一核验与代码一致）：`T=144, Δt=1/6, E_min=1200, E_max=10800, P_max=5000, η=0.9, E_0=6000, α_em=5, w=[0.3,…,0.05], SEED=2026, 334天, 单日约577变量(3×144+145=577)` —— 与 `common.py` / 方法说明一致。✅

## 2. 符号一致性（论文 ↔ symbol_table.md）

结论：**符号无前后矛盾**。逐项核对：

- 决策/状态：$x_{d,t}, z_{d,t}, c_{d,t}, q_{d,t}, E_{d,t}$ —— 与符号表 §5/§6 定义一致（计划购电/紧急购电/充电/放电/储电量）。
- 输入：$L_{d,t}, G_{d,t}, p_t$ —— §2 定义一致。
- 中间量：$N_{d,t}=L_{d,t}-G_{d,t}$（§7 第 76 行）、$\hat N_{d,t}=\sum_k w_k N_{d-k,t}$（第 77 行）、$e^q_{d,t}$（第 78 行）—— **完全复用符号表新增符号**。
- 参数：$E_{\min}, E_{\max}, P^{c}_{\max}=P^{d}_{\max}, \eta_c=\eta_d, E_0, \alpha_{em}$ —— §3/§4 一致。
- 费用：$C_2=\sum_{d,t}p_t(x_{d,t}+\alpha_{em}z_{d,t})$ —— 符号表 §7 第 73 行、§8 一致。
- 核心关系式：能量平衡 $x+z+q\ge N\Delta t+c$、储能动态 $E_{t+1}=E_t+\eta_c c_t-q_t/\eta_d$ —— 与符号表 §8 一致。
- 报童临界比 $\dfrac{\alpha_{em}-1}{\alpha_{em}-1+1}=\dfrac{4}{5}=0.8$ —— 与稳健性报告、决策台账一致。

## 3. 图表一致性（论文引用 ↔ 磁盘文件）

论文引用图 1–图 4，磁盘对应文件均存在（`paper/figures/`）：

| 论文编号 | 文件 | 存在 |
|---|---|---|
| 图 1 | fig_q2_1_quantile_sensitivity.png | ✅ |
| 图 2 | fig_q2_2_baseline_comparison.png | ✅ |
| 图 3 | fig_q2_3_representative_day.png | ✅ |
| 图 4 | fig_q2_4_monthly_cost.png | ✅ |

图 3 的"典型日 2025-03-20"与图生成脚本 `d_star=79`（3.20）一致。✅

## 4. 表格/图编号一致性

- 图：图 1–图 4 编号连续、唯一。✅
- 表：**低severity**——仅稳健性检验表编号为"表 5-1"，其余（符号说明、主模型结果、基线对比、预报窗口）未编号，建议 final_assembly 阶段统一为"表 1…表 5"顺序编号。

## 5. 发现的问题（非阻断）

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| F1 | `robustness/Q2/q2_robustness_report.md` L12/L44、`q2_robustness_summary.json` L46 | 稳健性报告称 R2"5/7/14 天 ±2%"（L44）或"−2%~+0%"（summary L46），但冻结值 7天均匀=16,875,313.78 相对基准实为 **−4.88%**；报告自身阈值实为"<5%"。**论文 §5 已按真实值写成"−4.9% ~ +1.3%"，正确**。建议修正稳健性报告措辞以匹配其自身 "<5%" 阈值。 | 低 |
| F2 | `robustness/Q2/q2_robustness_report.md` L53、`q2_robustness_summary.json` L65 | 稳健性报告称储能价值"两种口径均 >400 万元"，但基准口径储能价值=3,595,936.42 元≈359.6 万元（<400 万），仅往返口径≈413 万 >400 万。**论文 §5 R3 已改为"基准口径 3,595,936.42 元、往返口径更高"，正确**。建议修正稳健性报告措辞。 | 低 |

## 6. 结论

**PASS**。论文数值、符号、图表与 frozen_numbers.json / symbol_table.md / 磁盘图表完全一致，无越界数字、无符号矛盾、无图表错配。F1/F2 为稳健性报告（G4 遗留）的措辞不精确，已由论文正文纠正，不阻断 G6，但建议后续修正稳健性报告措辞。
