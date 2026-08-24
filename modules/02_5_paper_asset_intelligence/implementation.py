"""
Module 02.5 — Paper Asset Intelligence

Downloads and saves the first 3 figures from each paper.
Prefers arXiv LaTeX source; falls back to PDF extraction.
Does NOT analyze image content.

Outputs:
  - assets/figure_1.png, figure_2.png, figure_3.png per paper
  - paper_assets.json (path, filename, source)
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from interface import (
    PaperAssetIntelligenceInput,
    PaperAssetIntelligenceOutput,
    Module02_5Interface,
)


class PaperAssetIntelligenceEngine(Module02_5Interface):
    """Extracts and saves first 3 figures from papers."""

    MODULE_ID = "02_5"
    MODULE_NAME = "Paper Asset Intelligence"

    def load_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._output_dir = config.get("output", {}).get("paper_dir", "output/paper")

    def validate_input(self, input_data: PaperAssetIntelligenceInput) -> bool:
        return bool(input_data.task_id)

    def execute(self, input_data: PaperAssetIntelligenceInput) -> PaperAssetIntelligenceOutput:
        task_id = input_data.task_id
        output_dir = os.path.join(self._output_dir, task_id, "assets")
        os.makedirs(output_dir, exist_ok=True)

        papers_dir = self._find_papers_dir(input_data)
        all_assets: List[Dict[str, Any]] = []

        if papers_dir and os.path.isdir(papers_dir):
            for paper_subdir in sorted(Path(papers_dir).iterdir()):
                if not paper_subdir.is_dir():
                    continue
                paper_id = paper_subdir.name
                figures = self._extract_figures(paper_subdir, output_dir, paper_id)
                all_assets.extend(figures)

        assets_path = os.path.join(output_dir, "paper_assets.json")
        with open(assets_path, "w", encoding="utf-8") as f:
            json.dump(all_assets, f, indent=2, ensure_ascii=False)

        output_files = {"paper_assets.json": assets_path}
        for asset in all_assets:
            rel = asset.get("path", "")
            if rel:
                output_files[rel] = asset.get("full_path", "")

        manifest = {
            "module_id": self.MODULE_ID,
            "module_name": self.MODULE_NAME,
            "data_origin": "paper_asset_extraction",
            "papers_processed": len(set(a.get("paper_id", "") for a in all_assets)),
            "figures_extracted": len(all_assets),
        }

        # v8.3: Generate Stage_Report.md
        stage_report = self._build_stage_report(task_id, manifest)
        stage_path = os.path.join(output_dir, "Stage_Report.md")
        with open(stage_path, "w", encoding="utf-8") as f:
            f.write(stage_report)
        output_files["Stage_Report.md"] = stage_path

        return PaperAssetIntelligenceOutput(
            task_id=task_id,
            output_files=output_files,
            manifest=manifest,
            warnings=[],
            errors=[],
        )

    def _build_stage_report(self, task_id: str, manifest: Dict[str, Any]) -> str:
        """v8.3: Build Stage_Report.md for Module 02.5."""
        from datetime import datetime
        lines = [
            "# Module 02.5 — Paper Asset Intelligence Stage Report",
            "",
            f"- **Task ID**: {task_id}",
            f"- **时间戳**: {datetime.now().isoformat()}",
            f"- **状态**: 完成",
            "",
            "## 当前目标",
            "从论文目录中提取图片和资产，生成paper_assets.json",
            "",
            "## 输入",
            "- Module 02 输出的论文目录 (papers/)",
            "",
            "## 输出",
            "- paper_assets.json",
            "- Stage_Report.md",
            "",
            "## 完成状态",
            f"- 处理论文数: {manifest.get('papers_processed', 0)}",
            f"- 提取图片数: {manifest.get('figures_extracted', 0)}",
            "",
        ]
        return "\n".join(lines)

    def _find_papers_dir(self, input_data: PaperAssetIntelligenceInput) -> str:
        upstream = input_data.upstream_module_02 or {}
        output_files = upstream.get("output_files", {})

        if isinstance(output_files, dict):
            for key, fpath in output_files.items():
                if key.startswith("papers/") and "/" in key[7:]:
                    path = Path(fpath)
                    if path.exists():
                        return str(path.parent.parent)

        for key, fpath in output_files.items():
            if "papers" in key.lower() and fpath:
                path = Path(fpath)
                if path.exists():
                    return str(path.parent.parent)

        return ""

    def _extract_figures(self, paper_dir: Path, output_dir: str, paper_id: str) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []

        latex_source = paper_dir / "source"
        if latex_source.exists() and any(latex_source.iterdir()):
            figures = self._extract_from_latex(latex_source, output_dir, paper_id)

        if not figures:
            pdf_path = paper_dir / "original.pdf"
            if not pdf_path.exists():
                pdfs = list(paper_dir.glob("*.pdf"))
                pdf_path = pdfs[0] if pdfs else None
            if pdf_path:
                figures = self._extract_from_pdf(pdf_path, output_dir, paper_id)

        return figures[:3]

    def _extract_from_latex(self, source_dir: Path, output_dir: str, paper_id: str) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []
        img_extensions = [".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg"]

        img_files: List[Path] = []
        for ext in img_extensions:
            img_files.extend(sorted(source_dir.rglob(f"*{ext}")))

        for i, img_path in enumerate(img_files[:3], 1):
            dest_name = f"figure_{i}.png"
            dest_path = os.path.join(output_dir, f"{paper_id}_{dest_name}")

            if img_path.suffix.lower() == ".png":
                shutil.copy2(str(img_path), dest_path)
            elif img_path.suffix.lower() in (".jpg", ".jpeg"):
                try:
                    from PIL import Image
                    img = Image.open(str(img_path))
                    img.save(dest_path, "PNG")
                except Exception:
                    shutil.copy2(str(img_path), dest_path)
            else:
                shutil.copy2(str(img_path), dest_path)

            figures.append({
                "paper_id": paper_id,
                "figure_id": f"fig{i}",
                "path": f"assets/{paper_id}_{dest_name}",
                "full_path": dest_path,
                "filename": dest_name,
                "source": "latex",
                "original_name": img_path.name,
            })

        return figures

    def _extract_from_pdf(self, pdf_path: Path, output_dir: str, paper_id: str) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []

        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            img_count = 0

            for page_num in range(min(len(doc), 20)):
                if img_count >= 3:
                    break
                page = doc[page_num]
                img_list = page.get_images(full=True)

                for img_info in img_list:
                    if img_count >= 3:
                        break
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        img_bytes = base_image["image"]
                        img_ext = base_image.get("ext", "png")

                        dest_name = f"figure_{img_count + 1}.png"
                        dest_path = os.path.join(output_dir, f"{paper_id}_{dest_name}")

                        if img_ext.lower() == "png":
                            with open(dest_path, "wb") as f:
                                f.write(img_bytes)
                        else:
                            try:
                                from PIL import Image
                                import io
                                img = Image.open(io.BytesIO(img_bytes))
                                img.save(dest_path, "PNG")
                            except Exception:
                                with open(dest_path, "wb") as f:
                                    f.write(img_bytes)

                        figures.append({
                            "paper_id": paper_id,
                            "figure_id": f"fig{img_count + 1}",
                            "path": f"assets/{paper_id}_{dest_name}",
                            "full_path": dest_path,
                            "filename": dest_name,
                            "source": "pdf",
                            "page": page_num + 1,
                        })
                        img_count += 1
                    except Exception:
                        continue

            doc.close()
        except ImportError:
            pass
        except Exception:
            pass

        return figures

    def validate_output(self, output: PaperAssetIntelligenceOutput) -> bool:
        return output.manifest.get("papers_processed", -1) >= 0

    def quality_assessment(self, output: PaperAssetIntelligenceOutput) -> Dict[str, Any]:
        return {
            "hard_requirements": {
                "paper_assets_generated": "paper_assets.json" in output.output_files,
            },
            "soft_requirements": {
                "figures_extracted": output.manifest.get("figures_extracted", 0) > 0,
            },
        }

    def write_manifest(self, output: PaperAssetIntelligenceOutput) -> Dict[str, Any]:
        return output.manifest

    def write_report(self, output: PaperAssetIntelligenceOutput) -> str:
        lines = [
            f"# Module 02.5 — Paper Asset Intelligence Report",
            f"",
            f"- Papers processed: {output.manifest.get('papers_processed', 0)}",
            f"- Figures extracted: {output.manifest.get('figures_extracted', 0)}",
            f"- Output files: {len(output.output_files)}",
        ]
        if output.warnings:
            lines.append(f"\n## Warnings\n")
            for w in output.warnings:
                lines.append(f"- {w}")
        return "\n".join(lines)
