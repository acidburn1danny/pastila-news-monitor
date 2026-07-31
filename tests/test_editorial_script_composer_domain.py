"""Pure-domain tests for Scout Editor Module 2.9 Phase 1."""

import pytest
from pydantic import ValidationError

from pastila_scout.editor.script_composer import *

ZERO = "0" * 64
ONE = "1" * 64


def _seal(model, field):
    return model.model_copy(update={field: semantic_fingerprint(model)})


def _annotation(effect=DeliveryAnnotationSemanticEffect.SEMANTIC, value="pause:short"):
    annotation = DeliveryAnnotation(
        delivery_annotation_id=f"annotation:{effect.value}:{value}",
        target_text_reference="sentence:target",
        annotation_type=(
            DeliveryAnnotationType.PAUSE
            if effect == DeliveryAnnotationSemanticEffect.SEMANTIC
            else DeliveryAnnotationType.TELEPROMPTER_LINE_WRAP
        ),
        annotation_value_reference=value,
        source_guidance_references=("spoken:guidance",),
        semantic_effect=effect,
        annotation_fingerprint=ZERO,
    )
    return _seal(annotation, "annotation_fingerprint")


def _sentence(text="Școala a publicat raportul 😀.", *, request=ONE, annotations=()):
    sentence_id = script_sentence_identity(request, "segment:1", "beat:1", 1, 1)
    paragraph_id = script_paragraph_identity(request, "segment:1", "beat:1", 1)
    sentence = ScriptSentence(
        script_sentence_id=sentence_id,
        script_paragraph_reference=paragraph_id,
        sentence_position=1,
        text=text,
        sentence_kind=SentenceKind.FACTUAL,
        delivery_annotations=annotations,
        generation_trace_references=("trace:1",),
        sentence_fingerprint=ZERO,
    )
    return _seal(sentence, "sentence_fingerprint")


def _span(sentence, start, end, classification="evidence"):
    classification = (
        classification
        if classification in {item.value for item in TextSpanBindingClassification}
        else TextSpanBindingClassification.EVIDENCE
    )
    referenced = sentence.text[start:end]
    span_id = text_span_identity(
        sentence.script_sentence_id, start, end, classification, referenced
    )
    span = TextSpanReference(
        text_span_id=span_id,
        parent_sentence_reference=sentence.script_sentence_id,
        start_offset=start,
        end_offset=end,
        referenced_text=referenced,
        binding_classification=classification,
        span_fingerprint=ZERO,
    )
    return _seal(span, "span_fingerprint")


def _authority(kind=RevisionAuthorityType.EDITOR):
    allowed = tuple(
        sorted(revision_types_for_authority(kind), key=lambda item: item.value)
    )
    authority = RevisionAuthority(
        revision_authority_id=f"authority:{kind.value}",
        authority_type=kind,
        authority_reference=f"authority-source:{kind.value}",
        authority_version="1.0.0",
        authorized_revision_types=allowed,
        authority_fingerprint=ZERO,
    )
    return _seal(authority, "authority_fingerprint")


def _instruction():
    value = GenerationInstruction(
        generation_instruction_id="instruction:1",
        instruction_type=GenerationInstructionType.BEAT_REALIZATION,
        target_references=("beat:1",),
        authority_level=AuthorityLevel.COMPOSITION_PLAN,
        instruction_reference="instruction-source:1",
        required=True,
        source_rule_references=("rule:1",),
        instruction_fingerprint=ZERO,
    )
    return _seal(value, "instruction_fingerprint")


def _constraint():
    value = GenerationConstraint(
        generation_constraint_id="constraint:1",
        constraint_type="factual",
        target_references=("beat:1",),
        severity=ConstraintSeverity.BLOCKING,
        mandatory=True,
        constraint_reference="constraint-source:1",
        prohibited_outcomes=("unsupported-fact",),
        source_references=("policy:1",),
        constraint_fingerprint=ZERO,
    )
    return _seal(value, "constraint_fingerprint")


