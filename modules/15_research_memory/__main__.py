"""Module 15 entry point for standalone execution."""
import json
import sys
from pathlib import Path

from implementation import ResearchMemoryModule
from schema import Module15Input

if __name__ == "__main__":
    config_path = Path("config/module_config.yaml")
    config = {}
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    task_id = config.get("task_id", "default_task")
    input_dir = Path(config.get("input_dir", "input"))
    output_dir = Path(config.get("output_dir", "output"))

    input_files = {}
    if input_dir.exists():
        for p in input_dir.rglob("Stage_Report.md"):
            input_files[str(p.relative_to(input_dir))] = str(p)
        for p in input_dir.rglob("*.json"):
            input_files[str(p.relative_to(input_dir))] = str(p)

    module = ResearchMemoryModule()
    module.load_config(config)
    result = module.execute(Module15Input(
        task_id=task_id,
        config=config,
        input_files=input_files,
    ))

    print(json.dumps({
        "success": result.success,
        "output_files": result.output_files,
        "warnings": result.warnings,
        "errors": result.errors,
    }, indent=2, ensure_ascii=False))

    sys.exit(0 if result.success else 1)
