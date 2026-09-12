# -*- coding: utf-8 -*-
"""Q3 因果风险校准优化试验。

在原 M3 框架上只替换光伏风险修正：由每个 issue 一个标量 P80，改为
issue × 执行区间的历史分位数修正。每天仍按 0/6/12/18 四个时刻滚动，
计划/调整分段计费、紧急购电和日末 SOC 闭合均不变。
"""
import json, os, sys
from datetime import datetime
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

MIN_HIST = 7
Q_TEST = [82.0, 85.0, 88.0, 90.0, 92.0, 95.0]


def block_over(forecast, pv):
    """返回 (D,4,36)，每个 issue 的实际执行块预报高估误差。"""
    D = pv.shape[0]
    out = np.zeros((D, 4, 36))
    for s in range(4):
        fc_s = forecast[s::4]
        for j in range(36):
            out[:, s, j] = fc_s[:, j // 6] - pv[:, 36*s+j]
    return out


def block_delta(over, d, q):
    hist = over[MIN_HIST:d]
    if len(hist) == 0:
        return np.zeros((4, 36))
    qv = np.asarray(q if np.ndim(q) else [q] * 4, dtype=float)
    return np.stack([np.percentile(hist[:, s, :], qv[s], axis=0) for s in range(4)])


def corrected_forecast(fc, d, s, delta):
    g = forecast_intervals(fc, d, s).copy()
    start = 36*s
    # 只修正本阶段实际会执行的 6 小时块。
    g[start:start+36] = clip0(g[start:start+36] - delta[s])
    return g


def mpc_day(price, load_d, pv_actual, fc, d, E_carry, delta):
    g0 = corrected_forecast(fc, d, 0, delta)
    _, x, c0, q0, E0t = daily_lp(price, load_d, g0, E0=E_carry, terminal_eq=True, E_term=E0_INIT)
    g1 = corrected_forecast(fc, d, 1, delta); sl = 36
    _, y1, c1, q1, E1t = stage_lp(price[sl:], load_d[sl:], g1[sl:], x[sl:], E0t[sl], terminal_eq=True, E_term=E0_INIT)
    g2 = corrected_forecast(fc, d, 2, delta); sl = 72
    _, y2, c2, q2, E2t = stage_lp(price[sl:], load_d[sl:], g2[sl:], x[sl:], E1t[sl-36], terminal_eq=True, E_term=E0_INIT)
    g3 = corrected_forecast(fc, d, 3, delta); sl = 108
    _, y3, c3, q3, E3t = stage_lp(price[sl:], load_d[sl:], g3[sl:], x[sl:], E2t[sl-72], terminal_eq=True, E_term=E0_INIT)
    y = np.concatenate([x[:36], y1[:36], y2[:36], y3[:36]])
    c = np.concatenate([c0[:36], c1[:36], c2[:36], c3[:36]])
    qv = np.concatenate([q0[:36], q1[:36], q2[:36], q3[:36]])
    z = clip0(load_d*DT+c-y-pv_actual*DT-qv)
    bill = price*(np.minimum(x,y)+BETA_PEN*np.maximum(x-y,0)+GAMMA_PRE*np.maximum(y-x,0))
    return float(bill.sum()+ALPHA_EM*(price*z).sum()), x, y, c, qv, E3t[-1], z


def run(b, quantile):
    price=b['附件1']['price']; load=b['附件2_load']; pv=b['附件2_pv']; fc=b['附件3']['forecast']; D=len(load)
    over=block_over(fc,pv); total=plan=penalty=emergency=emg_kwh=curt=0.; E=E0_INIT; emg_int=0; emin=EMAX; emax=EMIN
    for d in range(D):
        delta=block_delta(over,d,quantile)
        cost,x,y,c,qv,E,z=mpc_day(price,load[d],pv[d],fc,d,E,delta)
        if d>=WARMUP_DAYS:
            total+=cost; pr=np.tile(price,(1,1))[0]
            plan+=float((pr*np.minimum(x,y)).sum())
            penalty+=float((pr*(BETA_PEN*np.maximum(x-y,0)+GAMMA_PRE*np.maximum(y-x,0))).sum())
            emergency+=float((ALPHA_EM*pr*z).sum()); emg_kwh+=float(z.sum()); emg_int+=int((z>1e-8).sum())
            curt+=float(clip0(y+pv[d]*DT+qv-load[d]*DT-c).sum())
        emin=min(emin,float(E0_INIT)); emax=max(emax,float(E0_INIT)); E=E0_INIT
    pv_energy=float(pv[WARMUP_DAYS:].sum()*DT)
    return {'total':round(total,2),'plan':round(plan,2),'penalty':round(penalty,2),'emergency':round(emergency,2),
            'emergency_kwh':round(emg_kwh,2),'emergency_intervals':emg_int,'curtailment_kwh':round(curt,2),
            'curtailment_rate':round(curt/pv_energy,6),'E_min':round(emin,2),'E_max':round(emax,2),'q':quantile}


def main():
    b=load_bundle(); out={'meta':{'question_id':'Q3','model':'M3 + causal issue-by-execution-block risk correction','information_set':'附件3当前已发布预报 + 历史附件2误差','seed':SEED}}
    out['block_quantile']= {str(q):run(b,q) for q in Q_TEST}
    out_dir=os.path.join(RESULTS_DIR,'Q3','experiments','optimization'); os.makedirs(out_dir,exist_ok=True)
    with open(os.path.join(out_dir,'block_risk_summary.json'),'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
