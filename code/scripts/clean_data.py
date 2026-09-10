# -*- coding: utf-8 -*-
"""
C题 数据审计与清洗脚本（data-auditor-cleaner）
- 原始数据只读，来源 data_raw/
- 生成规范化清洗副本到 data_clean/
- 生成 data/data_profile.json（结构画像）
- 不做任何假设性插补/删除（数据本身无缺失/异常，清洗仅为"表示规范化"）
"""
import openpyxl, os, json, hashlib, datetime
import numpy as np
import pandas as pd

RAW = "data_raw"
CLEAN = "data_clean"
DATA = "data"
os.makedirs(CLEAN, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

profile = {"schema_version": 1, "raw_files": [], "attachment_mapping": [],
           "fields": [], "quality": {"missingness": {}, "duplicates": {},
           "impossible_values": {}, "outliers": {}},
           "coverage": {}, "distribution_risks": {},
           "per_question_readiness": {}, "cleaned_files": [], "unresolved_risks": []}

def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def record_raw(name, path):
    profile["raw_files"].append({"name": name, "path": path,
        "size_bytes": os.path.getsize(path), "sha256": sha256(path)})

def stats(arr):
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    return {"n": int(a.size), "min": float(a.min()), "max": float(a.max()),
            "mean": float(a.mean()), "std": float(a.std())}

# ---------- 附件1 ----------
record_raw("附件1.xlsx", f"{RAW}/附件1.xlsx")
wb = openpyxl.load_workbook(f"{RAW}/附件1.xlsx", data_only=True)
rows = list(wb["Sheet1"].iter_rows(values_only=True))
hdr1 = rows[0]; d1 = rows[1:]
times = [str(r[0]) for r in d1]
price = np.array([r[1] for r in d1], float)
load  = np.array([r[2] for r in d1], float)
pv    = np.array([r[3] for r in d1], float)
wb.close()
df1 = pd.DataFrame({"t": range(1, 145), "time": times,
                    "price": price, "load": load, "pv_forecast": pv})
df1.to_csv(f"{CLEAN}/附件1_clean.csv", index=False)
profile["cleaned_files"].append(f"{CLEAN}/附件1_clean.csv")
profile["fields"].extend([
  {"field": "附件1.time", "unit": "10min标签", "type": "categorical", "cardinality": 144},
  {"field": "附件1.price", "unit": "元/kWh", "type": "numeric", "stats": stats(price)},
  {"field": "附件1.load", "unit": "kW", "type": "numeric", "stats": stats(load)},
  {"field": "附件1.pv_forecast", "unit": "kW", "type": "numeric", "stats": stats(pv),
   "nonzero": int((pv > 0).sum())}])

# ---------- 附件2 ----------
record_raw("附件2.xlsx", f"{RAW}/附件2.xlsx")
wb = openpyxl.load_workbook(f"{RAW}/附件2.xlsx", data_only=True)
rows = list(wb["小区负载"].iter_rows(values_only=True))
hdr2 = rows[0]; dates2 = [r[0] for r in rows[1:]]
load_mat = np.array([[float(v) for v in r[1:]] for r in rows[1:]], float)
rows_pv = list(wb["光伏发电实际功率"].iter_rows(values_only=True))
pv_mat = np.array([[float(v) for v in r[1:]] for r in rows_pv[1:]], float)
wb.close()
# 长表
def to_long(mat, colname, dates):
    idx = pd.MultiIndex.from_product([dates, range(1,145)], names=["date","t"])
    return pd.DataFrame({colname: mat.ravel()}, index=idx).reset_index()
to_long(load_mat, "load", dates2).to_csv(f"{CLEAN}/附件2_load_clean.csv", index=False)
to_long(pv_mat, "pv", dates2).to_csv(f"{CLEAN}/附件2_pv_clean.csv", index=False)
profile["cleaned_files"].extend([f"{CLEAN}/附件2_load_clean.csv", f"{CLEAN}/附件2_pv_clean.csv"])
profile["fields"].extend([
  {"field": "附件2.load", "unit": "kW", "type": "numeric", "stats": stats(load_mat),
   "shape": list(load_mat.shape)},
  {"field": "附件2.pv", "unit": "kW", "type": "numeric", "stats": stats(pv_mat),
   "shape": list(pv_mat.shape), "nonzero": int((pv_mat > 0).sum())}])

# ---------- 附件3 ----------
record_raw("附件3.xlsx", f"{RAW}/附件3.xlsx")
wb = openpyxl.load_workbook(f"{RAW}/附件3.xlsx", data_only=True)
rows3 = list(wb["Sheet1"].iter_rows(values_only=True))
hdr3 = rows3[0]; d3 = rows3[1:]
wb.close()
# 前向填充合并日期
dates3, issues, fc = [], [], []
cur_date = None
for r in d3:
    if r[0] not in (None, ""):
        cur_date = r[0]
    dates3.append(cur_date)
    issues.append(str(r[1]))
    fc.append([float(v) for v in r[2:]])
fc = np.array(fc, float)
# 长表
recs = []
for i in range(len(dates3)):
    for h in range(24):
        recs.append((dates3[i], issues[i], h+1, fc[i, h]))
df3 = pd.DataFrame(recs, columns=["date","issue_time","forecast_hour","forecast_power"])
df3.to_csv(f"{CLEAN}/附件3_clean.csv", index=False)
profile["cleaned_files"].append(f"{CLEAN}/附件3_clean.csv")
profile["fields"].append({"field": "附件3.forecast_power", "unit": "kW", "type": "numeric",
    "stats": stats(fc), "shape": list(fc.shape), "nonzero": int((fc > 0).sum()),
    "note": "前向填充合并日期；issue_time∈{0:00,6:00,12:00,18:00}；forecast_hour 1..24"})

# ---------- 附件4 ----------
record_raw("附件4.xlsx", f"{RAW}/附件4.xlsx")
wb = openpyxl.load_workbook(f"{RAW}/附件4.xlsx", data_only=True)
rows4 = list(wb["Sheet1"].iter_rows(values_only=True))
dates4 = [r[0] for r in rows4[1:]]
price_mat = np.array([[float(v) for v in r[1:]] for r in rows4[1:]], float)
wb.close()
to_long(price_mat, "price", dates4).to_csv(f"{CLEAN}/附件4_clean.csv", index=False)
profile["cleaned_files"].append(f"{CLEAN}/附件4_clean.csv")
profile["fields"].append({"field": "附件4.price", "unit": "元/kWh", "type": "numeric",
    "stats": stats(price_mat), "shape": list(price_mat.shape)})

# ---------- 附件5 模板 ----------
for fn in ["result1.xlsx","result2.xlsx","result3.xlsx","result4-2.xlsx","result4-3.xlsx"]:
    record_raw(f"附件5/{fn}", f"{RAW}/附件5/{fn}")

# ---------- 质量检查 ----------
miss = {}
for name, m in [("附件1", np.column_stack([price,load,pv])),
                ("附件2.load", load_mat), ("附件2.pv", pv_mat),
                ("附件3", fc), ("附件4", price_mat)]:
    miss[name] = int(np.isnan(m).sum())
profile["quality"]["missingness"] = miss

imp = {}
imp["附件1.负值(price/load/pv)"] = int(((price<0)|(load<0)|(pv<0)).sum())
imp["附件2.负值(load/pv)"] = int(((load_mat<0)|(pv_mat<0)).sum())
imp["附件3.负值"] = int((fc<0).sum())
imp["附件4.price<=0"] = int((price_mat<=0).sum())
profile["quality"]["impossible_values"] = imp

# 重复：附件3 原始 (date,issue) 唯一性（1460 行，前向填充后）
pairs3 = [(str(dates3[i]), issues[i]) for i in range(len(dates3))]
dups3 = len(pairs3) - len(set(pairs3))
profile["quality"]["duplicates"] = {"附件3.(date,issue)原始重复": int(dups3),
    "附件2/4日期重复": int(pd.Series([str(x) for x in dates2]).duplicated().sum())}

# 离群点(IQR)：仅报告，不处理
def iqr_outliers(a):
    a = np.asarray(a, float).ravel()
    q1, q3 = np.percentile(a, [25, 75]); iqr = q3 - q1
    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
    return int(((a < lo) | (a > hi)).sum())
profile["quality"]["outliers"] = {
    "附件1.price(IQR)": iqr_outliers(price), "附件1.load(IQR)": iqr_outliers(load),
    "附件2.load(IQR)": iqr_outliers(load_mat), "附件2.pv(IQR)": iqr_outliers(pv_mat),
    "附件4.price(IQR)": iqr_outliers(price_mat),
    "note": "夜间光伏=0为正常非离群；电价0.0076为极端低价(波动电价特性)"}

# ---------- 覆盖 ----------
profile["coverage"] = {
    "附件1": {"rows": len(d1), "intervals": 144, "time_range": "0:10 ~ 24:00(单日)"},
    "附件2": {"days": len(dates2), "intervals_per_day": 144,
              "date_range": [str(dates2[0]), str(dates2[-1])]},
    "附件3": {"records": len(df3), "days": df3["date"].nunique(),
              "issues_per_day": df3.groupby("date")["issue_time"].nunique().max(),
              "date_range": [str(df3["date"].iloc[0]), str(df3["date"].iloc[-1])]},
    "附件4": {"days": len(dates4), "intervals_per_day": 144,
              "date_range": [str(dates4[0]), str(dates4[-1])]},
    "note": "2025全年连续，无日期缺口；附件2/3/4日期均为2025-01-01~2025-12-31(365天)"}

# ---------- 附件-子问题映射 ----------
profile["attachment_mapping"] = [
    {"attachment": "附件1", "content": "代表日(年均)电价/负载/光伏预测", "maps_to": ["Q1"], "role": "输入"},
    {"attachment": "附件1", "content": "电价曲线(恒定)", "maps_to": ["Q2","Q3"], "role": "输入(仅电价)"},
    {"attachment": "附件2", "content": "全年实际负载/光伏", "maps_to": ["Q2","Q3","Q4"], "role": "输入(实际结算)"},
    {"attachment": "附件3", "content": "滚动光伏预报(0/6/12/18)", "maps_to": ["Q3","Q4"], "role": "输入(预报)"},
    {"attachment": "附件4", "content": "全年波动电价", "maps_to": ["Q4"], "role": "输入(电价)"},
    {"attachment": "附件5/result1", "maps_to": ["Q1"], "role": "输出模板"},
    {"attachment": "附件5/result2", "maps_to": ["Q2"], "role": "输出模板"},
    {"attachment": "附件5/result3", "maps_to": ["Q3"], "role": "输出模板"},
    {"attachment": "附件5/result4-2", "maps_to": ["Q4(对应Q2)"], "role": "输出模板"},
    {"attachment": "附件5/result4-3", "maps_to": ["Q4(对应Q3)"], "role": "输出模板"},
]

# ---------- 每问就绪度 ----------
profile["per_question_readiness"] = {
    "Q1": {"status": "ready", "fields": ["附件1.price","附件1.load","附件1.pv_forecast","附录1参数"]},
    "Q2": {"status": "ready_with_warnings",
           "fields": ["附件1.price","附件2.load","附件2.pv","附录1参数"],
           "warning": "计划信息集(完美预见与否)待HD3确认"},
    "Q3": {"status": "ready_with_warnings",
           "fields": ["附件1.price","附件2.load","附件2.pv","附件3.forecast","附录1参数"],
           "warning": "整点预报→10min区间需插值(HD/S8)；计费口径待HD4确认"},
    "Q4": {"status": "ready_with_warnings",
           "fields": ["附件4.price","附件2.load","附件2.pv","附件3.forecast","附录1参数"],
           "warning": "波动电价含极低价(0.0076)，需核对储能套利边界"},
}

profile["unresolved_risks"] = [
    "附件3为整点(1h)预报，负载/光伏/电价为10min粒度，需约定插值/阶梯映射(S8)",
    "附件1=年均代表日(负载精确=附件2均值，电价=附件4均值)，Q1结果仅代表典型日",
    "Q2完美预见假设下紧急购电机制在最优解≈0，其意义由HD3决定",
    "电价极端值0.0076元/kWh与1.7936元/kWh并存，波动大，影响储能套利策略稳定性"
]

# ---------- 统一 pickle ----------
import pickle
bundle = {
    "dates": [str(x) for x in dates2],
    "附件1": {"times": times, "price": price, "load": load, "pv_forecast": pv},
    "附件2_load": load_mat, "附件2_pv": pv_mat,
    "附件3": {"dates": [str(x) for x in dates3], "issues": issues, "forecast": fc},
    "附件4_price": price_mat,
    "params": {"C":12000, "E_min":1200, "E_max":10800, "P_chg_max":5000,
               "P_dis_max":5000, "eta_c":0.9, "eta_d":0.9, "E0":6000,
               "alpha_em":5, "beta_pen":0.5, "gamma_pre":1.5, "dt_hr":1/6, "T":144, "D":365},
}
with open(f"{CLEAN}/cleaned_data.pkl", "wb") as f:
    pickle.dump(bundle, f)
profile["cleaned_files"].append(f"{CLEAN}/cleaned_data.pkl")

with open(f"{DATA}/data_profile.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, ensure_ascii=False, indent=2, default=str)

print("=== DONE ===")
print("missingness:", miss)
print("impossible:", imp)
print("附件3 (date,issue) dup:", dups3)
print("outliers:", profile["quality"]["outliers"])
print("cleaned files:", len(profile["cleaned_files"]))
print("附件3 date range:", str(df3['date'].iloc[0]), str(df3['date'].iloc[-1]), "days:", df3['date'].nunique())
print("issues sample:", df3['issue_time'].unique().tolist())
