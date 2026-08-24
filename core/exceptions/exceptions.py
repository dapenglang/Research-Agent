"""Unified exception hierarchy for Research Agent v3.

All custom exceptions inherit from ``ResearchAgentError`` so that callers
can catch any project-specific error with a single ``except`` clause.
"""


class ResearchAgentError(Exception):
    """Base exception for all Research Agent errors."""

    pass


class ConfigError(ResearchAgentError):
    """Raised when configuration is missing, malformed, or invalid."""

    pass


class ValidationError(ResearchAgentError):
    """Raised when input/output validation or quality assessment fails."""

    pass


class ModuleError(ResearchAgentError):
    """Raised when a pipeline module encounters an execution error."""

    pass


class StateError(ResearchAgentError):
    """Raised on illegal state transitions or corrupted state files."""

    pass


class StorageError(ResearchAgentError):
    """Raised when storage operations (read/write/list) fail."""

    pass


class ModelError(ResearchAgentError):
    """Raised when a local model fails to load, run, or produce output."""

    pass


class LLMProviderError(ResearchAgentError):
    """Raised when an LLM provider call fails or returns invalid output."""

    pass


class ExperimentError(ResearchAgentError):
    """Raised when experiment execution, interruption, or resumption fails."""

    pass


class ProvenanceError(ResearchAgentError):
    """Raised when provenance tracking detects an integrity violation."""

    pass


class CheckpointError(ResearchAgentError):
    """Raised when a checkpoint is missing, corrupted, or fails verification."""

    pass
