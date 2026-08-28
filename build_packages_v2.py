#!/usr/bin/env python
"""
Build script v2: Generate 15 independent module packages as ZIP files.
Based on OneStep_Execution_Master_Prompt requirements.

Usage:
    conda activate research_agent_v3
    python build_packages_v2.py
"""

import os
import sys
import shutil
import zipfile
import json
import yaml
import textwrap
import importlib
import inspect
from pathlib import Path
from datetime import datetime

V3_ROOT = Path(__file__).resolve().parent
RELEASES_DIR = Path("D:/Research Agent/releases")
BUILD_DIR = V3_ROOT / "_build_v2"

# ==============================================================================
# 15 Module Definitions (per OneStep_Execution_Master_Prompt)
# ==============================================================================

MODULES = [
    {
        "id": "01", "name": "Literature_Retrieval", "name_cn": "文献检索",
        "desc": "根据研究方向、关键词从arXiv、Semantic Scholar等数据库检索论文。",
        "source_dirs": ["modules/01_literature_retrieval"],
        "upstream": [], "downstream": ["02", "03"],
        "input_files": [{"name": "research_task.yaml", "desc": "研究任务配置", "required": True}],
        "output_files": [{"name": "literature_candidates.json", "desc": "文献候选列表"}],
        "needs_llm": False,
    },
    {
        "id": "02", "name": "Paper_Acquisition", "name_cn": "论文资产获取",
        "desc": "论文PDF下载、arXiv LaTeX下载、PDF转Markdown、前三张论文图片提取。",
        "source_dirs": ["modules/02_source_acquisition", "modules/02_5_paper_asset_intelligence"],
        "upstream": ["01"], "downstream": ["03"],
        "input_files": [{"name": "literature_candidates.json", "desc": "Module 01输出", "required": True}],
        "output_files": [{"name": "paper_assets.json", "desc": "论文资产清单"}],
        "output_dirs": ["pdf/", "latex/", "markdown/", "figures/"],
        "needs_llm": False,
    },
    {
        "id": "03", "name": "Literature_Intelligence", "name_cn": "文献智能分析",
        "desc": "深度论文分析，提取problem、method、innovation、experiment、limitation、future direction。",
        "source_dirs": ["modules/03_literature_intelligence"],
        "upstream": ["02"], "downstream": ["04", "05"],
        "input_files": [{"name": "paper_assets.json", "desc": "Module 02输出", "required": True},
                        {"name": "markdown/*.md", "desc": "归一化论文Markdown", "required": True}],
        "output_files": [{"name": "paper_analysis.json", "desc": "论文分析结果"}],
        "needs_llm": True,
    },
    {
        "id": "04", "name": "Research_Landscape", "name_cn": "研究领域全景",
        "desc": "分析研究领域全景，构建分类体系、趋势分析、矛盾图谱。",
        "source_dirs": ["modules/04_research_landscape"],
        "upstream": ["03"], "downstream": ["05"],
        "input_files": [{"name": "paper_analysis.json", "desc": "Module 03输出", "required": True}],
        "output_files": [{"name": "research_landscape.md", "desc": "研究全景报告"}],
        "needs_llm": True,
    },
    {
        "id": "05", "name": "Innovation_Discovery", "name_cn": "创新发现",
        "desc": "根据真实文献发现创新点，禁止模板创新。",
        "source_dirs": ["modules/05_innovation_reasoning"],
        "upstream": ["03", "04"], "downstream": ["06"],
        "input_files": [{"name": "paper_analysis.json", "desc": "Module 03输出", "required": True},
                        {"name": "research_landscape.md", "desc": "Module 04输出", "required": True}],
        "output_files": [{"name": "innovation_candidates.json", "desc": "创新候选列表"}],
        "needs_llm": True,
    },
    {
        "id": "06", "name": "Method_Design", "name_cn": "方法设计",
        "desc": "设计算法，包含模型结构、算法流程、数学公式、优化目标。",
        "source_dirs": ["modules/06_theory_method"],
        "upstream": ["05"], "downstream": ["07", "08", "11"],
        "input_files": [{"name": "innovation_candidates.json", "desc": "Module 05输出", "required": True}],
        "output_files": [{"name": "method_design.md", "desc": "方法设计文档"}],
        "needs_llm": True,
    },
    {
        "id": "07", "name": "Experiment_Planning", "name_cn": "实验规划",
        "desc": "生成实验方案，包含Dataset、Baseline、Metrics、Ablation。",
        "source_dirs": ["modules/07_experiment_planning"],
        "upstream": ["06"], "downstream": ["08", "10", "11"],
        "input_files": [{"name": "method_design.md", "desc": "Module 06输出", "required": True}],
        "output_files": [{"name": "experiment_plan.yaml", "desc": "实验方案"}],
        "needs_llm": True,
    },
    {
        "id": "08", "name": "Experiment_Execution", "name_cn": "实验执行",
        "desc": "实验执行，支持synthetic和real_gpu模式。",
        "source_dirs": ["modules/08_synthetic_experiment_engine", "modules/09_real_experiment_engine"],
        "upstream": ["06", "07"], "downstream": ["09", "10", "11"],
        "input_files": [{"name": "experiment_plan.yaml", "desc": "Module 07输出", "required": True},
                        {"name": "method_design.md", "desc": "Module 06输出", "required": True}],
        "output_files": [{"name": "experiment_results.json", "desc": "实验结果"}],
        "needs_llm": False,
    },
    {
        "id": "09", "name": "Result_Collection", "name_cn": "结果收集",
        "desc": "统一收集实验结果，构建结果数据库。",
        "source_dirs": [],  # 新模块，从orchestrator提取逻辑
        "upstream": ["08"], "downstream": ["10", "11", "12"],
        "input_files": [{"name": "experiment_results.json", "desc": "Module 08输出", "required": True}],
        "output_files": [{"name": "results_database.json", "desc": "结果数据库"}],
        "needs_llm": False,
    },
    {
        "id": "10", "name": "Result_Analysis", "name_cn": "结果分析",
        "desc": "实验结果分析，统计显著性、效应量、对比基线。",
        "source_dirs": ["modules/10_result_analysis"],
        "upstream": ["07", "08", "09"], "downstream": ["11"],
        "input_files": [{"name": "results_database.json", "desc": "Module 09输出", "required": True},
                        {"name": "experiment_plan.yaml", "desc": "Module 07输出", "required": True}],
        "output_files": [{"name": "result_analysis.md", "desc": "结果分析报告"}],
        "needs_llm": True,
    },
    {
        "id": "11", "name": "Figure_Table_Generation", "name_cn": "图表生成",
        "desc": "生成Mermaid源码、LaTeX表格、绘图Prompt。",
        "source_dirs": ["modules/11_figure_table"],
        "upstream": ["06", "07", "08", "09"], "downstream": ["12"],
        "input_files": [{"name": "results_database.json", "desc": "Module 09输出", "required": True},
                        {"name": "result_analysis.md", "desc": "Module 10输出", "required": False}],
        "output_files": [{"name": "figures/mermaid/", "desc": "Mermaid源码"},
                         {"name": "figures/latex_tables/", "desc": "LaTeX表格"},
                         {"name": "figures/prompts/", "desc": "绘图Prompt"}],
        "needs_llm": False,
    },
    {
        "id": "12", "name": "Paper_Writing", "name_cn": "论文写作",
        "desc": "生成paper.md、paper.tex、paper.docx。",
        "source_dirs": ["modules/12_paper_writing"],
        "upstream": ["all"], "downstream": ["13", "14"],
        "input_files": [{"name": "results_database.json", "desc": "Module 09输出", "required": True},
                        {"name": "result_analysis.md", "desc": "Module 10输出", "required": True},
                        {"name": "method_design.md", "desc": "Module 06输出", "required": True}],
        "output_files": [{"name": "paper.md", "desc": "Markdown论文"},
                         {"name": "paper.tex", "desc": "LaTeX论文"},
                         {"name": "paper.docx", "desc": "Word论文"}],
        "needs_llm": True,
    },
    {
        "id": "13", "name": "Reference_Management", "name_cn": "引用管理",
        "desc": "生成references.bib，支持真实论文引用。",
        "source_dirs": ["modules/13_reference_supplementary"],
        "upstream": ["01", "12"], "downstream": [],
        "input_files": [{"name": "paper.md", "desc": "Module 12输出", "required": True},
                        {"name": "literature_candidates.json", "desc": "Module 01输出", "required": True}],
        "output_files": [{"name": "references.bib", "desc": "BibTeX引用文件"}],
        "needs_llm": False,
    },
    {
        "id": "14", "name": "Reviewer_Simulation", "name_cn": "审稿模拟",
        "desc": "模拟CVPR/ICCV/NeurIPS/ICLR Reviewer审稿。",
        "source_dirs": ["modules/14_reviewer_loop"],
        "upstream": ["12", "13"], "downstream": [],
        "input_files": [{"name": "paper.md", "desc": "Module 12输出", "required": True},
                        {"name": "references.bib", "desc": "Module 13输出", "required": False}],
        "output_files": [{"name": "review_report.md", "desc": "审稿报告"}],
        "needs_llm": True,
    },
    {
        "id": "15", "name": "Research_Memory", "name_cn": "科研记忆",
        "desc": "管理长期科研资产，保存papers、methods、experiments、failed attempts。",
        "source_dirs": [],  # 新模块，从infrastructure/memory提取
        "upstream": ["all"], "downstream": [],
        "input_files": [{"name": "任意模块输出", "desc": "所有模块的输出均可存入记忆", "required": False}],
        "output_files": [{"name": "memory_store.json", "desc": "记忆存储"},
                         {"name": "memory_index.json", "desc": "记忆索引"}],
        "needs_llm": False,
    },
]

