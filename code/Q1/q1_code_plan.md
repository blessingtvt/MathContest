# Q1 代码计划 (model-code-analyzer)

## 目标与成功标准
- 目标：代表日（附件1，144 个 10 分钟区间）最小化全天购电费 C1 = Σ p_t·x_t。
- 输出：`results/Q1/result1.xlsx`（计划购电量 + 充放电量 两张 sheet）+ `experiments/round1/run_summary.json`。
- 成功标准：LP 返回 success；能量平衡满足、储能落在 [1200,10800]、终态 E_0=E_T=6000；数值可信（优于两个基线）。

## 目录结构（experiments/round1）
```
results/Q1/
├── result1.xlsx
└── experiments/round1/
    ├── run_summary.json        # 主模型 M1
    └── baseline_metrics.json   # 基线 B1/R1
```

## 数据来源（只读 data_clean/cleaned_data.pkl）
- `附件1.price`：(144,) 分时购电价（元/kWh）。
- `附件1.load`：(144,) 负荷功率（kW）。
- `附件1.pv_forecast`：(144,) 光伏功率（kW）。
- `params`：Emin/Emax/Pmax/ηc/ηd/α/β/γ/E0（与 common.py 常量一致，代码以 common.py 为准）。
- 不修改 `data_raw/` 任何原始文件。

## 主模型 M1：单日线性规划
调用 `common.daily_lp(price, load, pv, E0=E0_INIT, terminal_eq=True, E_term=E0_INIT)`。
- 变量 577 个：x(144) + c(144) + q(144) + E(145)。
- 约束：能量平衡 `x + G·Δt + q ≥ L·Δt + c`；`c≤PmaxE`、`q≤PmaxE`；储能动态 `E_{t+1}=E_t+ηc·c−q/ηd`；`E∈[1200,10800]`；`E_0=E_T=6000`。
- 求解器：scipy.optimize.linprog(method="highs")。

## 基线
- **B1 无储能**：`no_storage` → x_t = max(L·Δt − G·Δt, 0)。
- **R1 规则套利**：`rule_arbitrage`（低价 1/3 充满、高价 1/3 放空、中价不动，余缺购电补足）。

## 计算步骤（q1_main.py）
1. `load_bundle()` 读取清洗数据。
2. `daily_lp` 求解 M1，得到 (cost, x, c, q, E)。
3. `no_storage` / `rule_arbitrage` 计算 B1/R1。
4. 加载模板 `data_raw/附件5/result1.xlsx`，写入计划购电量（列 B，144 行）、充放电量（6 段汇总 + 0:00/24:00 储电量）。
5. 写 `run_summary.json`；`q1_baseline.py` 写 `baseline_metrics.json`。

## 可比指标（metrics）
- 储能价值 = B1 − M1；储能价值占比 = (B1−M1)/B1。
- 优化价值 = R1 − M1。
- 附加：总购电量 kWh、总充/放电量 kWh、终态储能量 kWh。

## 风险监控
- LP 不可行 → `daily_lp` 抛出 RuntimeError（终态等式约束若与储能功率边界冲突会暴露）。
- 数值退化：充电/放电同一区间同时为正（应被最优性自然排除）；`clip0(tol=1e-8)` 清洗浮点残差。
- 终态约束：核对 `E[0]==E[-1]==6000`。

## 路径 / 种子 / 依赖
- 种子：`common.SEED = 2026`（`np.random.seed(SEED)`，本模型无随机量，种子为可复现约定）。
- 依赖：numpy、scipy(HiGHS)、openpyxl。
- 路径：`code/Q1/q1_main.py`、`code/Q1/q1_baseline.py`、`code/common.py`。
