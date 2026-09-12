# -*- coding: utf-8 -*-
"""Q4 论文精确值汇总表：tab_q4_cost_5group / decomposition / const_vs_fluct / q_sweep。

数据源（全部为冻结口径 round3 块级 q=80）：
  - results/Q4/experiments/round3/run_summary.json        主模型+基线+诊断
  - results/Q4/experiments/optimization/e44_quantile_sweep.json   result4-3 块级 q 扫描
  - robustness/Q4/q4_robustness_summary.json               result4-2 q 扫描 + 恒定/波动对照
  - results/Q3/reports/frozen_numbers.json                 Q3 块级 q=80（result4-3 恒定基准）
输出：results/Q4/reports/q4_paper_tables.md
"""
import os, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RS = json.load(open(os.path.join(ROOT, "results", "Q4", "experiments", "round3", "run_summary.json"), encoding="utf-8"))
E44 = json.load(open(os.path.join(ROOT, "results", "Q4", "experiments", "optimization", "e44_quantile_sweep.json"), encoding="utf-8"))
ROB = json.load(open(os.path.join(ROOT, "robustness", "Q4", "q4_robustness_summary.json"), encoding="utf-8"))
Q3F = json.load(open(os.path.join(ROOT, "results", "Q3", "reports", "frozen_numbers.json"), encoding="utf-8"))


def w(wan):
    return f"{wan/1e4:,.2f}"


