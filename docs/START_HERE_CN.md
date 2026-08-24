# Research Agent v8 — 快速开始指南

> 本文档面向初次使用 Research Agent 的用户，从零开始完成环境配置到运行第一个研究任务。

---

## 目录

1. [环境准备](#1-环境准备)
2. [配置 LLM](#2-配置-llm)
3. [准备论文](#3-准备论文)
4. [启动任务](#4-启动任务)
5. [排查错误](#5-排查错误)

---

## 1. 环境准备

### 1.1 安装 Python 3.12

```bash
# 推荐使用 Anaconda
conda create -n research_agent_v3 python=3.12
conda activate research_agent_v3
```

### 1.2 安装依赖

```bash
pip install pyyaml numpy matplotlib openai
```

### 1.3 验证环境

```bash
python scripts/check_research_ready.py --skip-api-test
```

如果输出 `[NOT READY]`，请根据报告修复问题。

---

## 2. 配置 LLM

Research Agent 需要真实 LLM 来生成研究内容。支持三种提供商：

### 方案 A: DeepSeek（推荐，性价比最高）

```bash
# 1. 获取 API Key
# 访问 https://platform.deepseek.com/api_keys 注册并创建 Key

# 2. 设置环境变量
set DEEPSEEK_API_KEY=sk-你的密钥

# 3. 测试连接
python scripts/check_llm.py
```

### 方案 B: OpenAI

```bash
# 1. 获取 API Key
# 访问 https://platform.openai.com/api-keys

# 2. 设置环境变量
set OPENAI_API_KEY=sk-你的密钥

# 3. 测试连接
python scripts/check_llm.py
```

### 方案 C: 本地模型（免费，需要 GPU）

```bash
# 1. 安装 vLLM 或 Ollama
# 2. 启动模型服务
# 3. 设置环境变量
set LOCAL_LLM_ENDPOINT=http://localhost:8000/v1

# 4. 测试连接
python scripts/check_llm.py
```

> 详细配置请参考 [LLM_Configuration_Guide_CN.md](LLM_Configuration_Guide_CN.md)

成功后你会看到：
```
LLM Connection Success
  [OK] deepseek (deepseek-chat)
```

---

## 3. 准备论文

Pipeline 要求 **至少 50 篇论文** 才能进入文献分析阶段。

### 3.1 目录结构

```
data/literature/
├── pdf/          # 放 PDF 文件
│   ├── 2401.00001.pdf
│   ├── 2401.00002.pdf
│   └── ...
└── latex/        # 放 LaTeX 源码
    ├── 2401.00003/
    │   └── main.tex
    └── ...
```

### 3.2 下载论文

**方法 1: 手动下载 PDF**
1. 从 arXiv (https://arxiv.org) 搜索你的研究关键词
2. 下载 PDF 文件
3. 放入 `data/literature/pdf/`

**方法 2: 下载 LaTeX 源码**
1. 在 arXiv 论文页面点击 "Download source"
2. 解压到 `data/literature/latex/{arxiv_id}/`
3. 确保目录中有 `.tex` 文件

**方法 3: 使用 Module 01 自动下载**（需要配置额外 API）

### 3.3 检查论文数量

```bash
python scripts/check_literature.py
```

如果论文不足 50 篇，会输出：
```
[FAIL] Literature check failed: 12 papers (need 50)
Missing: 38 papers
```

> 详细说明请参考 [Literature_Preparation_Guide_CN.md](Literature_Preparation_Guide_CN.md)

---

## 4. 启动任务

### 4.1 完整就绪检查

```bash
python scripts/check_research_ready.py
```

所有检查通过后输出：
```
[READY] All checks passed — pipeline is ready to start
```

### 4.2 运行 Pipeline

```bash
python -c "
from Research_Agent_v3.orchestrator.pipeline import PipelineOrchestrator
orchestrator = PipelineOrchestrator('tasks/task_001.yaml')
result = orchestrator.start()
print(f'Status: {result[\"status\"]}')
"
```

### 4.3 查看输出

```
output/
├── paper/              # 生成的论文 (Markdown/LaTeX/Word)
├── figures_tables/     # 图表 (SVG/PDF/CSV)
├── analysis/           # 分析报告
└── references/         # 参考文献
```

---

## 5. 排查错误

### 5.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `Literature gate FAILED` | 论文不足 50 篇 | 往 `data/literature/pdf/` 添加更多 PDF |
| `LLM gate WARNING` | 未设置 API Key | 设置 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY` |
| `ModuleNotFoundError` | Python 包未安装 | `pip install pyyaml openai numpy` |
| `State transition error` | 状态文件冲突 | 删除 `state/` 目录后重试 |

### 5.2 诊断脚本

```bash
# LLM 诊断
python scripts/check_llm.py

# 文献检查
python scripts/check_literature.py

# 完整就绪检查
python scripts/check_research_ready.py
```

### 5.3 跳过门控（仅限开发测试）

如果需要在不满足门控条件时运行 Pipeline（例如开发测试）：

```python
orchestrator = PipelineOrchestrator(
    'tasks/task_001.yaml',
    skip_gates=True  # 跳过文献门控和 LLM 门控
)
```

> **注意**: 跳过门控仅用于开发测试。生产环境必须满足所有门控条件。

---

## 下一步

- 配置 LLM: [LLM_Configuration_Guide_CN.md](LLM_Configuration_Guide_CN.md)
- 准备论文: [Literature_Preparation_Guide_CN.md](Literature_Preparation_Guide_CN.md)
- 创建新任务: [02_Usage/New_Research_Task_Guide.md](02_Usage/New_Research_Task_Guide.md)
- 故障排查: [04_Troubleshooting/Troubleshooting_Guide.md](04_Troubleshooting/Troubleshooting_Guide.md)
