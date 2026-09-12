# Q3 冻结变更日志 (freeze_change_log.md)

> 规则：冻结后任何规范源变更须先记录于此，再走 thaw→rerun→refreeze 流程。

## 2026-09-11 — 解冻（thaw）：round1 储能末端短视缺陷

- **原因**：round1 合理性分析（`methods/Q3/q3_reasonableness_analysis.md`）发现 `daily_lp`/`stage_lp` 无储能终态约束（`terminal_eq=False`），储能每日倒空至 1200 下界、丧失跨日价值；含储能方案 16,972,663.03 元反贵于无储能完美预见 16,407,319.63 元，属**方法级缺陷**。
- **动作**：解冻 round1 冻结结果，G2 重开（修正终端约束：日闭合 E(144)=E(0)=6000 或终态残值），待人类确认后 G3 重跑 → 重新冻结。
- **受影响（round1 作废）**：`results/Q3/reports/frozen_numbers.json`、`results/Q3/experiments/round1/run_summary.json`、`methods/Q3/q3_final_method_explanation.md`。
- **待确认口径**：HD4 计费、S8 预报粒度（此前按默认提案应用，未显式 DECIDED）。

## 2026-09-12 — 解冻（thaw）→ 重跑 → 重冻结（round4）：光伏风险修正由「按 issue 标量」升级为「按 issue × 执行区间逐区间」

- **原因（thaw）**：round3 的风险修正把每个 issue（0/6/12/18）的预报高估用一个标量 $P_{80}$ 修正（`delta_issue_kW=[0,1005.49,-6.27,0]`）。实际执行时，各 issue 预报覆盖的是**未来 24h 逐 10min 区间**，高估误差在不同执行区间（6h 块）差异很大；按 issue 分桶解释预报误差方差 43.5% 之后，进一步按「issue × 执行块」分桶可再解释剩余方差。逐区间分位修正在**因果信息集内**（只用 `[MIN_HIST, d)` 历史，无前瞻）且**严格更优**。
- **动作（rerun）**：`code/Q3/q3_new_methods/q3_optimized.py`（块级修正顺序法），含 q=80 对照与 B3/R3 块级基线。同步修复 run() 的储电量校验：原 `emin=min(emin,E0_INIT); emax=max(emax,E0_INIT)` 恒得 6000、不校验日内轨迹；现改为追踪 4 段拼接的真实日内轨迹 `E_day`，校验 1200≤E≤10800 与 E0=E24=6000。
- **重冻结（refreeze）数值（q=80，与 round3 同分位，纯粒度对照）**：

| 量 | round3 标量 q=80 | round4 块级 q=80 | Δ | Δ% |
|---|---|---|---|---|
| 目标总购电费(元) | 15,081,833.10 | **14,049,999.28** | −1,031,833.82 | −6.84% |
| 紧急购电费(元) | 912,934.41 | 564,060.69 | −348,873.72 | −38.2% |
| 紧急购电电量(kWh) | 245,793.57 | 145,059.00 | −100,734.57 | −41.0% |
| 弃光电量(kWh) | 2,812,018.61 | 1,914,415.30 | −897,603.31 | −31.9% |
| 弃光率 | 0.147466 | 0.100395 | — | −4.71pp |

- **块级基线（同修正轴，q=80）**：B3（静态不调整）= 17,291,136.58；R3（规则套利）= 16,956,099.35；B3_ref（无储能·完美预见下界）= 16,407,319.63；NS_fc（无储能·附件3预报）= 20,128,453.40。派生：调整价值 3,241,137.30、优化价值 2,906,100.07、储能价值 6,078,454.12。
- **储电量校验（修复后）**：`E_min=1200.0, E_max=10800.0`（日内轨迹触及 LP 上下界、从不越界）；`E0_min=E0_max=E24_min=E24_max=6000.0`（日闭合成立）。`storage_bounds_verified=true`。
- **分位选型（DECIDED）**：**取 q=80 作冻结主值**（报童临界比 0.8 与 Q2 及 round3 一致，理论锚定）；q=85 为样本内经验 argmin=14,020,104.48，仅比 q=80 低 0.21%，无理论锚定，故只作稳健性对照（目标在 [80,85] 平坦）。
- **延期项（deferred → G5）**：`result3.xlsx`、`q3_answer_tables.md`（题目指定日期表 1/2/3）与 `paper/figures/fig_q3_*` 仍为 round3 标量口径；待 SP 出样本定胜负后，以**最终选定方法**一次性重生成，避免 SP 胜出时返工。本冻结仅更新**权威数值**，不更新输出表。
- **受影响**：`results/Q3/reports/frozen_numbers.json`（round3→round4）；`results/Q3/experiments/optimization/block_risk_summary.json`（新增，块级分位扫描+块级基线）。

