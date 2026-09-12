# -*- coding: utf-8 -*-
"""Q3 论文图生成（round4 块级，柔和低饱和配色 + 白底极简风格）。

配色方案（从参考图学习）：白底 #FFFFFF + 低饱和高亮度的柔和色调——
  蓝 #6E9BC9(主模型)、珊瑚红 #E08E8E(紧急/负向)、琥珀 #E0B878(溢价/次级)、青 #7FBFA8(弃光/正向)，
  基线用中性灰，网格/边框极淡。仅输出 PNG(300dpi)，不输出 SVG。

图清单:
  fig_q3_1  滚动 MPC 机制示意图（柔和配色）
  fig_q3_2  典型日 计划购电 vs 调整购电
  fig_q3_3  全年总购电费 主模型 vs 基线
  fig_q3_4  调整时刻边际价值
  fig_q3_5  分位敏感性 × 成本分解（计划/溢价/紧急 堆叠 + 总费用）   [增强]
  fig_q3_6  负荷/光伏 ±5% 扰动
  fig_q3_7  光伏预报误差-前瞻时域
  fig_q3_8  光伏风险修正量 δ[s,t] 热图（建模分析）                    [新增]
  fig_q3_9  典型日储能 SOC 轨迹（结果验证）                          [新增]
输出: paper/figures/*.png（并复制到 results/Q3/figures/）
"""
import os, sys, json, warnings
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # code/Q3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # code
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import openpyxl
from common import RESULTS_DIR, ROOT, load_bundle, E0_INIT, EMIN, EMAX
import q3_new_methods.q3_optimized as qopt

# ---- 中文字体 ----
_FONT_OK = False
for _fn in ("Microsoft YaHei", "SimHei"):
    _names = {f.name for f in font_manager.fontManager.ttflist}
    if _fn in _names:
        matplotlib.rcParams["font.sans-serif"] = [_fn, "SimHei", "DejaVu Sans"]
        matplotlib.rcParams["font.family"] = "sans-serif"
        _FONT_OK = True
        _FONT_NAME = _fn
        break
matplotlib.rcParams["axes.unicode_minus"] = False

# ---- 配色系统（柔和低饱和，白底极简）----
PALETTE = {
    "blue": "#6E9BC9",        # 主模型 / 计划购电
    "blue_deep": "#4A7FB5",   # 主模型线（更深）
    "blue_fill": "#A9C7E3",   # 主模型浅填充
    "coral": "#E08E8E",       # 紧急购电 / 负向
    "coral_fill": "#F0B8B8",
    "amber": "#E0B878",       # 溢价 / 次级
    "amber_fill": "#EED0A8",
    "teal": "#7FBFA8",        # 弃光 / 正向
    "teal_fill": "#B0DCCB",
    "gray": "#9A9A9A",        # 基线
    "gray_light": "#C9C9C9",
    "text": "#3A3A3A",
    "axis": "#8A8A8A",
    "grid": "#E6E6E6",
    "bg": "#FFFFFF",
}

FIG_DIR = os.path.join(ROOT, "paper", "figures")
EXP_DIR = os.path.join(RESULTS_DIR, "Q3", "experiments", "round4")
RENDER_WARNINGS = []


