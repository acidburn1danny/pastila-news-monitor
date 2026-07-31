"""Phase 1 hardening regressions for the Module 2.9 contracts."""

import hashlib

import pytest
from pydantic import ValidationError

import pastila_scout.editor.script_composer as public_api
from pastila_scout.editor.script_composer import (
    AllegationStatus,
    ApprovedClaim,
    AttributionForm,
    AttributionRealization,
    AuthorityLevel,
    CertaintyLevel,
    DeliveryAnnotation,
    DeliveryAnnotationSemanticEffect,
    DeliveryAnnotationType,
    DomainValidationError,
    GenerationInstruction,
    GenerationInstructionType,
    ProviderExecutionReference,
    ProviderExecutionStatus,
    ProviderFailureReason,
    ProviderGeneratedUnit,
    ProviderGeneratedUnitKind,
    ProviderGenerationRequest,
    ProviderGenerationResponse,
    ProviderNeutralExecutionMetadata,
    ProviderPartialResponse,
    ProviderResponseValidationStatus,
    QuotationStatus,
    ResolvedGenerationPolicySnapshot,
    RevisionAuthority,
    RevisionAuthorityInputSnapshot,
    RevisionAuthorityType,
    RevisionExecutionResult,
    RevisionExecutionStatus,
    RevisionRequest,
    RevisionResultDisposition,
    RevisionScope,
    RevisionType,
    TextSpanBindingClassification,
    TextSpanReference,
    TextualUnitLineage,
    construct_artifact,
    derive_identity,
    provider_request_identity,
    provider_response_identity,
    revision_target_scope_fingerprint,
    semantic_fingerprint,
    validate_artifact,
)
from pastila_scout.editor.script_composer.validation import (
    PRIMARY_FINGERPRINT_FIELDS,
)

ZERO = "0" * 64
ONE = "1" * 64


def _seal(value, field):
    return value.model_copy(update={field: semantic_fingerprint(value)})


def _instruction():
    return _seal(
        GenerationInstruction(
            generation_instruction_id="instruction:one",
            instruction_type=GenerationInstructionType.BEAT_REALIZATION,
            target_references=("beat:one",),
            authority_level=AuthorityLevel.COMPOSITION_PLAN,
            instruction_reference="instruction-source:one",
            required=True,
            source_rule_references=("rule:one",),
            instruction_fingerprint=ZERO,
        ),
        "instruction_fingerprint",
    )


def _authority_inputs():
    return RevisionAuthorityInputSnapshot(
        **{name: ONE for name in RevisionAuthorityInputSnapshot.model_fields}
    )


def _provider_request():
    metadata = ProviderNeutralExecutionMetadata(
        execution_policy_reference="execution-policy:one",
        response_schema_reference="schema:one",
        reproducibility_policy_reference="reproducibility:one",
    )
    request = ProviderGenerationRequest(
        provider_generation_request_id=derive_identity(
            "provider-generation-request", "temporary"
        ),
        request_version="1.0.0",
        target_episode_reference="episode:one",
        target_segment_references=("segment:one",),
        target_beat_references=("beat:one",),
        generation_profile_reference="profile:one",
        generation_profile_fingerprint=ONE,
        composition_plan_reference="composition:one",
        composition_plan_fingerprint=ONE,
        authority_references=("authority:one",),
        output_schema_identity="schema:one",
        prompt_template_identity_reference="prompt:one",
        execution_policy_reference="execution-policy:one",
        provider_neutral_execution_metadata=metadata,
        request_fingerprint=ZERO,
    )
    request = request.model_copy(
        update={"provider_generation_request_id": provider_request_identity(request)}
    )
    return _seal(request, "request_fingerprint")


