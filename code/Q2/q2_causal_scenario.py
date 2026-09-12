# -*- coding: utf-8 -*-
"""Q2 因果场景 LP 优化。

严格遵守 Q2 信息集：第 d 天 0:00 只使用 d 日之前的附件2历史数据；
不使用完美预见、附件3、日内更新或全年联合规划。每天只求解一个带场景
紧急购电成本的 LP，实际执行后再用当日真实数据结算。
"""
import json, os, sys
from datetime import datetime
import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

Q_LEVELS = np.array([10., 30., 50., 70., 90.])
Q_PROB = np.array([.10, .20, .40, .20, .10])


def make_forecast(N, d, mode):
    """因果预测：只读取 d 之前的完整日历史。"""
    if mode == 'weekday4_scaled':
        if d < 28:
            return N[d-7:d].mean(axis=0)
        idx = [d-7, d-14, d-21, d-28]
        w = np.array([.4, .3, .2, .1])
        base = sum(w[i] * N[idx[i]] for i in range(4))
        recent = np.mean(np.sum(N[d-7:d], axis=1))
        reference = np.mean(np.sum(N[d-28:d], axis=1))
        scale = np.clip(recent / reference, .85, 1.15) if abs(reference) > 1e-9 else 1.0
        return base * scale
    if mode.startswith('blend'):
        if d < 28:
            return N[d-7:d].mean(axis=0)
        a = float(mode.replace('blend','')) / 100.0
        wd = make_forecast(N, d, 'weekday4')
        recent = make_forecast(N, d, 'uniform7')
        return a * wd + (1-a) * recent
    if mode == 'weekday4':
        idx = [d-7, d-14, d-21, d-28]
        w = np.array([.4, .3, .2, .1])
        return sum(w[i] * N[idx[i]] for i in range(4))
    if mode == 'uniform7':
        return N[d-7:d].mean(axis=0)
    w = np.array([.3, .2, .15, .12, .1, .08, .05])
    return sum(w[k] * N[d-1-k] for k in range(7))


def scenario_lp(price, scenarios, E0=E0_INIT, rho=0.0, beta=0.9):
    """场景共享 x/c/q/E，场景独立 z；目标含期望紧急费用和可选 CVaR。"""
    S, Tn = scenarios.shape
    n = 3*Tn + (Tn+1) + S*Tn + 1 + S
    ix = lambda t: t
    ic = lambda t: Tn+t
    iq = lambda t: 2*Tn+t
    iE = lambda t: 3*Tn+t
    iz = lambda s,t: 4*Tn+1+s*Tn+t
    ieta = 4*Tn+1+S*Tn
    ixi = lambda s: ieta+1+s
    obj = np.zeros(n); obj[:Tn] = price
    for s in range(S):
        obj[4*Tn+1+s*Tn:4*Tn+1+(s+1)*Tn] = Q_PROB[s]*ALPHA_EM*price
    obj[ieta] = rho
    obj[ieta+1:] = rho*Q_PROB/(1-beta)
    Aub=[]; bub=[]
    for s in range(S):
        for t in range(Tn):
            row=np.zeros(n); row[ix(t)]=-1; row[iq(t)]=-1; row[ic(t)]=1; row[iz(s,t)]=-1
            Aub.append(row); bub.append(-scenarios[s,t]*DT)
    if rho > 0:
        for s in range(S):
            row=np.zeros(n); row[:Tn]=price
            row[4*Tn+1+s*Tn:4*Tn+1+(s+1)*Tn]=ALPHA_EM*price
            row[ieta]=-1; row[ixi(s)]=-1
            Aub.append(row); bub.append(0.)
    Aeq=[]; beq=[]
    for t in range(Tn):
        row=np.zeros(n); row[iE(t+1)]=1; row[iE(t)]=-1; row[ic(t)]=-ETA_C; row[iq(t)]=1/ETA_D
        Aeq.append(row); beq.append(0.)
    row=np.zeros(n); row[iE(0)]=1; Aeq.append(row); beq.append(E0)
    row=np.zeros(n); row[iE(Tn)]=1; Aeq.append(row); beq.append(E0_INIT)
    bounds=[(0,None)]*(3*Tn)+[(EMIN,EMAX)]*(Tn+1)+[(0,None)]*(S*Tn)+[(None,None)]+[(0,None)]*S
    res=linprog(obj,A_ub=np.asarray(Aub),b_ub=np.asarray(bub),A_eq=np.asarray(Aeq),b_eq=np.asarray(beq),bounds=bounds,method='highs')
    if not res.success: raise RuntimeError(res.message)
    v=res.x
    return v[:Tn],v[Tn:2*Tn],v[2*Tn:3*Tn],v[3*Tn:4*Tn+1]


