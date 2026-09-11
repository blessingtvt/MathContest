# -*- coding: utf-8 -*-
"""Q3 论文图生成（math-figure-generator）：中文标注 + 统一配色系统 + 渲染校验。

图清单（见 methods/Q3/q3_figure_table_plan.md）:
  fig_q3_1 滚动 MPC 机制示意图          (Type 3 论文正式)
  fig_q3_2 典型日 计划购电 vs 调整购电   (Type 3 论文正式)
  fig_q3_3 全年总购电费 主模型 vs 基线    (Type 3 论文正式)
  fig_q3_4 预报/调整时刻边际价值          (Type 3 论文正式)
  fig_q3_5 风险修正分位敏感性             (Type 4 附录)
  fig_q3_6 负荷/光伏 ±5% 扰动            (Type 4 附录)
  fig_q3_7 光伏预报误差-前瞻时域          (Type 4 附录)
输出: paper/figures/*.png (300dpi) + *.svg (矢量)。
"""
import os, sys, json, warnings
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import openpyxl
from common import RESULTS_DIR, ROOT

# ---- 中文字体（已确认 Microsoft YaHei / SimHei 可用）----
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

# ---- 配色系统（math-figure-generator color-systems.md）----
PALETTE = {
    "primary": "#1A6FC4",      # 主模型 M3
    "primary_light": "#5B9BD5",
    "baseline": "#767676",     # 基线（恒灰）
    "baseline_dark": "#4D4D4D",
    "positive": "#2E9E44",
    "negative": "#E53935",
    "accent1": "#E28E2C",      # 次级（调整购电/12:00 等）
    "accent2": "#7B5FD6",
    "accent3": "#33B5A5",
    "neutral_mid": "#A8A8A8",
    "neutral_dark": "#606060",
    "neutral_black": "#333333",
}

FIG_DIR = os.path.join(ROOT, "paper", "figures")
EXP_DIR = os.path.join(RESULTS_DIR, "Q3", "experiments", "round3")
RENDER_WARNINGS = []


