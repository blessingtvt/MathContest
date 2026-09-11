# -*- coding: utf-8 -*-
"""Q2 方案对比实验: 用户提议的「逐日滚动 + 历史自预报 + 风险惩罚(分位)」模型。

关键修正: 附件3 用于 Q3/Q4, 非 Q2(见 problem_parse.md 数据清单)。Q2 的信息集 = 附件1电价 + 附件2历史。
因此 Q2 用附件2 历史自预报净负荷 N=L-P, 并用历史误差分位数做风险修正。

对比: 不同风险分位 (0=无修正) × 日末循环约束 (S_144=S_0 vs 自由终态)。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from common import *

b = load_bundle()
price = b['附件1']['price']
load = b['附件2_load']
pv = b['附件2_pv']
D = load.shape[0]
N = load - pv   # 净负荷 (kW), (365,144)

w = np.array([0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05])
assert abs(w.sum() - 1.0) < 1e-12

# 7 天加权平均预报 (只用当天之前的历史)
Nhat = np.zeros_like(N)
for d in range(7, D):
    for k in range(7):
        Nhat[d] += w[k] * N[d - 1 - k]
Eerr = N - Nhat  # 预报误差 (d>=7 有效)


def run(quantile=90.0, daily_cycle=True):
    plan_cost = emg_cost = emg_energy = 0.0
    emg_intervals = 0
    E0 = E0_INIT
    for d in range(WARMUP_DAYS, D):
        # 历史误差 90 分位 (仅用 d 之前的数据, 因果)
        e_q = np.percentile(Eerr[7:d], quantile, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e_q
        _, G, C, Q, Est = daily_lp(price, Nsafe, np.zeros(T),
                                   E0=E0, terminal_eq=daily_cycle,
                                   E_term=(E0 if daily_cycle else None))
        # 实际结算: 真实净负荷 N[d] = L-P
        short = N[d] * DT + C - G - Q
        Er = clip0(short)
        plan_cost += float((price * G).sum())
        emg_cost += float(ALPHA_EM * (price * Er).sum())
        emg_energy += float(Er.sum())
        emg_intervals += int((Er > 1e-8).sum())
        E0 = Est[T]
    total = plan_cost + emg_cost
    return dict(plan=plan_cost, emg=emg_cost, total=total,
                emg_energy=emg_energy, emg_intervals=emg_intervals,
                emg_share=emg_cost / total)


print('=== 日末循环 S_144=S_0 (用户提议) ===')
for q in [0, 50, 70, 80, 90, 95, 99]:
    r = run(quantile=q, daily_cycle=True)
    print(f'  分位={q:>2}: total={r["total"]:>14,.2f}  plan={r["plan"]:>13,.2f}  '
          f'emg={r["emg"]:>12,.2f}  emg占比={r["emg_share"]:>6.2%}  紧急区间={r["emg_intervals"]}')

print('=== 自由终态 (跨日结转, 无日末约束) ===')
for q in [0, 80, 90]:
    r = run(quantile=q, daily_cycle=False)
    print(f'  分位={q:>2}: total={r["total"]:>14,.2f}  plan={r["plan"]:>13,.2f}  '
          f'emg={r["emg"]:>12,.2f}  emg占比={r["emg_share"]:>6.2%}  紧急区间={r["emg_intervals"]}')

print()
print('对照: 旧方案(附件3日前预报+逐日滚动) total=17,400,028.28, 紧急占比=27.75%')
