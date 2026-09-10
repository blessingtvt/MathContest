# -*- coding: utf-8 -*-
"""Q3 主模型 (M3: 滚动时域 MPC + 分段计费线性化)。

0:00 用 0:00 预报制定计划 x; 6/12/18 各据最新预报调整 y;
计费 = p·min(x,y)+0.5p·max(x-y,0)+1.5p·max(y-x,0); 紧急购电用附件2实际值结算(5倍)。
输出: results/Q3/result3.xlsx + experiments/round1/run_summary.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import *


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]     # (1460,24)
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()

    # ---- 主模型 M3: 滚动 MPC ----
    X = np.zeros((REPORT_DAYS, T)); Y = np.zeros((REPORT_DAYS, T))
    C = np.zeros((REPORT_DAYS, T)); Q = np.zeros((REPORT_DAYS, T))
    Z = np.zeros((REPORT_DAYS, T))
    E0_arr = np.zeros(REPORT_DAYS); E24_arr = np.zeros(REPORT_DAYS)
    E = E0_INIT
    total = 0.0
    row = 0
    for d in range(D):
        E_start = E
        cost, x, yf, cf, qf, E_end, z = q3_mpc_day(price, load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            E0_arr[row] = E_start
            E24_arr[row] = E_end
            X[row], Y[row], C[row], Q[row], Z[row] = x, yf, cf, qf, z
            total += cost
            row += 1

    # ---- 基线 ----
    # B3 静态不调整 (仅 0:00 计划并执行, 储能跨日)
    b3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        cost, _, _, _, E_end, _ = q3_static_day(price, load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            b3_cost += cost
    # R3 规则套利 (滚动预报贪心, 与 M3 同信息同计费)
    r3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        cost_d, _, _, _, _, E_end, _ = rule_mpc_day(price, load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            r3_cost += cost_d

    # ---- 写 result3.xlsx ----
    out_dir = os.path.join(RESULTS_DIR, "Q3")
    os.makedirs(os.path.join(out_dir, "experiments", "round1"), exist_ok=True)
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
    emergency_cost = float(np.sum(ALPHA_EM * price_r * Z))

    summary = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": "round1",
        "method": "M3-MPC",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "data_sources": ["data_clean/cleaned_data.pkl"],
        "report_period": "2025-02-01 ~ 2025-12-31",
        "main": {
            "method_id": "M3",
            "objective_name": "报告期总购电费(元, 含违约/溢价/紧急)",
            "objective_value": round(total, 2),
            "plan_cost": round(plan_cost, 2),
            "penalty_cost": round(penalty_cost, 2),
            "emergency_cost": round(emergency_cost, 2),
            "outputs": ["results/Q3/result3.xlsx"],
        },
        "baselines": [
            {"id": "B3", "name": "静态不调整", "objective_value": round(b3_cost, 2)},
            {"id": "R3", "name": "规则套利", "objective_value": round(r3_cost, 2)},
        ],
        "metrics": {
            "调整价值_元": round(b3_cost - total, 2),
            "优化价值_元": round(r3_cost - total, 2),
        },
    }
    with open(os.path.join(out_dir, "experiments", "round1", "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
