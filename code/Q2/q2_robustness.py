# -*- coding: utf-8 -*-
"""Q2 round3 稳健性/敏感性实验 (robustness-checker)。

针对 round3 模型 M2 (逐日滚动 LP + 附件2历史自预报 + 80分位风险修正) 的
load-bearing 假设做定向检验, 不堆砌无关测试:

  R1  风险分位 q 敏感性 (报童临界比 0.8 是否为最优)
  R2  预报窗口/加权 敏感性 (7天加权 vs 3/5/7/14天均匀)
  R3  充放电效率口径 HD2 (单向 η=0.9 vs 往返 √0.9)
  R4  电价线性扰动 (费用应随电价线性缩放, 无放大)
  R5  日末循环 vs 自由终态 (S_144=S_0 约束的影响)

输出: robustness/Q2/q2_robustness_summary.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import common
from common import *


def make_forecast(N, w):
    """历史自预报: K 天加权平均 (仅用当天之前数据)。返回 (Nhat, Eerr)。"""
    K = len(w)
    w = np.array(w, dtype=float)
    w = w / w.sum()
    D = N.shape[0]
    Nhat = np.zeros_like(N)
    for d in range(K, D):
        for k in range(K):
            Nhat[d] += w[k] * N[d - 1 - k]
    return Nhat, N - Nhat


def sim_report(price, N, Nhat, Eerr, quantile, daily_cycle=True):
    """逐日滚动报告期模拟。返回报告期费用与紧急购电指标。"""
    plan = emg = emg_energy = 0.0
    emg_int = 0
    E0 = E0_INIT
    for d in range(WARMUP_DAYS, N.shape[0]):
        e_q = np.percentile(Eerr[7:d], quantile, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e_q
        _, x, c, q, Est = daily_lp(price, Nsafe, np.zeros(T), E0=E0,
                                   terminal_eq=daily_cycle,
                                   E_term=(E0 if daily_cycle else None))
        z = clip0(N[d] * DT + c - x - q)
        plan += float((price * x).sum())
        emg += float(ALPHA_EM * (price * z).sum())
        emg_energy += float(z.sum())
        emg_int += int((z > 1e-8).sum())
        E0 = Est[T]
    total = plan + emg
    return dict(total=round(total, 2), plan=round(plan, 2), emg=round(emg, 2),
                emg_energy=round(emg_energy, 2), emg_intervals=emg_int,
                emg_share=round(emg / total, 6))


def main():
    b = load_bundle()
    price = b['附件1']['price']
    load = b['附件2_load']
    pv = b['附件2_pv']
    D = load.shape[0]
    N = load - pv

    W = np.array([0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05])
    Nhat_base, Eerr_base = make_forecast(N, W)

    out = {}

    # ---- R1 风险分位敏感性 ----
    qs = [0, 30, 50, 70, 80, 90, 95, 99]
    r1 = {str(q): sim_report(price, N, Nhat_base, Eerr_base, q, True) for q in qs}
    totals = {q: r1[str(q)]['total'] for q in qs}
    q_star = min(totals, key=totals.get)
    out['R1_quantile'] = {
        'sweep': r1,
        'argmin_total_quantile': q_star,
        'argmin_total': totals[q_star],
        'baseline_q80_total': totals[80],
    }

    # ---- R2 预报窗口/加权敏感性 (固定 q=80) ----
    windows = [
        ('3天均匀', [1/3, 1/3, 1/3]),
        ('5天均匀', [1/5]*5),
        ('7天均匀', [1/7]*7),
        ('7天加权(基准)', list(W)),
        ('14天均匀', [1/14]*14),
    ]
    r2 = {}
    for label, w in windows:
        Nhat, Eerr = make_forecast(N, w)
        r2[label] = sim_report(price, N, Nhat, Eerr, 80, True)
    out['R2_window'] = r2

    # ---- R3 效率口径 HD2 (固定 q=80, 基准窗口) ----
    r3_base = sim_report(price, N, Nhat_base, Eerr_base, 80, True)   # 单向 η=0.9 (往返0.81)
    common.ETA_C = common.ETA_D = float(np.sqrt(0.9))                 # 往返0.9
    r3_rt = sim_report(price, N, Nhat_base, Eerr_base, 80, True)
    common.ETA_C = common.ETA_D = 0.9                                 # 还原
    out['R3_efficiency'] = {
        'eta_single_0.9_roundtrip_0.81': r3_base,
        'eta_sqrt0.9_roundtrip_0.90': r3_rt,
    }

    # ---- R4 电价线性扰动 (固定 q=80) ----
    r4 = {}
    for k in [0.90, 0.95, 1.00, 1.05, 1.10]:
        r4[f'price_x{k:.2f}'] = sim_report(price * k, N, Nhat_base, Eerr_base, 80, True)
    out['R4_price'] = r4

    # ---- R5 日末循环 vs 自由终态 (固定 q=80) ----
    out['R5_terminal'] = {
        'daily_cycle_S144_eq_S0': sim_report(price, N, Nhat_base, Eerr_base, 80, True),
        'free_terminal': sim_report(price, N, Nhat_base, Eerr_base, 80, False),
    }

    # ---- 汇总写盘 ----
    out['meta'] = {
        'question_id': 'Q2',
        'model': 'M2-daily-rolling-LP+self-forecast+risk-correction(q80)',
        'seed': SEED,
        'generated_at': datetime.now().isoformat(),
        'report_period': '2025-02-01 ~ 2025-12-31',
        'data_source': 'data_clean/cleaned_data.pkl',
    }
    out_dir = os.path.join(ROOT, 'robustness', 'Q2')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'q2_robustness_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 简明打印
    print('R1 quantile sweep (total, emg_share):')
    for q in qs:
        print(f'  q={q:>2}: total={r1[str(q)]["total"]:>14,.2f}  emg_share={r1[str(q)]["emg_share"]:>7.2%}')
    print(f'  => argmin q*={q_star}  total={totals[q_star]:,.2f}')
    print('\nR2 window (total @ q=80):')
    for label, r in r2.items():
        print(f'  {label}: {r["total"]:>14,.2f}  emg_share={r["emg_share"]:>7.2%}')
    print('\nR3 efficiency:')
    print(f'  单向0.9(往返0.81): {r3_base["total"]:,.2f}')
    print(f'  往返0.90:          {r3_rt["total"]:,.2f}')
    print('\nR4 price:')
    for k, r in r4.items():
        print(f'  {k}: {r["total"]:>14,.2f}')
    print('\nR5 terminal:')
    for k, r in out['R5_terminal'].items():
        print(f'  {k}: {r["total"]:>14,.2f}')
    print(f'\nwritten -> {out_dir}/q2_robustness_summary.json')


if __name__ == '__main__':
    main()
