#!/usr/bin/env python
"""
Build script: Generate 15 independent module packages as ZIP files.
Each package is self-contained and can run independently.

Usage:
    conda activate research_agent_v3
    python build_packages.py
"""

import os
import sys
import shutil
import zipfile
import json
import yaml
import textwrap
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parent
RELEASES_DIR = Path("D:/Research Agent/releases")
BUILD_DIR = V3_ROOT / "_build_packages"

# ─── Module metadata ───
MODULES = [
    {
        "id": "01", "dir": "01_literature_retrieval", "zip": "Module_01_Literature_Retrieval",
        "name_cn": "文献检索", "name_en": "Literature Retrieval",
        "desc": "根据研究任务从arXiv、Semantic Scholar等数据库检索相关文献，生成元数据、下载队列和文献清单。",
        "upstream": [], "downstream": ["02", "03"],
        "inputs": [{"name": "research_task.yaml", "desc": "研究任务配置文件", "required": True}],
        "outputs": [
            {"name": "literature_manifest.json", "desc": "文献清单总览"},
            {"name": "paper_metadata.jsonl", "desc": "论文元数据（JSONL格式）"},
            {"name": "download_queue.json", "desc": "下载队列"},
        ],
        "needs_llm": False,
    },
    {
        "id": "02", "dir": "02_source_acquisition", "zip": "Module_02_Source_Acquisition",
        "name_cn": "论文下载与解析", "name_en": "Source Acquisition & Parsing",
        "desc": "从下载队列获取论文PDF，解析为归一化Markdown，提取公式、图表、表格和引用信息。",
        "upstream": ["01"], "downstream": ["03"],
        "inputs": [{"name": "download_queue.json", "desc": "Module 01生成的下载队列", "required": True}],
        "outputs": [
            {"name": "papers/<paper_id>/normalized/paper.md", "desc": "归一化论文Markdown"},
            {"name": "papers/<paper_id>/equations.json", "desc": "公式提取结果"},
            {"name": "papers/<paper_id>/figures.json", "desc": "图表信息"},
            {"name": "papers/<paper_id>/tables.json", "desc": "表格信息"},
            {"name": "papers/<paper_id>/citations.json", "desc": "引用信息"},
            {"name": "papers/<paper_id>/provenance.json", "desc": "溯源信息"},
        ],
        "needs_llm": False,
    },
    {
        "id": "02_5", "dir": "02_5_paper_asset_intelligence", "zip": "Module_02_5_Paper_Asset_Intelligence",
        "name_cn": "论文图片提取", "name_en": "Paper Asset Intelligence",
        "desc": "从每篇论文中提取前3张核心图片并保存，优先使用arXiv LaTeX源码，回退到PDF提取。",
        "upstream": ["02"], "downstream": ["03", "12"],
        "inputs": [{"name": "paper_metadata.jsonl", "desc": "Module 01生成的论文元数据", "required": True}],
        "outputs": [
            {"name": "paper_assets.json", "desc": "图片资产清单"},
            {"name": "assets/figure_*.png", "desc": "提取的图片文件"},
        ],
        "needs_llm": False,
    },
    {
        "id": "03", "dir": "03_literature_intelligence", "zip": "Module_03_Literature_Intelligence",
        "name_cn": "文献智能分析", "name_en": "Literature Intelligence",
        "desc": "对归一化论文进行深度分析，提取贡献点、方法、数据集、局限性和论文间关系。",
        "upstream": ["02"], "downstream": ["04", "05"],
        "inputs": [{"name": "papers/<paper_id>/normalized/paper.md", "desc": "Module 02生成的归一化论文", "required": True}],
        "outputs": [
            {"name": "paper_analysis.json", "desc": "单篇论文分析结果"},
            {"name": "paper_analysis.md", "desc": "分析报告Markdown"},
            {"name": "literature_analysis_index.jsonl", "desc": "跨论文索引"},
        ],
        "needs_llm": True,
    },
    {
        "id": "04", "dir": "04_research_landscape", "zip": "Module_04_Research_Landscape",
        "name_cn": "研究全景与空白分析", "name_en": "Research Landscape & Gap Analysis",
        "desc": "将单篇分析综合为研究全景，构建分类体系、趋势分析、矛盾图谱，识别研究空白候选点。",
        "upstream": ["03"], "downstream": ["05"],
        "inputs": [{"name": "paper_analysis.json", "desc": "Module 03生成的论文分析", "required": True}],
        "outputs": [
            {"name": "research_landscape.md", "desc": "研究全景报告"},
            {"name": "taxonomy.json", "desc": "分类体系"},
            {"name": "trend_analysis.json", "desc": "趋势分析"},
            {"name": "contradiction_map.json", "desc": "矛盾图谱"},
            {"name": "gap_candidates.json", "desc": "研究空白候选点"},
        ],
        "needs_llm": True,
    },
    {
        "id": "05", "dir": "05_innovation_reasoning", "zip": "Module_05_Innovation_Reasoning",
        "name_cn": "创新与新颖性推理", "name_en": "Innovation & Novelty Reasoning",
        "desc": "评估研究空白的新颖性和可行性，生成创新候选点并选出最终研究方向。",
        "upstream": ["03", "04"], "downstream": ["06"],
        "inputs": [
            {"name": "gap_candidates.json", "desc": "Module 04生成的空白候选点", "required": True},
            {"name": "paper_analysis.json", "desc": "Module 03生成的论文分析", "required": True},
        ],
        "outputs": [
            {"name": "innovation_candidates.json", "desc": "创新候选点"},
            {"name": "novelty_analysis.md", "desc": "新颖性分析报告"},
            {"name": "final_research_direction.md", "desc": "最终研究方向"},
        ],
        "needs_llm": True,
    },
    {
        "id": "06", "dir": "06_theory_method", "zip": "Module_06_Theory_Method",
        "name_cn": "理论与方法设计", "name_en": "Theory & Method Design",
        "desc": "基于选定研究方向，设计理论框架、方法规格、数学公式和算法设计。",
        "upstream": ["05"], "downstream": ["07", "08", "09", "11"],
        "inputs": [{"name": "final_research_direction.md", "desc": "Module 05选定的研究方向", "required": True}],
        "outputs": [
            {"name": "method_spec.json", "desc": "方法规格（核心文件）"},
            {"name": "theory_framework.md", "desc": "理论框架"},
            {"name": "method_design.md", "desc": "方法设计文档"},
            {"name": "mathematical_formulation.md", "desc": "数学公式推导"},
            {"name": "algorithm_design.md", "desc": "算法设计"},
        ],
        "needs_llm": True,
    },
    {
        "id": "07", "dir": "07_experiment_planning", "zip": "Module_07_Experiment_Planning",
        "name_cn": "实验规划", "name_en": "Experiment Planning",
        "desc": "将方法规格转化为具体实验计划，包含实验矩阵、Claim-Evidence映射和论文图表规划。",
        "upstream": ["06"], "downstream": ["08", "09", "10", "11"],
        "inputs": [{"name": "method_spec.json", "desc": "Module 06生成的方法规格", "required": True}],
        "outputs": [
            {"name": "experiment_plan.md", "desc": "实验计划文档"},
            {"name": "experiment_matrix.yaml", "desc": "实验矩阵"},
            {"name": "claim_evidence_plan.json", "desc": "Claim-Evidence映射"},
            {"name": "paper_figure_plan.yaml", "desc": "论文图表规划"},
        ],
        "needs_llm": True,
    },
    {
        "id": "08", "dir": "08_synthetic_experiment_engine", "zip": "Module_08_Synthetic_Experiment_Engine",
        "name_cn": "仿真实验引擎", "name_en": "Synthetic Experiment Engine",
        "desc": "基于方法规格和实验矩阵执行仿真实验，生成原始/处理后的结果、指标和统计。后端适配器（如SAMRA）可插拔。",
        "upstream": ["06", "07"], "downstream": ["10", "11"],
        "inputs": [
            {"name": "method_spec.json", "desc": "Module 06生成的方法规格", "required": True},
            {"name": "experiment_matrix.yaml", "desc": "Module 07生成的实验矩阵", "required": True},
            {"name": "claim_evidence_plan.json", "desc": "Module 07生成的Claim计划", "required": True},
        ],
        "outputs": [
            {"name": "synthetic_results/metrics.csv", "desc": "实验指标"},
            {"name": "synthetic_results/statistics.json", "desc": "统计结果"},
            {"name": "synthetic_results/figures/", "desc": "结果图表"},
            {"name": "synthetic_results/provenance.json", "desc": "溯源信息"},
        ],
        "needs_llm": False,
    },
    {
        "id": "09", "dir": "09_real_experiment_engine", "zip": "Module_09_Real_Experiment_Engine",
        "name_cn": "真实实验引擎", "name_en": "Real Experiment Engine",
        "desc": "执行真实实验，生成配置、代码、检查点、原始/处理结果、日志和环境快照。SAMRA为适配器插件。",
        "upstream": ["06", "07"], "downstream": ["10", "11"],
        "inputs": [
            {"name": "method_spec.json", "desc": "Module 06生成的方法规格", "required": True},
            {"name": "experiment_matrix.yaml", "desc": "Module 07生成的实验矩阵", "required": True},
            {"name": "claim_evidence_plan.json", "desc": "Module 07生成的Claim计划", "required": True},
        ],
        "outputs": [
            {"name": "experiments/<task_id>/config/", "desc": "实验配置"},
            {"name": "experiments/<task_id>/raw_results/", "desc": "原始结果"},
            {"name": "experiments/<task_id>/processed_results/", "desc": "处理结果"},
            {"name": "experiments/<task_id>/logs/", "desc": "实验日志"},
        ],
        "needs_llm": False,
    },
    {
        "id": "10", "dir": "10_result_analysis", "zip": "Module_10_Result_Analysis",
        "name_cn": "科学结果分析", "name_en": "Scientific Result Analysis",
        "desc": "将实验结果与Claim-Evidence计划对比分析，生成科学分析、Claim验证映射和路由决策。",
        "upstream": ["07", "08", "09"], "downstream": ["11"],
        "inputs": [
            {"name": "synthetic_results/", "desc": "Module 08生成的仿真结果", "required": True},
            {"name": "claim_evidence_plan.json", "desc": "Module 07生成的Claim计划", "required": True},
        ],
        "outputs": [
            {"name": "scientific_result_analysis.md", "desc": "科学结果分析"},
            {"name": "claim_evidence_mapping.md", "desc": "Claim验证映射"},
            {"name": "revision_recommendation.md", "desc": "修订建议"},
            {"name": "decision.json", "desc": "路由决策"},
        ],
        "needs_llm": True,
    },
    {
        "id": "11", "dir": "11_figure_table", "zip": "Module_11_Figure_Table_Generation",
        "name_cn": "图表生成", "name_en": "Figure & Table Generation",
        "desc": "从实验结果、方法规格和外部数据生成出版级图表，产出SVG/PDF图表+源数据+绘图规格+图注。",
        "upstream": ["06", "07", "08", "09"], "downstream": ["12"],
        "inputs": [
            {"name": "method_spec.json", "desc": "Module 06生成的方法规格", "required": True},
            {"name": "paper_figure_plan.yaml", "desc": "Module 07生成的图表规划", "required": True},
        ],
        "outputs": [
            {"name": "figures/*.svg", "desc": "SVG图表"},
            {"name": "figures/*.pdf", "desc": "PDF图表"},
            {"name": "tables/*.xlsx", "desc": "Excel表格"},
            {"name": "tables/*.csv", "desc": "CSV表格"},
            {"name": "captions/captions.yaml", "desc": "图注"},
        ],
        "needs_llm": False,
    },
    {
        "id": "12", "dir": "12_paper_writing", "zip": "Module_12_Paper_Writing",
        "name_cn": "论文写作", "name_en": "Paper Writing",
        "desc": "整合所有上游输出（图表、方法规格、结果、分析），生成完整研究论文的Markdown、LaTeX、Word三种格式。",
        "upstream": ["all"], "downstream": ["13"],
        "inputs": [
            {"name": "figures/", "desc": "Module 11生成的图表", "required": True},
            {"name": "tables/", "desc": "Module 11生成的表格", "required": True},
            {"name": "method_spec.json", "desc": "Module 06生成的方法规格", "required": True},
            {"name": "scientific_result_analysis.md", "desc": "Module 10生成的结果分析", "required": True},
        ],
        "outputs": [
            {"name": "paper/paper.md", "desc": "Markdown格式论文"},
            {"name": "paper/latex/", "desc": "LaTeX格式论文"},
            {"name": "paper/word/", "desc": "Word格式论文"},
        ],
        "needs_llm": True,
    },
    {
        "id": "13", "dir": "13_reference_supplementary", "zip": "Module_13_Reference_Supplementary",
        "name_cn": "引用与补充材料", "name_en": "Reference & Supplementary",
        "desc": "生成参考文献文件，验证引用与论文元数据的匹配，产出LaTeX和Word格式的补充材料。",
        "upstream": ["01", "12"], "downstream": [],
        "inputs": [
            {"name": "paper/", "desc": "Module 12生成的论文", "required": True},
            {"name": "paper_metadata.jsonl", "desc": "Module 01生成的论文元数据", "required": True},
        ],
        "outputs": [
            {"name": "references.bib", "desc": "BibTeX参考文献"},
            {"name": "citation_validation_report.md", "desc": "引用验证报告"},
            {"name": "supplementary.tex", "desc": "LaTeX补充材料"},
            {"name": "supplementary.docx", "desc": "Word补充材料"},
        ],
        "needs_llm": False,
    },
    {
        "id": "14", "dir": "14_reviewer_loop", "zip": "Module_14_Reviewer_Loop",
        "name_cn": "审稿循环", "name_en": "Reviewer Loop",
        "desc": "模拟同行评审（LLM驱动），生成审稿报告，读取Human-in-the-loop反馈，产出修订建议。",
        "upstream": ["12", "13"], "downstream": [],
        "inputs": [{"name": "paper/paper.md", "desc": "Module 12生成的论文", "required": True}],
        "outputs": [
            {"name": "review_report.md", "desc": "审稿报告"},
            {"name": "revision_recommendations.md", "desc": "修订建议"},
            {"name": "review_decision.json", "desc": "审稿决策"},
        ],
        "needs_llm": True,
    },
]

