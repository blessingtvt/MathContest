# -*- coding: utf-8 -*-
"""Q4 主模型 (M4: 波动电价 附件4 下重解 Q2、Q3)。

result4-2.xlsx = Q2 结构(全年联合LP, 波动电价);
result4-3.xlsx = Q3 结构(滚动MPC, 波动电价)。
输出: results/Q4/result4-2.xlsx, result4-3.xlsx + experiments/round1/run_summary.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import *


def main():
    b = load_bundle()
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    price_d = b["附件4_price"]          # (365,144) 波动电价
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()

    # ============ result4-2: 全年联合 LP (波动电价) ============
    full_cost, X, C, Q, E = full_year_lp(price_d.reshape(-1), load.reshape(-1), pv.reshape(-1), E0=E0_INIT)
    Xr, Cr, Qr = X[WARMUP_DAYS:], C[WARMUP_DAYS:], Q[WARMUP_DAYS:]
    Er = E[WARMUP_DAYS * T:]
    report_cost_42 = float((price_d[WARMUP_DAYS:].reshape(-1) * Xr.reshape(-1)).sum())
    Z = np.zeros((REPORT_DAYS, T))

    out_dir = os.path.join(RESULTS_DIR, "Q4")
    os.makedirs(os.path.join(out_dir, "experiments", "round1"), exist_ok=True)
    wb = openpyxl.load_workbook(os.path.join(TEMPLATE_DIR, "result4-2.xlsx"))
    fill_plan_grid(wb["计划购电量"], Xr)
    rebuild_charge_sheet(wb["充放电量"], dates, Cr, Qr, Er)
    rebuild_emergency_sheet(wb["紧急购电量"], dates, Z, labels)
    wb.save(os.path.join(out_dir, "result4-2.xlsx"))

    # ============ result4-3: 滚动 MPC (波动电价) ============
    X3 = np.zeros((REPORT_DAYS, T)); Y3 = np.zeros((REPORT_DAYS, T))
    C3 = np.zeros((REPORT_DAYS, T)); Q3 = np.zeros((REPORT_DAYS, T))
    Z3 = np.zeros((REPORT_DAYS, T))
    E0_arr = np.zeros(REPORT_DAYS); E24_arr = np.zeros(REPORT_DAYS)
    E = E0_INIT
    total_43 = 0.0
    row = 0
    for d in range(D):
        E_start = E
        cost, x, yf, cf, qf, E_end, z = q3_mpc_day(price_d[d], load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            E0_arr[row] = E_start
            E24_arr[row] = E_end
            X3[row], Y3[row], C3[row], Q3[row], Z3[row] = x, yf, cf, qf, z
            total_43 += cost
            row += 1
    E_flat = np.zeros(REPORT_DAYS * T + 1)
    for d in range(REPORT_DAYS):
        E_flat[d * T] = E0_arr[d]
        E_flat[d * T + T] = E24_arr[d]
    wb = openpyxl.load_workbook(os.path.join(TEMPLATE_DIR, "result4-3.xlsx"))
    fill_plan_grid(wb["计划购电量"], X3)
    fill_plan_grid(wb["调整购电量"], Y3)
    rebuild_charge_sheet(wb["充放电量"], dates, C3, Q3, E_flat)
    rebuild_emergency_sheet(wb["紧急购电量"], dates, Z3, labels)
    wb.save(os.path.join(out_dir, "result4-3.xlsx"))

    # ============ 基线 (波动电价) ============
    b_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        b_cost += no_storage(price_d[d], load[d], pv[d])[0]
    r_cost = 0.0
    E = E0_INIT
    for d in range(D):
        cost_d, _, _, _, Est = rule_arbitrage(price_d[d], load[d], pv[d], E0=E)
        E = Est[-1]
        if d >= WARMUP_DAYS:
            r_cost += cost_d

    summary = {
        "schema_version": 1,
        "question_id": "Q4",
        "experiment_id": "round1",
        "method": "M4-fluctuating-price-LP/MPC",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "data_sources": ["data_clean/cleaned_data.pkl"],
        "report_period": "2025-02-01 ~ 2025-12-31",
        "result4_2": {
            "objective_name": "报告期总购电费(元, 完美预见+波动电价)",
            "objective_value": round(report_cost_42, 2),
            "outputs": ["results/Q4/result4-2.xlsx"],
        },
        "result4_3": {
            "objective_name": "报告期总购电费(元, MPC+波动电价)",
            "objective_value": round(total_43, 2),
            "outputs": ["results/Q4/result4-3.xlsx"],
        },
        "baselines": [
            {"id": "B4", "name": "无储能(波动电价)", "objective_value": round(b_cost, 2)},
            {"id": "R4", "name": "规则套利(波动电价)", "objective_value": round(r_cost, 2)},
        ],
    }
    with open(os.path.join(out_dir, "experiments", "round1", "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