def _provider_response(request):
    unit = _seal(
        ProviderGeneratedUnit(
            provider_generated_unit_id=derive_identity(
                "provider-generated-unit", "one"
            ),
            unit_kind=ProviderGeneratedUnitKind.SENTENCE,
            target_segment_reference="segment:one",
            target_beat_reference="beat:one",
            paragraph_ordinal=1,
            sentence_ordinal=1,
            text="Text verificat.",
            unit_fingerprint=ZERO,
        ),
        "unit_fingerprint",
    )
    execution = ProviderExecutionReference(
        provider_execution_reference_id="execution:one",
        provider="provider:test",
        model="model:test",
        prompt_template_id="prompt:one",
        prompt_template_version="1.0.0",
        output_schema_version="1",
        request_fingerprint=request.request_fingerprint,
        status=ProviderExecutionStatus.SUCCESS,
        attempt_count=1,
        retry_count=0,
    )
    response = ProviderGenerationResponse(
        provider_generation_response_id=derive_identity(
            "provider-generation-response", "temporary"
        ),
        response_version="1.0.0",
        originating_request_identity=request.provider_generation_request_id,
        originating_request_fingerprint=request.request_fingerprint,
        provider_execution_reference=execution,
        execution_status=ProviderExecutionStatus.SUCCESS,
        structured_generated_units=(unit,),
        response_fingerprint=ZERO,
        validation_status=ProviderResponseValidationStatus.ACCEPTED,
    )
    response = response.model_copy(
        update={"provider_generation_response_id": provider_response_identity(response)}
    )
    return _seal(response, "response_fingerprint")


def test_recursive_validation_detects_corrupt_nested_fingerprint():
    instruction = _instruction().model_copy(update={"instruction_fingerprint": ZERO})
    policy = ResolvedGenerationPolicySnapshot(
        resolved_generation_policy_id="policy:one",
        policy_version="1.0.0",
        source_policy_reference="policy-source:one",
        source_policy_fingerprint=ONE,
        resolved_generation_instructions=(instruction,),
        authority_references=("authority:one",),
        policy_fingerprint=ZERO,
    )
    policy = _seal(policy, "policy_fingerprint")
    issues = validate_artifact(policy)
    assert any(
        issue.code == "fingerprint-mismatch"
        and issue.field_path
        == (
            "resolved_generation_instructions",
            0,
            "instruction_fingerprint",
        )
        for issue in issues
    )


def test_attribution_span_must_belong_to_same_sentence():
    span = TextSpanReference(
        text_span_id=derive_identity("text-span", "one"),
        parent_sentence_reference=derive_identity("script-sentence", "one"),
        start_offset=0,
        end_offset=1,
        referenced_text="A",
        binding_classification=TextSpanBindingClassification.ATTRIBUTION,
        span_fingerprint=ZERO,
    )
    with pytest.raises(ValidationError, match="attribution-span-parent-mismatch"):
        AttributionRealization(
            attribution_realization_id="attribution:one",
            script_sentence_reference=derive_identity("script-sentence", "two"),
            approved_claim_reference="claim:one",
            source_reference="source:one",
            required_attribution_reference="requirement:one",
            text_span_reference=span,
            attribution_form=AttributionForm.DIRECT,
            attribution_preserved=True,
            attribution_fingerprint=ZERO,
        )


def test_delivery_type_effect_matrix_is_enforced():
    with pytest.raises(ValidationError, match="semantic effect"):
        DeliveryAnnotation(
            delivery_annotation_id="annotation:one",
            target_text_reference="sentence:one",
            annotation_type=DeliveryAnnotationType.PAUSE,
            annotation_value_reference="pause:short",
            source_guidance_references=("guidance:one",),
            semantic_effect=DeliveryAnnotationSemanticEffect.PRESENTATION_ONLY,
            annotation_fingerprint=ZERO,
        )


def test_system_regeneration_cannot_change_authority_inputs():
    authority = _seal(
        RevisionAuthority(
            revision_authority_id="authority:system",
            authority_type=RevisionAuthorityType.SYSTEM,
            authority_reference="authority-source:system",
            authority_version="1.0.0",
            authorized_revision_types=(RevisionType.REGENERATION,),
            authority_fingerprint=ZERO,
        ),
        "authority_fingerprint",
    )
    changed = _authority_inputs().model_copy(update={"structure_fingerprint": ZERO})
    with pytest.raises(ValidationError, match="cannot change authority inputs"):
        RevisionRequest(
            revision_request_id=derive_identity("revision-request", "one"),
            prior_script_draft_reference="draft:one",
            prior_script_draft_fingerprint=ONE,
            revision_scope=RevisionScope.COMPLETE_DRAFT,
            target_references=("draft:one",),
            revision_type=RevisionType.REGENERATION,
            requested_change_reference="change:one",
            revision_reason_reference="reason:one",
            revision_authority=authority,
            preserved_constraint_references=("constraint:one",),
            immutable_upstream_references=("composition:one",),
            expected_readiness_impact="requires_editor_review",
            prior_authority_inputs=_authority_inputs(),
            requested_authority_inputs=changed,
            request_fingerprint=ZERO,
        )


