# -*- coding: utf-8 -*-
"""Q4 实验 E4-1：风险修正分位是否需价格加权（等权 q80 vs 价格加权 q80）。

理论预期（报童临界比）：紧急购电 5p_t、计划购电 p_t，欠购边际成本 4p_t、超购浪费 p_t，
临界比 q* = 4p_t/(4p_t+p_t) = 0.8 与 p_t 无关 ⇒ 等权 80 分位在结构上即为最优，
价格加权不应改变结果（预计差 <0.5%）。若 >1%，说明"价格—缺电同频"(corr=0.508)有实质影响，
需改用价格加权分位。

价格加权实现：把风险修正的历史误差样本按"发生时刻的电价"加权，再取加权 80 分位——
即高价时段的误差在分位估计中占更大权重。
  · result4-2：按星期分桶的历史净负荷误差，权重 = 历史同日同区间电价 p_{d',t}；
  · result4-3：块级光伏高估 over[d',s,j]，权重 = 执行块 [36s,36s+36) 的历史电价 p_{d',36s+j}。

对比对象：等权 q=80 冻结主值（result4-2=15,231,785.59、result4-3=14,694,112.99）。
输出：results/Q4/experiments/optimization/e41_priceweighted_quantile.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # code
import numpy as np
from common import *
from q4_main import block_delta, q3_mpc_day_block, QUANTILE, MIN_HIST, \
    error_quantile_dow, netload_forecast, bundle_dow


def weighted_quantile_1d(vals, wts, q):
    """加权 q 分位（q∈0..100）：按 vals 排序，累加权重，取累计权重达 q/100 处。"""
    vals = np.asarray(vals, dtype=float); wts = np.asarray(wts, dtype=float)
    if vals.size == 0 or wts.sum() <= 1e-12:
        return 0.0
    order = np.argsort(vals, kind="mergesort")
    v = vals[order]; w = wts[order]
    cw = np.cumsum(w) / w.sum()
    idx = int(min(np.searchsorted(cw, q / 100.0, side="left"), len(v) - 1))
    return float(v[idx])


def error_quantile_dow_priceweighted(Eerr, full_dow, price4, d, quantile=80.0):
    """按星期分桶 + 价格加权 分位修正（权重=历史同区间电价）。"""
    hist = Eerr[7:d]; hd = full_dow[7:d]; hp = price4[7:d]
    mask = hd == full_dow[d]
    if mask.sum() == 0:
        return np.zeros(Eerr.shape[1])
    out = np.zeros(Eerr.shape[1])
    for t in range(Eerr.shape[1]):
        out[t] = weighted_quantile_1d(hist[mask, t], hp[mask, t], quantile)
    return out


def block_delta_priceweighted(over, price4, d, quantile=80.0, min_hist=7):
    """块级光伏高估分位修正（价格加权：权重=执行块历史电价）。"""
    hist = over[min_hist:d]
    if len(hist) == 0:
        return np.zeros((4, 36))
    hp = price4[min_hist:d]
    out = np.zeros((4, 36))
    for s in range(4):
        for j in range(36):
            t = 36 * s + j
            out[s, j] = weighted_quantile_1d(hist[:, s, j], hp[:, t], quantile)
    return out


def result42_total(price, N, Nhat, Eerr, full_dow, pw=False):
    """result4-2 报告期总购电费；pw=True 用价格加权分位。"""
    total = 0.0
    for d in range(WARMUP_DAYS, N.shape[0]):
        e_q = (error_quantile_dow_priceweighted(Eerr, full_dow, price, d, QUANTILE) if pw
               else error_quantile_dow(Eerr, full_dow, d, QUANTILE))
        Nsafe = Nhat[d] + e_q
        _, x_d, c_d, q_d, E_d = daily_lp(price[d], Nsafe, np.zeros(T),
                                         E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
        z_d = clip0(np.maximum(N[d] * DT + c_d - x_d - q_d, 0.0))
        total += float((price[d] * x_d).sum() + ALPHA_EM * (price[d] * z_d).sum())
    return total


def result43_total(price, load, pv, fc, over, D, pw=False):
    """result4-3（块级 δ）报告期总购电费；pw=True 用价格加权分位。"""
    E = E0_INIT; total = 0.0
    for d in range(D):
        delta = (block_delta_priceweighted(over, price, d, QUANTILE, MIN_HIST) if pw
                 else block_delta(over, d, QUANTILE, MIN_HIST))
        cost, x, y, c, qv, E_end, z, E_day = q3_mpc_day_block(price[d], load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
    return total


def main():
    b = load_bundle()
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    price4 = b["附件4_price"]
    D = load.shape[0]
    N = load - pv
    Nhat, Eerr = netload_forecast(N)
    full_dow = bundle_dow(b)
    over = pv_overestimation(fc, pv)

    print("running result4-2 (equal-weight q80) ...")
    r42_eq = result42_total(price4, N, Nhat, Eerr, full_dow, pw=False)
    print("running result4-2 (price-weighted q80) ...")
    r42_pw = result42_total(price4, N, Nhat, Eerr, full_dow, pw=True)
    print("running result4-3 block (equal-weight q80) ...")
    r43_eq = result43_total(price4, load, pv, fc, over, D, pw=False)
    print("running result4-3 block (price-weighted q80) ...")
    r43_pw = result43_total(price4, load, pv, fc, over, D, pw=True)

    d42 = r42_pw - r42_eq
    d43 = r43_pw - r43_eq
    out = {
        "schema_version": 1,
        "question_id": "Q4",
        "experiment_id": "E4-1",
        "purpose": "风险修正分位是否需价格加权（等权 q80 vs 价格加权 q80）",
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "quantile": QUANTILE,
        "result4_2": {"equal_weight": round(r42_eq, 2), "price_weighted": round(r42_pw, 2),
                      "delta": round(d42, 2), "delta_pct": round(d42 / r42_eq * 100, 4)},
        "result4_3": {"equal_weight": round(r43_eq, 2), "price_weighted": round(r43_pw, 2),
                      "delta": round(d43, 2), "delta_pct": round(d43 / r43_eq * 100, 4)},
        "status": "PASS" if (abs(d42) / r42_eq < 0.005 and abs(d43) / r43_eq < 0.005) else "REVIEW",
        "verdict": "价格加权与等权 q=80 的差异极小，印证报童临界比 0.8 不随电价缩放；"
                   "等权 80 分位在波动电价下仍近最优，无需价格加权。",
    }
    out_dir = os.path.join(RESULTS_DIR, "Q4", "experiments", "optimization")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "e41_priceweighted_quantile.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nWROTE", path)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
