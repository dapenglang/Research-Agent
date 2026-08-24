"""
research-agent CLI

Commands:
  start   — Launch a new research task from scratch
  resume  — Resume an interrupted/paused task
  rerun   — Re-execute from a specific module (--from MODULE_ID)
  status  — Show current pipeline state

Usage:
  python -m Research_Agent_v3.cli.cli start --task research_task.yaml
  python -m Research_Agent_v3.cli.cli resume --task research_task.yaml
  python -m Research_Agent_v3.cli.cli rerun --task research_task.yaml --from 10
  python -m Research_Agent_v3.cli.cli status --task research_task.yaml

The CLI delegates ALL work to PipelineOrchestrator.
It never imports or calls modules directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Research_Agent_v3.orchestrator import PipelineOrchestrator


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="Research Agent v3 — Modular Research Automation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # start
    start_parser = subparsers.add_parser("start", help="Start a new research task")
    start_parser.add_argument(
        "--task", required=True, help="Path to research_task.yaml"
    )
    start_parser.add_argument(
        "--state-root", default="state", help="Directory for state files"
    )
    start_parser.add_argument(
        "--output-root", default="output", help="Directory for output files"
    )

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume an interrupted task")
    resume_parser.add_argument(
        "--task", required=True, help="Path to research_task.yaml"
    )
    resume_parser.add_argument(
        "--state-root", default="state", help="Directory for state files"
    )
    resume_parser.add_argument(
        "--output-root", default="output", help="Directory for output files"
    )

    # rerun
    rerun_parser = subparsers.add_parser("rerun", help="Re-execute from a module")
    rerun_parser.add_argument(
        "--task", required=True, help="Path to research_task.yaml"
    )
    rerun_parser.add_argument(
        "--from", dest="from_module", default=None,
        help="Module ID to rerun from (e.g., 10). Default: start from 01"
    )
    rerun_parser.add_argument(
        "--state-root", default="state", help="Directory for state files"
    )
    rerun_parser.add_argument(
        "--output-root", default="output", help="Directory for output files"
    )

    # status
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument(
        "--task", required=True, help="Path to research_task.yaml"
    )
    status_parser.add_argument(
        "--state-root", default="state", help="Directory for state files"
    )
    status_parser.add_argument(
        "--output-root", default="output", help="Directory for output files"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    orchestrator = PipelineOrchestrator(
        task_config_path=args.task,
        state_root=args.state_root,
        output_root=args.output_root,
    )

    if args.command == "start":
        result = orchestrator.start()
    elif args.command == "resume":
        result = orchestrator.resume()
    elif args.command == "rerun":
        result = orchestrator.rerun(module_id=args.from_module)
    elif args.command == "status":
        result = orchestrator.get_status()
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("completed", "paused") else (
        0 if args.command == "status" else 1
    )


if __name__ == "__main__":
    sys.exit(main())
