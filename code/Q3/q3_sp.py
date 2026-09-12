# -*- coding: utf-8 -*-
"""Q3 多阶段随机规划 (SP) 试验。

两阶段 SP（单日）:
  阶段 0（here-and-now, 0:00）: 计划 x[0:144]、c0/q0/E0，用 0:00 预报 Ĝ0 + 场景误差分布；
  阶段 1（recourse, 6/12/18）: 调整 y1/y2/y3、c/q/E，用各 issue 预报 Ĝ1/Ĝ2/Ĝ3；
    紧急购电 z 用场景实际光伏 G^ω（5 倍价）。
目标 = 期望总购电费（分段计费 β=0.5/γ=1.5 + α_em=5 紧急），非预见性由「阶段 0 决策全场景共享」保证。

产出：RP（here-and-now 期望值）、WS（wait-and-see 完美预见）、EEV（期望值解）→ EVPI/VSS；
随后滚动全年做**出样本**评估，与区间修正顺序法基线对比。
"""
import os, sys, json
import numpy as np
from scipy.optimize import linprog
from scipy import sparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # code/
from common import *

MIN_HIST = 7  # 风险修正/场景生成所需的最小历史天数


# ----------------------------------------------------------------------
# 场景生成（块 bootstrap：从历史 <d 借 0:00 预报误差模式，保留跨块相关）
# ----------------------------------------------------------------------
def day0_forecast_error(fc, pv):
    """0:00 预报误差 Ĝ0 − G 全 144 区间，形状 (D,144)。"""
    D = pv.shape[0]
    err = np.zeros((D, T))
    for d in range(D):
        err[d] = forecast_intervals(fc, d, 0) - pv[d]
    return err


def gen_scenarios(fc, day0_err, d, n, rng):
    """生成 day d 的 n 个实际光伏场景 G^ω（causal，仅用 [MIN_HIST,d) 历史）。"""
    g0 = forecast_intervals(fc, d, 0)
    hist = day0_err[MIN_HIST:d]
    if len(hist) == 0:
        return np.tile(clip0(g0), (n, 1))
    idx = rng.integers(0, len(hist), size=n)
    return clip0(g0[None, :] - hist[idx])  # (n,144)


