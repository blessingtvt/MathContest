# Q3 代码计划 (model-code-analyzer)

## 目标与成功标准
- 目标：滚动时域 MPC——0:00 用 0:00 预报制定计划 x；6/12/18 各据最新预报调整 y；分段计费；紧急购电用附件2实际光伏结算（5 倍）。报告期 334 天。
- 输出：`results/Q3/result3.xlsx`（计划购电量/调整购电量/充放电量/紧急购电量 四张 sheet）+ `experiments/round1/run_summary.json`。
- 成功标准：每日 LP/MPC 全部 success；紧急购电 z 与能量缺口一致；计划/违约/溢价/紧急四段费用加总等于目标值。

## 目录结构（experiments/round1）
```
results/Q3/
├── result3.xlsx
└── experiments/round1/
    ├── run_summary.json
    └── baseline_metrics.json
```

## 数据来源（只读 data_clean/cleaned_data.pkl）
- `附件1.price`：(144,) 恒定分时电价。
- `附件2_load` / `附件2_pv`：(365,144) 实际负荷/实际光伏（结算用实际值）。
- `附件3.forecast`：(1460,24) 滚动预报；issue s∈{0,1,2,3} 对应 0/6/12/18 点，覆盖小时 [6s, 6s+24)。
- 不修改 `data_raw/`。

## 主模型 M3：滚动 MPC（common.q3_mpc_day）
- 阶段0（0:00）：`daily_lp`（0:00 预报 ghat0）→ 计划 x、c0/q0、E 轨迹。
- 阶段1/2/3（6/12/18 点）：`stage_lp` 对剩余时段 [sl,144) 用新预报 ghat1/2/3 调整 y。
  - 分段计费线性化：y=u+v，0≤u≤x_plan，v≥0；目标 min Σ p(0.5u+1.5v)（常数项 0.5p·x 略去，不影响最优 y）。
- 拼接执行方案 y/c/q = [x[:36], y1[:36], y2[:36], y3[:36]]。
- 结算：`z = max(L·Δt + c − y − G_actual·Δt − q, 0)`（5 倍）；账单 `p·(min(x,y)+0.5·max(x−y,0)+1.5·max(y−x,0))`。

## 基线
- **B3 静态不调整**：`q3_static_day` 仅 0:00 计划并执行，预报误差全部由紧急购电吸收。
- **R3 规则套利（滚动预报）**：`rule_mpc_day`，与 M3 同信息（滚动预报）、同计费，仅用贪心规则替代 LP，保证可比。

## 计算步骤（q3_main.py）
1. 逐日滚动 M3（跨日结转 E），记录 X/Y/C/Q/Z/E0_arr/E24_arr（报告期 334 天）。
2. 基线 B3/R3 同滚动。
3. 加载模板 `result3.xlsx`：写计划购电量、调整购电量、重建充放电量 sheet、重建紧急购电量 sheet（稀疏，仅 z>0）。
4. 计算计划费用/违约/溢价/紧急四段分解。
5. 写 `run_summary.json`；`q3_baseline.py` 写 `baseline_metrics.json`。

## 可比指标（metrics）
- 调整价值 = B3 − M3；优化价值 = R3 − M3。
- 目标值 = plan_cost + penalty_cost + emergency_cost。

## 风险监控
- MPC 每阶段 LP 不可行 → RuntimeError。
- 调整时段拼接正确性：`sl` 依次 36/72/108，`y_final` 长度恒为 144。
- 分段计费线性化等价性：目标偏好把 y 尽量放入 u（0.5）而非 v（1.5）→ u*=min(y,x_plan)。
- 预报映射：`forecast_intervals` 保证区间 t（小时 t//6）→ forecast[d*4+s, t//6−6s]。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`。
- 依赖：numpy、scipy(HiGHS)、openpyxl。
- 路径：`code/Q3/q3_main.py`、`code/Q3/q3_baseline.py`、`code/common.py`。
