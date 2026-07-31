"""Storage-independent contracts for the evolving Scout pipeline."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PipelineStage = Literal[
    "sources",
    "parsing",
    "deduplication",
    "ai",
    "scoring",
    "reporting",
    "cache",
]
PipelineStageStatus = Literal["pending", "running", "success", "partial", "failed"]


class PipelineDiagnostic(BaseModel):
    """One portable diagnostic emitted by a pipeline stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    severity: Literal["info", "warning", "error"]
    entity_id: str | None = None


class PipelineStageResult(BaseModel):
    """Typed result boundary for one independently observable stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: PipelineStage
    status: PipelineStageStatus
    started_at: datetime
    finished_at: datetime | None = None
    processed_count: int = 0
    diagnostics: tuple[PipelineDiagnostic, ...] = ()


class PipelineRunResult(BaseModel):
    """Portable aggregate returned to future CLI and GUI callers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: PipelineStageStatus
    started_at: datetime
    finished_at: datetime | None = None
    stages: tuple[PipelineStageResult, ...] = ()
