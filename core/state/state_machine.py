"""Research Agent state machine.

Defines all possible states, the valid transitions between them, and a
``ResearchState`` class that persists to ``state/<task_id>/research_state.yaml``.

The state machine supports the full research pipeline lifecycle including
experiment-specific states for running, interrupting, and resuming.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from Research_Agent_v3.core.exceptions import StateError


class State(str, Enum):
    """All possible states the research pipeline can be in."""

    INIT = "init"
    LOADING_CONFIG = "loading_config"
    DEPENDENCY_CHECK = "dependency_check"
    MODULE_EXECUTING = "module_executing"
    VALIDATION_GATE = "validation_gate"
    DECISION_ROUTING = "decision_routing"
    CHECKPOINT = "checkpoint"
    RESUMING = "resuming"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED_HUMAN_REVIEW = "paused_human_review"
    EXPERIMENT_RUNNING = "experiment_running"
    EXPERIMENT_INTERRUPTED = "experiment_interrupted"
    EXPERIMENT_RESUMING = "experiment_resuming"


# Valid transitions: from_state -> set of allowed target states
_VALID_TRANSITIONS: Dict[State, set[State]] = {
    State.INIT: {State.LOADING_CONFIG},
    State.LOADING_CONFIG: {State.DEPENDENCY_CHECK, State.FAILED},
    State.DEPENDENCY_CHECK: {State.MODULE_EXECUTING, State.FAILED},
    State.MODULE_EXECUTING: {
        State.VALIDATION_GATE,
        State.CHECKPOINT,
        State.FAILED,
        State.EXPERIMENT_RUNNING,
    },
    State.VALIDATION_GATE: {
        State.DECISION_ROUTING,
        State.MODULE_EXECUTING,
        State.PAUSED_HUMAN_REVIEW,
        State.FAILED,
    },
    State.DECISION_ROUTING: {
        State.MODULE_EXECUTING,
        State.COMPLETED,
        State.PAUSED_HUMAN_REVIEW,
    },
    State.CHECKPOINT: {State.MODULE_EXECUTING, State.RESUMING, State.FAILED},
    State.RESUMING: {State.MODULE_EXECUTING, State.VALIDATION_GATE, State.FAILED},
    State.COMPLETED: set(),
    State.FAILED: {State.INIT, State.RESUMING},
    State.PAUSED_HUMAN_REVIEW: {State.MODULE_EXECUTING, State.DECISION_ROUTING, State.FAILED},
    State.EXPERIMENT_RUNNING: {
        State.EXPERIMENT_INTERRUPTED,
        State.VALIDATION_GATE,
        State.CHECKPOINT,
        State.FAILED,
    },
    State.EXPERIMENT_INTERRUPTED: {State.EXPERIMENT_RESUMING, State.FAILED},
    State.EXPERIMENT_RESUMING: {
        State.EXPERIMENT_RUNNING,
        State.VALIDATION_GATE,
        State.FAILED,
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModuleStateRecord:
    """Per-module state tracked in the research state file."""

    status: str = "pending"
    started_at: str = ""
    finished_at: str = ""
    inputs_verified: bool = False
    outputs_verified: bool = False
    quality_score: Optional[float] = None
    manifest_path: str = ""
    checkpoint_path: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    next_recommended_module: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleStateRecord":
        return cls(
            status=data.get("status", "pending"),
            started_at=data.get("started_at", ""),
            finished_at=data.get("finished_at", ""),
            inputs_verified=data.get("inputs_verified", False),
            outputs_verified=data.get("outputs_verified", False),
            quality_score=data.get("quality_score"),
            manifest_path=data.get("manifest_path", ""),
            checkpoint_path=data.get("checkpoint_path", ""),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            next_recommended_module=data.get("next_recommended_module"),
        )


class ResearchState:
    """Manages the persistent state of a research task.

    State is saved to ``state/<task_id>/research_state.yaml`` and can be
    loaded on resume.  The class enforces valid state transitions and
    supports experiment-specific lifecycle methods.
    """

    SCHEMA_VERSION: str = "1.0"
    DEFAULT_MAX_RETRIES: int = 3

    def __init__(
        self,
        task_id: str,
        state_root: str | Path = "state",
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.task_id = task_id
        self.state_root = Path(state_root)
        self.max_retries = max_retries

        self.schema_version = self.SCHEMA_VERSION
        self.status: State = State.INIT
        self.current_module: Optional[str] = None
        self.completed_modules: List[str] = []
        self.module_states: Dict[str, ModuleStateRecord] = {}
        self.decision_routing: Dict[str, Any] = {}
        self.created_at: str = _now_iso()
        self.updated_at: str = self.created_at
        self._retry_count: int = 0
        self._previous_status: Optional[State] = None

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @property
    def state_dir(self) -> Path:
        return self.state_root / self.task_id

    @property
    def state_file(self) -> Path:
        return self.state_dir / "research_state.yaml"

    # ------------------------------------------------------------------
    # Transition logic
    # ------------------------------------------------------------------

    def _validate_transition(self, target: State) -> None:
        """Raise ``StateError`` if the transition is not allowed."""
        if target == self.status:
            return  # same-state is always allowed (no-op)
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise StateError(
                f"Invalid state transition: {self.status.value} -> {target.value}. "
                f"Allowed targets from {self.status.value}: "
                f"{[s.value for s in allowed] or 'none (terminal state)'}"
            )

    def transition_to(self, target: State | str) -> None:
        """Transition to *target* state after validating the transition.

        Args:
            target: The target state (enum member or string value).

        Raises:
            StateError: If the transition is not in the allowed set.
        """
        if isinstance(target, str):
            target = State(target)
        self._validate_transition(target)
        self._previous_status = self.status
        self.status = target
        self.updated_at = _now_iso()
        self.save()

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the pipeline from ``INIT``."""
        if self.status != State.INIT:
            raise StateError(f"Cannot start: current status is {self.status.value}, expected init")
        self.transition_to(State.LOADING_CONFIG)

    def resume(self) -> None:
        """Resume the pipeline from a paused/failed/checkpoint state."""
        if self.status not in (
            State.FAILED,
            State.CHECKPOINT,
            State.PAUSED_HUMAN_REVIEW,
            State.EXPERIMENT_INTERRUPTED,
        ):
            raise StateError(
                f"Cannot resume from status {self.status.value}; "
                "resume is only valid from failed, checkpoint, "
                "paused_human_review, or experiment_interrupted"
            )

        if self.status == State.EXPERIMENT_INTERRUPTED:
            self.transition_to(State.EXPERIMENT_RESUMING)
        else:
            self.transition_to(State.RESUMING)

    # ------------------------------------------------------------------
    # Module management
    # ------------------------------------------------------------------

    def set_current_module(self, module_id: str) -> None:
        """Record the module currently being executed."""
        self.current_module = module_id
        if module_id not in self.module_states:
            self.module_states[module_id] = ModuleStateRecord(
                status="running", started_at=_now_iso()
            )
        else:
            record = self.module_states[module_id]
            record.status = "running"
            record.started_at = _now_iso()
        self.updated_at = _now_iso()
        self.save()

    def complete_module(self, module_id: str, quality_score: Optional[float] = None) -> None:
        """Mark a module as completed."""
        if module_id not in self.module_states:
            self.module_states[module_id] = ModuleStateRecord()
        record = self.module_states[module_id]
        record.status = "completed"
        record.finished_at = _now_iso()
        record.quality_score = quality_score
        if module_id not in self.completed_modules:
            self.completed_modules.append(module_id)
        self.current_module = None
        self.updated_at = _now_iso()
        self.save()

    def fail_module(self, module_id: str, error: str) -> None:
        """Mark a module as failed and record the error."""
        if module_id not in self.module_states:
            self.module_states[module_id] = ModuleStateRecord()
        record = self.module_states[module_id]
        record.status = "failed"
        record.finished_at = _now_iso()
        record.errors.append(error)
        self._retry_count += 1
        self.updated_at = _now_iso()
        self.save()

    def get_module_status(self, module_id: str) -> Optional[str]:
        """Return the status string for a module, or ``None`` if unknown."""
        record = self.module_states.get(module_id)
        return record.status if record else None

    def can_retry(self) -> bool:
        """Return ``True`` if the retry limit has not been reached."""
        return self._retry_count < self.max_retries

    # ------------------------------------------------------------------
    # Experiment-specific methods
    # ------------------------------------------------------------------

    def start_experiment(self, module_id: str) -> None:
        """Transition into ``EXPERIMENT_RUNNING`` for an experiment module."""
        if self.status != State.MODULE_EXECUTING:
            raise StateError(
                f"Cannot start experiment from {self.status.value}; "
                "must be in module_executing"
            )
        self.set_current_module(module_id)
        self.transition_to(State.EXPERIMENT_RUNNING)

    def interrupt_experiment(self) -> None:
        """Interrupt a running experiment (e.g. user stop or resource limit)."""
        if self.status != State.EXPERIMENT_RUNNING:
            raise StateError(
                f"Cannot interrupt experiment from {self.status.value}; "
                "must be in experiment_running"
            )
        self.transition_to(State.EXPERIMENT_INTERRUPTED)

    def resume_experiment(self) -> None:
        """Resume an interrupted experiment."""
        if self.status != State.EXPERIMENT_INTERRUPTED:
            raise StateError(
                f"Cannot resume experiment from {self.status.value}; "
                "must be in experiment_interrupted"
            )
        self.transition_to(State.EXPERIMENT_RESUMING)
        self.transition_to(State.EXPERIMENT_RUNNING)

    def complete_experiment(self, module_id: str, quality_score: Optional[float] = None) -> None:
        """Complete an experiment and transition back to the validation gate."""
        if self.status not in (State.EXPERIMENT_RUNNING, State.EXPERIMENT_RESUMING):
            raise StateError(
                f"Cannot complete experiment from {self.status.value}; "
                "must be in experiment_running or experiment_resuming"
            )
        self.complete_module(module_id, quality_score)
        self.transition_to(State.VALIDATION_GATE)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> Path:
        """Persist the state to ``research_state.yaml``.

        Returns:
            Path to the written file.
        """
        self.state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "task_id": self.task_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "current_module": self.current_module,
            "completed_modules": self.completed_modules,
            "module_states": {
                mid: rec.to_dict() for mid, rec in self.module_states.items()
            },
            "decision_routing": self.decision_routing,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "retry_count": self._retry_count,
            "max_retries": self.max_retries,
        }
        self.state_file.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return self.state_file

    def load(self) -> None:
        """Load state from ``research_state.yaml`` if it exists.

        Raises:
            StateError: If the file exists but is malformed.
        """
        if not self.state_file.exists():
            return

        data = yaml.safe_load(self.state_file.read_text(encoding="utf-8"))
        if data is None:
            return

        try:
            self.schema_version = data.get("schema_version", self.SCHEMA_VERSION)
            self.status = State(data.get("status", State.INIT.value))
            self.current_module = data.get("current_module")
            self.completed_modules = data.get("completed_modules", [])
            self.module_states = {
                mid: ModuleStateRecord.from_dict(rec)
                for mid, rec in data.get("module_states", {}).items()
            }
            self.decision_routing = data.get("decision_routing", {})
            self.created_at = data.get("created_at", self.created_at)
            self.updated_at = data.get("updated_at", self.updated_at)
            self._retry_count = data.get("retry_count", 0)
            self.max_retries = data.get("max_retries", self.DEFAULT_MAX_RETRIES)
        except (KeyError, ValueError) as exc:
            raise StateError(f"Malformed state file {self.state_file}: {exc}") from exc

    def get_current_state(self) -> State:
        """Return the current state enum."""
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict snapshot of the state."""
        return {
            "task_id": self.task_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "current_module": self.current_module,
            "completed_modules": self.completed_modules,
            "module_states": {
                mid: rec.to_dict() for mid, rec in self.module_states.items()
            },
            "decision_routing": self.decision_routing,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "retry_count": self._retry_count,
            "max_retries": self.max_retries,
        }
