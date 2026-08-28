# Research Task Config Fix Report

**Date:** 2026-08-16
**Status:** PASS
**Project:** Research Agent v3

---

## 1. Root Cause

START_HERE.md 的 B4 要求用户在 `research_task.yaml` 中填写 research question、keywords、domain。但是：

1. **没有正式模板** — 用户被告知从 `tests/e2e_test_data/research_task.yaml` 复制作为新科研任务模板，但该文件仅包含 `task_id`、`title`、`analysis`、`experiment`、`llm`、`output`、`paper` 字段，没有任何研究内容字段。

2. **代码不支持嵌套字段** — Module 01 的 `execute()` 方法使用 `task_config.get("keywords", [])` 等扁平字段读取方式，无法读取 `research.keywords`、`research.research_question` 等嵌套字段。

3. **Schema 过时** — `modules/01_literature_retrieval/schema.py` 中的 `INPUT_FILE_SCHEMAS` 仅定义了扁平的 `research_question`、`keywords`、`domain` 字段，不反映嵌套结构。

4. **ConfigLoader 验证不完整** — `infrastructure/validation/config_loader.py` 的 `validate()` 仅检查 `research_task` 默认 section 中的 `task_id` 和 `domain`，不验证实际 YAML 文件中的嵌套研究内容字段。

---

## 2. Modified Files

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 1 | `configs/research_task_template.yaml` | **NEW** | 正式科研任务模板，包含嵌套 `research`、`literature`、`experiment` 等 section |
| 2 | `infrastructure/research_context_extractor.py` | **NEW** | 研究 context 提取器和验证器，支持嵌套+扁平格式 |
| 3 | `modules/01_literature_retrieval/implementation.py` | **MODIFIED** | `execute()` 使用 `extract_research_context()` 读取嵌套字段；manifest 新增 `research_context` 传递给下游模块 |
| 4 | `modules/01_literature_retrieval/schema.py` | **MODIFIED** | `INPUT_FILE_SCHEMAS` 更新为嵌套字段定义 |
| 5 | `infrastructure/validation/config_loader.py` | **MODIFIED** | `validate()` 新增嵌套 `research` section 验证 |
| 6 | `START_HERE.md` | **MODIFIED** | B4 和 Key Paths 指向 `configs/research_task_template.yaml` |
| 7 | `docs/02_Usage/New_Research_Task_Guide.md` | **MODIFIED** | 模板路径、结构、字段参考、示例全部更新为嵌套格式 |
| 8 | `docs/03_Configuration/Configuration_Guide.md` | **MODIFIED** | Section 5 和 Summary Table 更新为嵌套字段 |
| 9 | `tests/test_research_task_config.py` | **NEW** | 28 个验证测试 |

---

## 3. New Schema

### 3.1 Formal Template Structure

```yaml
# ---- Task Identity (REQUIRED) ----
task_id: "my_research_001"
title: "Your Research Title"

# ---- Research Content (REQUIRED — drives Modules 01-07) ----
research:
  domain: "computer_vision"
  topic: "Adversarial Robustness of Vision-Language Models"
  keywords:
    - "adversarial attack"
    - "vision-language model"
    - "robustness"
  research_question: "How do adversarial patches affect VLM reasoning capabilities?"
  target: "LLaVA-1.5-7B"

# ---- Literature Acquisition (OPTIONAL — drives Modules 01-02) ----
literature:
  candidate_target: []
  core_target: []
  deep_analysis_target: []
  arxiv:
    download_pdf: true
    download_source: false
    prefer_latex_analysis: true

# ---- LLM Configuration (REQUIRED) ----
llm:
  type: "openai"

# ---- Experiment Configuration (drives Modules 07-09) ----
experiment:
  method: "samra"
  synthetic:
    num_samples: 100
    seed: 42
  real:
    checkpoint_dir: "checkpoints"
    resume_from_checkpoint: false
    seed: 42

# ---- Analysis Configuration (Module 10) ----
analysis:
  output_dir: "output/analysis"
  significance_level: 0.05

# ---- Output Directories (Modules 11-13) ----
output:
  figure_table_dir: "output/figures_tables"
  paper_dir: "output/paper"
  reference_dir: "output/references"

# ---- Paper Configuration (Modules 12-13) ----
paper:
  min_references: 5
```

### 3.2 Required Fields

| Field | Section | Required | Description |
|-------|---------|----------|-------------|
| `task_id` | top-level | Yes | Unique task identifier |
| `title` | top-level | Yes | Human-readable title |
| `research.domain` | research | Yes | Research domain |
| `research.keywords` | research | Yes | Search keywords (List[str]) |
| `research.research_question` | research | Yes | Core research question |
| `llm.type` | llm | Yes | LLM provider type |

