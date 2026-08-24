<p align="center">
  <img src="assets/logo.jpg" width="200" alt="Research Agent Logo" />
</p>

<h1 align="center">Research Agent v8.3.1</h1>

<p align="center">
  <strong>Automated Research Pipeline — From Literature to Paper Generation</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-8.3.1-blue" alt="Version" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/PyTorch-Latest-EE4C2C?logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/modules-15-orange" alt="Modules" />
  <img src="https://img.shields.io/badge/LLM-OpenAI%20%7C%20DeepSeek%20%7C%20Ollama-purple" alt="LLM" />
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#modules">Modules</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#documentation">Docs</a>
</p>

---

## Overview

Research Agent is a **modular, end-to-end automated research pipeline** that covers the full scientific research lifecycle — from literature retrieval and innovation discovery, through experiment design and result analysis, to paper writing and peer-review simulation.

Each of the 15 modules operates **independently** with its own configuration, I/O specifications, and environment checker, while seamlessly forming a closed-loop pipeline when orchestrated together.

## Features

- **15 Independent Modules** — Each module can run standalone with its own config, START_HERE.md, and environment_check.py
- **Pipeline Closed Loop** — Module 01 → ... → Module 14 → Module 15 (Research Memory) complete chain
- **Unified LLM Management** — Supports OpenAI / DeepSeek / Ollama with UsageTracker and automatic Fallback chain
- **Shared Memory** — Cross-module memory directory for datasets, experiments, methods, papers, and failed attempts
- **Stage Reports** — 100% coverage (16/16 modules) — every module generates a Stage_Report.md
- **Monte Carlo Simulation** — Synthetic experiment engine based on real paper statistics, not random generation
- **4-Layer Data Persistence** — Raw / Processed / Comparison / Statistics data layers
- **Multi-format Paper Output** — DOCX + Markdown + LaTeX simultaneously

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Research Agent v8.3.1                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Module 01 ──► Module 02 ──► Module 02.5 ──► Module 03         │
│  Literature    Paper          Paper Asset      Literature       │
│  Retrieval      Acquisition    Intelligence     Intelligence     │
│                                                                 │
│  Module 04 ──► Module 05 ──► Module 06 ──► Module 07           │
│  Research      Innovation    Theory &       Experiment         │
│  Landscape     Discovery      Method         Planning           │
│                                                                 │
│  Module 08 ──► Module 09 ──► Module 10 ──► Module 11           │
│  Synthetic     Real           Result         Figure &           │
│  Experiment    Experiment     Analysis       Table              │
│                                                                 │
│  Module 12 ──► Module 13 ──► Module 14 ──► Module 15           │
│  Paper         Reference      Reviewer       Research           │
│  Writing       & Suppl.       Loop           Memory             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure: LLM Runtime │ State │ Memory │ MCP │ Skills    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- Git
- At least one LLM provider (OpenAI API key, DeepSeek API key, or local Ollama)

### Installation

```bash
# Clone the repository
git clone https://github.com/dapenglang/Research-Agent.git
cd Research-Agent

# Install dependencies
pip install -r requirements.txt

# Configure LLM
cp configs/llm.yaml.example configs/llm.yaml
# Edit llm.yaml with your API keys

# Verify environment
python scripts/check_research_ready.py
```

### Run the Pipeline

```bash
# Full pipeline
python -m orchestrator.pipeline --task configs/research_task.yaml

# Or run individual modules
cd modules/01_literature_retrieval
python -m src --task ../../configs/research_task.yaml
```

## Modules

| Module | Name | Input | Output |
|--------|------|-------|--------|
| 01 | Literature Retrieval | research_task.yaml | literature_database.json |
| 02 | Paper Acquisition | literature_database.json | pdf/, latex/, markdown/, figure_analysis.json |
| 02.5 | Paper Asset Intelligence | paper assets | paper_asset_report.json |
| 03 | Literature Intelligence | paper_database | paper_analysis.json, paper_analysis_trace.json |
| 04 | Research Landscape | paper_analysis | research_landscape.md |
| 05 | Innovation Discovery | limitations + future_work | innovation_candidates.json |
| 06 | Theory & Method | innovation + gap | theory_analysis.md, theory_confidence.json |
| 07 | Experiment Planning | theory + method | experiment_plan.yaml |
| 08 | Synthetic Experiment | experiment_plan | raw/, processed/, comparison.csv, statistics.json |
| 09 | Real Experiment | experiment_plan | experiment_results/ |
| 10 | Result Analysis | experiment_results | result_analysis.md |
| 11 | Figure & Table | results + analysis | mermaid_src, latex_tables, figure_prompts.json |
| 12 | Paper Writing | all upstream | paper.docx, paper.md, paper.tex |
| 13 | Reference & Supplementary | paper | references.bib |
| 14 | Reviewer Loop | paper | reviewer_report.md |
| 15 | Research Memory | all stage_reports | research_memory.md, decision_log.md, lessons_learned.md |

