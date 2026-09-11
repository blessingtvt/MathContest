# Q4 代码计划（model-code-analyzer，round2）

## 目标与成功标准
- 目标：波动电价（附件4）下，完全继承 Q2(round4)/Q3(round3) 最终模型重解，最小化总购电费。
- 成功标准：result4-2.xlsx、result4-3.xlsx 完整；两套 LP/MPC 全部 success；与 Q2/Q3 最终模型结构一致，仅电价 p_t→p_{d,t}；基线与诊断下界落盘。

## 已批准决策
- `q4_method_choice_r2`：主模型 M4 = 完全继承 Q2/Q3 最终模型，仅换波动电价。
- `q4_quantile_choice_r2`：风险修正分位 q=80 为主（G3 只实现 q=80，扫描留 G4 稳健性）。
- `q4_baseline_choice_r2`：基线 = 双基线 B4+R4 + 诊断下界 B4_ref。

## 目录结构（experiments/round2）
```
results/Q4/
├── result4-2.xlsx            # 对应 Q2（计划/充放电/紧急）
├── result4-3.xlsx            # 对应 Q3（计划/调整/充放电/紧急）
└── experiments/round2/
    ├── run_summary.json      # 主+基线+指标+fallback状态
    └── baseline_metrics.json # B4/R4/B4_ref
```

## 数据来源（只读 data_clean/cleaned_data.pkl，不修改 data_raw）
- `附件4_price` (365,144) 波动电价（均值 0.7662=附件1，min 0.0076，max 1.7936）。
- `附件2_load` / `附件2_pv` (365,144)；`附件3.forecast` (1460,24)；`dates`。
- 模板：`data_raw/附件5/result4-2.xlsx`、`result4-3.xlsx`（sheet 名与 Q2/Q3 一致）。

## 主模型 M4（仅换电价，数学结构完全继承）
- **result4-2（=Q2 模型）**：逐日 `daily_lp(price_d[d], Nsafe, zeros, E0=6000, terminal_eq=True, E_term=6000)`；
  净负荷自预报 N̂=Σ w_k N_{d−k}（w=[0.3,0.2,0.15,0.12,0.1,0.08,0.05]）+ 按星期分桶 80 分位 e80[dow]（因果，仅用 d 之前同星期）；结算 z=max(N·Δt+c−x−q,0)。
- **result4-3（=Q3 模型）**：逐日 `q3_mpc_day(price_d[d], load[d], pv[d], fc, d, E, delta)`，delta=issue_risk_delta(over, d, 80, 7)（δ=[0,1005.49,−6.27,0]），跨日结转 E；分段计费 + 日闭合。

## 基线（同信息集，波动电价）
- B4 无储能：`no_storage_forecast(price_d[d], Nsafe, N[d])`（自预报+星期80分位）。
- R4 规则套利：`rule_forecast_day(price_d[d], Nsafe, N[d], E_carry)`（自预报+星期80分位，E 跨日结转）。
- B4_ref 无储能完美预见：`no_storage(price_d[d], load[d], pv[d])`（诊断下界）。

## 可比指标
- result4-2：报告期总购电费（Q2 模型 + 波动电价）；储能价值=B4−result4-2；优化价值=R4−result4-2；预报误差成本=B4−B4_ref。
- result4-3：报告期总购电费（Q3 模型 + 波动电价）；紧急购电/弃光/储电量指标。

## 风险监控（探针条件落实）
- 两套求解器均 success，否则 RuntimeError；result4-2 逐日（日闭合）、result4-3 拼接（144 区间）。
- 电价口径核对：附件4 均值应≈0.766（≈附件1）；极端低价 0.0076 的套利行为记录在 metrics（弃光/储电量）。

## 路径 / 种子 / 依赖
- 种子 `common.SEED=2026`（LP 确定性，无随机量）；依赖 numpy、scipy(HiGHS)、openpyxl。
- 路径：`code/Q4/q4_main.py`、`code/Q4/q4_baseline.py`、`code/common.py`。

## 期望的下游审查项（python-code-reviewer）
syntax / input_contract / method_alignment / reproducibility / output_contract。
