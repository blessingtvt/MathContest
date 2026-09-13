# -*- coding: utf-8 -*-
"""
Q3 调整时刻边际价值消融柱状图  ——  fig_q3_4_adjust_ablation.svg + .png

论文位置：§4.6「是否需要引入其他预报时刻」图下方。
核心结论：随纳入的调整时刻增加，报告期总购电费递减但边际节省骤降，
          18:00 调整的边际节省仅 1.28 元（≈0），故无需引入更多预报时刻。

数据源（只读，全部数值从磁盘读取并交叉校验，禁止编造）：
  - results/Q3/experiments/round4/robustness_report.json
        stage_ablation.{0, 0+6, 0+6+12, 0+6+12+18}.total   四组消融（仅0:00 / +6 / +12 / +18）
        perfect_forecast_upper_bound.total                  完美预见理论下界
  - results/Q3/reports/frozen_numbers.json
        baselines[id=B3].objective_value                    应 == 仅0:00
        objective.value                                     应 == +18:00

输出：
  paper/figures/fig_q3_4_adjust_ablation.svg   矢量（SimHei 中文字体）
  脚本同目录/fig_q3_4_adjust_ablation.png      300 dpi 位图
"""
import os
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np

# ---------------- 路径 ----------------
HERE = os.path.dirname(os.path.abspath(__file__))                 # code/scripts
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))            # 项目根目录
ROBUST_JSON = os.path.join(ROOT, "results", "Q3", "experiments", "round4", "robustness_report.json")
FROZEN_JSON = os.path.join(ROOT, "results", "Q3", "reports", "frozen_numbers.json")
OUT_SVG = os.path.join(ROOT, "paper", "figures", "fig_q3_4_adjust_ablation.svg")
OUT_PNG = os.path.join(HERE, "fig_q3_4_adjust_ablation.png")      # 当前目录（脚本所在目录）

# ---------------- 中文字体（SimHei） ----------------
_SIMHEI = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(_SIMHEI):
    font_manager.fontManager.addfont(_SIMHEI)
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "path"   # 文字转路径：SVG 无字体依赖、中文不乱码

# ---------------- 出版级全局排版（大字号、强对比） ----------------
matplotlib.rcParams["axes.linewidth"]    = 1.0
matplotlib.rcParams["axes.edgecolor"]    = "#3A4550"
matplotlib.rcParams["axes.labelcolor"]   = "#1A2530"
matplotlib.rcParams["axes.labelsize"]    = 12
matplotlib.rcParams["axes.titlesize"]    = 13.5
matplotlib.rcParams["axes.titleweight"]  = "bold"
matplotlib.rcParams["axes.titlecolor"]   = "#0F1A26"
matplotlib.rcParams["xtick.direction"]   = "in"
matplotlib.rcParams["ytick.direction"]   = "in"
matplotlib.rcParams["xtick.color"]       = "#3A4550"
matplotlib.rcParams["ytick.color"]       = "#3A4550"
matplotlib.rcParams["xtick.labelsize"]   = 11
matplotlib.rcParams["ytick.labelsize"]   = 11
matplotlib.rcParams["xtick.major.size"]  = 4.0
matplotlib.rcParams["ytick.major.size"]  = 4.0
matplotlib.rcParams["xtick.major.width"] = 1.0
matplotlib.rcParams["ytick.major.width"] = 1.0

# ============================================================
# 新配色：取自参考图的柔和粉彩系（浅橙 / 浅粉 / 浅青 / 浅蓝 / 浅紫）
#   每根柱子自下而上做垂直渐变，整体明快轻盈，避免重色。
# ============================================================
PALETTE = {
    # 渐变柱： (底部色, 顶部色)
    "baseline": ("#F9C780", "#F7C1C1"),   # 浅橙 → 浅粉（中性柔和）
    "method":   ("#AEDBD2", "#93C8ED"),   # 浅青 → 浅蓝（清新过渡）
    "hero":     ("#BC9CC8", "#93C8ED"),   # 浅紫 → 浅蓝（视觉焦点）

    "bound":    "#B03A2E",                 # 完美预见下界（柔和深红，与粉彩形成对比）
    "saving":   "#1E8449",                 # 边际节省（深森林绿，正向强调）
    "text":     "#1A2530",                 # 正文近黑
    "axis":     "#3A4550",                 # 坐标轴 / 刻度
    "grid":     "#E2E7EC",                 # 网格
    "bg":       "#FFFFFF",
}


