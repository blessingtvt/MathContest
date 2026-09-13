# -*- coding: utf-8 -*-
"""
总体技术路线图（Our Work / 四问递进的建模与求解框架）—— fig_0_framework.png / .svg

论文位置：§2.1 整体分析（问题分析开头），一张图讲清「四问共享什么、各自新增什么、用什么解、产出什么」。
五层纵向流水线：
  输入层 → 信息处理层 → 建模内核 → 四问递进 → 求解输出层

配色：柔和低饱和和谐色系（与 q3_plots.py 一致）——灰/琥珀/蓝/深蓝/青。
输出：paper/figures/fig_0_framework.png（300 dpi）+ fig_0_framework.svg（矢量）。
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_PNG = os.path.join(ROOT, "paper", "figures", "fig_0_framework.png")
OUT_SVG = os.path.join(ROOT, "paper", "figures", "fig_0_framework.svg")

# ---------------- 中文字体（SimHei） ----------------
_SIMHEI = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(_SIMHEI):
    font_manager.fontManager.addfont(_SIMHEI)
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["svg.fonttype"] = "path"

# ---------------- 柔和低饱和和谐配色 ----------------
C = dict(
    gray="#9A9A9A", gray_fill="#F1F1F1",
    amber="#E0B878", amber_fill="#F7EBD5",
    blue="#6E9BC9", blue_fill="#E7F0F8",
    blue_deep="#4A7FB5", blue_deep_fill="#E3EDF7",
    teal="#7FBFA8", teal_fill="#E6F4EE",
    text="#333333", axis="#606060", arrow="#ABABAB", white="#FFFFFF",
)


def box(ax, x, y, w, h, fc, ec=None, lw=1.2, rounding=0.22, zorder=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size={}".format(rounding),
        facecolor=fc, edgecolor=(ec if ec else fc), linewidth=lw, zorder=zorder))


def txt(ax, x, y, s, size=9, color=None, weight="normal", ha="center", va="center", zorder=5):
    ax.text(x, y, s, fontsize=size, color=(color or C["text"]), fontweight=weight,
            ha=ha, va=va, zorder=zorder)


def arrow(ax, x1, y1, x2, y2, color=None, lw=1.6):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=(color or C["arrow"]), lw=lw,
                                mutation_scale=16, shrinkA=0, shrinkB=0))


def sub_box(ax, x, ybot, ytop, w, lines, ec, lw=1.1):
    """一个子模块圆角盒：白色填充、彩色描边，内部 n 行文字（每行 (text,size,weight)）。"""
    box(ax, x, ybot, w, ytop - ybot, C["white"], ec, lw=lw)
    n = len(lines)
    step = (ytop - ybot) / (n + 1)
    for i, ln in enumerate(lines):
        s, sz, wt = ln
        txt(ax, x + w / 2, ytop - (i + 1) * step, s, size=sz, weight=wt)


def grid_xs(n, x0=2.15, x1=11.25, gap=0.2):
    w = (x1 - x0 - (n - 1) * gap) / n
    return [x0 + i * (w + gap) for i in range(n)], w


def build_figure():
    fig, ax = plt.subplots(figsize=(10, 8.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(7.0, 16.2)
    ax.axis("off")

    txt(ax, 6.0, 16.02, "总体技术路线（四问递进的建模与求解框架）", size=13.5, weight="bold")

    BX0, BX1 = 0.6, 11.4          # 整层横跨范围
    TAG_X, TAG_W = 0.7, 1.25      # 左侧层名标签
    TAG_H = 0.62

    def band(name, ybot, ytop, fill, edge):
        """绘制一整层：浅色底 + 左侧层名标签。"""
        box(ax, BX0, ybot, BX1 - BX0, ytop - ybot, fill, edge, lw=1.3)
        yc = (ybot + ytop) / 2
        box(ax, TAG_X, yc - TAG_H / 2, TAG_W, TAG_H, edge)
        txt(ax, TAG_X + TAG_W / 2, yc, name, size=9, color=C["white"], weight="bold")

    # ---------------- 第 1 层：输入层 ----------------
    band("输入层", 14.45, 15.75, C["gray_fill"], C["gray"])
    xs, w = grid_xs(4)
    inputs = [
        [("附件1", 9, "bold"), ("恒定电价 $p_t$", 8, "normal")],
        [("附件2", 9, "bold"), ("负载 $L$ · 光伏 $G$", 8, "normal")],
        [("附件3", 9, "bold"), ("光伏预报 $\\hat{G}$", 8, "normal")],
        [("附件4", 9, "bold"), ("波动电价 $p_{d,t}$", 8, "normal")],
    ]
    for x, lines in zip(xs, inputs):
        sub_box(ax, x, 14.55, 15.65, w, lines, C["gray"])

    # ---------------- 第 2 层：信息处理层 ----------------
    band("信息处理", 12.85, 14.15, C["amber_fill"], C["amber"])
    xs, w = grid_xs(2)
    proc = [
        [("净负荷自预报 $\\hat{N}_{d,t}$", 9, "bold"), ("附件2历史 · 7天加权 · 星期分桶", 8, "normal")],
        [("区间级风险修正 $\\delta=P_{80}$", 9, "bold"), ("报童临界比 $q^*=0.8$", 8, "normal")],
    ]
    for x, lines in zip(xs, proc):
        sub_box(ax, x, 12.95, 14.05, w, lines, C["amber"])

    # ---------------- 第 3 层：建模内核 ----------------
    band("建模内核", 11.25, 12.55, C["blue_fill"], C["blue"])
    xs, w = grid_xs(4)
    kernel = [
        [("能量平衡", 9, "bold"), ("供电 ≥ 负载需求", 8, "normal")],
        [("储能动态", 9, "bold"), ("边界 + 日闭合", 8, "normal")],
        [("计费规则", 9, "bold"), ("计划·违约·溢价·紧急", 8, "normal")],
        [("储能参数", 9, "bold"), ("$C,E,P,\\eta$（附录1）", 8, "normal")],
    ]
    for x, lines in zip(xs, kernel):
        sub_box(ax, x, 11.35, 12.45, w, lines, C["blue"])

    # ---------------- 第 4 层：四问递进 ----------------
    band("四问递进", 8.95, 10.95, C["blue_deep_fill"], C["blue_deep"])
    xs, w = grid_xs(4)
    quests = [
        [("问题一", 9.5, "bold"), ("确定条件", 8.5, "normal"), ("静态 LP", 8.5, "bold")],
        [("问题二", 9.5, "bold"), ("逐日滚动", 8.5, "normal"), ("滚动 LP + 报童修正", 8.5, "bold")],
        [("问题三", 9.5, "bold"), ("滚动预报", 8.5, "normal"), ("滚动 MPC + 分段计费", 8.5, "bold")],
        [("问题四", 9.5, "bold"), ("波动电价", 8.5, "normal"), ("复用 Q2/Q3 框架", 8.5, "bold")],
    ]
    for x, lines in zip(xs, quests):
        sub_box(ax, x, 9.05, 10.85, w, lines, C["blue_deep"])

    # ---------------- 第 5 层：求解输出层（拆为 4 个流水盒子） ----------------
    band("求解输出", 7.25, 8.55, C["teal_fill"], C["teal"])
    xs, w = grid_xs(4)
    outputs = [
        [("HiGHS 求解", 8.5, "bold"), ("线性规划求解器", 7.2, "normal")],
        [("result1~4.xlsx", 8.5, "bold"), ("结果文件", 7.2, "normal")],
        [("答案表 1/2/3", 8.5, "bold"), ("提交答案", 7.2, "normal")],
        [("稳健性 / 敏感性", 8.5, "bold"), ("验证", 7.2, "normal")],
    ]
    for x, lines in zip(xs, outputs):
        sub_box(ax, x, 7.35, 8.45, w, lines, C["teal"])

    # ---------------- 层间箭头（居中） ----------------
    for y1, y2 in [(14.45, 14.15), (12.85, 12.55), (11.25, 10.95), (8.95, 8.55)]:
        arrow(ax, 6.0, y1, 6.0, y2)

    fig.tight_layout()
    return fig


def main():
    fig = build_figure()
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_SVG, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("已生成:", OUT_PNG)
    print("已生成:", OUT_SVG)


if __name__ == "__main__":
    main()
