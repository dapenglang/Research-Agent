from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class Module15Input:
    task_id: str = ""
    config: Any = None
    input_files: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    upstream_modules: Dict[str, Any] = field(default_factory=dict)
    llm_provider: Any = None

    def __post_init__(self):
        ctx = self.context or {}
        self.upstream_modules = ctx.get("upstream_modules", self.upstream_modules)


@dataclass
class Module15Output:
    research_memory: str = ""
    decision_log: str = ""
    lessons_learned: str = ""
    success: bool = True
    error: str = ""
    output_files: Dict[str, str] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
