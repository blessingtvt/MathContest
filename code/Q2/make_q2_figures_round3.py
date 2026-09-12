# -*- coding: utf-8 -*-
"""Q2 round3 论文图生成 (math-figure-generator)。

生成 5 图（柔和高级感配色，多图表形式）:
  fig_q2_1 风险分位敏感性 (面积图+折线)
  fig_q2_2 基线对比 (横向棒棒糖图)
  fig_q2_3 典型日调度策略 3.20 (面积图+柱状)
  fig_q2_4 月度费用构成 (堆叠柱状)
  fig_q2_5 每日紧急购电 vs 净负荷/光伏 (季节性解释)

输出目录: paper/figures/ (300 dpi PNG)
"""
import os, sys
from datetime import datetime
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
    'slate': '#3B7FBF',  # 主蓝
    'steel': '#1F4E79',  # 深海蓝
    'sky': '#6FA8DC',  # 亮天蓝
    'mist': '#DCEAF7',  # 极浅蓝填充
    'sage': '#2FA496',  # 青绿色
    'sage_d': '#1B6F64',  # 深青绿
    'taupe': '#D98E04',  # 暖橙强调
    'rose': '#E0634F',  # 珊瑚红
    'rose_d': '#A33F2C',  # 深砖红
    'gray': '#5F6A73',  # 中性灰
    'ink': '#14181C',  # 近黑文字
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


