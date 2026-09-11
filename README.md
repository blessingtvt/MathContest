# MathContest — 2026 CUMCM 数学建模 C 题

2026 年全国大学生数学建模竞赛 **C 题《微网与外部电网电力调控策略》** 的完整建模仓库。

**问题目标**：在分时/实时电价下，为含光伏与储能的微网制定最优购电调度策略，最小化全年购电费用，并满足「供电不低于负载」、储能容量/功率边界等约束。

## 题目四问

| 问 | 内容 | 方法 |
|---|---|---|
| Q1 | 代表日（附件1）最优购电策略 | 单日线性规划（LP, HiGHS） |
| Q2 | 全年日前计划（附件1+2+3），紧急购电 5 倍价 | 全年联合 LP + 日前光伏预报 |
| Q3 | 滚动预报下的购电调整（0/6/12/18 四时刻） | 滚动时域 MPC + 分段计费 |
| Q4 | 实时波动电价（附件4）下的调度 | 迁移 Q2/Q3 模型 |

## 目录结构

```
MathContest/
├── README.md            # 本文件
├── AGENTS.md            # AI 协作工作流编排策略（Claude Code）
├── CLAUDE.md            # 项目级 AI 协作约定
└── C题/                  # 主要工作目录
    ├── C题.pdf           # 题目原文
    ├── 附件/             # 原始附件（附件1-4 数据 + 附件5 结果模板）
    ├── data_raw/         # 原始数据（与附件对应，含结果模板）
    ├── data_clean/       # 清洗后数据（cleaned_data.pkl + 各附件 CSV）
    ├── data/             # 数据画像与审计报告
    ├── code/             # 代码
    │   ├── common.py     # 共享模型核心（LP / 基线 / 写盘）
    │   ├── Q1/ … Q4/     # 各问主模型 + 基线 + 代码计划 + 评审
    │   └── scripts/      # 数据清洗 / 图生成 / 数值冻结 / 稳健性
    ├── methods/          # 各问方法卡 / 决策记录 / 合理性分析
    ├── planning/         # 问题解析 / 分类 / 符号表 / 假设 / 清单
    ├── papers/           # 文献分析
    └── results/          # 结果 xlsx / 图 / 冻结数值 / 报告
```

### 目录说明

- **`code/common.py`**：全部四问共用的 LP 模型核心（`daily_lp`、`full_year_lp`、无储能/规则套利基线、Q3 滚动 MPC 组件、结果写盘函数），以及统一物理/费用参数（储能 1200–10800 kWh、充放 5000 kW、效率 0.9、紧急购电 5 倍价等）。
- **`code/Q*/q*_main.py`**：各问主入口，运行后生成 `results/Q*/result*.xlsx` 与 `experiments/round1/run_summary.json`。
- **`code/scripts/`**：`clean_data.py`（数据清洗）、`make_figures.py`（论文图）、`freeze_numbers.py`（冻结数值）、`robustness_check.py`（稳健性检验）。
- **`methods/Q*/q*_reasonableness_analysis.md`**：各问的约束检验 / 结果合理性 / 优化效果验证。
- **`planning/`**：`parse/problem_parse.json`（问题解析）、`classification/problem_classification.json`（分类）、`symbol_table.md`（符号表）、`model_assumptions.md`（假设）、`manifests/Q*.json`（各问门禁状态）。
- **`results/`**：`result*.xlsx`（题目要求的表格）、`figures/`（论文图）、`frozen_numbers.json/.md`（冻结数值）。

## 快速开始

依赖：Python 3.9+，`numpy scipy pandas openpyxl matplotlib`。

```bash
# 1. 数据清洗（生成 data_clean/cleaned_data.pkl）
python C题/code/scripts/clean_data.py

# 2. 逐问求解
python C题/code/Q1/q1_main.py
python C题/code/Q2/q2_main.py
python C题/code/Q3/q3_main.py
python C题/code/Q4/q4_main.py

# 3. 生成论文图
python C题/code/scripts/make_figures.py      # Q1 图
python C题/code/Q2/make_q2_figures.py         # Q2 图
```

## 核心建模约定

- **单位**：附件功率为 kW，决策变量为电量 kWh，转换系数 Δt = 1/6 h（10 分钟区间，每日 144 区间）。
- **能量平衡为不等式**：「供电 ≥ 需求」，即 `x + G·Δt + q ≥ L·Δt + c`；等号时为无弃光，大于时为弃光。
- **计划购电费按计划量结算**（非实际使用量）。
- **非完美预见**：Q2/Q3 的 0:00 计划用附件3 光伏预报，实际光伏决定紧急购电（5 倍价）。
