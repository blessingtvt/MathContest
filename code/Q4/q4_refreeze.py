# -*- coding: utf-8 -*-
"""Q4 重冻结（refreeze）：round2(标量δ) → round3(块级δ, q=80)。

协议：thaw → rerun → refreeze + freeze_change_log。
  - 权威数值来源 = results/Q4/experiments/round3/run_summary.json（q4_main.py 重跑产出）
  - q 敏感性(块级) 来源 = results/Q4/experiments/optimization/e44_quantile_sweep.json
  - result4-3 恒定电价参照 = results/Q3/reports/frozen_numbers.json (Q3 round4 块级 q=80)

不改 result4-2 侧任何值（result4-2 模型未变，仅换电价）。
"""
import os, json
from datetime import datetime, timezone, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FROZEN = os.path.join(ROOT, "results", "Q4", "reports", "frozen_numbers.json")
RUN = os.path.join(ROOT, "results", "Q4", "experiments", "round3", "run_summary.json")
E44 = os.path.join(ROOT, "results", "Q4", "experiments", "optimization", "e44_quantile_sweep.json")
Q3F = os.path.join(ROOT, "results", "Q3", "reports", "frozen_numbers.json")
LOG = os.path.join(ROOT, "results", "Q4", "reports", "freeze_change_log.md")

CST = timezone(timedelta(hours=8))


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def set_claim(fz, claim_id, value, source_file, locator):
    for n in fz["numbers"]:
        if n["claim_id"] == claim_id:
            n["value"] = value
            n["source_file"] = source_file
            n["source_locator"] = locator
            return
    fz["numbers"].append({"claim_id": claim_id, "value": value, "unit": "元",
                          "source_file": source_file, "source_locator": locator})


