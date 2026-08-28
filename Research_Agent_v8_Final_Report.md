# Research Agent v8 — Final Report

**版本**: v8 (Literature Gate & LLM Diagnostic Upgrade)
**日期**: 2026-08-16
**Python**: 3.12.13 (conda: research_agent_v3)
**平台**: Windows 11 Pro (无 GPU)
**基于**: Research_Agent_Release_v7.zip

---

## 1. 升级概述

Research Agent v8 在 v7 基础上新增两大核心功能：

1. **科研文献质量门控** — Pipeline 启动前检查论文数量，不足 50 篇禁止进入文献分析
2. **LLM 配置和诊断系统** — 全套 LLM 检测脚本、配置文档和诊断工具

| 升级领域 | v7 状态 | v8 改进 |
|---------|---------|---------|
| 文献质量门控 | 无 | data/literature/ + 自动检测 + Pipeline 阻断 |
| LLM 诊断 | 仅 get_status() | check_llm.py 完整诊断 + 错误报告 |
| 研究就绪检查 | 无 | check_research_ready.py 6 项检查 |
| 文档体系 | 英文为主 | 3 份中文指南 (快速开始/LLM配置/论文准备) |
| Pipeline 门控 | 无 | 文献门控 + LLM 门控 (skip_gates 参数) |
| 目录标准 | 无统一标准 | data/literature/{pdf,latex}/ |

**保持不变**: Module 架构、LLM Runtime、Memory、Pipeline 核心逻辑

---

## 2. v7 遗留问题

| # | 问题 | 严重程度 | v8 处理 |
|---|------|---------|---------|
| 1 | 无文献质量检查，Pipeline 可在 0 篇论文时运行 | 高 | 新增文献门控 |
| 2 | 无 LLM 诊断工具，用户难以排查 API 问题 | 高 | 新增 check_llm.py |
| 3 | 无就绪检查，用户不知道环境是否满足要求 | 中 | 新增 check_research_ready.py |
| 4 | 文档以英文为主，新用户上手困难 | 中 | 新增 3 份中文指南 |
| 5 | 无统一数据目录标准 | 低 | 新增 data/literature/ 标准目录 |
| 6 | LLM 强制要求未在 Pipeline 中检查 | 中 | 新增 LLM 门控 (Module 05/06/10/12) |

---

## 3. v8 新增功能

### 3.1 科研文献质量门控

**新增文件**:
- `data/literature/pdf/` — PDF 论文目录
- `data/literature/latex/` — LaTeX 源码目录
- `data/literature/README.md` — 目录说明
- `scripts/check_literature.py` — 论文检测脚本

**门控逻辑**:
- Pipeline 在进入 Module 03 (Literature Intelligence) 前检查论文数量
- 有效论文 = PDF 文件 (>1KB) + LaTeX 目录 (含 .tex 文件) - 重复项
- 最低要求: **50 篇**
- 不足时 Pipeline 返回 `status: "blocked"`，输出明确提示

**使用方式**:
```bash
python scripts/check_literature.py
python scripts/check_literature.py --min 50
python scripts/check_literature.py --data-dir /path/to/literature
```

**输出**: `Literature_Check_Report.md` (统计结果 + 文件列表 + 修复建议)

### 3.2 LLM 诊断系统

**新增文件**: `scripts/check_llm.py`

**检查内容**:
- Provider 配置 (providers.yaml 解析)
- API Key 环境变量检测
- Endpoint 连通性
- Model 可用性
- 实际 API 调用测试

**使用方式**:
```bash
python scripts/check_llm.py                      # 检查所有 Provider
python scripts/check_llm.py --provider deepseek   # 检查特定 Provider
```

**输出**:
- 成功: `LLM_Connection_Success.md`
- 失败: `LLM_Error_Report.md` (含详细错误和修复建议)

### 3.3 研究就绪检查

**新增文件**: `scripts/check_research_ready.py`

