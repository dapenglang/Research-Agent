# 论文准备指南

> 本文档说明如何为 Research Agent 准备研究论文，包括下载、组织和检查。

---

## 目录

1. [论文要求](#1-论文要求)
2. [目录结构](#2-目录结构)
3. [下载论文](#3-下载论文)
4. [文件命名规则](#4-文件命名规则)
5. [检查论文数量](#5-检查论文数量)
6. [常见问题](#6-常见问题)

---

## 1. 论文要求

| 要求 | 说明 |
|------|------|
| 最低数量 | **50 篇**有效论文 |
| 支持格式 | PDF 文件 和/或 arXiv LaTeX 源码 |
| 文件大小 | PDF > 1KB（排除空文件） |
| LaTeX 要求 | 每篇论文一个目录，包含至少一个 `.tex` 文件 |

### 什么算"有效论文"？

- **PDF**: `data/literature/pdf/` 目录下，后缀为 `.pdf`，文件大小 > 1KB
- **LaTeX**: `data/literature/latex/` 目录下的子目录，包含至少一个 `.tex` 文件
- **去重**: 如果同一论文同时存在 PDF 和 LaTeX 版本，按一篇计算

---

## 2. 目录结构

```
data/
└── literature/
    ├── pdf/                    # PDF 格式论文
    │   ├── 2401.00001.pdf
    │   ├── 2401.00002.pdf
    │   ├── vlm_safety_survey.pdf
    │   └── ...                 # 至少 50 个 PDF 文件
    ├── latex/                  # LaTeX 源码论文
    │   ├── 2401.00003/
    │   │   ├── main.tex
    │   │   ├── figures/
    │   │   └── ...
    │   ├── 2401.00004/
    │   │   ├── paper.tex
    │   │   └── ...
    │   └── ...                 # 或 LaTeX 目录
    └── README.md               # 说明文件
```

---

## 3. 下载论文

### 方法 1: 手动下载 PDF（推荐新手）

1. **搜索论文**:
   - arXiv: https://arxiv.org
   - Semantic Scholar: https://www.semanticscholar.org
   - Google Scholar: https://scholar.google.com

2. **下载 PDF**:
   - 在 arXiv 论文页面点击 "PDF" 下载
   - 或右键 "Save link as..." 保存

3. **放入目录**:
   ```
   data/literature/pdf/2401.00001.pdf
   data/literature/pdf/2401.00002.pdf
   ```

### 方法 2: 下载 arXiv LaTeX 源码

1. **在 arXiv 论文页面**:
   - 点击 "Download source" 下载 `.tar.gz` 文件
   - 或访问 `https://arxiv.org/e-print/2401.00001`

2. **解压到目录**:
   ```bash
   # Windows: 使用 7-Zip 或 WinRAR 解压
   # 将内容解压到 data/literature/latex/2401.00001/
   
   # Linux/Mac:
   mkdir -p data/literature/latex/2401.00001
   tar -xzf 2401.00001.tar.gz -C data/literature/latex/2401.00001/
   ```

3. **验证结构**:
   ```
   data/literature/latex/2401.00001/
   ├── main.tex          # 必须有至少一个 .tex 文件
   ├── figures/
   └── ...
   ```

### 方法 3: 批量下载（高级）

使用 Python 脚本批量从 arXiv 下载：

```python
import arxiv
import os

search = arxiv.Search(
    query="vision-language model safety",
    max_results=60,
    sort_by=arxiv.SortCriterion.Relevance
)

pdf_dir = "data/literature/pdf"
for paper in search.results():
    paper.download_pdf(dirpath=pdf_dir, filename=f"{paper.entry_id.split('/')[-1]}.pdf")
    print(f"Downloaded: {paper.title}")
```

> 安装 arxiv 包: `pip install arxiv`

### 方法 4: 使用 Module 01 自动检索

Research Agent 的 Module 01 (Literature Retrieval) 支持自动检索和下载论文。配置 Semantic Scholar API Key 后可使用：

```yaml
# tasks/task_001.yaml
literature:
  arxiv:
    download_pdf: true
    download_source: true
```

---

## 4. 文件命名规则

### PDF 文件命名

| 命名方式 | 示例 | 说明 |
|---------|------|------|
| arXiv ID | `2401.00001.pdf` | 推荐，便于追溯 |
| 短标题 | `vlm_safety_survey.pdf` | 可读性好 |
| 作者+年份 | `zhang2024_safety.pdf` | 学术风格 |

### LaTeX 目录命名

| 命名方式 | 示例 | 说明 |
|---------|------|------|
| arXiv ID | `2401.00003/` | 推荐 |
| 短标题 | `vlm_safety_2024/` | 可读性好 |

### 注意事项

- **不要使用中文**文件名
- **不要使用空格**，用下划线 `_` 替代
- **不要使用特殊字符**: `<>:"/\|?*`
- PDF 和 LaTeX 同名时会去重，建议统一命名

---

## 5. 检查论文数量

### 5.1 使用检查脚本

```bash
python scripts/check_literature.py
```

### 5.2 输出示例

**论文充足（>= 50篇）:**
```
[PASS] Literature check passed: 62 papers (min: 50)
Report saved to: Literature_Check_Report.md
```

**论文不足（< 50篇）:**
```
[FAIL] Literature check failed: 12 papers (need 50)
Missing: 38 papers
Report saved to: Literature_Check_Report.md
```

### 5.3 自定义最低数量

```bash
# 检查是否达到 100 篇
python scripts/check_literature.py --min 100
```

### 5.4 指定数据目录

```bash
python scripts/check_literature.py --data-dir /path/to/literature
```

### 5.5 Literature_Check_Report.md

检查脚本会生成详细的 Markdown 报告，包含：
- PDF 数量
- LaTeX 数量
- 重复项
- 有效论文总数
- 缺少数量
- 文件列表
- 添加论文的方法说明

---

## 6. 常见问题

### Q: 论文不足 50 篇会怎样？

Pipeline 在进入 Module 03 (Literature Intelligence) 之前会检查论文数量。如果不足 50 篇：
- Pipeline **停止执行**
- 返回 `status: "blocked"` 
- 输出明确的错误提示，包含当前数量和缺少数量

### Q: 可以用其他格式（如 Word、HTML）吗？

目前只支持 PDF 和 LaTeX。如果需要其他格式，可以：
- 将 Word 转为 PDF
- 将 HTML 转为 PDF

### Q: PDF 文件大小有限制吗？

最小 1KB（排除空文件和损坏文件）。没有上限，但建议单文件不超过 50MB。

### Q: LaTeX 目录中没有 main.tex 怎么办？

系统会扫描目录中所有 `.tex` 文件，不要求文件名必须是 `main.tex`。只要有至少一个 `.tex` 文件即可。

### Q: 如何快速获取 50 篇论文？

1. 在 arXiv 搜索你的研究关键词
2. 按 Relevance 排序
3. 下载前 50-60 篇的 PDF
4. 或使用批量下载脚本（见方法 3）

### Q: 重复的论文会怎样？

如果同一论文同时存在 PDF 和 LaTeX 版本（根据文件名匹配），系统会自动去重，只计算一次。

### Q: Pipeline 如何使用这些论文？

- Module 01 (Literature Retrieval): 检索和下载论文
- Module 02 (Source Acquisition): 获取论文源文件
- Module 02.5 (Paper Asset Intelligence): 提取论文图片
- Module 03 (Literature Intelligence): 从论文中提取结构化知识

论文存放在 `data/literature/` 中供这些模块使用。

### Q: 可以跳过文献检查吗？

可以，但**仅限开发测试**：

```python
orchestrator = PipelineOrchestrator(
    'tasks/task_001.yaml',
    skip_gates=True
)
```

> **警告**: 跳过门控会导致 Pipeline 在论文不足时仍运行，可能导致输出质量低下。