### 3.3 Optional Fields

| Field | Section | Default | Description |
|-------|---------|---------|-------------|
| `research.topic` | research | `""` | Specific topic |
| `research.target` | research | `""` | Target model/method |
| `literature.candidate_target` | literature | `[]` | Paper IDs for candidates |
| `literature.core_target` | literature | `[]` | Paper IDs for deep analysis |
| `literature.deep_analysis_target` | literature | `[]` | Paper IDs for deep analysis |
| `literature.arxiv.download_pdf` | literature.arxiv | `true` | Download PDFs |
| `literature.arxiv.download_source` | literature.arxiv | `false` | Download LaTeX source |
| `literature.arxiv.prefer_latex_analysis` | literature.arxiv | `true` | Prefer LaTeX over PDF |
| `experiment.synthetic` | experiment | `{}` | Synthetic experiment config |
| `experiment.real` | experiment | `{}` | Real experiment config |

### 3.4 Backward Compatibility

旧版扁平格式仍然支持（用于 E2E test）：

```yaml
# Legacy flat format (backward compatible)
keywords: ["keyword"]
research_question: "Question?"
domain: "computer_vision"
```

当同时存在嵌套和扁平字段时，嵌套字段优先。

---

## 4. Template Path

**正式模板:** `configs/research_task_template.yaml`

**E2E 测试配置（仅用于测试）:** `tests/e2e_test_data/research_task.yaml` (保留不变)

---

## 5. Implementation Details

### 5.1 Research Context Extractor

新增 `infrastructure/research_context_extractor.py`，提供两个核心函数：

- `extract_research_context(task_config)` — 从 YAML dict 提取所有研究字段，支持嵌套+扁平格式
- `validate_research_task(task_config)` — 验证必填字段是否存在，返回错误列表

### 5.2 Module 01 Changes

Module 01 的 `execute()` 方法改为使用 `extract_research_context()` 提取研究字段：

```python
# Before (flat only):
keywords = task_config.get("keywords", [])
research_question = task_config.get("research_question", "")

# After (nested + flat):
ctx = extract_research_context(task_config)
keywords = ctx["keywords"]
research_question = ctx["research_question"]
```

Module 01 的 manifest 新增 `research_context` 字段，包含 domain、topic、keywords、research_question、target、literature targets、experiment policy 等，供 Modules 02-07 通过 `context` 参数读取。

### 5.3 ConfigLoader Changes

`validate()` 方法新增对嵌套 `research` section 的验证：当 `research` section 存在时，检查 `domain`、`keywords`、`research_question` 是否非空。

---

## 6. Validation Results

### 6.1 New Test Suite

```
tests/test_research_task_config.py — 28 tests
```

| Test Class | Tests | Status |
|------------|-------|--------|
| TestTemplateExists | 2 | PASS |
| TestTemplateFieldReading | 11 | PASS |
| TestFullConfigExtraction | 1 | PASS |
| TestBackwardCompatibility | 3 | PASS |
| TestValidationMissingFields | 10 | PASS |
| TestUnknownFields | 1 | PASS |
| **Total** | **28** | **ALL PASS** |

### 6.2 Regression Check

| Test | Status |
|------|--------|
| `test_module01_to_02_handoff` | PASS |
| `test_research_task_config` (28 tests) | ALL PASS |

### 6.3 Test Coverage

- domain 可读取 ✓
- topic 可读取 ✓
- keywords 可读取 ✓
- research_question 可读取 ✓
- literature targets 可读取 ✓ (candidate_target, core_target, deep_analysis_target)
- arxiv settings 可读取 ✓ (download_pdf, download_source, prefer_latex_analysis)
- synthetic/real policy 可读取 ✓
- unknown fields 不报错 ✓
- missing required fields 明确报错 ✓ (domain, keywords, research_question, task_id, title, llm.type)
- E2E config backward compatibility ✓
- flat format backward compatibility ✓
- nested takes precedence over flat ✓

---

## 7. Constraints Compliance

| Constraint | Status |
|-----------|--------|
| 未重构整个系统 | ✓ 仅修改 Module 01 的 execute() 方法和新增工具函数 |
| 未修改 Phase 1-8 / Sprint 1-2 代码逻辑 | ✓ 改动为增量式，向后兼容 |
| E2E test config 保留不变 | ✓ `tests/e2e_test_data/research_task.yaml` 未修改 |
| Python 3.12 兼容 | ✓ 使用标准库和 typing |
| 未自动启动 pipeline | ✓ 仅修复配置和代码 |
