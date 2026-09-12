# Q2 整体质量保证审计（quality-assurance-auditor）

> 前置：本审计仅在"一致性审计"与"完整性审计"均通过后放行。二者本次均 **PASS**，故进入本审计。

> ⚠️ **本报告对应 round3（2026-09-11 round4 采纳之前）。** round4 已将 80 分位改为按星期分桶 e80[dow]，`paper/sections/q2.md` 与 `frozen_numbers.json` 均已更新为 round4（主结果总费用 14,559,104.58 元、经验 argmin 移至 q=90、claim 数由 26 增至 40）。本文 §2.3"argmin=80 吻合"、§2.1"26 项 claim"、§3 G1（稳健性报告措辞）均为 round3 历史记录；round4 下 `q2_robustness_report.md` 已重生成、G1 所指措辞已修正。建议在 final_assembly 前按 round4 重跑本审计。

## 1. 放行前置核查

| 前置审计 | 结果 | 路径 |
|---|---|---|
| 一致性审计 | **PASS** | `paper/audits/cross_media_consistency_audit.md` |
| 完整性审计 | **PASS** | `paper/audits/completeness_audit.md` |

→ 满足"只有前两项审计全部通过才放行"的硬约束。

## 2. 反造假审计

### 2.1 数值反造假
- 论文每个绝对结果数值均引用 `frozen_numbers.json`（26 项 claim），且逐项带 `source_file`/`source_locator`，可回溯到 `run_summary.json` 或 `q2_robustness_summary.json`。
- 未发现"冻结文件之外凭空生成的数字"：派生比例（R1"3.2倍/0.3%"、R2 相对变化）均由冻结绝对数值相除，并已在正文注明；R3/R5 占比已直接冻结。
- 冻结文件经 `freeze_change_log.md` 记录两次**纯新增**扩展（补稳健性敏感性数值），未改动任何既有冻结值，`q2_package_signoff=keep` 结论不变。

### 2.2 引用反造假
- `paper/refs.bib` 5 条文献全部真实、可查证（题目与附件、姜启源《数学模型》、Dantzig LP、Huangfu & Hall HiGHS、Silver 等报童），无虚构 DOI/卷期/页码，无"装饰性引用"。详见 `paper/reference_audit.md`（通过）。

### 2.3 结论反夸大（hedging 校准）
- 总费用、储能/优化价值、紧急占比等均直接引用冻结值，未四舍五入夸大。
- R2 预报窗口如实标注为 **CONDITIONAL**（绝对费用对预报调优有个位数百分比敏感），未粉饰为"完全稳健"。
- 模型评价 §6.2 明确列出三条局限（预报简单、分位未分层、弃光未对齐政策），无过度宣称。
- 报童临界比"理论预测 + 实测 argmin=80 吻合"这一强结论，有 R1 冻结数值（q=0/90）佐证，非臆断。

## 3. 遗留问题（非阻断，建议后续修正）

| 编号 | 位置 | 说明 |
|---|---|---|
| G1 | `robustness/Q2/q2_robustness_report.md` L12/L44/L53、`q2_robustness_summary.json` L46/L65 | 稳健性报告两处措辞不精确：(a) R2 称"±2%"但 7 天均匀实为 −4.88%；(b) 称储能价值"两种口径均 >400 万"，但基准口径 ≈359.6 万。**论文正文已按真实值修正**，建议后续一并修正稳健性报告措辞（不影响冻结值/结论）。 |
| G2 | `paper/sections/q2.md` 表格编号 | 仅稳健性表编号"表 5-1"，其余表未编号，建议 final_assembly 阶段统一为"表 1…表 5"。 |

## 4. 结论

**PASS**。Q2 论文通过整体质量保证：数值全部溯源冻结文件、引用全部真实、结论措辞严谨不夸大，一致性/完整性审计均通过。遗留 G1/G2 为低 severity 措辞/排版项，不阻断放行，建议在 final_assembly 前一并处理。