def run(bundle, predictor='uniform7', rho=0.0):
    price=bundle['附件1']['price']; load=bundle['附件2_load']; pv=bundle['附件2_pv']; N=load-pv
    dates=[datetime.strptime(s,'%Y-%m-%d %H:%M:%S') for s in bundle['dates']]
    plan=emg=emg_kwh=curt_kwh=0.; emg_int=curt_int=0; emin=EMAX; emax=EMIN
    for d in range(WARMUP_DAYS,len(load)):
        base=make_forecast(N,d,predictor)
        hist=np.arange(7,d)
        if predictor in ('weekday4','weekday4_scaled') or predictor.startswith('blend'):
            hist=hist[[dates[i].weekday()==dates[d].weekday() for i in hist]]
            hist=hist[hist >= 28]
        if len(hist)<5: hist=np.arange(7,d)
        hist=hist[hist >= (28 if predictor in ('weekday4','weekday4_scaled') or predictor.startswith('blend') else 7)]
        err=N[hist]-np.array([make_forecast(N,i,predictor) for i in hist])
        qerr=np.percentile(err,Q_LEVELS,axis=0)
        scenarios=base[None,:]+qerr
        x,c,qv,E=scenario_lp(price,scenarios,rho=rho)
        z=clip0(N[d]*DT+c-x-qv)
        curt=clip0(pv[d]*DT+x+qv-load[d]*DT-c)
        plan+=(price*x).sum(); emg+=ALPHA_EM*(price*z).sum(); emg_kwh+=z.sum(); curt_kwh+=curt.sum()
        emg_int+=int((z>1e-8).sum()); curt_int+=int((curt>1e-8).sum())
        emin=min(emin,float(E.min())); emax=max(emax,float(E.max()))
    total=plan+emg; pv_energy=float(pv[WARMUP_DAYS:].sum()*DT)
    return {'total':round(total,2),'plan':round(plan,2),'emergency':round(emg,2),'emergency_kwh':round(emg_kwh,2),
            'emergency_intervals':emg_int,'curtailment_kwh':round(curt_kwh,2),'curtailment_intervals':curt_int,
            'curtailment_rate':round(curt_kwh/pv_energy,6),'emg_share':round(emg/total,6),
            'E_min':round(emin,2),'E_max':round(emax,2),'predictor':predictor,'rho':rho}


def main():
    b=load_bundle(); out={'meta':{'question_id':'Q2','information_set':'history only, d日0:00','model':'causal daily scenario LP','seed':SEED}}
    out['recommended'] = run(b, 'blend25', 0.2)
    out['experiments']={}
    for predictor in ['weighted7','uniform7','weekday4','weekday4_scaled']:
        for rho in [0.0,0.1,0.3]:
            out['experiments'][f'{predictor}_rho{rho}']=run(b,predictor,rho)
    for rho in [0.35,0.4,0.5,0.6,0.8,1.0]:
        out['experiments'][f'weekday4_rho{rho}']=run(b,'weekday4',rho)
    out_dir=os.path.join(RESULTS_DIR,'Q2','experiments','optimization'); os.makedirs(out_dir,exist_ok=True)
    with open(os.path.join(out_dir,'causal_scenario_summary.json'),'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2)
    for k,v in out['experiments'].items(): print(k,v)


if __name__=='__main__': main()
