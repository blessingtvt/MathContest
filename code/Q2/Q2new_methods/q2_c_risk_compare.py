# -*- coding: utf-8 -*-
"""Q2 随机规划扩展 —— 尾部风险对照（round4 确定性 vs C 多场景随机规划）。

产出：
  1) results/Q2/experiments/optimization/c_risk_comparison.json —— 尾部风险指标
     （总费用/紧急购电费、最大单日紧急购电、CVaR90/CVaR95、超阈值天数等）。
  2) paper/figures/fig_q2_9_stochastic_risk.png —— 双面板：箱线图 + 尾部生存曲线。
  3) paper/figures/fig_q2_10_stochastic_timeseries.png —— 每日紧急购电成本时序对照（C 削峰）。

信息集两模型一致（因果、无前瞻）；仅不确定性处理不同（固定分位余量 vs 场景+CVaR）。
"""
import os, sys, json
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # code/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))                    # code/Q2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                                     # 当前目录
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from common import *
from q2_main import error_quantile_dow, netload_forecast, bundle_dow
from q2_causal_scenario import make_forecast as cf_make_forecast, scenario_lp, Q_LEVELS, Q_PROB

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

PALETTE = {
    'slate': '#3B7FBF', 'steel': '#1F4E79', 'sage': '#2FA496', 'sage_d': '#1B6F64',
    'taupe': '#D98E04', 'rose': '#E0634F', 'rose_d': '#A33F2C', 'gray': '#5F6A73', 'ink': '#14181C',
}

C_PRED = 'blend25'
C_RHO = 0.2

# 图内用简短命名，完整模型名在论文正文写清楚：
#   确定性模型 = 逐日滚动 LP + 星期分桶 80 分位风险修正（主模型）
#   随机模型   = 多场景随机规划 + CVaR_0.9（扩展模型）
NAME_DET = '确定性模型'
NAME_SP = '随机模型'