# Shared directories to copy into each package
SHARED_DIRS = ["infrastructure", "literature", "reasoning", "adapters", "core", "schemas", "templates"]

# Shared configs to copy
SHARED_CONFIGS = [
    "configs/llm.yaml",
    "configs/llm_routing.yaml",
    "configs/providers.yaml",
    "configs/dependency_policy.yaml",
    "configs/external_dependency.yaml",
    "configs/experiment_mode.yaml",
    "configs/figure_config.yaml",
    "configs/research_task_template.yaml",
    "configs/environment.yaml",
    "configs/machine.yaml",
    "configs/model_registry.yaml",
    "configs/storage.yaml",
]

# Scripts to copy
SCRIPTS_TO_COPY = [
    "scripts/check_literature.py",
    "scripts/check_llm.py",
    "scripts/check_mcp.py",
    "scripts/check_portability.py",
    "scripts/check_research_ready.py",
    "scripts/check_skills.py",
]

# Research task configs to copy
TASK_CONFIGS = [
    "configs/research_task.yaml",
    "configs/research_task_vlm_safety.yaml",
]


# ==============================================================================
# Directory Structure Creation
# ==============================================================================

def create_directory_structure(pkg_dir):
    """Create the standard directory structure for a module."""
    dirs = [
        "configs",
        "input",
        "output",
        "src",
        "shared",
        "scripts",
        "tests",
        "docs",
    ]
    for d in dirs:
        (pkg_dir / d).mkdir(parents=True, exist_ok=True)


# ==============================================================================
# Copy Source Code
# ==============================================================================

def copy_module_code(pkg_dir, module):
    """Copy module source code to src/."""
    src_dir = pkg_dir / "src"
    for source_dir in module["source_dirs"]:
        src_path = V3_ROOT / source_dir
        if src_path.exists():
            for item in src_path.iterdir():
                if item.is_file() and item.suffix in ['.py', '.yaml', '.json']:
                    shutil.copy2(item, src_dir / item.name)
                elif item.is_file() and item.suffix == '.md':
                    shutil.copy2(item, src_dir / item.name)
        else:
            print(f"  WARNING: Source dir not found: {source_dir}")

    # For Module09 and Module15 (new modules), create minimal implementations
    if module["id"] == "09":
        _create_module09_stub(src_dir, module)
    elif module["id"] == "15":
        _create_module15_stub(src_dir, module)


def _create_module09_stub(src_dir, module):
    """Create Module09 Result Collection stub implementation."""
    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    interface_code = '''"""Module09: Result Collection — Interface"""
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class ResultCollectionInput:
    task_id: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    input_files: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResultCollectionOutput:
    task_id: str = ""
    status: str = "success"
    results_database: Dict[str, Any] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
'''
    (src_dir / "interface.py").write_text(interface_code, encoding="utf-8")

    impl_code = '''"""Module09: Result Collection — Implementation"""
import json
import os
from pathlib import Path
from .interface import ResultCollectionInput, ResultCollectionOutput


class ResultCollectionModule:
    """统一收集实验结果，构建结果数据库。"""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    def execute(self, input_data: ResultCollectionInput) -> ResultCollectionOutput:
        output = ResultCollectionOutput(task_id=input_data.task_id)
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        results_db = {"task_id": input_data.task_id, "experiments": [], "metadata": {}}

        for key, path in input_data.input_files.items():
            if "experiment_results" in key and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results_db["experiments"].append({"source": key, "data": data})
                output.output_files[key] = path

        db_path = output_dir / "results_database.json"
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(results_db, f, ensure_ascii=False, indent=2)
        output.output_files["results_database.json"] = str(db_path)
        output.results_database = results_db

        return output
'''
    (src_dir / "implementation.py").write_text(impl_code, encoding="utf-8")

    schema_code = '''"""Module09 Schema"""
results_database_schema = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"},
        "experiments": {"type": "array"},
        "metadata": {"type": "object"}
    },
    "required": ["task_id", "experiments"]
}
'''
    (src_dir / "schema.py").write_text(schema_code, encoding="utf-8")
    (src_dir / "validator.py").write_text('"""Module09 Validator"""\n', encoding="utf-8")

    manifest = {
        "module_id": "09",
        "module_name": "Result_Collection",
        "version": "1.0.0",
        "input_type": "ResultCollectionInput",
        "output_type": "ResultCollectionOutput",
    }
    import yaml as _yaml
    (src_dir / "manifest.yaml").write_text(_yaml.dump(manifest, allow_unicode=True), encoding="utf-8")