def test_public_constructor_normalizes_pydantic_errors():
    with pytest.raises(DomainValidationError) as caught:
        construct_artifact(ApprovedClaim, {"approved_claim_id": "claim:one"})
    assert caught.value.issues
    assert {issue.code for issue in caught.value.issues} == {
        "contract-validation-failed"
    }
    assert all(issue.field_path for issue in caught.value.issues)


def test_public_api_does_not_leak_implementation_modules():
    assert not hasattr(public_api, "hashlib")
    assert not hasattr(public_api, "re")


def test_primary_fingerprint_registry_covers_hardened_contracts():
    assert PRIMARY_FINGERPRINT_FIELDS["TextualUnitLineage"] == "lineage_fingerprint"
    assert (
        PRIMARY_FINGERPRINT_FIELDS["ScriptCompositionInputBundle"]
        == "input_fingerprint"
    )
    assert PRIMARY_FINGERPRINT_FIELDS["VerifiedSourceMaterial"] == "source_fingerprint"
    lineage = _seal(
        TextualUnitLineage(
            textual_unit_reference="sentence:one",
            semantic_fingerprint=ONE,
            lineage_fingerprint=ZERO,
        ),
        "lineage_fingerprint",
    )
    assert validate_artifact(lineage) == ()


def test_canonical_sha256_fixed_vector_is_stable():
    payload = b'{"a":1,"b":"\xc8\x99"}'
    assert hashlib.sha256(payload).hexdigest() == (
        "5ac8f97f4a804b986aea10fb79e158ce0bf9d07580bd7594a0262dbf80fff5f4"
    )


def test_closed_claim_vocabularies_accept_normative_values():
    claim = ApprovedClaim(
        approved_claim_id="claim:one",
        claim_type="fact",
        canonical_claim="Fapt verificat.",
        source_span_references=("source-span:one",),
        certainty_level=CertaintyLevel.CONFIRMED,
        allegation_status=AllegationStatus.NOT_APPLICABLE,
        quotation_status=QuotationStatus.NOT_QUOTATION,
        claim_fingerprint=ZERO,
    )
    assert claim.certainty_level == CertaintyLevel.CONFIRMED


def test_resealed_provider_copy_cannot_bypass_explicit_validation():
    request = _provider_request()
    response = _provider_response(request)
    execution = response.provider_execution_reference.model_copy(
        update={
            "status": ProviderExecutionStatus.FAILED,
            "failure_reason": ProviderFailureReason.NONE,
        }
    )
    invalid = response.model_copy(
        update={
            "provider_execution_reference": execution,
            "execution_status": ProviderExecutionStatus.FAILED,
            "failure_reason": ProviderFailureReason.NONE,
            "validation_status": ProviderResponseValidationStatus.REJECTED,
        }
    )
    invalid = invalid.model_copy(
        update={"provider_generation_response_id": provider_response_identity(invalid)}
    )
    invalid = _seal(invalid, "response_fingerprint")
    assert "provider-failure-reason-required" in {
        issue.code for issue in validate_artifact(invalid)
    }


def test_provider_construction_and_explicit_validation_share_issue_semantics():
    request = _provider_request()
    invalid = _provider_response(request).model_copy(
        update={"execution_status": ProviderExecutionStatus.FAILED}
    )
    invalid = _seal(invalid, "response_fingerprint")
    explicit = next(
        issue
        for issue in validate_artifact(invalid)
        if issue.code == "provider-execution-status-mismatch"
    )
    with pytest.raises(DomainValidationError) as caught:
        construct_artifact(ProviderGenerationResponse, invalid.model_dump())
    constructed = next(
        issue
        for issue in caught.value.issues
        if issue.code == "provider-execution-status-mismatch"
    )
    assert constructed.artifact_reference == explicit.artifact_reference
    assert constructed.field_path == explicit.field_path


