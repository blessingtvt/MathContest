# -*- coding: utf-8 -*-
"""G4 图生成 —— 论文正式图（简洁、出版级、色盲友好）。

论文正式图(3张, 来源 Q1 代表日 daily_lp 解):
  fig1_power_balance.png   微网功率平衡图(负载/光伏/购电/储能充放)
  fig2_soc.png             储能SOC变化曲线(容量约束)
  fig3_price_purchase.png  电价-购电策略对比图(双纵轴)
对比图:
  fig_baseline_compare.png 四子题 主模型 vs 双基线

设计原则:
  无背景色块、无结论文字(结论写进正文/图注)、线条加粗、图例逐色说明。
"""

import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.ticker import AutoMinorLocator, FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

# ============================================================
# 全局出版级样式
# ============================================================
rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei",
                               "Noto Sans CJK SC", "DejaVu Sans"]
rcParams["font.size"]          = 10.5
rcParams["axes.unicode_minus"] = False
rcParams["mathtext.fontset"]   = "stixsans"     # 与无衬线正文协调的数学字体

# —— 坐标轴 / 边框 ——
rcParams["axes.linewidth"]  = 0.9
rcParams["axes.edgecolor"]  = "#3A3A3A"
rcParams["axes.labelcolor"] = "#1A1A1A"
rcParams["axes.labelsize"]  = 11
rcParams["axes.titlesize"]  = 12.5
rcParams["axes.titleweight"] = "bold"

# —— 刻度 ——
rcParams["xtick.direction"] = "in"
rcParams["ytick.direction"] = "in"
rcParams["xtick.color"]     = "#3A3A3A"
rcParams["ytick.color"]     = "#3A3A3A"
rcParams["xtick.labelsize"] = 10
rcParams["ytick.labelsize"] = 10
rcParams["xtick.major.size"] = 3.2
rcParams["ytick.major.size"] = 3.2
rcParams["xtick.minor.size"] = 1.8
rcParams["ytick.minor.size"] = 1.8

# —— 网格 ——
rcParams["axes.grid"]       = True
rcParams["grid.color"]      = "#B8B8B8"
rcParams["grid.alpha"]      = 0.25
rcParams["grid.linewidth"]  = 0.5
rcParams["grid.linestyle"]  = "-"

# —— 图例 ——
rcParams["legend.frameon"]      = False
rcParams["legend.fontsize"]     = 9
rcParams["legend.handlelength"] = 1.8
rcParams["legend.handletextpad"] = 0.55
rcParams["legend.labelspacing"] = 0.35
rcParams["legend.columnspacing"] = 1.3
rcParams["legend.borderaxespad"] = 0.6

rcParams["figure.facecolor"] = "white"
rcParams["savefig.facecolor"] = "white"

# ============================================================
# 统一配色（Okabe-Ito 色盲友好体系，柔和化处理）
# ============================================================
C = {
    "pv":      "#F2C14E",   # 光伏(供给)   琥珀黄
    "grid":    "#6FA8DC",   # 外网购电     天蓝
    "dis":     "#66C2A5",   # 储能放电     薄荷绿
    "load":    "#17324D",   # 负载(需求)   深藏青
    "loadchg": "#E4572E",   # 负载+充电    陶土红(虚线)
    "chg":     "#2A9D8F",   # 储能充电     青绿
    "bound":   "#9AA0A6",   # 容量边界     灰
    "E0":      "#8E5BC9",   # 初始储电量   紫
    "price":   "#2B2D42",   # 电价         近黑
    "band":    "#EDF1F4",   # 容量带底色   浅灰
}

PAPER   = os.path.join(ROOT, "results", "figures", "paper")
COMPARE = os.path.join(ROOT, "results", "figures", "comparison")

tP = (np.arange(T) + 1) / 6.0   # 功率点时刻 0:10..24:00 (h)
tE = np.arange(T + 1) / 6.0     # 储能量时刻 0:00..24:00 (h)


def q1_solution():
    b = load_bundle()
    a1 = b["附件1"]
    price, load, pv = a1["price"], a1["load"], a1["pv_forecast"]
    cost, x, c, q, E = daily_lp(price, load, pv, E0=E0_INIT,
                                terminal_eq=True, E_term=E0_INIT)
    return price, load, pv, x, c, q, E


def _xticks(ax, hours=range(0, 25, 4)):
    """统一的 24h 横轴刻度（主刻度 + 次级刻度）。"""
    ax.set_xlim(0, 24)
    ax.set_xticks(list(hours))
    ax.set_xticklabels([f"{h}:00" for h in hours])
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))


