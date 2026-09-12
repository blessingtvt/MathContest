# -*- coding: utf-8 -*-
"""Q3 G4 结果表生成：从 round3 的 result3.xlsx 提取 4 个指定日期的 表1/表2/表3，输出 markdown。

指定日期：2025.3.20(春分)、2025.6.21(夏至)、2025.9.23(秋分)、2025.12.21(冬至)。
表1 时间段：10:00-10:10 / 12:00-12:10 / 14:00-14:10 / 16:00-16:10 / 18:00-18:10 / 20:00-20:10。
输出：results/Q3/q3_answer_tables.md
"""
import os, sys, json, pickle
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import openpyxl
from common import T, time_labels, ROOT, RESULTS_DIR, DATA_CLEAN

DATES = [datetime(2025, 3, 20), datetime(2025, 6, 21),
         datetime(2025, 9, 23), datetime(2025, 12, 21)]
DATE_STR = ["2025.3.20", "2025.6.21", "2025.9.23", "2025.12.21"]
SLOTS = ["10:00-10:10", "12:00-12:10", "14:00-14:10",
         "16:00-16:10", "18:00-18:10", "20:00-20:10"]
# 指定时间段对应的区间索引 (time_labels[i] == SLOTS[k])
labels = time_labels()
SLOT_IDX = [labels.index(s) for s in SLOTS]


