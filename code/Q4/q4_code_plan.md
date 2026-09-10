# Q4 代码计划 (model-code-analyzer)

## 目标与成功标准
- 目标：将 Q2/Q3 的恒定电价 p_t 替换为附件4 波动电价 p_{d,t}，重解全年联合 LP（result4-2）与滚动 MPC（result4-3）。报告期 334 天。
- 输出：`results/Q4/result4-2.xlsx`（Q2 结构）、`results/Q4/result4-3.xlsx`（Q3 结构）+ `experiments/round1/run_summary.json`。
- 成功标准：两套 LP/MPC 全部 success；数值合理；与 Q2/Q3 的模型结构一致，仅电价输入不同。

## 目录结构（experiments/round1）
```
results/Q4/
├── result4-2.xlsx
├── result4-3.xlsx
└── experiments/round1/
    ├── run_summary.json
    └── baseline_metrics.json
```

## 数据来源（只读 data_clean/cleaned_data.pkl）
- `附件4_price`：(365,144) 波动电价（均值 ≈0.766 与附件1 一致，min≈0.0076，max≈1.7936）。
- `附件2_load` / `附件2_pv`：(365,144)。
- `附件3.forecast`：(1460,24)。
- 不修改 `data_raw/`。

## 主模型 M4
- **result4-2（全年联合 LP）**：`full_year_lp(price_d.reshape(-1), load, pv, E0)`，切报告期，完美预见 z=0。
- **result4-3（滚动 MPC）**：逐日 `q3_mpc_day(price_d[d], load[d], pv[d], fc, d, E)`，跨日结转 E，记录 X/Y/C/Q/Z。

## 基线
- **B4 无储能（波动电价）**：报告期逐日 `no_storage(price_d[d])`。
- **R4 规则套利（波动电价）**：全年逐日 `rule_arbitrage(price_d[d])`，报告期费用求和。

## 计算步骤（q4_main.py）
1. `load_bundle()`。
2. result4-2：`full_year_lp` → Xr/Cr/Qr/Er → 写 result4-2.xlsx。
3. result4-3：逐日 `q3_mpc_day` → X3/Y3/C3/Q3/Z3/E0_arr/E24_arr → 写 result4-3.xlsx。
4. 基线 B4/R4。
5. 写 `run_summary.json`；`q4_baseline.py` 写 `baseline_metrics.json`。

## 可比指标
- result4-2：报告期总购电费（完美预见+波动电价）。
- result4-3：报告期总购电费（MPC+波动电价）。
- 与 Q2/Q3 恒定电价结果对比，量化电价波动对成本的影响。

## 风险监控
- 两套求解器均需 success；否则 RuntimeError。
- result4-2 切片边界（334 天）；result4-3 拼接（144 区间）。
- 电价口径核对：附件4 均值应≈附件1 恒定电价（已核 ≈0.766）。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`。
- 依赖：numpy、scipy(HiGHS)、openpyxl。
- 路径：`code/Q4/q4_main.py`、`code/Q4/q4_baseline.py`、`code/common.py`。
