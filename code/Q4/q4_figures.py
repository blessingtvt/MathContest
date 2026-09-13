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
import matplotlib.patches as mpatches
import numpy as np

# ==================== 出版级全局样式 ====================
plt.rcParams["font.sans-serif"]      = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["font.family"]          = "sans-serif"
plt.rcParams["axes.unicode_minus"]   = False
plt.rcParams["svg.fonttype"]         = "path"     # 文字转路径：避免 SVG 中文字体缺失

plt.rcParams["axes.linewidth"]       = 1.0
plt.rcParams["axes.edgecolor"]       = "#3A4550"
plt.rcParams["axes.labelcolor"]      = "#1A2530"
plt.rcParams["axes.labelsize"]       = 10.5
plt.rcParams["axes.titlesize"]       = 11.5
plt.rcParams["axes.titleweight"]     = "bold"
plt.rcParams["axes.titlecolor"]      = "#0F1A26"

plt.rcParams["xtick.direction"]      = "in"
plt.rcParams["ytick.direction"]      = "in"
plt.rcParams["xtick.color"]          = "#3A4550"
plt.rcParams["ytick.color"]          = "#3A4550"
plt.rcParams["xtick.labelsize"]      = 9.5
plt.rcParams["ytick.labelsize"]      = 9.5
plt.rcParams["xtick.major.size"]     = 3.6
plt.rcParams["ytick.major.size"]     = 3.6
plt.rcParams["xtick.major.width"]    = 1.0
plt.rcParams["ytick.major.width"]    = 1.0

plt.rcParams["legend.frameon"]       = False
plt.rcParams["legend.fontsize"]      = 8.5
plt.rcParams["legend.handlelength"]  = 1.4
plt.rcParams["legend.labelspacing"]  = 0.35
plt.rcParams["legend.columnspacing"] = 1.2

plt.rcParams["figure.facecolor"]     = "white"
plt.rcParams["savefig.facecolor"]    = "white"

ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN    = os.path.join(ROOT, "results", "Q4", "experiments", "round3", "run_summary.json")
ROB    = os.path.join(ROOT, "robustness", "Q4", "q4_robustness_summary.json")
E44    = os.path.join(ROOT, "results", "Q4", "experiments", "optimization", "e44_quantile_sweep.json")
FIGDIR = os.path.join(ROOT, "paper", "figures")

# ==================== 配色：优雅冷调 + 暖色点缀 ====================
# 主模型 → 深海军蓝；诊断基准 → 冷灰蓝；基线 → 中性灰；增益/损失 → 森林绿 / 深砖红
P = {
    # 主色系（由浅至深）
    "primary_pale":  "#C9DCEF",
    "primary_light": "#8DB4D9",
    "primary":       "#2F6EA5",
    "primary_deep":  "#1B4A78",

    # 基线灰系
    "baseline_pale":  "#D9DEE3",
    "baseline_light": "#B5BCC4",
    "baseline":       "#7C858E",

    # 语义色
    "positive":  "#2E8B57",     # 森林绿（正向成本节约）
    "negative":  "#C0392B",     # 深砖红（附加成本）
    "accent1":   "#D08A3E",     # 暗橙（result4-3）
    "accent2":   "#7B5FD6",     # 紫（备用）
    "accent3":   "#3AAE9E",     # 青绿（日闭合成本）
    "marker":    "#2F6EA5",     # 参考线
    "ref":       "#8A939B",     # 灰色参考线
}
WAN = 1e4  # 万元


def load():
    run = json.load(open(RUN, encoding="utf-8"))
    rob = json.load(open(ROB, encoding="utf-8"))
    e44 = json.load(open(E44, encoding="utf-8"))
    return run, rob, e44


def style_ax(ax):
    """统一的出版级坐标轴样式：去上/右边框、刻度朝内、弱化网格。"""
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_color("#3A4550")
    ax.spines["bottom"].set_color("#3A4550")
    ax.tick_params(labelsize=9.5, colors="#3A4550", width=1.0)
    ax.grid(True, axis="y", color="#E2E7EC", lw=0.75, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)


def _gradient_bar(ax, xc, height, width, c_bottom, c_top, bottom=0.0,
                  n=64, zorder=3):
    """垂直渐变柱体：用 n 条水平细条模拟，保持矢量，不位图化。"""
    import matplotlib.colors as mcolors
    from matplotlib.patches import Rectangle
    c0 = np.array(mcolors.to_rgb(c_bottom))
    c1 = np.array(mcolors.to_rgb(c_top))
    ys = np.linspace(bottom, bottom + height, n + 1)
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        col = tuple(c0 * (1 - t) + c1 * t)
        ax.add_patch(Rectangle(
            (xc - width / 2.0, ys[i]),
            width, ys[i + 1] - ys[i],
            facecolor=col, edgecolor="none", linewidth=0,
            zorder=zorder, antialiased=False,
        ))


