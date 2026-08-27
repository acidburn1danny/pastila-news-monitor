"""Exact Phase 2 prompt rendering and application-request candidates.

No provider authority is built and no provider, grammar, tokenizer, model,
runner, or subprocess is imported. Untrusted text is transported only as
strictly verified base64 inside the rendered canonical data envelope.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .immutable_source_span_reference_v1 import SourceRoleV1, SourceSpanReferenceV1
from .stage_p_construction_obligation_contract_v2 import ConstructionObligationLedgerV2
from .stage_p_role_coherence_contract_v1 import EntryType, EventAlignment, Modality, Timing


COMMITMENT_PROMPT_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-commitment-span-audit-prompt-v1-design.txt")
AUTHORITY_PROMPT_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-authority-reconciliation-audit-prompt-v1-design.txt")
COMMITMENT_PROMPT_SHA256 = "dc0bede64944419bfbdf806af159659d918ec22f8677c2a4a2888e64d87026a8"
AUTHORITY_PROMPT_SHA256 = "379b4f8db641906a57b0f4c86a09ab119fc1fae30a2d7c29fed893901f02d6ed"
MAX_RENDERED_PROMPT_CHARACTERS = 64_000
MAX_RENDERED_PROMPT_UTF8_BYTES = 96_000
DATA_BEGIN = "BEGIN_CANONICAL_QUOTED_DATA_V1"
DATA_END = "END_CANONICAL_QUOTED_DATA_V1"

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
EntryId = Annotated[str, StringConstraints(pattern=r"^P[1-8]$")]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _decode_bound(value: str, digest: str, *, name: str, minimum: int = 1,
                  maximum: int = 100_000) -> bytes:
    try:
        data = base64.b64decode(value, validate=True)
        data.decode("utf-8", errors="strict")
    except Exception as exc:
        raise ValueError(f"{name}_BYTES_INVALID") from exc
    if not minimum <= len(data) <= maximum or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{name}_IDENTITY_OR_SIZE_INVALID")
    return data


class CommitmentEntryBindingV1(_Frozen):
    entry_id: EntryId
    entry_type: EntryType
    candidate_span_ref: SourceSpanReferenceV1
    projected_candidate_span_utf8_base64: str
    projected_candidate_span_sha256: Sha256


class CommitmentSpanAuditRequestEnvelopeV1(_Frozen):
    schema_name: Literal["pastila-semantic-admission-v2-stage-p-commitment-span-audit-request"]
    schema_version: Literal["1.0.0-evaluation-candidate.1"]
    candidate_utf8_base64: str
    candidate_sha256: Sha256
    frozen_ledger_utf8_base64: str
    frozen_ledger_sha256: Sha256
    source_projection_receipt_identity: Sha256
    span_shape_receipt_identity: Sha256
    graph_obligation_receipt_identity: Sha256
    ordered_entry_bindings: tuple[CommitmentEntryBindingV1, ...] = Field(min_length=1, max_length=8)
    prompt_identity: Literal[COMMITMENT_PROMPT_SHA256]

    @model_validator(mode="after")
    def bind_sources_and_ledger(self) -> "CommitmentSpanAuditRequestEnvelopeV1":
        candidate = _decode_bound(self.candidate_utf8_base64, self.candidate_sha256,
                                  name="COMMITMENT_CANDIDATE", maximum=8_000)
        ledger_bytes = _decode_bound(self.frozen_ledger_utf8_base64, self.frozen_ledger_sha256,
                                     name="COMMITMENT_LEDGER", maximum=64_000)
        ledger = ConstructionObligationLedgerV2.model_validate_json(ledger_bytes)
        if len(self.ordered_entry_bindings) != len(ledger.entries):
            raise ValueError("COMMITMENT_BINDING_ENTRY_COVERAGE_MISMATCH")
        for binding, entry in zip(self.ordered_entry_bindings, ledger.entries, strict=True):
            if (binding.entry_id != entry.entry_id or binding.entry_type is not entry.entry_type or
                    binding.candidate_span_ref != entry.candidate_span_ref):
                raise ValueError("COMMITMENT_BINDING_LEDGER_ENTRY_MISMATCH")
            _validate_projection(binding.candidate_span_ref,
                                 binding.projected_candidate_span_utf8_base64,
                                 binding.projected_candidate_span_sha256,
                                 source=candidate, source_sha=self.candidate_sha256,
                                 required_role=SourceRoleV1.CANDIDATE, name="COMMITMENT_ENTRY")
        return self


class AuthorityEntryBindingV1(_Frozen):
    entry_id: EntryId
    candidate_span_ref: SourceSpanReferenceV1
    projected_candidate_span_utf8_base64: str
    projected_candidate_span_sha256: Sha256
    candidate_commitment_analysis_utf8_base64: str
    candidate_commitment_analysis_sha256: Sha256
    ledger_event_alignment: EventAlignment
    authority_modality: Modality
    candidate_modality: Modality
    authority_timing: Timing
    candidate_timing: Timing


class AuthorityReconciliationAuditRequestEnvelopeV1(_Frozen):
    schema_name: Literal["pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-request"]
    schema_version: Literal["1.0.0-evaluation-candidate.1"]
    factual_authority_utf8_base64: str
    factual_authority_sha256: Sha256
    candidate_utf8_base64: str
    candidate_sha256: Sha256
    frozen_ledger_utf8_base64: str
    frozen_ledger_sha256: Sha256
    commitment_span_receipt_identity: Sha256
    ordered_real_world_entry_bindings: tuple[AuthorityEntryBindingV1, ...] = Field(
        min_length=1, max_length=8)
    prompt_identity: Literal[AUTHORITY_PROMPT_SHA256]

    @model_validator(mode="after")
    def bind_sources_and_ledger(self) -> "AuthorityReconciliationAuditRequestEnvelopeV1":
        authority = _decode_bound(self.factual_authority_utf8_base64,
                                  self.factual_authority_sha256,
                                  name="AUTHORITY_FACTUAL", maximum=8_000)
        del authority
        candidate = _decode_bound(self.candidate_utf8_base64, self.candidate_sha256,
                                  name="AUTHORITY_CANDIDATE", maximum=8_000)
        ledger_bytes = _decode_bound(self.frozen_ledger_utf8_base64, self.frozen_ledger_sha256,
                                     name="AUTHORITY_LEDGER", maximum=64_000)
        ledger = ConstructionObligationLedgerV2.model_validate_json(ledger_bytes)
        real_entries = tuple(entry for entry in ledger.entries
                             if entry.entry_type is EntryType.REAL_WORLD_COMMITMENT)
        if len(self.ordered_real_world_entry_bindings) != len(real_entries):
            raise ValueError("AUTHORITY_BINDING_ENTRY_COVERAGE_MISMATCH")
        for binding, entry in zip(self.ordered_real_world_entry_bindings, real_entries, strict=True):
            if (binding.entry_id != entry.entry_id or
                    binding.candidate_span_ref != entry.candidate_span_ref or
                    binding.ledger_event_alignment is not entry.event_alignment or
                    binding.authority_modality is not entry.authority_modality or
                    binding.candidate_modality is not entry.candidate_modality or
                    binding.authority_timing is not entry.authority_timing or
                    binding.candidate_timing is not entry.candidate_timing):
                raise ValueError("AUTHORITY_BINDING_LEDGER_ENTRY_MISMATCH")
            _validate_projection(binding.candidate_span_ref,
                                 binding.projected_candidate_span_utf8_base64,
                                 binding.projected_candidate_span_sha256,
                                 source=candidate, source_sha=self.candidate_sha256,
                                 required_role=SourceRoleV1.CANDIDATE, name="AUTHORITY_ENTRY")
            analysis = _decode_bound(binding.candidate_commitment_analysis_utf8_base64,
                                     binding.candidate_commitment_analysis_sha256,
                                     name="AUTHORITY_COMMITMENT_ANALYSIS", maximum=2_000)
            if analysis.decode("utf-8") != entry.commitment:
                raise ValueError("AUTHORITY_COMMITMENT_ANALYSIS_LEDGER_MISMATCH")
        return self


def _validate_projection(reference: SourceSpanReferenceV1, projected_base64: str,
                         projected_sha: str, *, source: bytes, source_sha: str,
                         required_role: SourceRoleV1, name: str) -> None:
    if reference.source_role is not required_role or reference.source_sha256 != source_sha:
        raise ValueError(f"{name}_REFERENCE_BINDING_INVALID")
    if not 0 <= reference.start_utf8 < reference.end_utf8 <= len(source):
        raise ValueError(f"{name}_REFERENCE_RANGE_INVALID")
    projected = _decode_bound(projected_base64, projected_sha, name=f"{name}_PROJECTION",
                              maximum=len(source))
    if projected != source[reference.start_utf8:reference.end_utf8]:
        raise ValueError(f"{name}_PROJECTION_MISMATCH")


def _canonical_json(value: BaseModel) -> str:
    return json.dumps(value.model_dump(mode="json"), ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


class Phase2AuditRequestCandidateV1:
    """Exact prompt-prefix and application-request construction only."""

    def __init__(self, *, project_root: Path, timeout_seconds: float = 240.0) -> None:
        self.project_root = project_root.resolve(strict=True)
        if type(timeout_seconds) is not float or timeout_seconds <= 0:
            raise ValueError("PHASE2_REQUEST_TIMEOUT_INVALID")
        self.timeout_seconds = timeout_seconds
        self.commitment_instruction = self._load_prompt(
            COMMITMENT_PROMPT_RELATIVE, COMMITMENT_PROMPT_SHA256)
        self.authority_instruction = self._load_prompt(
            AUTHORITY_PROMPT_RELATIVE, AUTHORITY_PROMPT_SHA256)
        identity_fields = (
            "STAGE_P_PHASE2_AUDIT_REQUEST_CANDIDATE_V1", COMMITMENT_PROMPT_SHA256,
            AUTHORITY_PROMPT_SHA256, str(timeout_seconds),
            str(MAX_RENDERED_PROMPT_CHARACTERS), str(MAX_RENDERED_PROMPT_UTF8_BYTES),
            "TOKEN_CONTEXT_PROOF_PENDING_SEPARATE_TOKENIZER_AUTHORITY",
        )
        self.candidate_identity = hashlib.sha256("\n".join(identity_fields).encode()).hexdigest()

    def _load_prompt(self, relative: Path, expected_sha: str) -> str:
        data = (self.project_root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise RuntimeError(f"PHASE2_PROMPT_IDENTITY_DRIFT:{relative.as_posix()}")
        return data.decode("utf-8", errors="strict")

    def render_commitment(self, envelope: CommitmentSpanAuditRequestEnvelopeV1) -> str:
        if type(envelope) is not CommitmentSpanAuditRequestEnvelopeV1:
            raise TypeError("PHASE2_COMMITMENT_ENVELOPE_REQUIRED")
        return self._render(self.commitment_instruction, envelope)

    def render_authority(self, envelope: AuthorityReconciliationAuditRequestEnvelopeV1) -> str:
        if type(envelope) is not AuthorityReconciliationAuditRequestEnvelopeV1:
            raise TypeError("PHASE2_AUTHORITY_ENVELOPE_REQUIRED")
        return self._render(self.authority_instruction, envelope)

    def _render(self, instruction: str, envelope: BaseModel) -> str:
        if not instruction.endswith("\n"):
            raise RuntimeError("PHASE2_PROMPT_FINAL_NEWLINE_DRIFT")
        rendered = instruction + "\n" + DATA_BEGIN + "\n" + _canonical_json(envelope) + "\n" + DATA_END
        if rendered != rendered.strip():
            raise RuntimeError("PHASE2_RENDERED_PROMPT_PADDING_INVALID")
        if (len(rendered) > MAX_RENDERED_PROMPT_CHARACTERS or
                len(rendered.encode("utf-8")) > MAX_RENDERED_PROMPT_UTF8_BYTES):
            raise ValueError("PHASE2_RENDERED_PROMPT_CONSERVATIVE_CONTEXT_BUDGET_EXCEEDED")
        return rendered

    def build_commitment_application(self, envelope: CommitmentSpanAuditRequestEnvelopeV1,
                                     *, requested_at: datetime) -> ApplicationProviderRequestV1:
        return self._build(self.render_commitment(envelope), "commitment-span-v1", requested_at)

    def build_authority_application(self, envelope: AuthorityReconciliationAuditRequestEnvelopeV1,
                                    *, requested_at: datetime) -> ApplicationProviderRequestV1:
        return self._build(self.render_authority(envelope), "authority-reconciliation-v1", requested_at)

    def _build(self, prompt: str, lane: str, requested_at: datetime) -> ApplicationProviderRequestV1:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:stage-p:{lane}:{digest[:24]}", requested_at,
            TimeoutPolicyV2(timeout_seconds=self.timeout_seconds),
            CancellationTokenV2(cancellation_requested=False))


__all__ = (
    "AUTHORITY_PROMPT_SHA256", "COMMITMENT_PROMPT_SHA256", "AuthorityEntryBindingV1",
    "AuthorityReconciliationAuditRequestEnvelopeV1", "CommitmentEntryBindingV1",
    "CommitmentSpanAuditRequestEnvelopeV1", "DATA_BEGIN", "DATA_END",
    "MAX_RENDERED_PROMPT_CHARACTERS", "MAX_RENDERED_PROMPT_UTF8_BYTES",
    "Phase2AuditRequestCandidateV1",
)
