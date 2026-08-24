"""Module 02.5 validator."""

from typing import Any, Dict


def validate_input(input_data: Any) -> bool:
    return bool(getattr(input_data, "task_id", None))


def validate_output(output: Any) -> bool:
    return output.manifest.get("papers_processed", -1) >= 0