def test_resealed_attribution_copy_cannot_bypass_explicit_validation():
    sentence_one = derive_identity("script-sentence", "one")
    span = TextSpanReference(
        text_span_id=derive_identity("text-span", "one"),
        parent_sentence_reference=sentence_one,
        start_offset=0,
        end_offset=1,
        referenced_text="A",
        binding_classification=TextSpanBindingClassification.ATTRIBUTION,
        span_fingerprint=ZERO,
    )
    span = _seal(span, "span_fingerprint")
    attribution = AttributionRealization(
        attribution_realization_id="attribution:one",
        script_sentence_reference=sentence_one,
        approved_claim_reference="claim:one",
        source_reference="source:one",
        required_attribution_reference="requirement:one",
        text_span_reference=span,
        attribution_form=AttributionForm.DIRECT,
        attribution_preserved=True,
        attribution_fingerprint=ZERO,
    )
    invalid = attribution.model_copy(
        update={"script_sentence_reference": derive_identity("script-sentence", "two")}
    )
    invalid = _seal(invalid, "attribution_fingerprint")
    issue = next(
        item
        for item in validate_artifact(invalid)
        if item.code == "attribution-span-parent-mismatch"
    )
    assert issue.field_path == (
        "text_span_reference",
        "parent_sentence_reference",
    )


def test_partial_response_rejected_targets_are_disjoint_and_paired():
    values = {
        "provider_partial_response_id": derive_identity(
            "provider-partial-response", "one"
        ),
        "completed_target_references": ("beat:one",),
        "rejected_unit_references": ("unit:one",),
        "rejected_unit_target_references": ("beat:one",),
        "partial_reason": "reason:one",
        "recoverable": True,
        "partial_fingerprint": ZERO,
    }
    with pytest.raises(ValidationError, match="disjoint"):
        ProviderPartialResponse(**values)
    values["completed_target_references"] = ()
    values["rejected_unit_target_references"] = ()
    with pytest.raises(ValidationError, match="exactly one target"):
        ProviderPartialResponse(**values)


def test_partial_revision_may_omit_inspection_draft_but_success_may_not():
    values = {
        "revision_execution_result_id": derive_identity(
            "revision-execution-result", "one"
        ),
        "result_version": "1.0.0",
        "revision_request_reference": derive_identity("revision-request", "one"),
        "revision_request_fingerprint": ONE,
        "prior_draft_reference": "draft:one",
        "prior_draft_fingerprint": ONE,
        "readiness": "blocked",
        "result_fingerprint": ZERO,
    }
    partial = RevisionExecutionResult(
        **values,
        execution_status=RevisionExecutionStatus.PARTIAL,
        resulting_draft_disposition=RevisionResultDisposition.INSPECTION_ONLY,
    )
    assert partial.resulting_draft_reference is None
    with pytest.raises(ValidationError, match="requires a resulting draft"):
        RevisionExecutionResult(
            **values,
            execution_status=RevisionExecutionStatus.SUCCESS,
            resulting_draft_disposition=RevisionResultDisposition.REPLACEMENT,
        )


def test_system_regeneration_targets_are_bound_to_scope_snapshot():
    authority = _seal(
        RevisionAuthority(
            revision_authority_id="authority:system",
            authority_type=RevisionAuthorityType.SYSTEM,
            authority_reference="authority-source:system",
            authority_version="1.0.0",
            authorized_revision_types=(RevisionType.REGENERATION,),
            authority_fingerprint=ZERO,
        ),
        "authority_fingerprint",
    )
    original_targets = ("draft:one",)
    snapshot = _authority_inputs().model_copy(
        update={
            "target_scope_fingerprint": revision_target_scope_fingerprint(
                RevisionScope.COMPLETE_DRAFT, original_targets
            )
        }
    )
    with pytest.raises(ValidationError, match="target scope mismatch"):
        RevisionRequest(
            revision_request_id=derive_identity("revision-request", "scope"),
            prior_script_draft_reference="draft:one",
            prior_script_draft_fingerprint=ONE,
            revision_scope=RevisionScope.COMPLETE_DRAFT,
            target_references=("draft:two",),
            revision_type=RevisionType.REGENERATION,
            requested_change_reference="change:one",
            revision_reason_reference="reason:one",
            revision_authority=authority,
            preserved_constraint_references=("constraint:one",),
            immutable_upstream_references=("composition:one",),
            expected_readiness_impact="requires_editor_review",
            prior_authority_inputs=snapshot,
            requested_authority_inputs=snapshot,
            request_fingerprint=ZERO,
        )
