"""Module 12 — Paper Writing Engine.

Generates research papers in Markdown (intermediate), LaTeX, and Word formats.
Uses LLM with paper_generation task type (mock prohibited).
"""

from .interface import PaperWritingInput, PaperWritingOutput, Module12Interface

__all__ = [
    "PaperWritingInput",
    "PaperWritingOutput",
    "Module12Interface",
]