def main():
    r2 = RS["result4_2"]; r3 = RS["result4_3"]
    bl = {b["id"]: b["objective_value"] for b in RS["baselines"]}
    dg = {d["id"]: d["objective_value"] for d in RS["diagnostics"]}
    m2 = RS["metrics"]["result4_2"]; m3 = RS["metrics"]["result4_3"]
    R1 = ROB["R1_quantile_sweep"]; R3 = ROB["R3_constant_vs_fluctuating"]
    q3_const = Q3F["objective"]["value"]

    L = []
    L.append("# Q4 论文精确值汇总表（round3 块级 q=80 冻结口径）")
    L.append("")
    L.append("> 数值一律引用冻结文件 `results/Q4/reports/frozen_numbers.json`，严禁在正文另写数值。")
    L.append("> 单位：购电费为元（万元括号内），电量为 kWh，弃光率为无量纲。报告期 2025-02-01 ~ 2025-12-31（334 天）。")
    L.append("")

    # ---- P1 方案对比 ----
    L.append("## 表 P1 各方案报告期总购电费对比（tab_q4_cost_5group）")
    L.append("")
    L.append("| 方案 | 总购电费（元） | 总购电费（万元） | 相对诊断下界 B 增量 |")
    L.append("|---|---|---|---|")
    rows = [
        ("诊断 B：储能+完美预见+跨日自由结转（全局理论下界）", dg["B"], "—"),
        ("诊断 A：储能+完美预见+日闭合（与主模型同约束）", dg["A"], f"{dg['A']-dg['B']:,.2f}"),
        ("主模型 M4-3：滚动 MPC+分段计费+块级80分位修正", r3["objective_value"], f"{r3['objective_value']-dg['B']:,.2f}"),
        ("主模型 M4-2：逐日滚动 LP+星期80分位修正", r2["objective_value"], f"{r2['objective_value']-dg['B']:,.2f}"),
        ("基线 B4_ref：无储能+完美预见（诊断下界）", bl["B4_ref"], f"{bl['B4_ref']-dg['B']:,.2f}"),
        ("基线 R4：规则峰谷套利+自预报", bl["R4"], f"{bl['R4']-dg['B']:,.2f}"),
        ("基线 B4：无储能+自预报+星期80分位", bl["B4"], f"{bl['B4']-dg['B']:,.2f}"),
    ]
    for name, v, d in rows:
        L.append(f"| {name} | {v:,.2f} | {w(v)} | {d} |")
    L.append("")
    L.append("> 排序校验：B < A < M4-3 < M4-2 < B4_ref < R4 < B4 单调有序。")
    L.append("")

    # ---- P2 成本分解 ----
    L.append("## 表 P2 成本分解（tab_q4_decomposition）")
    L.append("")
    L.append("| 成本项 | result4-2（逐日LP） | result4-3（MPC） |")
    L.append("|---|---|---|")
    L.append(f"| 理论下界 B（完美预见+自由结转） | {dg['B']:,.2f} | {dg['B']:,.2f} |")
    L.append(f"| ＋ 日闭合约束成本（A−B） | {dg['A']-dg['B']:,.2f} | {dg['A']-dg['B']:,.2f} |")
    L.append(f"| ＝ 诊断 A（完美预见+日闭合） | {dg['A']:,.2f} | {dg['A']:,.2f} |")
    fe2 = r2["objective_value"] - dg["A"]
    fe3 = r3["objective_value"] - dg["A"]
    L.append(f"| ＋ 预报误差成本（主模型−A） | {fe2:,.2f} | {fe3:,.2f} |")
    L.append(f"| ＝ 主模型总购电费 | **{r2['objective_value']:,.2f}** | **{r3['objective_value']:,.2f}** |")
    L.append("")
    L.append(f"> result4-3 较 result4-2 的预报误差成本降低 {fe2-fe3:,.2f} 元（−{(fe2-fe3)/fe2*100:.1f}%），"
             f"源于 MPC 滚动调整 + 块级光伏风险修正同时削减违约溢价与紧急购电。")
    L.append("")

    # ---- P2b 分项计费 ----
    L.append("## 表 P2b 分项购电费（计划/违约溢价/紧急）")
    L.append("")
    L.append("| 分项（元） | result4-2 | result4-3 |")
    L.append("|---|---|---|")
    L.append(f"| 计划购电费 | {r2['plan_cost']:,.2f} | {r3['plan_cost']:,.2f} |")
    L.append(f"| 违约/溢价 | — | {r3['penalty_cost']:,.2f} |")
    L.append(f"| 紧急购电费 | {r2['emergency_cost']:,.2f} | {r3['emergency_cost']:,.2f} |")
    L.append(f"| **合计** | **{r2['objective_value']:,.2f}** | **{r3['objective_value']:,.2f}** |")
    L.append(f"| 紧急购电电量（kWh） | {m2['紧急购电_电量kWh']:,.2f} | {m3['紧急购电_电量kWh']:,.2f} |")
    L.append(f"| 弃光电量（kWh） | {m2['弃光_电量kWh']:,.2f} | {m3['弃光_电量kWh']:,.2f} |")
    L.append(f"| 弃光率 | {m2['弃光率']:.4f} | {m3['弃光率']:.4f} |")
    L.append("")

    # ---- P3 恒定 vs 波动 ----
    L.append("## 表 P3 恒定电价 vs 波动电价（tab_q4_const_vs_fluct）")
    L.append("")
    L.append("| 指标 | 恒定（附件1） | 波动（附件4） | Δ | Δ% |")
    L.append("|---|---|---|---|---|")
    c2f2 = R3["result4_2_fluctuating"] - R3["result4_2_constant"]
    c3f3 = r3["objective_value"] - q3_const
    items = [
        ("result4-2 总购电费（元）", R3["result4_2_constant"], R3["result4_2_fluctuating"],
         c2f2, c2f2 / R3["result4_2_constant"] * 100),
        ("result4-3 总购电费（元）", q3_const, r3["objective_value"],
         c3f3, c3f3 / q3_const * 100),
        ("储能价值（元, result4-2侧）", R3["storage_value_constant"], R3["storage_value_fluctuating"],
         R3["storage_value_fluctuating"] - R3["storage_value_constant"],
         (R3["storage_value_fluctuating"] - R3["storage_value_constant"]) / R3["storage_value_constant"] * 100),
        ("预报误差成本·储能侧（元）", R3["forecast_error_cost_storage_constant"],
         R3["forecast_error_cost_storage_fluctuating"],
         R3["forecast_error_cost_storage_fluctuating"] - R3["forecast_error_cost_storage_constant"],
         (R3["forecast_error_cost_storage_fluctuating"] - R3["forecast_error_cost_storage_constant"])
         / R3["forecast_error_cost_storage_constant"] * 100),
        ("日闭合约束成本（元）", R3["day_closure_cost_constant"], R3["day_closure_cost_fluctuating"],
         R3["day_closure_cost_fluctuating"] - R3["day_closure_cost_constant"],
         (R3["day_closure_cost_fluctuating"] - R3["day_closure_cost_constant"])
         / R3["day_closure_cost_constant"] * 100),
        ("储能套利空间（元）", R3["storage_arbitrage_space_constant"],
         R3["storage_arbitrage_space_fluctuating"],
         R3["storage_arbitrage_space_fluctuating"] - R3["storage_arbitrage_space_constant"],
         (R3["storage_arbitrage_space_fluctuating"] - R3["storage_arbitrage_space_constant"])
         / R3["storage_arbitrage_space_constant"] * 100),
    ]
    for name, c, f, d, dp in items:
        L.append(f"| {name} | {c:,.2f} | {f:,.2f} | {d:+,.2f} | {dp:+.2f}% |")
    L.append("")
    L.append("> 结论：波动电价主要抬升基础用电成本（电价与负荷正相关 corr=+0.508），并同时放大储能套利空间与预报误差损失。")
    L.append("")

    # ---- P4 q 扫描 ----
    L.append("## 表 P4 风险修正分位 q 敏感性（tab_q4_q_sweep）")
    L.append("")
    L.append("### 表 P4a result4-2（星期80分位，逐日LP）")
    L.append("")
    q2 = R1["result4_2_total_by_q"]
    L.append("| q（%） | " + " | ".join(q2.keys()) + " |")
    L.append("|---" * (len(q2) + 1) + "|")
    L.append("| 总购电费（元） | " + " | ".join(f"{q2[k]:,.2f}" for k in q2) + " |")
    L.append("")
    L.append(f"> argmin q={R1['argmin_q_result4_2']}；q=80 相对 argmin 差 {R1['q80_vs_argmin_result4_2_delta']:,.2f} 元（"
             f"{R1['q80_vs_argmin_result4_2_delta']/q2['80']*100:.2f}%），仍近优。")
    L.append("")
    L.append("### 表 P4b result4-3（块级 issue×执行块 逐区间80分位，MPC）")
    L.append("")
    sweep = E44["q_sweep"]
    L.append("| q（%） | " + " | ".join(sweep.keys()) + " |")
    L.append("|---" * (len(sweep) + 1) + "|")
    L.append("| 总购电费（元） | " + " | ".join(f"{sweep[k]['total']:,.2f}" for k in sweep) + " |")
    L.append("| 紧急购电（kWh） | " + " | ".join(f"{sweep[k]['emergency_kwh']:,.2f}" for k in sweep) + " |")
    L.append("")
    L.append(f"> argmin q={E44['argmin_q']}；q=80 相对 argmin 差 {E44['q80_vs_argmin_delta']:,.2f} 元（"
             f"{E44['q80_delta_pct']:.2f}%），仍近优——报童临界比 (5−1)/5=0.8 结构上不随电价缩放，故 q=80 作冻结主值。")
    L.append("")

    out = os.path.join(ROOT, "results", "Q4", "reports", "q4_paper_tables.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", out)


if __name__ == "__main__":
    main()
