# Human Intervention Request — Research Agent v8.2.2 Pipeline

## 一、当前问题

### 1.1 阻塞性问题 (BLOCKER)

| 编号 | 模块 | 问题 | 严重性 |
|------|------|------|--------|
| B-01 | Module 08 | 实验引擎后端 'default' 未注册 | 阻塞 |
| B-02 | Module 01 | 139篇PDF已下载但 literature_database.json 为空 | 阻塞 |
| B-03 | Module 13 | references.bib 为空文件 (0 bytes) | 阻塞 |
| B-04 | Module 11 | 所有图表为空占位符 | 严重 |

### 1.2 Module 08 详细说明

**错误信息**:
```
"Method backend 'default' not registered. Available: ['samra']"
```

**原因分析**:
- `implementation.py` 第40行: `self._method_name = config.get("experiment", {}).get("method", "default")`
- 配置文件中 `experiment.method` 未设置或设为 "default"
- `backend_registry` 中仅注册了 "samra" 后端
- 当 `backend_registry.get("default")` 被调用时返回 None，导致后续操作失败

**影响**: Module 08 无法执行合成实验，导致:
- 所有 5 个 Claim 均为 inconclusive（无实验数据）
- Module 11 图表为空占位符（无数据源）
- 论文中的实验数据为 LLM 虚构（非真实）

---

## 二、缺少信息

### 2.1 LLM 配置

| 项目 | 当前状态 | 需要的信息 |
|------|---------|-----------|
| Ollama 服务 | 运行中（后台进程） | 确认端口 11434 可访问 |
| OpenAI API | 未配置 | OPENAI_API_KEY 环境变量 |
| DeepSeek API | 未配置 | DEEPSEEK_API_KEY 环境变量 |
| LLM 使用追踪 | 不完整 | Module 03/05/06/07/10 无 LLM 调用记录 |

### 2.2 实验配置

| 项目 | 当前值 | 需要确认 |
|------|--------|---------|
| experiment.method | "default" (未注册) | 改为 "samra" 或注册 "default" 后端 |
| experiment.synthetic.num_samples | 1000 | 是否足够 |
| experiment.synthetic.seed | 42 | 是否需要更改 |

### 2.3 文献索引

| 项目 | 当前状态 | 需要的信息 |
|------|---------|-----------|
| PDF 文件数 | 139 | 已下载到 data/literature/pdf/ |
| 索引论文数 | 0 | literature_database.json 为空 |
| Markdown 解析 | 0 | 无 PDF→Markdown 转换 |
| LaTeX 源码 | 0 | 无 arXiv LaTeX 下载 |

---

## 三、用户补充方式

### 3.1 修复 Module 08（推荐方案 A：修改配置）

**方式**: 修改研究任务配置文件

**文件**: `D:\Research Agent\Research_Agent_v3\configs\research_task_vlm_safety.yaml`

**修改内容**:
```yaml
experiment:
  method: "samra"  # 将 "default" 改为 "samra"
  synthetic:
    num_samples: 1000
    seed: 42
```

**或方案 B**: 修改代码注册 default 后端

**文件**: `D:\Research Agent\Research_Agent_v3\modules\08_synthetic_experiment_engine\implementation.py`

**修改内容**: 在 `execute` 方法中添加 fallback:
```python
def execute(self, input_data: SyntheticExperimentInput) -> SyntheticExperimentOutput:
    backend = backend_registry.get(self._method_name.lower())
    if backend is None:
        # Fallback to samra if default not registered
        backend = backend_registry.get("samra")
    if backend is None:
        raise RuntimeError(f"No experiment backend available. Tried: {self._method_name}, samra")
```

### 3.2 修复文献索引

**方式**: 重新运行 Module 01 或手动构建索引

**手动补充**:
1. 扫描 `data/literature/pdf/` 目录下所有 PDF
2. 从文件名提取 arXiv ID 和元数据
3. 构建 `literature_database.json`:
```json
{
  "papers": [
    {
      "paper_id": "arxiv_2401.00001",
      "title": "Paper Title",
      "authors": ["Author1", "Author2"],
      "year": 2024,
      "arxiv_id": "2401.00001",
      "pdf_path": "data/literature/pdf/2401.00001.pdf",
      "keywords": ["VLM safety", "adversarial defense"]
    }
  ]
}
```

