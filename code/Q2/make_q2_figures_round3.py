# -*- coding: utf-8 -*-
"""Q2 round3 论文图生成 (math-figure-generator)。

生成 4 图（柔和高级感配色，多图表形式）:
  fig_q2_1 风险分位敏感性 (面积图+折线)
  fig_q2_2 基线对比 (横向棒棒糖图)
  fig_q2_3 典型日调度策略 3.20 (面积图+柱状)
  fig_q2_4 月度费用构成 (堆叠柱状)

输出目录: paper/figures/ (300 dpi PNG)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common
from common import *

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 110

ROOT = common.ROOT
FIG_DIR = os.path.join(ROOT, 'paper', 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

W = np.array([0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05])

# ---- 柔和高级感配色（避免默认红蓝黄绿） ----
PALETTE = {
    'slate':   '#40566B',   # 石板蓝灰
    'steel':   '#66809A',   # 雾钢蓝
    'sky':     '#A3C0D3',   # 灰天蓝
    'mist':    '#D8E1E8',   # 雾白蓝
    'sage':    '#8CA69A',   # 鼠尾草绿
    'sage_d':  '#5C7569',   # 深鼠尾草
    'taupe':   '#B3A08C',   # 灰褐
    'rose':    '#C79C9D',   # 干枯玫瑰
    'rose_d':  '#97696B',   # 深玫瑰
    'gray':    '#8E979E',   # 中灰
    'ink':     '#3D454C',   # 墨灰
}


def make_forecast(N, w):
    K = len(w)
    w = np.array(w, dtype=float); w = w / w.sum()
    D = N.shape[0]
    Nhat = np.zeros_like(N)
    for d in range(K, D):
        for k in range(K):
            Nhat[d] += w[k] * N[d - 1 - k]
    return Nhat, N - Nhat


def run_full_report(price, N, Nhat, Eerr, quantile=80.0):
    R = REPORT_DAYS
    Xr = np.zeros((R, T)); Cr = np.zeros((R, T)); Qr = np.zeros((R, T)); Zr = np.zeros((R, T))
    plan_day = np.zeros(R); emg_day = np.zeros(R)
    for i, d in enumerate(range(WARMUP_DAYS, N.shape[0])):
        e_q = np.percentile(Eerr[7:d], quantile, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e_q
        _, x, c, q, Est = daily_lp(price, Nsafe, np.zeros(T), E0=E0_INIT,
                                   terminal_eq=True, E_term=E0_INIT)
        z = clip0(N[d] * DT + c - x - q)
        Xr[i] = x; Cr[i] = c; Qr[i] = q; Zr[i] = z
        plan_day[i] = float((price * x).sum())
        emg_day[i] = float(ALPHA_EM * (price * z).sum())
    return Xr, Cr, Qr, Zr, plan_day, emg_day


def main():
    b = load_bundle()
    price = b['附件1']['price']
    load = b['附件2_load']
    pv = b['附件2_pv']
    N = load - pv
    dates = report_dates(b)
    Nhat, Eerr = make_forecast(N, W)

    Xr, Cr, Qr, Zr, plan_day, emg_day = run_full_report(price, N, Nhat, Eerr, 80.0)

    # ---- fig 1: 风险分位敏感性（面积图 + 折线） ----
    qs = [0, 30, 50, 70, 80, 90, 95, 99]
    totals = [57567252.07, 26403078.64, 20105495.72, 18223007.92,
              17741097.14, 17793134.79, 18228658.05, 19503771.29]
    shares = [92.76, 56.24, 32.09, 18.10, 11.28, 4.75, 2.31, 0.69]
    fig, ax1 = plt.subplots(figsize=(6.4, 4.2))
    ax1.fill_between(qs, totals, color=PALETTE['mist'], alpha=0.7, linewidth=0)
    ax1.plot(qs, totals, color=PALETTE['slate'], lw=2, marker='o', ms=4.5,
             markerfacecolor=PALETTE['slate'], label='报告期总费用（左轴）')
    ax1.scatter([80], [17741097.14], s=120, color=PALETTE['rose_d'], zorder=5,
                marker='*', label='最优 q*=80')
    ax1.axvline(80, color=PALETTE['rose_d'], ls=':', lw=1.4, alpha=0.8)
    ax1.set_xlabel('风险分位 q（%）'); ax1.set_ylabel('总费用（元）', color=PALETTE['slate'])
    ax1.tick_params(axis='y', labelcolor=PALETTE['slate'])
    ax2 = ax1.twinx()
    ax2.plot(qs, shares, color=PALETTE['taupe'], lw=1.5, ls='--', marker='s', ms=4,
             label='紧急购电费占比（右轴）')
    ax2.set_ylabel('紧急购电费占比（%）', color=PALETTE['taupe'])
    ax2.tick_params(axis='y', labelcolor=PALETTE['taupe'])
    ax1.legend(loc='upper center', fontsize=8, frameon=False)
    ax2.legend(loc='center right', fontsize=8, frameon=False)
    ax1.grid(alpha=0.25, color=PALETTE['gray'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_1_quantile_sensitivity.png'), dpi=300)
    plt.close(fig)

    # ---- fig 2: 基线对比（横向棒棒糖图） ----
    methods = ['B2_ref\n完美预见', 'M2\n主模型', 'R2\n规则套利', 'B2\n无储能']
    vals = [16407319.63, 17741097.14, 19161505.44, 21337033.56]
    dots = [PALETTE['sky'], PALETTE['slate'], PALETTE['taupe'], PALETTE['gray']]
    ypos = np.arange(len(methods))[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for y, v, c in zip(ypos, vals, dots):
        ax.hlines(y, 0, v, color=c, lw=2.2, alpha=0.9)
        ax.scatter([v], [y], s=110, color=c, zorder=5, edgecolor='white', linewidth=1.2)
        ax.text(v + 250000, y, f'{v/1e6:.2f} M', va='center', fontsize=9, color=PALETTE['ink'])
    ax.set_yticks(ypos); ax.set_yticklabels(methods, fontsize=9)
    ax.set_xlabel('报告期总购电费（元）')
    ax.set_xlim(0, 23500000)
    ax.grid(axis='x', alpha=0.25, color=PALETTE['gray'])
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_2_baseline_comparison.png'), dpi=300)
    plt.close(fig)

    # ---- fig 3: 典型日 2025-03-20 调度策略（面积图 + 柱状） ----
    d_star = 79          # 2025-03-20（第 79 天）
    i_star = d_star - WARMUP_DAYS
    tt = np.arange(T)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True)
    # 上：负载/光伏（面积 + 折线）
    ax1.fill_between(tt, pv[d_star], color=PALETTE['sage'], alpha=0.55, linewidth=0, label='光伏 G')
    ax1.plot(tt, load[d_star], color=PALETTE['rose_d'], lw=1.6, label='负载 L')
    ax1.plot(tt, N[d_star], color=PALETTE['gray'], lw=1.1, ls=':', label='净负荷 N=L−G')
    ax1.set_ylabel('功率（kW）'); ax1.legend(loc='upper right', fontsize=8, frameon=False)
    ax1.grid(alpha=0.25, color=PALETTE['gray'])
    # 下：购电/充放电（柱状 + 折线）
    ax2.bar(tt, Cr[i_star]/DT, color=PALETTE['sage_d'], alpha=0.8, width=1.0, label='充电 c/Δt')
    ax2.bar(tt, -Qr[i_star]/DT, color=PALETTE['rose'], alpha=0.8, width=1.0, label='放电 −q/Δt')
    ax2.plot(tt, Xr[i_star]/DT, color=PALETTE['slate'], lw=1.4, label='计划购电 x/Δt')
    ax2.set_ylabel('调度功率（kW）'); ax2.set_xlabel('日内区间 t（10 分钟）')
    ax2.legend(loc='lower left', fontsize=8, frameon=False)
    ax2.grid(alpha=0.25, color=PALETTE['gray'])
    fig.suptitle('典型日调度策略（2025-03-20）', fontsize=11, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_3_representative_day.png'), dpi=300)
    plt.close(fig)

    # ---- fig 4: 月度费用构成（堆叠柱状） ----
    months = [d.month for d in dates]
    month_ids = sorted(set(months))
    plan_m = [float(plan_day[np.array([m == mm for mm in months])].sum()) for m in month_ids]
    emg_m = [float(emg_day[np.array([m == mm for mm in months])].sum()) for m in month_ids]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xpos = np.arange(len(month_ids))
    ax.bar(xpos, plan_m, color=PALETTE['steel'], label='计划购电费')
    ax.bar(xpos, emg_m, bottom=plan_m, color=PALETTE['rose_d'], label='紧急购电费')
    ax.set_xticks(xpos); ax.set_xticklabels([f'{m}月' for m in month_ids])
    ax.set_ylabel('购电费（元）'); ax.set_xlabel('月份')
    ax.legend(fontsize=9, frameon=False); ax.grid(axis='y', alpha=0.25, color=PALETTE['gray'])
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_4_monthly_cost.png'), dpi=300)
    plt.close(fig)

    print('figures written to', FIG_DIR)
    for f in ['fig_q2_1_quantile_sensitivity.png', 'fig_q2_2_baseline_comparison.png',
              'fig_q2_3_representative_day.png', 'fig_q2_4_monthly_cost.png']:
        p = os.path.join(FIG_DIR, f)
        print(' ', p, os.path.getsize(p), 'bytes')


if __name__ == '__main__':
    main()
