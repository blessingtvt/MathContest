# -*- coding: utf-8 -*-
"""Q3 G4 结果写盘（主模型 = 区间修正顺序法，块级 q=80，round4）。

以 frozen_numbers.json 权威数值为准，重生成 result3.xlsx（计划/调整购电量、
充放电量、紧急购电量三张 sheet）+ experiments/round4/run_summary.json。

主模型 = M3 滚动 MPC + 分段计费线性化 + 日闭合 E(144)=E(0)=6000
         + 光伏风险修正按「issue(0/6/12/18) × 执行块(6h 逐 10min 区间)」取 80 分位。
块级修正实现复用 code/Q3/q3_new_methods/q3_optimized.py（block_delta / corrected_forecast / mpc_day）。
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))           # code/Q3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # code
import numpy as np
import openpyxl
from common import *
import q3_new_methods.q3_optimized as qopt

ROUND = "round4"
QUANTILE = 80.0
FROZEN = os.path.join(RESULTS_DIR, "Q3", "reports", "frozen_numbers.json")


def run_mpc_year_block(price, load, pv, fc, D, over):
    """全年滚动 MPC（块级 q=80 修正），返回 (total, X, Y, C, Q, Z, E0_arr, E24_arr,
    plan_cost, penalty_cost, emergency_cost, emergency_kwh, curtail_kwh)。"""
    X = np.zeros((REPORT_DAYS, T)); Y = np.zeros((REPORT_DAYS, T))
    C = np.zeros((REPORT_DAYS, T)); Q = np.zeros((REPORT_DAYS, T))
    Z = np.zeros((REPORT_DAYS, T))
    E0_arr = np.zeros(REPORT_DAYS); E24_arr = np.zeros(REPORT_DAYS)
    E = E0_INIT
    total = plan = penalty = emergency = emg_kwh = curt = 0.0
    row = 0
    for d in range(D):
        delta = qopt.block_delta(over, d, QUANTILE)
        cost, x, y, c, qv, E_end, z, E_day = qopt.mpc_day(price, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            X[row], Y[row], C[row], Q[row], Z[row] = x, y, c, qv, z
            E0_arr[row] = float(E_day[0])
            E24_arr[row] = float(E_day[-1])
            total += cost
            plan += float((price * np.minimum(x, y)).sum())
            penalty += float((price * (BETA_PEN * np.maximum(x - y, 0.0)
                                       + GAMMA_PRE * np.maximum(y - x, 0.0))).sum())
            emergency += float((ALPHA_EM * price * z).sum())
            emg_kwh += float(z.sum())
            curt += float(clip0(y + pv[d] * DT + qv - load[d] * DT - c).sum())
            row += 1
    return (total, X, Y, C, Q, Z, E0_arr, E24_arr,
            plan, penalty, emergency, emg_kwh, curt)


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()
    over = qopt.block_over(fc, pv)

    (total, X, Y, C, Q, Z, E0_arr, E24_arr,
     plan, penalty, emergency, emg_kwh, curt) = run_mpc_year_block(price, load, pv, fc, D, over)

    # ---- 与冻结值交叉校验 ----
    with open(FROZEN, "r", encoding="utf-8") as f:
        fz = json.load(f)
    fz_total = fz["objective"]["value"]
    fz_plan = fz["cost_breakdown"]["plan_cost_yuan"]
    fz_pen = fz["cost_breakdown"]["penalty_cost_yuan"]
    fz_emg = fz["cost_breakdown"]["emergency_cost_yuan"]
    checks = [
        ("total", total, fz_total),
        ("plan", plan, fz_plan),
        ("penalty", penalty, fz_pen),
        ("emergency", emergency, fz_emg),
        ("emg_kwh", emg_kwh, fz["metrics"]["紧急购电_电量kWh"]),
        ("curtail", curt, fz["metrics"]["弃光_电量kWh"]),
    ]
    print("=== 与 frozen_numbers.json (round4) 交叉校验 ===")
    ok = True
    for name, got, want in checks:
        d = abs(got - want)
        status = "OK" if d < 0.01 else "MISMATCH"
        if d >= 0.01:
            ok = False
        print(f"  {name:10s} got={got:,.2f}  want={want:,.2f}  Δ={d:+.4f}  [{status}]")

    # ---- 写 result3.xlsx（主模型，块级 q=80）----
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
    print(f"WROTE {out_path}")

    # ---- run_summary.json ----
    summary = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": ROUND,
        "method": "M3-MPC+piecewise-billing+terminal-daily-cycle+issue-by-block-80pct-pv-risk-correction",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "risk_correction": {
            "axis": "issue(0/6/12/18) × execution-block(6h, 逐10min区间)",
            "quantile": QUANTILE,
            "min_hist_days": qopt.MIN_HIST,
            "formula": "Ghat_safe[s,t] = clip0(Ghat[s,t] - delta[s,t]), delta[s,:]=P80(overestimate) 逐区间因果分位",
        },
        "main": {
            "method_id": "M3-block",
            "objective_name": "报告期总购电费(元, 含违约/溢价/紧急)",
            "objective_value": round(total, 2),
            "plan_cost": round(plan, 2),
            "penalty_cost": round(penalty, 2),
            "emergency_cost": round(emergency, 2),
            "outputs": ["results/Q3/result3.xlsx"],
        },
        "metrics": {
            "紧急购电_电量kWh": round(emg_kwh, 2),
            "弃光_电量kWh": round(curt, 2),
            "弃光率": round(curt / float(pv[WARMUP_DAYS:].sum() * DT), 6),
            "储电量_E0_min": round(float(E0_arr.min()), 2),
            "储电量_E0_max": round(float(E0_arr.max()), 2),
            "储电量_E24_min": round(float(E24_arr.min()), 2),
            "储电量_E24_max": round(float(E24_arr.max()), 2),
        },
        "cross_check_vs_frozen": {name: (got, want) for name, got, want in
                                  [(n, g, w) for n, g, w in checks]},
        "cross_check_ok": ok,
    }
    with open(os.path.join(out_dir, "experiments", ROUND, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("WROTE experiments/round4/run_summary.json  cross_check_ok=", ok)


if __name__ == "__main__":
    main()
