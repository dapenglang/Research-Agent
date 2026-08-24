"""
Infrastructure layer for Research Agent v3.

Contains concrete implementations of cross-cutting concerns:
  - storage:   Path resolution and disk management
  - llm:       Unified LLM provider interface and prompt management
  - models:    Model hub (non-singleton) and validation
  - memory:    Three-layer memory store, retriever, and usage logger
  - validation: Configuration loading and validation
"""

__version__ = "3.0.0"
