# -*- coding: utf-8 -*-
"""Q4 基线 (B4 无储能 + R4 规则套利, 波动电价)。输出 baseline_metrics.json。"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *


def main():
    b = load_bundle()
    load = b["附件2_load"]; pv = b["附件2_pv"]; price_d = b["附件4_price"]
    D = load.shape[0]

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

    out = {
        "question_id": "Q4",
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "baselines": [
            {"id": "B4", "name": "无储能(波动电价)", "objective_value": round(b_cost, 2)},
            {"id": "R4", "name": "规则套利(波动电价)", "objective_value": round(r_cost, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q4", "experiments", "round1")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