def _despine(ax, top=True, right=True):
    """去掉上/右边框，保持画面轻盈。"""
    if top:
        ax.spines["top"].set_visible(False)
    if right:
        ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


# ============================================================
# Fig 1 · 微网功率平衡
# ============================================================
def fig1_power_balance(price, load, pv, x, c, q):
    y_grid = x / DT
    y_dis  = q / DT
    y_need = load + c / DT

    fig, ax = plt.subplots(figsize=(9.6, 4.9), dpi=300)

    # —— 供给堆叠（自下而上）：光伏 → 购电 → 放电 ——
    ax.stackplot(
        tP, pv, y_grid, y_dis,
        colors=[C["pv"], C["grid"], C["dis"]],
        labels=["光伏 $G_t$ (kW)",
                "购电 $x_t/\\Delta t$ (kW)",
                "放电 $q_t/\\Delta t$ (kW)"],
        alpha=0.95, edgecolor="none", zorder=2,
    )

    # —— 需求侧：负载实线 + 负载+充电虚线 ——
    ax.plot(tP, load, color=C["load"], lw=2.6,
            solid_capstyle="round", zorder=6,
            label="负载 $L_t$ (kW)")
    ax.plot(tP, y_need, color=C["loadchg"], lw=1.6,
            ls=(0, (5, 2.5)), solid_capstyle="round", zorder=5,
            label="负载+充电 $L_t+c_t/\\Delta t$ (kW)")

    _xticks(ax)
    ax.set_ylim(0, float(np.max(y_need)) * 1.14)
    ax.set_xlabel("时间 (h)", labelpad=4)
    ax.set_ylabel("功率 (kW)", labelpad=4)
    ax.set_title("微网功率平衡（代表日）", pad=8)

    ax.legend(loc="upper left", ncol=2, fontsize=8.6)

    _despine(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig1_power_balance.png"))
    plt.close(fig)


# ============================================================
# Fig 2 · 储能 SOC 变化
# ============================================================
def fig2_soc(E):
    fig, ax = plt.subplots(figsize=(9.2, 4.5), dpi=300)

    # —— 可用容量区间（浅灰底） ——
    ax.fill_between(tE, EMIN, EMAX, color=C["band"], lw=0, zorder=1)

    # —— 曲线下方强调（浅青绿） ——
    ax.fill_between(tE, EMIN, E, color=C["chg"], alpha=0.13, lw=0, zorder=2)

    # —— 约束参考线 ——
    ax.axhline(EMAX, color=C["bound"], ls="--", lw=1.2, zorder=3,
               label=f"容量上界 $E_{{\\max}}={EMAX:,.0f}$ kWh")
    ax.axhline(EMIN, color=C["bound"], ls="--", lw=1.2, zorder=3,
               label=f"容量下界 $E_{{\\min}}={EMIN:,.0f}$ kWh")
    ax.axhline(E0_INIT, color=C["E0"], ls=":", lw=1.6, zorder=3,
               label=f"初始储电量 $E_0={E0_INIT:,.0f}$ kWh")

    # —— SOC 曲线 ——
    ax.plot(tE, E, color=C["chg"], lw=2.5,
            solid_capstyle="round", zorder=5,
            label="储电量 $E(t)$ (kWh)")

    _xticks(ax)
    lo = min(EMIN, float(np.min(E)))
    hi = max(EMAX, float(np.max(E)))
    pad = (hi - lo) * 0.10
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))

    ax.set_xlabel("时间 (h)", labelpad=4)
    ax.set_ylabel("储电量 (kWh)", labelpad=4)
    ax.set_title("储能 SOC 变化（代表日）", pad=8)

    ax.legend(loc="lower right", ncol=2, fontsize=8.6)

    _despine(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig2_soc.png"))
    plt.close(fig)


# ============================================================
# Fig 3 · 电价与购电策略（双纵轴）
# ============================================================
def fig3_price_purchase(price, x):
    y_buy = x / DT

    fig, ax1 = plt.subplots(figsize=(9.6, 4.7), dpi=300)

    # —— 左轴：电价 ——
    ax1.fill_between(tP, 0, price, step="mid",
                     color=C["price"], alpha=0.08, lw=0, zorder=1)
    ax1.step(tP, price, where="mid", color=C["price"], lw=2.0, zorder=6,
             label="电价 $p_t$ (元/kWh)")
    ax1.set_xlabel("时间 (h)", labelpad=4)
    ax1.set_ylabel("电价 (元/kWh)", color=C["price"], labelpad=6)
    ax1.tick_params(axis="y", labelcolor=C["price"])
    ax1.set_ylim(0, float(np.max(price)) * 1.25)

    # —— 右轴：购电功率 ——
    ax2 = ax1.twinx()
    ax2.fill_between(tP, 0, y_buy, step="mid",
                     color=C["grid"], alpha=0.20, lw=0, zorder=2)
    ax2.step(tP, y_buy, where="mid", color="#4E90C8", lw=2.0, zorder=5,
             label="购电功率 $x_t/\\Delta t$ (kW)")
    ax2.set_ylabel("购电功率 (kW)", color="#4E90C8", labelpad=6)
    ax2.tick_params(axis="y", labelcolor="#4E90C8")
    ax2.set_ylim(0, float(np.max(y_buy)) * 1.30)

    # 保证电价线不被右轴的填充遮盖
    ax1.set_zorder(ax2.get_zorder() + 1)
    ax1.patch.set_visible(False)

    _xticks(ax1)
    ax1.set_title("电价与购电策略（代表日）", pad=8)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2, fontsize=8.8)

    _despine(ax1)
    ax2.spines["top"].set_visible(False)
    ax1.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig3_price_purchase.png"))
    plt.close(fig)


