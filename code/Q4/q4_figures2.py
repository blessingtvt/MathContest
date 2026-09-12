# -*- coding: utf-8 -*-
"""Q4 论文正文图（第二批）—— 调整时刻边际价值 / 电价波动趋势 / 关键变量灵敏度。

与 q4_figures.py 同配色、同风格，补齐论文正文所需的实验证据图：
  fig_q4_4_adjustment_value     调整时刻边际价值（E4-5 嵌套消融，MPC 各调整时刻省多少钱）
  fig_q4_5_price_trend          电价波动趋势（附件4 日平均电价时间序列 + 日内曲线 vs 附件1）
  fig_q4_6_volatility_sensitivity  波动幅度 k 灵敏度（E4-6，k=0→恒定, k=1→波动）
  fig_q4_7_price_forecast_uncertainty  电价预测不确定性成本（E4-3，日前已知 vs 因果自预报）

输出: paper/figures/fig_q4_*.png (300 dpi) + .svg
"""
import os, sys, json, pickle
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # code
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPT = os.path.join(ROOT, "results", "Q4", "experiments", "optimization")
FIGDIR = os.path.join(ROOT, "paper", "figures")
DATA_CLEAN = os.path.join(ROOT, "data_clean", "cleaned_data.pkl")

P = {
    "primary": "#1A6FC4", "primary_light": "#5B9BD5", "primary_pale": "#B4D4F0",
    "baseline": "#767676", "baseline_light": "#A8A8A8", "baseline_pale": "#D8D8D8",
    "positive": "#2E9E44", "negative": "#E53935",
    "accent1": "#E28E2C", "accent2": "#7B5FD6", "accent3": "#33B5A5",
}
WAN = 1e4  # 万元


def load():
    e45 = json.load(open(os.path.join(OPT, "e45_adjust_value.json"), encoding="utf-8"))
    e46 = json.load(open(os.path.join(OPT, "e46_volatility_sweep.json"), encoding="utf-8"))
    e43 = json.load(open(os.path.join(OPT, "e43_price_uncertainty.json"), encoding="utf-8"))
    b = pickle.load(open(DATA_CLEAN, "rb"))
    return e45, e46, e43, b


def style_ax(ax):
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.tick_params(labelsize=9)


