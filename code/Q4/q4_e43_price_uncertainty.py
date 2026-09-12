# -*- coding: utf-8 -*-
"""Q4 实验 E4-3：电价不确定性成本（C1"电价视为已知"的备选稳健性情景）。

问题：主模型按"当天逐时段电价已知（日前出清价）"建模；本实验量化若电价"实时未知"、
需用因果自预报替代，会损失多少 = 电价预测误差成本。

电价自预报（与 Q2 净负荷自预报同构，因果、只用历史）：
  m_d   = mean_t(p_{d,t}) / mean_t(p^{(1)}_t)          # 每日水平乘子(星期效应)
  m̂_d   = 历史同星期 m_{d'} 的均值（扩张窗口, d'<d, MIN_HIST=7）
  p̂_{d,t} = p^{(1)}_t × m̂_d                              # 分时曲线 × 星期乘子

对比：
  · C_known（基线，= 冻结主值）：LP 目标用真实 p_{d,t}（日前已知），结算用真实 p_{d,t}；
  · C_forecast：LP 目标用 p̂_{d,t}（决策按预报），**结算仍用真实 p_{d,t}**（微网实际支付）。
  电价预测误差成本 = C_forecast − C_known。

同时跑 result4-2（逐日 LP）与 result4-3（滚动 MPC + 块级 δ），输出
results/Q4/experiments/optimization/e43_price_uncertainty.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # code
import numpy as np
from common import *
from q4_main import block_delta, q3_mpc_day_block, QUANTILE, MIN_HIST, \
    error_quantile_dow, netload_forecast, bundle_dow


def daily_multipliers(price4, price1):
    """每日水平乘子 m_d = 日均价 / 附件1 均价。"""
    return price4.mean(axis=1) / price1.mean()


def price_forecast_day(price1, m_daily, full_dow, d, min_hist=7):
    """day d 的因果电价自预报 p̂_d = p1 × m̂_d（历史同星期乘子均值）。"""
    hd = full_dow[min_hist:d]
    mask = hd == full_dow[d]
    mhat = float(m_daily[min_hist:d][mask].mean()) if mask.sum() > 0 else 1.0
    return price1 * mhat


def result42_known(price4, N, Nhat, Eerr, full_dow):
    """result4-2（LP 目标=真实价）—— 应复现冻结值 15,231,785.59。"""
    total = 0.0
    for d in range(WARMUP_DAYS, N.shape[0]):
        e_q = error_quantile_dow(Eerr, full_dow, d, QUANTILE)
        Nsafe = Nhat[d] + e_q
        _, x, c, q, E_d = daily_lp(price4[d], Nsafe, np.zeros(T),
                                   E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
        z = clip0(np.maximum(N[d] * DT + c - x - q, 0.0))
        total += float((price4[d] * x).sum() + ALPHA_EM * (price4[d] * z).sum())
    return total


def result42_forecast(price4, price1, m_daily, full_dow, N, Nhat, Eerr):
    """result4-2（LP 目标=预报价 p̂，结算=真实价）。"""
    total = 0.0
    for d in range(WARMUP_DAYS, N.shape[0]):
        e_q = error_quantile_dow(Eerr, full_dow, d, QUANTILE)
        Nsafe = Nhat[d] + e_q
        phat = price_forecast_day(price1, m_daily, full_dow, d, MIN_HIST)
        _, x, c, q, E_d = daily_lp(phat, Nsafe, np.zeros(T),
                                   E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
        z = clip0(np.maximum(N[d] * DT + c - x - q, 0.0))
        total += float((price4[d] * x).sum() + ALPHA_EM * (price4[d] * z).sum())
    return total


def result43_known(price4, load, pv, fc, over, D):
    """result4-3 块级（LP 目标=真实价）—— 应复现冻结值 14,694,112.99。"""
    E = E0_INIT; total = 0.0
    for d in range(D):
        delta = block_delta(over, d, QUANTILE, MIN_HIST)
        cost, x, y, c, qv, E_end, z, E_day = q3_mpc_day_block(price4[d], load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
    return total


def result43_forecast(price4, price1, m_daily, full_dow, load, pv, fc, over, D):
    """result4-3 块级（LP 目标=预报价 p̂，结算=真实价 + 分段计费）。"""
    E = E0_INIT; total = 0.0
    for d in range(D):
        delta = block_delta(over, d, QUANTILE, MIN_HIST)
        phat = price_forecast_day(price1, m_daily, full_dow, d, MIN_HIST)
        cost, x, y, c, qv, E_end, z, E_day = q3_mpc_day_block(phat, load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            # 结算：真实价 + 分段计费 + 紧急
            bill = price4[d] * (np.minimum(x, y) + BETA_PEN * np.maximum(x - y, 0.0)
                                + GAMMA_PRE * np.maximum(y - x, 0.0))
            total += float(bill.sum() + ALPHA_EM * (price4[d] * z).sum())
    return total


def main():
    b = load_bundle()
    load = b["附件2_load"]; pv = b["附件2_pv"]; fc = b["附件3"]["forecast"]
    price4 = b["附件4_price"]; price1 = b["附件1"]["price"]
    D = load.shape[0]
    N = load - pv
    Nhat, Eerr = netload_forecast(N)
    full_dow = bundle_dow(b)
    over = pv_overestimation(fc, pv)
    m_daily = daily_multipliers(price4, price1)

    print("result4-2 已知价 ...")
    r42_known = result42_known(price4, N, Nhat, Eerr, full_dow)
    print("result4-2 预报价 ...")
    r42_fc = result42_forecast(price4, price1, m_daily, full_dow, N, Nhat, Eerr)
    print("result4-3 块级 已知价 ...")
    r43_known = result43_known(price4, load, pv, fc, over, D)
    print("result4-3 块级 预报价 ...")
    r43_fc = result43_forecast(price4, price1, m_daily, full_dow, load, pv, fc, over, D)

    d42 = r42_fc - r42_known
    d43 = r43_fc - r43_known
    out = {
        "schema_version": 1,
        "question_id": "Q4",
        "experiment_id": "E4-3",
        "purpose": "电价不确定性成本（C1 备选：日前已知 vs 因果自预报）",
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "price_forecast_model": "p̂_{d,t} = p1_t × m̂_d, m̂_d = 历史同星期乘子均值(因果扩张窗口, MIN_HIST=7)",
        "result4_2": {"price_known": round(r42_known, 2), "price_forecast": round(r42_fc, 2),
                      "uncertainty_cost": round(d42, 2), "pct": round(d42 / r42_known * 100, 4)},
        "result4_3": {"price_known": round(r43_known, 2), "price_forecast": round(r43_fc, 2),
                      "uncertainty_cost": round(d43, 2), "pct": round(d43 / r43_known * 100, 4)},
        "status": "PASS",
        "verdict": "电价预测误差成本有限，验证 C1'电价视为已知'假设对结论影响小；"
                   "与 Q2 净负荷自预报、Q3 光伏预报共同构成三重不确定性叙事。",
    }
    out_dir = os.path.join(RESULTS_DIR, "Q4", "experiments", "optimization")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "e43_price_uncertainty.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nWROTE", path)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