# ============================================================
# Fig 4 · 主模型 vs 双基线
# ============================================================
def fig_baseline_compare():
    rs = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        p = os.path.join(RESULTS_DIR, q, "experiments", "round1", "run_summary.json")
        with open(p, encoding="utf-8") as f:
            rs[q] = json.load(f)

    main = [rs["Q1"]["main"]["objective_value"],
            rs["Q2"]["main"]["objective_value"],
            rs["Q3"]["main"]["objective_value"],
            rs["Q4"]["result4_2"]["objective_value"]]
    baseB = [rs["Q1"]["baselines"][0]["objective_value"],
             rs["Q2"]["baselines"][0]["objective_value"],
             rs["Q3"]["baselines"][0]["objective_value"],
             rs["Q4"]["baselines"][0]["objective_value"]]
    baseR = [rs["Q1"]["baselines"][1]["objective_value"],
             rs["Q2"]["baselines"][1]["objective_value"],
             rs["Q3"]["baselines"][1]["objective_value"],
             rs["Q4"]["baselines"][1]["objective_value"]]

    labels = ["Q1(日)", "Q2(报告期)", "Q3(报告期)", "Q4-2(报告期)"]
    xx = np.arange(len(labels))
    w = 0.26

    fig, ax = plt.subplots(figsize=(8.8, 4.9), dpi=300)

    ax.bar(xx - w, main,  w, label="主模型",       color="#2C6E9B",
           edgecolor="white", linewidth=0.6, zorder=3)
    ax.bar(xx,     baseB, w, label="无储能基线",   color="#A8CBE0",
           edgecolor="white", linewidth=0.6, zorder=3)
    ax.bar(xx + w, baseR, w, label="规则套利基线", color="#6FBFA3",
           edgecolor="white", linewidth=0.6, zorder=3)

    ax.set_xticks(xx)
    ax.set_xticklabels(labels)
    ax.set_ylabel("购电费用 (元)")
    ax.set_yscale("log")

    ymin = min(min(main), min(baseB), min(baseR))
    ymax = max(max(main), max(baseB), max(baseR))
    ax.set_ylim(ymin * 0.5, ymax * 3.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))

    ax.set_title("主模型与双基线 购电费用对比", pad=8)
    ax.legend(loc="upper left", ncol=3, fontsize=8.8)

    # 仅对主模型标注数值，避免拥挤
    for i, v in enumerate(main):
        ax.text(xx[i] - w, v * 1.10, f"{v:,.0f}", ha="center", va="bottom",
                fontsize=7.2, rotation=90, color="#1B4A6B")

    ax.grid(True, axis="y", color="#B8B8B8", alpha=0.25, lw=0.5)
    ax.grid(False, axis="x")
    _despine(ax)

    fig.tight_layout()
    fig.savefig(os.path.join(COMPARE, "fig_baseline_compare.png"))
    plt.close(fig)


def main():
    os.makedirs(PAPER, exist_ok=True)
    os.makedirs(COMPARE, exist_ok=True)

    price, load, pv, x, c, q, E = q1_solution()

    fig1_power_balance(price, load, pv, x, c, q)
    fig2_soc(E)
    fig3_price_purchase(price, x)
    fig_baseline_compare()

    print("figures written:")
    for d in (PAPER, COMPARE):
        for fn in sorted(os.listdir(d)):
            print(" ", os.path.join(d, fn))


if __name__ == "__main__":
    main()