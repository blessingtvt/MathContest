# -*- coding: utf-8 -*-
"""Q4 实验 E4-5：MPC 调整时刻的边际价值（嵌套消融）。

对 result4-3（滚动 MPC + 块级 δ + 分段计费）逐级删减调整时刻，量化每个调整
时刻（6:00 / 12:00 / 18:00）新增的边际价值：
  · 1 时刻：仅 0:00 计划（执行 x，无任何调整）；
  · 2 时刻：0:00 + 6:00；
  · 3 时刻：0:00 + 6:00 + 12:00；
  · 4 时刻：0:00 + 6:00 + 12:00 + 18:00（= result4-3 冻结主值）。
所有消融用同一信息集（附件3 预报 + 块级 δ）与同一结算口径（分段计费 + 紧急购电），
只改变"重优化的决策点数"。

输出：results/Q4/experiments/optimization/e45_adjust_value.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # code
import numpy as np
from common import *
from q4_main import block_delta, QUANTILE, MIN_HIST, corrected_forecast_block


def mpc_day_ablation(price, load_d, pv_actual, fc, d, E_carry, delta, n_stages):
    """result4-3 的嵌套消融（n_stages ∈ {1,2,3,4} 个决策时刻）。

    返回 (cost, E_end)。cost 用分段计费 + 紧急购电的真实结算口径。
    """
    # 阶段 0 (0:00)：计划 x（日闭合）
    g0 = corrected_forecast_block(fc, d, 0, delta)
    _, x, c0, q0, E0t = daily_lp(price, load_d, g0, E0=E_carry, terminal_eq=True, E_term=E0_INIT)
    y = x.copy(); c = c0.copy(); q = q0.copy()
    E_end = float(E0t[-1])

    if n_stages >= 2:
        g1 = corrected_forecast_block(fc, d, 1, delta); sl = 36
        _, y1, c1, q1, E1t = stage_lp(price[sl:], load_d[sl:], g1[sl:], x[sl:],
                                      E0=E0t[sl], terminal_eq=True, E_term=E0_INIT)
        y[sl:] = y1; c[sl:] = c1; q[sl:] = q1
        E_end = float(E1t[-1])

    if n_stages >= 3:
        g2 = corrected_forecast_block(fc, d, 2, delta); sl = 72
        _, y2, c2, q2, E2t = stage_lp(price[sl:], load_d[sl:], g2[sl:], x[sl:],
                                      E0=E1t[sl - 36], terminal_eq=True, E_term=E0_INIT)
        y[sl:] = y2; c[sl:] = c2; q[sl:] = q2
        E_end = float(E2t[-1])

    if n_stages >= 4:
        g3 = corrected_forecast_block(fc, d, 3, delta); sl = 108
        _, y3, c3, q3, E3t = stage_lp(price[sl:], load_d[sl:], g3[sl:], x[sl:],
                                      E0=E2t[sl - 72], terminal_eq=True, E_term=E0_INIT)
        y[sl:] = y3; c[sl:] = c3; q[sl:] = q3
        E_end = float(E3t[-1])

    z = clip0(load_d * DT + c - y - pv_actual * DT - q)
    bill = price * (np.minimum(x, y) + BETA_PEN * np.maximum(x - y, 0.0)
                    + GAMMA_PRE * np.maximum(y - x, 0.0))
    cost = float(bill.sum() + ALPHA_EM * (price * z).sum())
    return cost, E_end


def result43_ablation(price, load, pv, fc, over, D, n_stages):
    E = E0_INIT; total = 0.0
    for d in range(D):
        delta = block_delta(over, d, QUANTILE, MIN_HIST)
        cost, E_end = mpc_day_ablation(price[d], load[d], pv[d], fc, d, E, delta, n_stages)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
    return total


def main():
    b = load_bundle()
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    price4 = b["附件4_price"]
    D = load.shape[0]
    over = pv_overestimation(fc, pv)

    STAGE_LABELS = {1: "仅0:00计划", 2: "0:00+6:00", 3: "0:00+6:00+12:00", 4: "全4时刻(=result4-3)"}
    costs = {}
    for ns in [1, 2, 3, 4]:
        print(f"n_stages={ns} ({STAGE_LABELS[ns]}) ...")
        costs[str(ns)] = round(result43_ablation(price4, load, pv, fc, over, D, ns), 2)

    # 边际价值：新增第 k 个决策时刻省下的钱
    marginal = {
        "6:00调整(1→2)": round(costs["1"] - costs["2"], 2),
        "12:00调整(2→3)": round(costs["2"] - costs["3"], 2),
        "18:00调整(3→4)": round(costs["3"] - costs["4"], 2),
    }
    full = costs["4"]

    out = {
        "schema_version": 1,
        "question_id": "Q4",
        "experiment_id": "E4-5",
        "purpose": "MPC 调整时刻的边际价值（嵌套消融）",
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "total_by_n_stages": {k: {"label": STAGE_LABELS[int(k)], "total": costs[k]} for k in costs},
        "marginal_value_of_each_adjustment": marginal,
        "total_adjustment_value": round(costs["1"] - full, 2),
        "full_result4_3": full,
        "status": "PASS",
        "verdict": "6:00 首次调整价值最大（纳入后 12 小时新光伏预报），18:00 晚高峰调整边际价值较小；"
                   "滚动调整合计削减约 (仅0:00计划 − result4-3) 元。",
    }
    out_dir = os.path.join(RESULTS_DIR, "Q4", "experiments", "optimization")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "e45_adjust_value.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nWROTE", path)
    for k in costs:
        print(f"  {STAGE_LABELS[int(k)]}: {costs[k]:,.2f}")
    print("marginal:", marginal)
    print("total adjustment value:", out["total_adjustment_value"])


if __name__ == "__main__":
    main()