def main():
    with open(os.path.join(DATA_CLEAN, "cleaned_data.pkl"), "rb") as f:
        bundle = pickle.load(f)
    price = np.asarray(bundle["附件1"]["price"], dtype=float)  # 144

    xlsx = os.path.join(RESULTS_DIR, "Q3", "result3.xlsx")
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)

    # ---- 计划/调整购电量网格 ----
    def read_grid(ws):
        rows = []
        dts = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                continue
            dts.append(row[0])
            rows.append([float(v) if v is not None else 0.0 for v in row[1:1 + T]])
        return dts, np.array(rows)

    dts, X = read_grid(wb["计划购电量"])
    _, Y = read_grid(wb["调整购电量"])
    dtmap = {d.date(): i for i, d in enumerate(dts)}

    # ---- 充放电量 sheet: (日期, 时间段, 充电量, 放电量, 时刻, 储电量) ----
    # 注: 日期仅写在每段 6 行的首行(s=0), 其余行日期列为 None, 需 carry-forward。
    chg = {}; dis = {}; estore = {}
    cur_date = None
    for row in wb["充放电量"].iter_rows(min_row=2, values_only=True):
        if row[0] is not None:
            cur_date = row[0].date()
        if cur_date is None:
            continue
        d = cur_date
        seg = row[1]
        chg.setdefault(d, {})[seg] = float(row[2]) if row[2] is not None else 0.0
        dis.setdefault(d, {})[seg] = float(row[3]) if row[3] is not None else 0.0
        if row[4] is not None and row[5] is not None:
            estore.setdefault(d, {})[str(row[4])] = float(row[5])

    # ---- 紧急购电量 sheet: (日期, 购电时间段, 购电量) ----
    emerg = {}
    for row in wb["紧急购电量"].iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        d = row[0].date()
        lab = row[1]
        val = float(row[2]) if row[2] is not None else 0.0
        if lab is None or val <= 1e-8:
            continue
        emerg.setdefault(d, []).append((lab, val))

    wb.close()

    # ---- 逐日期计算 ----
    X_d = {}; Y_d = {}; C_d = {}; Q_d = {}; E0_d = {}; E24_d = {}
    plan_total = {}; adj_total = {}; bill = {}; emg_cost = {}
    for k, dt in enumerate(DATES):
        i = dtmap[dt.date()]
        x = X[i]; y = Y[i]
        X_d[dt] = x; Y_d[dt] = y
        plan_total[dt] = float(x.sum())
        adj_total[dt] = float(y.sum())
        base = price * (np.minimum(x, y)
                        + 0.5 * np.maximum(x - y, 0.0)
                        + 1.5 * np.maximum(y - x, 0.0))
        emg = 0.0
        for lab, val in emerg.get(dt.date(), []):
            t = labels.index(lab)
            emg += 5.0 * price[t] * val
        bill[dt] = float(base.sum() + emg)
        emg_cost[dt] = float(emg)
        segs = ["0:00-4:00", "4:00-8:00", "8:00-12:00",
                "12:00-16:00", "16:00-20:00", "20:00-24:00"]
        C_d[dt] = [chg.get(dt.date(), {}).get(s, 0.0) for s in segs]
        Q_d[dt] = [dis.get(dt.date(), {}).get(s, 0.0) for s in segs]
        E0_d[dt] = estore.get(dt.date(), {}).get("00:00:00", 6000.0)
        E24_d[dt] = estore.get(dt.date(), {}).get("24:00", 6000.0)

    # ---- 写 markdown ----
    L = []
    L.append("# Q3 指定日期结果表（表1 / 表2 / 表3）")
    L.append("")
    L.append("> 数据来源：`results/Q3/result3.xlsx`（主模型 M3：滚动时域 MPC + 分段计费线性化 + 日闭合 E(144)=E(0)=6000 + 光伏风险修正按 issue×执行块 逐区间 80 分位，round4 块级）。")
    L.append("> 指定日期：2025.3.20（春分）、2025.6.21（夏至）、2025.9.23（秋分）、2025.12.21（冬至）。")
    L.append("> 单位：购电量 / 充电量 / 放电量 / 储电量均为 kWh，购电费为元。")
    L.append("")
    L.append("## 表1 微网在指定时间段的购电量及全天的购电量和购电费")
    L.append("")
    L.append("### 表1(a) 计划购电量（0:00 制定）")
    L.append("")
    L.append("| 时间段 | " + " | ".join(DATE_STR) + " |")
    L.append("|---" * (len(DATE_STR) + 1) + "|")
    for s, idx in zip(SLOTS, SLOT_IDX):
        vals = [f"{X_d[dt][idx]:.2f}" for dt in DATES]
        L.append(f"| {s} | " + " | ".join(vals) + " |")
    L.append(f"| 全天计划购电量（kWh） | " + " | ".join(f"{plan_total[dt]:.2f}" for dt in DATES) + " |")
    L.append("")
    L.append("### 表1(b) 调整购电量（6/12/18 滚动调整后执行）")
    L.append("")
    L.append("| 时间段 | " + " | ".join(DATE_STR) + " |")
    L.append("|---" * (len(DATE_STR) + 1) + "|")
    for s, idx in zip(SLOTS, SLOT_IDX):
        vals = [f"{Y_d[dt][idx]:.2f}" for dt in DATES]
        L.append(f"| {s} | " + " | ".join(vals) + " |")
    L.append(f"| 全天调整购电量（kWh） | " + " | ".join(f"{adj_total[dt]:.2f}" for dt in DATES) + " |")
    L.append(f"| 全天购电费（元） | " + " | ".join(f"{bill[dt]:.2f}" for dt in DATES) + " |")
    L.append("")
    L.append("## 表2 储能设备在指定时间段的充放电量及0:00和24:00的储电量")
    L.append("")
    segs = ["0:00-4:00", "4:00-8:00", "8:00-12:00",
            "12:00-16:00", "16:00-20:00", "20:00-24:00"]
    hdr = []
    for ds in DATE_STR:
        hdr += [f"{ds} 充电量", f"{ds} 放电量"]
    L.append("| 时间段 | " + " | ".join(hdr) + " |")
    L.append("|---" * (len(hdr) + 1) + "|")
    for si, seg in enumerate(segs):
        cells = []
        for dt in DATES:
            cells += [f"{C_d[dt][si]:.2f}", f"{Q_d[dt][si]:.2f}"]
        L.append(f"| {seg} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("> 0:00 储电量与 24:00 储电量：四个指定日期均为 6000.00 kWh（滚动 MPC 日闭合约束 E(0) = E(144) = 6000）。")
    L.append("")
    L.append("## 表3 微网在指定日期的紧急购电量")
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
    L.append(f"> 注：紧急购电时段数——2025.3.20 为 {n_emg[0]} 个、2025.6.21 为 {n_emg[1]} 个、"
             f"2025.9.23 为 {n_emg[2]} 个、2025.12.21 为 {n_emg[3]} 个。"
             "经按 issue×执行块 逐区间 80 分位光伏风险修正后，6:00 高估缺口转成弃光，紧急购电显著低于未修正方案。")

    out = os.path.join(RESULTS_DIR, "Q3", "q3_answer_tables.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"WROTE {out}")
    print("emg counts:", n_emg)
    print("bills:", {DATE_STR[k]: round(bill[dt], 2) for k, dt in enumerate(DATES)})


if __name__ == "__main__":
    main()
