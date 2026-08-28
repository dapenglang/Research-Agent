"""
PipelineOrchestrator — the single entry point for running the
Research Agent v3 pipeline.

Responsibilities:
  1. Load research_task.yaml configuration
  2. Dynamically load and execute modules 01-13 in sequence
  3. Pass upstream module outputs as context to downstream modules
  4. Handle decision routing from Module 10 (PASS / RETURN_TO_*)
  5. Persist state via ResearchState for resume/rerun
  6. Collect provenance across the full pipeline

Design constraints:
  - CLI calls Orchestrator only; CLI never calls modules
  - Modules are loaded dynamically (directory names start with digits)
  - Decision routing can loop back to earlier modules (max retries enforced)
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

from Research_Agent_v3.core.state.state_machine import ResearchState, State
from Research_Agent_v3.core.exceptions import StateError, ModuleError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_V3_ROOT = Path(__file__).resolve().parent.parent

MODULE_SEQUENCE = [
    "01", "02", "02_5", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13", "14", "15",
]

MODULE_DIR_MAP = {
    "01": "01_literature_retrieval",
    "02": "02_source_acquisition",
    "02_5": "02_5_paper_asset_intelligence",
    "03": "03_literature_intelligence",
    "04": "04_research_landscape",
    "05": "05_innovation_reasoning",
    "06": "06_theory_method",
    "07": "07_experiment_planning",
    "08": "08_synthetic_experiment_engine",
    "09": "09_real_experiment_engine",
    "10": "10_result_analysis",
    "11": "11_figure_table",
    "12": "12_paper_writing",
    "13": "13_reference_supplementary",
    "14": "14_reviewer_loop",
    "15": "15_research_memory",
}

IMPL_CLASS_MAP = {
    "01": "LiteratureRetrievalImplementation",
    "02": "SourceAcquisitionImplementation",
    "02_5": "PaperAssetIntelligenceEngine",
    "03": "LiteratureIntelligenceImplementation",
    "04": "ResearchLandscapeModule",
    "05": "InnovationReasoningModule",
    "06": "TheoryMethodModule",
    "07": "ExperimentPlanningModule",
    "08": "SyntheticExperimentEngine",
    "09": "RealExperimentEngine",
    "10": "ResultAnalysisEngine",
    "11": "FigureTableEngine",
    "12": "PaperWritingEngine",
    "13": "ReferenceSupplementaryEngine",
    "14": "ReviewerLoopModule",
    "15": "ResearchMemoryModule",
}

INPUT_CLASS_MAP = {
    "01": "LiteratureRetrievalInput",
    "02": "SourceAcquisitionInput",
    "02_5": "PaperAssetIntelligenceInput",
    "03": "LiteratureIntelligenceInput",
    "04": "ResearchLandscapeInput",
    "05": "InnovationReasoningInput",
    "06": "TheoryMethodInput",
    "07": "ExperimentPlanningInput",
    "08": "SyntheticExperimentInput",
    "09": "RealExperimentInput",
    "10": "ResultAnalysisInput",
    "11": "FigureTableInput",
    "12": "PaperWritingInput",
    "13": "ReferenceSupplementaryInput",
    "14": "Module14Input",
    "15": "Module15Input",
}

OUTPUT_CLASS_MAP = {
    "01": "LiteratureRetrievalOutput",
    "02": "SourceAcquisitionOutput",
    "02_5": "PaperAssetIntelligenceOutput",
    "03": "LiteratureIntelligenceOutput",
    "04": "ResearchLandscapeOutput",
    "05": "InnovationReasoningOutput",
    "06": "TheoryMethodOutput",
    "07": "ExperimentPlanningOutput",
    "08": "SyntheticExperimentOutput",
    "09": "RealExperimentOutput",
    "10": "ResultAnalysisOutput",
    "11": "FigureTableOutput",
    "12": "PaperWritingOutput",
    "13": "ReferenceSupplementaryOutput",
    "14": "Module14Output",
    "15": "Module15Output",
}

DECISION_TARGET_MODULE = {
    "PASS_TO_FIGURE_TABLE": "11",
    "RETURN_TO_EXPERIMENT": "09",
    "RETURN_TO_EXPERIMENT_PLAN": "07",
    "RETURN_TO_METHOD": "06",
    "RETURN_TO_INNOVATION": "05",
    "HUMAN_REVIEW_REQUIRED": None,
}

# v8: Literature Quality Gate
MIN_PAPERS = 50
LITERATURE_GATE_MODULE = "03"  # Gate checks before Literature Intelligence

# v8: Modules that require real LLM (not Mock, not template-only)
# Module 10 is purely statistical, no LLM needed
LLM_REQUIRED_MODULES = {"04", "05", "06", "07", "12", "14"}
LLM_TASK_TYPE_MAP = {
    "04": "literature_analysis",
    "05": "innovation_reasoning",
    "06": "method_design",
    "07": "method_design",
    "12": "paper_generation",
    "14": "reviewer",
}

# Modules whose constructors accept llm_provider parameter for injection
LLM_INJECT_MODULES = {"04", "05", "06", "07"}

# v8.2: Human-in-the-loop feedback mapping
HUMAN_FEEDBACK_MODULES = {
    "05": "innovation",
    "06": "method",
    "14": "review",
}


class PipelineOrchestrator:
    """Orchestrates the full 13-module research pipeline.

    The orchestrator is the ONLY caller of modules. External interfaces
    (CLI, API, tests) must go through the orchestrator.
    """

    MAX_DECISION_LOOPS = 3

    def __init__(
        self,
        task_config_path: str | Path,
        state_root: str | Path = "state",
        output_root: str | Path = "output",
        skip_gates: bool = False,
    ) -> None:
        self.task_config_path = Path(task_config_path)
        self.output_root = Path(output_root)
        self.state_root = Path(state_root)
        self.skip_gates = skip_gates

        with open(self.task_config_path, "r", encoding="utf-8") as f:
            self.task_config: Dict[str, Any] = yaml.safe_load(f)

        self.task_id: str = self.task_config.get("task_id", "default_task")
        self.state = ResearchState(self.task_id, self.state_root)
        self.state.load()

        self._module_outputs: Dict[str, Any] = {}
        self._module_instances: Dict[str, Any] = {}
        self._provenance: List[Dict[str, Any]] = []
        self._decision_loop_count = 0
        self._gate_warnings: List[str] = []

        # v8.2: Initialize Skill Runtime and MCP Manager
        self._skill_runtime = None
        self._mcp_manager = None
        self._skill_integration = None
        self._init_v82_subsystems()

        # v8.2.2: Load unified external dependency config and fallback policy
        self._external_deps = self._load_yaml_config(_V3_ROOT / "configs" / "external_dependency.yaml")
        self._fallback_policy = self._load_yaml_config(_V3_ROOT / "configs" / "dependency_policy.yaml")
        self._run_mode = self._external_deps.get("run_mode", "limited")
        self._pre_check_results: Optional[Dict[str, Any]] = None
        logger.info("v8.2.2 Run mode: %s", self._run_mode)

    def _init_v82_subsystems(self) -> None:
        """Initialize v8.2 subsystems: Skills, MCP, LLM config."""
        try:
            from Research_Agent_v3.infrastructure.skills import SkillRuntime, SkillIntegration
            self._skill_runtime = SkillRuntime()
            self._skill_integration = SkillIntegration()
            skill_count = self._skill_runtime.get_total_count()
            logger.info("v8.2 Skill Runtime: %d skills discovered", skill_count)
        except Exception as e:
            logger.warning("Skill Runtime init failed (non-fatal): %s", e)

        try:
            from Research_Agent_v3.infrastructure.mcp import MCPManager
            self._mcp_manager = MCPManager()
            enabled = self._mcp_manager.list_enabled()
            logger.info("v8.2 MCP Manager: %d servers enabled", len(enabled))
        except Exception as e:
            logger.warning("MCP Manager init failed (non-fatal): %s", e)

    # ------------------------------------------------------------------
    # v8.2.2: Unified dependency management
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml_config(path: Path) -> Dict[str, Any]:
        """Load a YAML config file, returning empty dict on failure."""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to load %s: %s", path, e)
            return {}

    def _run_pre_checks(self) -> Dict[str, Any]:
        """Run pre-pipeline checks: skills, MCP, portability.

        Behavior depends on run_mode:
        - production: blocks if required components are missing
        - limited: logs warnings, continues
        - development: logs warnings, continues
        """
        results: Dict[str, Any] = {
            "passed": True,
            "mode": self._run_mode,
            "skill_check": None,
            "mcp_check": None,
            "portability_check": None,
            "warnings": [],
            "blocking_errors": [],
        }

        # 1. Skill availability check
        if self._skill_runtime:
            try:
                skill_report = self._skill_runtime.check_all_modules()
                results["skill_check"] = skill_report
                if not skill_report["all_required_present"]:
                    missing = skill_report["total_required_missing"]
                    msg = f"Required skills missing: {missing} skill(s) not installed"
                    results["warnings"].append(msg)
                    if self._run_mode == "production":
                        results["blocking_errors"].append(msg)
                        results["passed"] = False
            except Exception as e:
                logger.warning("Skill pre-check failed: %s", e)
                results["warnings"].append(f"Skill pre-check error: {e}")
        else:
            results["warnings"].append("Skill Runtime not initialized")

        # 2. MCP availability check
        if self._mcp_manager:
            try:
                mcp_report = self._mcp_manager.check_all_availability()
                results["mcp_check"] = mcp_report
                if not mcp_report["all_installed"]:
                    missing_names = [m["name"] for m in mcp_report.get("missing", [])]
                    msg = f"MCP servers not installed: {missing_names}"
                    results["warnings"].append(msg)
                    if self._run_mode == "production":
                        results["blocking_errors"].append(msg)
                        results["passed"] = False
            except Exception as e:
                logger.warning("MCP pre-check failed: %s", e)
                results["warnings"].append(f"MCP pre-check error: {e}")
        else:
            results["warnings"].append("MCP Manager not initialized")

        # 3. Portability check (lightweight, always non-blocking)
        try:
            scripts_dir = _V3_ROOT / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from check_portability import (
                check_python, check_conda, check_skills as cp_skills,
                check_mcp as cp_mcp, check_llm, check_gpu, check_storage,
                generate_report as gen_report,
            )
            checks = [
                check_python(),
                check_conda(),
                cp_skills(_V3_ROOT),
                cp_mcp(_V3_ROOT),
                check_llm(),
                check_gpu(),
                check_storage(_V3_ROOT),
            ]
            portability_report = {
                "checks": [{"name": c["name"], "status": c["status"]} for c in checks],
            }
            results["portability_check"] = portability_report
            for c in checks:
                if c["status"] == "WARN":
                    results["warnings"].append(f"Portability: {c['name']} needs attention")
        except Exception as e:
            logger.warning("Portability pre-check failed: %s", e)
            results["warnings"].append(f"Portability pre-check error: {e}")

        self._pre_check_results = results

        if results["blocking_errors"]:
            logger.error("Pre-checks FAILED (production mode): %s", results["blocking_errors"])
        elif results["warnings"]:
            logger.info("Pre-checks passed with warnings: %s", results["warnings"])

        return results

    def get_fallback(self, module_id: str, dependency_type: str) -> Dict[str, Any]:
        """
        Unified Fallback query entry point.
        Modules call this to get fallback policy — they must NOT decide fallback on their own.

        Args:
            module_id: Module ID (e.g., "01", "05")
            dependency_type: Dependency key (e.g., "skill:light-literature-search", "mcp:arxiv")

        Returns:
            Fallback policy dict with 'action', 'message', and optional params.
            Returns {"action": "block"} in production mode if fallback not allowed.
            Returns {"action": "none"} if no policy found.
        """
        mode_constraints = self._fallback_policy.get("mode_constraints", {})
        mode_cfg = mode_constraints.get(self._run_mode, {})
        allow_fallback = mode_cfg.get("allow_fallback", True)

        if not allow_fallback:
            return {
                "action": "block",
                "reason": f"Fallback not allowed in {self._run_mode} mode",
                "module_id": module_id,
                "dependency_type": dependency_type,
            }

        # Query skill_fallback policies
        if dependency_type.startswith("skill:"):
            policies = self._fallback_policy.get("skill_fallback", {})
            policy = policies.get(dependency_type)
            if policy:
                return {**policy, "module_id": module_id, "dependency_type": dependency_type}
            # Try default skill fallback
            default_policy = policies.get("skill:default", {"action": "skip", "message": "Skill missing, skipping"})
            return {**default_policy, "module_id": module_id, "dependency_type": dependency_type}

        # Query mcp_fallback policies
        if dependency_type.startswith("mcp:"):
            policies = self._fallback_policy.get("mcp_fallback", {})
            policy = policies.get(dependency_type)
            if policy:
                return {**policy, "module_id": module_id, "dependency_type": dependency_type}
            default_policy = policies.get("mcp:default", {"action": "skip", "message": "MCP unavailable, skipping"})
            return {**default_policy, "module_id": module_id, "dependency_type": dependency_type}

        # Query llm_fallback policy
        if dependency_type == "llm":
            policy = self._fallback_policy.get("llm_fallback", {"action": "template", "message": "LLM unavailable, using template mode"})
            return {**policy, "module_id": module_id, "dependency_type": dependency_type}

        # Query model_fallback policy
        if dependency_type == "model":
            policy = self._fallback_policy.get("model_fallback", {"action": "skip", "message": "Model not available"})
            return {**policy, "module_id": module_id, "dependency_type": dependency_type}

        return {"action": "none", "module_id": module_id, "dependency_type": dependency_type}

    @property
    def run_mode(self) -> str:
        """Return current run mode (production/limited/development)."""
        return self._run_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        """Start a new pipeline run from INIT."""
        if self.state.status not in (State.INIT, State.FAILED):
            return {
                "status": "error",
                "message": f"Cannot start: current state is {self.state.status.value}. "
                           f"Use 'resume' or 'rerun' instead.",
            }

        if self.state.status == State.FAILED:
            self.state.transition_to(State.INIT)

        # v8.2.2: Run pre-checks (skip if skip_gates=True)
        if not self.skip_gates:
            pre_check = self._run_pre_checks()
            if not pre_check["passed"]:
                return {
                    "status": "blocked",
                    "message": "Pre-checks failed (production mode). See blocking_errors.",
                    "pre_check_results": pre_check,
                    "blocking_errors": pre_check.get("blocking_errors", []),
                }

        self.state.start()
        self.state.transition_to(State.DEPENDENCY_CHECK)
        self.state.transition_to(State.MODULE_EXECUTING)

        return self._run_pipeline(from_module="01")

    def resume(self) -> Dict[str, Any]:
        """Resume an interrupted pipeline from the last checkpoint."""
        if self.state.status in (State.FAILED, State.CHECKPOINT,
                                 State.PAUSED_HUMAN_REVIEW,
                                 State.EXPERIMENT_INTERRUPTED):
            self.state.resume()
            if self.state.status == State.RESUMING:
                self.state.transition_to(State.MODULE_EXECUTING)
            elif self.state.status == State.EXPERIMENT_RESUMING:
                self.state.transition_to(State.EXPERIMENT_RUNNING)
                self.state.transition_to(State.VALIDATION_GATE)
                self.state.transition_to(State.MODULE_EXECUTING)

            completed = list(self.state.completed_modules)
            next_module = self._find_next_module(completed)
            if next_module is None:
                self.state.transition_to(State.COMPLETED)
                return {"status": "completed", "message": "All modules already completed."}

            return self._run_pipeline(from_module=next_module)
        else:
            return {
                "status": "error",
                "message": f"Cannot resume from state {self.state.status.value}.",
            }

    def rerun(self, module_id: Optional[str] = None) -> Dict[str, Any]:
        """Re-execute from a specific module (or from the beginning)."""
        if module_id is None:
            module_id = "01"

        if module_id not in MODULE_SEQUENCE:
            return {"status": "error", "message": f"Unknown module ID: {module_id}"}

        if self.state.status == State.COMPLETED:
            self.state.transition_to(State.INIT)

        if self.state.status == State.INIT:
            self.state.start()
            self.state.transition_to(State.DEPENDENCY_CHECK)
            self.state.transition_to(State.MODULE_EXECUTING)

        idx = MODULE_SEQUENCE.index(module_id)
        for mid in MODULE_SEQUENCE[idx:]:
            if mid in self.state.completed_modules:
                self.state.completed_modules.remove(mid)
                if mid in self.state.module_states:
                    self.state.module_states[mid].status = "pending"

        return self._run_pipeline(from_module=module_id)

    def get_status(self) -> Dict[str, Any]:
        """Return current pipeline status."""
        state_dict = self.state.to_dict()
        state_dict["provenance"] = self._provenance
        return state_dict

    # ------------------------------------------------------------------
    # v8: Quality Gates
    # ------------------------------------------------------------------

    def _check_literature_gate(self) -> Dict[str, Any]:
        """Check if sufficient literature exists before entering Module 03.

        Returns dict with:
          - passed: bool
          - paper_count: int
          - message: str
        """
        data_dir = _V3_ROOT / "data" / "literature"
        pdf_dir = data_dir / "pdf"
        latex_dir = data_dir / "latex"

        pdf_count = 0
        latex_count = 0

        if pdf_dir.exists():
            pdf_count = sum(
                1 for f in pdf_dir.iterdir()
                if f.is_file() and f.suffix.lower() == ".pdf" and f.stat().st_size > 1024
            )

        if latex_dir.exists():
            for d in latex_dir.iterdir():
                if d.is_dir() and list(d.rglob("*.tex")):
                    latex_count += 1

        total = pdf_count + latex_count
        passed = total >= MIN_PAPERS

        if passed:
            message = f"Literature gate passed: {total} papers (min: {MIN_PAPERS})"
        else:
            message = (
                f"Literature gate FAILED: {total} papers found, "
                f"need at least {MIN_PAPERS}. "
                f"Please add papers to data/literature/pdf/ or data/literature/latex/. "
                f"Missing: {MIN_PAPERS - total} papers."
            )

        return {
            "passed": passed,
            "paper_count": total,
            "pdf_count": pdf_count,
            "latex_count": latex_count,
            "message": message,
        }

    def _check_llm_gate(self, module_id: str) -> Dict[str, Any]:
        """Check if a real LLM provider is available for a required module.

        Returns dict with:
          - passed: bool (True if real LLM available or module not in required set)
          - message: str
          - block: bool (True if pipeline should stop)
        """
        if module_id not in LLM_REQUIRED_MODULES:
            return {"passed": True, "message": "", "block": False}

        task_type = LLM_TASK_TYPE_MAP.get(module_id, "")
        if not task_type:
            return {"passed": True, "message": "", "block": False}

        try:
            from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
            from Research_Agent_v3.infrastructure.llm.llm_provider import MockProvider
            runtime = LLMRuntime(str(_V3_ROOT / "configs"))
            runtime.load()
            provider = runtime.get_provider(task_type)
            if provider is None:
                available = False
            elif isinstance(provider, MockProvider):
                available = False
                logger.error(
                    "Mock provider detected for Module %s (task: %s)! "
                    "Research tasks require real LLM.",
                    module_id, task_type,
                )
            else:
                available = provider.is_available()
        except Exception as e:
            available = False
            logger.warning("LLM gate check error for %s: %s", module_id, e)

        if available:
            return {
                "passed": True,
                "message": f"LLM gate passed for Module {module_id} (task: {task_type}, model: {provider.model_name})",
                "block": False,
            }
        else:
            return {
                "passed": False,
                "block": True,
                "message": (
                    f"LLM gate BLOCKED for Module {module_id}: "
                    f"No real LLM provider available for task '{task_type}'. "
                    f"Ollama models (deepseek-r1:8b, gemma4:26b) must be running. "
                    f"Run: ollama serve"
                ),
            }

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def _run_pipeline(self, from_module: str) -> Dict[str, Any]:
        """Execute modules starting from *from_module* to Module 13."""
        start_idx = MODULE_SEQUENCE.index(from_module)
        module_outputs_summary: List[Dict[str, Any]] = []
        skip_modules = self._determine_skip_modules()

        for i in range(start_idx, len(MODULE_SEQUENCE)):
            module_id = MODULE_SEQUENCE[i]

            # v8: Literature Quality Gate — before Module 03
            if module_id == LITERATURE_GATE_MODULE and not self.skip_gates:
                gate = self._check_literature_gate()
                if not gate["passed"]:
                    logger.error("Literature gate blocked pipeline: %s", gate["message"])
                    return {
                        "status": "blocked",
                        "message": gate["message"],
                        "gate": "literature_quality",
                        "paper_count": gate["paper_count"],
                        "min_required": MIN_PAPERS,
                        "modules_run": module_outputs_summary,
                    }
                logger.info("Literature gate passed: %d papers", gate["paper_count"])

            # v8: LLM Gate — block if no real LLM for required modules
            if module_id in LLM_REQUIRED_MODULES and not self.skip_gates:
                llm_gate = self._check_llm_gate(module_id)
                if not llm_gate["passed"]:
                    logger.error("LLM gate BLOCKED: %s", llm_gate["message"])
                    if llm_gate.get("block", False):
                        return {
                            "status": "blocked",
                            "message": llm_gate["message"],
                            "gate": "llm_availability",
                            "module_id": module_id,
                            "modules_run": module_outputs_summary,
                        }
                    self._gate_warnings.append(llm_gate["message"])
                    logger.warning("LLM gate warning: %s", llm_gate["message"])

            if module_id in skip_modules:
                module_outputs_summary.append({
                    "module_id": module_id,
                    "status": "SKIPPED",
                    "data_origin": "skipped",
                    "output_files": {},
                })
                self.state.complete_module(module_id)
                continue

            result = self._execute_module(module_id)

            module_outputs_summary.append({
                "module_id": module_id,
                "status": result.get("status"),
                "data_origin": result.get("data_origin"),
                "output_files": result.get("output_files", {}),
            })

            if result["status"] == "FAIL":
                exp_mode = self.task_config.get("experiment", {}).get("mode", "synthetic_research")
                if exp_mode == "synthetic_research":
                    logger.warning("Module %s failed in synthetic mode, continuing pipeline: %s",
                                   module_id, result.get("errors", []))
                else:
                    return {
                        "status": "failed",
                        "message": f"Module {module_id} failed: {result.get('errors', [])}",
                        "module_id": module_id,
                        "modules_run": module_outputs_summary,
                    }

            if result["status"] == "WARNING":
                logger.warning("Module %s returned WARNING, continuing pipeline", module_id)

            if module_id == "10":
                decision = result.get("decision", "PASS_TO_FIGURE_TABLE")
                exp_mode = self.task_config.get("experiment", {}).get("mode", "synthetic_research")
                if exp_mode == "synthetic_research" and decision == "HUMAN_REVIEW_REQUIRED":
                    decision = "PASS_TO_FIGURE_TABLE"
                if decision != "PASS_TO_FIGURE_TABLE":
                    target = DECISION_TARGET_MODULE.get(decision)
                    if target is None or target in skip_modules:
                        decision = "PASS_TO_FIGURE_TABLE"
                    else:
                        self._decision_loop_count += 1
                        if self._decision_loop_count > self.MAX_DECISION_LOOPS:
                            logger.warning("Max decision loops exceeded, continuing to figure table")
                            decision = "PASS_TO_FIGURE_TABLE"
                        else:
                            return self._run_pipeline(from_module=target)

        # Transition through validation_gate -> decision_routing -> completed
        try:
            self.state.transition_to(State.VALIDATION_GATE)
            self.state.transition_to(State.DECISION_ROUTING)
            self.state.transition_to(State.COMPLETED)
        except Exception as e:
            logger.warning("State transition error (non-fatal): %s", e)
        return {
            "status": "completed",
            "message": "Pipeline completed successfully.",
            "modules_run": module_outputs_summary,
            "provenance": self._provenance,
            "gate_warnings": self._gate_warnings,
        }

    def _determine_skip_modules(self) -> List[str]:
        """Determine which modules to skip based on experiment mode."""
        exp_config = self.task_config.get("experiment", {})
        exp_mode = exp_config.get("mode", "synthetic_research")

        skip: List[str] = []

        if exp_mode == "synthetic_research":
            skip.append("09")
        elif exp_mode == "real_gpu_only":
            skip.append("08")

        return skip

    def _execute_module(self, module_id: str) -> Dict[str, Any]:
        """Load, validate, execute, and assess a single module."""
        try:
            instance = self._load_module(module_id)
        except Exception as e:
            self.state.fail_module(module_id, str(e))
            stub_output = self._create_stub_output(module_id, type("StubInput", (), {"task_id": self.task_id})())
            self._module_outputs[module_id] = stub_output
            return {"status": "FAIL", "errors": [str(e)], "module_id": module_id,
                    "output_files": {}}

        instance.load_config(self.task_config)

        input_data = self._build_input(module_id)
        input_result = instance.validate_input(input_data)
        if input_result is False or (hasattr(input_result, 'value') and input_result.value == "FAIL") or input_result == "FAIL":
            self.state.fail_module(module_id, "Input validation failed")
            stub_output = self._create_stub_output(module_id, input_data)
            self._module_outputs[module_id] = stub_output
            return {"status": "FAIL", "errors": ["Input validation failed"], "module_id": module_id,
                    "output_files": {}}

        self.state.set_current_module(module_id)

        try:
            output = instance.execute(input_data)
        except Exception as e:
            self.state.fail_module(module_id, str(e))
            # Store a minimal stub so downstream modules get something
            stub_output = self._create_stub_output(module_id, input_data)
            self._module_outputs[module_id] = stub_output
            return {"status": "FAIL", "errors": [str(e)], "module_id": module_id,
                    "output_files": {}}

        output_result = instance.validate_output(output)
        if output_result is False or (hasattr(output_result, 'value') and output_result.value == "FAIL") or output_result == "FAIL":
            # Store partial output so downstream modules can still access it
            self._module_outputs[module_id] = output
            self.state.fail_module(module_id, "Output validation failed")
            return {"status": "FAIL", "errors": ["Output validation failed"], "module_id": module_id,
                    "output_files": output.output_files if hasattr(output, 'output_files') else {}}

        quality = instance.quality_assessment(output)

        hard_reqs = quality.get("hard_requirements", {})
        all_hard_pass = all(hard_reqs.values()) if hard_reqs else True

        status = "PASS" if all_hard_pass else "WARNING"

        self._module_outputs[module_id] = output

        self._provenance.append({
            "module_id": module_id,
            "status": status,
            "data_origin": output.manifest.get("data_origin", "unknown"),
            "output_files": list(output.output_files.keys()),
            "timestamp": time.time(),
        })

        if status == "PASS":
            self.state.complete_module(module_id)
        else:
            self.state.complete_module(module_id)

        result: Dict[str, Any] = {
            "status": status,
            "module_id": module_id,
            "output_files": output.output_files,
            "data_origin": output.manifest.get("data_origin", "unknown"),
            "manifest": output.manifest,
            "warnings": output.warnings,
            "errors": output.errors,
        }

        if module_id == "10":
            decision_path = output.output_files.get("decision.json", "")
            if decision_path and os.path.exists(decision_path):
                with open(decision_path, "r", encoding="utf-8") as f:
                    decision_data = json.load(f)
                result["decision"] = decision_data.get("decision", "PASS_TO_FIGURE_TABLE")
            else:
                result["decision"] = output.manifest.get("decision", "PASS_TO_FIGURE_TABLE")

        return result

    # ------------------------------------------------------------------
    # Dynamic module loading
    # ------------------------------------------------------------------

    def _load_module(self, module_id: str) -> Any:
        """Dynamically load a module implementation by ID.

        Handles two loading patterns:
        - Modules 01-03, 08-13: use ``from interface import ...`` (bare name)
        - Modules 04-07: use ``from .interface import ...`` (relative import)

        For bare-name imports, evict cached ``interface`` from sys.modules.
        For relative imports, set ``__package__`` so Python can resolve them.
        """
        dir_name = MODULE_DIR_MAP[module_id]
        impl_path = _V3_ROOT / "modules" / dir_name / "implementation.py"

        if not impl_path.exists():
            raise ModuleError(
                f"Module {module_id} implementation not found at {impl_path}"
            )

        module_dir = str(impl_path.parent)
        if module_dir in sys.path:
            sys.path.remove(module_dir)
        sys.path.insert(0, module_dir)
        if str(_PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(_PROJECT_ROOT))
        if str(_V3_ROOT) not in sys.path:
            sys.path.insert(0, str(_V3_ROOT))

        # Evict cached bare-name modules so the correct local files are loaded
        for stale_key in ("interface", "schema", "validator"):
            sys.modules.pop(stale_key, None)

        # Modules 04-07 use relative imports; set __package__ for resolution
        pkg_name = f"Research_Agent_v3.modules.{dir_name}"

        spec = importlib.util.spec_from_file_location(
            f"module_{module_id}_impl",
            str(impl_path),
            submodule_search_locations=[module_dir],
        )
        if spec is None or spec.loader is None:
            raise ModuleError(f"Failed to create spec for module {module_id}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = pkg_name
        sys.modules[f"module_{module_id}_impl"] = module
        spec.loader.exec_module(module)

        impl_class_name = IMPL_CLASS_MAP[module_id]
        if not hasattr(module, impl_class_name):
            raise ModuleError(
                f"Module {module_id} implementation does not expose class {impl_class_name}"
            )

        impl_class = getattr(module, impl_class_name)

        # Inject LLM provider for modules that accept it (04, 05, 06, 07)
        if module_id in LLM_INJECT_MODULES:
            llm_provider = self._get_llm_provider_for_module(module_id)
            if llm_provider is not None:
                logger.info(
                    "Injecting LLM provider for Module %s: %s",
                    module_id, llm_provider.get_name(),
                )
                return impl_class(llm_provider=llm_provider)
            else:
                logger.warning(
                    "No LLM provider available for Module %s, running in template mode",
                    module_id,
                )

        return impl_class()

    def _get_llm_provider_for_module(self, module_id: str) -> Any:
        """Get an LLM provider for the given module via LLMRuntime routing."""
        task_type = LLM_TASK_TYPE_MAP.get(module_id, "")
        if not task_type:
            return None
        try:
            from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
            from Research_Agent_v3.infrastructure.llm.llm_provider import LLMLoggingProxy, MockProvider
            if not hasattr(self, "_llm_runtime") or self._llm_runtime is None:
                self._llm_runtime = LLMRuntime(str(_V3_ROOT / "configs"))
                self._llm_runtime.load()
            provider = self._llm_runtime.get_provider(task_type)
            if provider and provider.is_available():
                # Block Mock provider for research-critical modules
                if isinstance(provider, MockProvider):
                    logger.error(
                        "Mock provider detected for Module %s (task: %s)! "
                        "Research tasks require real LLM. Pipeline should stop.",
                        module_id, task_type,
                    )
                    return None
                # Wrap with logging proxy for usage tracking
                log_path = str(_V3_ROOT / "output" / "llm_usage_report.json")
                wrapped = LLMLoggingProxy(provider, module_id=module_id, log_path=log_path)
                return wrapped
        except Exception as e:
            logger.warning("Failed to get LLM provider for Module %s: %s", module_id, e)
        return None

    # ------------------------------------------------------------------
    # Input construction
    # ------------------------------------------------------------------

    def _build_input(self, module_id: str) -> Any:
        """Build the input dataclass for *module_id* from upstream outputs."""
        input_class_name = INPUT_CLASS_MAP[module_id]
        module_dir = MODULE_DIR_MAP[module_id]
        interface_path = _V3_ROOT / "modules" / module_dir / "interface.py"

        module_dir_str = str(interface_path.parent)
        if module_dir_str in sys.path:
            sys.path.remove(module_dir_str)
        sys.path.insert(0, module_dir_str)

        # Evict cached bare-name interface module
        sys.modules.pop("interface", None)

        interface_mod_name = f"module_{module_id}_interface"
        spec = importlib.util.spec_from_file_location(
            interface_mod_name, str(interface_path)
        )
        interface_module = importlib.util.module_from_spec(spec)
        sys.modules[interface_mod_name] = interface_module
        spec.loader.exec_module(interface_module)

        input_class = getattr(interface_module, input_class_name)

        input_files = self._collect_input_files(module_id)
        context = self._build_context(module_id)

        kwargs: Dict[str, Any] = {
            "task_id": self.task_id,
            "config": self.task_config,
            "input_files": input_files,
            "context": context,
        }

        upstream_map = self._get_upstream_fields(module_id)
        for field_name, upstream_id in upstream_map.items():
            kwargs[field_name] = self._extract_upstream_output(upstream_id)

        return input_class(**kwargs)

    def _collect_input_files(self, module_id: str) -> Dict[str, str]:
        """Collect file paths for the module from upstream outputs and config."""
        files: Dict[str, str] = {}
        # Module 01 is the entry point — seed with task config path
        if module_id == "01":
            files["research_task.yaml"] = str(self.task_config_path)
        for mid, output in self._module_outputs.items():
            if hasattr(output, "output_files"):
                for name, path in output.output_files.items():
                    files[name] = path
        return files

    def _build_context(self, module_id: str) -> Dict[str, Any]:
        """Build context dict from all upstream module manifests."""
        context: Dict[str, Any] = {}
        for mid, output in self._module_outputs.items():
            if hasattr(output, "manifest"):
                context[f"module_{mid}"] = output.manifest

        # v8.2: Inject skill instructions into context
        if self._skill_integration:
            try:
                context = self._skill_integration.enhance_context(module_id, context)
            except Exception as e:
                logger.warning("Skill integration failed for module %s: %s", module_id, e)
                context.setdefault("skill_instructions", "")
                context.setdefault("available_skills", [])

        # v8.2: Inject human-in-the-loop feedback
        if module_id in HUMAN_FEEDBACK_MODULES:
            feedback_type = HUMAN_FEEDBACK_MODULES[module_id]
            feedback_dir = _V3_ROOT / "human_feedback"
            if self._skill_integration:
                try:
                    feedback = self._skill_integration.read_human_feedback(feedback_dir, feedback_type)
                    if feedback:
                        context["human_feedback"] = feedback
                        logger.info("Human feedback loaded for module %s (%s)", module_id, feedback_type)
                except Exception as e:
                    logger.warning("Human feedback read failed for module %s: %s", module_id, e)

        # v8.2.2: Inject pipeline reference for fallback queries
        context["pipeline"] = self
        context["run_mode"] = self._run_mode

        return context

    def _get_upstream_fields(self, module_id: str) -> Dict[str, str]:
        """Map upstream field names to module IDs for a given module."""
        upstream_map: Dict[str, str] = {}
        if module_id == "02":
            upstream_map = {"upstream_module_01": "01"}
        elif module_id == "02_5":
            upstream_map = {"upstream_module_02": "02"}
        elif module_id == "03":
            upstream_map = {"upstream_module_02": "02"}
        elif module_id == "04":
            upstream_map = {"upstream_module_03": "03"}
        elif module_id == "05":
            upstream_map = {
                "upstream_module_03": "03",
                "upstream_module_04": "04",
            }
        elif module_id == "06":
            upstream_map = {"upstream_module_05": "05"}
        elif module_id == "07":
            upstream_map = {"upstream_module_06": "06"}
        elif module_id == "08":
            upstream_map = {
                "upstream_module_06": "06",
                "upstream_module_07": "07",
            }
        elif module_id == "09":
            upstream_map = {
                "upstream_module_06": "06",
                "upstream_module_07": "07",
            }
        elif module_id == "10":
            upstream_map = {
                "upstream_module_07": "07",
                "upstream_module_08": "08",
                "upstream_module_09": "09",
            }
        elif module_id == "11":
            upstream_map = {
                "upstream_module_06": "06",
                "upstream_module_07": "07",
                "upstream_module_08": "08",
                "upstream_module_09": "09",
                "upstream_module_external": "external",
            }
        elif module_id == "12":
            upstream_map = {"upstream_module_all": "all"}
        elif module_id == "13":
            upstream_map = {
                "upstream_module_01": "01",
                "upstream_module_12": "12",
            }
        elif module_id == "14":
            upstream_map = {
                "upstream_module_12": "12",
                "upstream_module_13": "13",
            }
        return upstream_map

    def _extract_upstream_output(self, upstream_id: str) -> Dict[str, Any]:
        """Extract upstream output as a dict for input construction."""
        if upstream_id == "all":
            result = {}
            for mid, output in self._module_outputs.items():
                if hasattr(output, "manifest"):
                    result[mid] = output.manifest
                    if hasattr(output, "output_files"):
                        result[mid]["output_files"] = output.output_files
                else:
                    result[mid] = output
            return result
        if upstream_id == "external":
            return {}
        output = self._module_outputs.get(upstream_id)
        if output is None:
            return {}
        result = {}
        if hasattr(output, "manifest"):
            result = dict(output.manifest)
        elif isinstance(output, dict):
            result = dict(output)
        if hasattr(output, "output_files"):
            result["output_files"] = output.output_files
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_stub_output(module_id: str, input_data: Any) -> Any:
        """Create a minimal stub output for failed modules.

        Returns a SimpleNamespace with output_files, manifest, warnings,
        and errors so downstream modules can access them without crashing.
        """
        from types import SimpleNamespace
        return SimpleNamespace(
            task_id=getattr(input_data, "task_id", ""),
            output_files={},
            manifest={"module_id": module_id, "status": "FAILED", "stub": True},
            warnings=["Module failed, stub output created"],
            errors=["Module execution failed"],
        )

    @staticmethod
    def _find_next_module(completed: List[str]) -> Optional[str]:
        """Find the next module to execute after completed ones."""
        for mid in MODULE_SEQUENCE:
            if mid not in completed:
                return mid
        return None
