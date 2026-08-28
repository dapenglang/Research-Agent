"""
Orchestrator package for Research Agent v3.

The PipelineOrchestrator manages the full research pipeline lifecycle:
  start  — Launch a new research task from scratch
  resume — Resume an interrupted/paused task from checkpoint
  rerun  — Re-execute from a specific module
  status — Query current pipeline state

The orchestrator is the ONLY layer that calls modules directly.
The CLI calls the orchestrator; it never touches modules.
"""

from .pipeline import PipelineOrchestrator

__all__ = ["PipelineOrchestrator"]
