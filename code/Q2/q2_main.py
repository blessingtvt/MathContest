# -*- coding: utf-8 -*-
"""Q2 主模型 (M2: 日前计划 + 紧急购电, 非完美预见 HD3)。

每天 0:00 用附件3 0:00 光伏预报制定当日计划 (x, c, q), 负载用附件2 实际值(已知);
储能跨日连续(全年联合 LP)。实际光伏(附件2)与预报的偏差由紧急购电 z(5倍价)吸收。
计划购电费按计划量结算, 紧急购电费按 5 倍价结算:
  cost = Σ p_t·x_t + 5·Σ p_t·z_t,  z_t = max(L_t·Δt + c_t − x_t − G_t^实际·Δt − q_t, 0)

报告期 2025-02-01 ~ 2025-12-31; 1 月预热(HD5)。
终态约束 E(12-31 24:00)=6000 消除年末倒空(end-of-horizon)。
输出: results/Q2/result2.xlsx + experiments/round1/run_summary.json
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import *


def rule_dayahead_day(price, load_d, pv_actual, forecast, d, E_carry):
    """R2 基线: 规则套利 + 0:00 日前预报(与 M2 同信息), 预报误差由紧急购电吸收。

    返回 (cost, x, c, q, E_end, z)。
    """
    ghat0 = forecast_intervals(forecast, d, 0)
    _, x, c, q, Est = rule_arbitrage(price, load_d, ghat0, E0=E_carry)
    z = clip0(np.maximum(load_d * DT + c - x - pv_actual * DT - q, 0.0))
    cost = float((price * x).sum() + ALPHA_EM * (price * z).sum())
    return cost, x, c, q, Est[-1], z


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]        # (365,144) 实际负载 (已知/确定性)
    pv = b["附件2_pv"]            # (365,144) 实际光伏 (结算用)
    fc = b["附件3"]["forecast"]   # (1460,24) 滚动光伏预报
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()

    # ---- 0:00 日前光伏预报 (每天取 forecast[d, 0, :]) ----
    ghat0 = np.zeros((D, T))
    for d in range(D):
        ghat0[d] = forecast_intervals(fc, d, 0)

    # ---- 主模型 M2: 全年联合 LP (计划用日前预报, 终态闭合) ----
    price_flat = np.tile(price, D)
    load_flat = load.reshape(-1)
    pv_flat = pv.reshape(-1)
    _, X, C, Q, E = full_year_lp(price_flat, load_flat, ghat0.reshape(-1),
                                 E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)

    # ---- 紧急购电: 实际光伏与计划的偏差, 5 倍价 ----
    x_flat = X.reshape(-1); c_flat = C.reshape(-1); q_flat = Q.reshape(-1)
    Z_flat = clip0(np.maximum(load_flat * DT + c_flat - x_flat - pv_flat * DT - q_flat, 0.0))
    Z = Z_flat.reshape(D, T)

    # ---- 报告期切片 (索引 31..364) ----
    Xr, Cr, Qr, Zr = X[WARMUP_DAYS:], C[WARMUP_DAYS:], Q[WARMUP_DAYS:], Z[WARMUP_DAYS:]
    Er = E[WARMUP_DAYS * T:]
    price_r = np.tile(price, (REPORT_DAYS, 1))
    plan_cost = float((price_r * Xr).sum())
    emergency_cost = float(ALPHA_EM * (price_r * Zr).sum())
    report_cost = plan_cost + emergency_cost

    # ---- 基线 ----
    # B2 无储能 + 日前预报 + 紧急 (与 M2 同信息, 公平对比)
    b_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        b_cost += no_storage_dayahead(price, load[d], pv[d], fc, d)[0]
    # B2_old 无储能 + 完美预见 (参考下界, 无预报误差)
    b_old_cost = 0.0
    for d in range(WARMUP_DAYS, D):
        b_old_cost += no_storage(price, load[d], pv[d])[0]
    r_cost = 0.0
    Erule = E0_INIT
    for d in range(D):
        cost_d, _, _, _, E_end, _ = rule_dayahead_day(price, load[d], pv[d], fc, d, Erule)
        Erule = E_end
        if d >= WARMUP_DAYS:
            r_cost += cost_d

    # ---- 校验指标 ----
    emg_int = int((Zr > 1e-8).sum())
    emg_energy = float(Zr.sum())
    # 实际弃光: 实际供给 - 实际需求 > 0 (光伏富余, 非购电)
    supply = Xr + pv[WARMUP_DAYS:] * DT + Qr
    demand = load[WARMUP_DAYS:] * DT + Cr
    curt = clip0(supply - demand)
    curt_int = int((curt > 1e-8).sum())
    curt_energy = float(curt.sum())
    pv_report = float(pv[WARMUP_DAYS:].sum() * DT)
    E_all = np.asarray(E)

    # ---- 写 result2.xlsx ----
    out_dir = os.path.join(RESULTS_DIR, "Q2")
    os.makedirs(os.path.join(out_dir, "experiments", "round1"), exist_ok=True)
    out_path = os.path.join(out_dir, "result2.xlsx")
    wb = openpyxl.load_workbook(os.path.join(TEMPLATE_DIR, "result2.xlsx"))
    fill_plan_grid(wb["计划购电量"], Xr)
    rebuild_charge_sheet(wb["充放电量"], dates, Cr, Qr, Er)
    rebuild_emergency_sheet(wb["紧急购电量"], dates, Zr, labels)
    wb.save(out_path)

    # ---- run_summary.json ----
    summary = {
        "schema_version": 1,
        "question_id": "Q2",
        "experiment_id": "round1",
        "method": "M2-day-ahead-LP+emergency",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "data_sources": ["data_clean/cleaned_data.pkl"],
        "report_period": "2025-02-01 ~ 2025-12-31",
        "warmup": "2025-01-01 ~ 2025-01-31 (31天, HD5)",
        "forecast": "附件3 0:00 日前预报 (非完美预见), 负载用附件2实际值",
        "main": {
            "method_id": "M2",
            "objective_name": "报告期总购电费(元, 含计划+紧急)",
            "objective_value": round(report_cost, 2),
            "plan_cost": round(plan_cost, 2),
            "emergency_cost": round(emergency_cost, 2),
            "outputs": ["results/Q2/result2.xlsx"],
        },
        "baselines": [
            {"id": "B2", "name": "无储能(日前预报+紧急)", "objective_value": round(b_cost, 2)},
            {"id": "B2_ref", "name": "无储能(完美预见, 下界)", "objective_value": round(b_old_cost, 2)},
            {"id": "R2", "name": "规则套利(日前预报)", "objective_value": round(r_cost, 2)},
        ],
        "metrics": {
            "储能价值_元": round(b_cost - report_cost, 2),
            "储能价值_占比": round((b_cost - report_cost) / b_cost, 6),
            "优化价值_元": round(r_cost - report_cost, 2),
            "预报误差成本_无储能": round(b_cost - b_old_cost, 2),
            "紧急购电_区间数": emg_int,
            "紧急购电_电量kWh": round(emg_energy, 2),
            "紧急购电_占比": round(emg_energy / pv_report, 6),
            "弃光_区间数": curt_int,
            "弃光_电量kWh": round(curt_energy, 2),
            "弃光率": round(curt_energy / pv_report, 6),
            "储电量_min": round(float(E_all.min()), 2),
            "储电量_max": round(float(E_all.max()), 2),
            "终态储电量": round(float(E_all[-1]), 2),
        },
    }
    with open(os.path.join(out_dir, "experiments", "round1", "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
