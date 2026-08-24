# 模块接口文档

> Research Agent v8.2.2 — 模块接口规范与生命周期说明

---

## 目录

1. [概述](#1-概述)
2. [七步模块生命周期](#2-七步模块生命周期)
3. [v8.2.2 接口变更说明](#3-v822-接口变更说明)
4. [Fallback 查询机制](#4-fallback-查询机制)
5. [模块清单与依赖关系](#5-模块清单与依赖关系)
6. [模块输入/输出数据类结构](#6-模块输入输出数据类结构)

---

## 1. 概述

Research Agent 流水线由 15 个模块组成（编号 01-14，含 02_5）。每个模块实现统一的七步生命周期接口，由 `PipelineOrchestrator`（`orchestrator/pipeline.py`）统一调度。

核心设计原则：

- **CLI 仅调用 Orchestrator，不直接调用模块。**
- 模块通过目录名前缀数字动态加载（如 `01_literature_retrieval`）。
- 上游模块输出作为 context 传递给下游模块。
- 模块不自行决定 Fallback 策略，必须通过 `context["pipeline"].get_fallback()` 查询。

---

## 2. 七步模块生命周期

每个模块必须实现以下七个方法，按顺序由 Orchestrator 调用：

```
load_config → validate_input → execute → validate_output → quality_assessment → write_manifest → write_report
```

### 2.1 各步骤说明

| 步骤 | 方法签名 | 职责 | 返回值 |
|------|---------|------|--------|
| 1. 加载配置 | `load_config(config: Dict) -> None` | 加载并验证模块级配置参数 | 无返回值，失败抛异常 |
| 2. 验证输入 | `validate_input(input_data: ModuleInput) -> bool` | 检查所有必需输入文件是否存在且格式正确 | `True`/`False` |
| 3. 执行核心逻辑 | `execute(input_data: ModuleInput) -> ModuleOutput` | 运行模块核心逻辑，产出输出文件 | `ModuleOutput` 数据类 |
| 4. 验证输出 | `validate_output(output: ModuleOutput) -> bool` | 检查所有必需输出文件是否存在且格式正确 | `True`/`False` |
| 5. 质量评估 | `quality_assessment(output: ModuleOutput) -> Dict` | 对照硬性要求和软性阈值评估输出质量 | 质量指标字典 |
| 6. 写入清单 | `write_manifest(output: ModuleOutput) -> Dict` | 生成模块清单用于溯源追踪 | 清单字典 |
| 7. 写入报告 | `write_report(output: ModuleOutput) -> str` | 生成人类可读的验证报告 | Markdown 字符串 |

### 2.2 Orchestrator 调用流程

Orchestrator 在 `_execute_module()` 方法中按以下顺序调用（见 `orchestrator/pipeline.py` 第 681-764 行）：

```python
# 1. 动态加载模块实例
instance = self._load_module(module_id)

# 2. 加载配置
instance.load_config(self.task_config)

# 3. 构建输入并验证
input_data = self._build_input(module_id)
instance.validate_input(input_data)  # False → FAIL

# 4. 执行
output = instance.execute(input_data)

# 5. 验证输出
instance.validate_output(output)  # False → FAIL（保留部分输出供下游使用）

# 6. 质量评估
quality = instance.quality_assessment(output)

# 状态判定：硬性要求全通过 → PASS，否则 → WARNING
```

### 2.3 质量评估规则

`quality_assessment()` 返回的字典中包含 `hard_requirements` 字段：

- **所有硬性要求通过** → 模块状态为 `PASS`
- **任一硬性要求未通过** → 模块状态为 `WARNING`（流水线继续执行）

无论 PASS 还是 WARNING，Orchestrator 都会标记模块为已完成（`complete_module`）。

---

## 3. v8.2.2 接口变更说明

> **重要：v8.2.2 未修改模块接口本身。**

七步生命周期方法签名、输入/输出数据类结构在 v8.2.2 中保持不变。v8.2.2 的变更集中在 Orchestrator 层面，对模块透明：

### 3.1 新增的 Context 注入

v8.2.2 在 `_build_context()` 中向 context 字典注入了两个新字段（见 `pipeline.py` 第 910-912 行）：

```python
# v8.2.2: 注入 pipeline 引用供模块查询 Fallback
context["pipeline"] = self
context["run_mode"] = self._run_mode
```

模块可通过 `context["pipeline"]` 访问 Orchestrator 实例，调用 `get_fallback()` 方法。模块可通过 `context["run_mode"]` 获知当前运行模式（`production`/`limited`/`development`）。

### 3.2 新增的配置文件

v8.2.2 引入两个配置文件，不影响模块接口：

| 文件 | 用途 |
|------|------|
| `configs/external_dependency.yaml` | 外部依赖配置的统一入口，定义运行模式和依赖配置路径 |
| `configs/dependency_policy.yaml` | 集中式 Fallback 策略定义 |

### 3.3 运行模式

由 `configs/external_dependency.yaml` 中的 `run_mode` 字段控制：

| 模式 | Fallback | 真实 LLM | Mock |
|------|----------|---------|------|
| `production` | 禁止（返回 `block`） | 必须 | 禁止 |
| `limited` | 允许 | 非必须 | 禁止 |
| `development` | 允许 | 非必须 | 允许 |

---

## 4. Fallback 查询机制

### 4.1 核心原则

> **模块不得自行决定 Fallback 策略。** 模块必须通过 `context["pipeline"].get_fallback()` 查询统一策略。

### 4.2 调用方式

模块在执行过程中，当发现某个外部依赖（Skill、MCP、LLM）不可用时，按以下方式查询 Fallback：

```python
def execute(self, input_data: ModuleInput) -> ModuleOutput:
    pipeline = input_data.context["pipeline"]
    run_mode = input_data.context["run_mode"]

    # 查询 Skill 缺失时的 Fallback 策略
    policy = pipeline.get_fallback(
        module_id=self.MODULE_ID,          # 如 "01"
        dependency_type="skill:light-literature-search"
    )

    if policy["action"] == "block":
        # production 模式下 Fallback 被禁止，模块必须中止
        raise ModuleError(policy["reason"])
    elif policy["action"] == "llm_prompt":
        # 使用 LLM 提示词替代
        prompt_template = policy.get("prompt_template", "")
        ...
    elif policy["action"] == "internal_implementation":
        # 使用内置实现替代
        ...
    elif policy["action"] == "skip":
        # 跳过该功能
        ...
    elif policy["action"] == "template":
        # 使用模板模式
        ...
    elif policy["action"] == "none":
        # 无策略，模块自行处理
        ...
```

### 4.3 dependency_type 取值

| 类型前缀 | 示例 | 说明 |
|---------|------|------|
| `skill:` | `skill:light-literature-search` | Skill 不可用 |
| `skill:` | `skill:arxiv` | arxiv Skill 不可用 |
| `mcp:` | `mcp:arxiv` | MCP 服务不可用 |
| `mcp:` | `mcp:drawio` | Draw.io MCP 不可用 |
| `llm` | `llm` | LLM 不可用 |
| `model` | `model` | 本地模型不可用 |

### 4.4 返回值结构

`get_fallback()` 返回字典包含以下字段：

```python
{
    "action": "llm_prompt",          # Fallback 动作类型
    "message": "Skill missing...",   # 人类可读说明
    "module_id": "01",               # 查询的模块 ID
    "dependency_type": "skill:...",  # 查询的依赖类型
    # 可选字段：
    "prompt_template": "literature_search_basic",  # action=llm_prompt 时
    "reason": "Fallback not allowed in production mode"  # action=block 时
}
```

### 4.5 action 取值汇总

| action | 含义 | 典型场景 |
|--------|------|---------|
| `block` | 禁止 Fallback，模块必须中止 | production 模式下依赖缺失 |
| `llm_prompt` | 使用 LLM 提示词替代 | Skill 缺失，降级为 LLM 基础提示 |
| `internal_implementation` | 使用内置实现替代 | MCP 不可用，使用内置下载器 |
| `matplotlib` | 使用 matplotlib 内置绘图 | 绘图 Skill 缺失 |
| `local_file` | 使用本地文件替代 | Zotero MCP 不可用，使用本地 .bib |
| `template` | 使用模板模式生成 | LLM 不可用 |
| `skip` | 跳过该功能 | 非关键依赖缺失 |
| `none` | 无匹配策略 | 模块自行决定处理方式 |

### 4.6 策略定义位置

所有 Fallback 策略定义在 `configs/dependency_policy.yaml` 中，分为四组：

- `skill_fallback` — Skill 缺失策略
- `mcp_fallback` — MCP 不可用策略
- `llm_fallback` — LLM 不可用策略
- `model_fallback` — 本地模型不可用策略

每组都有 `default` 兜底策略。运行模式约束在 `mode_constraints` 中定义。

---

## 5. 模块清单与依赖关系

### 5.1 模块执行顺序

流水线按以下顺序执行（`MODULE_SEQUENCE`）：

```
01 → 02 → 02_5 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14
```

### 5.2 全部 15 个模块

| 编号 | 模块名称 | 实现类 | 上游模块 | 下游模块 |
|------|---------|--------|---------|---------|
| 01 | 文献检索 (Literature Retrieval) | `LiteratureRetrievalImplementation` | 无（入口） | 02, 03 |
| 02 | 来源获取与解析 (Source Acquisition) | `SourceAcquisitionImplementation` | 01 | 03 |
| 02_5 | 论文资产智能 (Paper Asset Intelligence) | `PaperAssetIntelligenceEngine` | 02 | 03, 12 |
| 03 | 文献智能 (Literature Intelligence) | `LiteratureIntelligenceImplementation` | 02 | 04, 05 |
| 04 | 研究全景与差距分析 (Research Landscape) | `ResearchLandscapeModule` | 03 | 05 |
| 05 | 创新推理 (Innovation Reasoning) | `InnovationReasoningModule` | 03, 04 | 06 |
| 06 | 理论与方法设计 (Theory & Method) | `TheoryMethodModule` | 05 | 07, 08, 09, 11 |
| 07 | 实验规划 (Experiment Planning) | `ExperimentPlanningModule` | 06 | 08, 09, 10, 11 |
| 08 | 合成实验引擎 (Synthetic Experiment Engine) | `SyntheticExperimentEngine` | 06, 07 | 10, 11 |
| 09 | 真实实验引擎 (Real Experiment Engine) | `RealExperimentEngine` | 06, 07 | 10, 11 |
| 10 | 结果分析 (Result Analysis) | `ResultAnalysisEngine` | 07, 08, 09 | 11 |
| 11 | 图表生成 (Figure & Table) | `FigureTableEngine` | 06, 07, 08, 09, external | 12 |
| 12 | 论文写作 (Paper Writing) | `PaperWritingEngine` | all（全部上游） | 13 |
| 13 | 引用与补充材料 (Reference & Supplementary) | `ReferenceSupplementaryEngine` | 01, 12 | 无 |
| 14 | 审稿循环 (Reviewer Loop) | `ReviewerLoopModule` | 12, 13 | 无 |

### 5.3 模块跳过规则

根据 `research_task.yaml` 中的 `experiment.mode` 配置，Orchestrator 自动跳过部分模块：

| 实验模式 | 跳过的模块 | 说明 |
|---------|-----------|------|
| `synthetic_research`（默认） | 09（真实实验） | 仅使用合成实验 |
| `real_gpu_only` | 08（合成实验） | 仅使用真实实验 |

### 5.4 决策路由

Module 10 完成后，根据 `decision.json` 中的决策值进行路由（最多循环 3 次）：

| 决策值 | 跳转目标 |
|--------|---------|
| `PASS_TO_FIGURE_TABLE` | Module 11（正常前进） |
| `RETURN_TO_EXPERIMENT` | Module 09（重做实验） |
| `RETURN_TO_EXPERIMENT_PLAN` | Module 07（重做实验规划） |
| `RETURN_TO_METHOD` | Module 06（重做方法设计） |
| `RETURN_TO_INNOVATION` | Module 05（重做创新推理） |
| `HUMAN_REVIEW_REQUIRED` | 暂停等待人工审查 |

> 在 `synthetic_research` 模式下，`HUMAN_REVIEW_REQUIRED` 自动转换为 `PASS_TO_FIGURE_TABLE`。

### 5.5 质量门控

| 门控 | 位置 | 条件 | 失败行为 |
|------|------|------|---------|
| 文献质量门控 | Module 03 执行前 | `data/literature/` 下论文数 >= 50 | 阻塞流水线（返回 `blocked`） |
| LLM 门控 | Module 05/06/10/12/14 执行前 | 对应任务类型有真实 LLM 可用 | 记录警告，继续执行（模板模式） |

可通过 `skip_gates=True` 跳过所有门控。

---

## 6. 模块输入/输出数据类结构

### 6.1 统一输入数据类

每个模块定义自己的 `XxxInput` 数据类，但共享以下通用字段：

```python
@dataclass
class ModuleInput:
    task_id: str                        # 任务 ID
    config: Dict[str, Any]              # 任务配置（research_task.yaml 内容）
    input_files: Dict[str, str]         # 输入文件名 → 路径映射
    context: Dict[str, Any]             # 上游模块 context（含 pipeline 引用）
    # 上游模块输出字段（按模块不同而异），例如：
    # upstream_module_01: Dict[str, Any]
    # upstream_module_03: Dict[str, Any]
```

### 6.2 统一输出数据类

每个模块定义自己的 `XxxOutput` 数据类，共享以下通用字段：

```python
@dataclass
class ModuleOutput:
    task_id: str                        # 任务 ID
    output_files: Dict[str, str]       # 输出文件名 → 路径映射
    manifest: Dict[str, Any]           # 模块清单（含 data_origin 等溯源信息）
    warnings: List[str] = []           # 警告信息列表
    errors: List[str] = []             # 错误信息列表
```

### 6.3 context 字典内容

`context` 字段由 Orchestrator 的 `_build_context()` 方法构建，包含：

| 键 | 类型 | 说明 |
|----|------|------|
| `module_<id>` | Dict | 各上游模块的 manifest |
| `pipeline` | PipelineOrchestrator | v8.2.2 新增：Orchestrator 实例引用 |
| `run_mode` | str | v8.2.2 新增：运行模式 |
| `skill_instructions` | str | v8.2 新增：可用 Skill 提示词 |
| `available_skills` | List | v8.2 新增：可用 Skill 列表 |
| `human_feedback` | str | v8.2 新增：人工反馈内容（仅限支持反馈的模块） |

### 6.4 各模块输入/输出类名映射

| 模块 | 输入类 | 输出类 |
|------|--------|--------|
| 01 | `LiteratureRetrievalInput` | `LiteratureRetrievalOutput` |
| 02 | `SourceAcquisitionInput` | `SourceAcquisitionOutput` |
| 02_5 | `PaperAssetIntelligenceInput` | `PaperAssetIntelligenceOutput` |
| 03 | `LiteratureIntelligenceInput` | `LiteratureIntelligenceOutput` |
| 04 | `ResearchLandscapeInput` | `ResearchLandscapeOutput` |
| 05 | `InnovationReasoningInput` | `InnovationReasoningOutput` |
| 06 | `TheoryMethodInput` | `TheoryMethodOutput` |
| 07 | `ExperimentPlanningInput` | `ExperimentPlanningOutput` |
| 08 | `SyntheticExperimentInput` | `SyntheticExperimentOutput` |
| 09 | `RealExperimentInput` | `RealExperimentOutput` |
| 10 | `ResultAnalysisInput` | `ResultAnalysisOutput` |
| 11 | `FigureTableInput` | `FigureTableOutput` |
| 12 | `PaperWritingInput` | `PaperWritingOutput` |
| 13 | `ReferenceSupplementaryInput` | `ReferenceSupplementaryOutput` |
| 14 | `Module14Input` | `Module14Output` |

### 6.5 上游字段映射

Orchestrator 通过 `_get_upstream_fields()` 为每个模块构建上游字段（字段名 → 上游模块 ID）：

| 模块 | 上游字段 → 模块 ID |
|------|-------------------|
| 02 | `upstream_module_01` → 01 |
| 02_5 | `upstream_module_02` → 02 |
| 03 | `upstream_module_02` → 02 |
| 04 | `upstream_module_03` → 03 |
| 05 | `upstream_module_03` → 03, `upstream_module_04` → 04 |
| 06 | `upstream_module_05` → 05 |
| 07 | `upstream_module_06` → 06 |
| 08 | `upstream_module_06` → 06, `upstream_module_07` → 07 |
| 09 | `upstream_module_06` → 06, `upstream_module_07` → 07 |
| 10 | `upstream_module_07` → 07, `upstream_module_08` → 08, `upstream_module_09` → 09 |
| 11 | `upstream_module_06` → 06, `upstream_module_07` → 07, `upstream_module_08` → 08, `upstream_module_09` → 09, `upstream_module_external` → external |
| 12 | `upstream_module_all` → all（全部上游） |
| 13 | `upstream_module_01` → 01, `upstream_module_12` → 12 |
| 14 | `upstream_module_12` → 12, `upstream_module_13` → 13 |

### 6.6 模块加载方式

Orchestrator 通过 `_load_module()` 动态加载模块，处理两种导入模式：

- **Module 01-03, 08-13**：使用裸名导入（`from interface import ...`）
- **Module 04-07**：使用相对导入（`from .interface import ...`）

加载前会清除 `sys.modules` 中缓存的 `interface`、`schema`、`validator` 模块，确保加载正确的本地文件。

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `orchestrator/pipeline.py` | 流水线编排器，模块加载与调度 |
| `modules/<module_dir>/interface.py` | 各模块接口定义与输入/输出数据类 |
| `modules/<module_dir>/manifest.yaml` | 各模块清单（依赖、输入输出、质量指标） |
| `modules/<module_dir>/implementation.py` | 各模块实现 |
| `modules/<module_dir>/schema.py` | 各模块数据模式定义 |
| `modules/<module_dir>/validator.py` | 各模块验证器 |
| `configs/external_dependency.yaml` | 外部依赖统一配置 |
| `configs/dependency_policy.yaml` | Fallback 策略定义 |
| `core/exceptions/exceptions.py` | 异常层次结构 |
| `core/state/state_machine.py` | 状态机定义 |