# ============================================================
# Fig 1 · 5 组方案总成本柱状对比
# ============================================================
def fig1(run):
    d   = run["diagnostics"]
    b   = {x["id"]: x["objective_value"] for x in run["baselines"]}
    A   = next(x for x in d if x["id"] == "A")["objective_value"]
    Bv  = next(x for x in d if x["id"] == "B")["objective_value"]
    r42 = run["result4_2"]["objective_value"]
    b4    = b["B4"]
    b4ref = b["B4_ref"]

    names  = ["B\n(储能·完美\n自由结转)", "A\n(储能·完美\n日闭合)",
              "M4(result4-2)\n(储能·自预报)",
              "B4_ref\n(无储能·完美)", "B4\n(无储能·自预报)"]
    vals   = [Bv, A, r42, b4ref, b4]

    # 每根柱 (底, 顶) 渐变：主模型最深，诊断基准次之，基线为灰
    grads = [
        (P["primary_pale"],  "#E4EDF6"),   # B：极浅蓝
        (P["primary_light"], P["primary_pale"]),  # A：浅蓝
        (P["primary_deep"],  P["primary"]),       # M4：深海军蓝（视觉焦点）
        (P["baseline_light"], P["baseline_pale"]),# B4_ref：浅灰
        (P["baseline"],       P["baseline_light"]),# B4：深灰
    ]

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.set_ylim(0, max(vals) / WAN * 1.18)
    ax.set_xlim(-0.6, 4.6)

    W = 0.62
    for i, v in enumerate(vals):
        c_b, c_t = grads[i]
        _gradient_bar(ax, i, v / WAN, W, c_b, c_t, n=64, zorder=3)

    # 数值标签
    for i, v in enumerate(vals):
        is_hero = (i == 2)
        ax.text(i, v / WAN + max(vals) / WAN * 0.02,
                f"{v/WAN:,.1f}",
                ha="center", va="bottom",
                fontsize=9.5 if is_hero else 9.0,
                fontweight="bold",
                color=P["primary_deep"] if is_hero else "#2B333B",
                zorder=6)

    ax.set_xticks(range(5))
    ax.set_xticklabels(names, fontsize=8.8, color="#2B333B")
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10.5)
    ax.set_title("波动电价下各方案总购电费对比 (Q4)",
                 fontsize=11.5, fontweight="bold", pad=10)

    # 图例：用渐变色块示意
    lg = [
        mpatches.Patch(facecolor=P["primary_deep"],  edgecolor="none",
                       label="主模型 M4 (可执行)"),
        mpatches.Patch(facecolor=P["baseline"],      edgecolor="none",
                       label="基线 B4 (可执行)"),
        mpatches.Patch(facecolor=P["primary_light"], edgecolor="none",
                       label="储能·完美预见 (诊断基准)"),
        mpatches.Patch(facecolor=P["baseline_light"], edgecolor="none",
                       label="无储能·完美预见 (诊断基准)"),
    ]
    ax.legend(handles=lg, fontsize=8.4, loc="upper left",
              borderaxespad=0.7)

    style_ax(ax)
    fig.tight_layout()
    return fig


