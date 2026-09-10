# -*- coding: utf-8 -*-
"""Q2 图生成: 日前预报 + 紧急购电模型的可视化论证。

  fig_q2_power_balance.png   代表性日功率平衡(预报 vs 实际光伏 + 紧急购电 + 储能)
  fig_q2_soc.png             全年储能 SOC(逐日 0:00, 跨日连续 + 终态闭合)
  fig_q2_emergency_seasonal.png  月度紧急购电 / 弃光 / 负载 / 光伏(季节双峰)
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

C = {
    "load": "#2c3e50",
    "pv_fc": "#e67e22",      # 预报光伏(浅)
    "pv_act": "#f1c40f",     # 实际光伏(亮)
    "grid": "#2980b9",
    "emg": "#c0392b",        # 紧急购电
    "chg": "#27ae60",
    "dis": "#e74c3c",
    "bound": "#c0392b",
    "E0": "#8e44ad",
}

OUT = os.path.join(RESULTS_DIR, "figures", "q2")
tP = (np.arange(T) + 0.5) / 6.0    # 区间中心时刻
tE = np.arange(T + 1) / 6.0


def load_solution():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    D = load.shape[0]
    ghat0 = np.zeros((D, T))
    for d in range(D):
        ghat0[d] = forecast_intervals(fc, d, 0)
    price_flat = np.tile(price, D)
    load_flat = load.reshape(-1)
    pv_flat = pv.reshape(-1)
    _, X, C, Q, E = full_year_lp(price_flat, load_flat, ghat0.reshape(-1),
                                 E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)
    x_flat = X.reshape(-1); c_flat = C.reshape(-1); q_flat = Q.reshape(-1)
    Z_flat = clip0(np.maximum(load_flat * DT + c_flat - x_flat - pv_flat * DT - q_flat, 0.0))
    Z = Z_flat.reshape(D, T)
    curt_flat = clip0(x_flat + pv_flat * DT + q_flat - load_flat * DT - c_flat)
    return b, price, load, pv, ghat0, X, C, Q, E, Z, curt_flat


def _xticks_day(ax):
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 4))
    ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 4)])
    ax.grid(alpha=0.22, lw=0.5)


def fig_power_balance(b, price, load, pv, ghat0, X, Cc, Q, E, Z):
    D = load.shape[0]
    # 选预报误差大(紧急购电最多)的一天
    d = int(np.argmax(Z.sum(axis=1)))
    date = datetime.strptime(b["dates"][d], "%Y-%m-%d %H:%M:%S").strftime("%m-%d")
    L, Gfc, G = load[d], ghat0[d], pv[d]
    x, c, q, z = X[d], Cc[d], Q[d], Z[d]
    Es = E[d * T:d * T + T + 1]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.6, 7.2), dpi=200,
                                   sharex=True, gridspec_kw={"height_ratios": [1.05, 0.95]})

    # 上: 负载 / 预报光伏 / 实际光伏
    ax1.fill_between(tP, G, 0, color=C["pv_act"], alpha=0.16, lw=0)
    ax1.plot(tP, G, color=C["pv_act"], lw=1.5, label="实际光伏 $G_t$")
    ax1.plot(tP, Gfc, color=C["pv_fc"], lw=1.3, ls="--", label="0:00 预报 $\\hat G_t$")
    ax1.plot(tP, L, color=C["load"], lw=2.0, label="小区负载 $L_t$")
    ax1.set_ylabel("功率 (kW)")
    ax1.set_title(f"Q2 日前计划功率平衡（{date}，预报误差较大日）", fontsize=12.5, fontweight="bold")
    ax1.legend(loc="upper right", fontsize=8.5, ncol=3, framealpha=0.9)
    ax1.grid(alpha=0.22, lw=0.5)

    # 下: 计划购电 / 紧急购电 / 储能 SOC
    ax2.fill_between(tP, x / DT, 0, color=C["grid"], alpha=0.35, lw=0, label="计划购电 $x_t/\\Delta t$")
    ax2.fill_between(tP, z / DT, 0, color=C["emg"], alpha=0.55, lw=0, label="紧急购电 $z_t/\\Delta t$ (5倍价)")
    ax2.plot(tP, x / DT, color=C["grid"], lw=1.4)
    ax2.set_ylabel("购电功率 (kW)")
    ax2.set_ylim(0, max(8500, (x / DT).max() * 1.15))
    ax2b = ax2.twinx()
    ax2b.plot(tE, Es, color=C["chg"], lw=2.0, label="储电量 $E_t$")
    ax2b.set_ylabel("储电量 (kWh)", color=C["chg"])
    ax2b.tick_params(axis="y", labelcolor=C["chg"])
    ax2b.set_ylim(0, 12200)
    ax2b.axhline(EMIN, color="0.5", ls=":", lw=1.0)
    ax2b.axhline(EMAX, color="0.5", ls=":", lw=1.0)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2b.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8.5, framealpha=0.9)

    _xticks_day(ax2)
    ax2.set_xlabel("时间 (h)")
    fig.text(0.5, 0.012,
             "结论：预报低估光伏时计划购电不足，缺口由紧急购电(5倍)补足；预报高估时多余光伏被弃——非完美预见下 z>0",
             ha="center", fontsize=8.8, color="0.3")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(OUT, "fig_q2_power_balance.png"))
    plt.close(fig)


def fig_soc(b, E):
    D = len(b["附件2_load"])
    Ed = E[0::T]   # 每日 0:00 储电量 (长度 D+1)
    days = np.arange(D + 1)
    # 月分界线
    month_start = [0]
    for d in range(1, D):
        if datetime.strptime(b["dates"][d - 1], "%Y-%m-%d %H:%M:%S").month != \
           datetime.strptime(b["dates"][d], "%Y-%m-%d %H:%M:%S").month:
            month_start.append(d)
    fig, ax = plt.subplots(figsize=(10.6, 4.6), dpi=200)
    ax.fill_between(days, EMIN, EMAX, color="gray", alpha=0.06)
    ax.axhline(EMAX, color=C["bound"], ls="--", lw=1.0, label=f"容量上界 $E_{{\\max}}=10800$")
    ax.axhline(EMIN, color=C["bound"], ls="--", lw=1.0, label=f"容量下界 $E_{{\\min}}=1200$")
    ax.plot(days, Ed, color=C["chg"], lw=1.2, label="每日 0:00 储电量 $E_0(d)$")
    ax.plot([0, D], [E0_INIT, E0_INIT], "o", color=C["E0"], ms=6, zorder=6, label="初始/终态 $6000$")
    for m in month_start:
        ax.axvline(m, color="0.6", lw=0.5, alpha=0.5)
    ax.set_xlim(0, D)
    ax.set_ylim(0, 12200)
    ax.set_xlabel("日期（2025年，1月为预热期）")
    ax.set_ylabel("储电量 (kWh)")
    ax.set_title("Q2 全年储能 SOC：跨日连续、终态闭合", fontsize=12.5, fontweight="bold")
    ax.text(0.5, 0.01, "结论：储电量全年在 [1200,10800] 内跨日连续漂移(无每日倒空)，12-31 终态回到 6000",
            transform=ax.transAxes, fontsize=8.8, ha="center", color="0.3")
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_q2_soc.png"))
    plt.close(fig)


def fig_seasonal(b, load, pv, Z, curt_flat):
    D = load.shape[0]
    Z_rep = Z[WARMUP_DAYS:].sum(axis=1)              # 每日紧急购电 kWh
    curt_rep = curt_flat.reshape(D, T)[WARMUP_DAYS:].sum(axis=1)
    load_rep = (load[WARMUP_DAYS:] * DT).sum(axis=1)  # 每日负载 MWh
    pv_rep = (pv[WARMUP_DAYS:] * DT).sum(axis=1)      # 每日光伏 MWh
    months = range(2, 13)
    emg_m = [Z_rep[np.array([datetime.strptime(b["dates"][WARMUP_DAYS + i], "%Y-%m-%d %H:%M:%S").month
                              for i in range(len(Z_rep))]) == m].sum() / 1000.0 for m in months]
    curt_m = [curt_rep[np.array([datetime.strptime(b["dates"][WARMUP_DAYS + i], "%Y-%m-%d %H:%M:%S").month
                                 for i in range(len(Z_rep))]) == m].sum() / 1000.0 for m in months]
    load_m = [load_rep[np.array([datetime.strptime(b["dates"][WARMUP_DAYS + i], "%Y-%m-%d %H:%M:%S").month
                                 for i in range(len(Z_rep))]) == m].mean() for m in months]
    pv_m = [pv_rep[np.array([datetime.strptime(b["dates"][WARMUP_DAYS + i], "%Y-%m-%d %H:%M:%S").month
                            for i in range(len(Z_rep))]) == m].mean() for m in months]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.0, 6.6), dpi=200)
    xx = np.arange(len(months)); w = 0.38
    ax1.bar(xx - w / 2, emg_m, w, label="紧急购电", color=C["emg"], alpha=0.85)
    ax1.bar(xx + w / 2, curt_m, w, label="弃光", color=C["pv_act"], alpha=0.85)
    ax1.set_xticks(xx); ax1.set_xticklabels([f"{m}月" for m in months])
    ax1.set_ylabel("月度电量 (MWh)")
    ax1.set_title("Q2 月度紧急购电与弃光", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.25, lw=0.5)

    ax2.plot(xx, load_m, "-o", color=C["load"], lw=1.8, label="日均负载")
    ax2.plot(xx, pv_m, "-s", color=C["pv_act"], lw=1.8, label="日均光伏")
    ax2.set_xticks(xx); ax2.set_xticklabels([f"{m}月" for m in months])
    ax2.set_ylabel("日均电量 (MWh)")
    ax2.set_title("季节性：负载双峰(夏冬高) + 光伏夏高冬低", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_q2_emergency_seasonal.png"))
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    b, price, load, pv, ghat0, X, C, Q, E, Z, curt = load_solution()
    fig_power_balance(b, price, load, pv, ghat0, X, C, Q, E, Z)
    fig_soc(b, E)
    fig_seasonal(b, load, pv, Z, curt)
    print("Q2 figures written to", OUT)
    for fn in sorted(os.listdir(OUT)):
        print(" ", fn)


if __name__ == "__main__":
    main()
