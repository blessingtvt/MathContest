# Q2 代码计划 (model-code-analyzer) — round2 逐日滚动

## 目标与成功标准
- 目标：报告期（2025-02-01 ~ 12-31，334 天）最小化总购电费 C2 = Σ p_t·(x_t + 5·z_t)。
- 主模型 M2：**逐日滚动 LP**（单尺度 MPC）。每天 0:00 用附件3 0:00 日前光伏预报制定当日计划 (x,c,q)，附件2 实际光伏结算，缺口由紧急购电 z（5 倍价）吸收。
- 成功标准：LP 全部 success；能量平衡满足、储能连续且落界；日前预报下紧急购电 z>0 真实触发。

## 批准决策
- `q2_method_choice_r2`（M2=逐日滚动 LP）/ `q2_information_set_r2`（日前预报，非完美预见）/ `q2_baseline_choice_r2`（B2+R2 同信息集）。

## 目录结构（experiments/round2）
```
results/Q2/
├── result2.xlsx
└── experiments/round2/
    ├── run_summary.json
    └── baseline_metrics.json
```

## 数据来源（只读 data_clean/cleaned_data.pkl，不改 data_raw/）
- `附件2_load`：(365,144) 实际负载（确定性已知）。
- `附件2_pv`：(365,144) 实际光伏（结算用）。
- `附件1.price`：(144,) 恒定分时电价（每天复制）。
- `附件3.forecast`：(1460,24) 滚动预报；0:00 日前预报 = `forecast_intervals(fc, d, 0)` → (144,)。
- 报告期切片：索引 31..364（1 月为预热，HD5）。

## 主模型 M2：逐日滚动 LP（时间因果律，不跨日看未来）
1. 预计算 `ghat0[d] = forecast_intervals(fc, d, 0)`（每天 0:00 日前预报）。
2. `for d in 0..364:` `daily_lp(price, load[d], ghat0[d], E0=E_carry, terminal_eq=False)` → (x_d, c_d, q_d, E_d)。
3. 紧急购电 `z_d = max(L_d·Δt + c_d − x_d − G_d^实际·Δt − q_d, 0)`。
4. 储能跨日结转 `E_carry = E_d[T]`（E 序列拼接为长度 D·T+1）。
5. 报告期费用 = Σ price·Xr + 5·Σ price·Zr。

> 与全年联合不同：每天只解当天 LP（变量 577 个），无跨日耦合，符合"每天 0:00 制定当天计划"的题设；全年联合已降为事后下界诊断参考。

## 基线（同信息集：日前预报 + 紧急购电）
- **B2 无储能**：报告期逐日 `no_storage_dayahead(price, load[d], pv[d], fc, d)` 求和。
- **R2 规则套利**：逐日 `rule_dayahead_day`（`rule_arbitrage` + ghat0 预报 + 紧急），储能跨日结转。
- **B2_ref 无储能·完美预见**：`no_storage(price, load[d], pv[d])`（诊断参考，量化预报误差成本）。

## 计算步骤（q2_main.py）
1. `load_bundle()`。
2. 逐日滚动 LP 求全年 (X,C,Q,Z,E)，切报告期 Xr/Cr/Qr/Zr/Er。
3. 报告期费用 = Σ price_tile·Xr + 5·Σ price_tile·Zr。
4. 基线 B2 / R2 / B2_ref。
5. 加载模板 `result2.xlsx`：写计划购电量、重建充放电量 sheet（含 0:00/24:00 储电量）、重建紧急购电量 sheet。
6. 写 `run_summary.json`；`q2_baseline.py` 写 `baseline_metrics.json`。

## 可比指标（metrics）
- 储能价值 = B2 − M2；储能价值占比 = (B2−M2)/B2。
- 优化价值 = R2 − M2。
- 预报误差成本(无储能) = B2 − B2_ref。
- 紧急购电区间数/电量/占比；弃光区间数/电量/弃光率；储电量 min/max/终态。

## 风险监控
- LP 不可行 → RuntimeError（每日常见原因：E0 越界或约束矛盾）。
- 储能连续性：`E_d[T] = E_{d+1}[0]`（跨日结转无跳变）。
- 报告期切片边界：Er 长度 = 334·T+1，覆盖 2-01 00:00 至 12-31 24:00。
- 广播：price_tile 与 Xr 同形（334×144）。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`；scipy linprog (HiGHS)；numpy；openpyxl。
- 路径：`code/Q2/q2_main.py`、`code/Q2/q2_baseline.py`、`code/common.py`。

## 下游审查检查（python-code-reviewer）
- `syntax` / `input_contract` / `method_alignment` / `reproducibility` / `output_contract`。
