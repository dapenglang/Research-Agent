"""
Research Agent v3 — Modular Research Automation Framework

Unified package exporting all v3 subsystems:
  - core:          exceptions, contracts, state machine, provenance, validation
  - infrastructure: storage, LLM, models, memory, config loading
  - modules:        13 research workflow modules (01-13)
  - adapters:       method backend interface + SAMRA adapter
  - cli:            command-line orchestrator
"""

__version__ = "3.0.0"
__author__ = "Research Agent v3"

# ============================================================
# Sub-package imports
# ============================================================

from Research_Agent_v3 import core
from Research_Agent_v3 import infrastructure
from Research_Agent_v3 import modules
from Research_Agent_v3 import adapters

# ============================================================
# Key exports
# ============================================================

# Core
from Research_Agent_v3.core.exceptions import (
    ResearchAgentError,
    StateError,
    CheckpointError,
    ValidationError,
    ModuleError,
)
from Research_Agent_v3.core.state import ResearchState, State, CheckpointManager
from Research_Agent_v3.core.provenance import ProvenanceTracker

# Infrastructure
from Research_Agent_v3.infrastructure.llm.llm_provider import (
    LLMProvider,
    LLMProviderFactory,
    validate_usage,
)
from Research_Agent_v3.infrastructure.memory.memory_retriever import MemoryRetriever
from Research_Agent_v3.infrastructure.storage.storage_manager import StorageManager

# Adapters
from Research_Agent_v3.adapters import (
    MethodBackend,
    BackendRegistry,
    backend_registry,
    SAMRAAdapter,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "core",
    "ResearchAgentError",
    "StateError",
    "CheckpointError",
    "ValidationError",
    "ModuleError",
    "ResearchState",
    "State",
    "CheckpointManager",
    "ProvenanceTracker",
    # Infrastructure
    "infrastructure",
    "LLMProvider",
    "LLMProviderFactory",
    "validate_usage",
    "MemoryRetriever",
    "StorageManager",
    # Adapters
    "adapters",
    "MethodBackend",
    "BackendRegistry",
    "backend_registry",
    "SAMRAAdapter",
    # Modules
    "modules",
]