**检查项目** (6 项):
1. Python 环境 (版本 + 依赖包)
2. LLM 配置 (Provider + API Key)
3. API 连接测试 (实际调用)
4. 论文数量 (>= 50 篇)
5. 目录结构 (configs/modules/data/...)
6. 输出目录可写性

**使用方式**:
```bash
python scripts/check_research_ready.py
python scripts/check_research_ready.py --task tasks/task_001.yaml
python scripts/check_research_ready.py --skip-api-test
```

**输出**: `Research_Readiness_Report.md`

### 3.4 Pipeline 门控集成

**修改文件**: `orchestrator/pipeline.py`

**新增常量**:
```python
MIN_PAPERS = 50
LITERATURE_GATE_MODULE = "03"
LLM_REQUIRED_MODULES = {"05", "06", "10", "12"}
LLM_TASK_TYPE_MAP = {
    "05": "innovation_reasoning",
    "06": "method_design",
    "10": "experiment_analysis",
    "12": "paper_generation",
}
```

**新增方法**:
- `_check_literature_gate()` — 检查论文数量
- `_check_llm_gate(module_id)` — 检查 LLM 可用性

**Pipeline 流程**:
```
Environment Check (外部脚本)
    ↓
LLM Check (外部脚本)
    ↓
Literature Check (外部脚本)
    ↓
Module 01-02 (文献检索/获取)
    ↓
[文献质量门控] — 检查 >= 50 篇
    ↓ (通过)
Module 03 (Literature Intelligence)
    ↓
Module 04 (Research Gap)
    ↓
[LLM 门控] — Module 05 检查
    ↓
Module 05 (Innovation) ← 需要真实 LLM
    ↓
Module 06 (Method) ← 需要真实 LLM
    ↓
Module 07-09 (Experiment)
    ↓
[LLM 门控] — Module 10 检查
    ↓
Module 10 (Analysis) ← 需要真实 LLM
    ↓
Module 11 (Figure/Table)
    ↓
[LLM 门控] — Module 12 检查
    ↓
Module 12 (Paper Writing) ← 需要真实 LLM
    ↓
Module 13 (Reference)
```

**skip_gates 参数**:
```python
# 正常使用 (门控启用)
orchestrator = PipelineOrchestrator('tasks/task_001.yaml')

# 开发测试 (跳过门控)
orchestrator = PipelineOrchestrator('tasks/task_001.yaml', skip_gates=True)
```

### 3.5 中文文档体系

**新增文件**:
| 文档 | 内容 |
|------|------|
| `docs/START_HERE_CN.md` | 快速开始指南 (环境/LLM/论文/任务/排查) |
| `docs/LLM_Configuration_Guide_CN.md` | LLM 配置指南 (OpenAI/DeepSeek/Local) |
| `docs/Literature_Preparation_Guide_CN.md` | 论文准备指南 (下载/命名/检查) |

---

## 4. 测试结果

### 4.1 测试环境

- **Python**: 3.12.13 (Anaconda)
- **conda 环境**: research_agent_v3
- **GPU**: 不可用 (Windows 11 Pro)
- **LLM**: 无 API 密钥 (测试模式)
- **论文**: 0 篇 (初始状态)

### 4.2 测试结果

| 测试 | 描述 | 结果 | 详情 |
|------|------|------|------|
| Test 1 | 无 API Key — 系统正确提示 | **PASS** | OpenAI/DeepSeek 均检测为 unavailable |
| Test 2 | API Key 存在 — LLM 检测 Key | **PASS** | DeepSeekProvider.is_available() 返回 True |
| Test 3 | 论文 < 50 篇 — Pipeline 停止 | **PASS** | 返回 status=blocked, gate=literature_quality |
| Test 4 | 论文 >= 50 篇 — 进入研究流程 | **PASS** | 文献门控通过，Pipeline 未被阻止 |
| Test 5 | 检测脚本执行 | **PASS** | 3 个脚本均正常运行 |

