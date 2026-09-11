# Q3 冻结变更日志 (freeze_change_log.md)

> 规则：冻结后任何规范源变更须先记录于此，再走 thaw→rerun→refreeze 流程。

## 2026-09-11 — 解冻（thaw）：round1 储能末端短视缺陷

- **原因**：round1 合理性分析（`methods/Q3/q3_reasonableness_analysis.md`）发现 `daily_lp`/`stage_lp` 无储能终态约束（`terminal_eq=False`），储能每日倒空至 1200 下界、丧失跨日价值；含储能方案 16,972,663.03 元反贵于无储能完美预见 16,407,319.63 元，属**方法级缺陷**。
- **动作**：解冻 round1 冻结结果，G2 重开（修正终端约束：日闭合 E(144)=E(0)=6000 或终态残值），待人类确认后 G3 重跑 → 重新冻结。
- **受影响（round1 作废）**：`results/Q3/reports/frozen_numbers.json`、`results/Q3/experiments/round1/run_summary.json`、`methods/Q3/q3_final_method_explanation.md`。
- **待确认口径**：HD4 计费、S8 预报粒度（此前按默认提案应用，未显式 DECIDED）。
