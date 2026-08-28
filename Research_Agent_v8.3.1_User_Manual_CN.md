# Research Agent v8.3.1 用户手册（中文版）

> **版本**: 8.3.1
> **文档语言**: 简体中文（技术术语与代码除外）
> **适用系统**: Windows 11 / Linux
> **最后更新**: 2026-08-18

---

## 目录

1. [总体架构](#1-总体架构)
2. [15模块功能详解](#2-15模块功能详解)
3. [输入输出关系](#3-输入输出关系)
4. [参数含义](#4-参数含义)
5. [YAML配置](#5-yaml配置)
6. [LLM配置](#6-llm配置)
7. [Skill/MCP配置](#7-skillmcp配置)
8. [独立运行方式](#8-独立运行方式)
9. [Pipeline运行方式](#9-pipeline运行方式)
10. [错误处理](#10-错误处理)
11. [附录](#11-附录)

---

## 1. 总体架构

### 1.1 系统概述

Research Agent 是一套**15模块的自动化科研系统**，旨在将学术研究的完整生命周期——从文献检索、论文分析、创新推理、实验设计、实验执行、结果分析到论文撰写与审稿模拟——全流程自动化。系统基于"模块独立运行、统一接口、共享LLM管理"三大架构原则构建，每个模块均可单独发布、独立运行，也可通过编排器（orchestrator）串联为端到端的完整流水线。

系统覆盖以下研究阶段：

- **文献阶段**（模块 01–04）：检索、获取、解析、分析、全景综述
- **创新阶段**（模块 05）：从论文局限性推导研究空白与创新点
- **设计阶段**（模块 06–07）：理论方法设计与实验规划
- **实验阶段**（模块 08–09）：合成仿真实验与真实GPU实验
- **分析阶段**（模块 10–11）：结果分析与图表生成
- **成文阶段**（模块 12–13）：论文撰写与引用补充
- **审校阶段**（模块 14–15）：审稿模拟与科研记忆管理

### 1.2 技术栈

| 组件 | 版本/规格 | 说明 |
|------|-----------|------|
| Python | 3.12 | 主运行语言 |
| Conda 环境 | `research_agent_v3` | 专用虚拟环境 |
| LLM 后端 | Ollama (localhost:11434) | 本地推理服务 |
| 推理模型 | `deepseek-r1:8b` | 逻辑推理专用 |
| 生成模型 | `gemma4:26b` | 文本生成专用 |
| 包管理 | pip / conda | 依赖管理 |
| 配置格式 | YAML | 所有配置文件 |
| 数据格式 | JSON / YAML / Markdown / DOCX / BibTeX | 多格式输出 |

### 1.3 架构原则

**原则一：模块独立运行**
每个模块以独立 zip 包形式发布，内含完整的 `src/`、`scripts/`、`input/`、`output/` 目录结构。用户可只下载需要的模块，按"放入输入文件 → 运行 → 读取报告"的三步流程使用，无需部署完整系统。

**原则二：统一接口**
所有模块遵循统一的输入输出约定：
- 输入文件统一放置于 `input/` 目录
- 输出文件统一写入 `output/` 目录
- 每个模块在 `output/` 下生成 `Stage_Report.md` 阶段报告
- 模块间通过 JSON/YAML 文件传递结构化数据，实现松耦合

**原则三：共享LLM管理**
所有模块共享统一的 LLM 调用层，通过 `llm_routing.yaml` 配置路由策略，实现：
- 双模型分工（推理模型 + 生成模型）
- 自动回退链（fallback chain）
- 用量追踪（`llm_usage_report.json`）
- 生产环境禁止使用 mock provider

### 1.4 目录结构

```
D:\Research Agent\Research_Agent_v3\
├── orchestrator/                    # 流水线编排器
│   ├── pipeline.py                  # 主流水线入口
│   ├── pipeline_runner.py           # 运行器
│   └── task_scheduler.py            # 任务调度
├── modules/                         # 15个模块实现
│   ├── 01_literature_search/
│   ├── 02_paper_acquisition/
│   ├── 02.5_paper_asset/
│   ├── 03_paper_analysis/
│   ├── 04_field_panorama/
│   ├── 05_innovation_reasoning/
│   ├── 06_theory_method/
│   ├── 07_experiment_planning/
│   ├── 08_synthetic_engine/
│   ├── 09_real_experiment/
│   ├── 10_result_analysis/
│   ├── 11_figure_generation/
│   ├── 12_paper_writing/
│   ├── 13_citation_supplement/
│   ├── 14_review_cycle/
│   └── 15_research_memory/
├── config/                         # 配置文件
│   ├── module_config.yaml           # 模块级配置
│   ├── research_task.yaml           # 研究任务定义
│   ├── llm_routing.yaml             # LLM路由策略
│   ├── providers.yaml               # LLM提供商配置
│   ├── experiment_mode.yaml         # 实验模式配置
│   ├── skill_registry.yaml          # Skill注册表（可选）
│   └── mcp_registry.yaml            # MCP服务注册表（可选）
├── data/                           # 共享数据
│   ├── literature/
│   │   ├── pdf/                    # 论文PDF
│   │   └── latex/                  # LaTeX源码
│   └── checkpoints/                # 实验检查点
├── scripts/                        # 工具脚本
│   ├── environment_check.py        # 环境检查
│   └── setup_conda.py              # 环境初始化
├── output/                         # 全局输出目录
│   └── llm_usage_report.json       # LLM用量报告
└── requirements.txt                # 依赖清单
```

---

## 2. 15模块功能详解

### 2.1 模块总览表

| 模块ID | 名称 | 核心功能 | 阶段 |
|--------|------|----------|------|
| 01 | 文献检索 | 从 arXiv/Semantic Scholar 检索论文 | 文献 |
| 02 | 论文获取与解析 | arXiv LaTeX 优先解析，PDF 转 Markdown | 文献 |
| 02.5 | 论文资产智能 | 提取论文图片和资产 | 文献 |
| 03 | 文献智能分析 | 10维度深度分析每篇论文 | 文献 |
| 04 | 研究领域全景 | 分类体系/趋势/矛盾/空白 | 文献 |
| 05 | 创新推理 | Limitations→Research Gap→Innovation | 创新 |
| 06 | 理论方法设计 | 方法规范/理论分析/置信度评估 | 设计 |
| 07 | 实验规划 | 实验矩阵与实验方案 | 设计 |
| 08 | 合成实验引擎 | Monte Carlo 仿真实验 | 实验 |
| 09 | 真实实验引擎 | GPU 实验，checkpoint 恢复 | 实验 |
| 10 | 结果分析 | Claim-Evidence 评估，决策路由 | 分析 |
| 11 | 图表生成 | Mermaid/LaTeX表格/Figure Prompt | 分析 |
| 12 | 论文撰写 | 生成 paper.docx/md/tex | 成文 |
| 13 | 引用与补充 | references.bib，补充材料 | 成文 |
| 14 | 审稿循环 | 顶会 Reviewer 模拟审稿 | 审校 |
| 15 | 科研记忆 | 记忆/决策日志/经验教训 | 审校 |

---

### 2.2 模块 01：文献检索

| 属性 | 值 |
|------|-----|
| **模块ID** | 01 |
| **名称** | 文献检索（Literature Search） |
| **功能描述** | 自动从 arXiv 和 Semantic Scholar 检索与研究主题相关的学术论文。支持关键词检索、时间范围过滤、引用量排序。构建结构化的 `literature_database.json`，记录每篇论文的标题、作者、摘要、DOI、arXiv ID、引用数、发表年份等元数据。系统建议每个研究主题检索至少 50 篇论文以保证文献覆盖度。 |
| **输入文件** | `research_task.yaml`（含研究主题关键词） |
| **输出文件** | `output/literature_database.json` |
| **LLM需求** | 低 — 主要为 API 调用，LLM 仅用于关键词扩展与去重判断 |

**关键参数**：
- `min_papers`: 最少检索论文数（默认 50）
- `sources`: 检索源（`arxiv`, `semantic_scholar`）
- `year_range`: 发表年份范围
- `sort_by`: 排序方式（`citations` / `recency` / `relevance`）

---

### 2.3 模块 02：论文获取与解析

| 属性 | 值 |
|------|-----|
| **模块ID** | 02 |
| **名称** | 论文获取与解析（Paper Acquisition & Parsing） |
| **功能描述** | 对 `literature_database.json` 中收录的论文逐篇获取全文。策略优先级：arXiv LaTeX 源码 > PDF 转 Markdown。LaTeX 源码经解析后提取正文结构（标题、摘要、章节、公式、表格、图片引用）；PDF 文件通过解析工具转为 Markdown 并保留结构。同时提取论文中的所有图片，生成 `figure_analysis.json` 记录图片编号、上下文描述和引用位置。 |
| **输入文件** | `output/literature_database.json` |
| **输出文件** | `output/papers/` 目录（每篇论文一个子目录，含 `paper.md`、`figures/`）、`output/figure_analysis.json` |
| **LLM需求** | 中 — 用于 LaTeX 结构解析辅助、图片语义标注 |

**解析策略**：
1. 优先从 arXiv 下载 LaTeX 源码包（`.tar.gz`），解压后解析 `.tex` 文件
2. 若 LaTeX 不可用，下载 PDF 并转为 Markdown
3. 提取所有嵌入图片（PDF 中的 figure 或 LaTeX 中的 `\includegraphics`）
4. 为每张图片生成语义描述和上下文位置

---

### 2.4 模块 02.5：论文资产智能

| 属性 | 值 |
|------|-----|
| **模块ID** | 02.5 |
| **名称** | 论文资产智能（Paper Asset Intelligence） |
| **功能描述** | 作为模块 02 的增强扩展，专门负责论文图片和科研资产的深度提取与智能管理。从已解析的论文中系统化提取所有图表资产，按论文 ID 归档，生成资产清单，并为每个资产生成结构化的元数据（类型、尺寸、所在章节、图注文本、引用关系）。支持后续模块（如图表生成、论文撰写）对资产的复用引用。 |
| **输入文件** | `output/papers/`（模块 02 输出）、`output/figure_analysis.json` |
| **输出文件** | `output/paper_assets/` 目录、`output/asset_index.json` |
| **LLM需求** | 中 — 用于图片分类标注和图注语义理解 |

---

### 2.5 模块 03：文献智能分析

| 属性 | 值 |
|------|-----|
| **模块ID** | 03 |
| **名称** | 文献智能分析（Intelligent Paper Analysis） |
| **功能描述** | 对每篇论文执行 **10 维度深度分析**，生成结构化的 `paper_analysis_trace.json`。十个分析维度如下：|
| | 1. **Problem（问题定义）**：论文解决什么问题，问题的重要性与动机 |
| | 2. **Method（方法概述）**：核心方法名称、方法论类别、与现有方法的关系 |
| | 3. **Architecture（架构）**：系统/模型架构图描述，各组件及连接关系 |
| | 4. **Algorithm（算法）**：关键算法步骤、伪代码、算法复杂度 |
| | 5. **Formula（公式）**：核心数学公式及其符号定义与推导 |
| | 6. **Loss（损失函数）**：训练目标、损失函数设计、优化策略 |
| | 7. **Dataset（数据集）**：使用的数据集名称、规模、来源、预处理 |
| | 8. **Experiment（实验）**：实验设置、对比基线、主要结果、消融实验 |
| | 9. **Limitation（局限性）**：方法/实验的局限与不足 |
| | 10. **Future Work（未来工作）**：作者提出的后续研究方向 |
| **输入文件** | `output/papers/`（模块 02 输出） |
| **输出文件** | `output/paper_analysis_trace.json` |
| **LLM需求** | 高 — 每篇论文的 10 维度分析需要大量 LLM 推理调用 |

---

### 2.6 模块 04：研究领域全景

| 属性 | 值 |
|------|-----|
| **模块ID** | 04 |
| **名称** | 研究领域全景（Research Field Panorama） |
| **功能描述** | 基于模块 03 的多篇论文分析结果，构建研究领域的全局视图，包含四大产出：|
| | 1. **分类体系（Taxonomy）**：将研究领域的方法、问题、数据集组织为层次化分类树 |
| | 2. **趋势分析（Trend Analysis）**：按时间维度分析研究热点演变、方法兴衰、引用增长趋势 |
| | 3. **矛盾图谱（Contradiction Map）**：识别不同论文间的方法冲突、结论矛盾、实验结果对立 |
| | 4. **研究空白（Research Gap）**：综合分类体系和矛盾图谱，发现尚未被充分研究的方向 |
| **输入文件** | `output/paper_analysis_trace.json`（模块 03 输出） |
| **输出文件** | `output/field_panorama.json`、`output/taxonomy.md`、`output/research_gaps.json` |
| **LLM需求** | 高 — 需要跨论文综合推理与领域知识 |

---

### 2.7 模块 05：创新推理

| 属性 | 值 |
|------|-----|
| **模块ID** | 05 |
| **名称** | 创新推理（Innovation Reasoning） |
| **功能描述** | 核心创新模块。从模块 03 提取所有论文的 Limitations 和 Future Work，结合模块 04 发现的研究空白，通过推理链生成创新研究方向。推理链为：**论文 Limitations + Future Work → Research Gap 聚合 → Innovation 方案生成 → 撞车检测**。撞车检测将生成的创新点与已有文献库对比，确保创新点未被既有论文覆盖。输出结构化的创新方案，含动机、方法概述、预期贡献、与最相似前作的差异（delta）。 |
| **输入文件** | `output/paper_analysis_trace.json`、`output/research_gaps.json` |
| **输出文件** | `output/innovation_proposals.json`、`output/collision_check_report.json` |
| **LLM需求** | 极高 — 需要深度推理模型的创意生成与对比分析 |

**撞车检测机制**：
- 将创新点拆解为"问题+方法+数据集"三要素
- 与 `literature_database.json` 中每篇论文做相似度匹配
- 若相似度超过阈值（默认 0.85），标记为撞车风险并要求重新生成

---

### 2.8 模块 06：理论方法设计

| 属性 | 值 |
|------|-----|
| **模块ID** | 06 |
| **名称** | 理论方法设计（Theory & Method Design） |
| **功能描述** | 将创新方案转化为形式化的理论与方法规范，产出三份核心文件：|
| | 1. **`method_spec.json`**：方法规范，含方法名、输入输出定义、模块划分、接口契约、超参数列表 |
| | 2. **`theory_analysis.md`**：理论分析文档，包含：假设（Assumptions）、定义（Definitions）、定理（Theorems）、引理（Lemmas）、推论（Corollaries）、证明（Proofs）、复杂度分析（Complexity Analysis） |
| | 3. **`theory_confidence.json`**：理论置信度评估，对每个假设和定理给出置信度分数与依据 |
| **输入文件** | `output/innovation_proposals.json`（模块 05 输出） |
| **输出文件** | `output/method_spec.json`、`output/theory_analysis.md`、`output/theory_confidence.json` |
| **LLM需求** | 极高 — 需要推理模型进行数学推导与形式化定义 |

---

### 2.9 模块 07：实验规划

| 属性 | 值 |
|------|-----|
| **模块ID** | 07 |
| **名称** | 实验规划（Experiment Planning） |
| **功能描述** | 基于方法规范设计完整的实验方案，产出两份核心文件：|
| | 1. **`experiment_matrix.yaml`**：实验矩阵，定义实验因子（factors）与水平（levels）的网格组合，包含主实验、消融实验（ablation）、对比实验（baseline comparison）、敏感性分析（sensitivity analysis） |
| | 2. **`experiment_plan.yaml`**：实验方案，定义每个实验配置的具体参数、数据集、评估指标、预期运行时间、资源需求 |
| **输入文件** | `output/method_spec.json`、`output/theory_analysis.md` |
| **输出文件** | `output/experiment_matrix.yaml`、`output/experiment_plan.yaml` |
| **LLM需求** | 中 — 实验设计推理与参数推荐 |

---

### 2.10 模块 08：合成实验引擎

| 属性 | 值 |
|------|-----|
| **模块ID** | 08 |
| **名称** | 合成实验引擎（Synthetic Experiment Engine） |
| **功能描述** | 通过 Monte Carlo 仿真在合成数据上快速验证理论方法的有效性。无需真实数据和 GPU 资源，即可在数分钟内完成大量实验配置的验证。采用**四层数据保存架构**：|
| | 1. **raw/**：原始仿真数据（每次 Monte Carlo trial 的原始输出）|
| | 2. **processed/**：处理后的数据（聚合、归一化、过滤）|
| | 3. **comparison/**：对比数据（各实验配置间的横向对比）|
| | 4. **statistics/**：统计结果（均值、方差、置信区间、显著性检验）|
| **输入文件** | `output/experiment_matrix.yaml`、`output/experiment_plan.yaml` |
| **输出文件** | `output/experiments/raw/`、`output/experiments/processed/`、`output/experiments/comparison/`、`output/experiments/statistics/` |
| **LLM需求** | 低 — 主要为数值计算，LLM 仅用于结果解读 |

---

### 2.11 模块 09：真实实验引擎

| 属性 | 值 |
|------|-----|
| **模块ID** | 09 |
| **名称** | 真实实验引擎（Real Experiment Engine） |
| **功能描述** | 在真实数据集和 GPU 上执行实验，是系统的核心实验执行模块。支持自动 checkpoint 恢复——实验中断后可从最近的检查点继续运行，无需从头开始。自动管理 GPU 资源分配、训练日志记录、中间结果保存。根据 `experiment_mode.yaml` 中注册的后端（backend）选择执行框架（PyTorch / JAX / 其他）。 |
| **输入文件** | `output/experiment_matrix.yaml`、`output/experiment_plan.yaml`、`config/experiment_mode.yaml` |
| **输出文件** | `output/experiments/real_results/`、`output/experiments/checkpoints/`、`output/experiments/logs/` |
| **LLM需求** | 低 — 主要为 GPU 训练，LLM 仅用于错误诊断 |

**Checkpoint 恢复机制**：
- 每 N 个 epoch 自动保存 checkpoint（含模型权重、优化器状态、当前 epoch）
- 恢复时自动检测最新 checkpoint 并从断点继续
- 支持手动指定 checkpoint 路径进行恢复

---

### 2.12 模块 10：结果分析

| 属性 | 值 |
|------|-----|
| **模块ID** | 10 |
| **名称** | 结果分析（Result Analysis） |
| **功能描述** | 对实验结果执行系统化分析，包含三大功能：|
| | 1. **Claim-Evidence 评估**：将理论方法设计（模块 06）中提出的每个 claim 与实验证据逐条对照，判定 claim 是否被实验结果支持（supported / partial / not_supported）|
| | 2. **统计分析**：计算效应量（effect size）、置信区间（CI）、显著性检验（t-test / Wilcoxon）、多重比较校正（Bonferroni / FDR）|
| | 3. **决策路由**：根据分析结果决定后续动作——通过则进入论文撰写（模块 12）；部分通过则返回实验规划（模块 07）补充实验；未通过则返回创新推理（模块 05）重新设计 |
| **输入文件** | `output/experiments/statistics/`、`output/theory_analysis.md`、`output/method_spec.json` |
| **输出文件** | `output/result_analysis.json`、`output/claim_evidence_map.json`、`output/decision_route.json` |
| **LLM需求** | 高 — Claim-Evidence 评估需要深度推理 |

---

### 2.13 模块 11：图表生成

| 属性 | 值 |
|------|-----|
| **模块ID** | 11 |
| **名称** | 图表生成（Figure Generation） |
| **功能描述** | 根据结果分析数据自动生成论文所需的全部图表，产出四类资产：|
| | 1. **Mermaid 源码**：架构图、流程图、时序图的 Mermaid 源码，可直接嵌入 Markdown |
| | 2. **LaTeX 表格**：结果对比表、消融表、参数表的 LaTeX 源码 |
| | 3. **Figure Prompt**：为复杂数据可视化生成绘图指令（prompt），可配合绘图工具生成高质量图表 |
| | 4. **`input_schema.md`**：描述每个图表的数据输入模式（schema），指导数据组织 |
| **输入文件** | `output/result_analysis.json`、`output/experiments/comparison/` |
| **输出文件** | `output/figures/mermaid/`、`output/figures/latex_tables/`、`output/figures/prompts/`、`output/input_schema.md` |
| **LLM需求** | 中 — 图表设计推理与 LaTeX 生成 |

---

### 2.14 模块 12：论文撰写

| 属性 | 值 |
|------|-----|
| **模块ID** | 12 |
| **名称** | 论文撰写（Paper Writing） |
| **功能描述** | 自动撰写完整学术论文，以 **`paper.docx`** 为主输出格式（同时生成 `paper.md` 和 `paper.tex`）。论文结构遵循标准学术论文格式：标题、摘要、引言、相关工作、方法（Method）、理论（Theory 章节含假设/定义/定理/证明）、实验、结果与分析、讨论、结论。Theory 章节直接引用模块 06 的 `theory_analysis.md` 内容。所有图表引用模块 11 的产出。 |
| **输入文件** | `output/result_analysis.json`、`output/theory_analysis.md`、`output/figures/`、`output/method_spec.json` |
| **输出文件** | `output/paper.docx`、`output/paper.md`、`output/paper.tex` |
| **LLM需求** | 极高 — 需要生成模型的大量高质量学术写作 |

---

### 2.15 模块 13：引用与补充

| 属性 | 值 |
|------|-----|
| **模块ID** | 13 |
| **名称** | 引用与补充（Citation & Supplement） |
| **功能描述** | 为论文补充参考文献和补充材料。产出两份核心文件：|
| | 1. **`references.bib`**：BibTeX 格式参考文献库，要求**不少于 30 条引用**。从 `literature_database.json` 中自动匹配论文正文引用的文献，补充经典奠基性工作，确保引用覆盖度 |
| | 2. **`supplementary.md`**：补充材料，包含额外实验细节、超参数完整表、数据集统计、证明详细推导、额外消融实验 |
| **输入文件** | `output/paper.docx`（或 `paper.md`）、`output/literature_database.json` |
| **输出文件** | `output/references.bib`、`output/supplementary.md` |
| **LLM需求** | 中 — 引用匹配与补充材料生成 |

---

### 2.16 模块 14：审稿循环

| 属性 | 值 |
|------|-----|
| **模块ID** | 14 |
| **名称** | 审稿循环（Review Cycle） |
| **功能描述** | 模拟顶会审稿流程，对生成的论文进行多轮审稿与修订。支持四大顶会的 Reviewer 角色模拟：|
| | - **CVPR / ICCV**：计算机视觉方向审稿人 |
| | - **NeurIPS**：神经信息处理方向审稿人 |
| | - **ICLR**：学习表征方向审稿人 |
| | 每轮审稿模拟 3 位独立 Reviewer，分别从原创性、技术严谨性、实验充分性、写作清晰度给出评分与修改意见。系统根据审稿意见自动修订论文，迭代至达到接收标准或达到最大轮数。 |
| **输入文件** | `output/paper.docx`、`output/references.bib`、`output/theory_analysis.md` |
| **输出文件** | `output/reviews/review_round_N.json`、`output/revisions/revision_round_N.md`、`output/final_review_decision.md` |
| **LLM需求** | 极高 — 审稿意见生成与论文修订 |

---

### 2.17 模块 15：科研记忆

| 属性 | 值 |
|------|-----|
| **模块ID** | 15 |
| **名称** | 科研记忆（Research Memory） |
| **功能描述** | 系统的长期记忆与知识管理模块，贯穿整个研究流程，持续记录决策、经验与教训。产出三份核心文件：|
| | 1. **`research_memory.md`**：研究记忆，记录整个研究过程中的关键发现、方法选择、数据来源、实验配置 |
| | 2. **`decision_log.md`**：决策日志，按时间线记录每个关键决策点（如为什么选择方法 A 而非方法 B）及其依据 |
| | 3. **`lessons_learned.md`**：经验教训，总结实验中的失败案例、踩坑记录、最佳实践 |
| **输入文件** | 所有前序模块的输出（持续累积） |
| **输出文件** | `output/research_memory.md`、`output/decision_log.md`、`output/lessons_learned.md` |
| **LLM需求** | 中 — 记忆提取与知识总结 |

---

## 3. 输入输出关系

### 3.1 模块流转图

以下流程图展示了 15 个模块之间的数据流传递关系。箭头 `→` 表示上游模块的输出作为下游模块的输入：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        文献阶段                                      │
│                                                                     │
│  [01 文献检索] ──→ [02 论文获取与解析] ──→ [02.5 论文资产智能]       │
│       │                    │                      │                 │
│       │                    ↓                      ↓                 │
│       │             [03 文献智能分析] ←────────────┘                 │
│       │                    │                                         │
│       │                    ↓                                         │
│       │             [04 研究领域全景]                                 │
│       │                    │                                         │
└───────┼────────────────────┼─────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼─────────────────────────────────────────┐
        │          │         │           创新阶段                       │
        │          │         ↓                                         │
        │          │   [05 创新推理] ←── 撞车检测 ←── literature_db     │
        │          │         │                                         │
        │          └─────────┼─────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼─────────────────────────────────────────┐
        │          │         │           设计阶段                       │
        │          │         ↓                                         │
        │          │   [06 理论方法设计]                                 │
        │          │         │                                         │
        │          │         ↓                                         │
        │          │   [07 实验规划]                                    │
        │          │         │                                         │
        │          └─────────┼─────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼─────────────────────────────────────────┐
        │          │         │           实验阶段                       │
        │          │    ┌────┴────┐                                    │
        │          │    ↓         ↓                                     │
        │          │ [08 合成]  [09 真实]                               │
        │          │    └────┬────┘                                    │
        │          └─────────┼─────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼─────────────────────────────────────────┐
        │          │         │           分析阶段                       │
        │          │         ↓                                         │
        │          │   [10 结果分析] ──→ 决策路由                        │
        │          │         │           │                              │
        │          │         │     ┌─────┼─────┐                       │
        │          │         │     ↓     ↓     ↓                       │
        │          │         │  通过  部分  未通过                     │
        │          │         │   │     │     │                         │
        │          │         │   │     ↓     ↓                         │
        │          │         │   │  →[07] →[05]                        │
        │          └─────────┼───┼─────────────────────────────────────┘
        │                    │   │
        │          ┌─────────┼───┼─────────────────────────────────────┐
        │          │         │   │           成文阶段                   │
        │          │         ↓   ↓                                         │
        │          │   [11 图表生成]                                       │
        │          │         │                                            │
        │          │         ↓                                            │
        │          │   [12 论文撰写]                                      │
        │          │         │                                            │
        │          │         ↓                                            │
        │          │   [13 引用与补充]                                    │
        │          └─────────┼──────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼──────────────────────────────────────────┐
        │          │         │           审校阶段                       │
        │          │         ↓                                            │
        │          │   [14 审稿循环]                                      │
        │          │         │                                            │
        │          └─────────┼──────────────────────────────────────────┘
        │                    │
        │          ┌─────────┼──────────────────────────────────────────┐
        └──────────┼─────────┼──────────────────────────────────────────┘
                   │         │
                   ↓         ↓
              [15 科研记忆]（贯穿全程，持续累积）
```

### 3.2 数据流说明

| 上游模块 | 传递文件 | 下游模块 |
|----------|----------|----------|
| 01 文献检索 | `literature_database.json` | 02 论文获取与解析 |
| 02 论文获取与解析 | `papers/`、`figure_analysis.json` | 02.5 论文资产智能、03 文献智能分析 |
| 02.5 论文资产智能 | `paper_assets/`、`asset_index.json` | 03 文献智能分析、11 图表生成 |
| 03 文献智能分析 | `paper_analysis_trace.json` | 04 研究领域全景、05 创新推理 |
| 04 研究领域全景 | `research_gaps.json` | 05 创新推理 |
| 05 创新推理 | `innovation_proposals.json` | 06 理论方法设计 |
| 06 理论方法设计 | `method_spec.json`、`theory_analysis.md` | 07 实验规划、10 结果分析、12 论文撰写 |
| 07 实验规划 | `experiment_matrix.yaml`、`experiment_plan.yaml` | 08 合成实验引擎、09 真实实验引擎 |
| 08 合成实验引擎 | `experiments/raw/` 等 | 10 结果分析 |
| 09 真实实验引擎 | `experiments/real_results/` | 10 结果分析 |
| 10 结果分析 | `result_analysis.json`、`decision_route.json` | 11 图表生成、12 论文撰写 |
| 11 图表生成 | `figures/`、`input_schema.md` | 12 论文撰写 |
| 12 论文撰写 | `paper.docx` | 13 引用与补充、14 审稿循环 |
| 13 引用与补充 | `references.bib`、`supplementary.md` | 14 审稿循环 |
| 14 审稿循环 | 修订后的论文 | 15 科研记忆 |
| 全部模块 | 所有输出 | 15 科研记忆（持续累积） |

### 3.3 决策路由

模块 10（结果分析）的决策路由是流水线中的关键分支点：

```
                    ┌── Claim 全部 supported ──→ 继续 [11 图表生成] → [12 论文撰写]
                    │
[10 结果分析] ──────┼── Claim 部分 supported ──→ 返回 [07 实验规划] 补充实验
                    │
                    └── Claim 未 supported ───→ 返回 [05 创新推理] 重新设计
```

---

## 4. 参数含义

### 4.1 `module_config.yaml` 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `module_id` | string | — | 模块唯一标识符 |
| `module_name` | string | — | 模块显示名称 |
| `enabled` | bool | `true` | 是否启用该模块 |
| `input_dir` | path | `./input` | 输入文件目录 |
| `output_dir` | path | `./output` | 输出文件目录 |
| `llm_model` | string | `deepseek-r1:8b` | 该模块使用的 LLM 模型 |
| `llm_fallback` | bool | `true` | 是否启用 LLM 回退链 |
| `max_retries` | int | `3` | LLM 调用失败最大重试次数 |
| `timeout_seconds` | int | `300` | 单次 LLM 调用超时（秒） |
| `temperature` | float | `0.7` | LLM 生成温度 |
| `max_tokens` | int | `4096` | LLM 最大输出 token 数 |
| `parallel_workers` | int | `4` | 并行处理工作线程数 |
| `checkpoint_interval` | int | `100` | Checkpoint 保存间隔（模块 09） |
| `min_papers` | int | `50` | 最少文献检索数（模块 01） |
| `min_citations` | int | `30` | 最少引用文献数（模块 13） |
| `review_rounds` | int | `3` | 审稿循环最大轮数（模块 14） |
| `venue` | string | `CVPR` | 模拟审稿目标会议（模块 14） |
| `seed` | int | `42` | 随机种子，保证可复现 |

### 4.2 参数使用建议

- **`temperature`**：推理任务（模块 03/05/06/10）建议 0.3-0.5 以保证严谨性；生成任务（模块 12/14）建议 0.7-0.9 以保证多样性
- **`max_tokens`**：论文撰写模块建议设为 8192 以上；分析模块 4096 通常足够
- **`parallel_workers`**：文献分析和实验执行模块建议根据 CPU/GPU 核心数调整
- **`seed`**：同一 seed 保证结果可复现；不同 seed 可用于多轮实验取统计平均

---

## 5. YAML配置

### 5.1 `module_config.yaml` 示例

```yaml
# module_config.yaml — 模块级配置
# 定义每个模块的运行参数

modules:
  - module_id: "01"
    module_name: "文献检索"
    enabled: true
    input_dir: "./input"
    output_dir: "./output"
    llm_model: "gemma4:26b"
    llm_fallback: true
    max_retries: 3
    timeout_seconds: 300
    temperature: 0.5
    max_tokens: 2048
    parallel_workers: 4
    params:
      min_papers: 50
      sources:
        - arxiv
        - semantic_scholar
      year_range: [2020, 2026]
      sort_by: "citations"

  - module_id: "03"
    module_name: "文献智能分析"
    enabled: true
    llm_model: "deepseek-r1:8b"
    temperature: 0.3
    max_tokens: 4096
    params:
      dimensions: 10
      batch_size: 5

  - module_id: "05"
    module_name: "创新推理"
    enabled: true
    llm_model: "deepseek-r1:8b"
    temperature: 0.5
    max_tokens: 8192
    params:
      collision_threshold: 0.85
      max_proposals: 10

  - module_id: "09"
    module_name: "真实实验引擎"
    enabled: true
    params:
      checkpoint_interval: 100
      gpu_device: "cuda:0"
      mixed_precision: "bf16"

  - module_id: "14"
    module_name: "审稿循环"
    enabled: true
    llm_model: "deepseek-r1:8b"
    params:
      venue: "CVPR"
      review_rounds: 3
      num_reviewers: 3

global:
  seed: 42
  log_level: "INFO"
  save_intermediate: true
```

### 5.2 `research_task.yaml` 示例

```yaml
# research_task.yaml — 研究任务定义
# 定义当前研究任务的主题、范围和目标

task_id: "vlm_safety_001"
task_name: "视觉语言模型安全性研究"
description: >
  研究视觉语言模型（VLM）在面对对抗性图片输入时的安全性问题，
  探索新型防御方法以提升模型鲁棒性。

research_keywords:
  primary:
    - "vision-language model safety"
    - "adversarial attack VLM"
    - "multimodal robustness"
  secondary:
    - "CLIP security"
    - "cross-modal adversarial"
    - "jailbreak multimodal"

research_questions:
  - "如何检测视觉语言模型中的跨模态对抗攻击？"
  - "能否设计一种轻量级防御方法在不损失性能的前提下提升安全性？"
  - "现有防御方法在多模态场景下的局限性是什么？"

target_venue: "CVPR"
target_year: 2026

literature:
  min_papers: 50
  max_papers: 150
  year_range: [2020, 2026]
  sources:
    - arxiv
    - semantic_scholar

experiment:
  mode: "both"          # both = 合成 + 真实
  gpu_required: true
  estimated_hours: 48

output:
  format: "docx"         # docx / md / tex
  language: "en"         # 论文输出语言
  min_citations: 30
```

### 5.3 `llm_routing.yaml` 示例

```yaml
# llm_routing.yaml — LLM路由策略
# 定义不同任务的模型分配与回退链

routing_rules:
  # 推理类任务 → 使用 deepseek-r1:8b
  reasoning:
    model: "deepseek-r1:8b"
    provider: "ollama_r1"
    tasks:
      - "paper_analysis"        # 模块 03
      - "innovation_reasoning"  # 模块 05
      - "theory_design"         # 模块 06
      - "result_analysis"       # 模块 10
      - "review_simulation"     # 模块 14
    temperature: 0.3
    max_tokens: 4096

  # 生成类任务 → 使用 gemma4:26b
  generation:
    model: "gemma4:26b"
    provider: "ollama"
    tasks:
      - "literature_search"     # 模块 01
      - "field_panorama"         # 模块 04
      - "figure_generation"     # 模块 11
      - "paper_writing"         # 模块 12
      - "citation_supplement"   # 模块 13
    temperature: 0.7
    max_tokens: 8192

# 回退链：当首选 provider 不可用时按顺序尝试
fallback_chain:
  - "ollama_r1"      # 首选：本地 deepseek-r1
  - "ollama"          # 次选：本地 gemma4
  - "deepseek"        # 第三：远程 DeepSeek API
  - "openai"          # 第四：OpenAI API
  - "mock"            # 最后：mock（仅测试，生产禁用）

# 生产环境约束
production:
  forbid_mock: true         # 禁止使用 mock provider
  max_daily_tokens: 500000  # 每日 token 上限
  track_usage: true         # 启用用量追踪

# 用量追踪
usage_tracking:
  enabled: true
  output_file: "output/llm_usage_report.json"
  log_level: "detailed"     # detailed / summary
  fields:
    - timestamp
    - module_id
    - provider
    - model
    - task_type
    - prompt_tokens
    - completion_tokens
    - latency_ms
    - status
```

### 5.4 `providers.yaml` 示例

```yaml
# providers.yaml — LLM提供商配置
# 定义各 LLM provider 的连接参数

providers:
  # 本地 Ollama - deepseek-r1 推理模型
  ollama_r1:
    type: "ollama"
    base_url: "http://localhost:11434"
    model: "deepseek-r1:8b"
    api_type: "chat"
    timeout: 300
    max_retries: 3
    options:
      temperature: 0.3
      num_ctx: 8192
      num_gpu: 1
      seed: 42

  # 本地 Ollama - gemma4 生成模型
  ollama:
    type: "ollama"
    base_url: "http://localhost:11434"
    model: "gemma4:26b"
    api_type: "chat"
    timeout: 300
    max_retries: 3
    options:
      temperature: 0.7
      num_ctx: 8192
      num_gpu: 1
      seed: 42

  # 远程 DeepSeek API
  deepseek:
    type: "openai_compatible"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    api_key_env: "DEEPSEEK_API_KEY"
    timeout: 120
    max_retries: 2

  # OpenAI API
  openai:
    type: "openai"
    model: "gpt-4o"
    api_key_env: "OPENAI_API_KEY"
    timeout: 120
    max_retries: 2

  # Mock provider（仅用于测试）
  mock:
    type: "mock"
    model: "mock-model"
    responses:
      default: "This is a mock response."

# 健康检查
health_check:
  interval_seconds: 60
  on_failure: "fallback"
  retry_after_seconds: 300
```

---

## 6. LLM配置

### 6.1 双模型策略

Research Agent v8.3.1 采用**双模型分工策略**，充分发挥不同模型的优势：

| 模型 | 角色 | 擅长任务 | 使用模块 |
|------|------|----------|----------|
| `deepseek-r1:8b` | 推理模型（Reasoning） | 逻辑推理、数学推导、分析判断、审稿评审 | 03, 05, 06, 10, 14 |
| `gemma4:26b` | 生成模型（Generation） | 文本生成、论文撰写、图表描述、文献综述 | 01, 04, 11, 12, 13 |

**分工理由**：
- `deepseek-r1:8b` 具备链式思维（Chain-of-Thought）能力，适合需要严谨逻辑推理的任务
- `gemma4:26b` 参数量更大，生成文本更流畅自然，适合需要高质量长文本输出的任务
- 双模型均通过本地 Ollama 部署，无需外部 API 密钥，保障数据隐私与运行成本可控

### 6.2 Ollama 本地部署

两个模型均通过 **Ollama** 在本地运行，服务地址为 `localhost:11434`。

**安装与拉取模型**：

```bash
# 安装 Ollama（首次使用）
# Windows: 从 https://ollama.com 下载安装包
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull deepseek-r1:8b
ollama pull gemma4:26b

# 验证模型已就绪
ollama list
```

**验证服务可用**：

```bash
# 检查 Ollama 服务状态
ollama list

# 测试模型响应
ollama run deepseek-r1:8b "请用一句话解释什么是视觉语言模型"
```

### 6.3 回退链机制

当首选 LLM provider 不可用时，系统按以下顺序自动回退：

```
ollama_r1  ──(失败)──→  ollama  ──(失败)──→  deepseek  ──(失败)──→  openai  ──(失败)──→  mock
(本地首选)              (本地次选)            (远程API)            (远程API)           (仅测试)
```

**回退触发条件**：
- 连接超时（超过 `timeout_seconds`）
- HTTP 错误（5xx 服务端错误）
- 模型未找到（model not found）
- 速率限制（429 Too Many Requests）

**回退日志**：每次回退都会记录到 `output/llm_usage_report.json`，包含触发原因、回退到的 provider、延迟等信息。

### 6.4 用量追踪

系统自动追踪所有 LLM 调用，生成 `output/llm_usage_report.json`：

```json
{
  "report_date": "2026-08-18",
  "total_calls": 1247,
  "total_prompt_tokens": 2856432,
  "total_completion_tokens": 1874521,
  "by_provider": {
    "ollama_r1": {
      "calls": 523,
      "prompt_tokens": 1203421,
      "completion_tokens": 845632,
      "avg_latency_ms": 3421
    },
    "ollama": {
      "calls": 689,
      "prompt_tokens": 1456789,
      "completion_tokens": 982453,
      "avg_latency_ms": 2156
    },
    "deepseek": {
      "calls": 35,
      "prompt_tokens": 196222,
      "completion_tokens": 46436,
      "avg_latency_ms": 5123
    }
  },
  "by_module": {
    "03": { "calls": 312, "tokens": 892341 },
    "05": { "calls": 187, "tokens": 567823 },
    "12": { "calls": 456, "tokens": 1234567 }
  },
  "fallback_events": 12,
  "errors": 3
}
```

### 6.5 Mock Provider 限制

`mock` provider 是回退链的最后一环，仅返回固定测试响应。**生产环境严格禁止使用 mock provider**：

- `llm_routing.yaml` 中 `production.forbid_mock: true` 强制禁用
- 若所有正常 provider 均不可用且回退至 mock，系统将抛出错误并终止任务
- mock 仅用于单元测试和开发调试

---

## 7. Skill/MCP配置

### 7.1 概述

Skill 和 MCP（Model Context Protocol）服务器是 Research Agent v8.3.1 的**可选增强组件**。它们为系统提供额外能力扩展，但非运行必需。系统在无 Skill 和 MCP 配置的情况下仍可完整运行全部 15 个模块。

### 7.2 Skill 配置

Skill 是可复用的能力模块，通过 `skill_registry.yaml` 注册。Skill 为可选组件，用户可根据需要启用：

```yaml
# skill_registry.yaml — Skill注册表（可选）

skills:
  # 示例：文献检索增强 Skill
  - name: "arxiv_advanced_search"
    enabled: false                    # 默认关闭，按需启用
    module: "01"
    description: "arXiv 高级搜索，支持分类过滤与全文检索"
    config:
      max_results: 200
      categories:
        - "cs.CV"
        - "cs.CL"
        - "cs.AI"

  # 示例：图表美化 Skill
  - name: "figure_beautifier"
    enabled: false
    module: "11"
    description: "自动美化生成的 Mermaid 和 LaTeX 图表"
    config:
      theme: "academic"
      color_palette: "colorblind_safe"

  # 示例：论文润色 Skill
  - name: "paper_polisher"
    enabled: false
    module: "12"
    description: "学术英文润色，去除 AI 痕迹"
    config:
      style: "academic"
      remove_ai_patterns: true
```

**Skill 加载机制**：
- 系统启动时读取 `skill_registry.yaml`
- 仅加载 `enabled: true` 的 Skill
- Skill 失载不影响主流程运行（fail-safe）
- Skill 通过统一接口注入对应模块

### 7.3 MCP 配置

MCP 服务器提供外部工具和数据源接入能力，通过 `mcp_registry.yaml` 注册。MCP 同样为可选组件：

```yaml
# mcp_registry.yaml — MCP服务注册表（可选）

mcp_servers:
  # 示例：学术数据库 MCP
  - name: "academic_db"
    enabled: false
    transport: "stdio"
    command: "python"
    args: ["-m", "mcp_academic_server"]
    description: "接入 PubMed/arXiv 等学术数据库"
    used_by_modules: ["01", "13"]

  # 示例：实验追踪 MCP
  - name: "experiment_tracker"
    enabled: false
    transport: "sse"
    url: "http://localhost:8080/mcp"
    description: "接入 MLflow/WandB 实验追踪平台"
    used_by_modules: ["08", "09"]

  # 示例：LaTeX 编译 MCP
  - name: "latex_compiler"
    enabled: false
    transport: "stdio"
    command: "latex-mcp-server"
    description: "在线 LaTeX 编译与预览"
    used_by_modules: ["12"]
```

**MCP 加载机制**：
- 系统启动时读取 `mcp_registry.yaml`
- 仅加载 `enabled: true` 的 MCP 服务器
- MCP 连接失败不影响主流程运行（fail-safe）
- 模块通过 MCP 客户端调用注册的工具

### 7.4 Skill/MCP 与核心模块的关系

```
┌──────────────────────────────────────────────────┐
│              Research Agent 核心系统              │
│                                                  │
│    15 个核心模块（必需，独立可运行）              │
│                                                  │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│    │ 模块 01 │  │ 模块 02 │  │  ...    │        │
│    └────┬────┘  └────┬────┘  └─────────┘        │
│         │            │                            │
└─────────┼────────────┼───────────────────────────┘
          │            │
     ┌────┴────┐  ┌────┴────┐
     │  Skill  │  │  Skill  │      ← 可选增强
     │ (可选)  │  │ (可选)  │
     └─────────┘  └─────────┘
          │            │
     ┌────┴────┐  ┌────┴────┐
     │   MCP   │  │   MCP   │      ← 可选外部接入
     │ (可选)  │  │ (可选)  │
     └─────────┘  └─────────┘
```

**关键原则**：Skill 和 MCP 是"锦上添花"而非"雪中送炭"。系统在没有它们的情况下仍可完整运行；启用它们可增强特定模块的能力，但不会改变核心流程。

---

## 8. 独立运行方式

每个模块均以独立 zip 包发布，可脱离完整系统单独运行。以下是通用运行步骤：

### 步骤 1：解压模块包

将模块 zip 包解压到任意目录：

```bash
# 示例：解压模块 03（文献智能分析）
# 假设模块包为 module_03_paper_analysis_v8.3.1.zip

# Windows PowerShell
Expand-Archive -Path "module_03_paper_analysis_v8.3.1.zip" -DestinationPath "D:\modules\module_03"

# Linux
unzip module_03_paper_analysis_v8.3.1.zip -d ~/modules/module_03
```

解压后目录结构：

```
module_03/
├── src/
│   └── implementation.py        # 模块主入口
├── scripts/
│   └── environment_check.py     # 环境检查脚本
├── input/                       # 放置输入文件
├── output/                      # 运行输出
├── config/
│   └── module_config.yaml       # 模块配置
├── requirements.txt             # 依赖清单
└── README.md                    # 模块说明
```

### 步骤 2：环境检查

运行环境检查脚本，确认 Python 版本、依赖包和 LLM 服务可用：

```bash
conda activate research_agent_v3
cd D:\modules\module_03
python scripts/environment_check.py
```

环境检查脚本会检测：
- Python 版本是否为 3.12
- 所需依赖包是否已安装（对照 `requirements.txt`）
- Ollama 服务是否在 `localhost:11434` 运行
- 所需模型（`deepseek-r1:8b` / `gemma4:26b`）是否已拉取
- GPU 是否可用（仅模块 09 需要）

**检查通过的输出示例**：

```
[OK] Python 3.12.0
[OK] 依赖包检查通过 (23/23)
[OK] Ollama 服务运行中 (localhost:11434)
[OK] 模型 deepseek-r1:8b 已就绪
[OK] 模型 gemma4:26b 已就绪
[OK] 环境检查全部通过，可以运行模块
```

### 步骤 3：放置输入文件

将上游模块的输出文件复制到 `input/` 目录。每个模块所需的输入文件参见第 2 节各模块的"输入文件"说明。

```bash
# 示例：模块 03 需要模块 02 的输出
copy "D:\Research Agent\Research_Agent_v3\output\papers" "D:\modules\module_03\input\papers" /E /I
copy "D:\Research Agent\Research_Agent_v3\output\figure_analysis.json" "D:\modules\module_03\input\"
```

### 步骤 4：运行模块

通过 Python 模块方式运行：

```bash
conda activate research_agent_v3
cd D:\modules\module_03
python -m src.implementation
```

模块运行过程中会：
1. 读取 `config/module_config.yaml` 配置
2. 加载 `input/` 目录中的输入文件
3. 执行模块核心逻辑（含 LLM 调用）
4. 将结果写入 `output/` 目录
5. 生成 `output/Stage_Report.md` 阶段报告

### 步骤 5：查看结果

运行完成后，查看阶段报告获取运行结果摘要：

```bash
# 查看阶段报告
type D:\modules\module_03\output\Stage_Report.md
```

`Stage_Report.md` 包含：
- 模块运行状态（成功/部分成功/失败）
- 输入文件统计
- 处理过程摘要
- 输出文件清单
- LLM 调用统计
- 错误与警告（如有）

**阶段报告示例**：

```markdown
# 模块 03：文献智能分析 — 阶段报告

## 运行状态：成功

## 输入统计
- 论文总数：52 篇
- 总图片数：318 张

## 处理摘要
- 完成 10 维度分析：52 篇
- 平均每篇分析耗时：23.5 秒
- LLM 调用总数：520 次

## 输出文件
- output/paper_analysis_trace.json (12.3 MB)
- output/analysis_summary.md (45 KB)

## LLM 统计
- deepseek-r1:8b 调用 520 次
- 总 prompt tokens: 1,234,567
- 总 completion tokens: 567,890
- 回退事件：0 次

## 警告
- 无
```

---

## 9. Pipeline运行方式

### 9.1 完整流水线运行

通过编排器（orchestrator）串联运行全部 15 个模块，实现端到端的自动化研究流程：

```bash
# 激活 Conda 环境
conda activate research_agent_v3

# 切换到项目目录
cd "D:\Research Agent\Research_Agent_v3"

# 运行完整流水线
python orchestrator/pipeline.py --task vlm_safety_001
```

### 9.2 命令行参数

```bash
python orchestrator/pipeline.py [选项]

必需参数：
  --task TASK_ID          研究任务 ID（对应 research_task.yaml 中的 task_id）

可选参数：
  --config CONFIG_PATH    模块配置文件路径（默认 config/module_config.yaml）
  --start MODULE_ID       从指定模块开始（默认 01）
  --end MODULE_ID         运行到指定模块结束（默认 15）
  --skip MODULE_IDS       跳过指定模块（逗号分隔，如 --skip 08,09）
  --resume                从上次中断处恢复运行
  --dry-run               仅显示执行计划，不实际运行
  --verbose               显示详细日志
  --help                  显示帮助信息
```

### 9.3 运行示例

**完整运行**：

```bash
python orchestrator/pipeline.py --task vlm_safety_001
```

**仅运行文献阶段（模块 01-04）**：

```bash
python orchestrator/pipeline.py --task vlm_safety_001 --start 01 --end 04
```

**跳过真实实验（仅用合成实验）**：

```bash
python orchestrator/pipeline.py --task vlm_safety_001 --skip 09
```

**从中断处恢复**：

```bash
python orchestrator/pipeline.py --task vlm_safety_001 --resume
```

**预览执行计划**：

```bash
python orchestrator/pipeline.py --task vlm_safety_001 --dry-run
```

### 9.4 流水线执行流程

```
1. 加载 research_task.yaml 任务定义
       ↓
2. 加载 module_config.yaml 模块配置
       ↓
3. 初始化 LLM 路由（连接 Ollama，验证模型）
       ↓
4. 按顺序执行模块 01 → 02 → 02.5 → 03 → 04 → 05 → 06 → 07
       ↓
5. 执行实验模块 08（合成）和/或 09（真实）
       ↓
6. 执行模块 10 结果分析
       ↓
7. 决策路由判断：
   - 通过 → 继续 11 → 12 → 13 → 14 → 15
   - 部分通过 → 返回 07 补充实验
   - 未通过 → 返回 05 重新设计
       ↓
8. 生成最终论文 paper.docx + references.bib
       ↓
9. 审稿循环（模块 14）迭代修订
       ↓
10. 更新科研记忆（模块 15）
       ↓
11. 输出流水线总结报告
```

### 9.5 流水线中断与恢复

流水线支持中断恢复。系统在每个模块完成后自动保存进度状态。若运行中断（如机器关机、网络断开），使用 `--resume` 可从最后完成的模块继续：

```bash
# 中断后恢复
python orchestrator/pipeline.py --task vlm_safety_001 --resume

# 系统会显示：
# [INFO] 检测到上次进度：模块 07 已完成
# [INFO] 从模块 08 开始继续执行
```

### 9.6 人工介入

当系统遇到需要人工判断的情况时，会生成 `output/Human_Input_Request.md` 文件并暂停运行。用户需阅读该文件，填写人工输入后继续：

```bash
# 查看人工输入请求
type output\Human_Input_Request.md

# 按照文件指引填写人工输入后，恢复运行
python orchestrator/pipeline.py --task vlm_safety_001 --resume
```

人工介入触发场景包括：
- 创新点撞车检测无法自动判定
- 实验结果与理论严重不符，需人工确认
- 审稿循环达到最大轮数仍未通过
- LLM 连续失败超过阈值

---

## 10. 错误处理

### 10.1 常见错误与解决方案

#### 错误 1：输入文件缺失

**现象**：
```
[ERROR] 模块 03 运行失败：未找到输入文件 input/papers/
[ERROR] 请将模块 02 的输出文件放入 input/ 目录
```

**原因**：`input/` 目录缺少所需文件。

**解决方案**：
1. 确认上游模块已成功运行
2. 将上游模块的输出文件复制到当前模块的 `input/` 目录
3. 重新运行模块

```bash
# 确认上游输出存在
dir "D:\Research Agent\Research_Agent_v3\output\papers"

# 复制到输入目录
xcopy "D:\Research Agent\Research_Agent_v3\output\papers" "D:\modules\module_03\input\papers\" /E /I

# 重新运行
python -m src.implementation
```

---

#### 错误 2：LLM 连接失败

**现象**：
```
[ERROR] 无法连接到 Ollama 服务 (localhost:11434)
[ERROR] ConnectionRefusedError: [Errno 111] Connection refused
```

**原因**：Ollama 服务未启动或模型未拉取。

**解决方案**：
1. 检查 Ollama 服务状态
2. 确认模型已拉取
3. 重启 Ollama 服务

```bash
# 检查 Ollama 服务
ollama list

# 若无输出或报错，启动 Ollama 服务
# Windows: 通过开始菜单启动 Ollama
# Linux: sudo systemctl start ollama

# 确认模型已拉取
ollama list
# 应显示：
# NAME                SIZE     MODIFIED
# deepseek-r1:8b      4.7 GB   2026-08-18
# gemma4:26b          16 GB    2026-08-18

# 若模型缺失，拉取模型
ollama pull deepseek-r1:8b
ollama pull gemma4:26b

# 测试模型可用
ollama run deepseek-r1:8b "测试"
```

---

#### 错误 3：实验后端未注册

**现象**：
```
[ERROR] 模块 09 运行失败：未找到已注册的实验后端
[ERROR] 请检查 config/experiment_mode.yaml 配置
```

**原因**：`experiment_mode.yaml` 中未注册任何实验执行后端，或后端配置有误。

**解决方案**：
1. 检查 `experiment_mode.yaml` 配置
2. 确认后端框架已安装
3. 注册正确的后端

```bash
# 查看 experiment_mode.yaml
type config\experiment_mode.yaml
```

```yaml
# experiment_mode.yaml 正确配置示例
experiment_mode:
  backends:
    - name: "pytorch"
      type: "torch"
      enabled: true
      config:
        device: "cuda:0"
        mixed_precision: "bf16"
        distributed: false

    # - name: "jax"
    #   type: "jax"
    #   enabled: false
    #   config:
    #     devices: [0, 1]

  default_backend: "pytorch"
  auto_select: true    # 自动选择可用后端
```

---

#### 错误 4：文献数量不足

**现象**：
```
[WARNING] 检索到的文献数量不足：当前 32 篇，要求至少 50 篇
[ERROR] 文献数量低于阈值，无法保证分析质量
```

**原因**：arXiv/Semantic Scholar 检索结果少于 `min_papers`（默认 50）阈值。

**解决方案**：
1. 手动添加更多论文到 `data/literature/pdf/` 目录
2. 扩展检索关键词
3. 放宽年份范围

```bash
# 方法 1：手动添加 PDF 论文
# 将相关论文 PDF 复制到数据目录
copy "C:\Downloads\paper1.pdf" "D:\Research Agent\Research_Agent_v3\data\literature\pdf\"
copy "C:\Downloads\paper2.pdf" "D:\Research Agent\Research_Agent_v3\data\literature\pdf\"

# 方法 2：修改 research_task.yaml 扩展关键词
# 添加更多 secondary 关键词，放宽 year_range

# 方法 3：降低 min_papers 阈值（不推荐，可能影响分析质量）
# 修改 module_config.yaml 中 min_papers: 30

# 重新运行模块 01
python -m src.implementation
```

---

#### 错误 5：人工输入请求

**现象**：系统在 `output/` 目录生成 `Human_Input_Request.md` 文件并暂停运行。

**原因**：系统遇到需要人工判断的情况。

**解决方案**：
1. 阅读 `Human_Input_Request.md` 了解请求内容
2. 按文件指引提供人工输入
3. 使用 `--resume` 恢复运行

```bash
# 查看人工输入请求
type output\Human_Input_Request.md
```

**`Human_Input_Request.md` 示例**：

```markdown
# 人工输入请求

## 请求时间：2026-08-18 14:32:00

## 模块：05 创新推理

## 请求原因
创新点 "跨模态对抗训练防御方法" 的撞车检测相似度为 0.83（阈值 0.85），
处于边界区域，无法自动判定是否为撞车。

## 相似论文
- arXiv:2401.12345 "Cross-Modal Adversarial Training for VLM Safety" (相似度 0.83)

## 请求内容
请判断本创新点与上述论文是否构成撞车：
1. 若认为撞车 → 在下方填写 "COLLISION"，系统将重新生成创新点
2. 若认为不撞车 → 在下方填写 "NO_COLLISION"，系统将继续执行

## 您的判断：
[请在此填写]
```

填写后恢复：

```bash
python orchestrator/pipeline.py --task vlm_safety_001 --resume
```

---

#### 错误 6：Mock Provider 被禁用

**现象**：
```
[ERROR] 生产环境禁止使用 mock provider
[ERROR] 所有正常 provider 均不可用，无法继续执行
```

**原因**：Ollama 服务、远程 API 均不可用，回退链最终到达 mock，但生产环境禁用 mock。

**解决方案**：
1. 优先修复 Ollama 服务（参见错误 2）
2. 配置远程 API 作为备用（`providers.yaml` 中设置 API key）
3. 若仅为测试，可临时关闭 `forbid_mock`

```bash
# 检查所有 provider 可用性
python scripts/environment_check.py --check-llm

# 配置远程 API（设置环境变量）
set DEEPSEEK_API_KEY=your_key_here
set OPENAI_API_KEY=your_key_here

# 仅测试时临时关闭 mock 禁用（不推荐用于生产）
# 修改 llm_routing.yaml: production.forbid_mock: false
```

---

#### 错误 7：Checkpoint 恢复失败

**现象**：
```
[ERROR] 模块 09 checkpoint 恢复失败：checkpoint 文件损坏
[ERROR] 文件：output/experiments/checkpoints/ckpt_epoch_100.pt
```

**原因**：checkpoint 文件损坏或格式不兼容。

**解决方案**：
1. 删除损坏的 checkpoint
2. 从更早的 checkpoint 恢复
3. 或从头开始实验

```bash
# 查看可用 checkpoint
dir output\experiments\checkpoints\

# 删除损坏的 checkpoint
del output\experiments\checkpoints\ckpt_epoch_100.pt

# 从上一个 checkpoint 恢复（系统自动选择最新的有效 checkpoint）
python -m src.implementation --resume

# 或从头开始（删除所有 checkpoint）
del output\experiments\checkpoints\*.pt
python -m src.implementation
```

---

#### 错误 8：GPU 内存不足（OOM）

**现象**：
```
[ERROR] CUDA out of memory. Tried to allocate 12.00 GiB
```

**原因**：GPU 显存不足以运行当前实验配置。

**解决方案**：
1. 减小 batch size
2. 启用梯度累积（gradient accumulation）
3. 使用混合精度训练（mixed precision）
4. 使用更小的模型

```yaml
# 修改 experiment_plan.yaml
training:
  batch_size: 16          # 减小（如从 32 降到 16）
  gradient_accumulation_steps: 2   # 梯度累积补偿
  mixed_precision: "bf16"          # 混合精度
  gradient_checkpointing: true      # 梯度检查点（省显存）
```

---

### 10.2 错误处理总览

| 错误类型 | 严重程度 | 是否阻断 | 解决方式 |
|----------|----------|----------|----------|
| 输入文件缺失 | 高 | 是 | 补充输入文件后重试 |
| LLM 连接失败 | 高 | 是 | 修复 Ollama 服务后重试 |
| 后端未注册 | 高 | 是 | 配置 experiment_mode.yaml |
| 文献数量不足 | 中 | 是 | 补充文献或调整阈值 |
| 人工输入请求 | 中 | 是（暂停） | 填写 Human_Input_Request.md |
| Mock 被禁用 | 高 | 是 | 修复 LLM provider |
| Checkpoint 损坏 | 中 | 是 | 删除损坏文件，从有效断点恢复 |
| GPU OOM | 高 | 是 | 减小 batch size / 启用混合精度 |
| 单次 LLM 超时 | 低 | 否 | 自动重试或回退 |
| Skill 加载失败 | 低 | 否 | 跳过 Skill，继续运行 |
| MCP 连接失败 | 低 | 否 | 跳过 MCP，继续运行 |

---

## 11. 附录

### 11.1 快速开始检查清单

在开始使用 Research Agent v8.3.1 前，请逐项确认：

- [ ] Python 3.12 已安装
- [ ] Conda 环境 `research_agent_v3` 已创建并激活
- [ ] 所有依赖包已安装（`pip install -r requirements.txt`）
- [ ] Ollama 已安装并运行（`ollama list` 有输出）
- [ ] `deepseek-r1:8b` 模型已拉取
- [ ] `gemma4:26b` 模型已拉取
- [ ] `research_task.yaml` 已配置研究任务
- [ ] `module_config.yaml` 已配置模块参数
- [ ] `llm_routing.yaml` 已配置 LLM 路由
- [ ] `providers.yaml` 已配置 provider 连接
- [ ] `data/literature/pdf/` 目录已准备（如需手动补充文献）
- [ ] GPU 驱动正常（仅模块 09 需要）

### 11.2 模块输入输出速查表

| 模块 | 关键输入 | 关键输出 | LLM 模型 |
|------|----------|----------|----------|
| 01 | research_task.yaml | literature_database.json | gemma4:26b |
| 02 | literature_database.json | papers/, figure_analysis.json | gemma4:26b |
| 02.5 | papers/, figure_analysis.json | paper_assets/, asset_index.json | gemma4:26b |
| 03 | papers/ | paper_analysis_trace.json | deepseek-r1:8b |
| 04 | paper_analysis_trace.json | field_panorama.json, research_gaps.json | gemma4:26b |
| 05 | paper_analysis_trace.json, research_gaps.json | innovation_proposals.json, collision_check_report.json | deepseek-r1:8b |
| 06 | innovation_proposals.json | method_spec.json, theory_analysis.md, theory_confidence.json | deepseek-r1:8b |
| 07 | method_spec.json, theory_analysis.md | experiment_matrix.yaml, experiment_plan.yaml | gemma4:26b |
| 08 | experiment_matrix.yaml, experiment_plan.yaml | experiments/raw/, processed/, comparison/, statistics/ | — |
| 09 | experiment_matrix.yaml, experiment_plan.yaml, experiment_mode.yaml | experiments/real_results/, checkpoints/, logs/ | — |
| 10 | experiments/statistics/, theory_analysis.md | result_analysis.json, claim_evidence_map.json, decision_route.json | deepseek-r1:8b |
| 11 | result_analysis.json, experiments/comparison/ | figures/mermaid/, latex_tables/, prompts/, input_schema.md | gemma4:26b |
| 12 | result_analysis.json, theory_analysis.md, figures/ | paper.docx, paper.md, paper.tex | gemma4:26b |
| 13 | paper.docx, literature_database.json | references.bib, supplementary.md | gemma4:26b |
| 14 | paper.docx, references.bib, theory_analysis.md | reviews/, revisions/, final_review_decision.md | deepseek-r1:8b |
| 15 | 所有前序模块输出 | research_memory.md, decision_log.md, lessons_learned.md | gemma4:26b |

### 11.3 环境变量

| 变量名 | 用途 | 是否必需 |
|--------|------|----------|
| `DEEPSEEK_API_KEY` | 远程 DeepSeek API 密钥 | 否（仅回退时需要） |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 否（仅回退时需要） |
| `CUDA_VISIBLE_DEVICES` | 指定可见 GPU | 否（模块 09 可选） |
| `OLLAMA_HOST` | Ollama 服务地址（默认 localhost:11434） | 否 |

### 11.4 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 8.3.1 | 2026-08-18 | 文档更新，错误处理完善 |
| 8.3.0 | 2026-07-15 | 新增模块 02.5 论文资产智能 |
| 8.2.0 | 2026-06-01 | 双模型策略引入，回退链优化 |
| 8.1.0 | 2026-04-20 | 模块 14 审稿循环支持 ICLR |
| 8.0.0 | 2026-02-10 | 初始 15 模块架构发布 |

### 11.5 技术支持

如遇本手册未覆盖的问题，请按以下顺序排查：

1. **查看阶段报告**：`output/Stage_Report.md`（独立运行）或流水线日志（Pipeline 运行）
2. **查看 LLM 用量报告**：`output/llm_usage_report.json`
3. **查看人工输入请求**：`output/Human_Input_Request.md`
4. **运行环境检查**：`python scripts/environment_check.py`
5. **检查配置文件**：对照第 5 节确认 YAML 配置正确

---

> **免责声明**：Research Agent 生成的论文、分析和实验结果仅供研究参考。所有产出需经过人工审核后方可用于学术发表。系统不对生成内容的学术准确性承担最终责任。
