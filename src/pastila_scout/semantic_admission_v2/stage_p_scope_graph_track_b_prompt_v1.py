"""Construction-only contract for the Track-B semantic scope prompt."""
from __future__ import annotations

import hashlib
from pathlib import Path


PROMPT_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-prompt-v1.txt")


class StagePScopeGraphTrackBPromptContractV1:
    def __init__(self, project_root: Path) -> None:
        data = (project_root.resolve(strict=True) / PROMPT_RELATIVE).read_bytes()
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise RuntimeError("Track-B prompt padding drift")
        execution = data[:-1]
        self.template = execution.decode("utf-8", errors="strict")
        if self.template.count("{candidate}") != 1 or self.template.count("{factual_summary}") != 1:
            raise RuntimeError("Track-B prompt placeholder drift")
        if self.template.index("{candidate}") >= self.template.index("{factual_summary}"):
            raise RuntimeError("Track-B candidate-first ordering drift")
        self.prompt_identity = "sha256:" + hashlib.sha256(execution).hexdigest()

    def render(self, *, factual_summary: str, candidate: str) -> str:
        if type(factual_summary) is not str or type(candidate) is not str or not factual_summary or not candidate:
            raise ValueError("Track-B prompt source text invalid")
        if "{factual_summary}" in factual_summary or "{candidate}" in candidate:
            raise ValueError("Track-B reserved placeholder in source text")
        rendered = self.template.replace("{candidate}", candidate).replace("{factual_summary}", factual_summary)
        if "{candidate}" in rendered or "{factual_summary}" in rendered:
            raise ValueError("Track-B prompt render incomplete")
        return rendered


__all__ = ("PROMPT_RELATIVE", "StagePScopeGraphTrackBPromptContractV1")
