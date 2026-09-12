# -*- coding: utf-8 -*-
"""Q4 指定日期结果表（表1/表2/表3）生成：result4-2 与 result4-3 各一份。

指定日期：2025.3.20(春分)、2025.6.21(夏至)、2025.9.23(秋分)、2025.12.21(冬至)。
表1 时间段：10:00-10:10 / 12:00-12:10 / 14:00-14:10 / 16:00-16:10 / 18:00-18:10 / 20:00-20:10。
电价：附件4 逐日逐时段波动电价 p_{d,t}（非附件1 固定曲线）。
输出：results/Q4/q4_answer_tables.md
"""
import os, sys, pickle
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import T, time_labels, ROOT, RESULTS_DIR, DATA_CLEAN, WARMUP_DAYS

DATES = [datetime(2025, 3, 20), datetime(2025, 6, 21),
         datetime(2025, 9, 23), datetime(2025, 12, 21)]
DATE_STR = ["2025.3.20", "2025.6.21", "2025.9.23", "2025.12.21"]
SLOTS = ["10:00-10:10", "12:00-12:10", "14:00-14:10",
         "16:00-16:10", "18:00-18:10", "20:00-20:10"]
labels = time_labels()
SLOT_IDX = [labels.index(s) for s in SLOTS]
SEGS = ["0:00-4:00", "4:00-8:00", "8:00-12:00",
        "12:00-16:00", "16:00-20:00", "20:00-24:00"]


def read_grid(ws):
    """读取计划/调整购电量网格 (335×144)，返回 (dates, X)。"""
    dts, rows = [], []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        dts.append(row[0])
        rows.append([float(v) if v is not None else 0.0 for v in row[1:1 + T]])
    return dts, np.array(rows)


def read_summary(ws):
    """读取 全天购电量(146列) / 全天购电费(147列)。"""
    daily_q, daily_cost = [], []
    for r, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[0] is None:
            continue
        daily_q.append(float(ws.cell(row=r, column=146).value or 0.0))
        daily_cost.append(float(ws.cell(row=r, column=147).value or 0.0))
    return np.array(daily_q), np.array(daily_cost)


def read_charge(ws):
    """读取充放电量 sheet：{date: {seg: (chg, dis)}} 与 {date: {时刻: 储电量}}。"""
    chg, dis, estore = {}, {}, {}
    cur = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None:
            cur = row[0].date()
        if cur is None:
            continue
        seg = row[1]
        chg.setdefault(cur, {})[seg] = float(row[2]) if row[2] is not None else 0.0
        dis.setdefault(cur, {})[seg] = float(row[3]) if row[3] is not None else 0.0
        if row[4] is not None and row[5] is not None:
            estore.setdefault(cur, {})[str(row[4])] = float(row[5])
    return chg, dis, estore


def read_emergency(ws):
    emerg = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        d = row[0].date()
        lab, val = row[1], row[2]
        if lab is None or val is None or float(val) <= 1e-8:
            continue
        emerg.setdefault(d, []).append((lab, float(val)))
    return emerg


def load_price_by_date():
    with open(os.path.join(DATA_CLEAN, "cleaned_data.pkl"), "rb") as f:
        b = pickle.load(f)
    p = np.asarray(b["附件4_price"], dtype=float)   # (365, 144)
    dates = b["dates"]
    dmap = {}
    for d, s in enumerate(dates):
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").date()
        dmap[dt] = d
    return p, dmap


