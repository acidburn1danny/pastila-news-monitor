"""Construction-only contract for the approved Stage P Scope Graph prompt candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path


PROMPT_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-scope-graph-prompt-v1.txt")


class StagePScopeGraphPromptContractV1:
    def __init__(self, project_root: Path) -> None:
        data = (project_root.resolve(strict=True) / PROMPT_RELATIVE).read_bytes()
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise RuntimeError("Stage P scope-graph prompt padding drift")
        execution = data[:-1]
        self.template = execution.decode("utf-8", errors="strict")
        self.prompt_identity = "sha256:" + hashlib.sha256(execution).hexdigest()

    def render(self, *, factual_summary: str, candidate: str) -> str:
        if type(factual_summary) is not str or type(candidate) is not str or not factual_summary or not candidate:
            raise ValueError("Stage P scope-graph source text invalid")
        if "{factual_summary}" in factual_summary or "{candidate}" in candidate:
            raise ValueError("Stage P scope-graph reserved placeholder in source text")
        rendered = self.template.replace("{factual_summary}", factual_summary).replace("{candidate}", candidate)
        if "{factual_summary}" in rendered or "{candidate}" in rendered:
            raise ValueError("Stage P scope-graph render incomplete")
        return rendered


__all__ = ("PROMPT_RELATIVE", "StagePScopeGraphPromptContractV1")
