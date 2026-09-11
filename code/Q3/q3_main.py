# -*- coding: utf-8 -*-
"""Q3 主模型 (M3: 滚动时域 MPC + 分段计费线性化 + 日闭合 + 按 issue 分桶 80 分位光伏风险修正)。

0:00 用 0:00 保守预报制定计划 x; 6/12/18 各据最新保守预报调整 y; 每日储能日闭合 E(144)=E(0)=6000。
保守光伏 Ĝ^safe = clip0(Ĝ − δ[issue]), δ[s]=P80(光伏高估), 把高估缺口转成弃光而非 5 倍紧急。
计费 = p·min(x,y)+0.5p·max(x-y,0)+1.5p·max(y-x,0); 紧急购电用附件2实际值结算(5倍)。
敏感性: 方案A(无修正) vs 方案B(按 issue 80 分位修正, 推荐)。
输出: results/Q3/result3.xlsx + experiments/round3/run_summary.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import *

ROUND = "round3"
QUANTILE = 80.0
MIN_HIST = 7


def run_mpc_year(price, load, pv, fc, D, over, use_correction):
    """全年滚动 MPC。use_correction=True 按 issue 80分位修正(方案B), False 无修正(方案A)。

    返回 (total, X, Y, C, Q, Z, E0_arr, E24_arr, emergency_cost, curt_energy)。
    """
    X = np.zeros((REPORT_DAYS, T)); Y = np.zeros((REPORT_DAYS, T))
    C = np.zeros((REPORT_DAYS, T)); Q = np.zeros((REPORT_DAYS, T))
    Z = np.zeros((REPORT_DAYS, T))
    E0_arr = np.zeros(REPORT_DAYS); E24_arr = np.zeros(REPORT_DAYS)
    E = E0_INIT
    total = 0.0
    row = 0
    for d in range(D):
        delta = issue_risk_delta(over, d, QUANTILE, MIN_HIST) if use_correction else None
        E_start = E
        cost, x, yf, cf, qf, E_end, z = q3_mpc_day(price, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            E0_arr[row] = E_start
            E24_arr[row] = E_end
            X[row], Y[row], C[row], Q[row], Z[row] = x, yf, cf, qf, z
            total += cost
            row += 1
    price_r = np.tile(price, (REPORT_DAYS, 1))
    emergency_cost = float(np.sum(ALPHA_EM * price_r * Z))
    supply = Y + pv[WARMUP_DAYS:] * DT + Q
    demand = load[WARMUP_DAYS:] * DT + C
    curt_energy = float(clip0(supply - demand).sum())
    return total, X, Y, C, Q, Z, E0_arr, E24_arr, emergency_cost, curt_energy


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()
    over = pv_overestimation(fc, pv)

    # ---- 方案B (推荐): 按 issue 80 分位保守修正 ----
    total, X, Y, C, Q, Z, E0_arr, E24_arr, emg_cost, curt_energy = \
        run_mpc_year(price, load, pv, fc, D, over, use_correction=True)

    # ---- 方案A (对照): 无修正 ----
    total_A, _, _, _, _, _, _, _, emg_cost_A, curt_energy_A = \
        run_mpc_year(price, load, pv, fc, D, over, use_correction=False)

    # ---- 基线 (均与方案B同修正口径) ----
    b3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        delta = issue_risk_delta(over, d, QUANTILE, MIN_HIST)
        cost, _, _, _, E_end, _ = q3_static_day(price, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            b3_cost += cost
    r3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        delta = issue_risk_delta(over, d, QUANTILE, MIN_HIST)
        cost_d, _, _, _, _, E_end, _ = rule_mpc_day(price, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            r3_cost += cost_d
    ns_cost = 0.0                      # 无储能完美预见(下界)
    for d in range(WARMUP_DAYS, D):
        ns_cost += no_storage(price, load[d], pv[d])[0]
    ns_fc_cost = 0.0                   # 无储能 + 附件3预报(无修正)
    for d in range(WARMUP_DAYS, D):
        ns_fc_cost += no_storage_dayahead(price, load[d], pv[d], fc, d)[0]

    # ---- 写 result3.xlsx (方案B) ----
    out_dir = os.path.join(RESULTS_DIR, "Q3")
    os.makedirs(os.path.join(out_dir, "experiments", ROUND), exist_ok=True)
    out_path = os.path.join(out_dir, "result3.xlsx")
    wb = openpyxl.load_workbook(os.path.join(TEMPLATE_DIR, "result3.xlsx"))
    fill_plan_grid(wb["计划购电量"], X)
    fill_plan_grid(wb["调整购电量"], Y)
    E_flat = np.zeros(REPORT_DAYS * T + 1)
    for d in range(REPORT_DAYS):
        E_flat[d * T] = E0_arr[d]
        E_flat[d * T + T] = E24_arr[d]
    rebuild_charge_sheet(wb["充放电量"], dates, C, Q, E_flat)
    rebuild_emergency_sheet(wb["紧急购电量"], dates, Z, labels)
    wb.save(out_path)

    price_r = np.tile(price, (REPORT_DAYS, 1))
    plan_cost = float(np.sum(price_r * np.minimum(X, Y)))
    penalty_cost = float(np.sum(price_r * (BETA_PEN * np.maximum(X - Y, 0.0) + GAMMA_PRE * np.maximum(Y - X, 0.0))))
    emg_energy = float(Z.sum())
    pv_report = float(pv[WARMUP_DAYS:].sum() * DT)

    summary = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": ROUND,
        "method": "M3-MPC+piecewise-billing+terminal-daily-cycle+issue-80pct-pv-risk-correction",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "data_sources": ["data_clean/cleaned_data.pkl"],
        "report_period": "2025-02-01 ~ 2025-12-31",
        "risk_correction": {
            "axis": "issue(0/6/12/18)",
            "quantile": QUANTILE,
            "min_hist_days": MIN_HIST,
            "formula": "Ghat_safe = clip0(Ghat - delta[issue]), delta[s]=P80(Ghat-G)",
            "delta_issue_kW": [round(float(issue_risk_delta(over, D - 1, QUANTILE, MIN_HIST)[s]), 2) for s in range(4)],
        },
        "main": {
            "method_id": "M3",
            "objective_name": "报告期总购电费(元, 含违约/溢价/紧急)",
            "objective_value": round(total, 2),
            "plan_cost": round(plan_cost, 2),
            "penalty_cost": round(penalty_cost, 2),
            "emergency_cost": round(emg_cost, 2),
            "outputs": ["results/Q3/result3.xlsx"],
        },
        "baselines": [
            {"id": "B3", "name": "静态不调整(日闭合+修正)", "objective_value": round(b3_cost, 2)},
            {"id": "R3", "name": "规则套利(日闭合+修正)", "objective_value": round(r3_cost, 2)},
            {"id": "B3_ref", "name": "无储能(完美预见,下界)", "objective_value": round(ns_cost, 2)},
        ],
        "metrics": {
            "调整价值_元": round(b3_cost - total, 2),
            "优化价值_元": round(r3_cost - total, 2),
            "储能价值_元_vs无储能预报": round(ns_fc_cost - total, 2),
            "紧急购电_电量kWh": round(emg_energy, 2),
            "弃光_电量kWh": round(curt_energy, 2),
            "弃光率": round(curt_energy / pv_report, 6),
            "储电量_E0_min": round(float(E0_arr.min()), 2),
            "储电量_E0_max": round(float(E0_arr.max()), 2),
            "储电量_E24_min": round(float(E24_arr.min()), 2),
            "储电量_E24_max": round(float(E24_arr.max()), 2),
        },
        "sensitivity": {
            "scheme_A_no_correction": {
                "total_cost": round(total_A, 2),
                "emergency_cost": round(emg_cost_A, 2),
                "curtailment_kWh": round(curt_energy_A, 2),
            },
            "scheme_B_issue_80pct": {
                "total_cost": round(total, 2),
                "emergency_cost": round(emg_cost, 2),
                "curtailment_kWh": round(curt_energy, 2),
            },
        },
    }
    with open(os.path.join(out_dir, "experiments", ROUND, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
