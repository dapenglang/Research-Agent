"""State package — state machine and checkpoint management."""

from .state_machine import (
    State,
    ResearchState,
    ModuleStateRecord,
)
from .checkpoint import CheckpointManager

__all__ = [
    "State",
    "ResearchState",
    "ModuleStateRecord",
    "CheckpointManager",
]
