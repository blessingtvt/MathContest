# -*- coding: utf-8 -*-
"""Q2 优化实验：弃光惩罚 + 动态风险修正。

保持原有逐日滚动 LP、净负荷自预报、紧急购电和日末循环框架不变。
方案 A 在日内 LP 中加入弃光松弛变量 r；方案 B 按月份/季节计算因果误差分位。
所有方案均用实际附件2数据进行事后结算，优化目标之外的紧急购电与实际弃光
按原 Q2 定义重新统计。
"""
import json, os, sys
from datetime import datetime
import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

W = np.array([0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05])
LAMBDAS = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0]
QUANTILES = [70.0, 80.0, 90.0]


def forecast(a):
    out = np.zeros_like(a)
    for d in range(len(W), len(a)):
        out[d] = sum(W[k] * a[d - 1 - k] for k in range(len(W)))
    return out, a - out


def daily_lp_curtail(price, load_f, pv_f, E0, lam):
    """带弃光变量 r 的单日 LP；r 是计划侧预测弃光量(kWh)。"""
    n = 4 * T + T + 1
    ix = lambda t: t
    ic = lambda t: T + t
    iq = lambda t: 2 * T + t
    ir = lambda t: 3 * T + t
    iE = lambda t: 4 * T + t
    obj = np.zeros(n); obj[:T] = price; obj[3*T:4*T] = lam
    Aub, bub = [], []
    for t in range(T):
        row = np.zeros(n); row[ix(t)] = -1; row[iq(t)] = -1; row[ic(t)] = 1
        Aub.append(row); bub.append(pv_f[t]*DT - load_f[t]*DT)
        row = np.zeros(n); row[ix(t)] = 1; row[iq(t)] = 1; row[ic(t)] = -1; row[ir(t)] = -1
        # r >= pv_f*DT + x + q - load_f*DT - c
        Aub.append(row); bub.append(load_f[t]*DT - pv_f[t]*DT)
    for t in range(T):
        row = np.zeros(n); row[ic(t)] = 1; Aub.append(row); bub.append(PMAX_E)
        row = np.zeros(n); row[iq(t)] = 1; Aub.append(row); bub.append(PMAX_E)
    Aeq, beq = [], []
    for t in range(T):
        row = np.zeros(n); row[iE(t+1)] = 1; row[iE(t)] = -1
        row[ic(t)] = -ETA_C; row[iq(t)] = 1/ETA_D
        Aeq.append(row); beq.append(0.0)
    row = np.zeros(n); row[iE(0)] = 1; Aeq.append(row); beq.append(E0)
    row = np.zeros(n); row[iE(T)] = 1; Aeq.append(row); beq.append(E0_INIT)
    bounds = [(0, None)] * (4*T) + [(EMIN, EMAX)] * (T+1)
    res = linprog(obj, A_ub=np.asarray(Aub), b_ub=np.asarray(bub),
                  A_eq=np.asarray(Aeq), b_eq=np.asarray(beq), bounds=bounds,
                  method='highs')
    if not res.success:
        raise RuntimeError(res.message)
    v = res.x
    return (clip0(v[:T]), clip0(v[T:2*T]), clip0(v[2*T:3*T]),
            clip0(v[3*T:4*T]), v[4*T:])


def risk_vector(err, dates, d, q, mode='fixed'):
    hist = np.arange(7, d)
    if mode == 'month':
        hist = hist[[dates[i].month == dates[d].month for i in hist]]
    elif mode == 'season':
        season = lambda m: (m % 12) // 3
        hist = hist[[season(dates[i].month) == season(dates[d].month) for i in hist]]
    if len(hist) < 3:
        hist = np.arange(7, d)
    return np.percentile(err[hist], q, axis=0) if len(hist) else np.zeros(T)


def simulate(price, load, pv, dates, lam=0.0, q=80.0, risk_mode='fixed'):
    N = load - pv
    Nhat, err = forecast(N)
    pvhat, _ = forecast(pv)
    plan = emergency = emg_kwh = curt_kwh = 0.0
    emg_int = curt_int = 0
    e_min, e_max = EMAX, EMIN
    for d in range(WARMUP_DAYS, len(load)):
        safe = Nhat[d] + risk_vector(err, dates, d, q, risk_mode)
        # 预测负荷 = 预测净负荷 + 预测光伏，保持与原净负荷口径等价。
        lf = safe + pvhat[d]
        x, c, qv, _, E = daily_lp_curtail(price, lf, pvhat[d], E0_INIT, lam)
        z = clip0(N[d] * DT + c - x - qv)
        curt = clip0(pv[d] * DT + x + qv - load[d] * DT - c)
        plan += float((price*x).sum()); emergency += float(ALPHA_EM*(price*z).sum())
        emg_kwh += float(z.sum()); curt_kwh += float(curt.sum())
        emg_int += int((z > 1e-8).sum()); curt_int += int((curt > 1e-8).sum())
        e_min = min(e_min, float(E.min())); e_max = max(e_max, float(E.max()))
    total = plan + emergency
    return dict(total=round(total,2), plan=round(plan,2), emergency=round(emergency,2),
                emergency_kwh=round(emg_kwh,2), emergency_intervals=emg_int,
                curtailment_kwh=round(curt_kwh,2), curtailment_intervals=curt_int,
                curtailment_rate=round(curt_kwh / float(pv[WARMUP_DAYS:].sum()*DT), 6),
                emg_share=round(emergency/total, 6), E_min=round(e_min,2), E_max=round(e_max,2))


def main():
    b = load_bundle(); price = b['附件1']['price']; load = b['附件2_load']; pv = b['附件2_pv']
    dates = [datetime.strptime(s, '%Y-%m-%d %H:%M:%S') for s in b['dates']]
    out = {'meta': {'question_id':'Q2', 'model':'M2 + curtailment penalty / dynamic risk',
                    'report_period':'2025-02-01 ~ 2025-12-31', 'seed':SEED}}
    out['curtailment_penalty'] = {str(lam): simulate(price, load, pv, dates, lam=lam, q=80, risk_mode='fixed')
                                  for lam in LAMBDAS}
    out['dynamic_risk'] = {
        'fixed_q70': simulate(price, load, pv, dates, q=70, risk_mode='fixed'),
        'fixed_q80': simulate(price, load, pv, dates, q=80, risk_mode='fixed'),
        'fixed_q90': simulate(price, load, pv, dates, q=90, risk_mode='fixed'),
        'monthly_q80': simulate(price, load, pv, dates, q=80, risk_mode='month'),
        'seasonal_q80': simulate(price, load, pv, dates, q=80, risk_mode='season'),
    }
    out_dir = os.path.join(RESULTS_DIR, 'Q2', 'experiments', 'optimization')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'optimization_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
