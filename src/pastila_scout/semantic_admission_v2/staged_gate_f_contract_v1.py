"""Evaluation-only staged Gate-F prompt and schema contract; no execution edge."""
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EntryTypeV1(StrEnum):
    REAL_WORLD_COMMITMENT = "REAL_WORLD_COMMITMENT"
    CONTAINED_CREATIVE = "CONTAINED_CREATIVE"
    UNRESOLVED_SCOPE = "UNRESOLVED_SCOPE"


class ScopeBasisV1(StrEnum):
    ASSERTED = "ASSERTED"
    PRESUPPOSED = "PRESUPPOSED"
    ENTAILED = "ENTAILED"
    NECESSARILY_IMPLIED = "NECESSARILY_IMPLIED"
    CREATIVE_CONTAINED = "CREATIVE_CONTAINED"
    UNRESOLVED = "UNRESOLVED"


class EventAlignmentV1(StrEnum):
    GOVERNED_EVENT = "GOVERNED_EVENT"
    NEW_UNSUPPORTED_EVENT = "NEW_UNSUPPORTED_EVENT"
    CREATIVE_VEHICLE_ONLY = "CREATIVE_VEHICLE_ONLY"
    UNRESOLVED = "UNRESOLVED"


class ModalityV1(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    POSSIBLE = "POSSIBLE"
    CONDITIONAL = "CONDITIONAL"
    PROPOSED = "PROPOSED"
    EXPECTED = "EXPECTED"
    CERTAIN_OR_ACTUAL = "CERTAIN_OR_ACTUAL"
    UNRESOLVED = "UNRESOLVED"


class TimingV1(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PAST = "PAST"
    PRESENT = "PRESENT"
    ONGOING = "ONGOING"
    FUTURE = "FUTURE"
    COMPLETED = "COMPLETED"
    UNDATED = "UNDATED"
    UNRESOLVED = "UNRESOLVED"


class CoverageDecisionV1(StrEnum):
    COMPLETE = "COMPLETE"
    INDETERMINATE = "INDETERMINATE"


class PropositionEntryV1(_Frozen):
    entry_id: str = Field(pattern=r"^P[1-8]$")
    entry_type: EntryTypeV1
    candidate_span: str = Field(min_length=1)
    authority_support: str | None
    commitment: str = Field(min_length=1, max_length=500)
    scope_basis: ScopeBasisV1
    event_alignment: EventAlignmentV1
    authority_modality: ModalityV1
    candidate_modality: ModalityV1
    authority_timing: TimingV1
    candidate_timing: TimingV1
    independence_group: str = Field(pattern=r"^G[1-8]$")


class CoverageReceiptV1(_Frozen):
    candidate_reviewed_as_whole: bool
    embedded_propositions_checked: bool
    creative_scope_checked: bool
    unresolved_scope_present: bool


class PropositionLedgerV1(_Frozen):
    stage_id: str = Field(pattern=r"^PROPOSITION_LEDGER$")
    coverage_decision: CoverageDecisionV1
    entries: tuple[PropositionEntryV1, ...] = Field(min_length=1, max_length=8)
    coverage_receipt: CoverageReceiptV1

    @model_validator(mode="after")
    def complete_is_exhaustive_and_resolved(self):
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("entry_id values must be unique")
        if self.coverage_decision is CoverageDecisionV1.COMPLETE:
            receipt = self.coverage_receipt
            if not (receipt.candidate_reviewed_as_whole and receipt.embedded_propositions_checked
                    and receipt.creative_scope_checked) or receipt.unresolved_scope_present:
                raise ValueError("COMPLETE coverage receipt is invalid")
            unresolved = any(
                entry.entry_type is EntryTypeV1.UNRESOLVED_SCOPE
                or entry.scope_basis is ScopeBasisV1.UNRESOLVED
                or entry.event_alignment is EventAlignmentV1.UNRESOLVED
                or entry.authority_modality is ModalityV1.UNRESOLVED
                or entry.candidate_modality is ModalityV1.UNRESOLVED
                or entry.authority_timing is TimingV1.UNRESOLVED
                or entry.candidate_timing is TimingV1.UNRESOLVED
                for entry in self.entries
            )
            if unresolved:
                raise ValueError("COMPLETE ledger contains unresolved evidence")
        return self


def validate_source_membership(ledger: PropositionLedgerV1, *, factual_summary: str, candidate: str) -> None:
    """Validate exact membership only; never infer, normalize, repair, or relabel."""
    for entry in ledger.entries:
        if entry.candidate_span not in candidate:
            raise ValueError("CANDIDATE_SPAN_NOT_IN_CANDIDATE")
        if entry.authority_support is not None and entry.authority_support not in factual_summary:
            raise ValueError("AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY")


class StagedGateFPromptContractV1:
    """Construct frozen Stage P/C prompts without any provider capability."""

    def __init__(self, project_root: Path) -> None:
        root = project_root.resolve(strict=True)
        self.stage_p_template, self.stage_p_prompt_identity = _load(root, "semantic-admission-v2-stage-p-prompt-v1.txt")
        self.stage_c_template, self.stage_c_prompt_identity = _load(root, "semantic-admission-v2-stage-c-prompt-v1.txt")

    def render_stage_p(self, *, factual_summary: str, candidate: str) -> str:
        return _render(self.stage_p_template, factual_summary=factual_summary, candidate=candidate)

    def render_stage_c(self, *, factual_summary: str, candidate: str, ledger: PropositionLedgerV1) -> str:
        serialized = ledger.model_dump_json()
        return _render(self.stage_c_template, factual_summary=factual_summary, candidate=candidate).replace(
            "{stage_p_ledger}", serialized
        )


def _load(root: Path, name: str) -> tuple[str, str]:
    data = (root / "docs" / "artifacts" / name).read_bytes()
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise RuntimeError("staged prompt padding drift")
    execution = data[:-1]
    execution.decode("utf-8", errors="strict")
    return execution.decode("utf-8"), "sha256:" + hashlib.sha256(execution).hexdigest()


def _render(template: str, *, factual_summary: str, candidate: str) -> str:
    if type(factual_summary) is not str or type(candidate) is not str or not factual_summary or not candidate:
        raise ValueError("staged Gate F request text is invalid")
    rendered = template.replace("{factual_summary}", factual_summary).replace("{candidate}", candidate)
    if "{factual_summary}" in rendered or "{candidate}" in rendered:
        raise ValueError("staged Gate F prompt construction incomplete")
    return rendered


def canonical_stage_p_schema() -> dict[str, object]:
    return PropositionLedgerV1.model_json_schema()


__all__ = (
    "PropositionLedgerV1", "StagedGateFPromptContractV1", "canonical_stage_p_schema",
    "validate_source_membership",
)