def _load_robustness():
    with open(os.path.join(EXP_DIR, "robustness_report.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_frozen():
    with open(os.path.join(RESULTS_DIR, "Q3", "reports", "frozen_numbers.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_quantile_decomp():
    with open(os.path.join(EXP_DIR, "quantile_decomp.json"), "r", encoding="utf-8") as f:
        return json.load(f)["quantiles"]


def _style_axis(ax):
    """极简白底：去上/右边框，淡网格，灰轴。"""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(PALETTE["axis"])
    ax.spines["bottom"].set_color(PALETTE["axis"])
    ax.tick_params(colors=PALETTE["axis"])
    ax.grid(True, color=PALETTE["grid"], lw=0.7, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_facecolor(PALETTE["bg"])


def _save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        png = os.path.join(FIG_DIR, name + ".png")
        fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
        for wi in w:
            if "Glyph" in str(wi.message) or "missing" in str(wi.message).lower():
                RENDER_WARNINGS.append(f"{name}: {wi.message}")
    plt.close(fig)
    return png


# ======================================================================
# fig_q3_1  滚动 MPC 机制示意图
# ======================================================================
def fig1_mpc_schematic():
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")

    ax.annotate("", xy=(9.8, 1.0), xytext=(0.2, 1.0),
                arrowprops=dict(arrowstyle="->", lw=1.3, color=PALETTE["gray"]))
    for x, lab in [(0.2, "0:00"), (2.6, "6:00"), (5.0, "12:00"), (7.4, "18:00"), (9.8, "24:00")]:
        ax.plot([x], [1.0], marker="|", ms=11, color=PALETTE["gray"])
        ax.text(x, 0.55, lab, ha="center", va="center", fontsize=9.5, color=PALETTE["text"])

    stages = [
        (0.2, 3.3, "0:00 制定计划 x\n日闭合 E(144)=E(0)=6000\n0:00 光伏预报", PALETTE["blue"], PALETTE["blue_fill"]),
        (2.6, 3.3, "6:00 调整 y\n[6:00,24:00) 滚动 LP\nĜ − δ[6:00,t]", PALETTE["blue_deep"], PALETTE["blue_fill"]),
        (5.0, 3.3, "12:00 调整 y\n[12:00,24:00) 滚动 LP\nĜ − δ[12:00,t]", PALETTE["blue_deep"], PALETTE["blue_fill"]),
        (7.4, 3.3, "18:00 调整 y\n[18:00,24:00) 滚动 LP\nĜ − δ[18:00,t]", PALETTE["blue_deep"], PALETTE["blue_fill"]),
    ]
    bw, bh = 2.1, 1.5
    for x, y, txt, edge, fill in stages:
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.08",
                                    facecolor=fill, edgecolor=edge, lw=1.2))
        ax.text(x + bw / 2, y + bh / 2, txt, ha="center", va="center", fontsize=8.2, color=PALETTE["text"])
        ax.annotate("", xy=(x + bw, 1.0), xytext=(x + bw / 2, y),
                    arrowprops=dict(arrowstyle="->", color=PALETTE["gray"], lw=1.1))
        ax.plot([x + bw / 2], [1.0], marker="o", ms=4, color=PALETTE["blue"])

    ax.add_patch(FancyBboxPatch((0.2, 5.05), 9.6, 0.75, boxstyle="round,pad=0.08",
                                facecolor=PALETTE["coral_fill"], edgecolor=PALETTE["coral"], lw=1.0))
    ax.text(5.0, 5.42, "光伏风险修正：Ĝ_safe[s,t] = clip0(Ĝ[s,t] − δ[s,t])，δ[s,t]=P80(逐区间光伏高估)  |  按 issue(0/6/12/18)×执行块 分桶",
            ha="center", va="center", fontsize=8.6, color=PALETTE["text"])

    ax.add_patch(FancyBboxPatch((0.2, 4.25), 9.6, 0.62, boxstyle="round,pad=0.08",
                                facecolor="#EEF4FB", edgecolor=PALETTE["blue"], lw=1.0))
    ax.text(5.0, 4.56, "分段计费结算：p·min(x,y) + 0.5p·max(x−y,0) + 1.5p·max(y−x,0) + 5p·z（紧急）",
            ha="center", va="center", fontsize=8.6, color=PALETTE["text"])

    ax.set_title("图1  滚动时域 MPC 购电策略机制（0:00 计划 + 6/12/18 调整 + 日闭合 + 区间级风险修正）",
                 fontsize=11, pad=10, color=PALETTE["text"])
    return fig


# ======================================================================
# fig_q3_2  典型日 计划购电 vs 调整购电
# ======================================================================
def fig2_typical_day():
    xlsx = os.path.join(RESULTS_DIR, "Q3", "result3.xlsx")
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)

    def read_grid(ws):
        dts, rows = [], []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                continue
            dts.append(row[0])
            rows.append([float(v) if v is not None else 0.0 for v in row[1:1 + 144]])
        return dts, np.array(rows)
    dts, X = read_grid(wb["计划购电量"])
    _, Y = read_grid(wb["调整购电量"])
    wb.close()
    idx = dts.index(datetime(2025, 6, 21))
    x = X[idx] * 6.0
    y = Y[idx] * 6.0

    tt = np.arange(144) / 6.0
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(tt, x, color=PALETTE["blue_deep"], lw=2.0, label="计划购电 x（0:00 制定）", zorder=3)
    ax.plot(tt, y, color=PALETTE["amber"], lw=2.0, ls="--", label="调整购电 y（滚动调整后）", zorder=3)
    for h in (6, 12, 18):
        ax.axvline(h, color=PALETTE["gray_light"], ls=":", lw=1.1, zorder=1)
        ax.text(h, ax.get_ylim()[1] * 0.98, f"{h}:00", ha="center", va="top",
                fontsize=8, color=PALETTE["axis"])
    _style_axis(ax)
    ax.set_xlabel("时间（h）", color=PALETTE["text"])
    ax.set_ylabel("购电功率（kW）", color=PALETTE["text"])
    ax.set_title("图2  典型日（2025-06-21）计划购电与调整购电", color=PALETTE["text"])
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.set_xlim(0, 24)
    return fig


# ======================================================================
# fig_q3_3  全年总购电费对比
# ======================================================================
def fig3_cost_comparison():
    fz = _load_frozen()
    names = ["无储能+附件3预报", "规则套利 R3", "静态不调整 B3",
             "无储能·完美预见下界", "主模型 M3"]
    vals = [fz["baselines"][3]["objective_value"], fz["baselines"][1]["objective_value"],
            fz["baselines"][0]["objective_value"], fz["baselines"][2]["objective_value"],
            fz["objective"]["value"]]
    order = np.argsort(vals)[::-1]
    names = [names[i] for i in order]
    vals = [vals[i] for i in order]
    colors = [PALETTE["gray_light"]] * len(vals)
    colors[names.index("主模型 M3")] = PALETTE["blue"]

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ypos = np.arange(len(names))
    ax.barh(ypos, [v / 1e6 for v in vals], color=colors, height=0.6, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v / 1e6 + 0.12, i, f"{v/1e4:.1f} 万", va="center", fontsize=8.6, color=PALETTE["text"])
    _style_axis(ax)
    ax.set_yticks(ypos); ax.set_yticklabels(names, fontsize=9, color=PALETTE["text"])
    ax.set_xlabel("报告期总购电费（百万元）", color=PALETTE["text"])
    ax.set_title("图3  主模型 M3 与各基线总购电费对比", color=PALETTE["text"])
    ax.invert_yaxis()
    ax.set_xlim(0, max(vals) / 1e6 * 1.12)
    return fig


# ======================================================================
# fig_q3_4  预报/调整时刻边际价值
# ======================================================================
def fig4_stage_value():
    r = _load_robustness()
    sa = r["stage_ablation"]
    pf = r["perfect_forecast_upper_bound"]["total"]
    labels = ["仅 0:00", "+6:00", "+12:00", "+18:00"]
    vals = [sa["0"]["total"], sa["0+6"]["total"], sa["0+6+12"]["total"], sa["0+6+12+18"]["total"]]
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ax.plot(range(4), [v / 1e6 for v in vals], color=PALETTE["blue_deep"], lw=2.2,
            marker="o", ms=6, zorder=3, label="含区间级风险修正的 MPC")
    ax.axhline(pf / 1e6, color=PALETTE["teal"], ls="--", lw=1.7,
               label=f"完美预见下界 {pf/1e6:.2f}M", zorder=2)
    for i, v in enumerate(vals):
        ax.annotate(f"{v/1e6:.2f}M", (i, v / 1e6), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8.6, color=PALETTE["text"])
    deltas = [vals[0]-vals[1], vals[1]-vals[2], vals[2]-vals[3]]
    for i, d in enumerate(deltas, start=1):
        ax.text(i, (vals[i] + vals[i-1]) / 2e6 + 0.06, f"边际省 {d/1e4:.1f} 万",
                ha="center", fontsize=7.8, color=PALETTE["coral"])
    _style_axis(ax)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9.5, color=PALETTE["text"])
    ax.set_ylabel("报告期总购电费（百万元）", color=PALETTE["text"])
    ax.set_xlabel("纳入的预报 / 调整时刻", color=PALETTE["text"])
    ax.set_title("图4  调整时刻的边际价值（是否引入其他预报时刻）", color=PALETTE["text"])
    ax.legend(fontsize=8.2, frameon=False)
    return fig


# ======================================================================
# fig_q3_5  分位敏感性 × 成本分解（堆叠 + 总费用）  [增强]
# ======================================================================
def fig5_quantile_decomp():
    rows = _load_quantile_decomp()
    qs = [r["q"] for r in rows]
    plan = [r["plan"] / 1e6 for r in rows]
    pen = [r["penalty"] / 1e6 for r in rows]
    emg = [r["emergency"] / 1e6 for r in rows]
    tot = [r["total"] / 1e6 for r in rows]

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    y = np.arange(len(qs))
    b1 = ax.barh(y, plan, color=PALETTE["blue_fill"], edgecolor=PALETTE["blue"], lw=0.8, zorder=3, label="计划购电")
    b2 = ax.barh(y, pen, left=plan, color=PALETTE["amber_fill"], edgecolor=PALETTE["amber"], lw=0.8, zorder=3, label="违约/溢价")
    b3 = ax.barh(y, emg, left=[p + e for p, e in zip(plan, pen)],
                 color=PALETTE["coral_fill"], edgecolor=PALETTE["coral"], lw=0.8, zorder=3, label="紧急购电")
    for i in range(len(qs)):
        ax.text(tot[i] + 0.25, i, f"{tot[i]:.2f}", va="center", fontsize=8.2, color=PALETTE["text"])
    _style_axis(ax)
    ax.set_yticks(y)
    ax.set_yticklabels([f"q={q}" for q in qs], fontsize=9, color=PALETTE["text"])
    # 冻结点 q=80 与经验 argmin q=85 高亮（须在 set_yticklabels 之后）
    for i, q in enumerate(qs):
        if q == 80:
            lbl = ax.get_yticklabels()[i]
            lbl.set_color(PALETTE["blue_deep"])
            lbl.set_fontweight("bold")
            ax.text(tot[i] + 0.25, i + 0.34, "冻结", va="bottom", fontsize=7.4, color=PALETTE["blue_deep"])
        if q == 85:
            ax.text(tot[i] + 0.25, i + 0.34, "argmin", va="bottom", fontsize=7.4, color=PALETTE["amber"])
    ax.set_xlabel("报告期总购电费（百万元）", color=PALETTE["text"])
    ax.set_title("图5  光伏风险修正分位 q 的成本分解（计划 / 溢价 / 紧急）", color=PALETTE["text"])
    ax.invert_yaxis()
    ax.legend(fontsize=8.4, frameon=False, loc="lower right")
    ax.set_xlim(0, max(tot) * 1.10)
    return fig


# ======================================================================
# fig_q3_6  负荷/光伏 ±5% 扰动
# ======================================================================
def fig6_perturbation():
    r = _load_robustness()
    pert = r["perturbation"]
    base = pert["base"]["total"]
    names = ["负荷 +5%", "负荷 −5%", "光伏 +5%", "光伏 −5%"]
    vals = [pert["load+5%"]["total"], pert["load-5%"]["total"],
            pert["pv+5%"]["total"], pert["pv-5%"]["total"]]
    d = [v - base for v in vals]
    colors = [PALETTE["coral"] if x > 0 else PALETTE["teal"] for x in d]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    y = np.arange(len(names))
    ax.barh(y, d, color=colors, alpha=0.85, height=0.55, zorder=3)
    ax.axvline(0, color=PALETTE["gray"], lw=0.9)
    for i, x in enumerate(d):
        ax.annotate(f"{x/1e4:+.1f} 万", (x, i), textcoords="offset points",
                    xytext=(4 if x >= 0 else -4, 0),
                    ha="left" if x >= 0 else "right", va="center", fontsize=8.4, color=PALETTE["text"])
    _style_axis(ax)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9.5, color=PALETTE["text"])
    ax.set_xlabel("相对基准的费用变化（元）", color=PALETTE["text"])
    ax.set_title("图6  负荷 / 光伏 ±5% 扰动的稳健性", color=PALETTE["text"])
    return fig