def load_numbers():
    """读取四组消融与完美预见下界，并用 frozen_numbers 交叉校验端点。"""
    with open(ROBUST_JSON, "r", encoding="utf-8") as f:
        rob = json.load(f)
    with open(FROZEN_JSON, "r", encoding="utf-8") as f:
        fz = json.load(f)

    sa = rob["stage_ablation"]
    labels = ["仅 0:00 计划", "+ 6:00 调整", "+ 12:00 调整", "+ 18:00 调整"]
    vals = [
        float(sa["0"]["total"]),
        float(sa["0+6"]["total"]),
        float(sa["0+6+12"]["total"]),
        float(sa["0+6+12+18"]["total"]),
    ]
    bound = float(rob["perfect_forecast_upper_bound"]["total"])

    # 端点交叉校验：消融端点必须与 frozen_numbers 一致，否则中止（防口径漂移/编造）
    b3 = next(b["objective_value"] for b in fz["baselines"] if b["id"] == "B3")
    obj = float(fz["objective"]["value"])
    if abs(vals[0] - b3) > 0.01:
        raise ValueError(f"消融「仅0:00」={vals[0]} 与 frozen B3={b3} 不一致")
    if abs(vals[3] - obj) > 0.01:
        raise ValueError(f"消融「+18:00」={vals[3]} 与 frozen objective={obj} 不一致")

    return labels, vals, bound


def _fmt_wan(v, _):
    """Y 轴刻度：金额以「万元」显示（Y 轴标题已注明单位元）。"""
    return "0" if v == 0 else f"{v / 1e4:,.0f}万"


def _fmt_yuan(v):
    """柱顶数值：以元为单位、千分位、两位小数。"""
    return f"{v:,.2f}"


def gradient_bar(ax, xc, height, width, c_bottom, c_top, n=72, zorder=3):
    """用 n 条水平细条模拟垂直渐变柱体（保持矢量，不位图化）。"""
    c0 = np.array(mcolors.to_rgb(c_bottom))
    c1 = np.array(mcolors.to_rgb(c_top))
    ys = np.linspace(0.0, height, n + 1)
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        col = tuple(c0 * (1 - t) + c1 * t)
        ax.add_patch(Rectangle(
            (xc - width / 2.0, ys[i]),
            width, ys[i + 1] - ys[i],
            facecolor=col, edgecolor=col, linewidth=0.15,
            zorder=zorder, antialiased=False,
        ))


