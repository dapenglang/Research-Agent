# Research Agent v8.2.2 — 文献注册表指南

> 本文档说明文献注册表的结构、14 个字段含义、Module 01 与 Module 02 的注册表更新流程、去重机制以及维护方法。

---

## 目录

1. [注册表文件位置](#1-注册表文件位置)
2. [14 个字段说明](#2-14-个字段说明)
3. [Module 01 创建与更新注册表](#3-module-01-创建与更新注册表)
4. [Module 02 下载后更新注册表](#4-module-02-下载后更新注册表)
5. [去重机制](#5-去重机制)
6. [注册表维护与重建](#6-注册表维护与重建)

---

## 1. 注册表文件位置

文献注册表存储在 `data/literature/` 目录下，包含多个格式的文件：

```
data/literature/
├── literature_registry.csv          # CSV 格式注册表（主文件，由 Module 01/02 读写）
├── literature_registry.xlsx         # Excel 格式注册表（由 Module 01 生成，便于人工查看）
├── literature_database.json         # JSON 数据库（用于跨任务去重）
├── literature_keyword_statistics.xlsx  # 关键词命中统计
├── Literature_Download_Report.md   # 下载报告
├── pdf/                             # PDF 格式论文
│   ├── paper_001.pdf
│   └── ...
├── latex/                           # arXiv LaTeX 源码论文
│   ├── 2401.00001/
│   │   ├── main.tex
│   │   └── ...
│   └── ...
└── README.md                        # 本目录说明
```

### 文件关系

| 文件 | 创建者 | 用途 | 读/写 |
|------|--------|------|-------|
| `literature_registry.csv` | Module 01 | 主注册表，记录所有论文条目 | Module 01 写入，Module 02 读写 |
| `literature_registry.xlsx` | Module 01 | Excel 副本，供人工查看 | Module 01 写入 |
| `literature_database.json` | Module 01/02 | JSON 数据库，用于跨任务去重 | Module 01/02 读写 |

---

## 2. 14 个字段说明

注册表包含以下 14 个字段（Module 01 和 Module 02 中的 `REGISTRY_FIELDS` 列表）：

| # | 字段名 | 类型 | 写入时机 | 说明 |
|---|--------|------|----------|------|
| 1 | `research_task_id` | string | Module 01 搜索时 | 研究任务 ID，用于跨任务去重 |
| 2 | `paper_id` | string | Module 01 搜索时 | 论文唯一标识（arXiv ID 或 DOI） |
| 3 | `title` | string | Module 01 搜索时 | 论文标题 |
| 4 | `authors` | string | Module 01 搜索时 | 作者列表（逗号分隔字符串） |
| 5 | `year` | string | Module 01 搜索时 | 发表年份 |
| 6 | `venue` | string | Module 01 搜索时 | 发表期刊/会议 |
| 7 | `DOI` | string | Module 01 搜索时 | DOI 标识符 |
| 8 | `arxiv_id` | string | Module 01 搜索时 | arXiv ID |
| 9 | `keyword_source` | string | Module 01 搜索时 | 命中的关键词 |
| 10 | `search_query` | string | Module 01 搜索时 | 搜索查询语句 |
| 11 | `download_source` | string | Module 01/02 | 下载来源数据库（arxiv/semantic_scholar 等） |
| 12 | `file_path` | string | Module 02 下载后 | 下载文件在本地的路径 |
| 13 | `hash` | string | Module 02 下载后 | 下载文件的 SHA-256 哈希值 |
| 14 | `status` | string | Module 01/02 | 论文状态（见下表） |

### status 字段值

| status 值 | 含义 | 写入时机 |
|-----------|------|----------|
| `pending` | 已检索到但未下载 | Module 01 搜索后 |
| `duplicate` | 与已有数据库中的论文重复 | Module 01 搜索后 |
| `downloaded` | 已成功下载 PDF | Module 02 下载后 |
| `synthetic` | 下载失败，使用合成数据 | Module 02 下载失败后 |

### `research_task_id` 的作用

`research_task_id` 是 v8.2.2 新增的关键字段，用于跨任务去重。当多个研究任务检索到同一篇论文时，通过该字段可以追溯论文最初是哪个任务检索到的，避免重复下载。

---

## 3. Module 01 创建与更新注册表

Module 01（Literature Retrieval / 文献检索）在完成搜索后，调用 `_update_literature_registry()` 方法创建或更新注册表。

### 3.1 触发时机

Module 01 的 `execute()` 方法在以下步骤完成后触发注册表更新：
1. 关键词搜索完成（arXiv / Semantic Scholar / OpenReview）
2. 搜索结果去重完成（同批次内去重 + 与数据库已有论文去重）
3. 输出文件写入完成（paper_metadata.jsonl, download_queue.json 等）

### 3.2 更新流程

```
搜索完成
  ↓
加载已有注册表 (literature_registry.csv)
  ↓
获取已有 paper_id 集合
  ↓
遍历搜索结果中的每篇论文：
  ├── paper_id 已存在 → 跳过（不重复添加）
  └── paper_id 不存在 → 创建新条目
      ├── research_task_id = 当前任务 ID
      ├── paper_id / title / authors / year / venue / DOI / arxiv_id
      ├── keyword_source / search_query = 命中关键词
      ├── download_source = 来源数据库
      ├── file_path = ""（空，待 Module 02 填充）
      ├── hash = ""（空，待 Module 02 填充）
      └── status = "pending" 或 "duplicate"
  ↓
合并已有条目 + 新条目
  ↓
写入 CSV → literature_registry.csv
写入 XLSX → literature_registry.xlsx
更新 JSON → literature_database.json
```

### 3.3 JSON 数据库更新

Module 01 同时更新 `literature_database.json`，将新论文的 `paper_id` 和 `research_task_id` 写入 `papers` 数组：

```json
{
  "papers": [
    {
      "research_task_id": "task_001",
      "paper_id": "2401.00001",
      "title": "...",
      ...
    }
  ],
  "last_updated": "2026-08-15T10:30:00Z",
  "total_papers": 42,
  "schema_version": "1.0",
  "description": "Literature database for deduplication and quick lookup."
}
```

---

## 4. Module 02 下载后更新注册表

Module 02（Source Acquisition / 来源获取）在完成论文下载后，调用 `_update_registry_after_download()` 方法更新注册表中的下载相关字段。

### 4.1 触发时机

Module 02 的 `execute()` 方法在以下步骤完成后触发注册表更新：
1. 读取 `download_queue.json`（由 Module 01 生成）
2. 逐篇下载论文 PDF
3. 计算每个文件的 SHA-256 哈希值
4. 收集所有下载结果

### 4.2 更新流程

```
下载完成
  ↓
加载已有注册条目 (literature_registry.csv)
  ↓
按 paper_id 建立索引
  ↓
遍历每篇已下载论文：
  ├── paper_id 已存在于注册表 → 更新该条目：
  │   ├── file_path = 下载文件路径
  │   ├── hash = 文件 SHA-256 哈希
  │   ├── status = "downloaded"（成功）或 "synthetic"（失败）
  │   └── download_source = 下载来源
  └── paper_id 不在注册表中 → 创建新条目：
      ├── 填充全部 14 个字段
      ├── research_task_id = 上游 Module 01 传递的任务 ID
      ├── file_path / hash / status = 下载结果
      └── status = "downloaded" 或 "synthetic"
  ↓
写入 CSV → literature_registry.csv（覆盖整个文件）
```

### 4.3 哈希计算

Module 02 使用 `hashlib` 计算下载文件的 SHA-256 哈希：

```python
def _compute_file_hash(filepath: str) -> str:
    """计算文件的 SHA-256 哈希值。"""
    # 读取文件二进制内容 → 计算 SHA-256 → 返回十六进制字符串
```

哈希值用于：
- 验证文件完整性
- 检测重复文件（不同论文但相同内容的检测）

### 4.4 更新的字段

Module 02 只更新以下 4 个字段（不覆盖 Module 01 写入的其他字段）：

| 字段 | 更新值 |
|------|--------|
| `file_path` | 下载文件的本地绝对路径 |
| `hash` | 文件内容的 SHA-256 哈希值 |
| `status` | `"downloaded"`（成功）或 `"synthetic"`（失败） |
| `download_source` | 实际下载来源数据库 |

---

## 5. 去重机制

Research Agent 实现了两级去重机制：**搜索去重**和**下载去重**。

### 5.1 搜索去重（Module 01）

**机制**：基于 `literature_database.json` 的 `paper_id` 集合进行去重。

**流程**：
```
Module 01 开始搜索
  ↓
加载 literature_database.json
  ↓
提取已有 paper_id 集合 (existing_ids)
  ↓
搜索每个关键词（arXiv / Semantic Scholar / OpenReview）
  ↓
合并所有搜索结果
  ↓
遍历每篇论文：
  ├── paper_id 在本批次 seen_ids 中 → 跳过（批次内重复）
  ├── paper_id 在 existing_ids 中 → 标记 status = "duplicate"，仍加入列表
  └── paper_id 是新的 → 标记 status = "pending"
  ↓
截断到 max_papers 上限
  ↓
生成 download_queue（仅含 pdf_url 的论文）
```

**特点**：
- 批次内去重：同一批搜索结果中，相同 `paper_id` 只保留第一条
- 跨任务去重：与 `literature_database.json` 中已有的 `paper_id` 比对，重复的标记为 `duplicate`
- 重复论文仍会出现在结果中（标记为 `duplicate`），但不会被加入注册表新条目

### 5.2 下载去重（Module 02）

**机制**：基于 `literature_registry.csv` 中 `status` 字段进行去重。

**流程**：
```
Module 02 开始下载
  ↓
加载 literature_registry.csv 所有条目
  ↓
提取 status == "downloaded" 的 paper_id 集合 (downloaded_ids)
  ↓
读取 download_queue.json
  ↓
遍历队列中每篇论文：
  ├── paper_id 在 downloaded_ids 中 → 跳过（已下载过）
  └── paper_id 不在 downloaded_ids 中 → 执行下载
  ↓
下载完成后更新注册表（file_path / hash / status）
```

**特点**：
- 只跳过 `status == "downloaded"` 的论文
- `status == "pending"` 的论文会被下载
- `status == "synthetic"` 的论文会被重新尝试下载
- `status == "duplicate"` 的论文如果在下载队列中也会被尝试下载

### 5.3 去重机制对比

| 维度 | 搜索去重 | 下载去重 |
|------|----------|----------|
| 所在模块 | Module 01 | Module 02 |
| 数据源 | `literature_database.json` | `literature_registry.csv` |
| 判断依据 | `paper_id` 是否存在 | `status` 是否为 `downloaded` |
| 目的 | 避免重复检索和注册 | 避免重复下载同一文件 |
| 层级 | 跨任务去重 | 跨任务去重 |

---

## 6. 注册表维护与重建

### 6.1 日常维护

注册表由 Module 01 和 Module 02 自动维护，一般无需手动干预。以下情况需要手动操作：

| 场景 | 操作 |
|------|------|
| 论文文件被手动删除 | 将对应条目的 `status` 改为 `pending`，`file_path` 清空 |
| 论文文件被移动 | 更新对应条目的 `file_path` |
| 需要重新下载某篇论文 | 将 `status` 改为 `pending` |
| 注册表损坏 | 从 `literature_database.json` 重建（见下文） |

### 6.2 检查文献完整性

运行文献检查脚本：

```bash
python scripts/check_literature.py
```

该脚本会检查：
- `pdf/` 目录下的 PDF 文件数量
- `latex/` 目录下的 LaTeX 源码目录数量
- 最低要求：50 篇有效论文（PDF + LaTeX 合计，无重复）

### 6.3 从 JSON 数据库重建 CSV 注册表

如果 `literature_registry.csv` 损坏或丢失，但 `literature_database.json` 完好，可手动重建：

```python
import csv
import json
from pathlib import Path

literature_dir = Path("data/literature")

# 从 JSON 加载
with open(literature_dir / "literature_database.json", "r", encoding="utf-8") as f:
    db = json.load(f)

FIELDS = [
    "research_task_id", "paper_id", "title", "authors", "year",
    "venue", "DOI", "arxiv_id", "keyword_source", "search_query",
    "download_source", "file_path", "hash", "status",
]

# 重建 CSV
with open(literature_dir / "literature_registry.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    for paper in db.get("papers", []):
        writer.writerow({k: paper.get(k, "") for k in FIELDS})

print(f"重建完成，共 {len(db.get('papers', []))} 条记录")
```

### 6.4 完全重建注册表

如果 CSV 和 JSON 都丢失，需要重新运行 Module 01：

1. 清空注册表：
   ```bash
   # CSV 重置为表头
   echo "research_task_id,paper_id,title,authors,year,venue,DOI,arxiv_id,keyword_source,search_query,download_source,file_path,hash,status" > data/literature/literature_registry.csv

   # JSON 重置为空
   ```
2. 重新运行 Module 01 搜索
3. 重新运行 Module 02 下载

### 6.5 检查注册表一致性

验证 CSV 注册表与 PDF/LaTeX 文件目录的一致性：

```python
import csv
from pathlib import Path

literature_dir = Path("data/literature")

# 读取注册表中已下载的论文
downloaded = []
with open(literature_dir / "literature_registry.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("status") == "downloaded" and row.get("file_path"):
            downloaded.append(row["file_path"])

# 检查文件是否存在
missing = [p for p in downloaded if not Path(p).exists()]
print(f"注册表记录已下载: {len(downloaded)} 篇")
print(f"文件缺失: {len(missing)} 篇")
for m in missing:
    print(f"  缺失: {m}")
```

---

## 常见问题

**Q: research_task_id 有什么作用？**

`research_task_id` 用于跨任务去重。当任务 A 和任务 B 都检索到同一篇论文时，通过该字段可以追溯论文最初由哪个任务检索到，避免在注册表中创建重复条目。Module 01 在搜索去重时会检查 `literature_database.json` 中的已有 `paper_id`，重复的标记为 `duplicate` 状态。

**Q: Module 01 和 Module 02 分别写哪些字段？**

Module 01 写入全部 14 个字段，但 `file_path`、`hash` 为空，`status` 为 `pending` 或 `duplicate`。Module 02 只更新 `file_path`、`hash`、`status`、`download_source` 这 4 个字段，不覆盖 Module 01 写入的其他字段。

**Q: 下载去重为什么只检查 status 为 downloaded 的？**

因为 `pending` 状态表示论文已检索到但尚未下载，需要尝试下载；`synthetic` 状态表示上次下载失败用了合成数据，可以重试。只有 `downloaded` 表示已成功获取真实文件，才需要跳过。

**Q: 如何手动添加一篇论文到注册表？**

在 `literature_registry.csv` 中添加一行，填写所有 14 个字段。`paper_id` 必须唯一，`research_task_id` 填写对应的任务 ID。如果文件已手动放入 `pdf/` 目录，将 `status` 设为 `downloaded`，`file_path` 填入实际路径。

**Q: literature_database.json 和 literature_registry.csv 有什么区别？**

`literature_registry.csv` 是主注册表，包含全部 14 个字段的详细信息。`literature_database.json` 是轻量级数据库，主要用于 Module 01 的搜索去重快速查询。两者由 Module 01 同时维护，保持同步。如果 CSV 丢失但 JSON 完好，可以从 JSON 重建 CSV。
