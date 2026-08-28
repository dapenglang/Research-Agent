#!/usr/bin/env python
"""
Literature Quality Gate — checks paper count before pipeline entry.

Scans data/literature/pdf/ and data/literature/latex/ for valid papers.
Minimum requirement: 50 valid papers (PDF + LaTeX combined).

Usage:
    python scripts/check_literature.py
    python scripts/check_literature.py --min 50
    python scripts/check_literature.py --data-dir /path/to/data/literature

Exit codes:
    0 — sufficient papers (>= min_papers)
    1 — insufficient papers (< min_papers)
    2 — directory not found or error
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple


def find_project_root() -> Path:
    """Find project root by looking for the 'configs' directory."""
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


def count_pdfs(pdf_dir: Path) -> List[str]:
    """Count valid PDF files in the pdf directory."""
    pdfs: List[str] = []
    if not pdf_dir.exists():
        return pdfs
    for f in pdf_dir.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            size = f.stat().st_size
            if size > 1024:
                pdfs.append(f.name)
    return pdfs


def count_latex(latex_dir: Path) -> List[str]:
    """Count valid LaTeX source directories."""
    latex_papers: List[str] = []
    if not latex_dir.exists():
        return latex_papers
    for d in latex_dir.iterdir():
        if d.is_dir():
            tex_files = list(d.rglob("*.tex"))
            if tex_files:
                latex_papers.append(d.name)
    return latex_papers


def check_duplicates(pdfs: List[str], latex: List[str]) -> List[str]:
    """Detect potential duplicates by matching base names."""
    pdf_bases = set()
    for p in pdfs:
        base = os.path.splitext(p)[0].lower()
        pdf_bases.add(base)

    duplicates: List[str] = []
    for l in latex:
        if l.lower() in pdf_bases:
            duplicates.append(l)
    return duplicates


def generate_report(
    pdfs: List[str],
    latex: List[str],
    duplicates: List[str],
    min_papers: int,
    data_dir: Path,
) -> str:
    """Generate markdown report."""
    total = len(pdfs) + len(latex) - len(duplicates)
    sufficient = total >= min_papers
    missing = max(0, min_papers - total)

    lines: List[str] = []
    lines.append("# Literature Check Report")
    lines.append("")
    lines.append(f"**检查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**数据目录**: `{data_dir}`")
    lines.append(f"**最低要求**: {min_papers} 篇有效论文")
    lines.append("")

    lines.append("## 统计结果")
    lines.append("")
    lines.append(f"| 类型 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| PDF 文件 | {len(pdfs)} |")
    lines.append(f"| LaTeX 源码目录 | {len(latex)} |")
    lines.append(f"| 重复项 (PDF + LaTeX 同名) | {len(duplicates)} |")
    lines.append(f"| **有效论文总数** | **{total}** |")
    lines.append(f"| 最低要求 | {min_papers} |")
    lines.append(f"| 缺少数量 | {missing if missing > 0 else 0} |")
    lines.append("")

    if sufficient:
        lines.append("## 结论: PASS")
        lines.append("")
        lines.append(f"有效论文数量 ({total}) 满足最低要求 ({min_papers})，可以进入 Literature Intelligence 模块。")
    else:
        lines.append("## 结论: FAIL")
        lines.append("")
        lines.append(f"**有效论文数量不足！**")
        lines.append("")
        lines.append(f"- 当前数量: {total} 篇")
        lines.append(f"- 缺少数量: {missing} 篇")
        lines.append(f"- 要求目录: `data/literature/pdf/` 和 `data/literature/latex/`")
        lines.append("")
        lines.append("### 文件命名规则")
        lines.append("")
        lines.append("- PDF: `data/literature/pdf/{paper_id}.pdf`")
        lines.append("- LaTeX: `data/literature/latex/{paper_id}/main.tex`")
        lines.append("- paper_id 示例: `2401.00001`, `vlm_safety_survey`")
        lines.append("")
        lines.append("### 如何添加论文")
        lines.append("")
        lines.append("1. 从 arXiv 下载 PDF 放入 `data/literature/pdf/`")
        lines.append("2. 从 arXiv 下载 LaTeX 源码解压到 `data/literature/latex/{id}/`")
        lines.append("3. 参考 `docs/Literature_Preparation_Guide_CN.md` 获取详细说明")

    if pdfs:
        lines.append("")
        lines.append("## PDF 文件列表")
        lines.append("")
        for p in sorted(pdfs):
            lines.append(f"- {p}")

    if latex:
        lines.append("")
        lines.append("## LaTeX 源码目录列表")
        lines.append("")
        for l in sorted(latex):
            lines.append(f"- {l}/")

    if duplicates:
        lines.append("")
        lines.append("## 重复项")
        lines.append("")
        lines.append("以下论文同时存在 PDF 和 LaTeX 版本，已去重计数：")
        for d in sorted(duplicates):
            lines.append(f"- {d}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Literature Quality Gate Check")
    parser.add_argument("--min", type=int, default=50, help="Minimum papers required (default: 50)")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to data/literature directory")
    parser.add_argument("--output", type=str, default=None, help="Output report path")
    args = parser.parse_args()

    project_root = find_project_root()

    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = project_root / "data" / "literature"

    pdf_dir = data_dir / "pdf"
    latex_dir = data_dir / "latex"

    if not data_dir.exists():
        print(f"ERROR: Literature directory not found: {data_dir}")
        print("Please create: data/literature/pdf/ and data/literature/latex/")
        return 2

    pdfs = count_pdfs(pdf_dir)
    latex = count_latex(latex_dir)
    duplicates = check_duplicates(pdfs, latex)

    total = len(pdfs) + len(latex) - len(duplicates)

    report = generate_report(pdfs, latex, duplicates, args.min, data_dir)

    output_path = Path(args.output) if args.output else project_root / "Literature_Check_Report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    if total >= args.min:
        print(f"[PASS] Literature check passed: {total} papers (min: {args.min})")
        print(f"Report saved to: {output_path}")
        return 0
    else:
        print(f"[FAIL] Literature check failed: {total} papers (need {args.min})")
        print(f"Missing: {args.min - total} papers")
        print(f"Report saved to: {output_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