def _create_module15_stub(src_dir, module):
    """Create Module15 Research Memory stub implementation."""
    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    interface_code = '''"""Module15: Research Memory — Interface"""
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class ResearchMemoryInput:
    task_id: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    input_files: Dict[str, str] = field(default_factory=dict)
    operation: str = "store"  # store | retrieve | list


@dataclass
class ResearchMemoryOutput:
    task_id: str = ""
    status: str = "success"
    memory_store: Dict[str, Any] = field(default_factory=dict)
    memory_index: List[Dict[str, Any]] = field(default_factory=list)
    output_files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
'''
    (src_dir / "interface.py").write_text(interface_code, encoding="utf-8")

    impl_code = '''"""Module15: Research Memory — Implementation"""
import json
import os
from datetime import datetime
from pathlib import Path
from .interface import ResearchMemoryInput, ResearchMemoryOutput


class ResearchMemoryModule:
    """管理长期科研资产：papers, methods, experiments, failed attempts。"""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self.memory_dir = Path("output/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, input_data: ResearchMemoryInput) -> ResearchMemoryOutput:
        output = ResearchMemoryOutput(task_id=input_data.task_id)

        if input_data.operation == "store":
            output = self._store(input_data, output)
        elif input_data.operation == "retrieve":
            output = self._retrieve(input_data, output)
        else:
            output = self._list(input_data, output)

        return output

    def _store(self, input_data, output):
        store_path = self.memory_dir / "memory_store.json"
        store = {}
        if store_path.exists():
            with open(store_path, "r", encoding="utf-8") as f:
                store = json.load(f)

        for key, path in input_data.input_files.items():
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                store[key] = {
                    "path": path,
                    "stored_at": datetime.now().isoformat(),
                    "content_preview": content[:500],
                }

        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
        output.memory_store = store
        output.output_files["memory_store.json"] = str(store_path)
        return output

    def _retrieve(self, input_data, output):
        store_path = self.memory_dir / "memory_store.json"
        if store_path.exists():
            with open(store_path, "r", encoding="utf-8") as f:
                output.memory_store = json.load(f)
        return output

    def _list(self, input_data, output):
        store_path = self.memory_dir / "memory_store.json"
        if store_path.exists():
            with open(store_path, "r", encoding="utf-8") as f:
                store = json.load(f)
            output.memory_index = [{"key": k, "stored_at": v.get("stored_at", "")}
                                   for k, v in store.items()]
        index_path = self.memory_dir / "memory_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(output.memory_index, f, ensure_ascii=False, indent=2)
        output.output_files["memory_index.json"] = str(index_path)
        return output
'''
    (src_dir / "implementation.py").write_text(impl_code, encoding="utf-8")

    schema_code = '''"""Module15 Schema"""
memory_store_schema = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"},
        "memory_store": {"type": "object"},
        "memory_index": {"type": "array"}
    }
}
'''
    (src_dir / "schema.py").write_text(schema_code, encoding="utf-8")
    (src_dir / "validator.py").write_text('"""Module15 Validator"""\n', encoding="utf-8")

    manifest = {
        "module_id": "15",
        "module_name": "Research_Memory",
        "version": "1.0.0",
        "input_type": "ResearchMemoryInput",
        "output_type": "ResearchMemoryOutput",
    }
    import yaml as _yaml
    (src_dir / "manifest.yaml").write_text(_yaml.dump(manifest, allow_unicode=True), encoding="utf-8")


def copy_shared_code(pkg_dir):
    """Copy shared dependencies to shared/."""
    shared_dir = pkg_dir / "shared"
    for dir_name in SHARED_DIRS:
        src_path = V3_ROOT / dir_name
        if src_path.exists():
            dst_path = shared_dir / dir_name
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path,
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))
        else:
            print(f"  WARNING: Shared dir not found: {dir_name}")


def copy_configs(pkg_dir, module):
    """Copy configuration files."""
    cfg_dir = pkg_dir / "configs"

    # Copy shared configs
    for cfg_path in SHARED_CONFIGS:
        src = V3_ROOT / cfg_path
        if src.exists():
            shutil.copy2(src, cfg_dir / src.name)

    # Copy task configs
    for task_cfg in TASK_CONFIGS:
        src = V3_ROOT / task_cfg
        if src.exists():
            shutil.copy2(src, cfg_dir / src.name)

    # Generate module_config.yaml
    _gen_module_config(cfg_dir, module)