def _request():
    instruction = _instruction()
    constraint = _constraint()
    metadata = ProviderNeutralExecutionMetadata(
        execution_policy_reference="execution-policy:1",
        response_schema_reference="response-schema:1",
        capability_references=("capability:structured-output",),
        reproducibility_policy_reference="reproducibility-policy:1",
    )
    values = {
        "provider_generation_request_id": derive_identity(
            "provider-generation-request", "temporary"
        ),
        "request_version": "1.0.0",
        "target_episode_reference": "episode:1",
        "target_segment_references": ("segment:1",),
        "target_beat_references": ("beat:1",),
        "generation_profile_reference": "profile:1",
        "generation_profile_fingerprint": ONE,
        "composition_plan_reference": "composition:1",
        "composition_plan_fingerprint": ONE,
        "approved_claim_references": ("claim:1",),
        "source_span_references": ("source-span:1",),
        "generation_instruction_references": (instruction.generation_instruction_id,),
        "generation_instructions": (instruction,),
        "generation_constraint_references": (constraint.generation_constraint_id,),
        "generation_constraints": (constraint,),
        "authority_references": ("authority:1",),
        "output_schema_identity": "schema:1",
        "prompt_template_identity_reference": "prompt-template:1",
        "execution_policy_reference": "execution-policy:1",
        "provider_neutral_execution_metadata": metadata,
        "request_fingerprint": ZERO,
    }
    request = ProviderGenerationRequest(**values)
    request = request.model_copy(
        update={"provider_generation_request_id": provider_request_identity(request)}
    )
    return _seal(request, "request_fingerprint")


def _unit(request):
    unit_id = derive_identity(
        "provider-generated-unit",
        (request.request_fingerprint, "segment:1", "beat:1", 1, 1),
    )
    unit = ProviderGeneratedUnit(
        provider_generated_unit_id=unit_id,
        unit_kind=ProviderGeneratedUnitKind.SENTENCE,
        target_segment_reference="segment:1",
        target_beat_reference="beat:1",
        paragraph_ordinal=1,
        sentence_ordinal=1,
        text="Școala a publicat raportul.",
        source_instruction_references=("instruction:1",),
        unit_fingerprint=ZERO,
    )
    return _seal(unit, "unit_fingerprint")


def _response(request, *, status=ProviderExecutionStatus.SUCCESS):
    unit = _unit(request)
    execution = ProviderExecutionReference(
        provider_execution_reference_id="execution:1",
        provider="provider:test",
        model="model:test",
        prompt_template_id="prompt-template:1",
        prompt_template_version="1.0.0",
        output_schema_version="1",
        request_fingerprint=request.request_fingerprint,
        status=status,
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
        execution_status=status,
        structured_generated_units=(unit,),
        response_fingerprint=ZERO,
        validation_status=ProviderResponseValidationStatus.ACCEPTED,
    )
    response = response.model_copy(
        update={"provider_generation_response_id": provider_response_identity(response)}
    )
    return _seal(response, "response_fingerprint")


def test_reference_profile_is_frozen_complete_and_valid():
    profile = PASTILA_ACIDA_GENERATION_PROFILE
    assert profile.language == "ro"
    assert profile.preset_identity == "satirical_commentary"
    assert profile.audience_model_reference == "audience-model:pastila-acida-general"
    assert validate_artifact(profile) == ()
    with pytest.raises(ValidationError):
        profile.language = "en"


def test_generation_profile_rejects_unknown_provider_and_demographic_fields():
    values = PASTILA_ACIDA_GENERATION_PROFILE.model_dump()
    values["temperature"] = 0.5
    with pytest.raises(ValidationError):
        GenerationProfile(**values)
    values.pop("temperature")
    values["audience_age_range"] = "18-60"
    with pytest.raises(ValidationError):
        GenerationProfile(**values)


def test_profile_rejects_unknown_vocabulary_and_invalid_custom_value():
    values = PASTILA_ACIDA_GENERATION_PROFILE.model_dump()
    values["spoken_language_mode"] = "unknown"
    with pytest.raises(ValidationError):
        GenerationProfile(**values)
    values["spoken_language_mode"] = "custom:Invalid"
    with pytest.raises(ValidationError):
        GenerationProfile(**values)


