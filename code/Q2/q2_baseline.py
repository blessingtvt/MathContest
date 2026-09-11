# -*- coding: utf-8 -*-
"""Q2 基线 (B2 无储能 + R2 规则套利, 自预报 + 80 分位风险修正信息集)。

与 q2_main.py 主模型 M2 同信息集: 附件2历史自预报净负荷 + 80 分位风险修正。
输出: results/Q2/experiments/round3/baseline_metrics.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *

W = [0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05]
QUANTILE = 80.0


def netload_forecast(N):
    D = N.shape[0]
    w = np.array(W)
    Nhat = np.zeros_like(N)
    for d in range(len(w), D):
        for k in range(len(w)):
            Nhat[d] += w[k] * N[d - 1 - k]
    return Nhat, N - Nhat


def no_storage_forecast(price, Nsafe, Nreal):
    x = np.maximum(Nsafe * DT, 0.0)
    z = np.maximum(Nreal * DT - x, 0.0)
    return float((price * x).sum() + ALPHA_EM * (price * z).sum()), x, z


def rule_forecast_day(price, Nsafe, Nreal, E_carry):
    _, x, c, q, Est = rule_arbitrage(price, Nsafe, np.zeros(T), E0=E_carry)
    z = clip0(np.maximum(Nreal * DT + c - x - q, 0.0))
    cost = float((price * x).sum() + ALPHA_EM * (price * z).sum())
    return cost, x, c, q, Est[-1], z


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    D = load.shape[0]
    N = load - pv
    Nhat, Eerr = netload_forecast(N)

    b_cost = b_ref_cost = r_cost = 0.0
    Erule = E0_INIT
    for d in range(WARMUP_DAYS, D):
        e80 = np.percentile(Eerr[7:d], QUANTILE, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e80
        b_cost += no_storage_forecast(price, Nsafe, N[d])[0]
        b_ref_cost += no_storage(price, load[d], pv[d])[0]
        rc, _, _, _, E_end, _ = rule_forecast_day(price, Nsafe, N[d], Erule)
        r_cost += rc
        Erule = E_end

    out = {
        "schema_version": 1,
        "question_id": "Q2",
        "experiment_id": "round3",
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "forecast": "净负荷 7天加权平均 + 80分位风险修正",
        "baselines": [
            {"id": "B2", "name": "无储能(自预报+80分位)", "objective_value": round(b_cost, 2)},
            {"id": "B2_ref", "name": "无储能(完美预见, 下界)", "objective_value": round(b_ref_cost, 2)},
            {"id": "R2", "name": "规则套利(自预报+80分位)", "objective_value": round(r_cost, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q2", "experiments", "round3")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