## 2026-09-12 — G4 交付（非数值变更，元数据/产物指针更新 + 术语修正）

- **VSS 术语修正（用户指正）**：此前把 `基线1405.00万 − RP1383.37万 = 317.85万` 误标为 VSS。教科书 VSS = EEV − RP，其中 EEV 是"先用确定性均值场景解出决策、再用随机场景求其期望"的费用；317.85 万实为"滚动确定性基线 vs SP"的差值。**采用用户建议的方案 1**：`sp_summary.json` 中删除 VSS 字段，改记为 `benefit_vs_deterministic_baseline_yuan = 258,236.08`（=25.82 万，块级基线 14,049,999.28 − SP 出样本 13,791,763.20），EVPI 改为标准口径 RP − WS = 1,588,661.96。
- **主模型定论**：SP 作为**扩展对照**，Q3 主模型 = 块级顺序法（round4, q=80, 14,049,999.28）。SP 出样本 13,791,763.20，较块级基线低 25.82 万（−1.84%），仅作对照。
- **产物重生成（以主模型为准，块级 q=80）**：
  - `results/Q3/result3.xlsx` ← `code/Q3/q3_result_writer.py`（块级 MPC 写盘，交叉校验 6 项全 OK，Δ<0.005）。
  - `results/Q3/q3_answer_tables.md` ← `code/Q3/q3_tables.py`（指定日期表1/2/3，块级）。
  - `results/Q3/experiments/round4/robustness_report.json` ← `code/Q3/q3_robustness_block.py`（块级消融/扰动/分位扫描/误差时域）。
  - `paper/figures/fig_q3_*.png|svg` ← `code/Q3/q3_plots.py`（EXP_DIR→round4，图1 文本改块级 δ[s,t]），并复制到 `results/Q3/figures/`。
  - `methods/Q3/q3_final_method_explanation.md`（round4 块级底稿）；`planning/symbol_table.md` 新增 `δ_{d,s,t}` 符号。
- **受影响**：`results/Q3/reports/frozen_numbers.json`（answer_tables/result_workbook/robustness_report 指针由 deferred→round4 块级）；`results/Q3/experiments/sp/sp_summary.json`（VSS→收益口径）。
- **数值未变**：frozen 权威数值（目标 14,049,999.28、成本构成、基线、派生价值）均未改动。

## 2026-09-12 — G4 图件重设计（非数值变更，仅图形样式与新增图）

- **原因（用户指令）**：删除 Q3 图片中的 SVG；学习参考图的配色与图像设计，重新设计 Q3 全部图件；增强分位敏感性图为「总费用 + 成本分解（计划/溢价/紧急）」；补充其他建模分析、结果验证相关论文正式图。
- **动作**：
  - 删除 `paper/figures/` 与 `results/Q3/figures/` 下全部 `.svg`（残留 0 个），此后仅输出 PNG（300dpi）。
  - 配色由高饱和实色改为**柔和低饱和浅色系**（白底极简）：主模型蓝 `#6E9BC9`、紧急/负向珊瑚 `#E08E8E`、溢价/次级琥珀 `#E0B878`、弃光/正向青 `#7FBFA8`、基线中性灰；网格/边框极淡。图件由 `code/Q3/q3_plots.py` 一次性重绘并复制到 `results/Q3/figures/`。
  - **fig_q3_5 增强**：改为「不同分位 q 的总费用 + 计划/溢价/紧急 三项堆叠分解」，数据源 `results/Q3/experiments/round4/quantile_decomp.json`（`code/Q3/q3_quantile_decomp.py` 生成）；标注 q=80 冻结、q=85 样本内 argmin。
  - **fig_q3_8 新增（建模分析）**：光伏风险修正量 δ[s,t] 4×36 发散色热图（`qopt.block_delta(over, D−1, 80.0)`），展示 issue×执行块 的逐区间 P80 高估修正结构。
  - **fig_q3_9 新增（结果验证）**：典型日（夏至 06-21 / 冬至 12-21）储能 SOC 轨迹，含 E_min=1200/E_max=10800 上界下带与 E(0)=E(24)=6000 日闭合校验。
- **受影响**：`results/Q3/reports/frozen_numbers.json`（paper_figures 由 7 项→9 项，新增 fig_q3_8/fig_q3_9）；`code/Q3/q3_plots.py`（重写）。
- **数值未变**：frozen 权威数值全部未改动；图件仅样式重绘，未改任何数值口径。
