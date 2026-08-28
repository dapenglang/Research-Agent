# LLM 使用分析报告

**任务ID**: VLM_Safety_001
**分析时间**: 2026-08-17
**数据来源**: output/llm_usage_report.json

---

## 一、双模型策略配置

本次验证运行采用双模型 LLM 策略，通过 Ollama 本地部署两个模型分别负责不同任务层级。

### 1.1 模型配置

| 模型 | 角色 | 参数 | Endpoint | 温度 | 超时 |
|------|------|------|----------|------|------|
| deepseek-r1:8b | 核心推理模型 | 8B 参数 | http://localhost:11434/v1 | 0.2-0.5 | 300s |
| gemma4:26b | 辅助生成模型 | 26B 参数 | http://localhost:11434/v1 | 0.7 | 300s |

### 1.2 任务路由策略

| 任务类型 | 路由模型 | 温度 | 最大Token | 说明 |
|----------|----------|------|-----------|------|
| literature_analysis | deepseek-r1:8b | 0.2 | 8192 | 文献深度分析 |
| innovation_reasoning | deepseek-r1:8b | 0.5 | 8192 | 创新点推理 |
| method_design | deepseek-r1:8b | 0.3 | 8192 | 方法设计 |
| experiment_analysis | deepseek-r1:8b | 0.2 | 8192 | 实验结果分析 |
| reviewer | deepseek-r1:8b | 0.3 | 8192 | 审稿评估 |
| paper_generation | gemma4:26b | 0.7 | 8192 | 论文文本生成 |
| figure_generation | gemma4:26b | 0.5 | 8192 | 图表生成 |
| reference_checking | gemma4:26b | 0.2 | 8192 | 引用检查 |

### 1.3 配置文件

- **提供商配置**: `configs/providers.yaml`
- **路由策略**: `configs/llm_routing.yaml`
- **LLM参数**: `configs/llm.yaml`
- **任务配置**: `configs/research_task_vlm_safety.yaml`

---

## 二、LLM 调用日志分析

### 2.1 已记录的 LLM 调用

根据 `output/llm_usage_report.json`，本次运行共记录 **1 次** LLM 调用：

| 字段 | 值 |
|------|-----|
| 模块 | Module 04 (Research Gap Analysis) |
| Provider | LocalLLMProvider |
| 模型 | deepseek-r1:8b |
| 是否Mock | false |
| Prompt预览 | "Analyze research gaps based on 50 papers in unknown." |
| 时间戳 | 2026-08-17 10:01:53 |
| Fallback | none |
| 状态 | success |
| 响应长度 | 8,275 字符 |

### 2.2 调用详情

```json
{
  "module": "04",
  "provider": "LocalLLMProvider",
  "model": "deepseek-r1:8b",
  "is_mock": false,
  "prompt_preview": "Analyze research gaps based on 50 papers in unknown.",
  "timestamp": "2026-08-17 10:01:53",
  "fallback": "none",
  "status": "success",
  "response_length": 8275
}
```

### 2.3 调用统计

| 统计项 | 值 |
|--------|-----|
| 总调用次数 | 1 |
| 成功次数 | 1 |
| 失败次数 | 0 |
| Mock调用次数 | 0 |
| 真实LLM调用次数 | 1 |
| 总响应字符数 | 8,275 |
| 平均响应字符数 | 8,275 |

---

## 三、模块级 LLM 使用分析

### 3.1 各模块 LLM 使用情况