def test_custom_profile_value_requires_authority_and_documentation():
    values = PASTILA_ACIDA_GENERATION_PROFILE.model_dump()
    values["spoken_language_mode"] = "custom:radio-natural"
    with pytest.raises(ValidationError, match="matching definition"):
        GenerationProfile(**values)
    values["custom_value_definitions"] = (
        CustomProfileValueDefinition(
            custom_value="custom:radio-natural",
            semantic_documentation_reference="profile-doc:radio-natural",
            authority_references=("authority:editor",),
            compatibility_version="1.0.0",
        ),
    )
    assert GenerationProfile(**values).spoken_language_mode == "custom:radio-natural"


def test_unknown_fields_and_top_level_mutation_are_rejected():
    with pytest.raises(ValidationError):
        ProviderNeutralExecutionMetadata(
            execution_policy_reference="policy:1",
            response_schema_reference="schema:1",
            reproducibility_policy_reference="repro:1",
            unknown=True,
        )
    metadata = ProviderNeutralExecutionMetadata(
        execution_policy_reference="policy:1",
        response_schema_reference="schema:1",
        reproducibility_policy_reference="repro:1",
    )
    with pytest.raises(ValidationError):
        metadata.capability_references = ("changed",)


def test_nested_collections_are_immutable_and_defaults_are_not_shared():
    first = ProviderNeutralExecutionMetadata(
        execution_policy_reference="policy:1",
        response_schema_reference="schema:1",
        reproducibility_policy_reference="repro:1",
    )
    second = ProviderNeutralExecutionMetadata(
        execution_policy_reference="policy:2",
        response_schema_reference="schema:2",
        reproducibility_policy_reference="repro:2",
    )
    assert isinstance(first.capability_references, tuple)
    changed = first.model_copy(update={"capability_references": ("capability:one",)})
    assert changed.capability_references == ("capability:one",)
    assert second.capability_references == ()


def test_canonical_serialization_normalizes_nested_order_and_unicode():
    composed = "s\u0326coala"
    precomposed = "școala"
    left = {"items": {"beta", "alpha"}, "nested": {"text": composed}}
    right = {"nested": {"text": precomposed}, "items": {"alpha", "beta"}}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert canonical_bytes(left).decode("utf-8").find("școala") >= 0


def test_canonical_serialization_rejects_runtime_objects():
    with pytest.raises(CanonicalSerializationError):
        canonical_json({"value": object()})


def test_identity_is_full_lowercase_sha256_and_deterministic():
    first = derive_identity("script-sentence", {"b": 2, "a": 1})
    second = derive_identity("script-sentence", {"a": 1, "b": 2})
    assert first == second
    assert first.startswith("scout:script-sentence:")
    assert len(first.rsplit(":", 1)[1]) == 64
    assert first == first.lower()


def test_meaningful_identity_seed_change_changes_identity():
    assert script_sentence_identity(
        ONE, "segment:1", "beat:1", 1, 1
    ) != script_sentence_identity(ONE, "segment:2", "beat:1", 1, 1)


def test_sentence_nfc_normalization_and_changed_wording_fingerprint():
    first = _sentence("s\u0326coala")
    equivalent = _sentence("școala")
    changed = _sentence("Școala")
    assert first.text == "școala"
    assert first.script_sentence_id == changed.script_sentence_id
    assert first.sentence_fingerprint == equivalent.sentence_fingerprint
    assert first.sentence_fingerprint != changed.sentence_fingerprint


def test_changed_parent_changes_sentence_identity():
    assert script_sentence_identity(
        ONE, "segment:1", "beat:1", 1, 1
    ) != script_sentence_identity(ONE, "segment:1", "beat:2", 1, 1)


def test_text_span_uses_code_points_for_romanian_and_emoji():
    sentence = _sentence()
    emoji_index = sentence.text.index("😀")
    span = _span(sentence, emoji_index, emoji_index + 1, "emoji")
    assert span.referenced_text == "😀"
    assert validate_text_span(span, sentence) == ()


