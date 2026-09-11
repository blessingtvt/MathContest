# Q4 Method Card（G2 重入，对齐前三问最终模型）

## Goal and success criteria
- 目标：波动电价（附件4）下重解 Q2（result4-2）与 Q3（result4-3），最小化总购电费。
- 成功标准：result4-2.xlsx、result4-3.xlsx 完整；波动电价正确接入费用函数；**与 Q2(round4)/Q3(round3) 最终模型结构一致，仅电价 p_t→p_{d,t}**。

## 子问题拆解（method-selector 对每个子问题输出）
- **Q4a（=result4-2，对应 Q2）**：逐日滚动 LP + 附件2历史净负荷自预报（7 天加权）+ 按星期分桶 80 分位风险修正 + 日闭合 E(144)=E(0)=6000，仅电价 p_t→p_{d,t}。
- **Q4b（=result4-3，对应 Q3）**：滚动 MPC（0:00 计划 + 6/12/18 调整）+ 分段计费 + 日闭合 + 按 issue 分桶 80 分位光伏风险修正 δ=[0,1005.49,−6.27,0]，仅电价 p_t→p_{d,t}。

## 关键纠偏（相对 round1，round1 数值作废）
- round1 result4-2 误用 `full_year_lp`（全年联合·完美预见·无修正），与 Q2 最终模型（逐日滚动·自预报·星期80分位）不一致 → 改为逐日滚动自预报。
- round1 result4-3 误用 `q3_mpc_day(delta=None)`（无光伏修正），与 Q3 最终模型（issue-80分位修正）不一致 → 补 δ 修正。

## Human constraints（默认，选择卡确认）
- Output form：result4-2.xlsx + result4-3.xlsx + 论文结果表
- Priority：最优性 > 速度
- Unacceptable failure：电价错配（用错恒定/波动电价）；信息集错配（result4-2 误用完美预见/附件3、result4-3 漏光伏修正）
- Experiment budget：分钟级

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M4 | main | 波动电价下继承 Q2/Q3 最终模型（各自自预报/滚动MPC + 各自80分位风险修正 + 日闭合），p_t→p_{d,t} | 仅费用函数电价变化，骨架已由 Q2 round4 / Q3 round3 验证 | 极端低价 0.0076（0.05%）诱导激进套利；风险修正分位在波动价下可能偏移 | 低 |
| B4 | baseline（无储能） | 同 Q2 自预报信息集的无储能基准：x_t=max(N^safe·Δt,0)，缺口紧急 | 完整任务、费用可比较 | 非最优 | 极低 |
| R4 | baseline（规则套利） | 波动电价峰谷套利（低价充满、高价放空、余下购电补缺口） | 完整任务、量化优化价值 | 规则阈值主观、非最优 | 低 |
| B4_ref | diagnostic_reference | 无储能·完美预见·波动电价（用真实净负荷） | 诊断下界，量化预报误差成本 | 不可执行（完美预见） | 极低 |
| F4 | fallback | 继承 F2(HD3)/F3(HD4)；极端电价退化时加最低充电价阈值或次优目标（最小弃光） | 口径/退化触发时启用 | — | — |

## Baseline validity
- Real task completed：是（B4/R4 完成真实任务）
- Comparable：是（同信息集、同计费、同日闭合）
- B4_ref 为 diagnostic_reference（完美预见，不可执行），不满足 baseline 要求但保留作诊断下界

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M4 | PASS（骨架已验证） | 信息集对齐待 G3 实现；继承 HD3/HD4 | CONDITIONAL（极端电价） | PASS | PASS（≈15 s） | **CONDITIONAL** |
| B4 | PASS | — | PASS | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：HD3/HD4 口径变化 → 分别继承 F2/F3；极端低价 0.0076 导致储能解退化 → 加最低充电价阈值或次优目标（最小弃光）。

## Compact history
- 2026-09-10 G2/G2.5：M4(波动电价 LP/MPC) + B4 + F4；round1 已冻结（数值作废）。
- 2026-09-12 G2 重入：round1 与 Q2(round4)/Q3(round3) 最终模型不一致（result4-2 误用完美预见、result4-3 漏光伏修正），重做 G2 对齐。
- 2026-09-12 G2.5：人类确认（q4_method_choice_r2）完全继承 Q2/Q3 最终模型仅换电价；（q4_quantile_choice_r2）风险修正分位 q=80 为主 + G3 扫描验证；（q4_baseline_choice_r2）双基线 B4+R4 + 诊断下界 B4_ref。
