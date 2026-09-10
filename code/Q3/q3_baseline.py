# -*- coding: utf-8 -*-
"""Q3 基线 (B3 静态不调整 + R3 规则套利)。输出 baseline_metrics.json。"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]

    b3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        cost, _, _, _, E_end, _ = q3_static_day(price, load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            b3_cost += cost

    r3_cost = 0.0
    E = E0_INIT
    for d in range(D):
        cost_d, _, _, _, _, E_end, _ = rule_mpc_day(price, load[d], pv[d], fc, d, E)
        E = E_end
        if d >= WARMUP_DAYS:
            r3_cost += cost_d

    out = {
        "question_id": "Q3",
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "baselines": [
            {"id": "B3", "name": "静态不调整", "objective_value": round(b3_cost, 2)},
            {"id": "R3", "name": "规则套利", "objective_value": round(r3_cost, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q3", "experiments", "round1")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