def main():
    rs = load(RUN)
    e44 = load(E44)
    q3f = load(Q3F)
    fz = load(FROZEN)

    r2, r3 = rs["result4_2"], rs["result4_3"]
    m3 = rs["metrics"]["result4_3"]
    src_run = os.path.join("D:\\MathContest\\C题", "results", "Q4", "experiments", "round3", "run_summary.json")
    src_e44 = os.path.join("D:\\MathContest\\C题", "results", "Q4", "experiments", "optimization", "e44_quantile_sweep.json")
    src_q3 = os.path.join("D:\\MathContest\\C题", "results", "Q3", "reports", "frozen_numbers.json")

    # ---- result4-3 目标 + 成本构成（块级 δ，q=80）----
    for cid, val, loc in [
        ("q4_result4_3_total_cost", r3["objective_value"], "$.result4_3.objective_value"),
        ("q4_result4_3_plan_cost", r3["plan_cost"], "$.result4_3.plan_cost"),
        ("q4_result4_3_penalty_cost", r3["penalty_cost"], "$.result4_3.penalty_cost"),
        ("q4_result4_3_emergency_cost", r3["emergency_cost"], "$.result4_3.emergency_cost"),
    ]:
        set_claim(fz, cid, val, src_run, loc)

    # ---- result4-3 指标（块级 δ）----
    set_claim(fz, "q4_emergency_energy_43", m3["紧急购电_电量kWh"], src_run,
              "$.metrics.result4_3.紧急购电_电量kWh")
    set_claim(fz, "q4_curtailment_rate_43", m3["弃光率"], src_run,
              "$.metrics.result4_3.弃光率")
    set_claim(fz, "q4_curtailment_energy_43", m3["弃光_电量kWh"], src_run,
              "$.metrics.result4_3.弃光_电量kWh")
    set_claim(fz, "q4_storage_min_43", m3["储电量_min"], src_run,
              "$.metrics.result4_3.储电量_min")
    set_claim(fz, "q4_storage_max_43", m3["储电量_max"], src_run,
              "$.metrics.result4_3.储电量_max")

    # ---- q 敏感性（块级 δ，E4-4）----
    set_claim(fz, "q4_quantile_argmin_43", e44["argmin_q"], src_e44, "$.argmin_q")
    set_claim(fz, "q4_quantile_q80_delta_43", e44["q80_vs_argmin_delta"], src_e44,
              "$.q80_vs_argmin_delta")

    # ---- result4-3 恒定 vs 波动电价（Q3 块级 q=80 恒定基准）----
    set_claim(fz, "q4_result4_3_constant", q3f["objective"]["value"], src_q3, "$.objective.value")
    set_claim(fz, "q4_result4_3_fluctuating", r3["objective_value"], src_run,
              "$.result4_3.objective_value")

    # ---- 元数据 ----
    fz["round"] = "round3"
    fz["frozen_at"] = datetime.now(CST).isoformat(timespec="seconds")
    fz["note"] = ("波动电价(附件4)下完全继承 Q2(round4)/Q3(round4 块级) 最终模型仅换电价。"
                  "Q3 光伏风险修正采用 issue×执行块 逐区间 80 分位(块级 δ, 4×36)，"
                  "q=80 为报童临界比 (5-1)/5=0.8 冻结主值；样本内经验 argmin q=85 仅作敏感性参照。"
                  "完美预见(A/B/B4_ref)为诊断基准, 非可执行策略。"
                  "论文全部数值必须引用本文件, 严禁手工编辑。冻结后若规范源变更, 须走 thaw→rerun→refreeze 并记 freeze_change_log.md。")

    with open(FROZEN, "w", encoding="utf-8") as f:
        json.dump(fz, f, ensure_ascii=False, indent=2)

    # ---- freeze_change_log ----
    entry = f"""

## {datetime.now(CST).strftime('%Y-%m-%d')} — 解冻(thaw) → 重跑 → 重冻结(round3)：result4-3 光伏风险修正由「按 issue 标量」升级为「按 issue × 执行块 逐区间」

- **原因(thaw)**：round2 的 result4-3 沿用 round3 标量 δ（`issue_risk_delta`, 每 issue 一个标量 [0,1005.49,-6.27,0]），与 Q3 最终冻结模型（round4 块级，issue×执行块 逐区间 80 分位）**口径不一致**，导致 result4-3(15,759,231.74) 反超 result4-2(15,231,785.59)，出现「MPC 比逐日 LP 更差」的假象。
- **动作(rerun)**：`code/Q4/q4_main.py` 将 result4-3 的 δ 由标量改为块级 `block_delta(over, d, 80.0, MIN_HIST=7)`（形状 4×36，与 `code/Q3/q3_new_methods/q3_optimized.py` 同构），并记录真实储能轨迹 E3_flat；同时补填 result4-2/4-3 模板的「全天购电量(第146列)/全天购电费(第147列)」汇总列。
- **重冻结数值（q=80，与 Q3 块级同分位）**：

| 量 | round2 标量 δ | round3 块级 δ | Δ | Δ% |
|---|---|---|---|---|
| result4-3 总购电费(元) | 15,759,231.74 | **14,694,112.99** | −1,065,118.75 | −6.76% |
| 计划购电费(元) | 12,929,399.19 | 12,758,457.67 | −170,941.52 | −1.32% |
| 违约/溢价(元) | 1,909,943.19 | 1,363,165.14 | −546,778.05 | −28.6% |
| 紧急购电费(元) | 919,889.36 | 572,490.18 | −347,399.18 | −37.8% |
| 紧急购电电量(kWh) | 245,553.35 | 145,152.63 | −100,400.72 | −40.9% |
| 弃光电量(kWh) | 2,821,761.39 | 1,914,784.21 | −906,977.18 | −32.1% |
| 弃光率 | 0.147977 | 0.100414 | — | −4.76pp |

- **排序恢复**：result4-2 = 15,231,785.59 元 > result4-3 = 14,694,112.99 元，MPC+分段计费 优于 逐日滚动 LP，与 Q2/Q3 相对关系一致。
- **分位选型（口径统一）**：**q=80 为冻结主值**（报童临界比 0.8，与 Q2/Q3 一致）；样本内经验 argmin q=85 = 14,667,083.32，仅比 q=80 低 27,029.67 元（0.184%），无理论锚定，作稳健性对照（见 E4-4 `e44_quantile_sweep.json`）。
- **恒定 vs 波动**：result4-3 恒定电价 = 14,049,999.28（Q3 round4 块级 q=80）→ 波动电价 = 14,694,112.99，加价率 +4.59%（与 result4-2 的 +4.62% 一致）。
- **受影响**：`results/Q4/reports/frozen_numbers.json`（round2→round3）；`results/Q4/result4-2.xlsx`、`results/Q4/result4-3.xlsx`（补全天购电量/购电费汇总列）。
"""
    if os.path.exists(LOG):
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        header = "# Q4 冻结变更日志 (freeze_change_log.md)\n\n> 规则：冻结后任何规范源变更须先记录于此，再走 thaw→rerun→refreeze 流程。\n"
        with open(LOG, "w", encoding="utf-8") as f:
            f.write(header + entry)

    print("REFROZEN ->", FROZEN)
    print("  round:", fz["round"], " frozen_at:", fz["frozen_at"])
    for n in fz["numbers"]:
        if "result4_3" in n["claim_id"] or n["claim_id"].startswith("q4_quantile"):
            print(f"  {n['claim_id']:35s} = {n['value']}")


if __name__ == "__main__":
    main()