def _load_robustness():
    with open(os.path.join(EXP_DIR, "robustness_report.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_frozen():
    with open(os.path.join(RESULTS_DIR, "Q3", "reports", "frozen_numbers.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _save(fig, name):
    """保存 PNG(300dpi) + SVG，并捕获渲染告警（中文缺字形等）。"""
    os.makedirs(FIG_DIR, exist_ok=True)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        png = os.path.join(FIG_DIR, name + ".png")
        svg = os.path.join(FIG_DIR, name + ".svg")
        fig.savefig(png, dpi=300, bbox_inches="tight")
        fig.savefig(svg, bbox_inches="tight")
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
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    ax.axis("off")

    # 时间轴
    ax.annotate("", xy=(9.8, 1.0), xytext=(0.2, 1.0),
                arrowprops=dict(arrowstyle="->", lw=1.3, color=PALETTE["neutral_dark"]))
    for x, lab in [(0.2, "0:00"), (2.6, "6:00"), (5.0, "12:00"), (7.4, "18:00"), (9.8, "24:00")]:
        ax.plot([x], [1.0], marker="|", ms=11, color=PALETTE["neutral_dark"])
        ax.text(x, 0.55, lab, ha="center", va="center", fontsize=9.5,
                color=PALETTE["neutral_black"])

    # 四个阶段框
    stages = [
        (0.2, 3.3, "0:00 制定计划 x\n日闭合 E(144)=E(0)=6000\n0:00 光伏预报", PALETTE["primary"]),
        (2.6, 3.3, "6:00 调整 y\n[6:00,24:00) 滚动 LP\nĜ − δ[6:00]", PALETTE["primary_light"]),
        (5.0, 3.3, "12:00 调整 y\n[12:00,24:00) 滚动 LP\nĜ − δ[12:00]", PALETTE["primary_light"]),
        (7.4, 3.3, "18:00 调整 y\n[18:00,24:00) 滚动 LP\nĜ − δ[18:00]", PALETTE["primary_light"]),
    ]
    bw, bh = 2.1, 1.5
    for x, y, txt, c in stages:
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.08",
                                    facecolor=c, edgecolor=PALETTE["baseline_dark"], lw=1.0))
        ax.text(x + bw / 2, y + bh / 2, txt, ha="center", va="center", fontsize=8.2,
                color="white" if c == PALETTE["primary"] else PALETTE["neutral_black"])
        ax.annotate("", xy=(x + bw, 1.0), xytext=(x + bw / 2, y),
                    arrowprops=dict(arrowstyle="->", color=PALETTE["neutral_dark"], lw=1.1))
        ax.plot([x + bw / 2], [1.0], marker="o", ms=4, color=PALETTE["primary"])

    # 风险修正框
    ax.add_patch(FancyBboxPatch((0.2, 5.05), 9.6, 0.75, boxstyle="round,pad=0.08",
                                facecolor="#FDE9E7", edgecolor=PALETTE["negative"], lw=1.0))
    ax.text(5.0, 5.42, "光伏风险修正：Ĝ_safe = clip0(Ĝ − δ[issue])，δ[s]=P80(光伏高估)  |  按 issue(0/6/12/18) 分桶",
            ha="center", va="center", fontsize=8.6, color=PALETTE["neutral_black"])

    # 结算框
    ax.add_patch(FancyBboxPatch((0.2, 4.25), 9.6, 0.62, boxstyle="round,pad=0.08",
                                facecolor="#E8F0FE", edgecolor=PALETTE["primary"], lw=1.0))
    ax.text(5.0, 4.56, "分段计费结算：p·min(x,y) + 0.5p·max(x−y,0) + 1.5p·max(y−x,0) + 5p·z（紧急）",
            ha="center", va="center", fontsize=8.6, color=PALETTE["neutral_black"])

    ax.set_title("图1  滚动时域 MPC 购电策略机制（0:00 计划 + 6/12/18 调整 + 日闭合 + 风险修正）",
                 fontsize=11, pad=10)
    return fig


# ======================================================================
# fig_q3_2  典型日 计划购电 vs 调整购电
# ======================================================================
def fig2_typical_day():
    # 读取 result3.xlsx 的计划/调整购电量网格，取 2025-06-21
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
    x = X[idx] * 6.0   # kWh/10min -> kW
    y = Y[idx] * 6.0

    tt = np.arange(144) / 6.0   # 小时
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(tt, x, color=PALETTE["primary"], lw=1.8, label="计划购电 x（0:00 制定）")
    ax.plot(tt, y, color=PALETTE["accent1"], lw=1.8, ls="--", label="调整购电 y（滚动调整后）")
    for h in (6, 12, 18):
        ax.axvline(h, color=PALETTE["neutral_mid"], ls=":", lw=1.0, alpha=0.9)
        ax.text(h, ax.get_ylim()[1] * 0.98, f"{h}:00", ha="center", va="top",
                fontsize=8, color=PALETTE["neutral_dark"])
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("购电功率（kW）")
    ax.set_title("图2  典型日（2025-06-21）计划购电与调整购电")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_xlim(0, 24)
    ax.grid(alpha=0.3)
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
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
    colors = [PALETTE["baseline"]] * len(vals)
    colors[names.index("主模型 M3")] = PALETTE["primary"]

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ypos = np.arange(len(names))
    ax.barh(ypos, [v / 1e6 for v in vals], color=colors, height=0.6,
            edgecolor="white", lw=0.5)
    for i, v in enumerate(vals):
        ax.text(v / 1e6 + 0.12, i, f"{v/1e4:.1f} 万", va="center", fontsize=8.6,
                color=PALETTE["neutral_black"])
    ax.set_yticks(ypos); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("报告期总购电费（百万元）")
    ax.set_title("图3  主模型 M3 与各基线总购电费对比")
    ax.invert_yaxis()
    ax.set_xlim(0, max(vals) / 1e6 * 1.12)
    ax.grid(alpha=0.3, axis="x")
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
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
    ax.plot(range(4), [v / 1e6 for v in vals], color=PALETTE["primary"], lw=2,
            marker="o", ms=6, label="含光伏风险修正的 MPC")
    ax.axhline(pf / 1e6, color=PALETTE["positive"], ls="--", lw=1.6,
               label=f"完美预见下界 {pf/1e6:.2f}M")
    for i, v in enumerate(vals):
        ax.annotate(f"{v/1e6:.2f}M", (i, v / 1e6), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8.6)
    # 边际节省标注
    deltas = [vals[0]-vals[1], vals[1]-vals[2], vals[2]-vals[3]]
    for i, d in enumerate(deltas, start=1):
        ax.text(i, (vals[i] + vals[i-1]) / 2e6 + 0.06, f"边际省 {d/1e4:.1f} 万",
                ha="center", fontsize=7.8, color=PALETTE["negative"])
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("报告期总购电费（百万元）")
    ax.set_xlabel("纳入的预报 / 调整时刻")
    ax.set_title("图4  调整时刻的边际价值（是否引入其他预报时刻）")
    ax.legend(fontsize=8.2)
    ax.grid(alpha=0.3)
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
    return fig


# ======================================================================
# fig_q3_5  风险修正分位敏感性
# ======================================================================
def fig5_quantile_sweep():
    r = _load_robustness()
    sweep = r["quantile_sweep_total"]
    qs = [int(k[1:]) for k in sweep]
    vals = [sweep[k] / 1e6 for k in sweep]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(qs, vals, color=PALETTE["primary"], lw=1.8, marker="o", ms=5)
    ax.axvline(80, color=PALETTE["neutral_mid"], ls="--", lw=1.0)
    ax.annotate("q=80 全局最优", xy=(80, sweep["q80"] / 1e6), xytext=(48, sweep["q80"] / 1e6 + 1.2),
                fontsize=8.6, arrowprops=dict(arrowstyle="->", color=PALETTE["neutral_dark"]))
    ax.set_xlabel("光伏风险修正分位 q（%）")
    ax.set_ylabel("报告期总购电费（百万元）")
    ax.set_title("图5  光伏风险修正分位的敏感性")
    ax.grid(alpha=0.3)
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
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
    colors = [PALETTE["negative"] if x > 0 else PALETTE["positive"] for x in d]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    y = np.arange(len(names))
    ax.barh(y, d, color=colors, alpha=0.9, height=0.55)
    ax.axvline(0, color=PALETTE["neutral_dark"], lw=0.9)
    for i, x in enumerate(d):
        ax.annotate(f"{x/1e4:+.1f} 万", (x, i), textcoords="offset points",
                    xytext=(4 if x >= 0 else -4, 0),
                    ha="left" if x >= 0 else "right", va="center", fontsize=8.4)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9.5)
    ax.set_xlabel("相对基准的费用变化（元）")
    ax.set_title("图6  负荷 / 光伏 ±5% 扰动的稳健性")
    ax.grid(alpha=0.3, axis="x")
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
    return fig


# ======================================================================
# fig_q3_7  光伏预报误差-前瞻时域
# ======================================================================
def fig7_horizon_error():
    r = _load_robustness()
    p80 = r["horizon_error_p80_kW"]
    hrs = np.arange(1, 25)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    colors = [PALETTE["primary"], PALETTE["accent1"], PALETTE["accent3"], PALETTE["accent2"]]
    for s in range(4):
        arr = [v if v is not None else np.nan for v in p80[str(s)]]
        ax.plot(hrs, arr, lw=1.7, color=colors[s], marker="o", ms=3.5,
                label=f"{6*s}:00 发布")
    ax.axhline(0, color=PALETTE["neutral_mid"], lw=0.8)
    ax.set_xlabel("前瞻时域（h）")
    ax.set_ylabel("光伏高估 P80（kW）")
    ax.set_title("图7  光伏预报误差随前瞻时域的变化")
    ax.legend(fontsize=8.5, ncol=2)
    ax.grid(alpha=0.3)
    ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
    return fig


def _verify_render():
    from PIL import Image
    ok = True
    files = sorted(os.listdir(FIG_DIR))
    pngs = [f for f in files if f.endswith(".png")]
    for f in pngs:
        p = os.path.join(FIG_DIR, f)
        try:
            im = Image.open(p); im.verify()
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
        "fig_q3_5_quantile_sensitivity": fig5_quantile_sweep,
        "fig_q3_6_perturbation": fig6_perturbation,
        "fig_q3_7_horizon_error": fig7_horizon_error,
    }
    saved = []
    for name, fn in figs.items():
        fig = fn()
        saved.append(_save(fig, name))
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
        print("无中文字形告警 (glyph warnings: 0)")


if __name__ == "__main__":
    main()
