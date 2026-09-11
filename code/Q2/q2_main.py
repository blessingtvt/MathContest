# -*- coding: utf-8 -*-
"""Q2 主模型 (M2: 逐日滚动 LP + 净负荷自预报 + 80分位风险修正)。

信息集(修正 2026-09-11): 附件3(光伏预报) 属于 Q3/Q4, Q2 只能用 附件1电价 + 附件2历史。
每天 0:00 决策流程:
  1. 净负荷 N_d = L_d - P_d; 7 天加权平均自预报 N̂_d = Σ w_k N_{d-k};
  2. 历史误差 80 分位 e^80 (仅用 d 之前数据, 因果), 安全净负荷 N^safe = N̂ + e^80;
  3. 单日 LP(净负荷口径) 求当日计划购电 G、充/放电 C/D, 日末循环 S_144 = S_0 = 6000;
  4. 用当日真实净负荷结算, 缺口紧急购电 z(5 倍价)。

费用: C2 = Σ p_t·G_t + 5·Σ p_t·z_t。报告期 2025-02-01 ~ 12-31。
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import *

W = [0.3, 0.2, 0.15, 0.12, 0.1, 0.08, 0.05]
QUANTILE = 80.0


def netload_forecast(N):
    """7 天加权平均净负荷预报 (仅用历史, 因果)。返回 (Nhat, Eerr)。"""
    D = N.shape[0]
    w = np.array(W)
    Nhat = np.zeros_like(N)
    for d in range(len(w), D):
        for k in range(len(w)):
            Nhat[d] += w[k] * N[d - 1 - k]
    return Nhat, N - Nhat


def no_storage_forecast(price, Nsafe, Nreal):
    """B2 基线: 无储能 + 自预报(含风险修正), 缺口紧急购电。返回 (cost, x, z)。"""
    x = np.maximum(Nsafe * DT, 0.0)
    z = np.maximum(Nreal * DT - x, 0.0)
    cost = float((price * x).sum() + ALPHA_EM * (price * z).sum())
    return cost, x, z


def rule_forecast_day(price, Nsafe, Nreal, E_carry):
    """R2 基线: 规则套利(价格阈值) + 自预报, 缺口紧急购电。返回 (cost, x, c, q, E_end, z)。"""
    _, x, c, q, Est = rule_arbitrage(price, Nsafe, np.zeros(T), E0=E_carry)
    z = clip0(np.maximum(Nreal * DT + c - x - q, 0.0))
    cost = float((price * x).sum() + ALPHA_EM * (price * z).sum())
    return cost, x, c, q, Est[-1], z


def main():
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    D = load.shape[0]
    dates = report_dates(b)
    labels = time_labels()
    N = load - pv                       # 净负荷 (kW)
    Nhat, Eerr = netload_forecast(N)

    # ---- 主模型 M2: 逐日滚动 LP + 80 分位风险修正 (日末循环 S_144=S_0) ----
    R = REPORT_DAYS
    Xr = np.zeros((R, T)); Cr = np.zeros((R, T)); Qr = np.zeros((R, T)); Zr = np.zeros((R, T))
    E_seq = [E0_INIT]
    for i, d in enumerate(range(WARMUP_DAYS, D)):
        e80 = np.percentile(Eerr[7:d], QUANTILE, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e80
        _, x_d, c_d, q_d, E_d = daily_lp(price, Nsafe, np.zeros(T), E0=E0_INIT,
                                         terminal_eq=True, E_term=E0_INIT)
        z_d = clip0(np.maximum(N[d] * DT + c_d - x_d - q_d, 0.0))
        Xr[i] = x_d; Cr[i] = c_d; Qr[i] = q_d; Zr[i] = z_d
        E_seq.extend(E_d[1:].tolist())
    Er = np.array(E_seq)                # 长度 R*T+1

    price_r = np.tile(price, (R, 1))
    plan_cost = float((price_r * Xr).sum())
    emergency_cost = float(ALPHA_EM * (price_r * Zr).sum())
    report_cost = plan_cost + emergency_cost

    # ---- 基线 (同信息集: 自预报 + 80 分位风险修正) ----
    b_cost = b_ref_cost = r_cost = 0.0
    Erule = E0_INIT
    for d in range(WARMUP_DAYS, D):
        e80 = np.percentile(Eerr[7:d], QUANTILE, axis=0) if d > 7 else np.zeros(T)
        Nsafe = Nhat[d] + e80
        b_cost += no_storage_forecast(price, Nsafe, N[d])[0]
        b_ref_cost += no_storage(price, load[d], pv[d])[0]
        rc, _, _, _, E_end, _ = rule_forecast_day(price, Nsafe, N[d], Erule)
        r_cost += rc
        Erule = E_end

    # ---- 指标 ----
    emg_int = int((Zr > 1e-8).sum())
    emg_energy = float(Zr.sum())
    supply = Xr + pv[WARMUP_DAYS:] * DT + Qr
    demand = load[WARMUP_DAYS:] * DT + Cr
    curt = clip0(supply - demand)
    curt_int = int((curt > 1e-8).sum())
    curt_energy = float(curt.sum())
    pv_report = float(pv[WARMUP_DAYS:].sum() * DT)

    # ---- 写 result2.xlsx ----
    out_dir = os.path.join(RESULTS_DIR, "Q2")
    os.makedirs(os.path.join(out_dir, "experiments", "round3"), exist_ok=True)
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
        "experiment_id": "round3",
        "method": "M2-daily-rolling-LP+netload-self-forecast+risk-correction(q80)",
        "seed": SEED,
        "status": "success",
        "created_at": datetime.now().isoformat(),
        "data_sources": ["data_clean/cleaned_data.pkl"],
        "report_period": "2025-02-01 ~ 2025-12-31",
        "warmup": "附件2历史(7天加权平均预报 + 历史误差分位, 仅用当日之前数据)",
        "forecast": "净负荷 N=L-P, 7天加权平均 w=[0.3,0.2,0.15,0.12,0.1,0.08,0.05]; 历史误差 80 分位风险修正",
        "information_set_note": "附件3(光伏预报)属 Q3/Q4, 非 Q2; Q2 用附件2历史自预报",
        "approved_decision_id": "q2_method_choice_r3",
        "main": {
            "method_id": "M2",
            "objective_name": "报告期总购电费(元, 含计划+紧急)",
            "objective_value": round(report_cost, 2),
            "plan_cost": round(plan_cost, 2),
            "emergency_cost": round(emergency_cost, 2),
            "outputs": ["results/Q2/result2.xlsx"],
        },
        "baselines": [
            {"id": "B2", "name": "无储能(自预报+80分位)", "objective_value": round(b_cost, 2)},
            {"id": "B2_ref", "name": "无储能(完美预见, 下界)", "objective_value": round(b_ref_cost, 2)},
            {"id": "R2", "name": "规则套利(自预报+80分位)", "objective_value": round(r_cost, 2)},
        ],
        "metrics": {
            "储能价值_元": round(b_cost - report_cost, 2),
            "储能价值_占比": round((b_cost - report_cost) / b_cost, 6),
            "优化价值_元": round(r_cost - report_cost, 2),
            "预报误差成本_无储能": round(b_cost - b_ref_cost, 2),
            "紧急购电_区间数": emg_int,
            "紧急购电_电量kWh": round(emg_energy, 2),
            "紧急购电_占比": round(emg_energy / pv_report, 6),
            "弃光_区间数": curt_int,
            "弃光_电量kWh": round(curt_energy, 2),
            "弃光率": round(curt_energy / pv_report, 6),
            "储电量_min": round(float(Er.min()), 2),
            "储电量_max": round(float(Er.max()), 2),
        },
    }
    with open(os.path.join(out_dir, "experiments", "round3", "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