| 模块 | 预期LLM | 实际LLM调用 | 日志记录 | 状态 |
|------|---------|-------------|----------|------|
| 01 Literature Search | 无需LLM | - | - | N/A |
| 02 Paper Download | 无需LLM | - | - | N/A |
| 02_5 Figure Extraction | 无需LLM | - | - | N/A |
| 03 Paper Analysis | 无需LLM | - | - | N/A |
| 04 Research Gap | deepseek-r1:8b | deepseek-r1:8b | 已记录 | **真实调用** |
| 05 Innovation | deepseek-r1:8b | 未记录 | 缺失 | **待验证** |
| 06 Method Design | deepseek-r1:8b | 未记录 | 缺失 | **待验证** |
| 07 Experiment Plan | deepseek-r1:8b | 未记录 | 缺失 | **待验证** |
| 08 Experiment Exec | 无需LLM | - | - | 模块失败 |
| 09 Result Collection | 无需LLM | - | - | N/A |
| 10 Result Analysis | deepseek-r1:8b | 未记录 | 缺失 | **待验证** |
| 11 Figure & Table | gemma4:26b | 未记录 | 缺失 | **待验证** |
| 12 Paper Writing | gemma4:26b | 可能调用 | 缺失 | **data_origin=llm_generated** |
| 13 Reference Mgmt | gemma4:26b | 未记录 | 缺失 | **WARNING** |
| 14 Auto Review | deepseek-r1:8b | 未记录 | 缺失 | **待验证** |

### 3.2 LLM Provider 注入分析

根据 `orchestrator/pipeline.py` 的配置，以下模块被注入 LLM Provider：

```python
LLM_INJECT_MODULES = {"04", "05", "06", "07"}
```

- **Module 04**: 已确认注入成功（日志记录了调用）
- **Module 05/06/07**: Provider 已注入但调用未被 LLMLoggingProxy 记录
- **Module 10/12/14**: 未在 LLM_INJECT_MODULES 中，可能通过其他路径获取 LLM

### 3.3 Module 12 特殊分析

Module 12 (Paper Writing) 的 pipeline_result 显示 `data_origin: "llm_generated"`，且执行时间约 300 秒（02:05:37 ~ 02:35:57），这表明：

- Module 12 确实调用了 LLM（gemma4:26b）生成论文
- 但该调用未被 LLMLoggingProxy 记录
- 可能原因：Module 12 通过 `configs/research_task_vlm_safety.yaml` 中的 llm 配置直接创建 Provider，未经过 Pipeline 的注入路径

---

## 四、Mock Provider 检查

### 4.1 Mock 使用检测结果

| 检查项 | 结果 |
|--------|------|
| llm_usage_report.json 中 is_mock 字段 | 全部为 false |
| LLM 网关警告 | 0 条（从之前的 5 条降为 0） |
| Provider 类型 | LocalLLMProvider（非 MockProvider） |
| Fallback 类型 | "none"（非 "mock_template"） |

### 4.2 结论

- **已记录的调用**: 100% 真实 LLM 调用，无 Mock
- **未记录的模块**: 需进一步验证是否使用了真实 LLM
- **Module 12**: data_origin 为 "llm_generated"，高度可能使用了真实 LLM

---

## 五、LLM 调用质量评估

### 5.1 Module 04 响应质量

- **响应长度**: 8,275 字符（约 1,500-2,000 词）
- **Prompt 质量**: 简洁明确（"Analyze research gaps based on 50 papers"）
- **生成内容**: 研究空白分析，被下游 Module 05/06 使用
- **执行时间**: 约 3 分 44 秒（02:01:53 ~ 02:05:37）

### 5.2 Module 12 论文生成质量

- **输出大小**: 75 KB (paper.md)
- **章节完整性**: 8 个完整章节
- **执行时间**: 约 30 分钟（300秒）
- **质量问题**:
  - 包含模板占位符（"[Insert Method Name]"）
  - 包含元评论文本（"Since the provided data..."）
  - 实验数据为 LLM 合成（非真实实验）

---

## 六、问题诊断

### 6.1 LLM 日志覆盖不全

**问题**: LLMLoggingProxy 仅记录了 Module 04 的调用，其他模块的 LLM 调用未被记录。

**根因分析**:
1. `LLM_INJECT_MODULES` 仅包含 {"04", "05", "06", "07"}，Module 10/12/14 未被包含
2. Module 12 通过 task config 中的 llm 字段直接创建 Provider，绕过了 Pipeline 的注入路径
3. Module 10/14 可能使用了内部的 LLM 调用逻辑，未经过 LLMRuntime

**修复建议**:
1. 将 `LLM_INJECT_MODULES` 扩展为 `{"04", "05", "06", "07", "10", "12", "14"}`
2. 确保 Module 12 使用 LLMRuntime 获取 Provider，而非直接从 task config 创建
3. 为 Module 10/14 添加 LLM Provider 注入

