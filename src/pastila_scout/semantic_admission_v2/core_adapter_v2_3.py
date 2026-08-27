"""Gate-F-only V2.3 contract candidate; not authorized for runtime use."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .core_adapter import CoreV12SemanticEvaluatorAdapter
from .models import GateIdV2

GATE_F_V23_SOURCE_SHA256 = "0039235b478b3eb83a8f6ffa581cd574c6aab8048fac7fd9b3b820de656ea02d"
GATE_F_V23_EXECUTION_SHA256 = "92a95381b7f75b09aba6cd4580f3617a7df2a6a1520b0ee22c52db6e9886dcc1"
GATE_F_V23_EVALUATOR_IDENTITY = "242fe5c18f83c68fe1267ae5cc9ee65cd77157f5e9329bad26ffffee0c8892e5"


class CoreV12SemanticEvaluatorAdapterV23(CoreV12SemanticEvaluatorAdapter):
    """Render the frozen V2.3 Gate-F candidate while preserving the call boundary."""

    def __init__(self, *, project_root: Path, executor, gate_id: GateIdV2) -> None:
        if gate_id is not GateIdV2.FACTUAL_SEMANTIC:
            raise ValueError("SAV2.3 candidate is Gate-F-only")
        super().__init__(project_root=project_root, executor=executor, gate_id=gate_id)
        data = (project_root / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-3-prompt.txt").read_bytes()
        if hashlib.sha256(data).hexdigest() != GATE_F_V23_SOURCE_SHA256:
            raise RuntimeError("SAV2.3 source prompt identity drift")
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise RuntimeError("SAV2.3 source prompt padding drift")
        execution = data[:-1]
        if hashlib.sha256(execution).hexdigest() != GATE_F_V23_EXECUTION_SHA256:
            raise RuntimeError("SAV2.3 executable prompt identity drift")
        self._template = execution.decode("utf-8", errors="strict")
        self.prompt_identity = "sha256:" + GATE_F_V23_EXECUTION_SHA256
        self.evaluator_identity = GATE_F_V23_EVALUATOR_IDENTITY


__all__ = (
    "CoreV12SemanticEvaluatorAdapterV23",
    "GATE_F_V23_EVALUATOR_IDENTITY",
    "GATE_F_V23_EXECUTION_SHA256",
    "GATE_F_V23_SOURCE_SHA256",
)
