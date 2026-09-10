# 相关文献分析（related-paper-analyzer 输出）

> 说明：本次由用户明确要求「检索该题型真实相关文献」。以下文献均来自联网检索（Web Search）返回的**真实、可核验**结果，仅收录标题与链接，**未编造作者、年份、期刊或 DOI**。论文正式引用前，请按链接核对完整元数据（作者/卷期/DOI）。

## 1. 已检索文献清单（真实可核验）

### A. 微网 EMS 的 LP/MILP 最优调度（对应 Q1、Q2、Q4 的确定性优化核心）
1. A Mixed Integer Linear Programming Approach for Cost-Effective Microgrid Operation with Renewable Energy and Outage Management — IEEE — https://xplorestaging.ieee.org/document/11255989
2. Cost-Effective Operation of Microgrids: A MILP-Based Energy Management System for Active and Reactive Power Control — https://idus.us.es/items/b38da323-58e7-4ca5-ba89-c5fcfdba196e/full
3. Optimal power dispatch in microgrids using mixed-integer linear programming — https://ouci.dntb.gov.ua/en/works/4kzeRqE7/
4. Robust Linear Programming Optimization of Grid-Connected PV Microgrids — Semantic Scholar — https://www.semanticscholar.org/paper/Robust-Linear-Programming-Optimization-of-PV-Enyam-Aidoo/eb4f85136af94144f543fbec39d977d640c85c9b
5. Energy Management in Microgrid using Linear programming Optimization — IEEE — https://ieeexplore.ieee.org/document/10726110
6. Optimal Operation of Battery Energy Storage Systems in Microgrid-Connected Distribution Networks for Economic Efficiency and Grid Security — MDPI Energies — https://www.mdpi.com/1996-1073/18/23/6335/xml

### B. 滚动/模型预测控制(MPC)与预报驱动的储能调度（对应 Q3、Q4 的滚动预报+调整）
7. Integrated forecasting and MPC framework for cost-optimised solar-battery energy management — Solar Energy (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S0038092X26004081
8. Bi-Layer Model Predictive Control strategy for techno-economic operation of grid-connected microgrids — Renewable Energy (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S096014812401509X
9. Arbitrage with Power Factor Correction using Energy Storage — arXiv — https://ar5iv.labs.arxiv.org/html/1903.06132
10. A model predictive control framework with customer-priority tiers for virtual power plant resilience during extreme weather — arXiv — https://ar5iv.labs.arxiv.org/html/2511.22528
11. Optimization and Control of Storage in Smart Grids — HAL (博士论文) — https://anr.halpreprod.archives-ouvertes.fr/INSMI/tel-02498912v1

### C. 日前/多时间尺度调度与不确定性（对应 Q2、Q3 的日前计划+实时调整+紧急购电）
12. Optimal day-ahead dispatch of microgrids in Cameroon: A framework for managing source and load uncertainties with demand-side flexibility — ScienceDirect — https://www.sciencedirect.com/science/article/pii/S2468227626004424
13. Double-layer optimal scheduling for wind-PV-hydro-hybrid energy storage system with multi-timescale coordination — Energy (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S0360544225041180
14. Coordinated dispatch optimization of multi-type energy storage systems using MILP and NSGA-II algorithms — Thermal Power Generation — https://castjournals.cast.org.cn/joweb/rlfd/EN/10.19666/j.rlfd.202508008
15. Optimizing energy flow in advanced microgrids: a prediction-independent two-stage hybrid system approach — Energy Informatics (Springer) — https://link.springer.com/article/10.1186/s42162-025-00523-7

## 2. 子问题 → 文献映射

| 子问题 | 题型 | 可借鉴文献 | 方法线索 |
|---|---|---|---|
| Q1 | 单日确定性优化 | #1 #2 #3 #5 #6 | 目标为最小购电费；储能 SoC 动态 + 充放电功率/容量约束 + 能量平衡，构成 LP/MILP |
| Q2 | 日前滚动优化(含紧急购电) | #12 #13 #14 #6 | 日前计划 + 实时偏差补偿；分层/多时间尺度调度对应"计划+紧急"结构 |
| Q3 | 滚动预报下的计划+调整 | #7 #8 #9 #15 #10 | MPC/滚动时域 + 两阶段(计划+调整) + 违约/溢价惩罚 |
| Q4 | 波动电价下的 Q2/Q3 | #4 #6 #7 #8 | 波动/实时电价只改费用函数，储能套利与滚动 MPC 直接复用 |

## 3. 可迁移的方法线索（供 method-selector）

- **Q1 结构**：线性规划(LP)。决策=区间购电量 x_t、充/放电 c_t/q_t、储电量 E_t；目标=Σ p_t·x_t；约束=能量平衡 + 储能 SoC 动态 E_t = E_{t-1} + η_c·c_t − q_t/η_d + 容量[E_min,E_max] + 功率上限 + 终态 E_0=E_T。（文献 #5、#6 的 SoC 动态式与本题附录1 一致）
- **Q2 结构**：日前确定性优化 + 逐日滚动；紧急购电 z 作为"实时偏差补偿"变量，费用按 α_em=5 倍计入。（对应文献 #12 的日前+实时两阶段、#13 的多时间尺度）
- **Q3 结构**：两阶段/滚动时域(MPC)。0:00 计划 + 6/12/18 调整，违约(50%)/溢价(1.5 倍)按区间差量计费——本质是带调整惩罚的滚动优化（文献 #8、#15）。
- **Q4 结构**：将 p_t 替换为波动 p_{d,t}，其余结构不变；储能"低买高卖"套利 + 极端电价下的稳健性需单独检验（文献 #4 robust LP、#7 MPC）。
- **通用技巧**：充放电互斥可用二进制(μ^c+μ^d=1)或省略(成本最小化下同区间充放恒非优)；效率 η_c/η_d 按文献统一写入 SoC 动态；固定随机种子与可复现性。

## 4. 风险与不可直接照搬之处

- 文献多含**电池退化成本、网损、无功/电压约束、碳排放**，本题未要求，**勿引入**以免偏离题设。
- 多数文献为**家庭/工业园微网或配电网多节点**，本题为**单一微网聚合模型**，无需网络潮流/OPF。
- MPC/鲁棒/随机规划需**显式不确定性建模**，本题 Q3 预报由附件3 给定(非自行预测)，滚动机制属确定性 MPC 即可，勿引入 LSTM/RL 等重模型（竞赛时间约束下不划算）。
- 极端电价 0.0076 元/kWh 属数据异常点，套利策略需做扰动敏感性检验，勿直接信任单点最优。

## 5. 缺失证据 / 待解决

- 未逐篇核对作者、年份、DOI、卷期（检索仅返回标题+链接），正式引用前需到源站补全。
- Q3 的"是否需引入其他预报时刻"无直接对应文献，需自行设计对比实验(0/6/12/18 vs 更细预报频次)。
- 无针对"违约 50% / 溢价 1.5 倍"这一具体计费口径的现成文献，该口径依题设为唯一权威。

## 6. 建议的下一步

`method-selector`（G2 方法筛选）。传入本报告的方法线索与风险，结合数据画像与假设清单，为 Q1–Q4 各定 main_candidate + usable_baseline。