def save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    fig.savefig(os.path.join(FIGDIR, f"{name}.png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.svg"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# ======================================================================
# fig_q4_4  调整时刻边际价值
# ======================================================================
def fig4_adjustment_value(e45):
    by = e45["total_by_n_stages"]
    ns = [1, 2, 3, 4]
    vals = [by[str(n)]["total"] / WAN for n in ns]
    labels = ["仅 0:00 计划\n(1 时刻)", "0:00 + 6:00\n(2 时刻)",
              "0:00+6:00+12:00\n(3 时刻)", "全 4 时刻\n(= result4-3)"]
    marg = e45["marginal_value_of_each_adjustment"]
    margs = [marg["6:00调整(1→2)"], marg["12:00调整(2→3)"], marg["18:00调整(3→4)"]]

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(ns, vals, color=P["primary"], linewidth=2.2, marker="o", markersize=7,
            zorder=3)
    # 边际价值标注（每段下降量，置于两段中点上方）
    for i in range(3):
        xm = (ns[i] + ns[i + 1]) / 2.0
        ym = (vals[i] + vals[i + 1]) / 2.0
        d = margs[i] / WAN
        lbl = f"−{d:,.1f} 万" if d >= 0.1 else "−≈0"
        ax.annotate(lbl, (xm, ym), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=9, fontweight="bold", color=P["negative"])
    for i, v in enumerate(vals):
        ax.text(ns[i], v + 25, f"{v:,.1f}", ha="center", fontsize=9,
                fontweight="bold", color=P["primary"] if i == 3 else "#333333")
    total_save = (vals[0] - vals[-1])
    ax.text(0.99, 0.95, f"滚动调整合计节省 {total_save:,.1f} 万元\n(18:00 调整几乎无边际价值)",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.8, color=P["primary"])
    ax.set_xticks(ns); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_title("调整时刻的边际价值：6:00 首调贡献最大 (Q4)", fontsize=11, fontweight="bold")
    style_ax(ax)
    fig.tight_layout()
    return fig


# ======================================================================
# fig_q4_5  电价波动趋势
# ======================================================================
def fig5_price_trend(b):
    price4 = b["附件4_price"]                       # (365,144)
    price1 = b["附件1"]["price"]                    # (144,)
    dates = b["dates"]
    tt = np.arange(144) / 6.0
    daily_mean = price4.mean(axis=1)
    intraday_mean4 = price4.mean(axis=0)            # 全年逐时段均值
    d0076 = int(np.argmin(price4.min(axis=1)))      # 含 0.0076 的极端低价日
    xs = np.array([datetime.strptime(s, "%Y-%m-%d %H:%M:%S") for s in dates])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [1.5, 1.0]})

    # 左：日平均电价时间序列
    ax1.plot(xs, daily_mean, color=P["primary_light"], lw=0.9, zorder=3)
    ax1.axhline(price1.mean(), color=P["baseline"], ls="--", lw=1.2,
                label="附件1 恒定电价 (均价 0.7662 元)")
    ax1.scatter([xs[d0076]], [daily_mean[d0076]], color=P["negative"], s=45, zorder=4,
                label=f"极端低价日 ({xs[d0076].strftime('%m-%d')}, 区间最低 0.0076 元)")
    ax1.annotate(f"{xs[d0076].strftime('%m-%d')} 极端低价日", (xs[d0076], daily_mean[d0076]),
                 textcoords="offset points", xytext=(-4, -18), fontsize=8.5,
                 color=P["negative"], ha="center")
    ax1.set_ylabel("日平均电价 (元/kWh)", fontsize=10)
    ax1.set_title("(a) 附件4 日平均电价全年时间序列", fontsize=10.5)
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
    ax1.legend(fontsize=8, frameon=False, loc="upper left")
    ax1.set_ylim(0.55, 1.05)

    # 右：日内曲线（附件1 vs 附件4 均值 vs 极端日）
    ax2.plot(tt, price1, color=P["baseline"], lw=2.0, label="附件1 固定曲线")
    ax2.plot(tt, intraday_mean4, color=P["primary"], lw=1.8, ls="--",
             label="附件4 全年逐时段均值")
    ax2.plot(tt, price4[d0076], color=P["negative"], lw=1.6, ls=":",
             label=f"附件4 极端低价日 {xs[d0076].strftime('%m-%d')}")
    ax2.set_xlabel("时间 (h)", fontsize=10)
    ax2.set_ylabel("电价 (元/kWh)", fontsize=10)
    ax2.set_title("(b) 日内电价曲线对比", fontsize=10.5)
    ax2.legend(fontsize=8, frameon=False, loc="upper left")
    ax2.set_xlim(0, 24)
    ax2.set_ylim(0, 1.6)

    for ax in (ax1, ax2):
        style_ax(ax)
    fig.suptitle("附件4 波动电价的结构：日内形状不变、日间水平波动 (Q4)", fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


# ======================================================================
# fig_q4_6  波动幅度 k 灵敏度
# ======================================================================
def fig6_volatility_sensitivity(e46):
    ks = sorted(float(k) for k in e46["k_sweep"])
    v42 = [e46["k_sweep"][f"{k:.1f}"]["result4_2"] / WAN for k in ks]
    v43 = [e46["k_sweep"][f"{k:.1f}"]["result4_3"] / WAN for k in ks]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(ks, v42, color=P["primary"], lw=2, marker="o", markersize=6,
            label="result4-2 (逐日 LP)")
    ax.plot(ks, v43, color=P["accent1"], lw=2, marker="s", markersize=6,
            label="result4-3 (滚动 MPC)")
    for k, v in zip(ks, v42):
        ax.text(k, v + 14, f"{v:,.1f}", ha="center", fontsize=8, color=P["primary"])
    for k, v in zip(ks, v43):
        ax.text(k, v - 40, f"{v:,.1f}", ha="center", fontsize=8, color=P["accent1"])
    ax.axvline(0, color=P["baseline"], ls="--", lw=1.0)
    ax.axvline(1, color=P["baseline"], ls="--", lw=1.0)
    ax.set_ylim(min(v43) - 65, max(v42) + 50)
    y0, y1 = ax.get_ylim()
    ax.text(0.02, y0 + 0.05 * (y1 - y0), "k=0\n(恒定电价=Q2/Q3)", fontsize=8, color="#606060", va="bottom")
    ax.text(1.02, y0 + 0.05 * (y1 - y0), "k=1\n(波动电价=Q4)", fontsize=8, color="#606060", va="bottom")
    ax.set_xlabel("波动幅度缩放系数 k", fontsize=10)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_title("电价日间波动幅度灵敏度：成本随 k 单调上升 (Q4)", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    style_ax(ax)
    fig.tight_layout()
    return fig


# ======================================================================
# fig_q4_7  电价预测不确定性成本
# ======================================================================
def fig7_price_forecast_uncertainty(e43):
    r42 = e43["result4_2"]; r43 = e43["result4_3"]
    names = ["result4-2\n(逐日 LP)", "result4-3\n(滚动 MPC)"]
    known = [r42["price_known"] / WAN, r43["price_known"] / WAN]
    forecast = [r42["price_forecast"] / WAN, r43["price_forecast"] / WAN]
    deltas = [r42["uncertainty_cost"] / WAN, r43["uncertainty_cost"] / WAN]

    x = np.arange(2); w = 0.34
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    b1 = ax.bar(x - w / 2, known, width=w, color=P["primary"], edgecolor="white",
                linewidth=0.8, label="电价日前已知 (主模型假设)")
    b2 = ax.bar(x + w / 2, forecast, width=w, color=P["primary_pale"], edgecolor="white",
                linewidth=0.8, label="电价实时未知 (因果自预报)")
    for i in range(2):
        ax.text(x[i] - w / 2, known[i] + 8, f"{known[i]:,.1f}", ha="center", fontsize=8.5,
                fontweight="bold", color=P["primary"])
        ax.text(x[i] + w / 2, forecast[i] + 8, f"{forecast[i]:,.1f}", ha="center", fontsize=8.5,
                color="#5A7A96")
        ax.text(x[i], forecast[i] + 62, f"预测误差成本 +{deltas[i]:,.1f} 万\n(+{deltas[i]/known[i]*100:.2f}%)",
                ha="center", fontsize=8.3, color=P["negative"])
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_ylim(0, max(forecast) * 1.14)
    ax.set_title("电价预测不确定性成本（影响有限）(Q4)", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    style_ax(ax)
    fig.tight_layout()
    return fig


def main():
    e45, e46, e43, b = load()
    save(fig4_adjustment_value(e45), "fig_q4_4_adjustment_value")
    save(fig5_price_trend(b), "fig_q4_5_price_trend")
    save(fig6_volatility_sensitivity(e46), "fig_q4_6_volatility_sensitivity")
    save(fig7_price_forecast_uncertainty(e43), "fig_q4_7_price_forecast_uncertainty")
    print("done")


if __name__ == "__main__":
    main()