def emit(L, wb, dates, dtmap, price, dmap, mode):
    """mode: '4-2'(仅计划) 或 '4-3'(计划+调整)。"""
    has_adj = (mode == "4-3")
    dts, X = read_grid(wb["计划购电量"])
    plan_q, plan_cost = read_summary(wb["计划购电量"])
    if has_adj:
        _, Y = read_grid(wb["调整购电量"])
        _, adj_cost = read_summary(wb["调整购电量"])
    chg, dis, estore = read_charge(wb["充放电量"])
    emerg = read_emergency(wb["紧急购电量"])
    idx = {d.date(): i for i, d in enumerate(dts)}

    X_d = {}; Y_d = {}
    pq = {}; pc = {}; aq = {}
    for k, dt in enumerate(DATES):
        i = idx[dt.date()]
        X_d[dt] = X[i]
        pq[dt] = plan_q[i]; pc[dt] = plan_cost[i]
        if has_adj:
            Y_d[dt] = Y[i]
            aq[dt] = float(Y[i].sum())

    L.append(f"## result{mode} 表1 微网在指定时间段的购电量及全天的购电量和购电费")
    L.append("")
    L.append(f"### 表1(a) 计划购电量（0:00 制定）")
    L.append("")
    L.append("| 时间段 | " + " | ".join(DATE_STR) + " |")
    L.append("|---" * (len(DATE_STR) + 1) + "|")
    for s, si in zip(SLOTS, SLOT_IDX):
        L.append(f"| {s} | " + " | ".join(f"{X_d[dt][si]:.2f}" for dt in DATES) + " |")
    L.append(f"| 全天计划购电量（kWh） | " + " | ".join(f"{pq[dt]:.2f}" for dt in DATES) + " |")
    L.append(f"| 全天购电费（元） | " + " | ".join(f"{pc[dt]:.2f}" for dt in DATES) + " |")
    L.append("")

    if has_adj:
        L.append("### 表1(b) 调整购电量（6/12/18 滚动调整后执行）")
        L.append("")
        L.append("| 时间段 | " + " | ".join(DATE_STR) + " |")
        L.append("|---" * (len(DATE_STR) + 1) + "|")
        for s, si in zip(SLOTS, SLOT_IDX):
            L.append(f"| {s} | " + " | ".join(f"{Y_d[dt][si]:.2f}" for dt in DATES) + " |")
        L.append(f"| 全天调整购电量（kWh） | " + " | ".join(f"{aq[dt]:.2f}" for dt in DATES) + " |")
        L.append(f"| 全天购电费（元） | " + " | ".join(f"{pc[dt]:.2f}" for dt in DATES) + " |")
        L.append("")

    L.append(f"## result{mode} 表2 储能设备在指定时间段的充放电量及 0:00 和 24:00 储电量")
    L.append("")
    hdr = []
    for ds in DATE_STR:
        hdr += [f"{ds} 充电量", f"{ds} 放电量"]
    L.append("| 时间段 | " + " | ".join(hdr) + " |")
    L.append("|---" * (len(hdr) + 1) + "|")
    C_d = {}; Q_d = {}
    for dt in DATES:
        C_d[dt] = [chg.get(dt.date(), {}).get(s, 0.0) for s in SEGS]
        Q_d[dt] = [dis.get(dt.date(), {}).get(s, 0.0) for s in SEGS]
    for si, seg in enumerate(SEGS):
        cells = []
        for dt in DATES:
            cells += [f"{C_d[dt][si]:.2f}", f"{Q_d[dt][si]:.2f}"]
        L.append(f"| {seg} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("> 0:00 储电量与 24:00 储电量：四个指定日期均为 6000.00 kWh（日闭合约束 E(0)=E(144)=6000）。")
    L.append("")

    L.append(f"## result{mode} 表3 微网在指定日期的紧急购电量")
    L.append("")
    hdr3 = []
    for ds in DATE_STR:
        hdr3 += [f"{ds} 时间段", f"{ds} 购电量"]
    L.append("| " + " | ".join(hdr3) + " |")
    L.append("|---" * (len(hdr3) + 1) + "|")
    n_emg = [len(emerg.get(dt.date(), [])) for dt in DATES]
    nrows = max(n_emg) if n_emg else 0
    for r in range(nrows):
        cells = []
        for dt in DATES:
            lst = emerg.get(dt.date(), [])
            if r < len(lst):
                cells += [lst[r][0], f"{lst[r][1]:.2f}"]
            else:
                cells += ["", ""]
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    L.append(f"> 注：紧急购电时段数——" + "、".join(f"{DATE_STR[k]} 为 {n_emg[k]} 个" for k in range(4)) + "。")
    L.append("")

    # ---- 每天电价（附件4 逐日逐时段）----
    L.append(f"## result{mode} 附：指定日期当天电价（附件4 波动电价 p_{{d,t}}）")
    L.append("")
    L.append("| 时间段 | " + " | ".join(DATE_STR) + " |")
    L.append("|---" * (len(DATE_STR) + 1) + "|")
    for s, si in zip(SLOTS, SLOT_IDX):
        vals = [f"{price[dmap[dt.date()], si]:.4f}" for dt in DATES]
        L.append(f"| {s}（元/kWh） | " + " | ".join(vals) + " |")
    avg = [f"{price[dmap[dt.date()]].mean():.4f}" for dt in DATES]
    L.append(f"| 日均价（元/kWh） | " + " | ".join(avg) + " |")
    L.append("")


def main():
    price, dmap = load_price_by_date()
    L = []
    L.append("# Q4 指定日期结果表（result4-2 / result4-3 的表1 / 表2 / 表3）")
    L.append("")
    L.append("> 数据来源：`results/Q4/result4-2.xlsx`（逐日滚动 LP + 星期80分位）、`results/Q4/result4-3.xlsx`（滚动 MPC + 分段计费 + 块级80分位光伏修正）。")
    L.append("> 电价：附件4 逐日逐时段波动电价 p_{d,t}。指定日期：2025.3.20（春分）、2025.6.21（夏至）、2025.9.23（秋分）、2025.12.21（冬至）。")
    L.append("> 单位：购电量 / 充电量 / 放电量 / 储电量均为 kWh，购电费为元，电价为 元/kWh。")
    L.append("")

    out_dir = os.path.join(RESULTS_DIR, "Q4")
    for mode, fn in [("4-2", "result4-2.xlsx"), ("4-3", "result4-3.xlsx")]:
        wb = openpyxl.load_workbook(os.path.join(out_dir, fn))
        emit(L, wb, None, None, price, dmap, mode)
        wb.close()

    out = os.path.join(out_dir, "q4_answer_tables.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", out)


if __name__ == "__main__":
    main()
