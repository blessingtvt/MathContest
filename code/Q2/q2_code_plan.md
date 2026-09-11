# Q2 代码计划 (model-code-analyzer) — round3 逐日滚动 + 自预报 + 80分位风险修正

## 目标与成功标准
- 目标：报告期（2025-02-01 ~ 12-31，334 天）最小化总购电费 C2 = Σ p_t·(x_t + 5·z_t)。
- 主模型 M2：**逐日滚动 LP + 净负荷自预报 + 80分位风险修正**。每天 0:00 用附件2历史自预报当天净负荷 N̂_d（7天加权平均）并加历史误差 80 分位修正 N^safe=N̂+e^80，附件2 实际光伏结算，缺口由紧急购电 z（5 倍价）吸收。
- 成功标准：LP 全部 success；能量平衡满足、储能连续且落界（日末循环 S_144=S_0=6000）；自预报下紧急购电 z>0 真实触发。

## 批准决策
- `q2_method_choice_r3`（M2=逐日滚动 LP + 自预报 + 80分位风险修正）/ `q2_information_set_r3`（附件2历史自预报，非附件3）/ `q2_baseline_choice_r3`（B2+R2 同信息集）。

## 目录结构（experiments/round3）
```
results/Q2/
├── result2.xlsx
└── experiments/round3/
    ├── run_summary.json
    └── baseline_metrics.json
```

## 数据来源（只读 data_clean/cleaned_data.pkl，不改 data_raw/）
- `附件2_load`：(365,144) 实际负载。
- `附件2_pv`：(365,144) 实际光伏（结算用）。
- `附件1.price`：(144,) 恒定分时电价（每天复制）。
- **不用附件3**：附件3(光伏预报)属 Q3/Q4；Q2 净负荷自预报全部由附件2历史产生（时间因果）。
- 报告期切片：索引 31..364（1 月为预热，HD5）。

## 主模型 M2：逐日滚动 LP + 自预报 + 风险修正（时间因果，不跨日看未来）
1. 净负荷 `N = load − pv`；`Nhat, Eerr = netload_forecast(N)`：7 天加权平均 w=[0.3,0.2,0.15,0.12,0.1,0.08,0.05]。
2. `for d in 31..364:` 历史误差 80 分位 `e80 = percentile(Eerr[7:d], 80)`（仅用 d 之前数据，因果）。
3. `Nsafe = Nhat[d] + e80`；`daily_lp(price, Nsafe, zeros(T), E0=6000, terminal_eq=True, E_term=6000)`（净负荷口径，日末循环）。
4. 紧急购电 `z_d = max(N_real·Δt + c_d − x_d − q_d, 0)`。
5. 报告期费用 = Σ price·Xr + 5·Σ price·Zr。

> 与全年联合不同：每天只解当天 LP（单日变量 577 个），无跨日耦合，符合"每天 0:00 制定当天计划"的题设；全年联合已降为事后下界诊断参考。日末循环 S_144=S_0=6000（用户指定，避免跨日自由终态）。

## 基线（同信息集：自预报 + 80分位风险修正 + 紧急购电）
- **B2 无储能**：报告期逐日 `no_storage_forecast(price, Nsafe, N_real)` 求和。
- **R2 规则套利**：逐日 `rule_forecast_day`（`rule_arbitrage` + Nsafe 净负荷 + 紧急），储能跨日结转。
- **B2_ref 无储能·完美预见**：`no_storage(price, load[d], pv[d])`（诊断参考，量化预报误差成本）。

## 计算步骤（q2_main.py）
1. `load_bundle()`。
2. 逐日滚动 LP 求全年 (X,C,Q,Z,E)，报告期 Xr/Cr/Qr/Zr/Er。
3. 报告期费用 = Σ price_tile·Xr + 5·Σ price_tile·Zr。
4. 基线 B2 / R2 / B2_ref。
5. 加载模板 `result2.xlsx`：写计划购电量、重建充放电量 sheet（含 0:00/24:00 储电量）、重建紧急购电量 sheet。
6. 写 `run_summary.json`；`q2_baseline.py` 写 `baseline_metrics.json`。

## 可比指标（metrics）
- 储能价值 = B2 − M2；储能价值占比 = (B2−M2)/B2。
- 优化价值 = R2 − M2。
- 预报误差成本(无储能) = B2 − B2_ref。
- 紧急购电区间数/电量/占比；弃光区间数/电量/弃光率；储电量 min/max。

## 风险监控
- LP 不可行 → RuntimeError（每日常见原因：E0 越界或约束矛盾）。
- 日末循环：`daily_lp(terminal_eq=True, E_term=6000)` 保证 S_144=S_0。
- 因果性：e80 只取 `Eerr[7:d]`（d 之前），Nhat[d] 只取前 7 天，无未来信息泄露。
- 报告期切片边界：Er 长度 = 334·T+1=48097，覆盖 2-01 00:00 至 12-31 24:00。
- 广播：price_tile 与 Xr 同形（334×144）。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`；scipy linprog (HiGHS)；numpy；openpyxl。
- 路径：`code/Q2/q2_main.py`、`code/Q2/q2_baseline.py`、`code/common.py`。

## 下游审查检查（python-code-reviewer）
- `syntax` / `input_contract` / `method_alignment` / `reproducibility` / `output_contract`。