def build_figure():
    labels, vals, bound = load_numbers()
    # 边际节省 = 相对前一策略的降费（由读取值相减，非人工填写）
    savings = [vals[i - 1] - vals[i] for i in range(1, len(vals))]

    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    x = np.arange(len(vals))
    bar_colors = [PALETTE["baseline"], PALETTE["method"],
                  PALETTE["method"], PALETTE["hero"]]

    # —— 手动设置坐标范围（供渐变柱体定位用） ——
    ax.set_xlim(-0.55, 3.55)
    ax.set_ylim(0, max(vals) * 1.30)

    # —— 渐变柱体（柔和粉彩：底 → 顶） ——
    W = 0.58
    for i, v in enumerate(vals):
        c_bottom, c_top = bar_colors[i]
        gradient_bar(ax, x[i], v, W, c_bottom, c_top, n=72, zorder=3)

    # —— 完美预见理论下界（柔和深红虚线 + 白字反底标签） ——
    ax.axhline(bound, color=PALETTE["bound"], linestyle=(0, (7, 3.5)),
               linewidth=2.0, zorder=5)
    ax.text(
        0.985, bound, f" 完美预见理论下界  {bound / 1e4:,.2f} 万元 ",
        transform=ax.get_yaxis_transform(),
        ha="right", va="bottom", fontsize=10.5, fontweight="bold",
        color="white",
        bbox=dict(boxstyle="round,pad=0.42",
                  facecolor=PALETTE["bound"], edgecolor="none", alpha=0.96),
        zorder=20,
    )

    # —— 柱顶：总费用 + 边际节省（两层注释） ——
    top_gap_total  = 10
    top_gap_saving = 32

    for i, v in enumerate(vals):
        ax.annotate(_fmt_yuan(v) + " 元", (x[i], v),
                    textcoords="offset points", xytext=(0, top_gap_total),
                    ha="center", va="bottom", fontsize=11,
                    color=PALETTE["text"], fontweight="bold", zorder=6)

        if i == 0:
            ax.annotate("基线（无调整）", (x[i], v),
                        textcoords="offset points", xytext=(0, top_gap_saving),
                        ha="center", va="bottom", fontsize=10.5,
                        color="#6B7682", fontweight="bold", zorder=6)
        else:
            s = savings[i - 1]
            if i == 3:  # +18:00 调整，边际节省几乎为 0
                txt = "边际节省 {:.2f} 元（≈0）".format(s)
            else:
                txt = "边际节省 {:,.2f} 万元".format(s / 1e4)
            ax.annotate(txt, (x[i], v),
                        textcoords="offset points", xytext=(0, top_gap_saving),
                        ha="center", va="bottom", fontsize=10.5,
                        color=PALETTE["saving"], fontweight="bold", zorder=6)

    # —— 极简出版风 ——
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(PALETTE["axis"])
    ax.spines["bottom"].set_color(PALETTE["axis"])
    ax.tick_params(colors=PALETTE["axis"], width=1.0)
    ax.grid(True, axis="y", color=PALETTE["grid"], lw=0.8, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)
    ax.set_facecolor(PALETTE["bg"])

    # —— 轴与标签 ——
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11.5, color=PALETTE["text"], fontweight="bold")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_wan))
    ax.set_ylabel("报告期总购电费（元）", color=PALETTE["text"], labelpad=8)
    ax.set_xlabel("纳入的调整时刻",       color=PALETTE["text"], labelpad=8)
    ax.set_title("调整时刻的边际价值（消融）", color=PALETTE["text"], pad=14)

    fig.tight_layout()
    return fig, (labels, vals, savings, bound)


def main():
    fig, (labels, vals, savings, bound) = build_figure()

    # —— 输出矢量 SVG ——
    os.makedirs(os.path.dirname(OUT_SVG), exist_ok=True)
    fig.savefig(OUT_SVG, bbox_inches="tight", facecolor="white")

    # —— 输出 300 dpi 位图 PNG（脚本所在目录） ——
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print("已生成:", OUT_SVG)
    print("已生成:", OUT_PNG)
    print("四组消融总购电费（元）:")
    for lb, v in zip(labels, vals):
        print(f"  {lb:<10} = {v:,.2f}")
    print("边际节省（元）: 6:00={:,.2f}  12:00={:,.2f}  18:00={:.2f}".format(*savings))
    print("完美预见理论下界（元）: {:.2f}".format(bound))


if __name__ == "__main__":
    main()


# ================= 图注（正文，120–180 字，置于图下方） =================
#
# 图 X　调整时刻边际价值消融。报告期总购电费由仅 0:00 计划的 1,729.11 万元降至纳入
# 6:00 调整后的 1,451.17 万元，边际节省 277.94 万元；继续纳入 12:00、18:00 调整，
# 边际节省骤降至 46.17 万元与 1.28 元。边际收益随调整时刻增加快速递减，18:00 调整
# 的降费几乎为零，表明 0/6/12 三时刻已基本耗尽预报信息价值，无需引入更多预报时刻。