# -*- coding: utf-8 -*-
"""Q3 基线 (B3 静态不调整 + R3 规则套利, 均日闭合 + 按 issue 80分位光伏风险修正)。
输出: results/Q3/experiments/round3/baseline_metrics.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *

ROUND = "round3"
QUANTILE = 80.0
MIN_HIST = 7


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]
    over = pv_overestimation(fc, pv)

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

    ns_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        ns_cost += no_storage(price, load[d], pv[d])[0]

    out = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": ROUND,
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "risk_correction": "issue(0/6/12/18) 80分位保守修正",
        "baselines": [
            {"id": "B3", "name": "静态不调整(日闭合+修正)", "objective_value": round(b3_cost, 2)},
            {"id": "R3", "name": "规则套利(日闭合+修正)", "objective_value": round(r3_cost, 2)},
            {"id": "B3_ref", "name": "无储能(完美预见,下界)", "objective_value": round(ns_cost, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q3", "experiments", ROUND)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
