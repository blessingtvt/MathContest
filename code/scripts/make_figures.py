# -*- coding: utf-8 -*-
"""G4 图生成 —— 论文正式图（简洁、出版级、色盲友好）。

论文正式图(3张, 来源 Q1 代表日 daily_lp 解):
  fig1_power_balance.png   微网功率平衡图(负载/光伏/购电/储能充放)
  fig2_soc.png             储能SOC变化曲线(容量约束)
  fig3_price_purchase.png  电价-购电策略对比图(双纵轴)
对比图:
  fig_baseline_compare.png 四子题 主模型 vs 双基线

设计原则: 无背景色块、无结论文字(结论写进正文/图注)、线条加粗、图例逐色说明。
"""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False
rcParams["axes.linewidth"] = 0.8
rcParams["xtick.direction"] = "in"
rcParams["ytick.direction"] = "in"
rcParams["axes.grid"] = True
rcParams["grid.alpha"] = 0.25
rcParams["grid.linewidth"] = 0.4

# 统一配色 (Okabe-Ito 色盲友好)
C = {
    "load": "#6F78B9",       # 负载(需求): 绿色
    "pv":   "#FED297",       # 光伏(供给): 淡黄
    "grid": "#779FC6",       # 外网购电: 淡蓝
    "chg":  "#009E73",       # 储能充电: 绿
    "dis":  "#7FB3B0",       # 储能放电: 浅绿
    "bound":"#9E9E9E",       # 容量边界: 灰
    "E0":   "#6A3D9A",       # 初始储电量: 紫
    "price":"#404040",       # 电价: 深灰
}

PAPER = os.path.join(ROOT, "results", "figures", "paper")
COMPARE = os.path.join(ROOT, "results", "figures", "comparison")

tP = (np.arange(T) + 1) / 6.0   # 功率点时刻 0:10..24:00 (h)
tE = np.arange(T + 1) / 6.0     # 储能量时刻 0:00..24:00 (h)


def q1_solution():
    b = load_bundle()
    a1 = b["附件1"]
    price, load, pv = a1["price"], a1["load"], a1["pv_forecast"]
    cost, x, c, q, E = daily_lp(price, load, pv, E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
    return price, load, pv, x, c, q, E


def _xticks(ax):
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 4))
    ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 4)])


def fig1_power_balance(price, load, pv, x, c, q):
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=300)
    # 供给堆叠(自下而上): 光伏 → 购电 → 放电
    ax.stackplot(tP, pv, x / DT, q / DT,
                 colors=[C["pv"], C["grid"], C["dis"]],
                 labels=["光伏 $G_t$ (kW)", "购电 $x_t/\\Delta t$ (kW)", "放电 $q_t/\\Delta t$ (kW)"],
                 alpha=0.88, edgecolor="none")
    # 需求: 负载线(绿) + 负载+充电线(绿虚线 = 供给堆顶)
    ax.plot(tP, load, color=C["load"], lw=2.8, label="负载 $L_t$ (kW)")
    ax.plot(tP, load + c / DT, color=C["chg"], lw=1.5, ls="--",
            label="负载+充电 $L_t+c_t/\\Delta t$ (kW)")
    _xticks(ax)
    ax.set_ylim(0, (load + c / DT).max() * 1.12)
    ax.set_xlabel("时间 (h)")
    ax.set_ylabel("功率 (kW)")
    ax.set_title("微网功率平衡（代表日）", fontsize=12.5, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9, ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig1_power_balance.png"))
    plt.close(fig)


def fig2_soc(E):
    fig, ax = plt.subplots(figsize=(9.0, 4.4), dpi=300)
    ax.fill_between(tE, EMIN, EMAX, color="0.85", alpha=0.30, lw=0)
    ax.axhline(EMAX, color=C["bound"], ls="--", lw=1.2, label=f"容量上界 $E_{{\\max}}=10800$ kWh")
    ax.axhline(EMIN, color=C["bound"], ls="--", lw=1.2, label=f"容量下界 $E_{{\\min}}=1200$ kWh")
    ax.axhline(E0_INIT, color=C["E0"], ls=":", lw=1.4, label=f"初始 $E_0=6000$ kWh")
    ax.plot(tE, E, color=C["chg"], lw=2.4, label="储电量 $E(t)$ (kWh)")
    _xticks(ax)
    ax.set_xlabel("时间 (h)")
    ax.set_ylabel("储电量 (kWh)")
    ax.set_title("储能 SOC 变化（代表日）", fontsize=12.5, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig2_soc.png"))
    plt.close(fig)


def fig3_price_purchase(price, x):
    fig, ax1 = plt.subplots(figsize=(9.5, 4.6), dpi=300)
    ax1.step(tP, price, where="mid", color=C["price"], lw=1.9, label="电价 $p_t$ (元/kWh)")
    ax1.set_xlabel("时间 (h)")
    ax1.set_ylabel("电价 (元/kWh)", color=C["price"])
    ax1.tick_params(axis="y", labelcolor=C["price"])
    ax1.set_ylim(0, price.max() * 1.22)

    ax2 = ax1.twinx()
    ax2.step(tP, x / DT, where="mid", color=C["grid"], lw=1.7, label="购电功率 $x_t/\\Delta t$ (kW)")
    ax2.set_ylabel("购电功率 (kW)", color=C["grid"])
    ax2.tick_params(axis="y", labelcolor=C["grid"])

    _xticks(ax1)
    ax1.set_title("电价与购电策略（代表日）", fontsize=12.5, fontweight="bold")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PAPER, "fig3_price_purchase.png"))
    plt.close(fig)


def fig_baseline_compare():
    rs = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        p = os.path.join(RESULTS_DIR, q, "experiments", "round1", "run_summary.json")
        with open(p, encoding="utf-8") as f:
            rs[q] = json.load(f)
    main = [rs["Q1"]["main"]["objective_value"], rs["Q2"]["main"]["objective_value"],
            rs["Q3"]["main"]["objective_value"], rs["Q4"]["result4_2"]["objective_value"]]
    baseB = [rs["Q1"]["baselines"][0]["objective_value"], rs["Q2"]["baselines"][0]["objective_value"],
             rs["Q3"]["baselines"][0]["objective_value"], rs["Q4"]["baselines"][0]["objective_value"]]
    baseR = [rs["Q1"]["baselines"][1]["objective_value"], rs["Q2"]["baselines"][1]["objective_value"],
             rs["Q3"]["baselines"][1]["objective_value"], rs["Q4"]["baselines"][1]["objective_value"]]
    labels = ["Q1(日)", "Q2(报告期)", "Q3(报告期)", "Q4-2(报告期)"]
    xx = np.arange(len(labels)); w = 0.26
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
    ax.bar(xx - w, main, w, label="主模型", color=C["grid"])
    ax.bar(xx, baseB, w, label="无储能基线", color=C["dis"])
    ax.bar(xx + w, baseR, w, label="规则套利基线", color=C["chg"])
    ax.set_xticks(xx); ax.set_xticklabels(labels)
    ax.set_ylabel("购电费用 (元)")
    ax.set_yscale("log")
    ax.set_title("主模型与双基线 购电费用对比", fontsize=12.5, fontweight="bold")
    ax.legend(fontsize=9, frameon=False)
    for i, v in enumerate(main):
        ax.text(xx[i] - w, v * 1.06, f"{v:,.0f}", ha="center", va="bottom", fontsize=7, rotation=90)
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