def run_full_report(price, N, Nhat, Eerr, quantile=80.0, full_dow=None):
    R = REPORT_DAYS
    Xr = np.zeros((R, T)); Cr = np.zeros((R, T)); Qr = np.zeros((R, T)); Zr = np.zeros((R, T))
    plan_day = np.zeros(R); emg_day = np.zeros(R)
    for i, d in enumerate(range(WARMUP_DAYS, N.shape[0])):
        if full_dow is not None:
            hist = Eerr[7:d]; hd = full_dow[7:d]; mask = hd == full_dow[d]
            e_q = np.percentile(hist[mask], quantile, axis=0) if mask.sum() > 0 else np.zeros(T)
        else:
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
    full_dow = np.array([datetime.strptime(s, "%Y-%m-%d %H:%M:%S").weekday()
                         for s in b['dates']])
    Nhat, Eerr = make_forecast(N, W)

    Xr, Cr, Qr, Zr, plan_day, emg_day = run_full_report(price, N, Nhat, Eerr, 80.0, full_dow)

    # ---- fig 1: 风险分位敏感性（面积图 + 折线） ----
    qs = [0, 30, 50, 70, 80, 90, 95, 99]
    totals = [25093998.32, 17575991.73, 15913613.91, 14870741.86,
              14559104.58, 14461289.17, 14624319.15, 15197625.85]
    shares = [60.16, 34.23, 24.04, 14.93, 10.65, 6.45, 4.36, 2.75]
    fig, ax1 = plt.subplots(figsize=(6.4, 4.2))
    ax1.fill_between(qs, totals, color=PALETTE['mist'], alpha=0.7, linewidth=0)
    ax1.plot(qs, totals, color=PALETTE['slate'], lw=2, marker='o', ms=4.5,
             markerfacecolor=PALETTE['slate'], label='报告期总费用（左轴）')
    ax1.scatter([90], [14461289.17], s=120, color=PALETTE['rose_d'], zorder=5,
                marker='*', label='经验最优 q*=90')
    ax1.axvline(80, color=PALETTE['slate'], ls=':', lw=1.4, alpha=0.8)
    ax1.text(81, totals[0] * 0.86, '设计 q=80（报童）\n仅高 0.67%', fontsize=8,
             color=PALETTE['slate'], ha='left')
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
    vals = [16407319.63, 14559104.58, 16572068.47, 18172127.42]
    dots = [PALETTE['sky'], PALETTE['slate'], PALETTE['taupe'], PALETTE['gray']]
    ypos = np.arange(len(methods))[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for y, v, c in zip(ypos, vals, dots):
        ax.hlines(y, 0, v, color=c, lw=2.2, alpha=0.9)
        ax.scatter([v], [y], s=110, color=c, zorder=5, edgecolor='white', linewidth=1.2)
        ax.text(v + 250000, y, f'{v/1e6:.2f} M', va='center', fontsize=9, color=PALETTE['ink'])
    ax.set_yticks(ypos); ax.set_yticklabels(methods, fontsize=9)
    ax.set_xlabel('报告期总购电费（元）')
    ax.set_xlim(0, 19500000)
    ax.grid(axis='x', alpha=0.25, color=PALETTE['gray'])
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_2_baseline_comparison.png'), dpi=300)
    plt.close(fig)

    # ---- fig 3: 典型日 2025-03-20 微网功率平衡与储能调度结果（面积图 + 柱状） ----
    d_star = 79          # 2025-03-20（第 79 天）
    i_star = d_star - WARMUP_DAYS
    tt = np.arange(T)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True)
    # 上：光伏出力 / 负荷需求 / 净负荷（面积 + 折线）
    ax1.fill_between(tt, pv[d_star], color=PALETTE['sage'], alpha=0.55, linewidth=0, label='光伏出力 G')
    ax1.plot(tt, load[d_star], color=PALETTE['rose_d'], lw=1.6, label='负荷需求 L')
    ax1.plot(tt, N[d_star], color=PALETTE['gray'], lw=1.1, ls=':', label='净负荷 N=L−G')
    ax1.set_ylabel('功率（kW）')
    ax1.set_title('（a）光伏与负荷功率', fontsize=9, color=PALETTE['ink'])
    ax1.legend(loc='upper right', fontsize=8, frameon=False)
    ax1.grid(alpha=0.25, color=PALETTE['gray'])
    ax1.tick_params(labelbottom=False)  # 横轴与下子图共享，仅下子图显示刻度
    # 下：外部购电 / 储能充放电（柱状 + 折线）
    # 注：为便于展示储能运行状态，将放电功率以负值形式表示（模型变量 q_t≥0 定义不变）。
    ax2.bar(tt, Cr[i_star]/DT, color=PALETTE['sage_d'], alpha=0.8, width=1.0, label='储能充电 $c_t$')
    ax2.bar(tt, -Qr[i_star]/DT, color=PALETTE['rose'], alpha=0.8, width=1.0, label='储能放电 $-q_t$')
    ax2.plot(tt, Xr[i_star]/DT, color=PALETTE['slate'], lw=1.4, label='计划购电 $x_t$')
    ax2.set_ylabel('调度功率（kW）')
    ax2.set_xlabel('调度时段（10 min）')
    ax2.set_title('（b）购电与储能充放电功率', fontsize=9, color=PALETTE['ink'])
    # 横轴刻度：调度时段编号 → 对应时刻（一天 144 个时段，每时段 10 min）
    ax2.set_xticks([0, 36, 72, 108, 143])
    ax2.set_xticklabels(['00:00', '06:00', '12:00', '18:00', '23:50'])
    ax2.legend(loc='lower left', fontsize=8, frameon=False)
    ax2.grid(alpha=0.25, color=PALETTE['gray'])
    ax2.text(0.02, 0.97, '注：为便于展示储能运行状态，将放电功率以负值形式表示',
             transform=ax2.transAxes, fontsize=7.5, va='top', color=PALETTE['gray'])
    fig.suptitle('典型日微网功率平衡与储能调度结果（2025-03-20）', fontsize=11, color=PALETTE['ink'])
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

    # ---- fig 5: 每日紧急购电 vs 净负荷/光伏（季节性解释） ----
    R = REPORT_DAYS
    emg_energy_day = Zr.sum(axis=1)                            # 每日紧急购电量 kWh
    netload_energy_day = (N[WARMUP_DAYS:].sum(axis=1)) * DT    # 每日净负荷电量 kWh
    solar_energy_day = (pv[WARMUP_DAYS:].sum(axis=1)) * DT     # 每日光伏电量 kWh

    def _idx(m, dd):
        for i, dt in enumerate(dates):
            if dt.month == m and dt.day == dd:
                return i
        return None
    marks = [('春分', _idx(3, 20)), ('夏至', _idx(6, 21)),
             ('秋分', _idx(9, 23)), ('冬至', _idx(12, 21))]

    x = np.arange(R)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.6, 5.8), sharex=True)
    # 上：每日紧急购电量
    ax1.bar(x, emg_energy_day, color=PALETTE['rose'], alpha=0.85, width=1.0)
    ax1.set_ylabel('紧急购电量\n(kWh/日)', fontsize=9)
    ax1.grid(alpha=0.25, color=PALETTE['gray'])
    ymax1 = float(emg_energy_day.max())
    ax1.set_ylim(0, ymax1 * 1.12)
    # 下：每日净负荷电量（面积）+ 光伏电量（折线）
    ax2.fill_between(x, netload_energy_day / 1e3, color=PALETTE['slate'], alpha=0.45,
                     linewidth=0, label='净负荷电量')
    ax2.plot(x, solar_energy_day / 1e3, color=PALETTE['sage'], lw=1.6, label='光伏电量')
    ax2.set_ylabel('电量\n(MWh/日)', fontsize=9)
    ax2.set_xlabel('日期')
    ax2.grid(alpha=0.25, color=PALETTE['gray'])
    ax2.legend(loc='upper right', fontsize=8, frameon=False)
    # 月份刻度
    month_starts = [0] + [i for i in range(1, R) if dates[i].month != dates[i - 1].month]
    ax2.set_xticks(month_starts)
    ax2.set_xticklabels([f'{dates[i].month}月' for i in month_starts], fontsize=8)
    # 四个日期标记
    for name, i in marks:
        if i is None:
            continue
        ax1.axvline(i, color=PALETTE['ink'], ls=':', lw=0.9, alpha=0.55)
        ax2.axvline(i, color=PALETTE['ink'], ls=':', lw=0.9, alpha=0.55)
        ax1.text(i, ymax1 * 1.05, name, rotation=90, va='top', ha='center',
                 fontsize=8, color=PALETTE['ink'])
    # 季节解释注释
    i_sum = marks[1][1]; i_win = marks[3][1]
    if i_sum is not None:
        ax1.annotate('夏至/梅雨：光伏波动大→误差大→6月紧急购电全年最高',
                     xy=(i_sum, emg_energy_day[i_sum]),
                     xytext=(i_sum - 80, ymax1 * 0.82),
                     fontsize=8, color=PALETTE['rose_d'], ha='center',
                     arrowprops=dict(arrowstyle='->', color=PALETTE['rose_d'], lw=1.0))
    if i_win is not None:
        ax1.annotate('冬至：冬季稳定→误差小→紧急购电最低（净负荷却最高）',
                     xy=(i_win, emg_energy_day[i_win]),
                     xytext=(i_win - 92, ymax1 * 0.45),
                     fontsize=8, color=PALETTE['sage_d'], ha='center',
                     arrowprops=dict(arrowstyle='->', color=PALETTE['sage_d'], lw=1.0))
    fig.suptitle('紧急购电的季节性：由预报误差波动驱动（梅雨高、冬季低），非净负荷水平', fontsize=11, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_5_seasonal_emergency.png'), dpi=300)
    plt.close(fig)

    # ---- fig 6: 净负荷周周期 (ACF) vs 预报加权衰减 ----
    daily_nl = (N.sum(axis=1)) * DT          # 全年日净负荷电量 (365 天)
    def _acf(x, k):
        x = x - x.mean()
        return float(np.sum(x[:-k] * x[k:]) / np.sum(x * x))
    lags = np.arange(1, 29)
    acf_vals = [_acf(daily_nl, k) for k in lags]
    acf1 = _acf(daily_nl, 1); acf7 = _acf(daily_nl, 7)
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(9.0, 3.6),
                                   gridspec_kw={'width_ratios': [2.4, 1]})
    colors = [PALETTE['rose_d'] if k % 7 == 0 else PALETTE['slate'] for k in lags]
    axa.bar(lags, acf_vals, color=colors, alpha=0.85, width=0.6)
    axa.axhline(0, color=PALETTE['gray'], lw=0.8)
    axa.annotate(f'lag-7 ≈ {acf7:.2f}\n（周周期）', xy=(7, acf7), xytext=(10, acf7 - 0.18),
                 fontsize=8, color=PALETTE['rose_d'],
                 arrowprops=dict(arrowstyle='->', color=PALETTE['rose_d'], lw=0.9))
    axa.annotate(f'lag-1 ≈ {acf1:.2f}', xy=(1, acf1), xytext=(5, acf1 + 0.16),
                 fontsize=8, color=PALETTE['slate'])
    axa.set_xlabel('滞后天数 k'); axa.set_ylabel('净负荷自相关 ACF')
    axa.set_title('（a）日净负荷：滞后 7 天尖峰', fontsize=9, color=PALETTE['ink'])
    axa.set_xticks([1, 7, 14, 21, 28])
    axa.grid(alpha=0.25, color=PALETTE['gray'])
    wk = np.arange(1, 8)
    axb.bar(wk, W, color=PALETTE['taupe'], alpha=0.85, width=0.6)
    axb.set_xlabel('滞后天数 k'); axb.set_ylabel('预报权重 w_k')
    axb.set_title('（b）自预报权重：按天衰减', fontsize=9, color=PALETTE['ink'])
    axb.set_xticks([1, 2, 3, 4, 5, 6, 7])
    axb.grid(alpha=0.25, color=PALETTE['gray'])
    fig.suptitle('周周期与预报加权错配：真相关在 lag-7 峰值，权重却把 lag-1 赋最高', fontsize=10.5, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_6_netload_acf.png'), dpi=300)
    plt.close(fig)

    # ---- fig 7: 分桶前后各星期几日均紧急购电 ----
    _, _, _, Zr_glob, _, _ = run_full_report(price, N, Nhat, Eerr, 80.0, None)  # round3 全局对照
    report_dow = full_dow[WARMUP_DAYS:]
    emg_glob_day = Zr_glob.sum(axis=1)
    emg_dow_day = Zr.sum(axis=1)
    wn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    g = [emg_glob_day[report_dow == w].mean() for w in range(7)]
    d = [emg_dow_day[report_dow == w].mean() for w in range(7)]
    x = np.arange(7)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.bar(x - 0.2, g, width=0.4, color=PALETTE['rose'], alpha=0.85, label='全局 80 分位（round3）')
    ax.bar(x + 0.2, d, width=0.4, color=PALETTE['slate'], alpha=0.85, label='按星期分桶（round4）')
    ax.set_xticks(x); ax.set_xticklabels(wn, fontsize=9)
    ax.set_ylabel('日均紧急购电量 (kWh)')
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis='y', alpha=0.25, color=PALETTE['gray'])
    ax.annotate(f'周日尖峰 {g[6]:.0f} → {d[6]:.0f}',
                xy=(6, d[6]), xytext=(3.4, g[6] * 0.86), fontsize=8, color=PALETTE['rose_d'],
                arrowprops=dict(arrowstyle='->', color=PALETTE['rose_d'], lw=0.9))
    fig.suptitle('按星期分桶效果：消除周日系统性低估尖峰', fontsize=10.5, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_7_dow_bucket_effect.png'), dpi=300)
    plt.close(fig)

    # ---- fig 8: 储能全年日充/日放 ----
    charge_day = Cr.sum(axis=1); disch_day = Qr.sum(axis=1)
    ratio = float(disch_day.sum() / charge_day.sum())
    xx = np.arange(REPORT_DAYS)
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.plot(xx, charge_day / 1e3, color=PALETTE['sage_d'], lw=1.2, label='日充电量')
    ax.plot(xx, disch_day / 1e3, color=PALETTE['taupe'], lw=1.2, label='日放电量')
    ax.set_ylabel('日充/放电量\n(MWh)', fontsize=9)
    ax.set_xlabel('日期')
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, color=PALETTE['gray'])
    month_starts = [0] + [i for i in range(1, REPORT_DAYS) if dates[i].month != dates[i - 1].month]
    ax.set_xticks(month_starts)
    ax.set_xticklabels([f'{dates[i].month}月' for i in month_starts], fontsize=8)
    ax.text(0.02, 0.94, f'全年 Σ放电/Σ充电 = {ratio:.4f}（= η_c·η_d = 0.81）',
            transform=ax.transAxes, fontsize=9, color=PALETTE['ink'])
    fig.suptitle('储能全年持续运行：日充/日放几乎成对出现', fontsize=10.5, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_q2_8_storage_daily.png'), dpi=300)
    plt.close(fig)

    # 季节性统计摘要（用于解释）
    emg_days_m, emg_energy_m = {}, {}
    for i, d in enumerate(dates):
        m = d.month
        emg_days_m[m] = emg_days_m.get(m, 0) + (1 if emg_energy_day[i] > 1e-6 else 0)
        emg_energy_m[m] = emg_energy_m.get(m, 0.0) + emg_energy_day[i]
    print('每日紧急购电统计（月）：')
    for m in sorted(emg_days_m):
        print(f'  {m:>2}月：紧急购电天数 {emg_days_m[m]:>3}，紧急购电量 {emg_energy_m[m]:>10.0f} kWh')

    print('figures written to', FIG_DIR)
    for f in ['fig_q2_1_quantile_sensitivity.png', 'fig_q2_2_baseline_comparison.png',
              'fig_q2_3_representative_day.png', 'fig_q2_4_monthly_cost.png',
              'fig_q2_5_seasonal_emergency.png', 'fig_q2_6_netload_acf.png',
              'fig_q2_7_dow_bucket_effect.png', 'fig_q2_8_storage_daily.png']:
        p = os.path.join(FIG_DIR, f)
        print(' ', p, os.path.getsize(p), 'bytes')


if __name__ == '__main__':
    main()
