# -*- coding: utf-8 -*-
"""Q3 分位敏感性 × 成本构成（块级 round4）。

对每个分位 q，输出 总费用 + 计划/违约溢价/紧急 三项分解，供图5（分位-成本分解）使用。
复用 code/Q3/q3_new_methods/q3_optimized.py 的块级 mpc_day。

输出: results/Q3/experiments/round4/quantile_decomp.json
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # code/Q3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # code
import numpy as np
from common import *
import q3_new_methods.q3_optimized as qopt

Q_LIST = [0, 50, 60, 70, 80, 82, 85, 88, 90, 92, 95, 100]


def run_quantile(price, load, pv, fc, over, D, q):
    E = E0_INIT
    plan = penalty = emergency = 0.0
    for d in range(D):
        delta = qopt.block_delta(over, d, q)
        cost, x, y, c, qv, E_end, z, _E_day = qopt.mpc_day(price, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            plan += float((price * np.minimum(x, y)).sum())
            penalty += float((price * (BETA_PEN * np.maximum(x - y, 0.0)
                                       + GAMMA_PRE * np.maximum(y - x, 0.0))).sum())
            emergency += float((ALPHA_EM * price * z).sum())
    return {"q": q, "total": round(plan + penalty + emergency, 2),
            "plan": round(plan, 2), "penalty": round(penalty, 2),
            "emergency": round(emergency, 2)}


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]
    over = qopt.block_over(fc, pv)
    out = {"schema_version": 1, "question_id": "Q3", "method": "block-level issue×execution-block",
           "quantiles": [run_quantile(price, load, pv, fc, over, D, q) for q in Q_LIST]}
    out_dir = os.path.join(RESULTS_DIR, "Q3", "experiments", "round4")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "quantile_decomp.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