# ----------------------------------------------------------------------
# 单日两阶段 SP 线性规划（确定性等价）
# ----------------------------------------------------------------------
def sp_day_lp(price, load_d, g0, g1, g2, g3, scen_G, E_carry, E_term=E0_INIT):
    """求解单日 SP 的确定性等价 LP。

    返回 (rp_cost, dict)。rp_cost 为 here-and-now 的期望总购电费（含分段计费 + 紧急）。
    """
    N = scen_G.shape[0]

    # ---- 变量偏移表 ----
    O = {}
    cur = 0
    for name, n in [("x", T), ("c0", T), ("q0", T), ("E0", T + 1),
                    ("y1", 108), ("c1", 108), ("q1", 108), ("E1", 109),
                    ("y2", 72), ("c2", 72), ("q2", 72), ("E2", 73),
                    ("y3", 36), ("c3", 36), ("q3", 36), ("E3", 37),
                    ("b", T), ("z", T * N)]:
        O[name] = cur
        cur += n
    n_tot = cur

    # ---- 目标 ----
    cobj = np.zeros(n_tot)
    cobj[O["b"]:O["b"] + T] = price
    cobj[O["z"]:O["z"] + T * N] = np.tile(ALPHA_EM * price / N, N)

    # ---- 边界 ----
    bounds = [(0, None)] * n_tot
    for name, n in [("E0", T + 1), ("E1", 109), ("E2", 73), ("E3", 37)]:
        for k in range(n):
            bounds[O[name] + k] = (EMIN, EMAX)

    # ---- 约束累加器 ----
    ub_rows, ub_cols, ub_vals, ub_rhs = [], [], [], []
    eq_rows, eq_cols, eq_vals, eq_rhs = [], [], [], []
    _r = [0, 0]  # ub, eq 行号

    def U(entries, rhs):
        r = _r[0]
        for c, v in entries:
            if v:
                ub_rows.append(r); ub_cols.append(c); ub_vals.append(v)
        ub_rhs.append(rhs); _r[0] += 1

    def E(entries, rhs):
        r = _r[1]
        for c, v in entries:
            if v:
                eq_rows.append(r); eq_cols.append(c); eq_vals.append(v)
        eq_rhs.append(rhs); _r[1] += 1

    def exec_off(t):
        """执行方案 t 区间对应的 (y,c,q) 变量全局偏移。"""
        if t < 36:
            return O["x"] + t, O["c0"] + t, O["q0"] + t
        if t < 72:
            return O["y1"] + t - 36, O["c1"] + t - 36, O["q1"] + t - 36
        if t < 108:
            return O["y2"] + t - 72, O["c2"] + t - 72, O["q2"] + t - 72
        return O["y3"] + t - 108, O["c3"] + t - 108, O["q3"] + t - 108

    # ---- 阶段 0（0:00 计划，预报 g0）----
    for t in range(T):
        U([(O["x"] + t, -1.0), (O["q0"] + t, -1.0), (O["c0"] + t, 1.0)],
          g0[t] * DT - load_d[t] * DT)                       # 能量平衡
        E([(O["E0"] + t + 1, 1.0), (O["E0"] + t, -1.0),
           (O["c0"] + t, -ETA_C), (O["q0"] + t, 1.0 / ETA_D)], 0.0)  # 储能动态
    E([(O["E0"] + 0, 1.0)], E_carry)
    E([(O["E0"] + T, 1.0)], E_term)

    # ---- 阶段 1/2/3（6/12/18 调整，预报 g1/g2/g3）----
    for name_y, name_c, name_q, name_E, M, base_t, ghat, E_from in [
            ("y1", "c1", "q1", "E1", 108, 36, g1, ("E0", 36)),
            ("y2", "c2", "q2", "E2", 72, 72, g2, ("E1", 36)),
            ("y3", "c3", "q3", "E3", 36, 108, g3, ("E2", 36))]:
        for j in range(M):
            t = base_t + j
            U([(O[name_y] + j, -1.0), (O[name_q] + j, -1.0), (O[name_c] + j, 1.0)],
              ghat[t] * DT - load_d[t] * DT)
            E([(O[name_E] + j + 1, 1.0), (O[name_E] + j, -1.0),
               (O[name_c] + j, -ETA_C), (O[name_q] + j, 1.0 / ETA_D)], 0.0)
        E([(O[name_E] + 0, 1.0), (O[E_from[0]] + E_from[1], -1.0)], 0.0)  # 与上一段储能衔接
        E([(O[name_E] + M, 1.0)], E_term)

    # ---- 分段计费线性化 b_t ≥ max(0.5x+0.5y, -0.5x+1.5y) ----
    for t in range(T):
        yo, _, _ = exec_off(t)
        U([(O["x"] + t, 0.5), (yo, 0.5), (O["b"] + t, -1.0)], 0.0)
        U([(O["x"] + t, -0.5), (yo, 1.5), (O["b"] + t, -1.0)], 0.0)

    # ---- 紧急购电 z^ω ≥ 缺口（场景实际光伏结算）----
    for w in range(N):
        for t in range(T):
            yo, co, qo = exec_off(t)
            U([(O["z"] + w * T + t, -1.0), (co, 1.0), (yo, -1.0), (qo, -1.0)],
              scen_G[w, t] * DT - load_d[t] * DT)

    A_ub = sparse.coo_matrix((ub_vals, (ub_rows, ub_cols)), shape=(_r[0], n_tot)).tocsr()
    A_eq = sparse.coo_matrix((eq_vals, (eq_rows, eq_cols)), shape=(_r[1], n_tot)).tocsr()
    b_ub = np.array(ub_rhs)
    b_eq = np.array(eq_rhs)

    res = linprog(cobj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError("sp_day_lp infeasible: " + res.message)
    v = res.x
    y_exec = np.concatenate([
        v[O["x"]:O["x"] + 36],
        v[O["y1"]:O["y1"] + 36],
        v[O["y2"]:O["y2"] + 36],
        v[O["y3"]:O["y3"] + 36],
    ])
    c_exec = np.concatenate([
        v[O["c0"]:O["c0"] + 36],
        v[O["c1"]:O["c1"] + 36],
        v[O["c2"]:O["c2"] + 36],
        v[O["c3"]:O["c3"] + 36],
    ])
    q_exec = np.concatenate([
        v[O["q0"]:O["q0"] + 36],
        v[O["q1"]:O["q1"] + 36],
        v[O["q2"]:O["q2"] + 36],
        v[O["q3"]:O["q3"] + 36],
    ])
    out = {
        "rp_cost": float(res.fun),
        "x": v[O["x"]:O["x"] + T],
        "y_exec": y_exec,
        "c_exec": c_exec,
        "q_exec": q_exec,
        "z_mean": v[O["z"]:O["z"] + T * N].reshape(N, T).mean(axis=0),
    }
    return out["rp_cost"], out


def realize_cost(price, load_d, pv_actual, x, y_exec, c_exec, q_exec):
    """用实际光伏结算：分段计费 + 5 倍紧急购电（出样本真实成本）。"""
    z = clip0(load_d * DT + c_exec - y_exec - pv_actual * DT - q_exec)
    bill = price * (np.minimum(x, y_exec)
                    + BETA_PEN * np.maximum(x - y_exec, 0.0)
                    + GAMMA_PRE * np.maximum(y_exec - x, 0.0))
    return float(bill.sum() + ALPHA_EM * (price * z).sum())


def ws_day(price, load_d, scen_G, E_carry, E_term=E0_INIT):
    """wait-and-see：平均完美预见成本（每个场景用实际 G 单独求解日 LP）。"""
    costs = [daily_lp(price, load_d, scen_G[w], E0=E_carry,
                      terminal_eq=True, E_term=E_term)[0] for w in range(scen_G.shape[0])]
    return float(np.mean(costs))


# ----------------------------------------------------------------------
# 全年滚动出样本评估
# ----------------------------------------------------------------------
def sp_year(n_scen=30):
    """全年滚动 SP：每日解 SP 拿 here-and-now 计划，用实际光伏出样本结算。

    返回 (sp_realized, ws_realized, rp_expected)。
    """
    b = load_bundle()
    price = b["附件1"]["price"]
    load = b["附件2_load"]
    pv = b["附件2_pv"]
    fc = b["附件3"]["forecast"]
    D = load.shape[0]
    rng = np.random.default_rng(SEED)
    day0_err = day0_forecast_error(fc, pv)

    sp_real = 0.0
    ws_real = 0.0
    rp_exp = 0.0
    for d in range(WARMUP_DAYS, D):
        scen_G = gen_scenarios(fc, day0_err, d, n_scen, rng)
        g0 = forecast_intervals(fc, d, 0)
        g1 = forecast_intervals(fc, d, 1)
        g2 = forecast_intervals(fc, d, 2)
        g3 = forecast_intervals(fc, d, 3)
        rp, out = sp_day_lp(price, load[d], g0, g1, g2, g3, scen_G, E0_INIT)
        sp_real += realize_cost(price, load[d], pv[d], out["x"], out["y_exec"],
                                out["c_exec"], out["q_exec"])
        ws_real += daily_lp(price, load[d], pv[d], E0=E0_INIT,
                            terminal_eq=True, E_term=E0_INIT)[0]
        rp_exp += rp
    return sp_real, ws_real, rp_exp


def main():
    import time
    t0 = time.time()
    n_scen = 30
    sp_real, ws_real, rp_exp = sp_year(n_scen)
    print(f"N={n_scen}  elapsed={time.time()-t0:.1f}s")
    print(f"  SP  出样本(实际结算) = {sp_real:,.2f}")
    print(f"  SP  样本内期望 RP    = {rp_exp:,.2f}")
    print(f"  WS  完美预见(储能)   = {ws_real:,.2f}")
    print(f"  块级基线 q=80        = {14049999.28:,.2f}")
    print(f"  无修正 EEV(schemeA)  = {16970240.79:,.2f}")
    print(f"  EVPI = SP_real - WS  = {sp_real - ws_real:,.2f}")
    print(f"  VSS  = EEV - SP_real = {16970240.79 - sp_real:,.2f}")
    print(f"  SP vs 块级基线       = {sp_real - 14049999.28:,.2f}  (负=优于基线)")


if __name__ == "__main__":
    main()
