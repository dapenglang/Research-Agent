# Research Agent v8.2.2 — 安装指南

> 本文档面向初次部署 Research Agent 的用户，从零开始完成环境搭建到首次运行验证。

---

## 目录

1. [环境准备](#1-环境准备)
2. [安装 Conda 环境](#2-安装-conda-环境)
3. [安装 pip 依赖](#3-安装-pip-依赖)
4. [目录结构概览](#4-目录结构概览)
5. [配置文件概览](#5-配置文件概览)
6. [首次安装向导](#6-首次安装向导)

---

## 1. 环境准备

### 1.1 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.12 | 3.12 |
| Conda | Miniconda / Anaconda | Anaconda |
| GPU | 不强制 | NVIDIA RTX A500 4GB+ |
| CUDA | 12.1（如有 GPU） | 12.1 |
| 磁盘空间 | 10 GB | 20 GB+ |

### 1.2 安装 Anaconda

如已安装 Anaconda 或 Miniconda，跳过此步。

1. 访问 https://www.anaconda.com/download 下载 Windows 安装包
2. 安装时勾选 "Add Anaconda to my PATH"（可选）
3. 安装完成后打开 Anaconda Prompt 验证：

```bash
conda --version
```

---

## 2. 安装 Conda 环境

### 2.1 创建环境

项目使用固定的 Conda 环境名 `research_agent_v3`，Python 版本为 3.12。

```bash
conda create -n research_agent_v3 python=3.12
conda activate research_agent_v3
```

也可直接使用项目根目录的 `environment.yml` 一键创建（包含所有 Conda 依赖）：

```bash
conda env create -f environment.yml
conda activate research_agent_v3
```

`environment.yml` 内容概览：
- Python 3.12
- PyTorch >= 2.1.0（含 CUDA 12.1 支持）
- numpy / scipy / pandas / matplotlib / pyyaml
- pip 子依赖：transformers, openai, python-docx, openpyxl 等

### 2.2 验证环境

```bash
python --version
# 输出应为 Python 3.12.x

conda info --envs
# 确认 research_agent_v3 已激活
```

---

## 3. 安装 pip 依赖

### 3.1 使用 requirements.txt

在激活 `research_agent_v3` 环境后执行：

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含以下核心依赖：

| 类别 | 包 | 说明 |
|------|----|------|
| 核心 | pyyaml, numpy, scipy, pandas, matplotlib, requests, tqdm | 数据处理与基础工具 |
| LLM/NLP | openai, transformers, tokenizers, sentencepiece | 语言模型调用 |
| 文档处理 | python-docx, openpyxl, markdownify, beautifulsoup4, lxml | Word/Excel/HTML 读写 |
| ML/GPU | accelerate, safetensors, scikit-learn, Pillow | 模型推理辅助 |
| 测试 | pytest | 单元测试 |

### 3.2 单独安装 PyTorch（如需 GPU 支持）

如 `environment.yml` 未覆盖你的 CUDA 版本，可手动安装：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3.3 验证依赖

```bash
python -c "import yaml, numpy, pandas, openai; print('核心依赖检查通过')"
```

---

## 4. 目录结构概览

项目根目录结构如下（仅列出关键目录）：

```
Research_Agent_v3/
├── configs/                    # 配置文件目录
├── core/                       # 核心框架代码
├── modules/                    # 14 个研究模块（Module 01-14）
│   ├── 01_literature_retrieval/
│   ├── 02_source_acquisition/
│   ├── ...
│   └── 14_reviewer_loop/
├── infrastructure/            # 基础设施层
│   ├── skills/                 # Skill 注册表与集成
│   ├── mcp/                    # MCP 服务器注册表
│   ├── llm/                    # LLM Provider 与 Prompt 管理
│   ├── llm_runtime/            # LLM 运行时
│   ├── memory/                 # 记忆存储与检索
│   ├── models/                 # 模型 Hub 与验证
│   └── storage/                # 存储与路径解析
├── data/
│   └── literature/             # 文献注册表与下载文件
├── scripts/                    # 检查与安装脚本
├── adapters/                   # 适配器层
├── orchestrator/               # 编排器
├── cli/                        # 命令行接口
├── templates/                  # 模板文件
├── tests/                      # 测试套件
├── environment.yml             # Conda 环境定义
├── requirements.txt            # pip 依赖清单
└── VERSION.md                  # 版本信息
```

### 模块编号说明

| 模块 | 编号 | 功能 |
|------|------|------|
| Literature Retrieval | 01 | 文献检索 |
| Source Acquisition | 02 | 论文下载 |
| Paper Asset Intelligence | 02_5 | 论文资产提取 |
| Literature Intelligence | 03 | 文献深度分析 |
| Research Landscape | 04 | 研究全景 |
| Innovation Reasoning | 05 | 创新推理 |
| Theory Method | 06 | 理论方法 |
| Experiment Planning | 07 | 实验规划 |
| Synthetic Experiment Engine | 08 | 合成实验引擎 |
| Real Experiment Engine | 09 | 真实实验引擎 |
| Result Analysis | 10 | 结果分析 |
| Figure Table | 11 | 图表生成 |
| Paper Writing | 12 | 论文写作 |
| Reference Supplementary | 13 | 引用补充 |
| Reviewer Loop | 14 | 审稿循环 |

---

## 5. 配置文件概览

所有配置文件位于 `configs/` 目录：

| 文件 | 用途 | 何时修改 |
|------|------|----------|
| `machine.yaml` | 描述部署机器的硬件与环境 | 换机器或硬件变更时 |
| `storage.yaml` | 存储路径配置（DATA_ROOT 等） | 需要更改数据存储位置时 |
| `providers.yaml` | LLM 提供商配置 | 切换 LLM 提供商时 |
| `llm.yaml` | LLM 调用参数 | 调整模型/温度/超时等 |
| `llm_routing.yaml` | LLM 路由策略 | 按任务类型路由不同模型 |
| `model_registry.yaml` | 本地模型路径注册 | 部署本地模型时 |
| `dependency_policy.yaml` | 依赖降级策略（Skill/MCP/LLM） | 调整 fallback 行为时 |
| `external_dependency.yaml` | 外部依赖声明 | 新增外部依赖时 |
| `experiment_mode.yaml` | 实验模式配置 | 切换合成/真实实验模式 |
| `research_task.yaml` | 研究任务配置 | 每次新研究任务 |
| `research_task_template.yaml` | 研究任务模板 | 参考模板 |
| `environment.yaml` | Conda 环境定义 | 环境初始化时 |

### 关键配置示例

**machine.yaml**（硬件描述）：
```yaml
machine:
  os: "Windows 11"
  python_version: "3.12"
  conda_env: "research_agent_v3"
  gpu:
    available: true
    device: "NVIDIA RTX A500 Laptop GPU"
    vram_gb: 4
    cuda_version: "12.1"
```

**llm.yaml**（LLM 配置）：
```yaml
provider: deepseek
model: deepseek-chat
api_key_env: DEEPSEEK_API_KEY
temperature: 0.7
max_tokens: 4096
timeout: 30
```

---

## 6. 首次安装向导

### 6.1 运行可移植性检查

完成环境搭建和依赖安装后，运行安装向导进行一次性检查：

```bash
python scripts/check_portability.py
```

该脚本会自动检测以下 8 项：

| 检查项 | 检测内容 | 状态 |
|--------|----------|------|
| Python 环境 | Python 版本 >= 3.10 | PASS/FAIL |
| Conda 环境 | 当前 Conda 环境为 `research_agent_v3` | PASS/WARN |
| Skill 安装 | Skill 注册表与已安装 Skill 一致性 | PASS/WARN |
| MCP 安装 | MCP 服务器安装状态 | PASS/WARN |
| LLM 配置 | OpenAI/DeepSeek API Key 是否设置 | PASS/WARN |
| 模型路径 | 本地模型文件是否存在 | PASS/INFO |
| GPU | nvidia-smi 是否可用 | PASS/INFO |
| 存储空间 | 磁盘可用空间 >= 10 GB | PASS/WARN |

### 6.2 检查报告

脚本运行后会在项目根目录生成 `Migration_Check_Report.md`，包含：

- **检测结果表格**：每项检查的详细状态
- **建议安装顺序**：如有缺失项，按优先级给出修复步骤
- **总体状态**：READY 或 NEEDS ATTENTION

### 6.3 典型输出示例

```
============================================================
Migration Check Report
============================================================
  Python 环境          PASS   {"version": "3.12.0", "required": ">=3.10"}
  Conda 环境           PASS   {"current_env": "research_agent_v3", ...}
  Skill 安装           WARN   {"installed": 5, "required_missing": 2}
  MCP 安装             WARN   {"enabled": 5, "installed": 3, ...}
  LLM 配置             PASS   {"openai": "not set", "deepseek": "configured"}
  模型路径             INFO   {"total": 3, "found": 0, "missing": [...]}
  GPU                  PASS   {"available": true, ...}
  存储空间             PASS   {"free_gb": 45.2, "required_gb": 10}

Report: D:\Research Agent\Research_Agent_v3\Migration_Check_Report.md
Overall: NEEDS ATTENTION
```

### 6.4 修复缺失项

根据报告中的"建议安装顺序"逐项修复：

1. **Conda 环境**：`conda activate research_agent_v3`
2. **LLM 配置**：设置 API Key 环境变量（推荐 DeepSeek）
3. **Skill 安装**：运行 `python scripts/check_skills.py`
4. **MCP 安装**：运行 `python scripts/check_mcp.py`

修复完成后重新运行：

```bash
python scripts/check_portability.py
```

直到输出 `Overall: READY` 即表示安装完成，可以启动 Pipeline。

---

## 快速验证清单

- [ ] Anaconda 已安装
- [ ] Conda 环境 `research_agent_v3` 已创建并激活
- [ ] Python 版本为 3.12
- [ ] `pip install -r requirements.txt` 已执行
- [ ] `configs/machine.yaml` 已配置为当前机器
- [ ] LLM API Key 已设置环境变量
- [ ] `python scripts/check_portability.py` 输出 READY

如有问题，请参阅 `docs/04_Troubleshooting/` 中的故障排查文档。
