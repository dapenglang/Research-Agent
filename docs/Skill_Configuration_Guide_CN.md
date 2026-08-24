# Research Agent v8.2.2 — Skill 配置指南

> 本文档说明 Skill 注册表的结构、字段含义、能力映射、降级策略管理以及 Skill 安装与检查流程。

---

## 目录

1. [注册表位置](#1-注册表位置)
2. [Skill 字段说明](#2-skill-字段说明)
3. [能力字段（capability）](#3-能力字段capability)
4. [降级策略管理](#4-降级策略管理)
5. [安装新 Skill](#5-安装新-skill)
6. [运行 check_skills.py](#6-运行-check_skillspy)
7. [注册表示例](#7-注册表示例)

---

## 1. 注册表位置

Skill 注册表位于项目基础设施层，**不会被迁移或移动**：

```
infrastructure/skills/skill_registry.yaml
```

该文件是所有模块与 Skill 映射的唯一真实来源（Single Source of Truth）。

相关文件：

| 文件 | 路径 | 用途 |
|------|------|------|
| 注册表 | `infrastructure/skills/skill_registry.yaml` | 模块到 Skill 的映射定义 |
| 已安装清单 | `infrastructure/skills/installed_skills.json` | 运行时记录已安装的 Skill |
| 集成层 | `infrastructure/skills/skill_integration.py` | Skill 调用与集成逻辑 |
| 运行时 | `infrastructure/skills/skill_runtime.py` | Skill 运行时加载 |
| 扫描器 | `infrastructure/skills/skill_scanner.py` | Skill 目录扫描 |

> **重要**：`skill_registry.yaml` 是项目内部文件，与 TRAE Skill Store 中的 Skill 安装目录是两个不同的概念。注册表定义"需要哪些 Skill"，安装目录存放"实际有哪些 Skill"。

---

## 2. Skill 字段说明

注册表采用 `module_skill_mapping` 顶层键，按模块编号组织。每个 Skill 条目包含以下 7 个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill_name` | string | Skill 的唯一标识名称（如 `light-literature-search`） |
| `version` | string | Skill 版本号（当前统一为 `"1.0"`） |
| `source` | string | Skill 来源（`trae-skill-store` / `mcp` / `pip`） |
| `install_path` | string | Skill 安装路径，空字符串表示未安装或使用默认路径 |
| `required` | bool | 是否为必需 Skill（`true` = 缺失时模块无法正常工作） |
| `capability` | string | 该 Skill 提供的能力类型（见[第 3 节](#3-能力字段capability)） |
| `fallback` | string | 降级策略引用名，对应 `dependency_policy.yaml` 中的策略键 |

### 字段使用规则

- **`required: true`** 的 Skill 缺失时，`check_skills.py` 会报 FAIL
- **`required: false`** 的 Skill 缺失时，触发降级策略，不影响流程运行
- **`install_path`** 为空时，系统会检查 TRAE 默认安装目录 `c:/Users/<user>/.trae-cn/skills/<skill_name>`
- **`install_path`** 包含 `<user>` 占位符时，运行时自动替换为当前用户主目录

---

## 3. 能力字段（capability）

`capability` 字段标识 Skill 提供的功能类型，用于模块在运行时按需查找合适的 Skill。一个模块可以绑定多个具有相同 capability 的 Skill，系统会依次尝试调用。

### 能力类型一览

| capability | 说明 | 典型模块 |
|------------|------|----------|
| `literature_search` | 文献检索 | Module 01, 04 |
| `paper_download` | 论文下载 | Module 02 |
| `pdf_parsing` | PDF 解析 | Module 02 |
| `figure_extraction` | 图表提取 | Module 02_5 |
| `paper_analysis` | 论文深度分析 | Module 03 |
| `file_reading` | 文件读取 | Module 03 |
| `idea_generation` | 创意生成 | Module 04, 05 |
| `idea_critique` | 创意评审 | Module 04, 05 |
| `literature_review` | 文献综述 | Module 04 |
| `brainstorming` | 头脑风暴 | Module 05 |
| `hypothesis` | 假设生成 | Module 05 |
| `novelty_check` | 查新 | Module 05 |
| `research_planning` | 研究规划 | Module 06 |
| `experiment_design` | 实验设计 | Module 06, 07 |
| `system_design` | 系统设计 | Module 06 |
| `formula_derivation` | 公式推导 | Module 06 |
| `experiment_coding` | 实验编码 | Module 07, 08, 09 |
| `experiment_execution` | 实验执行 | Module 09 |
| `experiment_monitoring` | 实验监控 | Module 09 |
| `data_engineering` | 数据工程 | Module 08 |
| `result_analysis` | 结果分析 | Module 10 |
| `statistical_analysis` | 统计分析 | Module 10 |
| `figure_generation` | 图表生成 | Module 11 |
| `figure_prompt` | 图表提示词 | Module 11 |
| `color_expert` | 配色专家 | Module 11 |
| `diagram_generation` | 图表绘制 | Module 11 |
| `visualization` | 可视化 | Module 11 |
| `plotting` | 绑图 | Module 11 |
| `paper_writing` | 论文写作 | Module 12 |
| `citation_management` | 引用管理 | Module 13 |
| `citation_audit` | 引用审计 | Module 13 |
| `citation_verification` | 引用验证 | Module 13 |
| `paper_review` | 论文审稿 | Module 14 |
| `review_loop` | 审稿循环 | Module 14 |
| `argument_analysis` | 论证分析 | Module 14 |

### 能力查找机制

模块在运行时通过 capability 查找可用的 Skill。例如 Module 01 需要 `literature_search` 能力：

1. 查找注册表中 Module 01 下所有 `capability: literature_search` 的 Skill
2. 按优先级（required 优先）依次检查是否已安装
3. 第一个已安装的 Skill 被调用
4. 若全部未安装，查询 `fallback` 策略

---

## 4. 降级策略管理

> **核心原则**：模块不得自行决定降级行为，所有降级由 `dependency_policy.yaml` 统一管理。

### 4.1 策略文件位置

```
configs/dependency_policy.yaml
```

### 4.2 Skill 降级策略

`skill_registry.yaml` 中每个 Skill 的 `fallback` 字段引用 `dependency_policy.yaml` 中的策略键：

```yaml
# skill_registry.yaml 中的条目
- skill_name: light-literature-search
  fallback: "skill:light-literature-search"   # 引用策略键

# dependency_policy.yaml 中对应的策略
skill_fallback:
  "skill:light-literature-search":
    action: "llm_prompt"                        # 降级行为
    prompt_template: "literature_search_basic"  # 使用的提示词模板
    message: "light-literature-search Skill missing, using LLM basic search prompt"
```

### 4.3 降级行为类型

| action | 说明 | 适用场景 |
|--------|------|----------|
| `llm_prompt` | 使用 LLM 提示词替代 Skill 功能 | 写作、搜索类 Skill |
| `internal_implementation` | 使用内置实现替代 | arxiv 下载等有内置实现的场景 |
| `matplotlib` | 使用 matplotlib 内置绘图 | 图表生成类 Skill |
| `skip` | 跳过该功能 | 非必需的增强功能 |

### 4.4 模块查询降级策略的流程

模块通过 `pipeline.get_fallback()` 查询当前降级策略，而非自行判断：

```
模块运行 → 需要 Skill → 检查是否已安装
                              ↓ 已安装 → 调用 Skill
                              ↓ 未安装 → 查询 pipeline.get_fallback(fallback_key)
                                          ↓ 返回策略 → 执行降级行为
```

### 4.5 运行模式约束

`dependency_policy.yaml` 还定义了不同运行模式的约束：

| 模式 | 允许降级 | 要求真实 LLM | 允许 Mock |
|------|----------|-------------|-----------|
| `production` | 否 | 是 | 否 |
| `limited` | 是 | 否 | 否 |
| `development` | 是 | 否 | 是 |

---

## 5. 安装新 Skill

### 5.1 Skill 安装目录

TRAE Skill 安装在用户主目录下：

```
c:/Users/<user>/.trae-cn/skills/<skill_name>/
```

其中 `<user>` 是当前 Windows 用户名。例如用户名为 `langd`，则路径为：

```
c:/Users/langd/.trae-cn/skills/light-literature-search/
```

### 5.2 安装步骤

1. **获取 Skill 包**：从 TRAE Skill Store 或其他来源获取 Skill 文件包
2. **解压到安装目录**：
   ```
   c:/Users/<你的用户名>/.trae-cn/skills/<skill_name>/
   ```
   确保 Skill 目录下包含 `SKILL.md` 或等价入口文件
3. **更新注册表**（可选）：在 `infrastructure/skills/skill_registry.yaml` 中为对应模块添加 Skill 条目，填写所有 7 个字段
4. **验证安装**：运行 `python scripts/check_skills.py`

### 5.3 批量安装场景

如果是迁移到新机器，可从原机器的 `c:/Users/<旧用户名>/.trae-cn/skills/` 复制整个 `skills` 目录到新机器的对应路径下。

---

## 6. 运行 check_skills.py

### 6.1 命令

```bash
python scripts/check_skills.py
```

### 6.2 检测内容

该脚本会逐一检查注册表中的每个 Skill：

- Skill 是否存在于 TRAE skills 目录（`~/.trae-cn/skills/`）
- Skill 是否在 `installed_skills.json` 中已记录
- `install_path` 是否指向有效路径
- 版本号是否与注册表一致
- capability 是否已定义

### 6.3 输出报告

脚本在控制台输出检测结果，并在有缺失时生成 `Skill_Install_Request.md`：

```
============================================================
Skill Check Report
============================================================
Total skills: 48
Found: 35
Missing (required): 2
Status: FAIL

Missing skills:
  - light-literature-search (Module 01, capability: literature_search) [REQUIRED]
  - arxiv (Module 02, capability: paper_download) [REQUIRED]

Install request generated: Skill_Install_Request.md
```

`Skill_Install_Request.md` 包含：
- 缺失的必需 Skill 列表（含模块、能力、版本、降级策略）
- 每个缺失 Skill 的安装路径
- 安装步骤说明

### 6.4 检查逻辑说明

| 检查条件 | 判定 |
|----------|------|
| Skill 目录存在于 `~/.trae-cn/skills/` | Found |
| `install_path` 指向的路径存在 | Found |
| Skill 出现在 `installed_skills.json` | Found |
| 以上均不满足且 `required: true` | Missing (required) → FAIL |
| 以上均不满足且 `required: false` | 不计入 Missing（触发降级） |

---

## 7. 注册表示例

以下是 `skill_registry.yaml` 中 Module 01（文献检索）的完整条目示例：

```yaml
module_skill_mapping:
  "01":
    - skill_name: light-literature-search
      version: "1.0"
      source: "trae-skill-store"
      install_path: "c:/Users/<user>/.trae-cn/skills/light-literature-search"
      required: true
      capability: "literature_search"
      fallback: "skill:light-literature-search"
    - skill_name: nature-academic-search
      version: "1.0"
      source: "trae-skill-store"
      install_path: ""
      required: false
      capability: "literature_search"
      fallback: "skill:default"
    - skill_name: qinyan-paper-search
      version: "1.0"
      source: "trae-skill-store"
      install_path: ""
      required: false
      capability: "literature_search"
      fallback: "skill:default"
```

在上面的示例中：
- `light-literature-search` 是 Module 01 的**必需** Skill，有明确的安装路径
- `nature-academic-search` 和 `qinyan-paper-search` 是**可选** Skill，缺失时使用 `skill:default` 策略（即 skip）

对应的 `dependency_policy.yaml` 降级策略：

```yaml
skill_fallback:
  "skill:light-literature-search":
    action: "llm_prompt"
    prompt_template: "literature_search_basic"
    message: "light-literature-search Skill missing, using LLM basic search prompt"

  "skill:default":
    action: "skip"
    message: "Skill missing, skipping enhancement"
```

---

## 常见问题

**Q: 如何添加一个新的 Skill 到某个模块？**

在 `infrastructure/skills/skill_registry.yaml` 中对应模块编号下添加条目，填写全部 7 个字段。`fallback` 字段必须引用 `dependency_policy.yaml` 中已定义的策略键。

**Q: 必需 Skill 和可选 Skill 的区别？**

必需 Skill（`required: true`）缺失时 `check_skills.py` 报 FAIL，Pipeline 在 production 模式下无法启动。可选 Skill 缺失时自动触发降级策略，不影响流程。

**Q: install_path 中的 `<user>` 怎么处理？**

运行时自动替换为 `Path.home()` 的值。`check_skills.py` 检测到 `<user>` 时会将其替换为 `~/.trae-cn/skills` 路径。

**Q: 模块能自己决定降级吗？**

不能。模块必须通过 `pipeline.get_fallback()` 查询 `dependency_policy.yaml` 中的策略。这确保降级行为集中管理、可审计。
