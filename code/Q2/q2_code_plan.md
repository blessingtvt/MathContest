# Q2 代码计划 (model-code-analyzer)

## 目标与成功标准
- 目标：全年（365 天）联合最小化购电费 C2 = Σ p_t·(x_t + 5·z_t)，储能跨日连续；报告期 2025-02-01 ~ 12-31（334 天）。
- 输出：`results/Q2/result2.xlsx`（计划购电量/充放电量/紧急购电量 三张 sheet）+ `experiments/round1/run_summary.json`。
- 成功标准：LP success；全年能量平衡满足、储能连续且落界、c·q=0；完美预见下紧急购电 z=0。

## 目录结构（experiments/round1）
```
results/Q2/
├── result2.xlsx
└── experiments/round1/
    ├── run_summary.json
    └── baseline_metrics.json
```

## 数据来源（只读 data_clean/cleaned_data.pkl）
- `附件2_load`：(365,144) 全年负荷（kW）。
- `附件2_pv`：(365,144) 全年光伏（kW）。
- `附件1.price`：(144,) 恒定分时电价（按天复制 D 次 → price_flat）。
- 报告期切片：索引 31..364（1 月为预热，HD5）。
- 不修改 `data_raw/`。

## 主模型 M2：全年联合稀疏 LP
调用 `common.full_year_lp(price_flat, load.reshape(-1), pv.reshape(-1), E0=E0_INIT)`。
- 变量 4N+1 = 210241（N=52560）。
- 约束（scipy.sparse，HiGHS）：能量平衡、充/放电功率、储能动态、`E∈[1200,10800]`、`E_0=6000`。
- 与逐日滚动不同，全年联合消除「日末短视」，允许跨日充放电（储能状态连续）。
- 完美预见：`z=0`（紧急购电量 sheet 全 0，占位「无」）。

## 基线
- **B2 无储能**：报告期逐日 `no_storage` 求和。
- **R2 规则套利**：全年逐日 `rule_arbitrage`（储能跨日结转 E），报告期费用求和。

## 计算步骤（q2_main.py）
1. `load_bundle()`。
2. `full_year_lp` 求解全年，得 (full_cost, X, C, Q, E)；切报告期 Xr/Cr/Qr/Er。
3. 报告期费用 = Σ price_tile · Xr（完美预见，紧急为 0）。
4. 基线 B2/R2。
5. 加载模板 `result2.xlsx`，写计划购电量（335×144）、重建充放电量 sheet（334 天×6 段 + 0:00/24:00 储电量）、重建紧急购电量 sheet（空）。
6. 写 `run_summary.json`；`q2_baseline.py` 写 `baseline_metrics.json`。

## 可比指标（metrics）
- 储能价值 = B2 − M2；储能价值占比 = (B2−M2)/B2。
- 优化价值 = R2 − M2。
- 附加：全年费用 full_year_cost。

## 风险监控
- LP 不可行 → RuntimeError。
- 储能连续性：核对相邻区间 E 跳变 ≤ PmaxE/ηd（≈925.93）。
- 报告期切片边界：Er 长度 = 334×T+1，覆盖 2-01 00:00 至 12-31 24:00。
- 广播：price_tile 与 Xr 同形（334×144）。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`。
- 依赖：numpy、scipy(sparse, HiGHS)、openpyxl。
- 路径：`code/Q2/q2_main.py`、`code/Q2/q2_baseline.py`、`code/common.py`。