def daily_series_B(b, N, Nhat, Eerr, full_dow):
    """round4：weighted7 自预报 + 星期分桶 80 分位余量 -> 每日计划/紧急购电费。"""
    price = b['附件1']['price']
    plan, emg = [], []
    for d in range(WARMUP_DAYS, N.shape[0]):
        e80 = error_quantile_dow(Eerr, full_dow, d, 80.0)
        Nsafe = Nhat[d] + e80
        _, x, c, q, E = daily_lp(price, Nsafe, np.zeros(T), E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
        z = clip0(N[d] * DT + c - x - q)
        plan.append(float((price * x).sum()))
        emg.append(float(ALPHA_EM * (price * z).sum()))
    return np.array(plan), np.array(emg)


def daily_series_C(b, N, dates, predictor=C_PRED, rho=C_RHO):
    """C：多场景随机规划（场景共享 x/c/q/E，CVaR 尾部约束）-> 每日计划/紧急购电费。"""
    price = b['附件1']['price']
    plan, emg = [], []
    for d in range(WARMUP_DAYS, N.shape[0]):
        base = cf_make_forecast(N, d, predictor)
        hist = np.arange(7, d)
        if predictor in ('weekday4', 'weekday4_scaled') or predictor.startswith('blend'):
            hist = hist[[dates[i].weekday() == dates[d].weekday() for i in hist]]
            hist = hist[hist >= 28]
        if len(hist) < 5:
            hist = np.arange(7, d)
        hist = hist[hist >= (28 if predictor in ('weekday4', 'weekday4_scaled') or predictor.startswith('blend') else 7)]
        err = N[hist] - np.array([cf_make_forecast(N, i, predictor) for i in hist])
        qerr = np.percentile(err, Q_LEVELS, axis=0)
        scenarios = base[None, :] + qerr
        x, c, qv, E = scenario_lp(price, scenarios, rho=rho)
        z = clip0(N[d] * DT + c - x - qv)
        plan.append(float((price * x).sum()))
        emg.append(float(ALPHA_EM * (price * z).sum()))
    return np.array(plan), np.array(emg)


def risk_metrics(plan, emg):
    total = plan + emg
    s = np.sort(emg)
    def cvar(alpha):
        k = int(np.ceil(alpha * len(s))) - 1
        return float(s[k:].mean()) if k + 1 < len(s) else float(s[-1])
    return {
        'total': float(total.sum()),
        'plan': float(plan.sum()),
        'emergency': float(emg.sum()),
        'daily_emergency_mean': float(emg.mean()),
        'max_daily_emergency': float(emg.max()),
        'max_daily_total': float(total.max()),
        'CVaR90_emergency': cvar(0.90),
        'CVaR95_emergency': cvar(0.95),
        'days_emergency_gt0': int((emg > 1e-6).sum()),
        'days_emergency_gt1000': int((emg > 1000).sum()),
        'days_emergency_gt5000': int((emg > 5000).sum()),
        'days_emergency_gt10000': int((emg > 10000).sum()),
    }


def fig_timeseries(emgB, emgC, dates):
    """fig_q2_10：每日紧急购电成本时序对照（随机模型在尖峰日削峰）。"""
    x = np.arange(len(emgB))
    diff = emgB - emgC
    month_starts = [0] + [i for i in range(1, len(emgB))
                          if dates[WARMUP_DAYS + i].month != dates[WARMUP_DAYS + i - 1].month]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.6, 5.8), sharex=True,
                                   gridspec_kw={'height_ratios': [2.3, 1.0]})
    ax1.plot(x, emgB / 1e3, color=PALETTE['slate'], lw=1.2, label=NAME_DET)
    ax1.plot(x, emgC / 1e3, color=PALETTE['sage'], lw=1.2, label=NAME_SP)
    ax1.fill_between(x, emgC / 1e3, emgB / 1e3, where=(diff > 0),
                     color=PALETTE['sage'], alpha=0.18, linewidth=0,
                     label='随机模型较确定性模型的节省')
    ax1.set_ylabel('每日紧急购电成本（千元/日）')
    ax1.set_title('（a）每日紧急购电成本：随机模型在尖峰日明显削峰', fontsize=9, color=PALETTE['ink'])
    ax1.legend(loc='upper right', fontsize=7.5, frameon=False)
    ax1.grid(alpha=0.25, color=PALETTE['gray'])
    ax2.bar(x, diff / 1e3, color=np.where(diff > 0, PALETTE['sage'], PALETTE['rose']),
            alpha=0.8, width=1.0)
    ax2.axhline(0, color=PALETTE['gray'], lw=0.8)
    ax2.set_ylabel('确定性 − 随机规划\n（千元/日）')
    ax2.set_xlabel('日期（2025-02 ~ 12，报告期 334 天）')
    ax2.set_title('（b）随机模型相对确定性模型的每日节省', fontsize=9, color=PALETTE['ink'])
    ax2.legend(handles=[Patch(facecolor=PALETTE['sage'], label='随机模型更省（削峰）'),
                        Patch(facecolor=PALETTE['rose'], label='随机模型更保守（少数日）')],
               loc='upper right', fontsize=7.5, frameon=False)
    ax2.set_xticks(month_starts)
    ax2.set_xticklabels([f'{dates[WARMUP_DAYS + i].month}月' for i in month_starts], fontsize=8)
    ax2.grid(alpha=0.25, color=PALETTE['gray'])
    fig.suptitle('随机模型的削峰时序：在夏季预报误差尖峰日系统性降低紧急购电', fontsize=11, color=PALETTE['ink'])
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, 'paper', 'figures', 'fig_q2_10_stochastic_timeseries.png'), dpi=300)
    plt.close(fig)


