# -*- coding: utf-8 -*-
"""Q4 优化实验（E4-4）：result4-3 块级修正分位重扫（波动电价）。

目的：验证波动电价下 Q3 的 issue×执行块 因果分位修正的最优分位是否漂移。
仅重算 result4-3（块级 δ，q ∈ {80,82,85,88,90,92,95}），写
results/Q4/experiments/optimization/e44_quantile_sweep.json。

依赖：复用 q4_main 的 block_delta / q3_mpc_day_block（与主模型完全同构）。
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # code/Q4
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # code
import numpy as np
from common import *
from q4_main import block_delta, q3_mpc_day_block, MIN_HIST

Q_TEST = [80.0, 82.0, 85.0, 88.0, 90.0, 92.0, 95.0]


def run_result43_q(price_d, load, pv, fc, over, D, q):
    """result4-3 块级 δ，分位 q，全年滚动；返回分项费用与紧急购电电量。"""
    total = plan = pen = emg = emg_kwh = 0.0
    E = E0_INIT
    for d in range(D):
        delta = block_delta(over, d, q, MIN_HIST)
        cost, x, y, c, qv, E_end, z, E_day = q3_mpc_day_block(price_d[d], load[d], pv[d], fc, d, E, delta)
        E = E_end
        if d >= WARMUP_DAYS:
            total += cost
            plan += float((price_d[d] * np.minimum(x, y)).sum())
            pen += float((price_d[d] * (BETA_PEN * np.maximum(x - y, 0.0)
                                        + GAMMA_PRE * np.maximum(y - x, 0.0))).sum())
            emg += float((ALPHA_EM * price_d[d] * z).sum())
            emg_kwh += float(z.sum())
    return {'total': round(total, 2), 'plan': round(plan, 2), 'penalty': round(pen, 2),
            'emergency': round(emg, 2), 'emergency_kwh': round(emg_kwh, 2)}


def main():
    b = load_bundle()
    price_d = b['附件4_price']
    load = b['附件2_load']; pv = b['附件2_pv']; fc = b['附件3']['forecast']
    D = load.shape[0]
    over = pv_overestimation(fc, pv)

    sweep = {f'{int(q)}': run_result43_q(price_d, load, pv, fc, over, D, q) for q in Q_TEST}
    argmin_q = min(Q_TEST, key=lambda q: sweep[f'{int(q)}']['total'])
    q80_total = sweep['80']['total']
    delta_vs_q80 = round(q80_total - sweep[f'{int(argmin_q)}']['total'], 2)

    out = {
        'schema_version': 1,
        'question_id': 'Q4',
        'experiment_id': 'E4-4',
        'purpose': 'result4-3 块级修正分位重扫（波动电价），确认 q=80 是否仍近优',
        'created_at': datetime.now().isoformat(),
        'seed': SEED,
        'q_sweep': sweep,
        'argmin_q': int(argmin_q),
        'q80_total': q80_total,
        'q80_vs_argmin_delta': delta_vs_q80,
        'q80_delta_pct': round(delta_vs_q80 / q80_total * 100, 4),
        'status': 'PASS' if delta_vs_q80 / q80_total < 0.01 else 'REVIEW',
        'note': 'q=80 相对 argmin 代价 <1% 则 q=80 仍近优（设计稳健）；Q3 恒定电价下 argmin=q85（14,020,104.48）'
    }
    out_dir = os.path.join(RESULTS_DIR, 'Q4', 'experiments', 'optimization')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'e44_quantile_sweep.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
