# Q2 Method Card

## Goal and success criteria
- 目标：全年(报告期2.1-12.31)最小化总购电费 C2=Σ p_t·(x_{d,t}+5·z_{d,t})，供电≥负载、储能跨日连续、紧急购电5倍价。
- 成功标准：全年可行；费用最小；result2.xlsx 完整（计划购电量/充放电量/紧急购电量）。

## Human constraints（默认，选择卡确认）
- Output form：表1/表2/表3 + result2.xlsx
- Priority：最优性 > 速度
- Unacceptable failure：任一区间供电不足或储能越界
- Experiment budget：分钟级（实测3.5s/年）

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M2 | main | 逐日滚动 LP（完美预见，储能跨日） | 精确最优、全年3.5s、1378万元 | 解退化；依赖HD3完美预见 | 低 |
| B2 | baseline(无储能) | 无储能：x_t=max(L·Δt−G·Δt,0) | 完整任务、费用可比较(1830万元) | 非最优 | 极低 |
| R2 | baseline(规则套利) | 峰谷套利：低价充到满、高价放到空，余下购电补缺口 | 完整任务、与主模型同类可比(均含储能) | 规则阈值主观、非最优 | 低 |
| F2 | fallback | 鲁棒/随机规划(场景法) | 若HD3判定非完美预见 | 需建不确定性集/场景 | 中 |

## Baseline validity
- Real task completed：是
- Comparable：是（储能较无储能全年省约452万元≈24.7%）
- 双基线：B2 无储能(诊断下限) + R2 规则套利(正式 baseline)

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M2 | PASS(3.5s/年) | 完美预见HD3待确认 | CONDITIONAL | PASS | PASS | **PASS** |
| B2 | PASS | — | PASS | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：HD3 判定"非完美预见" → 启用 F2 鲁棒/随机规划。
- 现状：HD3 已确认"完美预见"，F2 不触发。

## Compact history
- 2026-09-10 G2：主候选 M2(逐日LP) + 基线 B2(无储能) + 备用 F2(鲁棒)；探针 PASS。
- 2026-09-10 G2.5：人类确认 M2 主模型 + HD3完美预见(F2不触发) + 双基线(B2无储能+R2规则套利)。见 q2_decisions.jsonl
