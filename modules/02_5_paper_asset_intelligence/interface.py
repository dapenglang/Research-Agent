"""Module 02.5 Interface — Paper Asset Intelligence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PaperAssetIntelligenceInput:
    task_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    input_files: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    upstream_module_02: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaperAssetIntelligenceOutput:
    task_id: str
    output_files: Dict[str, str] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class Module02_5Interface(ABC):
    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> None: ...

    @abstractmethod
    def validate_input(self, input_data: PaperAssetIntelligenceInput) -> bool: ...

    @abstractmethod
    def execute(self, input_data: PaperAssetIntelligenceInput) -> PaperAssetIntelligenceOutput: ...

    @abstractmethod
    def validate_output(self, output: PaperAssetIntelligenceOutput) -> bool: ...

    @abstractmethod
    def quality_assessment(self, output: PaperAssetIntelligenceOutput) -> Dict[str, Any]: ...

    @abstractmethod
    def write_manifest(self, output: PaperAssetIntelligenceOutput) -> Dict[str, Any]: ...

    @abstractmethod
    def write_report(self, output: PaperAssetIntelligenceOutput) -> str: ...
