"""Module 13 — Reference & Supplementary.

Manages bibliography with paper_id/DOI binding. Prohibits LLM-generated fake citations.
"""

from .interface import ReferenceSupplementaryInput, ReferenceSupplementaryOutput, Module13Interface

__all__ = [
    "ReferenceSupplementaryInput",
    "ReferenceSupplementaryOutput",
    "Module13Interface",
]
