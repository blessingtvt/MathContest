# Q4 Method Card

## Goal and success criteria
- 目标：波动电价(附件4)下重解 Q2、Q3，最小化总购电费。
- 成功标准：result4-2.xlsx、result4-3.xlsx 完整；波动电价正确接入费用函数。

## Human constraints（默认，选择卡确认）
- Output form：result4-2.xlsx + result4-3.xlsx + 论文计算结果
- Priority：最优性 > 速度
- Unacceptable failure：电价错配(用错恒定/波动电价)
- Experiment budget：分钟级

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M4 | main | 波动电价 LP/MPC（p_t→p_{d,t} 重解 Q2/Q3） | 仅费用函数变化，骨架复用 | 极端低价0.0076诱导激进套利 | 低 |
| B4 | baseline(无储能) | 波动电价无储能基准 | 完整任务、费用可比较 | 非最优 | 极低 |
| R4 | baseline(规则套利) | 峰谷套利：低价充到满、高价放到空，余下购电补缺口 | 完整任务、量化优化价值 | 规则阈值主观、非最优 | 低 |
| F4 | fallback | 继承 F2(HD3)/F3(HD4) | 口径变化时启用 | — | — |

## Baseline validity
- Real task completed：是
- Comparable：是
- 双基线：B4 无储能(诊断下限) + R4 规则套利(正式 baseline)

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M4 | PASS(骨架已验证) | 极端电价待G3检验；继承HD3/HD4 | CONDITIONAL | PASS | PASS(≈3.5s+14s) | **PASS** |
| B4 | PASS | — | PASS | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：HD3/HD4 口径变化 → 分别继承 F2/F3。

## Compact history
- 2026-09-10 G2：主候选 M4(波动电价LP/MPC) + 基线 B4 + 备用 F4(继承)；探针 PASS。
- 2026-09-10 G2.5：人类确认 M4 主模型 + HD3完美预见(继承Q2) + 双基线(B4无储能+R4规则套利)。见 q4_decisions.jsonl