def main():
    b = load_bundle()
    price = b['附件1']['price']
    N = b['附件2_load'] - b['附件2_pv']
    dates = [datetime.strptime(s, '%Y-%m-%d %H:%M:%S') for s in b['dates']]
    full_dow = bundle_dow(b)
    Nhat, Eerr = netload_forecast(N)

    planB, emgB = daily_series_B(b, N, Nhat, Eerr, full_dow)
    planC, emgC = daily_series_C(b, N, dates)

    mB = risk_metrics(planB, emgB)
    mC = risk_metrics(planC, emgC)

    out = {
        'meta': {
            'question_id': 'Q2',
            'information_set': 'history only, d日0:00, 因果无前瞻 (两模型一致)',
            'comparison': 'round4 确定性(固定分位余量) vs C 多场景随机规划(CVaR)',
            'C_predictor': C_PRED, 'C_rho': C_RHO, 'C_beta': 0.9,
            'seed': SEED,
        },
        'round4_deterministic': mB,
        'C_stochastic': mC,
        'delta_C_minus_B': {k: round(mC[k] - mB[k], 4) for k in mB},
    }
    out_dir = os.path.join(RESULTS_DIR, 'Q2', 'experiments', 'optimization')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'c_risk_comparison.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # ---------------- 图：箱线图 + 尾部生存曲线 ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 4.2), gridspec_kw={'width_ratios': [1.05, 1.35]})

    # (a) 箱线图（隐去离群点，仅显示主体分布；尾部由 (b) 与文字标注呈现）
    bp = ax1.boxplot([emgB, emgC], widths=0.5, patch_artist=True, showfliers=False,
                     medianprops=dict(color=PALETTE['ink'], lw=1.2))
    bp['boxes'][0].set_facecolor(PALETTE['slate']); bp['boxes'][0].set_alpha(0.85)
    bp['boxes'][1].set_facecolor(PALETTE['sage']); bp['boxes'][1].set_alpha(0.85)
    for p in bp['whiskers'] + bp['caps']:
        p.set_color(PALETTE['ink']); p.set_lw(1.0)
    ax1.set_xticklabels(['确定性模型', '随机模型'], fontsize=9)
    ax1.set_ylabel('每日紧急购电成本（元/日）', fontsize=9)
    ax1.set_title('（a）紧急购电主体分布', fontsize=9, color=PALETTE['ink'])
    ax1.grid(axis='y', alpha=0.25, color=PALETTE['gray'])
    ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
    ax1.text(0.5, 0.97,
             f"最大单日紧急购电：{mB['max_daily_emergency']:,.0f}（确定性模型）  {mC['max_daily_emergency']:,.0f}（随机模型）",
             transform=ax1.transAxes, ha='center', va='top', fontsize=7.2, color=PALETTE['ink'])

    # (b) 尾部生存曲线：超过阈值的日数占比（对数 x）
    thr = np.logspace(2, 4.8, 60)  # 100 ~ 63000 元
    survB = [(emgB > t).mean() for t in thr]
    survC = [(emgC > t).mean() for t in thr]
    ax2.semilogx(thr, survB, color=PALETTE['slate'], lw=1.8, label=NAME_DET)
    ax2.semilogx(thr, survC, color=PALETTE['sage'], lw=1.8, label=NAME_SP)
    ax2.axvline(5000, color=PALETTE['gray'], ls=':', lw=1.0, alpha=0.7)
    ax2.annotate('阈值 5000 元', xy=(5000, 0.5), xytext=(1300, 0.52), fontsize=7.5,
                 color=PALETTE['gray'], arrowprops=dict(arrowstyle='->', color=PALETTE['gray'], lw=0.8))
    ax2.set_xlabel('每日紧急购电成本阈值（元，对数坐标）', fontsize=9)
    ax2.set_ylabel('超过阈值的日数占比', fontsize=9)
    ax2.set_title('（b）尾部生存曲线（随机模型处处更低）', fontsize=9, color=PALETTE['ink'])
    ax2.legend(loc='upper right', fontsize=7.5, frameon=False)
    ax2.grid(alpha=0.25, color=PALETTE['gray'])
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)

    fig.suptitle('随机模型相对确定性模型降低紧急购电暴露与尾部风险', fontsize=11, color=PALETTE['ink'])
    fig.tight_layout()
    fig_path = os.path.join(ROOT, 'paper', 'figures', 'fig_q2_9_stochastic_risk.png')
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)

    # 新增模型对比图：削峰时序
    fig_timeseries(emgB, emgC, dates)

    print(json.dumps({'round4': {k: mB[k] for k in ('total', 'emergency', 'max_daily_emergency', 'CVaR90_emergency', 'days_emergency_gt5000')},
                      'C': {k: mC[k] for k in ('total', 'emergency', 'max_daily_emergency', 'CVaR90_emergency', 'days_emergency_gt5000')}},
                     ensure_ascii=False, indent=2))
    print('json ->', os.path.join(out_dir, 'c_risk_comparison.json'))
    print('fig  ->', fig_path)


if __name__ == '__main__':
    main()