# ======================================================================
# fig_q3_7  光伏预报误差-前瞻时域
# ======================================================================
def fig7_horizon_error():
    r = _load_robustness()
    p80 = r["horizon_error_p80_kW"]
    hrs = np.arange(1, 25)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    colors = [PALETTE["blue_deep"], PALETTE["coral"], PALETTE["amber"], PALETTE["teal"]]
    for s in range(4):
        arr = [v if v is not None else np.nan for v in p80[str(s)]]
        ax.plot(hrs, arr, lw=1.8, color=colors[s], marker="o", ms=3.5, zorder=3,
                label=f"{6*s}:00 发布")
    ax.axhline(0, color=PALETTE["gray"], lw=0.8)
    _style_axis(ax)
    ax.set_xlabel("前瞻时域（h）", color=PALETTE["text"])
    ax.set_ylabel("光伏高估 P80（kW）", color=PALETTE["text"])
    ax.set_title("图7  光伏预报误差随前瞻时域的变化", color=PALETTE["text"])
    ax.legend(fontsize=8.5, ncol=2, frameon=False)
    return fig


# ======================================================================
# fig_q3_8  光伏风险修正量 δ[s,t] 热图（建模分析）  [新增]
# ======================================================================
def fig8_delta_heatmap():
    b = load_bundle()
    fc = b["附件3"]["forecast"]; pv = b["附件2_pv"]
    over = qopt.block_over(fc, pv)
    delta = qopt.block_delta(over, len(pv) - 1, 80.0)  # (4,36) 全历史因果分位

    fig, ax = plt.subplots(figsize=(8.0, 3.6))
    cmap = LinearSegmentedColormap.from_list("soft_div", [PALETTE["blue_deep"], "#FFFFFF", PALETTE["coral"]])
    vmax = max(abs(delta.min()), abs(delta.max()))
    im = ax.imshow(delta, aspect="auto", cmap=cmap, vmin=-vmax, vmax=vmax)
    ax.set_yticks(range(4))
    ax.set_yticklabels(["0:00 发布\n执行 0–6h", "6:00 发布\n执行 6–12h",
                        "12:00 发布\n执行 12–18h", "18:00 发布\n执行 18–24h"], fontsize=8.4, color=PALETTE["text"])
    ax.set_xticks(np.arange(0, 36, 6))
    ax.set_xticklabels([f"+{h}h" for h in range(0, 6)], fontsize=8, color=PALETTE["axis"])
    ax.set_xlabel("执行块内区间（每格 10 min，共 6 h）", color=PALETTE["text"])
    for i in range(4):
        for j in range(36):
            v = delta[i, j]
            if abs(v) > 0.6 * vmax:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.8,
                        color="white" if abs(v) > 0.55 * vmax else PALETTE["text"])
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("光伏高估修正量 δ[s,t]（kW）", fontsize=9, color=PALETTE["text"])
    cb.ax.tick_params(labelsize=8, colors=PALETTE["axis"])
    ax.set_title("图8  光伏风险修正量 δ[s,t]（P80 逐区间分位，全历史估计）", color=PALETTE["text"], fontsize=10.5)
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_color(PALETTE["gray_light"])
    ax.grid(False)
    return fig


