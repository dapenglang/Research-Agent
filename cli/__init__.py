"""
CLI package for Research Agent v3.

Entry point: research-agent {start|resume|rerun|status}

The CLI delegates all work to PipelineOrchestrator.
It never imports or calls modules directly.
"""

from .cli import main

__all__ = ["main"]