# ============================================================
# Fig 2 · 成本瀑布分解
# ============================================================
def fig2(run):
    m     = run["metrics"]["result4_2"]
    Bv    = next(x for x in run["diagnostics"] if x["id"] == "B")["objective_value"]
    dayc  = m["日闭合约束成本_元"]
    fc    = m["预报误差成本_储能侧_元"]
    total = run["result4_2"]["objective_value"]

    labels = ["理论最优下界 B\n(储能·完美·自由结转)",
              "日闭合约束成本",
              "预报误差附加成本",
              "实际 result4-2\n(储能·自预报)"]
    bottoms = [0, Bv, Bv + dayc, 0]
    heights = [Bv, dayc, fc, total]

    # 每根柱 (底, 顶) 渐变，语义色系
    grads = [
        (P["primary_pale"],  "#E4EDF6"),        # 下界：极浅蓝
        ("#BFE6DC",          P["accent3"]),     # 日闭合：青绿
        ("#F1B5AD",          P["negative"]),    # 预报误差：砖红
        (P["primary_deep"],  P["primary"]),     # 实际：深蓝
    ]

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(0, total / WAN * 1.22)

    W = 0.55
    for i in range(4):
        c_b, c_t = grads[i]
        _gradient_bar(ax, i, heights[i] / WAN, W, c_b, c_t,
                      bottom=bottoms[i] / WAN, n=64, zorder=3)

    # 连接虚线
    for i in range(3):
        x0, x1 = i, i + 1
        y = (bottoms[i] + heights[i]) / WAN
        ax.plot([x0 + 0.275, x1 - 0.275], [y, y],
                color="#9AA0A6", linestyle=(0, (5, 3)),
                linewidth=1.1, zorder=4)

    # 数值标签
    for i in range(4):
        top = (bottoms[i] + heights[i]) / WAN
        is_hero = (i == 3)
        ax.text(i, top + total / WAN * 0.015,
                f"{heights[i]/WAN:,.1f}",
                ha="center", va="bottom",
                fontsize=9.5 if is_hero else 9.0,
                fontweight="bold",
                color=P["primary_deep"] if is_hero else "#2B333B",
                zorder=6)

    ax.set_xticks(range(4))
    ax.set_xticklabels(labels, fontsize=8.8, color="#2B333B")
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10.5)
    ax.set_title("result4-2 成本结构分解：预报误差是主要附加成本",
                 fontsize=11.5, fontweight="bold", pad=10)

    style_ax(ax)
    fig.tight_layout()
    return fig


# ============================================================
# Fig 3 · 风险分位 q 灵敏度曲线
# ============================================================
def fig3(rob, e44):
    r1   = rob["R1_quantile_sweep"]
    q42  = r1["result4_2_total_by_q"]
    qs42 = sorted(int(k) for k in q42 if int(k) >= 50)
    v42  = [q42[str(q)] / WAN for q in qs42]

    sweep = e44["q_sweep"]
    qs43  = sorted(int(k) for k in sweep)
    v43   = [sweep[str(q)]["total"] / WAN for q in qs43]

    fig, ax = plt.subplots(figsize=(7.6, 4.8))

    # —— 曲线下方浅色填充，视觉上区分两条线 ——
    ax.fill_between(qs42, v42, min(v42) * 0.985,
                    color=P["primary"], alpha=0.08, lw=0, zorder=1)
    ax.fill_between(qs43, v43, min(v43) * 0.985,
                    color=P["accent1"], alpha=0.08, lw=0, zorder=1)

    # —— 两条曲线 ——
    ax.plot(qs42, v42, color=P["primary"], linewidth=2.2,
            marker="o", markersize=6.5,
            markeredgecolor="white", markeredgewidth=1.2,
            label="result4-2 (星期分位修正)", zorder=5)
    ax.plot(qs43, v43, color=P["accent1"], linewidth=2.2,
            marker="s", markersize=6.5,
            markeredgecolor="white", markeredgewidth=1.2,
            label="result4-3 (块级分位修正)", zorder=5)

    # —— 参考竖线 ——
    ax.axvline(x=80, color=P["ref"], linestyle=(0, (5, 3)),
               linewidth=1.2, zorder=2)
    ax.axvline(x=e44["argmin_q"], color=P["accent1"], linestyle=":",
               linewidth=1.4, zorder=2)

    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    ax.text(80.6, ymin + 0.03 * span, "q=80\n(设计值)",
            fontsize=8.4, color="#606060", va="bottom",
            fontweight="bold")
    ax.text(e44["argmin_q"] + 0.4, ymin + 0.03 * span,
            f"q={e44['argmin_q']}\n(result4-3 argmin)",
            fontsize=8.4, color=P["accent1"], va="bottom",
            fontweight="bold")

    ax.set_xlabel("风险修正分位 q (%)", fontsize=10.5)
    ax.set_ylabel("报告期总购电费 (万元)", fontsize=10.5)
    ax.set_title("风险分位 q 灵敏度：q=80 设计值近最优",
                 fontsize=11.5, fontweight="bold", pad=10)

    ax.legend(fontsize=9.0, loc="center right", borderaxespad=0.8)

    style_ax(ax)
    fig.tight_layout()
    return fig


def save(fig, name):
    fig.savefig(os.path.join(FIGDIR, f"{name}.png"),
                dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.svg"),
                bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    run, rob, e44 = load()
    save(fig1(run), "fig_q4_1_cost_comparison")
    save(fig2(run), "fig_q4_2_cost_decomposition")
    save(fig3(rob, e44), "fig_q4_3_quantile_sensitivity")
    print("done")


if __name__ == "__main__":
    main()