# ======================================================================
# fig_q3_9  典型日储能 SOC 轨迹（结果验证）  [新增]
# ======================================================================
def fig9_soc_trajectory():
    b = load_bundle()
    price = b["附件1"]["price"]; load = b["附件2_load"]; pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    dates = b["dates"]
    over = qopt.block_over(fc, pv)

    def day_idx(date_str):
        for i, s in enumerate(dates):
            if s.startswith(date_str):
                return i
        raise KeyError(date_str)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9))
    tt = np.arange(145) / 6.0
    for ax, ds in zip(axes, ["2025-06-21", "2025-12-21"]):
        d = day_idx(ds)
        delta = qopt.block_delta(over, d, 80.0)
        _, x, y, c, qv, E_end, z, E_day = qopt.mpc_day(price, load[d], pv[d], fc, d, E0_INIT, delta)
        ax.plot(tt, E_day, color=PALETTE["blue_deep"], lw=2.0, zorder=3)
        ax.fill_between(tt, EMIN, EMAX, color=PALETTE["blue_fill"], alpha=0.35, zorder=1)
        ax.axhline(EMIN, color=PALETTE["gray_light"], ls="--", lw=1.0)
        ax.axhline(EMAX, color=PALETTE["gray_light"], ls="--", lw=1.0)
        ax.axhline(E0_INIT, color=PALETTE["amber"], ls=":", lw=1.2)
        ax.scatter([0], [E_day[0]], color=PALETTE["teal"], s=30, zorder=4)
        ax.scatter([24], [E_day[-1]], color=PALETTE["teal"], s=30, zorder=4, label="E(0)=E(24)=6000")
        _style_axis(ax)
        ax.set_title(f"{ds}（{'夏至' if '06' in ds else '冬至'}）", fontsize=10, color=PALETTE["text"])
        ax.set_xlabel("时间（h）", color=PALETTE["text"])
        if ax is axes[0]:
            ax.set_ylabel("储电量 E（kWh）", color=PALETTE["text"])
        ax.set_xlim(0, 24)
        ax.set_ylim(0, EMAX * 1.12)
    axes[0].text(0.02, 0.97, "E_min=1200 / E_max=10800", transform=axes[0].transAxes,
                 fontsize=7.6, color=PALETTE["axis"], va="top")
    axes[0].legend(loc="lower right", fontsize=7.6, frameon=False)
    fig.suptitle("图9  典型日储能 SOC 轨迹（储能上下界与日闭合 E(0)=E(144)=6000 校验）",
                 fontsize=11, color=PALETTE["text"])
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return fig