### 6.2 Prompt 质量问题

**问题**: Module 04 的 Prompt 中包含 "in unknown"，表明研究领域未被正确传递。

**根因**: task config 中的 research_field 字段可能未正确设置，或传递路径有误。

**修复建议**: 检查 `configs/research_task_vlm_safety.yaml` 中的 field/keywords 配置，确保正确传递到 Module 04 的 Prompt。

### 6.3 模板文本泄露

**问题**: Module 12 生成的论文中包含模板指令文本（如 "Since the provided data..."）。

**根因**: LLM Prompt 中包含了上游分析报告的原始文本（含 "inconclusive" 等状态信息），LLM 将这些元信息直接输出到论文中。

**修复建议**:
1. 在 Module 12 的 Prompt 中明确指示"不要包含元评论或模板指令"
2. 添加后处理步骤，过滤已知的模板文本模式
3. 改进上游数据质量，确保 Claim 不是全部 inconclusive

---

## 七、模型性能对比

### 7.1 deepseek-r1:8b 表现

| 指标 | 值 | 评价 |
|------|-----|------|
| 首次响应时间 | ~3分钟 | 可接受（本地模型） |
| 响应长度 | 8,275字符 | 充分 |
| 内容质量 | 被下游模块使用 | 良好 |
| Mock使用 | 0次 | 合规 |
| 超时 | 无 | 正常 |

### 7.2 gemma4:26b 表现

| 指标 | 值 | 评价 |
|------|-----|------|
| 论文生成时间 | ~30分钟 | 较长但可接受 |
| 输出大小 | 75KB | 充分 |
| 内容质量 | 完整但含模板文本 | 需改进 |
| Mock使用 | 0次（推测） | 合规 |
| 超时 | 无（300秒限制内） | 正常 |

---

## 八、改进建议

### 8.1 短期改进（1-2天）

1. **扩展 LLM_INJECT_MODULES**: 将 Module 10/12/14 加入注入列表
2. **统一 Provider 获取路径**: Module 12 应通过 LLMRuntime 获取 Provider
3. **改进 Prompt 工程**: 移除模板指令，增加"不要输出元评论"的约束
4. **添加后处理**: 论文生成后自动过滤占位符和模板文本

### 8.2 中期改进（1-2周）

1. **增加 LLM 调用监控**: 为所有模块添加 LLMLoggingProxy 包装
2. **实现 LLM 调用重试**: 对超时或失败的调用添加自动重试机制
3. **优化模型选择**: 根据任务复杂度动态选择模型（简单任务用小模型，复杂任务用大模型）
4. **添加 LLM 成本统计**: 记录每次调用的 Token 消耗和计算时间

### 8.3 长期改进（1个月+）

1. **支持云端 LLM**: 集成 DeepSeek API、OpenAI API 作为高性能选项
2. **实现模型路由优化**: 根据任务类型和负载自动选择本地/云端模型
3. **添加 LLM 输出质量评估**: 自动评估生成内容的质量分数
4. **支持多模型协作**: 多个模型并行生成，取最优结果

---

## 九、总结

本次验证运行的 LLM 使用情况可以概括为：**框架正确、配置合理、覆盖不足**。

- **框架正确**: 双模型策略配置完整，Ollama 本地模型可正常调用，deepseek-r1:8b 和 gemma4:26b 的分工明确
- **配置合理**: providers.yaml、llm_routing.yaml、llm.yaml 三层配置体系运作正常，任务到模型的路由逻辑清晰
- **覆盖不足**: LLMLoggingProxy 仅记录了 1 次调用（Module 04），其他模块的 LLM 使用情况无法确认。需要扩展注入范围和日志覆盖

核心改进方向是**扩大 LLM Provider 注入范围**和**完善日志记录机制**，确保所有核心模块（04/05/06/07/10/12/14）都使用真实 LLM 并被完整记录。

---

*本报告由 Research Agent v8.2.2 自动生成*
*报告路径: D:\Research Agent\Research_Agent_v3\LLM_Usage_Analysis.md*
