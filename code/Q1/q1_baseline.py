# -*- coding: utf-8 -*-
"""Q1 基线 (B1 无储能 + R1 规则套利)。输出 baseline_metrics.json。"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *


def main():
    b = load_bundle()
    a1 = b["附件1"]
    price = a1["price"]; load = a1["load"]; pv = a1["pv_forecast"]

    b_cost, bx = no_storage(price, load, pv)
    r_cost, rx, rc, rq, rE = rule_arbitrage(price, load, pv, E0=E0_INIT)

    out = {
        "question_id": "Q1",
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "baselines": [
            {"id": "B1", "name": "无储能", "objective_value": round(b_cost, 4),
             "total_purchase_kwh": round(float(bx.sum()), 4)},
            {"id": "R1", "name": "规则套利", "objective_value": round(r_cost, 4),
             "total_purchase_kwh": round(float(rx.sum()), 4),
             "terminal_E_kwh": round(float(rE[-1]), 4)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q1", "experiments", "round1")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
