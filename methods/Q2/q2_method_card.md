# Q2 Method Card（重回 G2 · 选型已确认版）

> 选型结论：**M2 = 逐日滚动 LP（单尺度 MPC）+ 日前预报（非完美预见）**；全年联合 LP 降为事后下界诊断参考。
> 决策记录：q2_method_choice_r2 / q2_information_set_r2 / q2_baseline_choice_r2（见 q2_decisions.jsonl）。

## Goal and success criteria
- 目标：全年（报告期 2.1–12.31）最小化总购电费 C2 = Σ_{d,t} p_t·(x_{d,t} + 5·z_{d,t})；供电≥负载、储能跨日连续、紧急购电按交易时刻电价 5 倍计。
- 成功标准：全年可行；费用最小；result2.xlsx 完整（计划购电量 / 充放电量 / 紧急购电量）。

## Human constraints（沿用已确认口径）
- Output form：表1/表2/表3 + result2.xlsx
- Priority：最优性 > 速度
- Unacceptable failure：任一区间供电不足或储能越界
- Experiment budget：分钟级

## 框架定位（全文 MPC 递进）
- Q1 单日静态 LP → **Q2 逐日滚动（单尺度 MPC）** → Q3 多时间尺度 MPC（0/6/12/18 日内滚动）→ Q4 波动电价 MPC。
- Q2 是 MPC 的单尺度特例：每天 0:00 仅用当天日前预报求解当天，储能跨日结转，**不跨日看未来**（时间因果律）。

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M2 | main | 逐日滚动 LP（每天 0:00 用附件3 0:00 日前光伏预报做计划，附件2 实际结算，缺口紧急购电 5 倍价补齐） | 因果可执行；精确最优；5 倍价真实生效(z>0)；分钟级 | 附件3 小时级预报需映射 10min(S8)；跨题复用附件3 | 低 |
| B2 | baseline(无储能) | 无储能：x_t=max(L·Δt−Ĝ·Δt,0)，缺口紧急购电补齐（同信息集） | 完整任务、同信息集可比 | 非最优 | 极低 |
| R2 | baseline(规则套利) | 峰谷套利（同信息集，储能跨日结转） | 完整任务、与主模型同类可比 | 规则阈值主观、非最优 | 低 |
| B2_ref | diagnostic_reference | 无储能·完美预见下界 | 仅标注预报误差成本 | 乐观下界 | 极低 |
| 全年联合 LP | diagnostic_reference | 全年一次性求解（事后下界） | 仅量化跨日耦合强度(≈0.22%) | **违反时间因果律，不作主模型** | 低 |
| F2 | conditional_fallback | 鲁棒/随机规划（显式建模光伏预报不确定性） | 若需显式不确定性优化 | 需建不确定性集/场景 | 中 |

## Baseline validity
- Real task completed：是（B2/R2 完成全年购电策略，含紧急购电，输出与主模型同构）
- Comparable：是（同「日前预报+紧急购电」信息集，储能较无储能省约 275 万元 ≈ 13.67%）
- B2_ref 与 全年联合 均为 diagnostic_reference，不作正式 baseline。

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M2 | PASS(逐日LP已证3.5s/年) | HD3日前预报已确认 | PASS | PASS | PASS | **PASS** |
| B2 | PASS | 同信息集 | PASS | PASS | PASS | **PASS** |
| R2 | PASS | 同信息集 | PASS | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：HD3 若需显式建模光伏预报不确定性（非确定性日前预报吸收）→ 启用 F2 鲁棒/随机规划。
- 现状：日前预报 + 确定性紧急购电已确认，F2 未触发。

## Compact history
- 2026-09-10 G2/G2.5：主候选 M2(逐日LP·完美预见) + 双基线(B2+R2)，HD3=完美预见（q2_method_choice / q2_baseline_choice / q2_information_set）。
- 2026-09-10 晚：主模型被"升级"为全年联合 LP，HD3 被改为日前预报——均未落签，且全年联合违反时间因果律。
- 2026-09-11 重回 G2（q2_method_choice_r2 / q2_information_set_r2 / q2_baseline_choice_r2）：主模型改回**逐日滚动 LP**，HD3=**日前预报**，全年联合降为事后下界参考；全文采用 MPC 递进框架。
