# -*- coding: utf-8 -*-
"""G4 数值冻结 (solution-package-builder)。

本脚本是 frozen_numbers.json 的唯一生成源: 读取各 Qx 的 run_summary.json /
baseline_metrics.json, 原样转写为冻结文件。**禁止手工编辑任何 frozen 文件**;
数值若有变化, 只改代码重跑, 再由本脚本重写。

输出:
  results/Qx/reports/frozen_numbers.json   (每子题)
  results/frozen_numbers.json              (论文权威总表, 全部数值的唯一来源)
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import ROOT, RESULTS_DIR

QUARTERS = ["Q1", "Q2", "Q3", "Q4"]


def load_rs(q):
    p = os.path.join(RESULTS_DIR, q, "experiments", "round1", "run_summary.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_base(q):
    p = os.path.join(RESULTS_DIR, q, "experiments", "round1", "baseline_metrics.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build_q1():
    rs = load_rs("Q1")
    m = rs["main"]
    b = rs["baselines"]
    return {
        "schema_version": 1,
        "question_id": "Q1",
        "frozen_at": datetime.now().isoformat(),
        "method": rs["method"],
        "seed": rs["seed"],
        "period": "代表日(附件1, 144区间)",
        "objective": {
            "name": m["objective_name"], "unit": "元", "value": m["objective_value"],
        },
        "key_quantities": {
            "total_purchase_kwh": m["total_purchase_kwh"],
            "total_charge_kwh": m["total_charge_kwh"],
            "total_discharge_kwh": m["total_discharge_kwh"],
            "terminal_E0_kwh": rs["terminal"]["E0"],
            "terminal_ET_kwh": rs["terminal"]["E_T"],
        },
        "baselines": b,
        "metrics": rs["metrics"],
    }


def build_q2():
    rs = load_rs("Q2")
    m = rs["main"]
    b = rs["baselines"]
    return {
        "schema_version": 1,
        "question_id": "Q2",
        "frozen_at": datetime.now().isoformat(),
        "method": rs["method"],
        "seed": rs["seed"],
        "period": rs["report_period"],
        "objective": {
            "name": m["objective_name"], "unit": "元", "value": m["objective_value"],
        },
        "key_quantities": {
            "full_year_cost_yuan": m["full_year_cost"],
            "emergency_cost_yuan": m["emergency_cost"],
        },
        "baselines": b,
        "metrics": rs["metrics"],
    }


def build_q3():
    rs = load_rs("Q3")
    m = rs["main"]
    b = rs["baselines"]
    return {
        "schema_version": 1,
        "question_id": "Q3",
        "frozen_at": datetime.now().isoformat(),
        "method": rs["method"],
        "seed": rs["seed"],
        "period": rs["report_period"],
        "objective": {
            "name": m["objective_name"], "unit": "元", "value": m["objective_value"],
        },
        "cost_breakdown": {
            "plan_cost_yuan": m["plan_cost"],
            "penalty_cost_yuan": m["penalty_cost"],
            "emergency_cost_yuan": m["emergency_cost"],
        },
        "baselines": b,
        "metrics": rs["metrics"],
    }


def build_q4():
    rs = load_rs("Q4")
    b = rs["baselines"]
    return {
        "schema_version": 1,
        "question_id": "Q4",
        "frozen_at": datetime.now().isoformat(),
        "method": rs["method"],
        "seed": rs["seed"],
        "period": rs["report_period"],
        "result4_2": {"name": rs["result4_2"]["objective_name"], "unit": "元",
                      "value": rs["result4_2"]["objective_value"]},
        "result4_3": {"name": rs["result4_3"]["objective_name"], "unit": "元",
                      "value": rs["result4_3"]["objective_value"]},
        "baselines": b,
        "metrics": {},
    }


BUILDERS = {"Q1": build_q1, "Q2": build_q2, "Q3": build_q3, "Q4": build_q4}


def main():
    per_q = {}
    for q in QUARTERS:
        doc = BUILDERS[q]()
        per_q[q] = doc
        out_dir = os.path.join(RESULTS_DIR, q, "reports")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "frozen_numbers.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    # 论文权威总表
    consolidated = {
        "schema_version": 1,
        "frozen_at": datetime.now().isoformat(),
        "seed": 2026,
        "report_period": "2025-02-01 ~ 2025-12-31",
        "note": "论文全部数值的唯一权威来源, 禁止手工编辑",
        "parameters": {
            "T": 144, "delta_t_h": 1.0 / 6.0,
            "E_min_kwh": 1200.0, "E_max_kwh": 10800.0, "E0_kwh": 6000.0,
            "P_max_kw": 5000.0, "eta_c": 0.9, "eta_d": 0.9,
            "alpha_em": 5.0, "beta_pen": 0.5, "gamma_pre": 1.5,
        },
        "results": per_q,
    }
    with open(os.path.join(RESULTS_DIR, "frozen_numbers.json"), "w", encoding="utf-8") as f:
        json.dump(consolidated, f, ensure_ascii=False, indent=2)

    # 简明可读总表 (供 G5 论文引用与人工复核)
    lines = [
        "# 冻结数值总表 (frozen numbers, 权威来源)",
        "",
        "> 生成自 `code/scripts/freeze_numbers.py`, 禁止手工编辑。",
        f"> 冻结时间: {consolidated['frozen_at']}",
        "",
        "| 子题 | 主模型 | 目标值(元) | 基线B(无储能) | 基线R(规则套利) |",
        "|---|---|---|---|---|",
    ]
    r = per_q
    lines.append(f"| Q1 | M1-LP | {r['Q1']['objective']['value']} | {r['Q1']['baselines'][0]['objective_value']} | {r['Q1']['baselines'][1]['objective_value']} |")
    lines.append(f"| Q2 | M2-全年联合LP | {r['Q2']['objective']['value']} | {r['Q2']['baselines'][0]['objective_value']} | {r['Q2']['baselines'][1]['objective_value']} |")
    lines.append(f"| Q3 | M3-MPC | {r['Q3']['objective']['value']} | {r['Q3']['baselines'][0]['objective_value']} | {r['Q3']['baselines'][1]['objective_value']} |")
    lines.append(f"| Q4-2 | M4-LP(波动电价) | {r['Q4']['result4_2']['value']} | {r['Q4']['baselines'][0]['objective_value']} | {r['Q4']['baselines'][1]['objective_value']} |")
    lines.append(f"| Q4-3 | M4-MPC(波动电价) | {r['Q4']['result4_3']['value']} | — | — |")
    with open(os.path.join(RESULTS_DIR, "frozen_numbers.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps(consolidated, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