### 4.3 检测脚本验证

| 脚本 | 退出码 | 行为 |
|------|--------|------|
| check_literature.py | 1 (FAIL) | 正确报告 0 篇论文，生成 Literature_Check_Report.md |
| check_llm.py | 1 (FAIL) | 正确报告 API Key 未设置，生成 LLM_Error_Report.md |
| check_research_ready.py | 1 (NOT READY) | 正确报告论文不足，生成 Research_Readiness_Report.md |

### 4.4 文献门控验证

**Test 3 (论文不足)**:
```
[ERROR] Literature gate blocked pipeline: 
Literature gate FAILED: 0 papers found, need at least 50. 
Please add papers to data/literature/pdf/ or data/literature/latex/. 
Missing: 50 papers.
```
Pipeline 返回: `{"status": "blocked", "gate": "literature_quality", "paper_count": 0}`

**Test 4 (论文充足)**:
- 创建 50 个测试 PDF 文件
- Pipeline 文献门控通过
- Pipeline 未被阻止，继续执行

---

## 5. LLM 配置说明

### 5.1 支持的 Provider

| Provider | 类型 | 环境变量 | 状态 |
|----------|------|---------|------|
| OpenAI | 真实 API | OPENAI_API_KEY | 需配置 |
| DeepSeek | 真实 API | DEEPSEEK_API_KEY | 需配置 |
| Local | 本地 HTTP | LOCAL_LLM_ENDPOINT | 需启动服务 |
| Mock | 模板 | 无 | 仅限开发测试 |

### 5.2 LLM 强制要求

以下模块**必须**使用真实 LLM (非 Mock):

| 模块 | 任务类型 | 路由 Provider |
|------|---------|--------------|
| Module 05 (Innovation) | innovation_reasoning | openai (gpt-4) |
| Module 06 (Method) | method_design | openai (gpt-4) |
| Module 10 (Analysis) | experiment_analysis | deepseek (deepseek-chat) |
| Module 12 (Paper Writing) | paper_generation | openai (gpt-4) |

未配置 API Key 时，Pipeline 会输出警告但继续运行 (模板模式)。

### 5.3 配置方法

```bash
# DeepSeek (推荐)
set DEEPSEEK_API_KEY=sk-你的密钥

# OpenAI
set OPENAI_API_KEY=sk-你的密钥

# 本地模型
set LOCAL_LLM_ENDPOINT=http://localhost:8000/v1

# 验证
python scripts/check_llm.py
```

详细配置请参考 `docs/LLM_Configuration_Guide_CN.md`。

---

## 6. 文献检查说明

### 6.1 目录结构

```
data/literature/
├── pdf/          # PDF 文件 (>1KB)
│   ├── 2401.00001.pdf
│   └── ...
├── latex/        # LaTeX 目录 (含 .tex 文件)
│   ├── 2401.00003/
│   │   └── main.tex
│   └── ...
└── README.md
```

### 6.2 检查规则

- PDF: 后缀 `.pdf`，文件大小 > 1KB
- LaTeX: 子目录包含至少一个 `.tex` 文件
- 去重: PDF 和 LaTeX 同名按一篇计算
- 最低要求: 50 篇

### 6.3 检查方法

```bash
python scripts/check_literature.py
```

详细说明请参考 `docs/Literature_Preparation_Guide_CN.md`。

---

## 7. 使用方法

### 7.1 完整启动流程

```bash
# 1. 激活环境
conda activate research_agent_v3

# 2. 配置 LLM (至少一个)
set DEEPSEEK_API_KEY=sk-...

# 3. 准备论文 (>= 50 篇)
# 将 PDF 放入 data/literature/pdf/

# 4. 检查就绪状态
python scripts/check_research_ready.py

# 5. 启动 Pipeline
python -c "
from Research_Agent_v3.orchestrator.pipeline import PipelineOrchestrator
orch = PipelineOrchestrator('tasks/task_001.yaml')
result = orch.start()
print(f'Status: {result[\"status\"]}')
"

# 6. 查看输出
# 论文: output/paper/<task_id>/paper.md
# 图表: output/figures_tables/<task_id>/
# 分析: output/analysis/<task_id>/
```

