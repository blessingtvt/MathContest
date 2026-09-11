# -*- coding: utf-8 -*-
"""Q4 图表生成 (math-figure-generator) —— 读取冻结/稳健性 JSON, 渲染 3 张论文图。

图1 (Type 3 论文): 5 组方案总成本柱状对比 (诊断下界/对照/主模型/基线)。
图2 (Type 3 论文): 成本瀑布分解 (理论最优 + 日闭合约束成本 + 预报误差附加成本)。
图3 (Type 3 论文): 风险分位 q 灵敏度曲线 (result4-2 / result4-3)。

输出: paper/figures/fig_q4_*.png (300 dpi) + .svg
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(ROOT, "results", "Q4", "experiments", "round2", "run_summary.json")
ROB = os.path.join(ROOT, "robustness", "Q4", "q4_robustness_summary.json")
FIGDIR = os.path.join(ROOT, "paper", "figures")

P = {
    "primary": "#1A6FC4", "primary_light": "#5B9BD5", "primary_pale": "#B4D4F0",
    "baseline": "#767676", "baseline_light": "#A8A8A8", "baseline_pale": "#D8D8D8",
    "positive": "#2E9E44", "negative": "#E53935",
    "accent1": "#E28E2C", "accent2": "#7B5FD6", "accent3": "#33B5A5",
}
WAN = 1e4  # 万元


def load():
    run = json.load(open(RUN, encoding="utf-8"))
    rob = json.load(open(ROB, encoding="utf-8"))
    return run, rob


def style_ax(ax):
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.tick_params(labelsize=9)


def fig1(run):
    """5 组方案总成本柱状对比 (万元)。"""
    d = run["diagnostics"]
    b = {x["id"]: x["objective_value"] for x in run["baselines"]}
    A = next(x for x in d if x["id"] == "A")["objective_value"]
    Bv = next(x for x in d if x["id"] == "B")["objective_value"]
    r42 = run["result4_2"]["objective_value"]
    b4 = b["B4"]; b4ref = b["B4_ref"]

    names = ["B\n(储能·完美\n自由结转)", "A\n(储能·完美\n日闭合)", "M4(result4-2)\n(储能·自预报)",
             "B4_ref\n(无储能·完美)", "B4\n(无储能·自预报)"]
    vals = [Bv, A, r42, b4ref, b4]
    colors = [P["primary_pale"], P["primary_light"], P["primary"],
              P["baseline_light"], P["baseline"]]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    bars = ax.bar(range(5), [v / WAN for v in vals], color=colors,
                  edgecolor="white", linewidth=0.8, width=0.62)
    for i, (bar, v) in enumerate(zip(bars, vals)):
        ax.text(bar.get_x() + bar.get_width() / 2, v / WAN + 15,
                f"{v/WAN:,.1f}", ha="center", fontsize=8.5, fontweight="bold",
                color="#333333" if i != 2 else P["primary"])
    ax.set_xticks(range(5)); ax.set_xticklabels(names, fontsize=8.5)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_ylim(0, max(vals) / WAN * 1.16)
    ax.set_title("波动电价下各方案总购电费对比 (Q4)", fontsize=11, fontweight="bold")
    # 图例: 主模型/可执行基线/诊断基准
    import matplotlib.patches as mpatches
    lg = [mpatches.Patch(color=P["primary"], label="主模型 M4 (可执行)"),
          mpatches.Patch(color=P["baseline"], label="基线 B4 (可执行)"),
          mpatches.Patch(color=P["primary_light"], label="储能·完美预见 (诊断基准)"),
          mpatches.Patch(color=P["baseline_light"], label="无储能·完美预见 (诊断基准)")]
    ax.legend(handles=lg, fontsize=8, loc="upper left", frameon=False)
    style_ax(ax)
    fig.tight_layout()
    return fig


def fig2(run):
    """成本瀑布分解 (万元): B → +日闭合 → +预报误差 → result4-2。"""
    m = run["metrics"]["result4_2"]
    Bv = next(x for x in run["diagnostics"] if x["id"] == "B")["objective_value"]
    dayc = m["日闭合约束成本_元"]
    fc = m["预报误差成本_储能侧_元"]
    total = run["result4_2"]["objective_value"]

    labels = ["理论最优下界 B\n(储能·完美·自由结转)", "日闭合约束成本", "预报误差附加成本", "实际 result4-2\n(储能·自预报)"]
    # 瀑布: 累积
    bottoms = [0, Bv, Bv + dayc, 0]
    heights = [Bv, dayc, fc, total]
    colors = [P["primary_pale"], P["accent3"], P["negative"], P["primary"]]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for i in range(4):
        ax.bar(i, heights[i] / WAN, bottom=bottoms[i] / WAN, color=colors[i],
               edgecolor="white", linewidth=0.8, width=0.55, zorder=3)
    # 连接虚线
    for i in range(3):
        x0, x1 = i, i + 1
        y = (bottoms[i] + heights[i]) / WAN
        ax.plot([x0 + 0.275, x1 - 0.275], [y, y], color="#999999", linestyle="--", linewidth=1)
    # 数值标注
    for i in range(4):
        top = (bottoms[i] + heights[i]) / WAN
        ax.text(i, top + 8, f"{heights[i]/WAN:,.1f}", ha="center", fontsize=8.5, fontweight="bold",
                color="#333333" if i != 3 else P["primary"])
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_ylim(0, total / WAN * 1.2)
    ax.set_title("result4-2 成本结构分解：预报误差是主要附加成本", fontsize=11, fontweight="bold")
    style_ax(ax)
    fig.tight_layout()
    return fig


def fig3(rob):
    """风险分位 q 灵敏度曲线。"""
    r1 = rob["R1_quantile_sweep"]
    q42 = r1["result4_2_total_by_q"]; q43 = r1["result4_3_total_by_q"]
    qs = sorted(int(k) for k in q42)
    v42 = [q42[str(q)] / WAN for q in qs]
    v43 = [q43[str(q)] / WAN for q in qs]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(qs, v42, color=P["primary"], linewidth=2, marker="o", markersize=5, label="result4-2 (星期分位修正)")
    ax.plot(qs, v43, color=P["accent1"], linewidth=2, marker="s", markersize=5, label="result4-3 (issue分位修正)")
    ax.axvline(x=80, color="#999999", linestyle="--", linewidth=1)
    ax.text(80.5, ax.get_ylim()[0], "q=80 (设计值)", fontsize=8, color="#606060", va="bottom")
    ax.set_xlabel("风险修正分位 q (%)", fontsize=10)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10)
    ax.set_title("风险分位 q 灵敏度：q=80 近最优", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9, frameon=False, loc="center right")
    style_ax(ax)
    fig.tight_layout()
    return fig


def save(fig, name):
    fig.savefig(os.path.join(FIGDIR, f"{name}.png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.svg"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    run, rob = load()
    save(fig1(run), "fig_q4_1_cost_comparison")
    save(fig2(run), "fig_q4_2_cost_decomposition")
    save(fig3(rob), "fig_q4_3_quantile_sensitivity")
    print("done")


if __name__ == "__main__":
    main()
