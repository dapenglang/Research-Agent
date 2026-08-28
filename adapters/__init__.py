"""
Adapters package for Research Agent v3.

Method backends are pluggable adapters. SAMRA is one such adapter.
New research methods create their own adapter and register it.
"""

from .method_backend_interface import (
    MethodBackend,
    MethodSpec,
    ExperimentResult,
    BackendRegistry,
    backend_registry,
)
from .samra_adapter import SAMRAAdapter

__all__ = [
    "MethodBackend",
    "MethodSpec",
    "ExperimentResult",
    "BackendRegistry",
    "backend_registry",
    "SAMRAAdapter",
]