def _verify_render():
    from PIL import Image
    ok = True
    files = sorted(os.listdir(FIG_DIR))
    pngs = [f for f in files if f.startswith("fig_q3_") and f.endswith(".png")]
    for f in pngs:
        p = os.path.join(FIG_DIR, f)
        try:
            Image.open(p).verify()
        except Exception as e:
            print(f"RENDER-FAIL {f}: {e}"); ok = False
    return ok, pngs


def main():
    print(f"中文字体: {_FONT_NAME} (ok={_FONT_OK})")
    figs = {
        "fig_q3_1_mpc_schematic": fig1_mpc_schematic,
        "fig_q3_2_typical_day": fig2_typical_day,
        "fig_q3_3_cost_comparison": fig3_cost_comparison,
        "fig_q3_4_stage_value": fig4_stage_value,
        "fig_q3_5_quantile_sensitivity": fig5_quantile_decomp,
        "fig_q3_6_perturbation": fig6_perturbation,
        "fig_q3_7_horizon_error": fig7_horizon_error,
        "fig_q3_8_delta_heatmap": fig8_delta_heatmap,
        "fig_q3_9_soc_trajectory": fig9_soc_trajectory,
    }
    saved = []
    for name, fn in figs.items():
        try:
            fig = fn()
            saved.append(_save(fig, name))
        except Exception as e:
            print(f"FIG-ERROR {name}: {e}")
    ok, pngs = _verify_render()
    print("SAVED:")
    for s in saved:
        print("  ", s)
    print("RENDER-OK:", ok, f"({len(pngs)} png)")
    if RENDER_WARNINGS:
        print("RENDER WARNINGS:")
        for w in RENDER_WARNINGS:
            print("  ", w)
    else:
        print("无中文字形告警")


if __name__ == "__main__":
    main()
