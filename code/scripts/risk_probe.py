# -*- coding: utf-8 -*-
"""
G2 风险探针：主候选(LP)与基线(无储能)的可执行性/可行性/退化/扰动/规模
真实运行，输出 methods/Qx/probes/risk_probe_summary.json
"""
import json, time, pickle
import numpy as np
from scipy.optimize import linprog

# 参数
T = 144; dt = 1/6.0
Emin, Emax, Pmax = 1200.0, 10800.0, 5000.0
eta_c, eta_d = 0.9, 0.9
PmaxE = Pmax * dt  # 833.33 kWh/区间

bundle = pickle.load(open("data_clean/cleaned_data.pkl", "rb"))
p1 = bundle["附件1"]["price"]          # 恒定电价 144
L1 = bundle["附件1"]["load"]           # 代表日负载 144
G1 = bundle["附件1"]["pv_forecast"]    # 代表日光伏预测 144
L2 = bundle["附件2_load"]              # 365x144 实际负载
G2 = bundle["附件2_pv"]                # 365x144 实际光伏
p4 = bundle["附件4_price"]             # 365x144 波动电价

def daily_lp(price, load, pv, E0=None, terminal_eq=False):
    """单日 LP。返回 (obj, feasible, runtime, E_end, x_sum)。
    变量: x_t(购), c_t(充), q_t(放), E_0..E_T 共 3T+T+1。"""
    n = 3*T + (T+1)
    c = np.zeros(n)
    c[0:T] = price                      # 目标 min sum p_t x_t
    A_ub, b_ub = [], []
    A_eq, b_eq = [], []
    def idx_x(t): return t
    def idx_c(t): return T + t
    def idx_q(t): return 2*T + t
    def idx_E(t): return 3*T + t        # E_0..E_T
    for t in range(T):
        # 能量平衡: x_t + q_t - c_t >= L*dt - G*dt  =>  -x - q + c <= G*dt - L*dt
        row = np.zeros(n); row[idx_x(t)] = -1; row[idx_q(t)] = -1; row[idx_c(t)] = 1
        A_ub.append(row); b_ub.append(pv[t]*dt - load[t]*dt)
        # 充电功率: c_t <= PmaxE
        row = np.zeros(n); row[idx_c(t)] = 1; A_ub.append(row); b_ub.append(PmaxE)
        # 放电功率: q_t <= PmaxE
        row = np.zeros(n); row[idx_q(t)] = 1; A_ub.append(row); b_ub.append(PmaxE)
        # 储能动态(等式): E_t - E_{t-1} - eta_c*c_t + q_t/eta_d = 0
        row = np.zeros(n); row[idx_E(t+1)] = 1; row[idx_E(t)] = -1
        row[idx_c(t)] = -eta_c; row[idx_q(t)] = 1/eta_d
        A_eq.append(row); b_eq.append(0.0)
    if terminal_eq:
        # Q1 终态: E_T - E_0 = 0
        row = np.zeros(n); row[idx_E(T)] = 1; row[idx_E(0)] = -1
        A_eq.append(row); b_eq.append(0.0)
    bounds = [(0, None)]*(3*T) + [(Emin, Emax)]*(T+1)
    if E0 is not None:
        # 固定初始储电量
        A_eq.append((np.eye(n)[idx_E(0)]).tolist()); b_eq.append(E0)
    t0 = time.time()
    r = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                A_eq=np.array(A_eq), b_eq=np.array(b_eq), bounds=bounds,
                method="highs")
    rt = time.time() - t0
    ok = r.success
    if ok:
        E_end = r.x[idx_E(T)]
        x_sum = r.x[0:T].sum()
        return float(r.fun), ok, rt, float(E_end), float(x_sum)
    return None, ok, rt, None, None

def baseline_no_storage(load, pv):
    """无储能基线: x_t = max(L*dt - G*dt, 0)。返回总购电费。"""
    return float(np.maximum(load*dt - pv*dt, 0.0).sum() * 0)  # 占位，下面按电价算

def no_storage_cost(price, load, pv):
    x = np.maximum(load*dt - pv*dt, 0.0)
    return float((price * x).sum())

print("=== Q1 LP (代表日, 终态相等) ===")
obj1, ok1, rt1, e_end1, xsum1 = daily_lp(p1, L1, G1, terminal_eq=True)
print("obj(元):", round(obj1,2), "feasible:", ok1, "runtime(s):", round(rt1,4),
      "E_end:", round(e_end1,1), "E0:", None, "x_sum(kWh):", round(xsum1,1))
# 基线
base1 = no_storage_cost(p1, L1, G1)
print("基线无储能 Q1 cost(元):", round(base1,2))

print()
print("=== Q2 全年逐日 LP (完美预见, 储能跨日) ===")
t0 = time.time()
Ecarry = 6000.0
total2 = 0.0; feasible_all = True
for d in range(365):
    obj, ok, rt, e_end, xsum = daily_lp(p1, L2[d], G2[d], E0=Ecarry, terminal_eq=False)
    if not ok: feasible_all = False; break
    total2 += obj; Ecarry = e_end
rt_year = time.time() - t0
print("全年购电费(元):", round(total2,2), "feasible:", feasible_all,
      "全年求解(s):", round(rt_year,2), "日均(ms):", round(rt_year/365*1000,2))
# 基线
base2 = sum(no_storage_cost(p1, L2[d], G2[d]) for d in range(365))
print("基线无储能 Q2 全年费用(元):", round(base2,2))

print()
print("=== 扰动敏感性 (Q1 电价±5%, 负载±5%) ===")
for name, pr, lo in [("price+5%", p1*1.05, L1), ("price-5%", p1*0.95, L1),
                     ("load+5%", p1, L1*1.05), ("load-5%", p1, L1*0.95)]:
    o, ok, rt, e, xs = daily_lp(pr, lo, G1, terminal_eq=True)
    print(f"{name}: cost={round(o,2)} (Δ {round((o-obj1)/obj1*100,2)}%)")

print()
print("=== 规模检查 ===")
n_q1 = 3*T + (T+1)
print("Q1 变量数:", n_q1, "| Q2 全年(逐日):", n_q1, "x 365 =", n_q1*365, "次独立LP")
print("Q3 滚动(4次/日):", n_q1, "x 365 x 4 次")

# 输出 JSON
summary = {
  "schema_version": 1, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
  "data_refs": ["data/data_report.md"],
  "params": {"T":T, "dt_hr":dt, "Emin":Emin, "Emax":Emax, "Pmax":Pmax,
             "eta_c":eta_c, "eta_d":eta_d, "E0":6000},
  "q1_main": {"cost_yuan": obj1, "feasible": ok1, "runtime_s": rt1, "E_end": e_end1},
  "q1_baseline_no_storage": {"cost_yuan": base1},
  "q2_main_year": {"cost_yuan": total2, "feasible": feasible_all, "runtime_s": rt_year},
  "q2_baseline_no_storage": {"cost_yuan": base2},
}
os.makedirs if False else None
import os; os.makedirs("methods", exist_ok=True)
json.dump(summary, open("code/scripts/probe_raw.json","w"), ensure_ascii=False, indent=2)
print("\nprobe_raw.json saved")