### 7.2 开发测试模式

```python
# 跳过门控 (仅限开发测试)
orchestrator = PipelineOrchestrator(
    'tasks/task_001.yaml',
    skip_gates=True
)
```

### 7.3 诊断工具

```bash
# LLM 诊断
python scripts/check_llm.py

# 文献检查
python scripts/check_literature.py

# 完整就绪检查
python scripts/check_research_ready.py
```

---

## 8. 目录结构

```
Research_Agent_v3/
├── data/                   # v8 新增
│   └── literature/
│       ├── pdf/            # PDF 论文
│       ├── latex/          # LaTeX 源码
│       └── README.md
├── scripts/                # v8 扩展
│   ├── check_literature.py     # v8 新增
│   ├── check_llm.py            # v8 新增
│   ├── check_research_ready.py # v8 新增
│   ├── setup_environment.sh
│   └── setup_environment_windows.ps1
├── docs/                   # v8 扩展
│   ├── START_HERE_CN.md                # v8 新增
│   ├── LLM_Configuration_Guide_CN.md   # v8 新增
│   ├── Literature_Preparation_Guide_CN.md # v8 新增
│   ├── 01_Deployment/
│   ├── 02_Usage/
│   ├── 03_Configuration/
│   ├── 04_Troubleshooting/
│   └── ...
├── configs/                # v7 保持
├── modules/                # v7 保持 (14 个模块)
├── orchestrator/           # v8 修改 (添加门控)
├── infrastructure/         # v7 保持
├── memory/                 # v7 保持
├── tasks/                  # v7 保持
├── tools/                  # v7 保持
└── tests/                  # v7 保持
```

---

## 9. 已知限制

1. **文献门控为硬性阻断**: 论文不足 50 篇时 Pipeline 完全停止，不会继续执行 Module 03 及后续模块。开发测试可使用 `skip_gates=True` 跳过。

2. **LLM 门控为软性警告**: 未配置 API Key 时 Pipeline 输出警告但继续运行 (模板模式)。这是为了允许开发测试，生产环境应配置真实 API Key。

3. **论文去重基于文件名**: 如果 PDF 文件名为 `2401.00001.pdf`，LaTeX 目录名为 `2401.00001/`，系统会识别为重复。但不同命名 (如 `paper1.pdf` 和 `2401.00001/`) 不会去重。

4. **check_llm.py 的 local provider 测试**: 当本地 LLM 服务未运行时，连接测试会超时。脚本设置了 30 秒超时，超时后报告失败。

5. **Mock Provider 限制保持不变**: Mock 仍被禁止用于 literature_analysis、innovation_generation、paper_generation、experiment_analysis 任务。

---

## 10. 发布包信息

**文件**: `Research_Agent_Release_v8.zip`
**包含**: 完整项目代码 + 配置 + 文档 + 测试任务 + 检测脚本
**依赖**: Python 3.12+, conda 环境 research_agent_v3
**新增文件数**: 7 个 (3 个脚本 + 3 份文档 + 1 个 README)

---

## 结论

Research Agent v8 成功完成了文献质量门控和 LLM 诊断系统的升级。所有 5 项测试通过：

- 无 API Key 时系统正确提示
- API Key 存在时系统正确检测
- 论文不足 50 篇时 Pipeline 正确阻止
- 论文充足 50 篇时 Pipeline 正确放行
- 三个检测脚本均正常运行

v8 新增的文献门控确保了研究质量底线，LLM 诊断系统帮助用户快速排查配置问题，三份中文文档降低了新用户上手门槛。系统保持了 v7 的全部功能，未删除任何已有特性。

**Research Agent v8 Ready**
