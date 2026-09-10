# Q1 Method Card

## Goal and success criteria
- 目标：代表日最小化全天购电费 C1=Σ p_t·x_t，满足供电≥负载、储能边界、终态 E_0=E_T。
- 成功标准：解满足全部约束；费用最小；result1.xlsx 完整（144区间购电量、6段充放电+0:00/24:00储电量）。

## Human constraints（默认，选择卡确认）
- Output form：表1/表2 + result1.xlsx
- Priority：最优性(费用最小) > 计算速度（均秒级）
- Unacceptable failure：违反储能容量/功率边界或终态不闭合
- Experiment budget：秒级

## Shortlist
| ID | Role | 数学思想 | 为何合格 | 主要风险 | 实现成本 |
|---|---|---|---|---|---|
| M1 | main | 线性规划 LP（连续 x/c/q/E，577变量） | 精确最优、约束全覆盖、快(0.014s) | 解退化(多重最优) | 低(scipy linprog) |
| B1 | baseline(无储能) | 无储能：x_t=max(L·Δt−G·Δt,0) | 完成真实任务、费用可比较(48052元) | 非最优(上界) | 极低 |
| R1 | baseline(规则套利) | 峰谷套利：低价充到满、高价放到空，余下购电补缺口 | 完整任务、与主模型同类可比(均含储能) | 规则阈值主观、非最优 | 低 |
| F1 | fallback | 充放电互斥 MILP（加二进制） | 若质疑S4(同区间充放)则显式互斥 | 需整数求解 | 低 |

## Baseline validity
- Real task completed：是（完整购电计划）
- Comparable：是（同为全天购电费；储能较无储能省27%）
- 双基线：B1 无储能(诊断下限) + R1 规则套利(正式 baseline)，分别量化储能价值与优化价值

## Risk-probe summary
| ID | 可执行 | 数据/假设 | 退化 | 扰动 | 规模 | 结论 |
|---|---|---|---|---|---|---|
| M1 | PASS | 终态/储能可行；HD2待确认 | CONDITIONAL(多重最优) | PASS(线性) | PASS(0.014s) | **PASS** |
| B1 | PASS | — | PASS(唯一) | PASS | PASS | **PASS** |

## Fallback trigger
- Trigger：若人类质疑 S4（同区间边充边放）→ 启用 F1 MILP 显式互斥；或 LP 报 infeasible/终态残差>1e-6。

## Compact history
- 2026-09-10 G2：主候选 M1(LP) + 基线 B1(无储能) + 备用 F1(MILP)；探针 PASS。
- 2026-09-10 G2.5：人类确认 M1 主模型 + 双基线(B1无储能+R1规则套利)；无需 MILP(LP 最优解天然充放互斥)。见 q1_decisions.jsonl
