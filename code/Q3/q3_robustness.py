# -*- coding: utf-8 -*-
"""Q3 G4 稳健性分析 (robustness-checker)。

覆盖:
  1. 调整阶段消融 (stage ablation): 逐次加入 6:00/12:00/18:00 调整, 度量每个预报时刻的边际价值,
     直接回答「是否需要引入其他时刻的预报」。
  2. 完美预见上界: 4 个调整时刻但用附件2实际光伏替代预报 -> 任何预报方案的下界。
  3. 数据扰动: 负荷/光伏 ±5%, 观察总费用变化幅度 (无断崖)。
  4. 光伏预报误差-前瞻时域曲线: 度量误差随预测时域增长, 支撑「是否加报」结论。
  5. 分位敏感性: 重跑 q∈{0,50,60,70,80,90,95,100} 确认 80 分位近最优。

输出: results/Q3/experiments/round3/robustness_report.json + robustness_report.md
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *

ROUND = "round3"
QUANTILE = 80.0
MIN_HIST = 7


def mpc_day_general(price, load_d, pv_actual, ghats, E_carry, stages):
    """广义滚动 MPC。ghats: {issue_idx: 144维光伏预报(kW)}; stages: 升序 issue 索引, stages[0]=0。

    返回 (cost, x, y_final, c_final, q_final, E_end, z)。
    """
    assert stages[0] == 0
    _, x, c0, q0, E0t = daily_lp(price, load_d, ghats[0], E0=E_carry,
                                 terminal_eq=True, E_term=E0_INIT)
    y_blocks = [x[:36]]; c_blocks = [c0[:36]]; q_blocks = [q0[:36]]
    E_prev = E0t
    yk, ck, qk = x, c0, q0           # 末段方案默认取自 0:00 计划
    for k in range(1, len(stages)):
        s = stages[k]; prev_s = stages[k - 1]
        sl = 36 * s
        E0_k = E_prev[36 * (s - prev_s)]
        _, yk, ck, qk, Ek = stage_lp(price[sl:], load_d[sl:], ghats[s][sl:], x[sl:],
                                     E0=E0_k, terminal_eq=True, E_term=E0_INIT)
        y_blocks.append(yk[:36]); c_blocks.append(ck[:36]); q_blocks.append(qk[:36])
        E_prev = Ek
    sm = stages[-1]
    tail = 144 - 36 * sm - 36
    if tail > 0:
        y_blocks.append(yk[36:36 + tail]); c_blocks.append(ck[36:36 + tail]); q_blocks.append(qk[36:36 + tail])
    y_final = np.concatenate(y_blocks)
    c_final = np.concatenate(c_blocks)
    q_final = np.concatenate(q_blocks)
    E_end = E_prev[-1]

    z = clip0(np.maximum(load_d * DT + c_final - y_final - pv_actual * DT - q_final, 0.0))
    bill = price * (np.minimum(x, y_final)
                    + BETA_PEN * np.maximum(x - y_final, 0.0)
                    + GAMMA_PRE * np.maximum(y_final - x, 0.0))
    cost = float(bill.sum() + ALPHA_EM * (price * z).sum())
    return cost, x, y_final, c_final, q_final, E_end, z


def run_year(price, load, pv, fc, over, D, stages, perfect=False):
    """全年滚动 MPC(广义 stages)。perfect=True 用实际光伏替代预报(无修正)。返回 (total, emg_cost, curt_energy)。"""
    total = 0.0
    emg_cost = 0.0
    curt = 0.0
    E = E0_INIT
    for d in range(D):
        if perfect:
            ghats = {s: pv[d] for s in stages}
        else:
            delta = issue_risk_delta(over, d, QUANTILE, MIN_HIST)
            ghats = {s: clip0(forecast_intervals(fc, d, s) - delta[s]) for s in stages}
        cost, x, y, c, q, E_end, z = mpc_day_general(price, load[d], pv[d], ghats, E, stages)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
            emg_cost += float(np.sum(ALPHA_EM * price * z))
            curt += float(clip0(y + pv[d] * DT + q - (load[d] * DT + c)).sum())
    return total, emg_cost, curt


def horizon_error(forecast, pv):
    """各 issue 的光伏预报误差统计 (按前瞻小时 h=1..24)。返回 {issue: {mean, p80}} 数组。"""
    D = pv.shape[0]
    pv_hourly = pv.reshape(D, 24, 6).mean(axis=2)  # (D,24) 小时均值
    out = {}
    for s in range(4):
        fc_s = forecast[s::4]  # (D, 24)
        err = np.zeros(24)
        for h in range(1, 25):
            col = h - 1
            # issue s 的预报值列 col 对应实际小时 6*s + h
            actual_hour = 6 * s + h
            if actual_hour < 24:
                err[h - 1] = float(np.mean(fc_s[:, col] - pv_hourly[:, actual_hour]))
            else:
                err[h - 1] = np.nan
        out[s] = err
    return out


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    D = load.shape[0]
    over = pv_overestimation(fc, pv)

    # ---- 1. 调整阶段消融 ----
    stage_results = {}
    for stages in ([0], [0, 1], [0, 1, 2], [0, 1, 2, 3]):
        tot, emg, curt = run_year(price, load, pv, fc, over, D, list(stages))
        stage_results["+".join(f"{6*s}" for s in stages)] = {
            "stages": stages, "total": round(tot, 2),
            "emergency": round(emg, 2), "curtailment": round(curt, 2)}

    # ---- 2. 完美预见上界 ----
    tot_pf, emg_pf, curt_pf = run_year(price, load, pv, fc, over, D, [0, 1, 2, 3], perfect=True)

    # ---- 3. 数据扰动 (负荷/光伏 ±5%) ----
    pert = {}
    for name, ld, pvv, ov in [
        ("base", load, pv, over),
        ("load+5%", load * 1.05, pv, over),
        ("load-5%", load * 0.95, pv, over),
        ("pv+5%", load, pv * 1.05, pv_overestimation(fc, pv * 1.05)),
        ("pv-5%", load, pv * 0.95, pv_overestimation(fc, pv * 0.95)),
    ]:
        tot, emg, curt = run_year(price, ld, pvv, fc, ov, D, [0, 1, 2, 3])
        pert[name] = {"total": round(tot, 2), "emergency": round(emg, 2), "curtailment": round(curt, 2)}

    # ---- 4. 误差-时域曲线 ----
    he = horizon_error(fc, pv)
    # 用 P80 高估(正值=高估)逐小时统计
    pv_hourly = pv.reshape(D, 24, 6).mean(axis=2)
    he_p80 = {}
    for s in range(4):
        fc_s = fc[s::4]
        arr = np.zeros(24)
        for h in range(1, 25):
            col = h - 1; actual_hour = 6 * s + h
            if actual_hour < 24:
                arr[h - 1] = float(np.percentile(fc_s[:, col] - pv_hourly[:, actual_hour], 80))
            else:
                arr[h - 1] = np.nan
        he_p80[s] = [None if np.isnan(v) else round(float(v), 2) for v in arr]
    he_mean = {s: [None if np.isnan(v) else round(float(v), 2) for v in arr] for s, arr in he.items()}

    # ---- 5. 分位敏感性 (重跑) ----
    sweep = {}
    for q in (0, 50, 60, 70, 80, 90, 95, 100):
        tot_q = 0.0
        E = E0_INIT
        for d in range(D):
            delta = issue_risk_delta(over, d, q, MIN_HIST)
            ghats = {s: clip0(forecast_intervals(fc, d, s) - delta[s]) for s in (0, 1, 2, 3)}
            cost, _, _, _, _, E_end, _ = mpc_day_general(price, load[d], pv[d], ghats, E, [0, 1, 2, 3])
            E = E_end
            if d >= WARMUP_DAYS:
                tot_q += cost
        sweep[f"q{q}"] = round(tot_q, 2)

    report = {
        "schema_version": 1,
        "question_id": "Q3",
        "experiment_id": ROUND,
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "stage_ablation": stage_results,
        "perfect_forecast_upper_bound": {
            "total": round(tot_pf, 2), "emergency": round(emg_pf, 2), "curtailment": round(curt_pf, 2),
            "note": "4个调整时刻但用附件2实际光伏(完美预见), 为任何预报方案的下界"},
        "perturbation": pert,
        "horizon_error_mean_kW": he_mean,
        "horizon_error_p80_kW": he_p80,
        "quantile_sweep_total": sweep,
    }
    out_dir = os.path.join(RESULTS_DIR, "Q3", "experiments", ROUND)
    with open(os.path.join(out_dir, "robustness_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
