"""Deterministic canonical identities for Module 2.9 artifacts."""

import hashlib
import re
from typing import Any

from .canonical import canonical_bytes
from .defaults import IDENTITY_PATTERN


def derive_identity(artifact_type: str, identity_seed: Any) -> str:
    """Derive ``scout:<artifact-type>:<sha256>`` from canonical semantics."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", artifact_type):
        raise ValueError("artifact_type must be a lowercase hyphenated token")
    digest = hashlib.sha256(canonical_bytes(identity_seed)).hexdigest()
    return f"scout:{artifact_type}:{digest}"


def is_canonical_identity(value: str) -> bool:
    """Return whether a string uses the frozen canonical identity format."""
    return re.fullmatch(IDENTITY_PATTERN, value) is not None


def provider_request_identity(request) -> str:
    """Derive the frozen provider-request identity seed."""
    seed = {
        "contract_version": request.contract_version,
        "composition_plan_reference": request.composition_plan_reference,
        "composition_plan_fingerprint": request.composition_plan_fingerprint,
        "generation_profile_reference": request.generation_profile_reference,
        "generation_profile_fingerprint": request.generation_profile_fingerprint,
        "target_segment_references": request.target_segment_references,
        "target_beat_references": request.target_beat_references,
        "approved_claim_references": request.approved_claim_references,
        "source_span_references": request.source_span_references,
        "generation_instruction_fingerprints": tuple(
            item.instruction_fingerprint for item in request.generation_instructions
        ),
        "generation_constraint_fingerprints": tuple(
            item.constraint_fingerprint for item in request.generation_constraints
        ),
        "authority_references": request.authority_references,
        "output_schema_identity": request.output_schema_identity,
        "prompt_template_identity_reference": request.prompt_template_identity_reference,
        "execution_policy_reference": request.execution_policy_reference,
    }
    return derive_identity("provider-generation-request", seed)


def provider_response_identity(response) -> str:
    """Derive the frozen provider-response identity seed."""
    seed = {
        "contract_version": response.contract_version,
        "originating_request_identity": response.originating_request_identity,
        "originating_request_fingerprint": response.originating_request_fingerprint,
        "execution_status": response.execution_status,
        "unit_fingerprints": tuple(
            item.unit_fingerprint for item in response.structured_generated_units
        ),
        "partial_fingerprint": (
            response.partial_response.partial_fingerprint
            if response.partial_response is not None
            else None
        ),
        "failure_reason": response.failure_reason,
    }
    return derive_identity("provider-generation-response", seed)


def script_segment_identity(
    composition_plan_fingerprint: str, composition_segment_reference: str, position: int
) -> str:
    return derive_identity(
        "script-segment",
        (composition_plan_fingerprint, composition_segment_reference, position),
    )


def script_beat_identity(
    composition_plan_fingerprint: str,
    composition_segment_reference: str,
    composition_beat_reference: str,
    position: int,
) -> str:
    return derive_identity(
        "script-beat",
        (
            composition_plan_fingerprint,
            composition_segment_reference,
            composition_beat_reference,
            position,
        ),
    )


def script_paragraph_identity(
    request_fingerprint: str,
    composition_segment_reference: str,
    composition_beat_reference: str,
    paragraph_ordinal: int,
) -> str:
    return derive_identity(
        "script-paragraph",
        (
            request_fingerprint,
            composition_segment_reference,
            composition_beat_reference,
            paragraph_ordinal,
        ),
    )


def script_sentence_identity(
    request_fingerprint: str,
    composition_segment_reference: str,
    composition_beat_reference: str,
    paragraph_ordinal: int,
    sentence_ordinal: int,
) -> str:
    return derive_identity(
        "script-sentence",
        (
            request_fingerprint,
            composition_segment_reference,
            composition_beat_reference,
            paragraph_ordinal,
            sentence_ordinal,
        ),
    )


def text_span_identity(
    parent_sentence_reference: str,
    start_offset: int,
    end_offset: int,
    binding_classification: str,
    referenced_text: str,
) -> str:
    return derive_identity(
        "text-span",
        (
            parent_sentence_reference,
            start_offset,
            end_offset,
            binding_classification,
            referenced_text,
        ),
    )


def revision_request_identity(request) -> str:
    return derive_identity(
        "revision-request",
        {
            "prior_script_draft_reference": request.prior_script_draft_reference,
            "prior_script_draft_fingerprint": request.prior_script_draft_fingerprint,
            "revision_scope": request.revision_scope,
            "target_references": request.target_references,
            "revision_type": request.revision_type,
            "requested_change_reference": request.requested_change_reference,
            "revision_reason_reference": request.revision_reason_reference,
            "revision_authority_fingerprint": request.revision_authority.authority_fingerprint,
            "preserved_constraint_references": request.preserved_constraint_references,
        },
    )


def revision_result_identity(result) -> str:
    return derive_identity(
        "revision-execution-result",
        {
            "revision_request_reference": result.revision_request_reference,
            "revision_request_fingerprint": result.revision_request_fingerprint,
            "prior_draft_fingerprint": result.prior_draft_fingerprint,
            "resulting_draft_fingerprint": result.resulting_draft_fingerprint,
            "changed_units": tuple(
                item.textual_unit_reference for item in result.changed_textual_units
            ),
            "preserved_units": tuple(
                item.textual_unit_reference for item in result.preserved_textual_units
            ),
            "execution_status": result.execution_status,
        },
    )


__all__ = (
    "derive_identity",
    "provider_request_identity",
    "provider_response_identity",
    "revision_request_identity",
    "revision_result_identity",
    "script_beat_identity",
    "script_paragraph_identity",
    "script_segment_identity",
    "script_sentence_identity",
    "text_span_identity",
)
