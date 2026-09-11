# -*- coding: utf-8 -*-
"""Q4 基线 (B4 无储能 + R4 规则套利 + B4_ref 完美预见诊断下界)，波动电价。

与 q4_main.py 主模型同口径：B4/R4 用附件2历史净负荷自预报 + 按星期分桶80分位风险修正；
B4_ref 用完美预见（真实净负荷）作诊断下界。
输出: results/Q4/experiments/round2/baseline_metrics.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *

ROUND = "round2"
QUANTILE = 80.0
W = [0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05]


def bundle_dow(bundle):
    return np.array([datetime.strptime(s, "%Y-%m-%d %H:%M:%S").weekday()
                     for s in bundle["dates"]])


def error_quantile_dow(Eerr, full_dow, d, quantile=80.0):
    hist = Eerr[7:d]
    hd = full_dow[7:d]
    mask = hd == full_dow[d]
    if mask.sum() == 0:
        return np.zeros(Eerr.shape[1])
    return np.percentile(hist[mask], quantile, axis=0)


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
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    price_d = b["附件4_price"]
    D = load.shape[0]
    N = load - pv
    Nhat, Eerr = netload_forecast(N)
    full_dow = bundle_dow(b)

    b4 = b4ref = r4 = 0.0
    Erule = E0_INIT
    for d in range(WARMUP_DAYS, D):
        e80 = error_quantile_dow(Eerr, full_dow, d, QUANTILE)
        Nsafe = Nhat[d] + e80
        b4 += no_storage_forecast(price_d[d], Nsafe, N[d])[0]
        b4ref += no_storage(price_d[d], load[d], pv[d])[0]
        rc, _, _, _, E_end, _ = rule_forecast_day(price_d[d], Nsafe, N[d], Erule)
        r4 += rc
        Erule = E_end

    out = {
        "schema_version": 1,
        "question_id": "Q4",
        "experiment_id": ROUND,
        "seed": SEED,
        "created_at": datetime.now().isoformat(),
        "report_period": "2025-02-01 ~ 2025-12-31",
        "forecast": "净负荷 7天加权平均 w=[0.3,0.2,0.15,0.12,0.1,0.08,0.05] + 按星期分桶80分位风险修正",
        "baselines": [
            {"id": "B4", "name": "无储能(自预报+星期80分位,波动电价)", "objective_value": round(b4, 2)},
            {"id": "R4", "name": "规则套利(自预报+星期80分位,波动电价)", "objective_value": round(r4, 2)},
            {"id": "B4_ref", "name": "无储能(完美预见,波动电价,诊断下界)", "objective_value": round(b4ref, 2)},
        ],
    }
    out_dir = os.path.join(RESULTS_DIR, "Q4", "experiments", ROUND)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    main()
