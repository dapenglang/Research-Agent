#!/usr/bin/env python
"""
Build script v8.3.1: Generate 15 independent module packages as ZIP files.

Each package contains:
  - src/ (module implementation, interface, schema, validator)
  - shared/ (LLM runtime, providers, adapters, infrastructure)
  - configs/ (llm.yaml, providers.yaml, llm_routing.yaml, module_config.yaml)
  - scripts/ (environment_check.py)
  - input/ and output/ directories
  - START_HERE.md (Chinese quickstart guide)
  - README.md

Usage:
    conda activate research_agent_v3
    python build_packages_v831.py
"""

import hashlib
import os
import shutil
import zipfile
import json
from datetime import datetime
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parent
RELEASES_DIR = Path("D:/Research Agent/releases")
BUILD_DIR = V3_ROOT / "_build_v831"

MODULES = [
    {
        "id": "01", "name": "Literature_Retrieval", "name_cn": "文献检索",
        "source_dirs": ["modules/01_literature_retrieval"],
        "upstream": [], "downstream": ["02", "03"],
        "inputs": ["research_task.yaml"],
        "outputs": ["literature_database.json", "literature_registry.csv", "literature_registry.xlsx", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "02", "name": "Paper_Acquisition", "name_cn": "论文获取与解析",
        "source_dirs": ["modules/02_source_acquisition", "modules/02_5_paper_asset_intelligence"],
        "upstream": ["01"], "downstream": ["03"],
        "inputs": ["literature_database.json"],
        "outputs": ["paper_assets.json", "figure_analysis.json", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "03", "name": "Literature_Intelligence", "name_cn": "文献智能分析",
        "source_dirs": ["modules/03_literature_intelligence"],
        "upstream": ["02"], "downstream": ["04", "05"],
        "inputs": ["paper_assets.json"],
        "outputs": ["paper_analysis.json", "paper_analysis_trace.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "04", "name": "Research_Landscape", "name_cn": "研究领域全景",
        "source_dirs": ["modules/04_research_landscape"],
        "upstream": ["03"], "downstream": ["05"],
        "inputs": ["paper_analysis.json"],
        "outputs": ["research_landscape.md", "gap_candidates.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "05", "name": "Innovation_Discovery", "name_cn": "创新发现",
        "source_dirs": ["modules/05_innovation_reasoning"],
        "upstream": ["03", "04"], "downstream": ["06"],
        "inputs": ["paper_analysis.json", "research_landscape.md"],
        "outputs": ["innovation_candidates.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "06", "name": "Theory_Method", "name_cn": "理论方法设计",
        "source_dirs": ["modules/06_theory_method"],
        "upstream": ["05"], "downstream": ["07", "08", "11"],
        "inputs": ["innovation_candidates.json"],
        "outputs": ["method_spec.json", "theory_analysis.md", "theory_confidence.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "07", "name": "Experiment_Planning", "name_cn": "实验规划",
        "source_dirs": ["modules/07_experiment_planning"],
        "upstream": ["06"], "downstream": ["08", "10", "11"],
        "inputs": ["method_spec.json"],
        "outputs": ["experiment_matrix.yaml", "experiment_plan.yaml", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "08", "name": "Synthetic_Experiment", "name_cn": "合成实验引擎",
        "source_dirs": ["modules/08_synthetic_experiment_engine"],
        "upstream": ["06", "07"], "downstream": ["10", "11"],
        "inputs": ["method_spec.json", "experiment_matrix.yaml"],
        "outputs": ["synthetic_results.json", "raw/", "processed/", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "09", "name": "Real_Experiment", "name_cn": "真实实验引擎",
        "source_dirs": ["modules/09_real_experiment_engine"],
        "upstream": ["06", "07"], "downstream": ["10", "11"],
        "inputs": ["method_spec.json", "experiment_matrix.yaml"],
        "outputs": ["real_results.json", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "10", "name": "Result_Analysis", "name_cn": "结果分析",
        "source_dirs": ["modules/10_result_analysis"],
        "upstream": ["07", "08", "09"], "downstream": ["11"],
        "inputs": ["experiment_results.json", "claim_evidence_plan.json"],
        "outputs": ["analysis_report.json", "decision.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "11", "name": "Figure_Table", "name_cn": "图表生成",
        "source_dirs": ["modules/11_figure_table"],
        "upstream": ["06", "07", "08", "09"], "downstream": ["12"],
        "inputs": ["experiment_results.json", "analysis_report.json", "method_spec.json"],
        "outputs": ["figures/", "tables/", "mermaid/", "figure_prompts.json", "input_schema.md", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "12", "name": "Paper_Writing", "name_cn": "论文撰写",
        "source_dirs": ["modules/12_paper_writing"],
        "upstream": ["all"], "downstream": ["13", "14"],
        "inputs": ["method_spec.json", "experiment_results.json", "analysis_report.json"],
        "outputs": ["paper/paper.md", "paper/paper.tex", "paper/paper.docx", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "13", "name": "Reference_Supplementary", "name_cn": "引用与补充",
        "source_dirs": ["modules/13_reference_supplementary"],
        "upstream": ["01", "12"], "downstream": [],
        "inputs": ["paper/paper.md", "literature_database.json"],
        "outputs": ["references.bib", "supplementary.md", "Stage_Report.md"],
        "needs_llm": False,
    },
    {
        "id": "14", "name": "Reviewer_Loop", "name_cn": "审稿循环",
        "source_dirs": ["modules/14_reviewer_loop"],
        "upstream": ["12", "13"], "downstream": ["15"],
        "inputs": ["paper/paper.md"],
        "outputs": ["review_report.md", "review_decision.json", "Stage_Report.md"],
        "needs_llm": True,
    },
    {
        "id": "15", "name": "Research_Memory", "name_cn": "科研记忆",
        "source_dirs": ["modules/15_research_memory"],
        "upstream": ["all"], "downstream": [],
        "inputs": ["各模块Stage_Report.md"],
        "outputs": ["research_memory.md", "decision_log.md", "lessons_learned.md", "Stage_Report.md"],
        "needs_llm": False,
    },
]

SHARED_DIRS = ["infrastructure", "adapters"]
SHARED_CONFIGS = [
    "configs/llm.yaml",
    "configs/llm_routing.yaml",
    "configs/providers.yaml",
]
TASK_CONFIGS = [
    "configs/research_task.yaml",
    "configs/research_task_vlm_safety.yaml",
]


def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)


def copy_shared_files(pkg_dir):
    shared_dir = pkg_dir / "shared"
    shared_dir.mkdir(exist_ok=True)

    for sd in SHARED_DIRS:
        src = V3_ROOT / sd
        dst = shared_dir / sd
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    configs_dir = pkg_dir / "configs"
    configs_dir.mkdir(exist_ok=True)
    for cf in SHARED_CONFIGS:
        src = V3_ROOT / cf
        if src.exists():
            shutil.copy2(src, configs_dir / src.name)

    for tc in TASK_CONFIGS:
        src = V3_ROOT / tc
        if src.exists():
            shutil.copy2(src, configs_dir / src.name)


def copy_module_code(pkg_dir, module):
    src_dir = pkg_dir / "src"
    src_dir.mkdir(exist_ok=True)

    for source_dir in module["source_dirs"]:
        src_path = V3_ROOT / source_dir
        if not src_path.exists():
            print(f"  WARNING: {source_dir} not found")
            continue
        for item in src_path.iterdir():
            if item.name == "__pycache__":
                continue
            if item.is_file():
                shutil.copy2(item, src_dir / item.name)


def create_start_here(pkg_dir, module):
    mid = module["id"]
    name = module["name"]
    name_cn = module["name_cn"]
    upstream = ", ".join(module["upstream"]) if module["upstream"] else "无"
    downstream = ", ".join(module["downstream"]) if module["downstream"] else "无"
    inputs = "\n".join(f"  - {f}" for f in module["inputs"])
    outputs = "\n".join(f"  - {f}" for f in module["outputs"])
    llm_note = "需要LLM配置" if module["needs_llm"] else "不需要LLM"

    content = f"""# Module {mid} — {name_cn} ({name}) 快速开始

## 模块信息
- **模块ID**: {mid}
- **模块名称**: {name_cn}
- **上游模块**: {upstream}
- **下游模块**: {downstream}
- **LLM需求**: {llm_note}

## 目录结构
```
Module{mid}_{name}_v8.3.1/
├── src/              # 模块源代码
├── shared/           # 共享依赖 (LLM Runtime, adapters)
├── configs/          # 配置文件
├── input/            # 输入文件目录
├── output/           # 输出文件目录
├── scripts/           # 环境检测脚本
├── START_HERE.md     # 本文件
└── README.md         # 模块说明
```

## 输入文件
{inputs}

将输入文件放入 `input/` 目录。

## 输出文件
{outputs}

输出文件将生成在 `output/` 目录中。

## 快速运行

### 1. 环境检测
```bash
python scripts/environment_check.py
```

### 2. 运行模块
```bash
python -m src.implementation
```

或者：
```bash
python src/__main__.py
```

### 3. 查看结果
输出文件在 `output/` 目录中，包括 `Stage_Report.md` 状态报告。

## 配置说明

### configs/module_config.yaml
模块主配置文件，包含：
- `task_id`: 研究任务ID
- `input_dir`: 输入目录路径
- `output_dir`: 输出目录路径

### configs/llm_routing.yaml
LLM路由配置（如需要LLM）：
- `deepseek-r1:8b`: 推理任务
- `gemma4:26b`: 文本生成任务

## 错误处理

1. **输入文件缺失**: 检查 `input/` 目录是否有所需文件
2. **LLM连接失败**: 运行 `python scripts/environment_check.py` 检查LLM状态
3. **依赖缺失**: 确保 `shared/` 目录存在且完整

## 版本
- **版本**: v8.3.1
- **日期**: {datetime.now().strftime("%Y-%m-%d")}
"""
    (pkg_dir / "START_HERE.md").write_text(content, encoding="utf-8")


def create_readme(pkg_dir, module):
    mid = module["id"]
    content = f"""# Module {mid} — {module['name_cn']}

{module.get('desc', '')}

## 版本
v8.3.1 — Research Agent Final Patch

## 独立运行
```bash
# 1. 检查环境
python scripts/environment_check.py

# 2. 运行模块
python -m src.implementation
```

## 依赖
- Python 3.12
- research_agent_v3 conda环境
- 共享依赖在 shared/ 目录中
"""
    (pkg_dir / "README.md").write_text(content, encoding="utf-8")


def create_environment_check(pkg_dir, module):
    scripts_dir = pkg_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    needs_llm = module["needs_llm"]

    content = f'''#!/usr/bin/env python
"""Environment check for Module {module['id']} — {module['name_cn']} v8.3.1"""
import sys
import os
from pathlib import Path

def check_python():
    v = sys.version_info
    ok = v >= (3, 10)
    print(f"Python: {{v.major}}.{{v.minor}}.{{v.micro}} {{'✓' if ok else '✗ (需要3.10+)'}}")
    return ok

def check_shared():
    shared = Path(__file__).parent.parent / "shared"
    ok = shared.exists()
    print(f"Shared目录: {{'✓' if ok else '✗'}}")
    if ok:
        infra = shared / "infrastructure"
        print(f"  infrastructure: {{'✓' if infra.exists() else '✗'}}")
    return ok

def check_configs():
    cfg = Path(__file__).parent.parent / "configs"
    ok = cfg.exists()
    print(f"Configs目录: {{'✓' if ok else '✗'}}")
    return ok

def check_llm():
    cfg = Path(__file__).parent.parent / "configs" / "providers.yaml"
    ok = cfg.exists()
    print(f"LLM配置: {{'✓' if ok else '✗ (providers.yaml缺失)'}}")
    return ok

def check_directories():
    root = Path(__file__).parent.parent
    input_dir = root / "input"
    output_dir = root / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    print(f"Input目录: ✓")
    print(f"Output目录: ✓")
    return True

def main():
    print("=" * 50)
    print(f"Module {module['id']} — {module['name_cn']} 环境检测")
    print("=" * 50)
    results = [check_python(), check_shared(), check_configs(), check_directories()]
    if {str(needs_llm)}:
        results.append(check_llm())
    all_ok = all(results)
    print("=" * 50)
    print(f"结果: {{'全部通过 ✓' if all_ok else '存在问题 ✗'}}")
    print("=" * 50)
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
'''
    (scripts_dir / "environment_check.py").write_text(content, encoding="utf-8")


def create_module_config(pkg_dir, module):
    configs_dir = pkg_dir / "configs"
    configs_dir.mkdir(exist_ok=True)
    content = f"""# Module {module['id']} Configuration
module_id: "{module['id']}"
module_name: "{module['name_cn']}"
version: "8.3.1"

task_id: "vlm_safety_001"

input_dir: "input"
output_dir: "output"

output:
  root: "output"

experiment:
  method: "default"
  synthetic:
    seed: 42
    num_samples: 1000
  real:
    seed: 42
    checkpoint_dir: "experiments/checkpoints"
    resume_from_checkpoint: false

llm:
  routing_config: "configs/llm_routing.yaml"
  providers_config: "configs/providers.yaml"
"""
    (configs_dir / "module_config.yaml").write_text(content, encoding="utf-8")


def create_input_output_dirs(pkg_dir):
    (pkg_dir / "input").mkdir(exist_ok=True)
    (pkg_dir / "output").mkdir(exist_ok=True)
    (pkg_dir / "input" / ".gitkeep").write_text("", encoding="utf-8")
    (pkg_dir / "output" / ".gitkeep").write_text("", encoding="utf-8")


def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_module(module):
    mid = module["id"]
    name = module["name"]
    pkg_name = f"Research_Agent_Module{mid}_{name}_v8.3.1"
    pkg_dir = BUILD_DIR / pkg_name

    print(f"\n{'='*60}")
    print(f"Building Module {mid} — {module['name_cn']}")
    print(f"{'='*60}")

    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)

    copy_module_code(pkg_dir, module)
    copy_shared_files(pkg_dir)
    create_start_here(pkg_dir, module)
    create_readme(pkg_dir, module)
    create_environment_check(pkg_dir, module)
    create_module_config(pkg_dir, module)
    create_input_output_dirs(pkg_dir)

    # Remove __pycache__
    for pyc in pkg_dir.rglob("__pycache__"):
        shutil.rmtree(pyc)

    # Create ZIP
    zip_path = RELEASES_DIR / f"{pkg_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pkg_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(pkg_dir)
                zf.write(file_path, f"{pkg_name}/{arcname}")

    size = zip_path.stat().st_size
    sha256 = compute_sha256(zip_path)
    print(f"  ZIP: {zip_path}")
    print(f"  Size: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"  SHA256: {sha256}")

    return {
        "module_id": mid,
        "module_name": module["name_cn"],
        "zip_path": str(zip_path),
        "zip_name": zip_path.name,
        "size_bytes": size,
        "size_kb": round(size / 1024, 1),
        "sha256": sha256,
    }


def main():
    print("Research Agent v8.3.1 — Module Release Builder")
    print(f"Output: {RELEASES_DIR}")
    print(f"Time: {datetime.now().isoformat()}")

    clean_build_dir()

    results = []
    for module in MODULES:
        result = build_module(module)
        results.append(result)

    # Save manifest
    manifest = {
        "version": "8.3.1",
        "generated": datetime.now().isoformat(),
        "total_modules": len(results),
        "modules": results,
    }
    manifest_path = RELEASES_DIR / "release_manifest_v831.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nManifest saved: {manifest_path}")

    # Cleanup build dir
    shutil.rmtree(BUILD_DIR)
    print(f"\nDone! {len(results)} modules packaged.")


if __name__ == "__main__":
    main()