**保存位置**: `D:\Research Agent\Research_Agent_v3\data\literature\literature_database.json`

### 3.3 修复引用生成

**方式**: 手动补充 references.bib

**文件**: `D:\Research Agent\Research_Agent_v3\output\references\VLM_Safety_001\references.bib`

**要求**:
- 至少 30 篇引用
- 近 4 年（2022-2026）不少于 20 篇
- 格式: BibTeX

**示例**:
```bibtex
@inproceedings{example2024,
  title={Title},
  author={Author, A.},
  booktitle={Proceedings of CVPR},
  year={2024}
}
```

### 3.4 配置 LLM（可选）

**方式 A**: 确认 Ollama 运行
```bash
ollama list
# 应显示: gemma4:26b, deepseek-r1:8b
```

**方式 B**: 配置 API 密钥
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
$env:DEEPSEEK_API_KEY = "sk-..."
```

**验证**:
```bash
python scripts/check_llm.py
```

---

## 四、文件位置

| 文件 | 路径 | 用途 |
|------|------|------|
| Pipeline 状态 | `D:\Research Agent\Research_Agent_v3\state\VLM_Safety_001\research_state.yaml` | 查看模块状态 |
| 研究任务配置 | `D:\Research Agent\Research_Agent_v3\configs\research_task_vlm_safety.yaml` | 修改实验方法 |
| LLM 配置 | `D:\Research Agent\Research_Agent_v3\configs\llm.yaml` | 修改 LLM 设置 |
| 文献数据库 | `D:\Research Agent\Research_Agent_v3\data\literature\literature_database.json` | 手动补充索引 |
| 引用文件 | `D:\Research Agent\Research_Agent_v3\output\references\VLM_Safety_001\references.bib` | 手动补充引用 |
| 实验引擎 | `D:\Research Agent\Research_Agent_v3\modules\08_synthetic_experiment_engine\implementation.py` | 修复后端注册 |
| 论文输出 | `D:\Research Agent\Research_Agent_v3\output\paper\VLM_Safety_001\paper.md` | 论文文件 |
| 验证报告 | `C:\Users\langd\Downloads\Research_Agent_End_to_End_Validation_Report.md` | 完整验证报告 |

---

## 五、继续运行方法

### 5.1 修复后重新运行完整 Pipeline

```bash
cd "D:\Research Agent\Research_Agent_v3"
conda activate research_agent_v3
python run_vlm_safety.py
```

### 5.2 仅重新运行失败模块

```bash
cd "D:\Research Agent\Research_Agent_v3"
conda activate research_agent_v3
python -c "
from modules.08_synthetic_experiment_engine.implementation import SyntheticExperimentEngine
engine = SyntheticExperimentEngine()
# 需要先修复配置或代码
"
```

### 5.3 手动补充后继续

1. 按上述方式手动补充 `literature_database.json` 和 `references.bib`
2. 修改 `research_task_vlm_safety.yaml` 中的 `experiment.method` 为 `"samra"`
3. 重新运行 Pipeline: `python run_vlm_safety.py`
4. 或使用 `--resume` 参数从失败模块继续（如支持）

### 5.4 验证修复

```bash
# 验证 Module 08 后端
python -c "from Research_Agent_v3.adapters.method_backend_interface import backend_registry; print(backend_registry.list_backends())"

# 验证文献索引
python -c "import json; db = json.load(open('data/literature/literature_database.json')); print(f'Papers: {len(db.get(\"papers\", []))}')"

# 验证引用
python -c "import os; size = os.path.getsize('output/references/VLM_Safety_001/references.bib'); print(f'references.bib: {size} bytes')"
```

---

*生成时间: 2026-08-18*
*Pipeline: Research Agent v8.2.2 End-to-End Validation*
*任务: VLM_Safety_001*
