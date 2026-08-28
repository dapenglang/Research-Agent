from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class Module14Input:
    task_id: str = ""
    config: Any = None
    input_files: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    upstream_module_12: Dict[str, Any] = field(default_factory=dict)
    upstream_module_13: Dict[str, Any] = field(default_factory=dict)
    # v8.2: Skill and human feedback fields (populated from context)
    skill_instructions: str = ""
    available_skills: List[str] = field(default_factory=list)
    human_feedback: str = ""
    llm_provider: Any = None

    def __post_init__(self):
        ctx = self.context or {}
        self.skill_instructions = ctx.get("skill_instructions", "")
        self.available_skills = ctx.get("available_skills", [])
        self.human_feedback = ctx.get("human_feedback", "")


@dataclass
class Module14Output:
    review_report: str = ""
    revision_recommendations: str = ""
    decision: str = ""
    reviewer_comments: List[dict] = field(default_factory=list)
    success: bool = True
    error: str = ""
    output_files: Dict[str, str] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
