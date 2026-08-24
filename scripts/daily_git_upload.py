#!/usr/bin/env python3
"""
Research Agent v8.3.1 - 15-Day GitHub Upload Plan
=================================================
每天自动上传一部分代码到 GitHub，按模块分拆。

使用方法:
    python scripts/daily_git_upload.py           # 执行当天任务
    python scripts/daily_git_upload.py --status   # 查看进度
    python scripts/daily_git_upload.py --day 3    # 执行指定天数
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = PROJECT_ROOT / "scripts" / "upload_progress.json"

UPLOAD_PLAN = [
    {
        "day": 1,
        "title": "项目骨架与基础设施",
        "paths": [".gitignore", "README.md", "core/", "configs/", "docs/", "cli/"],
        "commit_msg": "Day1: 项目骨架 - .gitignore, README, core/, configs/, docs/, cli/",
    },
    {
        "day": 2,
        "title": "LLM 运行时与基础设施层",
        "paths": ["infrastructure/"],
        "commit_msg": "Day2: infrastructure/ - LLM runtime, providers, MCP, skills, storage",
    },
    {
        "day": 3,
        "title": "模块01 文献检索 + 模块02 论文获取与解析",
        "paths": ["modules/01_literature_retrieval/", "modules/02_source_acquisition/"],
        "commit_msg": "Day3: Module01 Literature Retrieval + Module02 Paper Acquisition",
    },
    {
        "day": 4,
        "title": "模块02.5 论文资产智能 + 模块03 文献智能分析",
        "paths": ["modules/02_5_paper_asset_intelligence/", "modules/03_literature_intelligence/"],
        "commit_msg": "Day4: Module02.5 Paper Asset Intelligence + Module03 Literature Intelligence",
    },
    {
        "day": 5,
        "title": "模块04 研究领域全景 + 模块05 创新发现",
        "paths": ["modules/04_research_landscape/", "modules/05_innovation_reasoning/"],
        "commit_msg": "Day5: Module04 Research Landscape + Module05 Innovation Reasoning",
    },
    {
        "day": 6,
        "title": "模块06 理论方法设计",
        "paths": ["modules/06_theory_method/"],
        "commit_msg": "Day6: Module06 Theory & Method Design",
    },
    {
        "day": 7,
        "title": "模块07 实验规划 + 模块08 合成实验引擎",
        "paths": ["modules/07_experiment_planning/", "modules/08_synthetic_experiment_engine/"],
        "commit_msg": "Day7: Module07 Experiment Planning + Module08 Synthetic Experiment Engine",
    },
    {
        "day": 8,
        "title": "模块09 真实实验引擎 + 模块10 结果分析",
        "paths": ["modules/09_real_experiment_engine/", "modules/10_result_analysis/"],
        "commit_msg": "Day8: Module09 Real Experiment Engine + Module10 Result Analysis",
    },
    {
        "day": 9,
        "title": "模块11 图表生成 + 模块12 论文撰写",
        "paths": ["modules/11_figure_table/", "modules/12_paper_writing/"],
        "commit_msg": "Day9: Module11 Figure & Table + Module12 Paper Writing",
    },
    {
        "day": 10,
        "title": "模块13 引用与补充 + 模块14 审稿循环",
        "paths": ["modules/13_reference_supplementary/", "modules/14_reviewer_loop/"],
        "commit_msg": "Day10: Module13 Reference & Supplementary + Module14 Reviewer Loop",
    },
    {
        "day": 11,
        "title": "模块15 科研记忆 + Orchestrator",
        "paths": ["modules/15_research_memory/", "orchestrator/"],
        "commit_msg": "Day11: Module15 Research Memory + Orchestrator",
    },
    {
        "day": 12,
        "title": "数据模型与状态管理",
        "paths": ["schemas/", "state/", "tasks/", "reasoning/", "adapters/"],
        "commit_msg": "Day12: schemas/ + state/ + tasks/ + reasoning/ + adapters/",
    },
    {
        "day": 13,
        "title": "测试、模板与工具",
        "paths": ["tests/", "templates/", "tools/"],
        "commit_msg": "Day13: tests/ + templates/ + tools/",
    },
    {
        "day": 14,
        "title": "记忆目录与数据元信息",
        "paths": ["memory/", "human_feedback/", "data/", "literature/"],
        "commit_msg": "Day14: memory/ + human_feedback/ + data/ metadata + literature/ metadata",
    },
    {
        "day": 15,
        "title": "最终整理与版本标签",
        "paths": ["output/", "papers/", "papers_output/", "literature_output/",
                  "intelligence_output/", "figures/",
                  "Research_Agent_v8.3.1_User_Manual_CN.md",
                  "Research_Agent_v8.3.1_Module_Release_Report.md",
                  "Research_Agent_v8.3.1_Final_Report.md",
                  "build_packages_v831.py"],
        "commit_msg": "Day15: Final - output reports, release docs, tag v8.3.1",
    },
]


def run_git(args, cwd=PROJECT_ROOT):
    """Run a git command and return the result."""
    cmd = ["git"] + args
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 and result.stderr:
        print(f"    stderr: {result.stderr.strip()}")
    return result


def load_progress():
    """Load progress from the progress file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_days": [], "current_day": 1, "start_date": None, "repo_url": "https://github.com/dapenglang/Research-Agent.git"}


