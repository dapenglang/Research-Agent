# Literature Directory

This directory stores research papers for the Research Agent pipeline.

## Structure

```
data/literature/
├── pdf/        # PDF format papers
│   ├── paper_001.pdf
│   ├── paper_002.pdf
│   └── ...
├── latex/      # arXiv LaTeX source papers
│   ├── 2401.00001/
│   │   ├── main.tex
│   │   └── ...
│   ├── 2401.00002/
│   │   ├── main.tex
│   │   └── ...
│   └── ...
└── README.md   # This file
```

## Rules

1. PDF files go in `pdf/` — one paper per file, named `*.pdf`
2. LaTeX sources go in `latex/` — one paper per subdirectory, each containing at least one `.tex` file
3. Minimum requirement: **50 valid papers** (PDF + LaTeX combined, no duplicates)
4. Papers are counted automatically by `scripts/check_literature.py`

## Naming Convention

- PDF: `{arxiv_id_or_short_title}.pdf` (e.g., `2401.00001.pdf`, `vlm_safety_survey.pdf`)
- LaTeX: `{arxiv_id}/` directory containing `main.tex` or equivalent

## How to Add Papers

### Option A: Manual Download
1. Download PDFs from arXiv, Semantic Scholar, etc.
2. Place them in `data/literature/pdf/`

### Option B: arXiv LaTeX Source
1. Download LaTeX source from arXiv (e.g., `arXiv:2401.00001`)
2. Extract to `data/literature/latex/2401.00001/`
3. Ensure at least one `.tex` file is in the directory

### Option C: Use Module 01 (Automated)
Module 01 (Literature Retrieval) can automatically download papers when configured with API keys.