def test_text_span_repeated_substrings_are_disambiguated_by_offsets():
    sentence = _sentence("test și iar test")
    first = _span(sentence, 0, 4)
    second = _span(sentence, 12, 16)
    assert first.referenced_text == second.referenced_text
    assert first.text_span_id != second.text_span_id


def test_text_span_rejects_zero_length_and_substring_mismatch():
    sentence = _sentence()
    with pytest.raises(ValidationError):
        TextSpanReference(
            text_span_id=derive_identity("text-span", "bad"),
            parent_sentence_reference=sentence.script_sentence_id,
            start_offset=1,
            end_offset=1,
            referenced_text="x",
            binding_classification="fact",
            span_fingerprint=ZERO,
        )
    span = _span(sentence, 0, 6).model_copy(update={"referenced_text": "greșit"})
    assert any(
        issue.code == "text-span-substring-mismatch"
        for issue in validate_text_span(span, sentence)
    )


def test_script_sentence_identity_validates_against_external_lineage():
    sentence = _sentence()
    assert (
        validate_script_unit_identity(
            sentence,
            request_fingerprint=ONE,
            composition_segment_reference="segment:1",
            composition_beat_reference="beat:1",
            paragraph_ordinal=1,
        )
        == ()
    )
    issues = validate_script_unit_identity(
        sentence,
        request_fingerprint=ONE,
        composition_segment_reference="segment:1",
        composition_beat_reference="beat:2",
        paragraph_ordinal=1,
    )
    assert {item.code for item in issues} == {"identity-mismatch"}


def test_text_span_wrong_parent_is_rejected():
    sentence = _sentence()
    span = _span(sentence, 0, 6).model_copy(
        update={
            "parent_sentence_reference": derive_identity("script-sentence", "other")
        }
    )
    assert any(
        issue.code == "text-span-parent-mismatch"
        for issue in validate_text_span(span, sentence)
    )


def test_nested_spans_allowed_and_crossing_spans_rejected():
    sentence = _sentence("abcdefghij")
    outer = _span(sentence, 0, 8, "outer")
    nested = _span(sentence, 2, 6, "nested")
    assert not any(
        issue.code == "crossing-text-spans"
        for issue in validate_text_span_collection((outer, nested), sentence)
    )
    crossing = _span(sentence, 4, 10, "crossing")
    assert any(
        issue.code == "crossing-text-spans"
        for issue in validate_text_span_collection((outer, crossing), sentence)
    )


def test_equivalent_spans_may_be_reused_by_distinct_bindings():
    sentence = _sentence("abcdefghij")
    first = _span(sentence, 0, 4, "fact")
    duplicate = first.model_copy(
        update={"text_span_id": derive_identity("text-span", "duplicate")}
    )
    assert not any(
        issue.code == "duplicate-equivalent-text-span"
        for issue in validate_text_span_collection((first, duplicate), sentence)
    )


def test_provider_request_identity_and_fingerprint_validate():
    request = _request()
    assert request.provider_generation_request_id == provider_request_identity(request)
    assert validate_artifact(request) == ()


def test_invalid_semantic_fingerprint_is_reported_structurally():
    request = _request().model_copy(update={"request_fingerprint": ZERO})
    assert any(
        issue.code == "fingerprint-mismatch" for issue in validate_artifact(request)
    )


def test_provider_response_lineage_and_fingerprint_validate():
    request = _request()
    response = _response(request)
    assert validate_provider_lineage(request, response) == ()


def test_provider_lineage_and_target_mismatches_are_structured():
    request = _request()
    response = _response(request)
    unit = response.structured_generated_units[0].model_copy(
        update={"target_beat_reference": "beat:unknown"}
    )
    changed = response.model_copy(
        update={
            "originating_request_fingerprint": ZERO,
            "structured_generated_units": (unit,),
        }
    )
    codes = {issue.code for issue in validate_provider_lineage(request, changed)}
    assert "provider-lineage-mismatch" in codes
    assert "provider-unit-target-mismatch" in codes


