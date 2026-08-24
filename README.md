# Research Agent v8.3.1

> 自动化科研流水线系统 — 从文献检索到论文生成的全流程 AI Research Agent

## 项目概述

Research Agent 是一个模块化的自动科研流水线系统，覆盖从文献检索、创新发现、实验设计、结果分析到论文撰写的完整科研生命周期。

## 架构

- **15 个独立模块** — 每个模块可独立运行，有独立的配置、输入输出说明和环境检测
- **Pipeline 闭环** — Module 01 → 14 → 15 (科研记忆) 完整链路
- **LLM 统一管理** — 支持 OpenAI / DeepSeek / Ollama，含 UsageTracker 和 Fallback 链
- **Memory 共享** — 跨模块共享记忆目录

## 模块清单

| Day | Module | 功能 |
|-----|--------|------|
| 1 | - | 项目骨架与基础设施 |
| 2 | - | LLM 运行时与基础设施层 |
| 3 | 01 + 02 | 文献检索 + 论文获取与解析 |
| 4 | 02.5 + 03 | 论文资产智能 + 文献智能分析 |
| 5 | 04 + 05 | 研究领域全景 + 创新发现 |
| 6 | 06 | 理论方法设计 |
| 7 | 07 + 08 | 实验规划 + 合成实验引擎 |
| 8 | 09 + 10 | 真实实验引擎 + 结果分析 |
| 9 | 11 + 12 | 图表生成 + 论文撰写 |
| 10 | 13 + 14 | 引用与补充 + 审稿循环 |
| 11 | 15 | 科研记忆 + Orchestrator |
| 12 | - | 数据模型与状态管理 |
| 13 | - | 测试、模板与工具 |
| 14 | - | 记忆目录与数据元信息 |
| 15 | - | 最终整理与版本标签 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM
cp configs/llm.yaml.example configs/llm.yaml
# 编辑 llm.yaml 填入 API Key

# 运行 Pipeline
python -m orchestrator.pipeline --task configs/research_task.yaml
```

## 技术栈

- Python 3.12
- PyTorch
- OpenAI / DeepSeek / Ollama LLM
- arXiv MCP Server

## 文档

- [用户手册](Research_Agent_v8.3.1_User_Manual_CN.md)
- [模块发布报告](Research_Agent_v8.3.1_Module_Release_Report.md)
- [最终报告](Research_Agent_v8.3.1_Final_Report.md)

## License

MIT

---

*Research Agent v8.3.1 Final Patch — 2026-08-18*
