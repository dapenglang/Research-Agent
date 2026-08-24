# Research Agent v8.2.2 完整说明文档

**版本**: v8.2.2  
**更新日期**: 2026-08-16  
**Python环境**: research_agent_v3 (Python 3.12)  

---

## 目录

1. [系统概述](#1-系统概述)
2. [快速开始](#2-快速开始)
3. [系统架构](#3-系统架构)
4. [模块详解](#4-模块详解)
5. [Skill Runtime System](#5-skill-runtime-system)
6. [MCP 管理](#6-mcp-管理)
7. [LLM 配置](#7-llm-配置)
8. [任务配置](#8-任务配置)
9. [Human-in-the-loop](#9-human-in-the-loop)
10. [故障处理](#10-故障处理)
11. [v8.2.2 新增功能](#11-v822-新增功能)
12. [文档索引](#12-文档索引)

---

## 1. 系统概述

Research Agent v8.2 是一个由真实 LLM、Skills、MCP、Human-in-the-loop 驱动的自动化科研智能体。

### 核心能力

输入 `research_task.yaml`，自动完成 15 个科研流程：

1. 文献检索 → 2. 论文下载 → 3. LaTeX/PDF解析 → 4. 文献深度分析 → 5. 创新点发现 → 6. 方法设计 → 7. 仿真实验 → 8. GPU真实实验 → 9. 数据分析 → 10. 科研绘图 → 11. CCF-A论文写作 → 12. 引用检查 → 13. Reviewer审稿 → 14. 自动修改

### 环境支持

- **Windows 无GPU仿真**: 方案A（合成数据实验）
- **GPU服务器实验**: 方案C（真实模型训练）

---

## 2. 快速开始

### 环境准备

```bash
conda activate research_agent_v3
```

### 启动流程

```bash
# 1. 检查研究就绪状态
python scripts/check_research_ready.py

# 2. 启动 Pipeline
python -c "
from orchestrator.pipeline import PipelineOrchestrator
pipe = PipelineOrchestrator('configs/research_task.yaml')
result = pipe.start()
print(result)
"
```

### 启动新研究

修改 `configs/research_task.yaml` 中的 `topic`、`keywords`、`target_venue` 字段即可。

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                  │
│                   (orchestrator/pipeline.py)              │
├─────────┬─────────┬─────────┬──────────┬────────────────┤
│ Skills  │   MCP   │   LLM   │  Human   │    Modules     │
│ Runtime │ Manager │ Runtime │ Feedback │  01 ──── 14    │
└─────────┴─────────┴─────────┴──────────┴────────────────┘
```

### 目录结构

```
Research_Agent_v3/
├── orchestrator/pipeline.py        # 核心流水线编排器
├── modules/                        # 15个科研流程模块
│   ├── 01_literature_retrieval/    # 文献检索
│   ├── 02_source_acquisition/      # 论文下载
│   ├── 02_5_paper_asset_intelligence/ # 图片提取
│   ├── 03_literature_intelligence/ # 文献分析
│   ├── 04_research_landscape/      # 研究综述
│   ├── 05_innovation_reasoning/    # 创新点发现
│   ├── 06_theory_method/           # 方法设计
│   ├── 07_experiment_planning/     # 实验规划
│   ├── 08_synthetic_experiment_engine/ # 仿真实验
│   ├── 09_real_experiment_engine/  # GPU实验
│   ├── 10_result_analysis/         # 结果分析
│   ├── 11_figure_table/            # 科研绘图
│   ├── 12_paper_writing/           # 论文写作
│   ├── 13_reference_supplementary/ # 引用检查
│   └── 14_reviewer_loop/           # Reviewer审稿 (v8.2新增)
├── configs/                        # 配置文件
│   ├── llm.yaml                    # LLM配置 (v8.2新增)
│   ├── research_task.yaml          # 任务配置 (v8.2新增)
│   ├── providers.yaml              # LLM提供商
│   ├── llm_routing.yaml            # LLM路由
│   ├── experiment_mode.yaml        # 实验模式
│   └── ...
├── infrastructure/
│   ├── skills/                     # Skill Runtime (v8.2新增)
│   │   ├── skill_scanner.py        # 技能扫描器
│   │   ├── skill_runtime.py        # 技能运行时
│   │   ├── skill_integration.py    # 技能集成器
│   │   ├── skill_registry.yaml     # 技能注册表
│   │   └── installed_skills.json   # 已安装技能清单
│   ├── mcp/                        # MCP管理 (v8.2新增)
│   │   ├── mcp_manager.py          # MCP管理器
│   │   └── mcp_registry.yaml       # MCP服务注册
│   ├── llm/                        # LLM提供者
│   └── llm_runtime/                # LLM运行时
├── human_feedback/                 # 人工反馈 (v8.2新增)
│   ├── innovation_feedback.md      # 创新点反馈
│   ├── method_feedback.md          # 方法反馈
│   └── review_response.md          # 审稿回复
├── scripts/                        # 脚本工具
├── docs/                           # 文档
└── data/literature/                # 文献数据
    ├── pdf/
    └── latex/
```

---

## 4. 模块详解

### 模块 01: 文献检索
- **功能**: 跨 arXiv、Semantic Scholar、OpenReview 搜索论文
- **输入**: `research_task.yaml`
- **输出**: `literature_manifest.json`, `paper_metadata.jsonl`, `download_queue.json`
- **Skill**: light-literature-search, nature-academic-search, qinyan-paper-search

### 模块 02: 论文下载与解析
- **功能**: 下载PDF，解析为Markdown，提取公式/图表/表格/引文
- **输入**: `download_queue.json`
- **输出**: `papers/<paper_id>/` (metadata.json, original.pdf, normalized/paper.md)
- **Skill**: nature-downloader, pdf-converter-mineru, arxiv
- **合成数据**: 下载失败时生成合成论文

### 模块 02.5: 图片提取
- **功能**: 每篇论文自动保存前三张图片 (Figure1, Figure2, Figure3)
- **输入**: Module 02 的 papers 目录
- **输出**: `assets/figure_1.png`, `figure_2.png`, `figure_3.png`
- **不分析图片内容**

### 模块 03: 文献智能分析
- **功能**: 结构化知识提取，质量检查，汇总分析
- **输入**: `normalized/paper.md` + `metadata.json`
- **输出**: `paper_analysis.json`, `paper_analysis.md`
- **Skill**: nature-reader, nature-paper-card, light-file-reading
- **门控**: 需要 ≥50 篇论文

### 模块 04: 研究综述
- **功能**: 分类法、趋势分析、矛盾图谱、研究差距
- **输入**: `paper_analysis.json`
- **输出**: `research_landscape.md`, `taxonomy.json`, `gap_candidates.json`

### 模块 05: 创新点发现
- **功能**: 因果分析、创新生成、新颖性检查、假设生成
- **输入**: `gap_candidates.json`, `paper_analysis.json`
- **输出**: `innovation_candidates.json`, `innovation_report.md`, `final_research_direction.md`
- **Skill**: light-idea-generation, research-ideation, scientific-brainstorming
- **LLM**: 必须使用真实LLM
- **Human-in-the-loop**: 支持人工反馈 (`innovation_feedback.md`)

### 模块 06: 方法设计
- **功能**: 问题形式化、理论构建、方法设计、数学公式、算法设计
- **输入**: `final_research_direction.md`, `innovation_candidates.json`
- **输出**: `method_spec.json`, `method_design.md`, `mathematical_formulation.md`
- **Skill**: light-research-plan, experiment-design, light-system-design
- **LLM**: 必须使用真实LLM
- **Human-in-the-loop**: 支持人工反馈 (`method_feedback.md`)

### 模块 07: 实验规划
- **功能**: 实验计划、实验矩阵、声明-证据计划、图表计划
- **输入**: `method_spec.json`
- **输出**: `experiment_plan.md`, `experiment_matrix.yaml`, `claim_evidence_plan.json`

### 模块 08: 仿真实验
- **功能**: 方案A合成实验引擎
- **输入**: `method_spec.json`, `experiment_matrix.yaml`
- **输出**: `synthetic_results/metrics.json`
- **数据来源**: `data_origin: synthetic`

### 模块 09: GPU实验 (可选)
- **功能**: 方案C真实模型训练和测试
- **条件**: 仅在GPU模式下启用

### 模块 10: 结果分析
- **功能**: 声明评估、统计分析、决策路由
- **输入**: `claim_evidence_plan.json`, 实验指标
- **输出**: `analysis_report.json`, `decision.json`
- **决策**: PASS / RETURN_TO_EXPERIMENT / RETURN_TO_METHOD 等

### 模块 11: 科研绘图
- **功能**: 生成出版级图表（结构图、流程图、实验图表）
- **输入**: `method_spec.json`, `paper_figure_plan.yaml`, 实验指标
- **输出**: SVG图片, PDF, CSV/LaTeX表格
- **Skill**: academic-figure-workflow, paper-framework-figure-studio-pro, drawio, light-figure

### 模块 12: 论文写作
- **功能**: 生成完整研究论文 (Markdown + LaTeX + Word)
- **输入**: 所有上游模块输出
- **输出**: `paper/paper.md`, `paper/latex/paper.tex`, `paper/word/paper.docx`
- **Skill**: ml-paper-writing, nature-writing, light-paper-writing, academic-paper
- **LLM**: 必须使用真实LLM
- **目标**: CVPR/ICCV/NeurIPS/ICLR 级论文结构

### 模块 13: 引用检查
- **功能**: 参考文献管理，引文解析与验证
- **输入**: `paper/paper.md`, `paper_metadata.jsonl`
- **输出**: `references.bib`, `citation_validation_report.md`
- **Skill**: light-citation, citation-audit, nature-ref-verifier
- **禁止**: 不生成虚假引文

### 模块 14: Reviewer循环 (v8.2新增)
- **功能**: 模拟同行评审，生成审稿报告和修改建议
- **输入**: `paper/paper.md`, `references.bib`, 人工反馈
- **输出**: `review_report.md`, `revision_recommendations.md`, `review_decision.json`
- **Skill**: academic-paper-reviewer, paper-self-review, auto-review-loop-llm
- **LLM**: 可选（无LLM时使用模板）
- **Human-in-the-loop**: 支持人工反馈 (`review_response.md`)

---

## 5. Skill Runtime System

### 功能

自动扫描 TRAE skills 目录，发现已安装的技能，并将其集成到科研流水线中。

### 工作流程

1. 启动时扫描 `c:/Users/<user>/.trae-cn/skills/` 目录
2. 解析每个技能的 `SKILL.md` 文件
3. 生成 `installed_skills.json` 技能清单
4. 根据模块映射 (`skill_registry.yaml`) 为每个模块匹配技能
5. 在模块执行前注入技能指令到上下文

### 配置文件

**`infrastructure/skills/skill_registry.yaml`**: 定义模块与技能的映射关系

```yaml
module_skill_mapping:
  "01":
    - light-literature-search
    - nature-academic-search
  "05":
    - light-idea-generation
    - research-ideation
    - scientific-brainstorming
  # ...
```

### 手动刷新技能清单

```python
from infrastructure.skills import SkillScanner
scanner = SkillScanner()
result = scanner.scan()
print(f"Found {result['total_skills']} skills")
```

---

## 6. MCP 管理

### 支持的 MCP 服务器

| MCP | 类别 | 功能 | 状态 |
|-----|------|------|------|
| arxiv | 文献 | arXiv搜索/下载/LaTeX/引用图谱 | 启用 |
| paper-search | 文献 | 20+平台多源文献搜索 | 启用 |
| zotero | 引用 | Zotero文献管理 | 需配置API Key |
| obsidian | 知识库 | Obsidian笔记读写 | 需配置Vault路径 |
| drawio | 绘图 | draw.io图表生成 | 启用 |
| chart | 绘图 | 26+种统计图表 | 启用 |
| fetch | 网络 | 网页内容提取 | 启用 |

### 配置文件

**`infrastructure/mcp/mcp_registry.yaml`**:

```yaml
mcp_servers:
  arxiv:
    type: stdio
    command: uvx
    args: ["arxiv-mcp-server"]
    enabled: true
  zotero:
    type: stdio
    command: uvx
    args: ["zotero-mcp-server"]
    env:
      ZOTERO_API_KEY: ""
      ZOTERO_LIBRARY_ID: ""
    enabled: false
```

### 获取MCP状态

```python
from infrastructure.mcp import MCPManager
mgr = MCPManager()
print(mgr.summary())
```

---

## 7. LLM 配置

### 支持的提供商

| 提供商 | 环境变量 | 模型 |
|--------|---------|------|
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| Qwen | `DASHSCOPE_API_KEY` | qwen-plus |
| Local | 无 | Qwen2.5-7B-Instruct (vLLM/Ollama) |

### 配置文件

**`configs/llm.yaml`**:

```yaml
provider: deepseek

providers:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
    endpoint: https://api.deepseek.com/v1
    temperature: 0.3
```

### 任务路由

不同任务可使用不同模型和温度：

| 任务 | 推荐提供商 | 温度 |
|------|-----------|------|
| 文献分析 | DeepSeek | 0.2 |
| 创新推理 | DeepSeek | 0.5 |
| 方法设计 | DeepSeek | 0.3 |
| 论文写作 | DeepSeek | 0.7 |
| 引用检查 | DeepSeek | 0.1 |
| 审稿 | DeepSeek | 0.2 |

### 必须使用真实LLM的模块

模块 05（创新点）、06（方法设计）、10（结果分析）、12（论文写作）、14（审稿）必须使用真实LLM。未配置时使用模板模式（质量降低）。

---

## 8. 任务配置

### 配置文件

**`configs/research_task.yaml`**:

```yaml
topic: "Visual Large Model Safety"
keywords:
  - "VLM safety"
  - "adversarial attack"
  - "jailbreak defense"
target_venue: CVPR
experiment_mode: A  # A=仿真, C=GPU
literature:
  max_papers: 50
  min_papers: 50
human_in_loop:
  enabled: true
  pause_at: ["05", "06", "14"]
```

### 修改研究方向

只需修改 `topic` 和 `keywords` 字段即可启动新的研究。所有下游模块将自动适配。

---

## 9. Human-in-the-loop

### 工作流程

1. Pipeline 执行到 Module 05/06/14 时检查反馈文件
2. 如果 `human_feedback/` 目录下有对应反馈文件且内容非空，注入到模块上下文
3. 模块将人工反馈作为额外信息处理

### 反馈文件

| 文件 | 触发模块 | 用途 |
|------|---------|------|
| `innovation_feedback.md` | Module 05 | 修改/添加创新方向 |
| `method_feedback.md` | Module 06 | 调整方法/算法/公式 |
| `review_response.md` | Module 14 | 回复审稿意见 |

### 使用方法

1. Pipeline 运行到对应模块后暂停
2. 编辑 `human_feedback/` 下的 Markdown 文件
3. 恢复 Pipeline 执行

---

## 10. 故障处理

### 常见问题

**Q: 文献不足50篇怎么办？**

```bash
python scripts/check_literature.py
```
将论文放入 `data/literature/pdf/` 或 `data/literature/latex/`。

**Q: LLM未配置怎么办？**

```bash
python scripts/check_llm.py
```
设置环境变量 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`。未配置时使用模板模式。

**Q: 模块失败怎么办？**

- 仿真模式下模块失败不阻断流水线，自动生成stub输出继续
- GPU模式下模块失败终止流水线
- 使用 `resume()` 从检查点恢复
- 使用 `rerun(module_id)` 重新执行特定模块

**Q: 如何切换实验模式？**

修改 `configs/research_task.yaml`:
```yaml
experiment_mode: A  # 仿真（CPU）
experiment_mode: C  # GPU真实实验
```

### 诊断脚本

```bash
# 环境检查
python scripts/check_research_ready.py

# LLM检查
python scripts/check_llm.py

# 文献检查
python scripts/check_literature.py
```

### 日志

Pipeline 运行日志通过 Python logging 输出。设置日志级别：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 附录

### v8.2 新增功能清单

1. **Skill Runtime System**: 自动扫描575+技能，按模块映射集成
2. **MCP 管理**: 7个MCP服务器注册（arxiv, paper-search, zotero, obsidian, drawio, chart, fetch）
3. **Module 14 Reviewer循环**: 3位审稿人模拟+元审稿+修改建议
4. **Human-in-the-loop**: 3个反馈文件（创新点/方法/审稿）
5. **统一LLM配置**: `configs/llm.yaml` 支持4个提供商
6. **任务配置**: `configs/research_task.yaml` 一键启动新研究
7. **图片提取增强**: 每篇论文前三张图自动保存
8. **论文流程优化**: arXiv LaTeX优先，PDF回退

---

## 11. v8.2.2 新增功能

### 统一外部依赖管理
- `configs/external_dependency.yaml`: 统一管理所有外部依赖（Skill/MCP/LLM/模型）的配置文件位置
- `configs/dependency_policy.yaml`: 集中管理所有Fallback策略，模块禁止自行决定
- `configs/environment.yaml`: 环境规范

### Skill Registry 增强
- 位置: `infrastructure/skills/skill_registry.yaml`（保持原路径，不迁移）
- 新增字段: `capability`（技能能力分类）
- 新增字段: `version`, `source`, `install_path`, `required`, `fallback`

### MCP Registry 增强
- 位置: `infrastructure/mcp/mcp_registry.yaml`（保持原路径，不迁移）
- 新增三态状态: `installed`, `configured`, `tested`

### 文献注册表系统
- 位置: `data/literature/`
- 14个字段，包含 `research_task_id` 用于跨任务去重
- 5个文件: CSV/XLSX/JSON数据库/关键词统计/下载报告

### 三种运行模式
| 模式 | Skill | MCP | LLM | Fallback |
|------|-------|-----|-----|----------|
| Production | 必须 | 必须 | 真实 | 不允许 |
| Limited (默认) | 可选 | 可选 | 模板 | 允许 |
| Development | 可选 | 可选 | Mock | 全部允许 |

### First Time Setup Wizard
```bash
python scripts/check_portability.py
```
自动检测8项并生成安装顺序。

### 新增检测脚本
- `scripts/check_skills.py`: Skill可用性检测
- `scripts/check_mcp.py`: MCP三态状态检测
- `scripts/check_portability.py`: 综合迁移检测+安装顺序生成

### 版本历史

| 版本 | 关键更新 |
|------|---------|
| v8.2.2 | 统一依赖管理/Fallback集中管理/文献Registry/三态MCP/Setup Wizard |
| v8.2 | Skill/MCP/Human-in-the-loop/Module 14 |
| v8.1 | 文献质量门控/LLM诊断 |
| v8 | 真实LLM/三级记忆/配置驱动实验 |
| v7 | OpenAI/DeepSeek/Local LLM/路由 |
| v6 | 14模块验证/YAML方向切换 |
| v5 | Windows/GPU统一代码库 |

---

## 12. 文档索引

| 文档 | 说明 |
|------|------|
| [START_HERE.md](../START_HERE.md) | 唯一入口文档（含First Time Setup Wizard） |
| [Installation_Guide_CN.md](Installation_Guide_CN.md) | 环境安装与配置 |
| [Skill_Configuration_Guide_CN.md](Skill_Configuration_Guide_CN.md) | Skill注册、capability、fallback管理 |
| [MCP_Configuration_Guide_CN.md](MCP_Configuration_Guide_CN.md) | MCP三态状态与安装 |
| [Literature_Registry_Guide_CN.md](Literature_Registry_Guide_CN.md) | 文献注册表与去重机制 |
| [Module_Interface_Documentation_CN.md](Module_Interface_Documentation_CN.md) | 模块接口文档 |
| [Human_Intervention_Guide_CN.md](Human_Intervention_Guide_CN.md) | 人工介入指南 |
| [Troubleshooting_CN.md](Troubleshooting_CN.md) | 故障排查 |
| [LLM_Configuration_Guide_CN.md](LLM_Configuration_Guide_CN.md) | LLM配置指南 |
| [Literature_Preparation_Guide_CN.md](Literature_Preparation_Guide_CN.md) | 文献准备指南 |