def test_empty_success_response_is_rejected_during_lineage_validation():
    request = _request()
    response = _response(request).model_copy(update={"structured_generated_units": ()})
    assert any(
        issue.code == "empty-success-response"
        for issue in validate_provider_lineage(request, response)
    )


def test_malformed_success_and_partial_response_overlap_are_rejected():
    request = _request()
    response = _response(request)
    with pytest.raises(ValidationError):
        ProviderGenerationResponse(
            **{
                **response.model_dump(),
                "failure_reason": ProviderFailureReason.TIMEOUT,
            }
        )
    with pytest.raises(ValidationError):
        ProviderPartialResponse(
            provider_partial_response_id=derive_identity(
                "provider-partial-response", "one"
            ),
            completed_target_references=("beat:1",),
            missing_mandatory_target_references=("beat:1",),
            partial_reason="partial:reason",
            recoverable=True,
            partial_fingerprint=ZERO,
        )


def test_unknown_provider_status_is_normalized():
    assert (
        normalize_provider_status("vendor-novel-status")
        == ProviderExecutionStatus.UNKNOWN
    )
    assert (
        normalize_provider_failure("vendor-error")
        == ProviderFailureReason.UNKNOWN_PROVIDER_FAILURE
    )


def test_revision_authority_matrix_and_system_limitations():
    system = _authority(RevisionAuthorityType.SYSTEM)
    assert RevisionType.REGENERATION in system.authorized_revision_types
    assert RevisionType.EDITORIAL_REVISION not in system.authorized_revision_types
    with pytest.raises(ValidationError):
        RevisionAuthority(
            revision_authority_id="authority:invalid",
            authority_type=RevisionAuthorityType.SYSTEM,
            authority_reference="authority-source:system",
            authority_version="1.0.0",
            authorized_revision_types=(RevisionType.EDITORIAL_REVISION,),
            authority_fingerprint=ZERO,
        )


def test_factual_revision_requires_updated_evidence():
    authority = _authority()
    authority_inputs = RevisionAuthorityInputSnapshot(
        **{name: ONE for name in RevisionAuthorityInputSnapshot.model_fields}
    )
    values = {
        "revision_request_id": derive_identity("revision-request", "temporary"),
        "prior_script_draft_reference": "draft:1",
        "prior_script_draft_fingerprint": ONE,
        "revision_scope": RevisionScope.SENTENCE,
        "target_references": ("sentence:1",),
        "revision_type": RevisionType.FACTUAL_CORRECTION,
        "requested_change_reference": "change:1",
        "revision_reason_reference": "reason:1",
        "revision_authority": authority,
        "preserved_constraint_references": ("constraint:1",),
        "immutable_upstream_references": ("composition:1",),
        "expected_readiness_impact": DraftReadiness.REQUIRES_EDITOR_REVIEW,
        "prior_authority_inputs": authority_inputs,
        "requested_authority_inputs": authority_inputs,
        "request_fingerprint": ZERO,
    }
    with pytest.raises(ValidationError, match="approved evidence"):
        RevisionRequest(**values)


def test_revision_result_sets_must_be_disjoint():
    lineage = TextualUnitLineage(
        textual_unit_reference="sentence:1",
        semantic_fingerprint=ONE,
        lineage_fingerprint=ZERO,
    )
    lineage = _seal(lineage, "lineage_fingerprint")
    with pytest.raises(ValidationError, match="disjoint"):
        RevisionExecutionResult(
            revision_execution_result_id=derive_identity(
                "revision-execution-result", "one"
            ),
            result_version="1.0.0",
            revision_request_reference=derive_identity("revision-request", "one"),
            revision_request_fingerprint=ONE,
            prior_draft_reference="draft:1",
            prior_draft_fingerprint=ONE,
            resulting_draft_reference="draft:2",
            resulting_draft_fingerprint=ONE,
            changed_textual_units=(lineage,),
            preserved_textual_units=(lineage,),
            readiness=DraftReadiness.BLOCKED,
            execution_status=RevisionExecutionStatus.SUCCESS,
            resulting_draft_disposition=RevisionResultDisposition.REPLACEMENT,
            result_fingerprint=ZERO,
        )