## Configuration

### LLM Configuration (`configs/llm.yaml`)

```yaml
providers:
  openai:
    api_key: "sk-xxx"
    model: "gpt-4"
  
  deepseek:
    api_key: "sk-xxx"
    model: "deepseek-chat"
  
  ollama:
    base_url: "http://localhost:11434"
    model: "deepseek-r1:8b"

fallback_order: ["ollama_r1", "ollama", "deepseek", "openai"]
```

### Research Task (`configs/research_task.yaml`)

```yaml
task_id: "VLM_Safety_001"
research_topic: "Vision-Language Model Safety"
arxiv_keywords: ["VLM", "adversarial", "safety"]
paper_count: 50
experiment_mode: "synthetic"  # or "real"
```

## Documentation

| Document | Description |
|----------|-------------|
| [User Manual (CN)](Research_Agent_v8.3.1_User_Manual_CN.md) | Complete Chinese user manual |
| [Module Release Report](Research_Agent_v8.3.1_Module_Release_Report.md) | 15 module ZIP packages with SHA256 |
| [Final Report](Research_Agent_v8.3.1_Final_Report.md) | Modifications, tests, known issues |
| [Start Here (CN)](docs/START_HERE_CN.md) | Quick start guide in Chinese |
| [LLM Config Guide (CN)](docs/LLM_Configuration_Guide_CN.md) | LLM provider setup |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| ML Framework | PyTorch |
| LLM Providers | OpenAI, DeepSeek, Ollama |
| Paper Source | arXiv MCP Server |
| Document Output | python-docx, LaTeX |
| Data Format | JSON, YAML, CSV, XLSX |
| Diagrams | Mermaid |
| Version Control | Git |

## Project Structure

```
Research-Agent/
├── core/                    # Core framework (state, contracts, validation)
├── infrastructure/          # LLM runtime, MCP, skills, storage
├── modules/                 # 15 independent modules
│   ├── 01_literature_retrieval/
│   ├── 02_source_acquisition/
│   ├── ...
│   └── 15_research_memory/
├── orchestrator/            # Pipeline orchestrator
├── configs/                 # YAML configurations
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── memory/                  # Shared research memory
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-module`)
3. Commit changes following Conventional Commits
4. Push to branch (`git push origin feature/new-module`)
5. Open a Pull Request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Citation

If you use Research Agent in your research, please cite:

```bibtex
@misc{research_agent_v831,
  title={Research Agent: Automated Research Pipeline from Literature to Paper},
  author={Lang, Bruce},
  year={2026},
  version={8.3.1},
  url={https://github.com/dapenglang/Research-Agent}
}
```

## Acknowledgments

- arXiv for open access to research papers
- OpenAI, DeepSeek, and Ollama for LLM infrastructure
- The open-source community for foundational tools

---

## 💡 支持本项目

> **Research Agent 不是一个玩具项目。**

这是一个**工程标准极高、功能完整**的自动化科研系统，覆盖了从文献检索到论文撰写的完整科研生命周期：

- **全流程覆盖** — 15 个独立模块，从文献检索 → 创新发现 → 理论方法设计 → 实验规划 → 合成/真实实验 → 结果分析 → 图表生成 → 论文撰写 → 引用管理 → 审稿模拟 → 科研记忆，端到端闭环
- **实验设计能力** — 自动生成实验方案（`experiment_plan.yaml`），支持消融实验、对比实验、敏感性分析
- **数据仿真引擎** — 基于真实论文统计建模的 Monte Carlo 仿真，四层数据保存（原始 → 中间 → 对比 → 统计），无需 GPU 即可验证研究假设
- **LLM 统一管理** — 支持 OpenAI / DeepSeek / Ollama，自动 Fallback 降级，全链路 Usage 追踪
- **多格式论文输出** — 同时生成 DOCX / Markdown / LaTeX，含理论章节、引用、图表
- **科研记忆系统** — 跨模块共享决策日志、经验教训，支持增量迭代

**特别适合以下人群：**

- 刚开始学术研究的硕博新生 — 不用从零搭建科研工具链
- 需要快速验证研究想法可行性的研究者 — 仿真实验无需 GPU
- 想要系统化管理文献和创新思路的团队 — 15 模块闭环覆盖
- 投稿顶会/顶刊需要完整实验+论文流水线的研究者 — 从 idea 到 paper 一站完成

如果你觉得这个项目对你的科研有帮助，运行过程中遇到问题需要技术支持，**请给作者支持 5 毛钱** ☕

你的支持是我持续维护和优化这个项目的动力。

<p align="center">
  <img src="assets/wechat_support.jpg" width="300" alt="微信支持" />
</p>

<p align="center">
  <sub>微信扫码 · ¥0.50 · 感谢支持</sub>
</p>

---

<p align="center">
  <sub>Built with ❤ for automated scientific research</sub><br>
  <sub>Research Agent v8.3.1 Final Patch — August 2026</sub>
</p>