def save_progress(progress):
    """Save progress to the progress file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def get_day_plan(day_num):
    """Get the upload plan for a specific day."""
    for plan in UPLOAD_PLAN:
        if plan["day"] == day_num:
            return plan
    return None


def execute_day(day_num, dry_run=False):
    """Execute the upload for a specific day."""
    plan = get_day_plan(day_num)
    if not plan:
        print(f"[ERROR] Day {day_num} not found in plan")
        return False

    print(f"\n{'='*60}")
    print(f"Day {day_num}: {plan['title']}")
    print(f"{'='*60}")

    if dry_run:
        print("[DRY RUN] Would add:")
        for p in plan["paths"]:
            full = PROJECT_ROOT / p
            print(f"  - {p} {'(exists)' if full.exists() else '(NOT FOUND)'}")
        return True

    # Step 1: Add files
    for path in plan["paths"]:
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            print(f"  [SKIP] {path} (not found)")
            continue
        print(f"  [ADD] {path}")
        run_git(["add", path])

    # Step 2: Check if there are staged changes
    status = run_git(["status", "--porcelain", "--untracked-files=no"])
    if not status.stdout.strip():
        print("  [INFO] No changes to commit (already committed)")
        return True

    # Step 3: Commit
    print(f"  [COMMIT] {plan['commit_msg']}")
    commit = run_git(["commit", "-m", plan["commit_msg"]])
    if commit.returncode != 0:
        print(f"  [ERROR] Commit failed: {commit.stderr}")
        return False

    # Step 4: Push
    print(f"  [PUSH] origin main")
    push = run_git(["push", "origin", "main"])
    if push.returncode != 0:
        print(f"  [ERROR] Push failed: {push.stderr}")
        print("  [HINT] Check if remote repository exists and credentials are configured")
        return False

    # Step 5: Update progress
    progress = load_progress()
    if day_num not in progress["completed_days"]:
        progress["completed_days"].append(day_num)
    progress["current_day"] = day_num + 1 if day_num < 15 else 15
    save_progress(progress)

    print(f"  [DONE] Day {day_num} complete. Progress: {len(progress['completed_days'])}/15 days")
    return True


def show_status():
    """Show the current upload progress."""
    progress = load_progress()
    print(f"\n{'='*60}")
    print(f"Research Agent v8.3.1 - GitHub Upload Progress")
    print(f"{'='*60}")
    print(f"Repository: {progress.get('repo_url', 'N/A')}")
    print(f"Start Date: {progress.get('start_date', 'N/A')}")
    print(f"Current Day: {progress.get('current_day', 1)}")
    print(f"Completed: {len(progress['completed_days'])}/15 days")
    print(f"Completed Days: {progress['completed_days']}")
    print(f"\nRemaining Days:")
    for plan in UPLOAD_PLAN:
        status = "DONE" if plan["day"] in progress["completed_days"] else "PENDING"
        print(f"  Day {plan['day']:2d} [{status:6s}] {plan['title']}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Research Agent 15-Day GitHub Upload Plan")
    parser.add_argument("--day", type=int, help="Execute specific day (1-15)")
    parser.add_argument("--status", action="store_true", help="Show upload progress")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no git operations)")
    parser.add_argument("--init-progress", action="store_true", help="Initialize progress file")
    args = parser.parse_args()

    if args.init_progress:
        progress = {
            "completed_days": [],
            "current_day": 1,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "repo_url": "https://github.com/dapenglang/Research-Agent.git",
        }
        save_progress(progress)
        print(f"[OK] Progress file initialized at {PROGRESS_FILE}")
        return

    if args.status:
        show_status()
        return

    if args.day:
        execute_day(args.day, dry_run=args.dry_run)
        return

    # Default: execute the current day
    progress = load_progress()
    current_day = progress.get("current_day", 1)
    if current_day > 15:
        print("[DONE] All 15 days completed!")
        show_status()
        return
    execute_day(current_day, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
