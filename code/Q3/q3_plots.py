# -*- coding: utf-8 -*-
"""Q3 G4 图表生成：灵敏度分析 + 模型示意图。

输出: results/Q3/figures/
  fig_quantile_sweep.png  分位 q 敏感性
  fig_stage_value.png     调整阶段边际价值 (是否引入其他预报时刻)
  fig_horizon_error.png   预报误差-前瞻时域
  fig_perturbation.png    负荷/光伏 ±5% 扰动
  fig_model_schematic.png 滚动 MPC 模型示意图
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import RESULTS_DIR

FIG_DIR = os.path.join(RESULTS_DIR, "Q3", "figures")

# 中文/西文字体
for fn in ("Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"):
    try:
        matplotlib.rcParams["font.sans-serif"] = [fn] + matplotlib.rcParams["font.sans-serif"]
        break
    except Exception:
        pass
matplotlib.rcParams["axes.unicode_minus"] = False


def load_report():
    p = os.path.join(RESULTS_DIR, "Q3", "experiments", "round3", "robustness_report.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def fig_quantile_sweep(rep):
    sweep = rep["quantile_sweep_total"]
    qs = [int(k[1:]) for k in sweep.keys()]
    vals = [sweep[k] / 1e6 for k in sweep.keys()]  # 百万元
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(qs, vals, "o-", color="#1f77b4", lw=1.8)
    ax.axvline(80, color="gray", ls="--", lw=1, alpha=0.7)
    ax.set_xlabel("Risk-correction quantile q (%)")
    ax.set_ylabel("Total purchase cost (million yuan)")
    ax.set_title("Sensitivity of total cost to PV-risk correction quantile")
    ax.annotate("q=80 chosen", xy=(80, sweep["q80"] / 1e6),
                xytext=(52, sweep["q80"] / 1e6 + 1.0), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="gray"))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_quantile_sweep.png"), dpi=150)
    plt.close(fig)


def fig_stage_value(rep):
    sa = rep["stage_ablation"]
    keys = ["0", "0+6", "0+6+12", "0+6+12+18"]
    labels = ["0:00\n(plan only)", "+6:00", "+12:00", "+18:00\n(full)"]
    vals = [sa[k]["total"] / 1e6 for k in keys]
    pf = rep["perfect_forecast_upper_bound"]["total"] / 1e6
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.plot(range(4), vals, "o-", color="#d62728", lw=2, label="Risk-corrected forecast")
    ax.axhline(pf, color="green", ls="--", lw=1.5, label=f"Perfect foresight bound ({pf:.2f}M)")
    for i, v in enumerate(vals):
        ax.annotate(f"{v:.2f}M", (i, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8.5)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Total purchase cost (million yuan)")
    ax.set_xlabel("Forecast/adjustment times included")
    ax.set_title("Marginal value of additional adjustment times")
    ax.legend(fontsize=8.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_stage_value.png"), dpi=150)
    plt.close(fig)


def fig_horizon_error(rep):
    p80 = rep["horizon_error_p80_kW"]
    hrs = np.arange(1, 25)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]
    for s in range(4):
        arr = [v if v is not None else np.nan for v in p80[str(s)]]
        ax.plot(hrs, arr, "o-", lw=1.6, color=colors[s],
                label=f"Forecast issued at {6*s}:00")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("Look-ahead horizon (h)")
    ax.set_ylabel("80th pct PV overestimate (kW)")
    ax.set_title("PV forecast error grows with horizon (per issue time)")
    ax.legend(fontsize=8.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_horizon_error.png"), dpi=150)
    plt.close(fig)


def fig_perturbation(rep):
    pert = rep["perturbation"]
    base = pert["base"]["total"]
    names = ["load+5%", "load-5%", "pv+5%", "pv-5%"]
    vals = [pert[n]["total"] for n in names]
    d = [v - base for v in vals]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    y = np.arange(len(names))
    ax.barh(y, d, color=["#d62728" if x > 0 else "#2ca02c" for x in d], alpha=0.85)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("Change in total cost vs base (yuan)")
    ax.set_title("Robustness to ±5% load / PV perturbation")
    for i, x in enumerate(d):
        ax.annotate(f"{x:+,.0f}", (x, i), textcoords="offset points",
                    xytext=(4 if x >= 0 else -4, 0), ha="left" if x >= 0 else "right",
                    va="center", fontsize=8.5)
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_perturbation.png"), dpi=150)
    plt.close(fig)


def fig_model_schematic():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.axis("off")
    # 时间轴
    ax.annotate("", xy=(1.0, 0.30), xytext=(0.0, 0.30),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#333"))
    for t, lab in [(0.0, "0:00"), (0.25, "6:00"), (0.5, "12:00"), (0.75, "18:00"), (1.0, "24:00")]:
        ax.plot([t], [0.30], "k|", markersize=10)
        ax.text(t, 0.22, lab, ha="center", fontsize=9)

    boxes = [
        (0.0, 0.62, "0:00 plan x\n(daily LP, 0:00 forecast)\nterminal E(144)=E(0)=6000"),
        (0.25, 0.62, "6:00 adjust y\n(stage LP on [6:00,24:00))\n6:00 forecast - δ[6:00]"),
        (0.5, 0.62, "12:00 adjust y\n(stage LP on [12:00,24:00))\n12:00 forecast - δ[12:00]"),
        (0.75, 0.62, "18:00 adjust y\n(stage LP on [18:00,24:00))\n18:00 forecast - δ[18:00]"),
    ]
    for x, y, txt in boxes:
        ax.text(x, y, txt, ha="center", va="center", fontsize=7.8,
                bbox=dict(boxstyle="round,pad=0.45", fc="#e8f0fe", ec="#1f77b4"))

    # 结算框
    ax.text(0.5, 0.86, "Settlement: p·min(x,y) + 0.5p·max(x−y,0) + 1.5p·max(y−x,0) + 5p·z   "
                       "|   Ĝ_safe = clip0(Ĝ − δ[issue]),  δ[s]=P80(overestimate)",
            ha="center", va="center", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.45", fc="#fdecea", ec="#d62728"))

    # 箭头: 计划 -> 调整
    for x0, x1 in [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75)]:
        ax.annotate("", xy=(x1 - 0.015, 0.30), xytext=(x0 + 0.015, 0.30),
                    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.2))
    ax.set_title("Q3 rolling-horizon MPC: 0:00 plan + 6/12/18 adjustment + daily energy closure",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_model_schematic.png"), dpi=150)
    plt.close(fig)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    rep = load_report()
    fig_quantile_sweep(rep)
    fig_stage_value(rep)
    fig_horizon_error(rep)
    fig_perturbation(rep)
    fig_model_schematic()
    print("FIGURES DONE ->", FIG_DIR)


if __name__ == "__main__":
    main()
