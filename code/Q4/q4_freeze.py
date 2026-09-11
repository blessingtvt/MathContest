# -*- coding: utf-8 -*-
"""Q4 数值冻结生成器 (solution-package-builder 冻结步骤)。

从 canonical 源 (run_summary.json / q4_robustness_summary.json) 程序化生成
results/Q4/reports/frozen_numbers.json。此文件严禁手工编辑; 若源变更须走
thaw→rerun→refreeze 流程并记 freeze_change_log.md。
"""
import json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(ROOT, "results", "Q4", "experiments", "round2", "run_summary.json")
ROB = os.path.join(ROOT, "robustness", "Q4", "q4_robustness_summary.json")
OUT = os.path.join(ROOT, "results", "Q4", "reports", "frozen_numbers.json")

run = json.load(open(RUN, encoding="utf-8"))
rob = json.load(open(ROB, encoding="utf-8"))
m42 = run["metrics"]["result4_2"]
m43 = run["metrics"]["result4_3"]
r3 = rob["R3_constant_vs_fluctuating"]
r1 = rob["R1_quantile_sweep"]

S = "$.{}"  # 便于 source_locator 拼写


def n(cid, val, unit, sf, loc):
    return {"claim_id": cid, "value": val, "unit": unit, "source_file": sf, "source_locator": loc}