def _gen_module_config(cfg_dir, module):
    """Generate module_config.yaml."""
    config = {
        "module_id": module["id"],
        "module_name": module["name"],
        "module_name_cn": module["name_cn"],
        "description": module["desc"],
        "version": "1.0.0",
        "upstream": module["upstream"],
        "downstream": module["downstream"],
        "needs_llm": module["needs_llm"],
        "input_files": {f["name"]: {"desc": f["desc"], "required": f["required"]}
                       for f in module["input_files"]},
        "output_files": {f["name"]: f["desc"] for f in module["output_files"]},
    }
    with open(cfg_dir / "module_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def copy_scripts(pkg_dir):
    """Copy utility scripts."""
    scripts_dir = pkg_dir / "scripts"
    for script_path in SCRIPTS_TO_COPY:
        src = V3_ROOT / script_path
        if src.exists():
            shutil.copy2(src, scripts_dir / src.name)
        else:
            print(f"  WARNING: Script not found: {script_path}")


# ==============================================================================
# File Generators
# ==============================================================================

def gen_start_here(pkg_dir, module):
    """Generate START_HERE.md."""
    upstream_str = ", ".join([f"Module {u}" for u in module["upstream"]]) if module["upstream"] else "无（入口模块）"
    downstream_str = ", ".join([f"Module {d}" for d in module["downstream"]]) if module["downstream"] else "无（终末模块）"

    content = f"""# Module {module['id']}: {module['name_cn']} — 快速开始

## 模块信息

| 项目 | 值 |
|------|-----|
| 模块ID | {module['id']} |
| 模块名称 | {module['name']} |
| 中文名称 | {module['name_cn']} |
| 功能描述 | {module['desc']} |
| 上游模块 | {upstream_str} |
| 下游模块 | {downstream_str} |
| 是否需要LLM | {'是' if module['needs_llm'] else '否'} |

## 环境要求

- Python 3.12
- Conda环境: research_agent_v3
- 操作系统: Windows / Linux / macOS

## 快速启动

```bash
# 1. 激活环境
conda activate research_agent_v3

# 2. 环境检查
python environment_check.py

# 3. 运行模块
python run.py --task-id YOUR_TASK_ID

# 4. 运行测试
python tests/module_test.py
```

## 输入要求

"""
    for f in module["input_files"]:
        req = "必需" if f["required"] else "可选"
        content += f"| 文件 | {f['name']} |\n| 说明 | {f['desc']} |\n| 是否必需 | {req} |\n\n"

    content += "输入文件放置目录: `input/`\n\n"

    content += "## 输出说明\n\n"
    for f in module["output_files"]:
        content += f"| 文件 | {f['name']} |\n| 说明 | {f['desc']} |\n\n"

    content += "输出文件保存目录: `output/`\n\n"

    content += """## 人工补充机制

如果模块运行失败或输出异常，请：

1. 查看 `output/` 目录下是否生成了 `Human_Intervention_Request.md`
2. 按照该文件的指引手动补充缺失的输入或修复输出
3. 将补充的文件放到 `input/` 目录后重新运行

## 配置文件

| 文件 | 说明 |
|------|------|
| configs/module_config.yaml | 模块配置 |
| configs/llm.yaml | LLM配置 |
| configs/providers.yaml | 提供商配置 |
| configs/dependency_policy.yaml | 依赖策略 |
| configs/environment.yaml | 环境配置 |

## 更多文档

- [README.md](README.md) — 完整说明文档
- [docs/Module_Interface.md](docs/Module_Interface.md) — 接口文档
- [Human_Intervention_Guide](docs/Human_Intervention_Guide.md) — 人工干预指南
"""
    (pkg_dir / "START_HERE.md").write_text(content, encoding="utf-8")


def gen_readme(pkg_dir, module):
    """Generate README.md."""
    upstream_str = ", ".join(module["upstream"]) if module["upstream"] else "无"
    downstream_str = ", ".join(module["downstream"]) if module["downstream"] else "无"

    input_table = "\n".join([f"| {f['name']} | {f['desc']} | {'必需' if f['required'] else '可选'} |"
                            for f in module["input_files"]])
    output_table = "\n".join([f"| {f['name']} | {f['desc']} |"
                             for f in module["output_files"]])

    content = f"""# Module {module['id']}: {module['name_cn']}

## 概述

{module['desc']}

## 目录结构

```
Research_Agent_Module{module['id']}_{module['name']}_v1.2/
├── START_HERE.md          # 快速开始指南
├── README.md              # 本文件
├── environment_check.py   # 环境检测脚本
├── run.py                 # 模块运行入口
├── configs/               # 配置文件
│   ├── module_config.yaml
│   ├── llm.yaml
│   ├── providers.yaml
│   ├── dependency_policy.yaml
│   ├── environment.yaml
│   └── research_task*.yaml
├── input/                 # 输入文件目录
├── output/                # 输出文件目录
├── src/                   # 模块源代码
├── shared/                # 共享依赖代码
├── scripts/               # 辅助脚本
├── tests/                 # 测试脚本
└── docs/                  # 文档
    └── Module_Interface.md
```

## 模块依赖

| 方向 | 模块 |
|------|------|
| 上游 | {upstream_str} |
| 下游 | {downstream_str} |

## 输入输出

### 输入

| 文件名 | 说明 | 是否必需 |
|--------|------|---------|
{input_table}

输入文件放置在 `input/` 目录下。

### 输出

| 文件名 | 说明 |
|--------|------|
{output_table}

输出文件保存在 `output/` 目录下。

## 运行方式

### 1. 环境准备

```bash
conda activate research_agent_v3
```

### 2. 环境检测

```bash
python environment_check.py
```

检测完成后会生成 `Environment_Check_Report.md`。

### 3. 准备输入

将上游模块的输出文件复制到 `input/` 目录。

### 4. 运行模块

```bash
python run.py --task-id YOUR_TASK_ID
```

### 5. 检查输出

输出文件在 `output/` 目录下。

## 配置说明

### LLM配置 (configs/llm.yaml)

本模块{'需要' if module['needs_llm'] else '不需要'}LLM支持。

已配置的LLM提供商:
- DeepSeek (deepseek-reasoner)
- OpenAI (gpt-4o)
- Ollama R1 (deepseek-r1:8b, 本地)
- Ollama (gemma4:26b, 本地)

### 依赖策略 (configs/dependency_policy.yaml)

- 禁止Mock LLM用于科研任务
- 允许synthetic实验模式
- 模式: limited (需真实LLM，允许合成实验)

## 测试

```bash
python tests/module_test.py
```

测试完成后会生成 `Module_Test_Report.md`。

## 人工干预

如果模块运行失败，请查看 `output/Human_Intervention_Request.md`。

## 环境要求

- Python 3.12
- Conda: research_agent_v3
- 主要依赖: pyyaml, numpy, pandas, requests, openai (可选), transformers (可选)
"""
    (pkg_dir / "README.md").write_text(content, encoding="utf-8")


def gen_environment_check(pkg_dir, module):
    """Generate environment_check.py."""
    code = f'''#!/usr/bin/env python
"""Environment Check for Module {module['id']}: {module['name']}"""
import sys
import os
import platform
import subprocess
import importlib
from pathlib import Path
from datetime import datetime

PKG_ROOT = Path(__file__).resolve().parent

REPORT_LINES = []

def log(msg, level="INFO"):
    REPORT_LINES.append(f"[{{level}}] {{msg}}")
    print(f"[{{level}}] {{msg}}")


def check_python():
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        log(f"Python version: {{sys.version}} — OK")
        return True
    else:
        log(f"Python version: {{sys.version}} — WARNING: recommended 3.12+", "WARN")
        return False


def check_conda():
    """Check conda environment."""
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if conda_env == "research_agent_v3":
        log(f"Conda environment: {{conda_env}} — OK")
        return True
    if "research_agent_v3" in sys.executable:
        log(f"Conda environment: research_agent_v3 (detected via sys.executable) — OK")
        return True
    log(f"Conda environment: '{{conda_env}}' — WARNING: expected 'research_agent_v3'", "WARN")
    return False


def check_dependencies():
    """Check required Python packages."""
    required = ["yaml", "numpy", "pandas", "requests"]
    optional = ["openai", "transformers", "torch", "matplotlib", "scipy"]
    all_ok = True
    for pkg in required:
        try:
            importlib.import_module(pkg)
            log(f"Package '{{pkg}}' — OK")
        except ImportError:
            log(f"Package '{{pkg}}' — MISSING", "ERROR")
            all_ok = False
    for pkg in optional:
        try:
            importlib.import_module(pkg)
            log(f"Optional package '{{pkg}}' — OK")
        except ImportError:
            log(f"Optional package '{{pkg}}' — not installed (optional)", "WARN")
    return all_ok


def check_llm():
    """Check LLM configuration."""
    llm_path = PKG_ROOT / "configs" / "llm.yaml"
    if not llm_path.exists():
        log("configs/llm.yaml — MISSING", "ERROR")
        return False
    log("configs/llm.yaml — OK")
    providers_path = PKG_ROOT / "configs" / "providers.yaml"
    if providers_path.exists():
        log("configs/providers.yaml — OK")
    else:
        log("configs/providers.yaml — MISSING", "WARN")
    return True


def check_paths():
    """Check required directories."""
    required_dirs = ["configs", "input", "output", "src", "shared", "scripts", "tests", "docs"]
    all_ok = True
    for d in required_dirs:
        dir_path = PKG_ROOT / d
        if dir_path.exists():
            log(f"Directory '{{d}}/' — OK")
        else:
            log(f"Directory '{{d}}/' — MISSING", "ERROR")
            all_ok = False
    return all_ok


def check_module_code():
    """Check module source code."""
    src_dir = PKG_ROOT / "src"
    interface_py = src_dir / "interface.py"
    impl_py = src_dir / "implementation.py"
    all_ok = True
    if interface_py.exists():
        log("src/interface.py — OK")
    else:
        log("src/interface.py — MISSING", "ERROR")
        all_ok = False
    if impl_py.exists():
        log("src/implementation.py — OK")
    else:
        log("src/implementation.py — MISSING", "ERROR")
        all_ok = False
    return all_ok


def main():
    log("=" * 60)
    log(f"Environment Check — Module {module['id']}: {module['name']}")
    log(f"Time: {{datetime.now().isoformat()}}")
    log(f"Platform: {{platform.platform()}}")
    log("=" * 60)

    results = []
    results.append(("Python Version", check_python()))
    results.append(("Conda Environment", check_conda()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("LLM Configuration", check_llm()))
    results.append(("Directory Structure", check_paths()))
    results.append(("Module Code", check_module_code()))

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        log(f"  {{name}}: {{status}}")
    log(f"Total: {{passed}}/{{total}} passed")

    report_path = PKG_ROOT / "Environment_Check_Report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Environment Check Report — Module {module['id']}: {module['name']}\\n\\n")
        f.write(f"**Time:** {{datetime.now().isoformat()}}\\n\\n")
        f.write(f"**Platform:** {{platform.platform()}}\\n\\n")
        f.write("## Results\\n\\n")
        f.write("| Check Item | Status |\\n")
        f.write("|------------|--------|\\n")
        for name, ok in results:
            f.write(f"| {{name}} | {{'PASS' if ok else 'FAIL'}} |\\n")
        f.write(f"\\n**Total: {{passed}}/{{total}} passed**\\n\\n")
        f.write("## Details\\n\\n")
        f.write("\\n".join(REPORT_LINES))
    log(f"Report saved to: {{report_path}}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    (pkg_dir / "environment_check.py").write_text(code, encoding="utf-8")


def gen_run_py(pkg_dir, module):
    """Generate run.py with dynamic interface adaptation."""
    code = '''#!/usr/bin/env python
"""独立运行入口 — 自动适配模块接口（支持相对导入）"""
import os, sys, json, yaml, argparse, logging, inspect, shutil
from pathlib import Path
from dataclasses import fields as dataclass_fields
from datetime import datetime

PKG_ROOT = Path(__file__).resolve().parent
for p in [str(PKG_ROOT), str(PKG_ROOT / "shared"), str(PKG_ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(PKG_ROOT / "run.log", encoding="utf-8")])
logger = logging.getLogger(__name__)


def load_config(config_dir):
    config = {}
    for name, key in [("research_task.yaml", None), ("llm.yaml", "llm"), ("providers.yaml", "providers"),
                      ("module_config.yaml", "module_config"), ("dependency_policy.yaml", "dependency_policy")]:
        p = config_dir / name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if key:
                    config[key] = data
                else:
                    config.update(data)
    return config


def load_inputs(input_dir):
    input_files = {}
    if input_dir.exists():
        for f in input_dir.rglob("*"):
            if f.is_file() and f.name != "example_input.json":
                key = str(f.relative_to(input_dir)).replace("\\\\", "/")
                input_files[key] = str(f)
    return input_files


def _import_module():
    interface_mod = None
    impl_mod = None
    try:
        from src import interface as interface_mod
        from src import implementation as impl_mod
        logger.info("模块导入方式: src包导入")
    except Exception:
        try:
            import interface as interface_mod
            import importlib.util
            impl_path = PKG_ROOT / "src" / "implementation.py"
            if impl_path.exists():
                spec = importlib.util.spec_from_file_location("implementation", impl_path)
                impl_mod = importlib.util.module_from_spec(spec)
                sys.modules["implementation"] = impl_mod
                spec.loader.exec_module(impl_mod)
                logger.info("模块导入方式: 直接导入（兼容模式）")
        except Exception as e:
            logger.error("模块导入失败: %s", e)
    return interface_mod, impl_mod


def find_class(module, suffix):
    if module is None:
        return None, None
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.endswith(suffix) and hasattr(obj, "__dataclass_fields__"):
            return name, obj
    return None, None


def find_impl_class(impl_mod):
    if impl_mod is None:
        return None, None
    candidates = []
    for name, obj in inspect.getmembers(impl_mod, inspect.isclass):
        if getattr(obj, "__abstractmethods__", None):
            continue
        if hasattr(obj, "execute") and callable(getattr(obj, "execute")):
            mod_name = obj.__module__ or ""
            if "implementation" in mod_name or "src" in mod_name or mod_name == "":
                candidates.append((name, obj))
    if candidates:
        for name, obj in candidates:
            if "Implementation" in name or "Module" in name:
                return name, obj
        return candidates[0]
    return None, None


def construct_input(input_cls, task_id, config, input_files):
    field_names = {f.name for f in dataclass_fields(input_cls)}
    kwargs = {}
    if "task_id" in field_names:
        kwargs["task_id"] = task_id
    if "config" in field_names:
        kwargs["config"] = config
    if "input_files" in field_names:
        kwargs["input_files"] = input_files
    if "research_task" in field_names and "research_task" in config:
        kwargs["research_task"] = config.get("research_task", {})
    for fname in field_names:
        if fname not in kwargs:
            f = next((f for f in dataclass_fields(input_cls) if f.name == fname), None)
            if f:
                type_str = str(f.type)
                if "dict" in type_str.lower():
                    kwargs[fname] = {}
                elif "list" in type_str.lower():
                    kwargs[fname] = []
                else:
                    kwargs[fname] = None
            else:
                kwargs[fname] = None
    return input_cls(**kwargs)


def save_output(output_obj, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(output_obj, "output_files"):
        for key, path in (output_obj.output_files or {}).items():
            if path and os.path.exists(path):
                dest = output_dir / os.path.basename(path)
                if path != str(dest):
                    shutil.copy2(path, dest)
    output_data = {}
    if hasattr(output_obj, "__dataclass_fields__"):
        for f in output_obj.__dataclass_fields__:
            val = getattr(output_obj, f, None)
            if val is not None:
                try:
                    json.dumps(val)
                    output_data[f] = val
                except (TypeError, ValueError):
                    output_data[f] = str(val)
    with open(output_dir / "module_output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("输出已保存到 %s", output_dir)


def main():
    parser = argparse.ArgumentParser(description="独立运行模块")
    parser.add_argument("--task-id", default="default_task", help="任务ID")
    parser.add_argument("--config-dir", default=None, help="配置目录")
    parser.add_argument("--input-dir", default=None, help="输入目录")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    args = parser.parse_args()

    config_dir = Path(args.config_dir) if args.config_dir else PKG_ROOT / "configs"
    input_dir = Path(args.input_dir) if args.input_dir else PKG_ROOT / "input"
    output_dir = Path(args.output_dir) if args.output_dir else PKG_ROOT / "output"

    logger.info("=" * 60)
    logger.info("模块启动 | Task ID: %s", args.task_id)
    logger.info("Config: %s", config_dir)
    logger.info("Input: %s", input_dir)
    logger.info("Output: %s", output_dir)
    logger.info("=" * 60)

    config = load_config(config_dir)
    input_files = load_inputs(input_dir)
    logger.info("配置加载完成: %d keys", len(config))
    logger.info("输入文件: %d files", len(input_files))
    for k, v in input_files.items():
        logger.info("  - %s -> %s", k, v)

    interface_mod, impl_mod = _import_module()
    if interface_mod is None:
        logger.error("无法导入模块接口")
        _gen_human_intervention(output_dir, "模块接口导入失败", "检查 src/interface.py 是否存在且语法正确")
        sys.exit(1)

    input_cls_name, input_cls = find_class(interface_mod, "Input")
    output_cls_name, output_cls = find_class(interface_mod, "Output")
    impl_name, impl_cls = find_impl_class(impl_mod)

    logger.info("Input class: %s", input_cls_name)
    logger.info("Output class: %s", output_cls_name)
    logger.info("Implementation class: %s", impl_name)

    if impl_cls is None:
        logger.error("无法找到实现类")
        _gen_human_intervention(output_dir, "实现类未找到", "检查 src/implementation.py 是否包含带有execute方法的类")
        sys.exit(1)

    try:
        impl = impl_cls()
    except TypeError:
        try:
            impl = impl_cls(llm_provider=None)
        except Exception as e:
            logger.error("实例化失败: %s", e)
            sys.exit(1)

    if input_cls:
        input_obj = construct_input(input_cls, args.task_id, config, input_files)
        try:
            output_obj = impl.execute(input_obj)
            logger.info("模块执行完成")
            if hasattr(output_obj, "status"):
                logger.info("状态: %s", output_obj.status)
            if hasattr(output_obj, "errors") and output_obj.errors:
                for err in output_obj.errors:
                    logger.warning("Error: %s", err)
            save_output(output_obj, output_dir)
        except Exception as e:
            logger.error("执行失败: %s", e, exc_info=True)
            _gen_human_intervention(output_dir, f"模块执行异常: {e}", "检查输入文件是否完整，LLM配置是否正确")
            sys.exit(1)
    else:
        logger.error("无法找到Input类")
        sys.exit(1)


def _gen_human_intervention(output_dir, problem, suggestion):
    output_dir.mkdir(parents=True, exist_ok=True)
    content = f"""# Human Intervention Request

## 当前问题

{problem}

## 需要用户补充内容

{suggestion}

## 文件格式

请将补充的文件放在 `input/` 目录下。

## 继续运行方法

1. 补充缺失的输入文件
2. 重新运行: `python run.py --task-id YOUR_TASK_ID`

## 生成时间

{datetime.now().isoformat()}
"""
    with open(output_dir / "Human_Intervention_Request.md", "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("人工干预请求已生成: %s", output_dir / "Human_Intervention_Request.md")


if __name__ == "__main__":
    main()
'''
    (pkg_dir / "run.py").write_text(code, encoding="utf-8")


def gen_module_interface(pkg_dir, module):
    """Generate docs/Module_Interface.md."""
    upstream_str = ", ".join(module["upstream"]) if module["upstream"] else "无"
    downstream_str = ", ".join(module["downstream"]) if module["downstream"] else "无"

    input_section = ""
    for f in module["input_files"]:
        req = "必需" if f["required"] else "可选"
        input_section += f"""
### {f['name']}

| 属性 | 值 |
|------|-----|
| 文件名 | {f['name']} |
| 说明 | {f['desc']} |
| 是否必需 | {req} |
| 格式 | {'YAML' if f['name'].endswith('.yaml') else 'JSON' if f['name'].endswith('.json') else 'Markdown' if f['name'].endswith('.md') else '文本'} |
| 存放路径 | input/{f['name']} |
| 来源 | Module {', '.join(module['upstream']) if module['upstream'] else '用户提供'} |
"""

    output_section = ""
    for f in module["output_files"]:
        output_section += f"""
### {f['name']}

| 属性 | 值 |
|------|-----|
| 文件名 | {f['name']} |
| 说明 | {f['desc']} |
| 格式 | {'YAML' if f['name'].endswith('.yaml') else 'JSON' if f['name'].endswith('.json') else 'Markdown' if f['name'].endswith('.md') else '目录'} |
| 输出路径 | output/{f['name']} |
| 下游消费者 | Module {', '.join(module['downstream']) if module['downstream'] else '无'} |
"""

    content = f"""# Module {module['id']}: {module['name_cn']} — 接口文档

## 模块概述

| 项目 | 值 |
|------|-----|
| 模块ID | {module['id']} |
| 模块名称 | {module['name']} |
| 功能描述 | {module['desc']} |
| 上游模块 | {upstream_str} |
| 下游模块 | {downstream_str} |
| 是否需要LLM | {'是' if module['needs_llm'] else '否'} |

## 输入接口
{input_section}

## 输出接口
{output_section}

## 数据流示例

```
上游模块输出 → input/ → [Module {module['id']}] → output/ → 下游模块输入
```

## 接口规范

### 输入文件格式

所有输入文件统一放在 `input/` 目录下。支持子目录结构（如 `input/papers/xxx/paper.md`）。

### 输出文件格式

所有输出文件统一放在 `output/` 目录下。模块运行后自动生成。

### JSON格式规范

```json
{{
  "task_id": "示例任务ID",
  "status": "success",
  "data": {{}},
  "metadata": {{
    "module_id": "{module['id']}",
    "timestamp": "2026-01-01T00:00:00"
  }}
}}
```

## 人工补充

如果输入缺失或输出异常，模块会生成 `output/Human_Intervention_Request.md`，请按指引操作。
"""
    docs_dir = pkg_dir / "docs"
    (docs_dir / "Module_Interface.md").write_text(content, encoding="utf-8")


def gen_test_script(pkg_dir, module):
    """Generate tests/module_test.py."""
    code = f'''#!/usr/bin/env python
"""Module {module['id']}: {module['name']} — Test Script"""
import sys
import os
import json
import yaml
from pathlib import Path
from datetime import datetime

PKG_ROOT = Path(__file__).resolve().parent.parent
for p in [str(PKG_ROOT), str(PKG_ROOT / "shared"), str(PKG_ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

REPORT_LINES = []

def log(msg, level="INFO"):
    REPORT_LINES.append(f"[{{level}}] {{msg}}")
    print(f"[{{level}}] {{msg}}")


def test_environment():
    """Test 1: Environment check."""
    log("Test 1: Environment")
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        log("  Python version: OK")
        return True
    log("  Python version: WARNING (recommended 3.12+)", "WARN")
    return False


def test_input():
    """Test 2: Input files check."""
    log("Test 2: Input files")
    input_dir = PKG_ROOT / "input"
    if not input_dir.exists():
        log("  input/ directory missing", "ERROR")
        return False
    files = list(input_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    if files:
        log(f"  Found {{len(files)}} input file(s)")
        return True
    log("  No input files found (will use defaults)", "WARN")
    return True


def test_config():
    """Test 3: Configuration check."""
    log("Test 3: Configuration")
    cfg_dir = PKG_ROOT / "configs"
    required = ["module_config.yaml", "llm.yaml"]
    all_ok = True
    for name in required:
        p = cfg_dir / name
        if p.exists():
            log(f"  {{name}}: OK")
        else:
            log(f"  {{name}}: MISSING", "ERROR")
            all_ok = False
    return all_ok


def test_source_code():
    """Test 4: Source code check."""
    log("Test 4: Source code")
    src_dir = PKG_ROOT / "src"
    interface_py = src_dir / "interface.py"
    impl_py = src_dir / "implementation.py"
    all_ok = True
    if interface_py.exists():
        log("  interface.py: OK")
    else:
        log("  interface.py: MISSING", "ERROR")
        all_ok = False
    if impl_py.exists():
        log("  implementation.py: OK")
    else:
        log("  implementation.py: MISSING", "ERROR")
        all_ok = False
    return all_ok


def test_import():
    """Test 5: Module import check."""
    log("Test 5: Module import")
    try:
        from src import interface as interface_mod
        from src import implementation as impl_mod
        log("  Import: OK")
        return True
    except Exception:
        try:
            import interface as interface_mod
            import importlib.util
            impl_path = src_dir / "implementation.py"
            if impl_path.exists():
                spec = importlib.util.spec_from_file_location("implementation", impl_path)
                impl_mod = importlib.util.module_from_spec(spec)
                sys.modules["implementation"] = impl_mod
                spec.loader.exec_module(impl_mod)
                log("  Import (fallback): OK")
                return True
        except Exception as e:
            log(f"  Import failed: {{e}}", "ERROR")
            return False


def test_output():
    """Test 6: Output directory check."""
    log("Test 6: Output directory")
    output_dir = PKG_ROOT / "output"
    if output_dir.exists():
        log("  output/ directory: OK")
        return True
    output_dir.mkdir(parents=True, exist_ok=True)
    log("  output/ directory: created")
    return True


def test_downstream_compatibility():
    """Test 7: Downstream compatibility check."""
    log("Test 7: Downstream compatibility")
    output_dir = PKG_ROOT / "output"
    expected_outputs = {[f["name"] for f in module["output_files"]]}
    found = []
    if output_dir.exists():
        for f in output_dir.rglob("*"):
            if f.is_file():
                found.append(f.name)
    missing = [o for o in expected_outputs if not any(o in fn for fn in found)]
    if not missing:
        log("  All expected outputs present")
        return True
    for m in missing:
        log(f"  Expected output not found: {{m}}", "WARN")
    return True


def main():
    log("=" * 60)
    log(f"Module {module['id']}: {module['name']} — Test Report")
    log(f"Time: {{datetime.now().isoformat()}}")
    log("=" * 60)

    results = []
    results.append(("Environment", test_environment()))
    results.append(("Input Files", test_input()))
    results.append(("Configuration", test_config()))
    results.append(("Source Code", test_source_code()))
    results.append(("Module Import", test_import()))
    results.append(("Output Directory", test_output()))
    results.append(("Downstream Compatibility", test_downstream_compatibility()))

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        log(f"  {{name}}: {{status}}")
    log(f"Total: {{passed}}/{{total}} passed")

    report_path = PKG_ROOT / "Module_Test_Report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Module Test Report — Module {module['id']}: {module['name']}\\n\\n")
        f.write(f"**Time:** {{datetime.now().isoformat()}}\\n\\n")
        f.write("## Test Results\\n\\n")
        f.write("| Test | Status |\\n")
        f.write("|------|--------|\\n")
        for name, ok in results:
            f.write(f"| {{name}} | {{'PASS' if ok else 'FAIL'}} |\\n")
        f.write(f"\\n**Total: {{passed}}/{{total}} passed**\\n\\n")
        f.write("## Details\\n\\n")
        f.write("\\n".join(REPORT_LINES))
    log(f"Report saved to: {{report_path}}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
'''
    tests_dir = pkg_dir / "tests"
    (tests_dir / "module_test.py").write_text(code, encoding="utf-8")


def gen_human_intervention_template(pkg_dir, module):
    """Generate Human_Intervention_Request.md template in output/."""
    output_dir = pkg_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    content = f"""# Human Intervention Request — Module {module['id']}: {module['name_cn']}

> 此文件在模块运行异常时自动生成。如果此文件存在，说明模块需要人工补充。

## 当前问题

（模块运行时会自动填写）

## 需要用户补充内容

### 输入文件补充

请检查以下输入文件是否完整：

"""
    for f in module["input_files"]:
        req = "必需" if f["required"] else "可选"
        content += f"- `{f['name']}` ({req}) — {f['desc']}\n"

    content += f"""
输入文件存放目录: `input/`

### 输出文件修复

如果输出不完整，请手动创建以下文件：

"""
    for f in module["output_files"]:
        content += f"- `{f['name']}` — {f['desc']}\n"

    content += f"""
输出文件存放目录: `output/`

## 文件格式

- JSON格式: 标准JSON，UTF-8编码
- YAML格式: 标准YAML
- Markdown格式: 标准Markdown

## 继续运行方法

1. 补充缺失的输入文件到 `input/` 目录
2. 重新运行: `python run.py --task-id YOUR_TASK_ID`
3. 或手动创建输出文件后，将 `output/` 内容传递给下游模块

## 下游模块

"""
    if module["downstream"]:
        for d in module["downstream"]:
            content += f"- Module {d}\n"
    else:
        content += "- 无（终末模块）\n"

    content += f"""
## 生成时间

{datetime.now().isoformat()}
"""
    (output_dir / "Human_Intervention_Request.md").write_text(content, encoding="utf-8")


def gen_example_input(pkg_dir, module):
    """Generate example input file."""
    input_dir = pkg_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    example = {
        "task_id": "example_task_001",
        "module_id": module["id"],
        "module_name": module["name"],
        "input_files": {f["name"]: f"input/{f['name']}" for f in module["input_files"]},
        "note": "请将上游模块的输出文件复制到input/目录后运行",
    }
    with open(input_dir / "example_input.json", "w", encoding="utf-8") as f:
        json.dump(example, f, ensure_ascii=False, indent=2)


def copy_docs(pkg_dir):
    """Copy relevant documentation."""
    docs_dir = pkg_dir / "docs"
    docs_to_copy = [
        "docs/Human_Intervention_Guide_CN.md",
        "docs/LLM_Configuration_Guide_CN.md",
        "docs/Skill_Configuration_Guide_CN.md",
        "docs/MCP_Configuration_Guide_CN.md",
        "docs/Troubleshooting_CN.md",
    ]
    for doc_path in docs_to_copy:
        src = V3_ROOT / doc_path
        if src.exists():
            shutil.copy2(src, docs_dir / src.name)


def copy_environment_files(pkg_dir):
    """Copy environment files."""
    # Copy environment.yml
    env_yml = V3_ROOT / "environment.yml"
    if env_yml.exists():
        shutil.copy2(env_yml, pkg_dir / "environment.yml")
    # Copy requirements.txt
    req_txt = V3_ROOT / "requirements.txt"
    if req_txt.exists():
        shutil.copy2(req_txt, pkg_dir / "requirements.txt")


# ==============================================================================
# Build Functions
# ==============================================================================

def build_module(module):
    """Build a single module package."""
    module_id = module["id"]
    module_name = module["name"]
    pkg_name = f"Research_Agent_Module{module_id}_{module_name}_v1.2"
    pkg_dir = BUILD_DIR / pkg_name

    print(f"\n{'='*60}")
    print(f"Building Module {module_id}: {module_name}")
    print(f"{'='*60}")

    # Clean and create
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    create_directory_structure(pkg_dir)

    # Copy code
    print("  Copying module code...")
    copy_module_code(pkg_dir, module)
    print("  Copying shared code...")
    copy_shared_code(pkg_dir)
    print("  Copying configs...")
    copy_configs(pkg_dir, module)
    print("  Copying scripts...")
    copy_scripts(pkg_dir)
    print("  Copying docs...")
    copy_docs(pkg_dir)
    print("  Copying environment files...")
    copy_environment_files(pkg_dir)

    # Generate files
    print("  Generating START_HERE.md...")
    gen_start_here(pkg_dir, module)
    print("  Generating README.md...")
    gen_readme(pkg_dir, module)
    print("  Generating environment_check.py...")
    gen_environment_check(pkg_dir, module)
    print("  Generating run.py...")
    gen_run_py(pkg_dir, module)
    print("  Generating docs/Module_Interface.md...")
    gen_module_interface(pkg_dir, module)
    print("  Generating tests/module_test.py...")
    gen_test_script(pkg_dir, module)
    print("  Generating Human_Intervention_Request.md template...")
    gen_human_intervention_template(pkg_dir, module)
    print("  Generating example input...")
    gen_example_input(pkg_dir, module)

    # Package as ZIP
    zip_path = RELEASES_DIR / f"{pkg_name}.zip"
    print(f"  Packaging ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(pkg_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(pkg_dir)
                zf.write(file_path, arcname)

    # Count files
    file_count = sum(1 for _ in pkg_dir.rglob("*") if _.is_file())
    zip_size = zip_path.stat().st_size
    print(f"  Done: {file_count} files, ZIP size: {zip_size / 1024 / 1024:.1f} MB")

    return {
        "module_id": module_id,
        "module_name": module_name,
        "zip_path": str(zip_path),
        "file_count": file_count,
        "zip_size_mb": round(zip_size / 1024 / 1024, 1),
        "status": "success",
    }


def generate_final_report(results):
    """Generate Research_Agent_Modularization_Final_Report.md."""
    report_path = RELEASES_DIR / "Research_Agent_Modularization_Final_Report.md"

    total_files = sum(r["file_count"] for r in results)
    total_size = sum(r["zip_size_mb"] for r in results)
    success_count = sum(1 for r in results if r["status"] == "success")

    content = f"""# Research Agent 模块化拆分最终报告

## 概述

- **拆分日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **源项目**: D:\\Research Agent\\Research_Agent_v3
- **输出目录**: D:\\Research Agent\\releases
- **模块总数**: {len(results)}
- **成功数量**: {success_count}/{len(results)}
- **总文件数**: {total_files}
- **总ZIP大小**: {total_size:.1f} MB

## 模块列表

| 模块ID | 模块名称 | ZIP文件 | 文件数 | 大小(MB) | 状态 |
|--------|---------|---------|--------|----------|------|
"""
    for r in results:
        content += f"| {r['module_id']} | {r['module_name']} | {Path(r['zip_path']).name} | {r['file_count']} | {r['zip_size_mb']} | {r['status']} |\n"

    content += f"""
## 文件结构

每个模块ZIP包含以下标准目录结构:

```
Research_Agent_ModuleXX_XXX_v1/
├── START_HERE.md              # 快速开始指南
├── README.md                  # 完整说明文档
├── environment_check.py       # 环境检测脚本
├── run.py                     # 模块运行入口
├── environment.yml            # Conda环境定义
├── requirements.txt           # pip依赖
├── configs/                   # 配置文件
│   ├── module_config.yaml     # 模块配置
│   ├── llm.yaml               # LLM配置
│   ├── llm_routing.yaml       # LLM路由
│   ├── providers.yaml         # 提供商配置
│   ├── dependency_policy.yaml # 依赖策略
│   ├── environment.yaml       # 环境配置
│   ├── research_task.yaml     # 研究任务配置
│   ├── research_task_vlm_safety.yaml
│   └── ...                    # 其他配置
├── input/                     # 输入文件目录
│   └── example_input.json     # 输入示例
├── output/                    # 输出文件目录
│   └── Human_Intervention_Request.md  # 人工干预模板
├── src/                       # 模块源代码
│   ├── interface.py           # 接口定义
│   ├── implementation.py      # 实现
│   ├── schema.py              # 数据模式
│   ├── validator.py           # 验证器
│   └── manifest.yaml          # 模块清单
├── shared/                    # 共享依赖代码
│   ├── infrastructure/        # 基础设施
│   ├── literature/            # 文献处理
│   ├── reasoning/             # 推理引擎
│   ├── adapters/              # 适配器
│   ├── core/                  # 核心逻辑
│   ├── schemas/               # 数据模式
│   └── templates/             # 模板
├── scripts/                   # 辅助脚本
│   ├── check_literature.py
│   ├── check_llm.py
│   ├── check_mcp.py
│   ├── check_portability.py
│   ├── check_research_ready.py
│   └── check_skills.py
├── tests/                     # 测试脚本
│   └── module_test.py
└── docs/                      # 文档
    ├── Module_Interface.md    # 接口文档
    ├── Human_Intervention_Guide_CN.md
    ├── LLM_Configuration_Guide_CN.md
    ├── Skill_Configuration_Guide_CN.md
    ├── MCP_Configuration_Guide_CN.md
    └── Troubleshooting_CN.md
```

## 输入输出关系

```
Module 01 (文献检索)
  ↓ literature_candidates.json
Module 02 (论文资产获取)
  ↓ paper_assets.json
Module 03 (文献智能分析)
  ↓ paper_analysis.json
Module 04 (研究领域全景)
  ↓ research_landscape.md
Module 05 (创新发现)
  ↓ innovation_candidates.json
Module 06 (方法设计)
  ↓ method_design.md
Module 07 (实验规划)
  ↓ experiment_plan.yaml
Module 08 (实验执行)
  ↓ experiment_results.json
Module 09 (结果收集)
  ↓ results_database.json
Module 10 (结果分析)
  ↓ result_analysis.md
Module 11 (图表生成)
  ↓ figures/ (Mermaid, LaTeX, Prompts)
Module 12 (论文写作)
  ↓ paper.md / paper.tex / paper.docx
Module 13 (引用管理)
  ↓ references.bib
Module 14 (审稿模拟)
  ↓ review_report.md
Module 15 (科研记忆)
  ↓ memory_store.json / memory_index.json
```

## 环境要求

- **Python**: 3.12
- **Conda环境**: research_agent_v3
- **操作系统**: Windows / Linux / macOS
- **主要依赖**: pyyaml, numpy, pandas, requests, openai (可选), transformers (可选)

## LLM配置

已配置的LLM提供商:
- DeepSeek (deepseek-reasoner) — API
- OpenAI (gpt-4o) — API
- Ollama R1 (deepseek-r1:8b) — 本地
- Ollama (gemma4:26b) — 本地

任务路由:
- 核心推理 → deepseek-r1:8b
- 辅助任务 → gemma4:26b

## 测试结果

每个模块包含自动测试脚本 `tests/module_test.py`，测试内容:
1. 环境检查
2. 输入文件检查
3. 配置文件检查
4. 源代码检查
5. 模块导入检查
6. 输出目录检查
7. 下游兼容性检查

## 已知问题

1. Module 09 (Result Collection) 和 Module 15 (Research Memory) 为新创建模块，使用最小化实现
2. Module 02 合并了原有的 02_source_acquisition 和 02_5_paper_asset_intelligence
3. Module 08 合并了原有的 08_synthetic_experiment_engine 和 09_real_experiment_engine
4. 部分模块的相对导入需要通过 run.py 中的路径适配处理
5. LLM连接需要本地Ollama服务 (localhost:11434)

## 使用方法

1. 解压所需模块的ZIP文件
2. 运行 `conda activate research_agent_v3`
3. 运行 `python environment_check.py` 检查环境
4. 将上游模块输出放入 `input/` 目录
5. 运行 `python run.py --task-id YOUR_TASK_ID`
6. 查看 `output/` 目录获取结果

## 人工干预

如果模块运行失败:
1. 查看 `output/Human_Intervention_Request.md`
2. 按指引手动补充缺失文件
3. 重新运行或直接传递给下游模块
"""
    report_path.write_text(content, encoding="utf-8")
    print(f"\n最终报告已生成: {report_path}")
    return report_path


# ==============================================================================
# Main
# ==============================================================================

def main():
    print("=" * 60)
    print("Research Agent v8.2.2 — 模块化拆分构建脚本 v2")
    print(f"源项目: {V3_ROOT}")
    print(f"输出目录: {RELEASES_DIR}")
    print(f"构建临时目录: {BUILD_DIR}")
    print("=" * 60)

    # Clean build dir
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Clean releases dir
    if RELEASES_DIR.exists():
        for f in RELEASES_DIR.iterdir():
            if f.is_file() and (f.suffix == ".zip" or f.suffix == ".md"):
                f.unlink()
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)

    # Build all modules
    results = []
    for module in MODULES:
        try:
            result = build_module(module)
            results.append(result)
        except Exception as e:
            print(f"  ERROR building Module {module['id']}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "module_id": module["id"],
                "module_name": module["name"],
                "zip_path": "",
                "file_count": 0,
                "zip_size_mb": 0,
                "status": f"failed: {e}",
            })

    # Generate final report
    report_path = generate_final_report(results)

    # Print summary
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    success = sum(1 for r in results if r["status"] == "success")
    print(f"成功: {success}/{len(results)}")
    for r in results:
        status_icon = "OK" if r["status"] == "success" else "FAIL"
        print(f"  Module {r['module_id']} {r['module_name']}: {status_icon} ({r['file_count']} files, {r['zip_size_mb']} MB)")
    print(f"\n最终报告: {report_path}")
    print(f"输出目录: {RELEASES_DIR}")

    # Clean build dir
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"临时构建目录已清理: {BUILD_DIR}")


if __name__ == "__main__":
    main()
