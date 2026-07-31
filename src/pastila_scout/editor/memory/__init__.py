"""Verdict-driven Editorial Memory, isolated from generation and knowledge bases."""

from pastila_scout.editor.memory.models import (
    CandidateFinding,
    EditorialCategory,
    EditorialMemory,
    EditorialProfile,
    VerdictInput,
    VerdictProcessingResult,
)
from pastila_scout.editor.memory.processor import (
    detect_patterns,
    interpret_verdict,
    process_verdict,
)
from pastila_scout.editor.memory.storage import load_memory, save_memory

__all__ = [
    "CandidateFinding",
    "EditorialCategory",
    "EditorialMemory",
    "EditorialProfile",
    "VerdictInput",
    "VerdictProcessingResult",
    "detect_patterns",
    "interpret_verdict",
    "load_memory",
    "process_verdict",
    "save_memory",
]
