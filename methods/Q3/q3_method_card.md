# Q3 Method Card

## Goal and success criteria
- 目标：滚动预报下最小化总购电费(计划+调整违约/溢价+紧急)，建立"0:00计划+6/12/18调整"多阶段模型。
- 成功标准：总费用最小；调整策略利用滚动预报降费；result3.xlsx 完整；回答"是否需引入更多预报时刻"。

## Human constraints（默认，选择卡确认）
- Output form：表1/表2/表3 + result3.xlsx + 分析结论
- Priority：最优性 > 速度
- Unacceptable failure：计费口径错误或调整策略不可行
- Experiment budget：分钟级（≈14s）

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M3 | main | 滚动时域 LP(MPC)：0:00计划+6/12/18调整+分段计费线性化 | 精确、预报自适应、文献主流 | 计费口径HD4待确认；解退化 | 中 |
| B3 | baseline(静态不调整) | 仅0:00计划不调整(Q2式静态) | 完整任务、量化调整价值 | 非最优(预报误差全由紧急购电吸收) | 低 |
| R3 | baseline(规则套利) | 峰谷套利：低价充到满、高价放到空，余下购电补缺口 | 完整任务、量化优化价值 | 规则阈值主观、非最优 | 低 |
| F3 | fallback | MILP 分段线性化(计费拐点) | 若HD4导致非凸/需显式分段 | 整数求解 | 中 |

## Baseline validity
- Real task completed：是
- Comparable：是（带调整 vs 不调整的费用差 = 调整策略价值）
- 多基线：B3 静态不调整(调整价值) + R3 规则套利(优化价值)；无储能口径可复用 Q2

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M3 | PASS(骨架已验证) | HD4计费、S8预报粒度待确认 | CONDITIONAL | PASS(滚动自适应) | PASS(≈14s) | **PASS** |
| B3 | PASS | — | PASS | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：HD4 计费口径导致目标非凸/需显式分段 → 启用 F3 MILP。

## Compact history
- 2026-09-10 G2：主候选 M3(滚动MPC-LP) + 基线 B3(不调整) + 备用 F3(MILP)；探针 PASS。
- 2026-09-10 G2.5：人类确认 M3 主模型 + 新增 R3 规则套利基线。见 q3_decisions.jsonl