numbers = [
    # result4-2 (Q2 模型 + 波动电价)
    n("q4_result4_2_total_cost", run["result4_2"]["objective_value"], "元", RUN, "$.result4_2.objective_value"),
    n("q4_result4_2_plan_cost", run["result4_2"]["plan_cost"], "元", RUN, "$.result4_2.plan_cost"),
    n("q4_result4_2_emergency_cost", run["result4_2"]["emergency_cost"], "元", RUN, "$.result4_2.emergency_cost"),
    # result4-3 (Q3 模型 + 波动电价)
    n("q4_result4_3_total_cost", run["result4_3"]["objective_value"], "元", RUN, "$.result4_3.objective_value"),
    n("q4_result4_3_plan_cost", run["result4_3"]["plan_cost"], "元", RUN, "$.result4_3.plan_cost"),
    n("q4_result4_3_penalty_cost", run["result4_3"]["penalty_cost"], "元", RUN, "$.result4_3.penalty_cost"),
    n("q4_result4_3_emergency_cost", run["result4_3"]["emergency_cost"], "元", RUN, "$.result4_3.emergency_cost"),
    # 基线
    n("q4_baseline_B4", run["baselines"][0]["objective_value"], "元", RUN, "$.baselines[0].objective_value"),
    n("q4_baseline_R4", run["baselines"][1]["objective_value"], "元", RUN, "$.baselines[1].objective_value"),
    n("q4_baseline_B4_ref", run["baselines"][2]["objective_value"], "元", RUN, "$.baselines[2].objective_value"),
    # 诊断参照 (储能完美预见)
    n("q4_diag_A_storage_perfect_daily", run["diagnostics"][0]["objective_value"], "元", RUN, "$.diagnostics[0].objective_value"),
    n("q4_diag_B_storage_perfect_free", run["diagnostics"][1]["objective_value"], "元", RUN, "$.diagnostics[1].objective_value"),
    # result4-2 价值分解
    n("q4_storage_value", m42["储能价值_元"], "元", RUN, "$.metrics.result4_2.储能价值_元"),
    n("q4_optimization_value", m42["优化价值_元"], "元", RUN, "$.metrics.result4_2.优化价值_元"),
    n("q4_forecast_error_cost_no_storage", m42["预报误差成本_无储能侧_元"], "元", RUN, "$.metrics.result4_2.预报误差成本_无储能侧_元"),
    n("q4_forecast_error_cost_storage", m42["预报误差成本_储能侧_元"], "元", RUN, "$.metrics.result4_2.预报误差成本_储能侧_元"),
    n("q4_day_closure_cost", m42["日闭合约束成本_元"], "元", RUN, "$.metrics.result4_2.日闭合约束成本_元"),
    n("q4_perfect_foresight_total_value", m42["完美预见总价值_储能侧_元"], "元", RUN, "$.metrics.result4_2.完美预见总价值_储能侧_元"),
    # 运行指标
    n("q4_emergency_energy_42", m42["紧急购电_电量kWh"], "kWh", RUN, "$.metrics.result4_2.紧急购电_电量kWh"),
    n("q4_curtailment_rate_42", m42["弃光率"], "无量纲", RUN, "$.metrics.result4_2.弃光率"),
    n("q4_emergency_energy_43", m43["紧急购电_电量kWh"], "kWh", RUN, "$.metrics.result4_3.紧急购电_电量kWh"),
    n("q4_curtailment_rate_43", m43["弃光率"], "无量纲", RUN, "$.metrics.result4_3.弃光率"),
    # 稳健性 R1 (q 扫描)
    n("q4_quantile_argmin_42", r1["argmin_q_result4_2"], "分位(%)", ROB, "$.R1_quantile_sweep.argmin_q_result4_2"),
    n("q4_quantile_argmin_43", r1["argmin_q_result4_3"], "分位(%)", ROB, "$.R1_quantile_sweep.argmin_q_result4_3"),
    n("q4_quantile_q80_delta_42", r1["q80_vs_argmin_result4_2_delta"], "元", ROB, "$.R1_quantile_sweep.q80_vs_argmin_result4_2_delta"),
    n("q4_quantile_q0_42", r1["result4_2_total_by_q"]["0"], "元", ROB, "$.R1_quantile_sweep.result4_2_total_by_q.0"),
    n("q4_quantile_q90_42", r1["result4_2_total_by_q"]["90"], "元", ROB, "$.R1_quantile_sweep.result4_2_total_by_q.90"),
    n("q4_quantile_q100_42", r1["result4_2_total_by_q"]["100"], "元", ROB, "$.R1_quantile_sweep.result4_2_total_by_q.100"),
    # 稳健性 R3 (恒定 vs 波动)
    n("q4_result4_2_constant", r3["result4_2_constant"], "元", ROB, "$.R3_constant_vs_fluctuating.result4_2_constant"),
    n("q4_storage_value_constant", r3["storage_value_constant"], "元", ROB, "$.R3_constant_vs_fluctuating.storage_value_constant"),
    n("q4_storage_value_fluctuating", r3["storage_value_fluctuating"], "元", ROB, "$.R3_constant_vs_fluctuating.storage_value_fluctuating"),
    n("q4_storage_arbitrage_space_constant", r3["storage_arbitrage_space_constant"], "元", ROB, "$.R3_constant_vs_fluctuating.storage_arbitrage_space_constant"),
    n("q4_storage_arbitrage_space_fluctuating", r3["storage_arbitrage_space_fluctuating"], "元", ROB, "$.R3_constant_vs_fluctuating.storage_arbitrage_space_fluctuating"),
    n("q4_forecast_error_cost_storage_constant", r3["forecast_error_cost_storage_constant"], "元", ROB, "$.R3_constant_vs_fluctuating.forecast_error_cost_storage_constant"),
    n("q4_forecast_error_cost_storage_fluctuating", r3["forecast_error_cost_storage_fluctuating"], "元", ROB, "$.R3_constant_vs_fluctuating.forecast_error_cost_storage_fluctuating"),
    n("q4_day_closure_cost_constant", r3["day_closure_cost_constant"], "元", ROB, "$.R3_constant_vs_fluctuating.day_closure_cost_constant"),
]

frozen = {
    "schema_version": 1,
    "question_id": "Q4",
    "frozen_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "frozen_by_skill": "solution-package-builder",
    "decision_id": "q4_package_signoff",
    "signoff_status": "confirmed_keep",
    "round": "round2",
    "seed": 2026,
    "method": "M4-inherit-Q2/Q3-final+fluctuating-price",
    "note": "波动电价(附件4)下完全继承 Q2(round4)/Q3(round3) 最终模型仅换电价。完美预见(A/B/B4_ref)为诊断基准, 非可执行策略。论文全部数值必须引用本文件, 严禁手工编辑。冻结后若规范源变更, 须走 thaw→rerun→refreeze 并记 freeze_change_log.md。",
    "numbers": numbers,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(frozen, f, ensure_ascii=False, indent=2)
print("frozen_numbers.json written:", OUT)
print("total claims:", len(numbers))