# ─── Shared directories to include in every package ───
SHARED_DIRS = ["infrastructure", "literature", "reasoning", "adapters", "core", "schemas", "templates"]
SHARED_CONFIGS = [
    "configs/llm.yaml", "configs/llm_routing.yaml", "configs/providers.yaml",
    "configs/dependency_policy.yaml", "configs/external_dependency.yaml",
    "configs/experiment_mode.yaml", "configs/figure_config.yaml",
    "configs/research_task_template.yaml",
]


def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)


def copy_shared_code(pkg_dir: Path):
    """Copy shared infrastructure code into package."""
    for d in SHARED_DIRS:
        src = V3_ROOT / d
        dst = pkg_dir / "shared" / d
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def copy_configs(pkg_dir: Path):
    """Copy config files into package."""
    cfg_dir = pkg_dir / "configs"
    cfg_dir.mkdir(exist_ok=True)
    for cfg in SHARED_CONFIGS:
        src = V3_ROOT / cfg
        if src.exists():
            shutil.copy2(src, cfg_dir / src.name)
    # Copy research_task.yaml as default
    task_src = V3_ROOT / "configs" / "research_task.yaml"
    if task_src.exists():
        shutil.copy2(task_src, cfg_dir / "research_task.yaml")


def copy_module_code(pkg_dir: Path, mod: dict):
    """Copy module-specific code."""
    src = V3_ROOT / "modules" / mod["dir"]
    dst = pkg_dir / "src"
    dst.mkdir(exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and f.suffix in (".py", ".yaml", ".yml"):
            shutil.copy2(f, dst / f.name)


def gen_run_py(pkg_dir: Path, mod: dict):
    """Generate run.py entry point — 通用动态适配版本。"""
    run_py = '''#!/usr/bin/env python
"""独立运行入口 — 自动适配模块接口"""
import os, sys, json, yaml, argparse, logging, inspect
from pathlib import Path
from dataclasses import fields as dataclass_fields

PKG_ROOT = Path(__file__).resolve().parent
for p in [str(PKG_ROOT / "shared"), str(PKG_ROOT / "src"), str(PKG_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(PKG_ROOT / "run.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

def load_config(config_dir):
    config = {}
    for name, key in [("research_task.yaml", None), ("llm.yaml", "llm"), ("providers.yaml", "providers")]:
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

def find_class(module, suffix):
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.endswith(suffix) and hasattr(obj, "__dataclass_fields__"):
            return name, obj
    return None, None

def find_impl_class():
    import implementation
    for name, obj in inspect.getmembers(implementation, inspect.isclass):
        if "Implementation" in name and obj.__module__ == "implementation":
            return name, obj
    return None, None

def construct_input(input_cls, task_id, config, input_files):
    field_names = {f.name for f in dataclass_fields(input_cls)}
    kwargs = {}
    for fname in field_names:
        if fname == "task_id": kwargs[fname] = task_id
        elif fname == "config": kwargs[fname] = config
        elif fname == "input_files": kwargs[fname] = input_files
        elif fname == "context": kwargs[fname] = {}
        elif fname.startswith("upstream_module_"): kwargs[fname] = {}
        else: kwargs[fname] = {}
    return input_cls(**kwargs)

def main():
    parser = argparse.ArgumentParser(description="模块独立运行")
    parser.add_argument("--input", default="input")
    parser.add_argument("--output", default="output")
    parser.add_argument("--config", default="configs")
    parser.add_argument("--task-id", default="test_001")
    args = parser.parse_args()

    input_dir = PKG_ROOT / args.input
    output_dir = PKG_ROOT / args.output
    config_dir = PKG_ROOT / args.config
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("输入目录: %s", input_dir)
    logger.info("输出目录: %s", output_dir)
    logger.info("=" * 60)

    config = load_config(config_dir)
    config["output_dir"] = str(output_dir)
    input_files = load_inputs(input_dir)
    logger.info("配置加载完成")
    logger.info("输入文件: %s", list(input_files.keys()) if input_files else "（无）")

    import interface
    _, input_cls = find_class(interface, "Input")
    _, output_cls = find_class(interface, "Output")
    impl_name, impl_cls = find_impl_class()
    if not impl_cls:
        logger.error("未找到Implementation类"); return 1
    logger.info("实现类: %s", impl_name)
    if input_cls: logger.info("输入类: %s", input_cls.__name__)

    # LLM初始化
    llm_provider = None
    try:
        from infrastructure.llm.llm_provider import LLMProviderFactory
        llm_cfg = config.get("llm", {})
        if isinstance(llm_cfg, dict) and llm_cfg.get("type"):
            llm_provider = LLMProviderFactory.create_provider(llm_cfg)
            if llm_provider and llm_provider.is_available():
                logger.info("LLM Provider: %s", llm_provider.get_name())
            else:
                llm_provider = None; logger.warning("LLM不可用，无LLM模式")
    except Exception as e:
        logger.warning("LLM初始化跳过: %s", e)

    # 实例化
    try:
        if llm_provider:
            try: instance = impl_cls(llm_provider=llm_provider)
            except TypeError: instance = impl_cls()
        else:
            instance = impl_cls()
        logger.info("模块实例化成功")
    except Exception as e:
        logger.error("实例化失败: %s", e); return 1

    if hasattr(instance, "load_config"):
        try: instance.load_config(config)
        except Exception as e: logger.warning("配置加载警告: %s", e)

    # 执行
    try:
        if input_cls:
            input_data = construct_input(input_cls, args.task_id, config, input_files)
            result = instance.execute(input_data)
        else:
            result = instance.execute()
        logger.info("模块执行完成")
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        logger.error("您可以手动补充输出文件到 output/ 目录，供下游模块使用")
        return 1

    # 保存结果
    if result:
        try:
            if hasattr(result, "output_files"):
                logger.info("输出文件清单:")
                for name, path in result.output_files.items():
                    logger.info("  - %s -> %s", name, path)
            result_dict = {}
            for attr in ["task_id", "output_files", "manifest", "warnings", "errors"]:
                if hasattr(result, attr):
                    val = getattr(result, attr)
                    result_dict[attr] = val if isinstance(val, (dict, list)) else str(val)
            with open(output_dir / "result.json", "w", encoding="utf-8") as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
            logger.info("结果已保存: %s", output_dir / "result.json")
        except Exception as e:
            logger.warning("结果保存警告: %s", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    (pkg_dir / "run.py").write_text(run_py, encoding="utf-8")


def gen_readme(pkg_dir: Path, mod: dict):
    """Generate Chinese README.md."""
    upstream_str = ", ".join(mod["upstream"]) if mod["upstream"] else "无（入口模块）"
    downstream_str = ", ".join(mod["downstream"]) if mod["downstream"] else "无（终点模块）"

    inputs_table = "\n".join([
        f"| `{i['name']}` | {'必需' if i['required'] else '可选'} | {i['desc']} |"
        for i in mod["inputs"]
    ])
    outputs_table = "\n".join([
        f"| `{o['name']}` | {o['desc']} |"
        for o in mod["outputs"]
    ])

    # Pre-compute input details section
    input_details_parts = []
    for i in mod["inputs"]:
        req_str = "**必需文件**" if i["required"] else "**可选文件**"
        input_details_parts.append(
            f"#### `{i['name']}`\n\n{i['desc']}。\n\n格式请参考 `src/schema.py` 中的定义。\n\n{req_str}"
        )
    input_details = "\n\n".join(input_details_parts)

    # Pre-compute upstream/downstream interface strings
    if mod["upstream"]:
        upstream_interfaces = "\n".join(
            [f"- Module {u}: 将其输出文件复制到本模块的 `input/` 目录" for u in mod["upstream"]]
        )
    else:
        upstream_interfaces = "- 无上游模块，本模块为流水线入口"

    if mod["downstream"]:
        downstream_interfaces = "\n".join(
            [f"- Module {d}: 读取本模块 `output/` 目录中的输出文件" for d in mod["downstream"]]
        )
    else:
        downstream_interfaces = "- 无下游模块，本模块为流水线终点"

    llm_section = ""
    if mod["needs_llm"]:
        llm_section = """
## LLM配置

本模块需要LLM支持。默认使用Ollama本地模型。

### 当前配置（已从总项目继承）

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Provider类型 | ollama | 本地Ollama模型 |
| 推理模型 | deepseek-r1:8b | 核心推理任务 |
| 辅助模型 | gemma4:26b | 辅助生成任务 |
| Endpoint | http://localhost:11434/v1 | Ollama API地址 |
| Timeout | 300秒 | 请求超时时间 |

### 修改LLM配置

如需修改LLM配置，请编辑 `configs/llm.yaml` 和 `configs/providers.yaml`。

如需使用OpenAI/DeepSeek等云端模型，请在 `configs/providers.yaml` 中设置API Key：

```yaml
providers:
  llm:
    default: "deepseek"
    deepseek:
      type: "deepseek"
      model: "deepseek-reasoner"
      api_key: "your-api-key-here"  # 修改为你的API Key
      temperature: 0.3
      max_tokens: 8192
```
"""

    readme = f'''# {mod["name_cn"]}（{mod["name_en"]}）

> 模块ID: **{mod["id"]}** | Research Agent 独立子项目

## 模块概述

{mod["desc"]}

### 流水线位置

| 项目 | 内容 |
|------|------|
| 上游模块 | {upstream_str} |
| 下游模块 | {downstream_str} |
| 需要LLM | {"是" if mod["needs_llm"] else "否"} |

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.12 |
| Conda环境 | research_agent_v3 |
| 操作系统 | Windows / Linux |
| GPU | {"可选（CPU亦可运行）" if mod["needs_llm"] else "不需要"} |

### 安装步骤

```bash
# 1. 解压压缩包
unzip {mod["zip"]}.zip
cd {mod["zip"]}

# 2. 激活conda环境
conda activate research_agent_v3

# 3. 安装依赖（如需要）
pip install -r requirements.txt

# 4. 运行模块
python run.py
```

## 目录结构

```
{mod["zip"]}/
├── run.py                    # 运行入口
├── requirements.txt          # Python依赖
├── README.md                 # 本说明文档
├── configs/                  # 配置文件目录
│   ├── research_task.yaml    # 研究任务配置
│   ├── llm.yaml              # LLM配置
│   ├── providers.yaml        # LLM Provider配置
│   └── dependency_policy.yaml # Fallback策略
├── input/                    # 输入目录
│   └── example_input.json    # 输入示例模板
├── output/                   # 输出目录（运行后自动创建）
├── src/                      # 模块源代码
│   ├── implementation.py     # 模块实现
│   ├── interface.py          # 接口定义
│   ├── schema.py             # 数据Schema
│   ├── validator.py          # 验证器
│   └── manifest.yaml         # 模块清单
└── shared/                   # 公共基础库
    ├── infrastructure/       # 基础设施（LLM、存储等）
    ├── literature/           # 文献处理库
    ├── reasoning/            # 推理库
    ├── adapters/             # 适配器（SAMRA等）
    └── core/                 # 核心工具
```
{llm_section}
## 输入格式说明

### 输入文件清单

| 文件名 | 必需性 | 说明 |
|--------|--------|------|
{inputs_table}

### 输入文件存储位置

所有输入文件放置在 `input/` 目录下。

### 手动创建输入文件

如果上游模块未运行或输出不完整，你可以手动创建输入文件：

1. 查看 `input/example_input.json` 了解格式模板
2. 按照格式创建输入文件
3. 将文件放入 `input/` 目录
4. 运行 `python run.py`

### 输入文件格式标准

每个输入文件都是标准JSON/YAML格式，具体Schema请参考 `src/schema.py` 文件中的定义。

## 输出格式说明

### 输出文件清单

| 文件名 | 说明 |
|--------|------|
{outputs_table}

### 输出文件存储位置

所有输出文件保存在 `output/` 目录下。

### 输出文件格式标准

输出文件遵循与上游模块一致的JSON/YAML格式，确保下游模块可直接读取。

## 运行方法

### 基本运行

```bash
conda activate research_agent_v3
python run.py
```

### 指定输入/输出目录

```bash
python run.py --input /path/to/inputs --output /path/to/outputs
```

### 指定配置目录

```bash
python run.py --config /path/to/configs
```

## 手动输入指南

当上游模块未运行时，你可以手动准备输入文件：

1. **创建input目录**: `mkdir input`
2. **复制示例模板**: `cp input/example_input.json input/`（如存在）
3. **编辑输入文件**: 按照Schema定义填写内容
4. **运行模块**: `python run.py`

### 输入文件详细说明

{input_details}

## 错误处理与手动修复

### 模块运行报错时

如果模块运行报错，你可以：

1. **查看日志**: 检查 `run.log` 文件了解错误详情
2. **手动补充输出**: 根据输出格式要求，手动创建输出文件到 `output/` 目录
3. **跳过本模块**: 直接使用手动创建的输出文件作为下游模块的输入

### 手动修复输出文件

1. 查看 `src/schema.py` 了解输出格式
2. 查看 `src/manifest.yaml` 了解输出文件清单
3. 手动创建输出文件，确保格式正确
4. 将文件放入 `output/` 目录
5. 下游模块可直接读取 `output/` 目录中的文件

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| LLM不可用 | 检查Ollama是否运行：`ollama list`，或修改 `configs/providers.yaml` 使用其他LLM |
| 输入文件缺失 | 手动创建输入文件，参考 `input/example_input.json` |
| 模块执行超时 | 增加 `configs/llm.yaml` 中的timeout值 |
| 依赖缺失 | 运行 `pip install -r requirements.txt` |

## 与其他模块的接口

### 上游接口（本模块的输入来源）

{upstream_interfaces}

### 下游接口（本模块的输出去向）

{downstream_interfaces}

## 配置文件说明

| 配置文件 | 说明 | 修改指引 |
|----------|------|----------|
| `configs/research_task.yaml` | 研究任务配置 | 修改研究方向和关键词 |
| `configs/llm.yaml` | LLM模型配置 | 修改模型类型和参数 |
| `configs/providers.yaml` | LLM Provider配置 | 修改API Key和Endpoint |
| `configs/dependency_policy.yaml` | Fallback策略 | 修改依赖缺失时的行为 |

详细配置说明请参考 `configs/` 目录下各文件中的注释。
'''
    (pkg_dir / "README.md").write_text(readme, encoding="utf-8")


def gen_input_schema(pkg_dir: Path, mod: dict):
    """Generate input_schema.yaml."""
    schema = {
        "module_id": mod["id"],
        "module_name": mod["name_en"],
        "inputs": [
            {
                "name": i["name"],
                "required": i["required"],
                "description": i["desc"],
                "format": "json" if i["name"].endswith(".json") else ("jsonl" if i["name"].endswith(".jsonl") else "yaml"),
            }
            for i in mod["inputs"]
        ],
    }
    (pkg_dir / "input_schema.yaml").write_text(
        yaml.dump(schema, allow_unicode=True, default_flow_style=False), encoding="utf-8"
    )


def gen_output_schema(pkg_dir: Path, mod: dict):
    """Generate output_schema.yaml."""
    schema = {
        "module_id": mod["id"],
        "module_name": mod["name_en"],
        "outputs": [
            {
                "name": o["name"],
                "description": o["desc"],
                "format": "json" if o["name"].endswith(".json") else ("jsonl" if o["name"].endswith(".jsonl") else ("csv" if o["name"].endswith(".csv") else "mixed")),
            }
            for o in mod["outputs"]
        ],
    }
    (pkg_dir / "output_schema.yaml").write_text(
        yaml.dump(schema, allow_unicode=True, default_flow_style=False), encoding="utf-8"
    )


def gen_example_input(pkg_dir: Path, mod: dict):
    """Generate example input file."""
    example = {
        "_comment": f"Module {mod['id']} ({mod['name_cn']}) 输入文件示例",
        "_usage": "将此文件复制并重命名为实际输入文件名，修改内容后放入 input/ 目录",
        "module_id": mod["id"],
        "module_name": mod["name_en"],
        "required_inputs": [i["name"] for i in mod["inputs"] if i["required"]],
        "input_format_examples": {},
    }
    for i in mod["inputs"]:
        name = i["name"]
        if "research_task.yaml" in name:
            example["input_format_examples"][name] = {
                "task_id": "VLM_Safety_001",
                "research_question": "How to defend VLMs against multimodal jailbreak attacks?",
                "keywords": ["vision-language model", "adversarial defense", "jailbreak"],
                "target_venues": ["CVPR", "ICCV", "NeurIPS", "ICLR"],
            }
        elif "download_queue" in name:
            example["input_format_examples"][name] = [
                {"paper_id": "2401.00123", "url": "https://arxiv.org/pdf/2401.00123", "source_db": "arxiv"},
            ]
        elif "paper_metadata" in name:
            example["input_format_examples"][name] = [
                {"paper_id": "2401.00123", "title": "Example Paper", "authors": ["Author A"], "year": 2024},
            ]
        elif "paper.md" in name:
            example["input_format_examples"][name] = "归一化论文Markdown文本内容..."
        elif "paper_analysis" in name:
            example["input_format_examples"][name] = {
                "paper_id": "2401.00123",
                "main_contribution": "Example contribution",
                "methodology": "Example methodology",
                "limitations": ["Limitation 1"],
            }
        elif "gap_candidates" in name:
            example["input_format_examples"][name] = [
                {"gap_id": "G1", "description": "Example gap", "supporting_papers": ["2401.00123"]},
            ]
        elif "method_spec" in name:
            example["input_format_examples"][name] = {
                "method_name": "MV-Guard",
                "components": [{"name": "SafetyAlignment", "type": "module"}],
                "input_schema": {},
                "output_schema": {},
            }
        elif "experiment_matrix" in name:
            example["input_format_examples"][name] = {
                "experiments": [
                    {"id": "EXP01", "type": "synthetic", "method": "baseline"},
                ]
            }
        elif "claim_evidence" in name:
            example["input_format_examples"][name] = {
                "claims": [
                    {"claim_id": "C1", "statement": "Example claim", "pass_criteria": "p < 0.05"},
                ]
            }
        elif "paper_figure_plan" in name:
            example["input_format_examples"][name] = {
                "figures": [{"id": "F1", "type": "bar_chart", "title": "Results"}],
            }
        elif "synthetic_results" in name:
            example["input_format_examples"][name] = {
                "metrics_csv": "method,score\nbaseline,0.42\nours,0.78",
                "statistics_json": {"mean": 0.78, "std": 0.05},
            }
        elif "final_research_direction" in name:
            example["input_format_examples"][name] = "# 最终研究方向\nMV-Guard: 多模态防御框架..."
        elif "scientific_result_analysis" in name:
            example["input_format_examples"][name] = "# 科学结果分析\n..."
        elif "figures/" in name or "tables/" in name:
            example["input_format_examples"][name] = "目录结构，包含图表文件..."
        elif "paper/" in name:
            example["input_format_examples"][name] = "论文目录，包含paper.md..."
        else:
            example["input_format_examples"][name] = "请参考 src/schema.py 了解格式"

    (pkg_dir / "input" / "example_input.json").parent.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "input" / "example_input.json").write_text(
        json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def gen_requirements(pkg_dir: Path):
    """Generate requirements.txt."""
    reqs = """pyyaml>=6.0
requests>=2.28
aiohttp>=3.8
matplotlib>=3.7
numpy>=1.24
pandas>=2.0
python-docx>=0.8
openai>=1.0
"""
    (pkg_dir / "requirements.txt").write_text(reqs, encoding="utf-8")


def build_package(mod: dict):
    """Build a single module package."""
    pkg_name = mod["zip"]
    pkg_dir = BUILD_DIR / pkg_name

    print(f"\n{'='*60}")
    print(f"构建: {pkg_name}")
    print(f"{'='*60}")

    # Create directories
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "input").mkdir()
    (pkg_dir / "output").mkdir()

    # Copy code and configs
    copy_module_code(pkg_dir, mod)
    copy_shared_code(pkg_dir)
    copy_configs(pkg_dir)

    # Generate files
    gen_run_py(pkg_dir, mod)
    gen_readme(pkg_dir, mod)
    gen_input_schema(pkg_dir, mod)
    gen_output_schema(pkg_dir, mod)
    gen_example_input(pkg_dir, mod)
    gen_requirements(pkg_dir)

    # Create zip
    zip_path = RELEASES_DIR / f"{pkg_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pkg_dir):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                filepath = Path(root) / file
                arcname = filepath.relative_to(pkg_dir)
                zf.write(filepath, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def main():
    print("=" * 60)
    print("Research Agent — 15个独立模块包构建脚本")
    print("=" * 60)

    clean_build_dir()

    results = []
    for mod in MODULES:
        try:
            zip_path = build_package(mod)
            results.append({"module": mod["id"], "name": mod["zip"], "status": "OK", "path": str(zip_path)})
        except Exception as e:
            print(f"  [FAIL] {mod['zip']}: {e}")
            results.append({"module": mod["id"], "name": mod["zip"], "status": "FAIL", "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("构建结果汇总")
    print("=" * 60)
    ok = sum(1 for r in results if r["status"] == "OK")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    print(f"成功: {ok}/15 | 失败: {fail}/15")
    print(f"输出目录: {RELEASES_DIR}")

    for r in results:
        status = "[OK]" if r["status"] == "OK" else "[FAIL]"
        print(f"  {status} Module {r['module']}: {r['name']}")

    # Clean up build dir
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