def test_failed_revision_cannot_expose_result_draft():
    with pytest.raises(ValidationError):
        RevisionExecutionResult(
            revision_execution_result_id=derive_identity(
                "revision-execution-result", "one"
            ),
            result_version="1.0.0",
            revision_request_reference=derive_identity("revision-request", "one"),
            revision_request_fingerprint=ONE,
            prior_draft_reference="draft:1",
            prior_draft_fingerprint=ONE,
            resulting_draft_reference="draft:2",
            resulting_draft_fingerprint=ONE,
            readiness=DraftReadiness.BLOCKED,
            execution_status=RevisionExecutionStatus.FAILED,
            result_fingerprint=ZERO,
        )


def test_semantic_delivery_annotation_changes_sentence_fingerprint():
    plain = _sentence()
    semantic = _sentence(annotations=(_annotation(),))
    assert plain.sentence_fingerprint != semantic.sentence_fingerprint


def test_presentation_annotation_is_excluded_from_sentence_fingerprint():
    plain = _sentence()
    presentation = _sentence(
        annotations=(
            _annotation(
                DeliveryAnnotationSemanticEffect.PRESENTATION_ONLY,
                "wrap:after-word",
            ),
        )
    )
    assert plain.sentence_fingerprint == presentation.sentence_fingerprint


def test_diagnostic_fields_are_excluded_from_semantic_fingerprint():
    payload = {
        "text": "Conținut",
        "validation_findings": ({"message": "first"},),
        "draft_readiness": "blocked",
    }
    changed = {
        "text": "Conținut",
        "validation_findings": ({"message": "different"},),
        "draft_readiness": "ready_for_editorial_review",
    }
    assert semantic_fingerprint(payload) == semantic_fingerprint(changed)
    changed["semantic_constraint"] = "constraint:1"
    assert semantic_fingerprint(payload) != semantic_fingerprint(changed)


def test_provider_execution_and_usage_are_excluded_from_script_semantics():
    left = {
        "text": "Conținut",
        "provider_execution_reference": {
            "provider": "provider:a",
            "model": "model:a",
            "input_tokens": 10,
            "output_tokens": 5,
            "latency_ms": 100,
        },
    }
    right = {
        "text": "Conținut",
        "provider_execution_reference": {
            "provider": "provider:b",
            "model": "model:b",
            "input_tokens": 999,
            "output_tokens": 999,
            "latency_ms": 9999,
        },
    }
    assert semantic_fingerprint(left) == semantic_fingerprint(right)


def test_policy_detects_equal_specificity_satire_conflict():
    def permission(identifier, state):
        value = SatirePermission(
            satire_permission_id=identifier,
            target_reference="segment:1",
            target_scope=SatireScope.SEGMENT,
            permission_state=state,
            authority_references=("authority:1",),
            permission_fingerprint=ZERO,
        )
        return _seal(value, "permission_fingerprint")

    policy = ResolvedGenerationPolicySnapshot(
        resolved_generation_policy_id="policy:resolved",
        policy_version="1.0.0",
        source_policy_reference="policy:source",
        source_policy_fingerprint=ONE,
        satire_permissions=(
            permission("permission:1", SatirePermissionState.PERMITTED),
            permission("permission:2", SatirePermissionState.PROHIBITED),
        ),
        authority_references=("authority:1",),
        policy_fingerprint=ZERO,
    )
    assert any(
        issue.code == "contradictory-satire-permission"
        for issue in validate_satire_permissions(policy)
    )


def test_module_has_no_provider_sdk_or_execution_entrypoint():
    import pastila_scout.editor.script_composer as package

    assert not hasattr(package, "OpenAI")
    assert not hasattr(package, "execute_generation")
    assert not hasattr(package, "EpisodeProfile")
    assert not hasattr(package, "PromptBuilder")
