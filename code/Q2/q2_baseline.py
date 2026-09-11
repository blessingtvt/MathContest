# -*- coding: utf-8 -*-
"""Q2 基线 (B2 无储能 + R2 规则套利, 日前预报信息集)。

与 q2_main.py 的主模型 M2(逐日滚动 LP) 同信息集: 0:00 日前光伏预报 + 附件2 实际结算 + 紧急购电。
输出: results/Q2/experiments/round2/baseline_metrics.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *


def rule_dayahead_day(price, load_d, pv_actual, forecast, d, E_carry):
    """R2 基线: 规则套利 + 0:00 日前预报(与 M2 同信息), 预报误差由紧急购电吸收。"""
    ghat0 = forecast_intervals(forecast, d, 0)
    _, x, c, q, Est = rule_arbitrage(price, load_d, ghat0, E0=E_carry)
    z = clip0(np.maximum(load_d * DT + c - x - pv_actual * DT - q, 0.0))
    cost = float((price * x).sum() + ALPHA_EM * (price * z).sum())
    return cost, x, c, q, Est[-1], z


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    D = load.shape[0]

    # B2 无储能 + 日前预报 + 紧急
    b_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        b_cost += no_storage_dayahead(price, load[d], pv[d], fc, d)[0]

    # B2_ref 无储能 + 完美预见 (诊断参考下界)
    b_ref_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        b_ref_cost += no_storage(price, load[d], pv[d])[0]

    # R2 规则套利 + 日前预报 (储能跨日结转)
    r_cost = 0.0
    Erule = E0_INIT
    for d in range(D):
        cost_d, _, _, _, E_end, _ = rule_dayahead_day(price, load[d], pv[d], fc, d, Erule)
        Erule = E_end
        if d >= WARMUP_DAYS:
            r_cost += cost_d

    out = {
        "schema_version": 1,
        "question_id": "Q2",
        "experiment_id": "round2",
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "baselines": [
            {"id": "B2", "name": "无储能(日前预报+紧急)", "objective_value": round(b_cost, 2)},
            {"id": "B2_ref", "name": "无储能(完美预见, 下界)", "objective_value": round(b_ref_cost, 2)},
            {"id": "R2", "name": "规则套利(日前预报)", "objective_value": round(r_cost, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q2", "experiments", "round2")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
