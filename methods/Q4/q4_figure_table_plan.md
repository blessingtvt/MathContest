# Q4 图表计划（figure-table-planner）

> 原则：每个视觉都必须支撑一条已验证的论断；诊断图（Type 1）禁入论文。

## 图（Type 分类）

| ID | 类型 | 来源 | 核心论断 | 形式 | 目标章节 | 状态 |
|---|---|---|---|---|---|---|
| fig_q4_1_cost_comparison | **Type 3 论文** | run_summary.json（5 组方案） | 主模型 M4 显著低于双基线；诊断下界 B < A < M4 < B4_ref < B4 单调有序 | 5 组竖向柱状（万元） | 结果·方案对比 | 已生成、渲染通过 |
| fig_q4_2_cost_decomposition | **Type 3 论文** | run_summary.json metrics | 预报误差是相对理论最优的**唯一主要**附加成本（240.1万），日闭合约束成本可忽略（5.0万） | 瀑布图（万元） | 结果·成本拆解 | 已生成、渲染通过 |
| fig_q4_3_quantile_sensitivity | **Type 3 论文** | R1（result4-2）+ E4-4 块级 e44_quantile_sweep.json（result4-3） | q=80 设计值近最优（result4-2 偏离 argmin q=90 共 0.69%、result4-3 偏离 argmin q=85 共 0.18%） | 双曲线 q-成本（万元） | 稳健性·分位敏感性 | 已生成、渲染通过 |
| fig_q4_4_adjustment_value | **Type 3 论文** | E4-5 e45_adjust_value.json | 6:00 首调边际价值最大（−286.0 万），12:00 次之（−46.9 万），18:00 近零（−1.5 元）；滚动调整合计 −332.9 万 | 4 时刻总成本折线 + 边际价值标注（万元） | 结果·MPC 调整价值 | 已生成、渲染通过 |
| fig_q4_5_price_trend | **Type 3 论文** | 附件4 price（365×144） | 附件4 波动电价 = 日内形状不变 + 日间水平波动（星期效应）；0.0076 元极端低价稀疏 | 双面板：日平均电价时间序列 + 日内曲线对比 | 问题·电价数据刻画 | 已生成、渲染通过 |
| fig_q4_6_volatility_sensitivity | **Type 3 论文** | E4-6 e46_volatility_sweep.json | 日间波动幅度 k 越大成本越高（k=0→恒定 Q2/Q3，k=1→波动 Q4，单调上升） | 双曲线 k-成本（万元） | 稳健性·波动幅度 | 已生成、渲染通过 |
| fig_q4_7_price_forecast_uncertainty | **Type 3 论文** | E4-3 e43_price_uncertainty.json | 电价预测误差成本有限（result4-2 +0.90%、result4-3 +0.80%），C1"电价已知"假设稳健 | 分组柱状（已知 vs 自预报，万元） | 稳健性·电价不确定性 | 已生成、渲染通过 |

- 无 Type 1 诊断图、无 Type 4 附录图（当前无需要补充的附录证据）。
- 恒定 vs 波动对比用**表格**表达（精确值优于图），见下表。

## 表（论文用精确值）

| ID | 内容 | 来源 | 目标章节 |
|---|---|---|---|
| tab_q4_cost_5group | 5 组方案总购电费（B/A/M4/B4_ref/B4） | frozen_numbers.json | 结果·方案对比 |
| tab_q4_decomposition | 成本分解（B + 日闭合 + 预报误差 = M4） | frozen_numbers.json | 结果·成本拆解 |
| tab_q4_const_vs_fluct | 恒定 vs 波动电价 6 项指标对比 | frozen_numbers.json（q4_result4_2_constant 等） | 结果·电价波动影响 |
| tab_q4_q_sweep | q 扫描各分位总成本 | result4-2: R1；result4-3: E4-4 块级 e44_quantile_sweep.json | 稳健性·分位敏感性 |

## 核心论断 → 视觉映射（验证）

1. "主模型优于基线" → fig_q4_1（柱状差）+ tab_q4_cost_5group（精确值）。
2. "预报误差经济价值 240 万" → fig_q4_2（瀑布红色段）+ tab_q4_decomposition。
3. "q=80 稳健" → fig_q4_3（曲线 + q=80 竖线）。
4. "波动电价放大套利与预报误差损失" → tab_q4_const_vs_fluct。

## 状态

全部 Type 3 论断均追溯至 `q4_package_signoff`（keep）与冻结文件；图已渲染校验（中文标签、无裁剪、无重叠、300dpi）。
