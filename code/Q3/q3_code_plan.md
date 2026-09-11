# Q3 编码计划 (model-code-analyzer) — round3

> 对应 Gate G3。修复 round1 储能末端短视缺陷 + round2 后新增光伏预报风险修正，采纳口径：
> 方案A 日闭合 E(144)=E(0)=6000 + HD4 同区间比较 + S8 阶梯映射 + **按 issue 分桶 80 分位光伏风险修正**。

## 1. 问题与信息集

- 输入（均指向清洗后数据 `data_clean/cleaned_data.pkl`，不修改 `data_raw`）：
  - `附件1.price`（144 维，10min 电价）
  - `附件2_load` / `附件2_pv`（365×144，实际负荷/光伏，用于结算）
  - `附件3.forecast`（1460×24，滚动光伏预报，4 个 issue×365 天）
- 随机种子 `SEED=2026`（`common.py` 顶部已固定 `np.random.seed(SEED)`）。
- 报告期 `2025-02-01 ~ 2025-12-31`（`WARMUP_DAYS=31`，`REPORT_DAYS=334`）。

## 2. round1 缺陷（根因）

`q3_mpc_day` / `q3_static_day` 调用 `daily_lp(..., terminal_eq=False)`，`stage_lp`
根本没有终端约束参数，导致储能每日被 LP 倒空至 1200 下界、丧失跨日价值；
round1 含储能 16,972,663.03 元 > 无储能完美预见 16,407,319.63 元（方法级缺陷）。

## 3. 修复方案（round2）

| 函数 | 修复 |
|------|------|
| `stage_lp` | 新增 `terminal_eq=False, E_term=None` 参数；`terminal_eq=True` 时追加 `E[M]=E_term` 等式（M=剩余区间数） |
| `rule_arbitrage` | 新增 `E_term=None` 参数；`terminal_eq=True` 时在最后 `NB=min(24,M)` 区间按功率/容量上限把储能拉回 `E_term` 并重算 `x` |
| `q3_mpc_day` | 0:00 `daily_lp` 与 6/12/18 三处 `stage_lp` 全部 `terminal_eq=True, E_term=E0_INIT` |
| `rule_mpc_day` | 4 处 `rule_arbitrage` 全部 `terminal_eq=True, E_term=E0_INIT` |
| `q3_static_day` | `daily_lp` 改为 `terminal_eq=True, E_term=E0_INIT` |

日闭合后：M3/B3/R3 每日 `E(0)=E(144)=6000`，跨日结转 `E_end` 恒为 6000。

## 4. 输出目录与文件

- `experiments/round2/`（round1 作废，不覆盖 round1 目录）
  - `results/Q3/experiments/round2/run_summary.json`（`q3_main.py`）
  - `results/Q3/experiments/round2/baseline_metrics.json`（`q3_baseline.py`）
- 结果表 `results/Q3/result3.xlsx`（4 sheet：计划购电量/调整购电量/充放电量/紧急购电量）

## 5. run_summary.json 结构（关键字段）

```json
{
  "schema_version": 1, "question_id": "Q3", "experiment_id": "round2",
  "method": "M3-MPC+piecewise-billing+terminal-daily-cycle",
  "seed": 2026, "status": "success",
  "main": { "objective_value": ..., "plan_cost": ..., "penalty_cost": ..., "emergency_cost": ... },
  "baselines": [
    {"id": "B3", "name": "静态不调整(日闭合)", "objective_value": ...},
    {"id": "R3", "name": "规则套利(日闭合)", "objective_value": ...},
    {"id": "B3_ref", "name": "无储能(完美预见,下界)", "objective_value": ...}
  ],
  "metrics": {
    "调整价值_元": ..., "优化价值_元": ...,
    "储电量_E0_min/max": ..., "储电量_E24_min/max": ...
  }
}
```

## 5.5 round3 新增：光伏预报风险修正（决策 q3_risk_correction_r2）

- 实测：光伏预报误差按星期分桶解释 0% 方差，按 issue(0/6/12/18) 解释 43.5%；
  6:00 预报系统性高估上午光伏（均值 478kW、P80≈1003kW）。
- 口径：`δ[s] = P80(Ĝ−G)`（issue s 高估 80 分位，因果仅用 [min_hist,d) 历史）；
  `Ĝ^safe = clip0(Ĝ − δ[s])`，据此做 MPC 规划，把光伏高估缺口转成弃光。
- `pv_overestimation(forecast,pv)` 预计算 (D,4,36) 高估；`issue_risk_delta(over,d,q,min_hist)` 滚动因果取分位。
- 敏感性：方案A(无修正) vs 方案B(按 issue 80分位修正，推荐)，对比总费用/紧急/弃光。

## 6. 合理性判定准则（供审查与 G4 使用）

1. **主模型优于无储能下界**：`M3.objective_value < B3_ref`（16,407,319.63 元），否则储能无价值。
2. **日闭合成立**：`E0_min = E0_max = E24_min = E24_max = 6000`（容差 1e-6）。
3. **调整价值为正**：`B3 - M3 > 0`（MPC 6/12/18 调整优于静态执行）。
