# -*- coding: utf-8 -*-
"""Q3 G4 稳健性分析（块级 risk correction，round4）。

与 round3 稳健性分析同构，但把「按 issue 标量修正」换成「按 issue × 执行块 逐区间
80 分位修正」，与主模型（round4 块级 q=80）同口径。

覆盖:
  1. 调整阶段消融 (stage ablation): 逐次加入 6/12/18 调整的边际价值。
  2. 完美预见上界 (4 时刻用实际光伏)。
  3. 数据扰动: 负荷/光伏 ±5%。
  4. 光伏预报误差-前瞻时域曲线 (数据级, 与方法无关)。
  5. 分位敏感性 (块级): q∈{0,50,60,70,80,82,85,88,90,92,95,100}。

输出: results/Q3/experiments/round4/robustness_report.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # code/Q3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # code
import numpy as np
from common import *
import q3_new_methods.q3_optimized as qopt

ROUND = "round4"
QUANTILE = 80.0


def mpc_day_block_general(price, load_d, pv_actual, fc, d, E_carry, delta, stages):
    """广义块级滚动 MPC。stages: 升序 issue 索引(0=0:00), 每阶段用块级修正预报。"""
    assert stages[0] == 0
    g0 = qopt.corrected_forecast(fc, d, 0, delta)
    _, x, c0, q0, E0t = daily_lp(price, load_d, g0, E0=E_carry,
                                 terminal_eq=True, E_term=E0_INIT)
    y_blocks = [x[:36]]; c_blocks = [c0[:36]]; q_blocks = [q0[:36]]
    E_prev = E0t
    yk, ck, qk = x, c0, q0
    for k in range(1, len(stages)):
        s = stages[k]; prev_s = stages[k - 1]
        sl = 36 * s
        g = qopt.corrected_forecast(fc, d, s, delta)
        E0_k = E_prev[36 * (s - prev_s)]
        _, yk, ck, qk, Ek = stage_lp(price[sl:], load_d[sl:], g[sl:], x[sl:],
                                     E0=E0_k, terminal_eq=True, E_term=E0_INIT)
        y_blocks.append(yk[:36]); c_blocks.append(ck[:36]); q_blocks.append(qk[:36])
        E_prev = Ek
    sm = stages[-1]
    tail = 144 - 36 * sm - 36
    if tail > 0:
        y_blocks.append(yk[36:36 + tail]); c_blocks.append(ck[36:36 + tail]); q_blocks.append(qk[36:36 + tail])
    y = np.concatenate(y_blocks); c = np.concatenate(c_blocks); q = np.concatenate(q_blocks)
    E_end = E_prev[-1]
    z = clip0(np.maximum(load_d * DT + c - y - pv_actual * DT - q, 0.0))
    bill = price * (np.minimum(x, y) + BETA_PEN * np.maximum(x - y, 0.0)
                    + GAMMA_PRE * np.maximum(y - x, 0.0))
    cost = float(bill.sum() + ALPHA_EM * (price * z).sum())
    return cost, x, y, c, q, E_end, z


def run_year_block(price, load, pv, fc, over, D, stages, quantile, perfect=False):
    """全年滚动块级 MPC。perfect=True 用实际光伏替代预报(无修正)。返回 (total, emg_cost, curt)。"""
    total = emg = curt = 0.0
    E = E0_INIT
    for d in range(D):
        if perfect:
            # 完美预见: 各阶段直接用实际光伏, 无修正
            _, x, c0, q0, E0t = daily_lp(price, load[d], pv[d], E0=E,
                                         terminal_eq=True, E_term=E0_INIT)
            y_blocks = [x[:36]]; c_blocks = [c0[:36]]; q_blocks = [q0[:36]]
            E_prev = E0t; yk, ck, qk = x, c0, q0
            for k in range(1, len(stages)):
                s = stages[k]; prev_s = stages[k - 1]; sl = 36 * s
                E0_k = E_prev[36 * (s - prev_s)]
                _, yk, ck, qk, Ek = stage_lp(price[sl:], load[d][sl:], pv[d][sl:], x[sl:],
                                             E0=E0_k, terminal_eq=True, E_term=E0_INIT)
                y_blocks.append(yk[:36]); c_blocks.append(ck[:36]); q_blocks.append(qk[:36])
                E_prev = Ek
            sm = stages[-1]; tail = 144 - 36 * sm - 36
            if tail > 0:
                y_blocks.append(yk[36:36 + tail]); c_blocks.append(ck[36:36 + tail]); q_blocks.append(qk[36:36 + tail])
            y = np.concatenate(y_blocks); c = np.concatenate(c_blocks); q = np.concatenate(q_blocks)
            E_end = E_prev[-1]
            z = clip0(np.maximum(load[d] * DT + c - y - pv[d] * DT - q, 0.0))
            cost = float((price * (np.minimum(x, y) + BETA_PEN * np.maximum(x - y, 0.0)
                                   + GAMMA_PRE * np.maximum(y - x, 0.0))).sum()
                         + ALPHA_EM * (price * z).sum())
        else:
            delta = qopt.block_delta(over, d, quantile)
            cost, x, y, c, q, E_end, z = mpc_day_block_general(
                price, load[d], pv[d], fc, d, E, delta, stages)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
            emg += float(np.sum(ALPHA_EM * price * z))
            curt += float(clip0(y + pv[d] * DT + q - (load[d] * DT + c)).sum())
    return total, emg, curt


def horizon_error_p80(fc, pv):
    """各 issue 光伏高估 P80 随前瞻时域 h=1..24 变化 (数据级, 与方法无关)。"""
    D = pv.shape[0]
    pv_hourly = pv.reshape(D, 24, 6).mean(axis=2)
    he = {}
    for s in range(4):
        fc_s = fc[s::4]
        arr = np.zeros(24)
        for h in range(1, 25):
            col = h - 1; actual_hour = 6 * s + h
            if actual_hour < 24:
                arr[h - 1] = float(np.percentile(fc_s[:, col] - pv_hourly[:, actual_hour], 80))
            else:
                arr[h - 1] = np.nan
        he[s] = [None if np.isnan(v) else round(float(v), 2) for v in arr]
    return he


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]
    over = qopt.block_over(fc, pv)
    stages4 = [0, 1, 2, 3]

    # ---- 1. 调整阶段消融 ----
    stage_results = {}
    for stages in ([0], [0, 1], [0, 1, 2], [0, 1, 2, 3]):
        tot, emg, curt = run_year_block(price, load, pv, fc, over, D, list(stages), QUANTILE)
        stage_results["+".join(f"{6*s}" for s in stages)] = {
            "stages": stages, "total": round(tot, 2),
            "emergency": round(emg, 2), "curtailment": round(curt, 2)}

    # ---- 2. 完美预见上界 ----
    tot_pf, emg_pf, curt_pf = run_year_block(price, load, pv, fc, over, D, stages4, QUANTILE, perfect=True)

    # ---- 3. 数据扰动 (负荷/光伏 ±5%) ----
    pert = {}
    for name, ld, pvv, ov in [
        ("base", load, pv, over),
        ("load+5%", load * 1.05, pv, over),
        ("load-5%", load * 0.95, pv, over),
        ("pv+5%", load, pv * 1.05, qopt.block_over(fc, pv * 1.05)),
        ("pv-5%", load, pv * 0.95, qopt.block_over(fc, pv * 0.95)),
    ]:
        tot, emg, curt = run_year_block(price, ld, pvv, fc, ov, D, stages4, QUANTILE)
        pert[name] = {"total": round(tot, 2), "emergency": round(emg, 2), "curtailment": round(curt, 2)}

    # ---- 4. 误差-时域曲线 ----
    he_p80 = horizon_error_p80(fc, pv)

    # ---- 5. 分位敏感性 (块级) ----
    sweep = {}
    for q in (0, 50, 60, 70, 80, 82, 85, 88, 90, 92, 95, 100):
        tot_q = 0.0; E = E0_INIT
        for d in range(D):
            delta = qopt.block_delta(over, d, q)
            cost, x, y, c, qv, E_end, z, _E_day = qopt.mpc_day(price, load[d], pv[d], fc, d, E, delta)
            E = E_end
            if d >= WARMUP_DAYS:
                tot_q += cost
        sweep[f"q{q}"] = round(tot_q, 2)

    report = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": ROUND,
        "method": "block-level issue×execution-block risk correction",
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "stage_ablation": stage_results,
        "perfect_forecast_upper_bound": {
            "total": round(tot_pf, 2), "emergency": round(emg_pf, 2), "curtailment": round(curt_pf, 2),
            "note": "4个调整时刻但用附件2实际光伏(完美预见), 为任何预报方案的下界"},
        "perturbation": pert,
        "horizon_error_p80_kW": he_p80,
        "quantile_sweep_total": sweep,
    }
    out_dir = os.path.join(RESULTS_DIR, "Q3", "experiments", ROUND)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "robustness_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
