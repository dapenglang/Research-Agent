# 人工干预指南

> Research Agent v8.2.2 — Human-in-the-loop 反馈机制说明

---

## 目录

1. [概述](#1-概述)
2. [反馈目录结构](#2-反馈目录结构)
3. [支持人工反馈的模块](#3-支持人工反馈的模块)
4. [反馈文件填写方法](#4-反馈文件填写方法)
5. [流水线恢复流程](#5-流水线恢复流程)
6. [多轮反馈与状态管理](#6-多轮反馈与状态管理)

---

## 1. 概述

Research Agent v8.2 引入了 Human-in-the-loop（人在回路）反馈机制，允许研究人员在关键决策点介入并修正模块输出。v8.2.2 保留了该机制，未做修改。

核心设计：

- 反馈以 Markdown 文件形式存储在 `human_feedback/` 目录中。
- 流水线在执行支持反馈的模块前，自动读取对应的反馈文件。
- 反馈内容作为 `context["human_feedback"]` 注入到下游模块。
- 如果反馈文件为空或不存在，流水线正常继续，不受影响。
- 反馈机制是可选的，不影响全自动运行模式。

---

## 2. 反馈目录结构

反馈文件位于项目根目录的 `human_feedback/` 文件夹中：

```
human_feedback/
├── README.md                    # 使用说明
├── innovation_feedback.md       # Module 05 创新推理反馈
├── method_feedback.md           # Module 06 方法设计反馈
└── review_response.md           # Module 14 审稿回复
```

---

## 3. 支持人工反馈的模块

以下模块支持人工反馈（由 `pipeline.py` 中 `HUMAN_FEEDBACK_MODULES` 定义）：

| 模块 | 模块名称 | 反馈文件 | 反馈类型键 | 触发时机 |
|------|---------|---------|-----------|---------|
| 05 | 创新推理 (Innovation Reasoning) | `innovation_feedback.md` | `innovation` | Module 05 执行前 |
| 06 | 理论与方法设计 (Theory & Method) | `method_feedback.md` | `method` | Module 06 执行前 |
| 14 | 审稿循环 (Reviewer Loop) | `review_response.md` | `review` | Module 14 执行前 |

### 3.1 LLM 必需模块

以下模块要求真实 LLM 支持（非 Mock），与人工反馈配合使用效果最佳：

| 模块 | LLM 任务类型 | 说明 |
|------|-------------|------|
| 05 | `innovation_reasoning` | 创新推理，高质量输出依赖 LLM |
| 06 | `method_design` | 方法设计，高质量输出依赖 LLM |
| 10 | `experiment_analysis` | 实验分析，高质量输出依赖 LLM |
| 12 | `paper_generation` | 论文生成，高质量输出依赖 LLM |
| 14 | `reviewer` | 审稿模拟，高质量输出依赖 LLM |

> 注意：Module 10 和 12 虽然是 LLM 必需模块，但目前未配置人工反馈钩子。如需扩展，可在 `HUMAN_FEEDBACK_MODULES` 中添加条目并在 `human_feedback/` 中创建对应文件。

### 3.2 反馈注入机制

Orchestrator 在 `_build_context()` 方法中注入反馈（见 `pipeline.py` 第 897-908 行）：

```python
if module_id in HUMAN_FEEDBACK_MODULES:
    feedback_type = HUMAN_FEEDBACK_MODULES[module_id]
    feedback_dir = _V3_ROOT / "human_feedback"
    if self._skill_integration:
        feedback = self._skill_integration.read_human_feedback(feedback_dir, feedback_type)
        if feedback:
            context["human_feedback"] = feedback
```

模块在 `execute()` 中可通过 `input_data.context.get("human_feedback", "")` 读取反馈内容。

---

## 4. 反馈文件填写方法

### 4.1 通用格式

所有反馈文件均为 Markdown 格式。流水线会读取文件全部内容并传递给对应模块。文件中包含预置的章节标题和注释提示，按需填写即可。

> 如果不填写任何内容（文件保持模板状态或为空），流水线将跳过反馈，正常运行。

### 4.2 innovation_feedback.md（Module 05 创新推理）

在 Module 05 执行前填写，用于调整创新方向。

文件结构：

```markdown
# Innovation Feedback

## Additional Innovation Directions
<!-- 在此处添加你的创新想法 -->

## Modifications to Generated Innovations
<!-- 修改或拒绝 innovation_report.md 中的创新点 -->

## Priority Adjustment
<!-- 重新排序或设定优先级 -->
```

填写示例：

```markdown
## Additional Innovation Directions

- 探索多模态对齐中的对抗样本鲁棒性问题
- 结合因果推理改进视觉语言模型的解释性

## Modifications to Generated Innovations

- 拒绝候选方案 #2（基于扩散模型的方法），理由：计算成本过高
- 候选方案 #3 需增加与 SAM 模型的对比实验

## Priority Adjustment

1. 候选方案 #3（最高优先级）
2. 候选方案 #1
```

### 4.3 method_feedback.md（Module 06 方法设计）

在 Module 06 执行前填写，用于调整方法设计、算法和公式。

文件结构：

```markdown
# Method Feedback

## Algorithm Adjustments
<!-- 修改算法设计 -->

## Formula Corrections
<!-- 修正或添加数学公式 -->

## Model Structure Changes
<!-- 调整模型架构 -->

## Complexity Analysis Updates
<!-- 更新复杂度分析 -->
```

填写示例：

```markdown
## Algorithm Adjustments

- 将注意力机制从多头自注意力改为稀疏注意力，降低 O(n^2) 复杂度
- 在训练阶段增加梯度裁剪，阈值设为 1.0

## Formula Corrections

- 损失函数应使用 Focal Loss 而非 Cross-Entropy，公式：
  L_FL = -α(1-p)^γ log(p)，其中 α=0.25, γ=2.0

## Model Structure Changes

- 编码器层数从 12 减少到 6
- 添加跳跃连接（skip connection）
```

### 4.4 review_response.md（Module 14 审稿回复）

在 Module 14 执行前填写，用于回复审稿意见并指导修订。

文件结构：

```markdown
# Review Response

## Response to Major Issues
<!-- 回应主要审稿意见 -->

## Response to Minor Issues
<!-- 回应次要审稿意见 -->

## Revision Plan
<!-- 描述修订计划 -->

## Additional Experiments Needed
<!-- 列出需要补充的实验 -->
```

填写示例：

```markdown
## Response to Major Issues

1. 审稿人质疑实验数据集规模不足 → 已补充在 ImageNet-1K 上的实验
2. 审稿人要求与 SOTA 方法对比 → 已添加与 SAM、SEEM 的定量对比

## Revision Plan

- 3.2 节：补充消融实验表格
- 4.1 节：更新性能对比图表
- 附录：增加计算成本分析
```

---

## 5. 流水线恢复流程

### 5.1 标准工作流

以 Module 05 为例：

```
1. 流水线执行 Module 05，生成 innovation_report.md
2. 流水线检查 Module 05 是否启用了人工反馈
3. 如果启用 → 流水线暂停，输出提示：
   "Waiting for human feedback in human_feedback/innovation_feedback.md"
4. 研究人员审阅 innovation_report.md
5. 研究人员填写 human_feedback/innovation_feedback.md
6. 研究人员通过 CLI resume 恢复流水线
7. 流水线读取反馈，注入到 Module 06 的 context 中
8. Module 06 执行时结合人工反馈调整方法设计
```

### 5.2 CLI 操作命令

```powershell
# 查看当前流水线状态
python -m Research_Agent_v3.cli.cli status --task research_task.yaml

# 恢复暂停的流水线（从检查点继续）
python -m Research_Agent_v3.cli.cli resume --task research_task.yaml

# 从指定模块重新执行
python -m Research_Agent_v3.cli.cli rerun --task research_task.yaml --from 05
```

### 5.3 状态机流转

人工反馈涉及的状态流转：

```
MODULE_EXECUTING → PAUSED_HUMAN_REVIEW → RESUMING → MODULE_EXECUTING
```

| 状态 | 说明 |
|------|------|
| `module_executing` | 模块正在执行 |
| `paused_human_review` | 等待人工反馈（流水线暂停） |
| `resuming` | 从暂停状态恢复中 |
| `module_executing` | 恢复后继续执行下一模块 |

### 5.4 反馈为空时的行为

如果反馈文件不存在、为空、或保持模板状态（只有注释没有实际内容）：

- 流水线正常继续执行，不注入 `human_feedback`。
- 不会报错或阻塞。
- 模块按全自动模式运行。

---

## 6. 多轮反馈与状态管理

### 6.1 多轮反馈

支持通过 `resume`/`rerun` 机制进行多轮反馈：

1. 第一轮：填写反馈 → resume → 查看新输出
2. 如果不满意：修改反馈 → rerun --from 05 → 查看新输出
3. 重复直到满意

### 6.2 反馈文件保留

- 反馈文件在流水线运行后不会被删除或覆盖。
- 每次运行时，流水线读取最新的文件内容。
- 修改反馈文件后无需重启，`resume` 或 `rerun` 会自动读取最新版本。

### 6.3 搭配决策路由使用

Module 10 的决策路由可与人工反馈配合：

- Module 10 返回 `RETURN_TO_METHOD` → 跳回 Module 06
- 在 Module 06 执行前，填写 `method_feedback.md` 修正方法
- 流水线读取反馈后重新执行 Module 06

决策路由最多循环 3 次（`MAX_DECISION_LOOPS = 3`），超过后自动前进。

### 6.4 注意事项

- 反馈内容为纯文本 Markdown，不支持代码执行。
- 反馈中引用的文件路径需使用正斜杠 `/`（跨平台兼容）。
- 反馈内容会作为 LLM 提示的一部分传递，注意控制长度。
- 在 `production` 模式下，`HUMAN_REVIEW_REQUIRED` 决策不会自动跳过（但在 `synthetic_research` 模式下会自动转为 `PASS_TO_FIGURE_TABLE`）。

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `orchestrator/pipeline.py` | `HUMAN_FEEDBACK_MODULES` 定义与反馈注入逻辑 |
| `human_feedback/README.md` | 反馈目录使用说明 |
| `human_feedback/innovation_feedback.md` | Module 05 反馈模板 |
| `human_feedback/method_feedback.md` | Module 06 反馈模板 |
| `human_feedback/review_response.md` | Module 14 反馈模板 |
| `core/state/state_machine.py` | `PAUSED_HUMAN_REVIEW` 状态定义 |
| `infrastructure/skills/skill_runtime.py` | `read_human_feedback()` 读取方法 |
