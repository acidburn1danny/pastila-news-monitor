"""Final freeze-coverage completion for Phase 6.2 provider mapping."""

import json
from dataclasses import asdict

import pytest
from pydantic import ValidationError
from test_editorial_script_composer_provider_mapping import (
    UPSTREAM,
    _context,
    _descriptor,
    _generic,
    _openai,
    _replace_message,
    _replace_request,
    _seal,
    _seal_generic,
    _seal_message,
    _seal_openai_plan,
    _seal_request,
)

from pastila_scout.editor.script_composer import (
    DomainValidationError,
    OpenAIProviderRequestPlan,
    ProviderMappingValidationContext,
    ProviderRequestPlanDescriptor,
    build_draft_provider_request_plan,
    build_openai_provider_request_plan,
    derive_draft_llm_execution_plan_fingerprint,
    derive_draft_llm_execution_plan_identity,
    derive_provider_request_plan_descriptor_fingerprint,
    derive_provider_request_plan_descriptor_identity,
    validate_draft_provider_request_plan,
    validate_openai_provider_request_plan,
)


def _codes(plan, context):
    return {item.code for item in validate_openai_provider_request_plan(plan, context)}


def _generic_codes(plan, context):
    return {item.code for item in validate_draft_provider_request_plan(plan, context)}


def _empty_generic(*, purpose=None):
    _, _, rendered, rendered_context = UPSTREAM["FREEZE"]["_empty_authority"](
        purpose=purpose
    )
    execution_context = UPSTREAM["_context"](rendered, rendered_context)
    execution = UPSTREAM["build_draft_llm_execution_plan"](rendered, execution_context)
    descriptor = _descriptor()
    context = _context(execution, execution_context, descriptor)
    return build_draft_provider_request_plan(execution, descriptor, context), context


_VERSION_ATTACKS = (
    pytest.param("Phase-6.2-openai-v1", id="case"),
    pytest.param(" phase-6.2-openai-v1", id="leading-whitespace"),
    pytest.param("phase-6.2-openai-v1 ", id="trailing-whitespace"),
    pytest.param("phase-6.2 openai-v1", id="embedded-whitespace"),
    pytest.param("phase-6.2\t-openai-v1", id="tab"),
    pytest.param("phase-6.2\nopenai-v1", id="newline"),
    pytest.param("phase-6.2-openai-v2", id="alternate-version"),
    pytest.param("https://version.invalid/v1", id="url"),
    pytest.param("https://version.invalid/v1?token=x", id="url-query"),
    pytest.param("https://version.invalid/v1#private", id="url-fragment"),
    pytest.param(r"C:\private\version.txt", id="windows-path"),
    pytest.param("/private/version.txt", id="posix-path"),
    pytest.param("v" * 500, id="oversized"),
    pytest.param("phase-6.2-оpenai-v1", id="unicode-confusable"),
    pytest.param("", id="empty"),
)


@pytest.mark.parametrize("version", _VERSION_ATTACKS)
def test_mapping_contract_version_attack_matrix(version):
    payload = _descriptor().model_dump(mode="python")
    payload["mapping_contract_version"] = version
    with pytest.raises(ValidationError):
        ProviderRequestPlanDescriptor.model_validate(payload)


def test_generic_descriptor_lineage_mismatch_is_rejected():
    plan, context = _generic()
    descriptor = _seal(
        plan.provider_descriptor.model_copy(
            update={
                "provider_descriptor_reference": "provider-mapping-descriptor:foreign"
            }
        ),
        derive_provider_request_plan_descriptor_identity,
        derive_provider_request_plan_descriptor_fingerprint,
    )
    changed = _seal_generic(plan.model_copy(update={"provider_descriptor": descriptor}))
    assert "provider-mapping-unknown-provider-descriptor" in _generic_codes(
        changed, context
    )


def test_generic_execution_plan_lineage_mismatch_is_rejected():
    plan, context = _generic()
    changed = _seal_generic(
        plan.model_copy(update={"execution_plan_identity": plan.identity})
    )
    assert "provider-mapping-unknown-execution-plan" in _generic_codes(changed, context)


def test_generic_draft_lineage_mismatch_is_rejected():
    plan, context = _generic()
    changed = _seal_generic(
        plan.model_copy(update={"draft_reference": plan.draft_reference + "-foreign"})
    )
    assert "provider-mapping-generic-draft-reference-mismatch" in _generic_codes(
        changed, context
    )


@pytest.mark.parametrize(
    ("field", "code"),
    (
        (
            "provider_plan_reference",
            "provider-mapping-generic-provider-plan-reference-mismatch",
        ),
        (
            "provider_plan_identity",
            "provider-mapping-generic-provider-plan-identity-mismatch",
        ),
        (
            "provider_plan_fingerprint",
            "provider-mapping-generic-provider-plan-fingerprint-mismatch",
        ),
    ),
)
def test_generic_provider_plan_seal_mismatches_are_rejected(field, code):
    plan, context = _generic()
    if field.endswith("identity"):
        original = getattr(plan, field)
        value = original[:-1] + ("e" if original.endswith("f") else "f")
    elif field.endswith("fingerprint"):
        value = "f" * 64
    else:
        value = "openai-request-plan:foreign"
    changed = _seal_generic(plan.model_copy(update={field: value}))
    assert code in _generic_codes(changed, context)


def test_generic_foreign_valid_openai_plan_is_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    changed = _seal_generic(
        plan.model_copy(update={"openai_request_plan": foreign.openai_request_plan})
    )
    assert "provider-mapping-generic-openai-request-plan-mismatch" in _generic_codes(
        changed, context
    )


def test_generic_wrapper_for_another_valid_execution_plan_is_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    changed = _seal_generic(
        plan.model_copy(
            update={
                "execution_plan_reference": foreign.execution_plan_reference,
                "execution_plan_identity": foreign.execution_plan_identity,
                "execution_plan_fingerprint": foreign.execution_plan_fingerprint,
            }
        )
    )
    assert "provider-mapping-unknown-execution-plan" in _generic_codes(changed, context)


def test_another_valid_descriptor_collapses_to_the_same_authority():
    first = _descriptor()
    second = _descriptor()
    assert first == second
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(first, second),
        )
    assert "provider-mapping-duplicate-provider_descriptors-identity" in str(
        caught.value
    )


def test_generic_correctly_sealed_foreign_concrete_artifacts_are_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    changed = _seal_generic(
        plan.model_copy(
            update={
                "provider_plan_reference": foreign.provider_plan_reference,
                "provider_plan_identity": foreign.provider_plan_identity,
                "provider_plan_fingerprint": foreign.provider_plan_fingerprint,
                "openai_request_plan": foreign.openai_request_plan,
            }
        )
    )
    assert _generic_codes(changed, context)


def test_true_foreign_valid_empty_execution_lineage_is_rejected():
    plan, context = _empty_generic(purpose="primary-empty-authority")
    foreign, foreign_context = _empty_generic(purpose="foreign-empty-authority")
    assert validate_draft_provider_request_plan(plan, context) == ()
    assert validate_draft_provider_request_plan(foreign, foreign_context) == ()
    assert plan.openai_request_plan.requests == ()
    assert foreign.openai_request_plan.requests == ()
    assert plan.execution_plan_identity != foreign.execution_plan_identity

    changed = _seal_generic(
        plan.model_copy(
            update={
                "provider_plan_reference": foreign.provider_plan_reference,
                "provider_plan_identity": foreign.provider_plan_identity,
                "provider_plan_fingerprint": foreign.provider_plan_fingerprint,
                "openai_request_plan": foreign.openai_request_plan,
            }
        )
    )
    codes = _generic_codes(changed, context)
    assert "provider-mapping-generic-openai-request-plan-mismatch" in codes
    assert "provider-mapping-unknown-execution-plan" in codes


def test_foreign_identity_derived_provider_descriptor_reference_is_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    descriptor = _seal(
        plan.provider_descriptor.model_copy(
            update={
                "provider_descriptor_reference": (
                    "provider-mapping-descriptor:openai:"
                    f"{foreign.execution_plan_identity}"
                )
            }
        ),
        derive_provider_request_plan_descriptor_identity,
        derive_provider_request_plan_descriptor_fingerprint,
    )
    changed = _seal_generic(plan.model_copy(update={"provider_descriptor": descriptor}))
    assert "provider-mapping-noncanonical-descriptor-reference" in _generic_codes(
        changed, context
    )


def test_foreign_identity_derived_generic_provider_plan_reference_is_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    changed = _seal_generic(
        plan.model_copy(
            update={
                "provider_request_plan_reference": (
                    f"provider-request-plan:openai:{foreign.execution_plan_identity}"
                )
            }
        )
    )
    assert (
        "provider-mapping-generic-provider-request-plan-reference-mismatch"
        in _generic_codes(changed, context)
    )


def test_foreign_identity_derived_openai_provider_plan_reference_is_rejected():
    plan, context = _generic(False)
    foreign, _ = _generic(True)
    changed_openai = _seal_openai_plan(
        plan.openai_request_plan.model_copy(
            update={
                "openai_request_plan_reference": (
                    f"openai-request-plan:{foreign.execution_plan_identity}"
                )
            }
        )
    )
    changed = _seal_generic(
        plan.model_copy(update={"openai_request_plan": changed_openai})
    )
    assert (
        "provider-mapping-openai-plan-openai-request-plan-reference-mismatch"
        in _generic_codes(changed, context)
    )


def test_foreign_identity_derived_openai_request_reference_is_rejected():
    plan, context = _openai(False)
    foreign, _ = _openai(True)
    changed_request = _seal_request(
        plan.requests[0].model_copy(
            update={
                "openai_request_reference": (
                    "openai-request:"
                    f"{foreign.requests[0].execution_request_identity}"
                )
            }
        )
    )
    assert (
        "provider-mapping-openai-request-openai-request-reference-mismatch"
        in _codes(_replace_request(plan, 0, changed_request), context)
    )


def test_foreign_identity_derived_openai_message_reference_is_rejected():
    plan, context = _openai(False)
    foreign, _ = _openai(True)
    changed_message = _seal_message(
        plan.requests[0]
        .messages[0]
        .model_copy(
            update={
                "openai_message_reference": (
                    "openai-message:"
                    f"{foreign.requests[0].messages[0].execution_message_identity}"
                )
            }
        )
    )
    changed = _replace_message(plan, 0, 0, changed_message)
    assert (
        "provider-mapping-openai-message-openai-message-reference-mismatch"
        in _codes(changed, context)
    )


def test_generic_correctly_resealed_execution_lineage_mismatch_is_rejected():
    test_generic_execution_plan_lineage_mismatch_is_rejected()


def test_generic_correctly_resealed_draft_lineage_mismatch_is_rejected():
    test_generic_draft_lineage_mismatch_is_rejected()


def test_generic_correctly_resealed_descriptor_lineage_mismatch_is_rejected():
    test_generic_descriptor_lineage_mismatch_is_rejected()


def _descriptor_pair(*, duplicate):
    first = _descriptor()
    if duplicate == "identity":
        second = first.model_copy(
            update={
                "provider_descriptor_reference": "provider-mapping-descriptor:foreign"
            }
        )
    elif duplicate == "reference":
        second = first.model_copy(
            update={
                "identity": first.identity[:-1]
                + ("e" if first.identity.endswith("f") else "f")
            }
        )
    else:
        second = first.model_copy(
            update={
                "identity": first.identity[:-1]
                + ("e" if first.identity.endswith("f") else "f"),
                "provider_descriptor_reference": "provider-mapping-descriptor:foreign",
            }
        )
    return first, second


def test_duplicate_descriptor_reference_is_rejected():
    first, second = _descriptor_pair(duplicate="reference")
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(first, second),
        )
    assert "provider-mapping-duplicate-provider_descriptors-reference" in str(
        caught.value
    )


def test_duplicate_descriptor_identity_is_rejected():
    first, second = _descriptor_pair(duplicate="identity")
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(first, second),
        )
    assert "provider-mapping-duplicate-provider_descriptors-identity" in str(
        caught.value
    )


def test_duplicate_provider_identifier_is_rejected():
    first, second = _descriptor_pair(duplicate="provider")
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(first, second),
        )
    assert "provider-mapping-duplicate-provider" in str(caught.value)


def test_duplicate_mapping_version_collapses_with_duplicate_provider():
    first, second = _descriptor_pair(duplicate="version")
    assert first.provider == second.provider == "openai"
    assert first.mapping_contract_version == second.mapping_contract_version
    with pytest.raises(ValidationError) as caught:
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(first, second),
        )
    assert "provider-mapping-duplicate-provider" in str(caught.value)


def test_complete_repeated_descriptor_is_rejected_independently():
    descriptor = _descriptor()
    with pytest.raises(ValidationError):
        ProviderMappingValidationContext(
            execution_plans=_context().execution_plans,
            execution_validation_context=_context().execution_validation_context,
            provider_descriptors=(descriptor, descriptor),
        )


@pytest.mark.parametrize("index", (0, 1, 2), ids=("first", "middle", "last"))
def test_provider_request_positional_omissions_are_rejected(index):
    plan, context = _openai(False)
    changed = _seal_openai_plan(
        plan.model_copy(
            update={"requests": plan.requests[:index] + plan.requests[index + 1 :]}
        )
    )
    assert "provider-mapping-missing-request" in _codes(changed, context)


def test_unique_extra_provider_request_is_rejected():
    plan, context = _openai(False)
    foreign, _ = _openai(True)
    changed = _seal_openai_plan(
        plan.model_copy(update={"requests": plan.requests + (foreign.requests[0],)})
    )
    assert "provider-mapping-extra-request" in _codes(changed, context)


def test_duplicate_provider_request_is_rejected():
    plan, context = _openai(False)
    changed = _seal_openai_plan(
        plan.model_copy(update={"requests": plan.requests + (plan.requests[0],)})
    )
    assert any(
        code.startswith("provider-mapping-duplicate-")
        for code in _codes(changed, context)
    )


def test_foreign_valid_provider_request_is_rejected():
    test_unique_extra_provider_request_is_rejected()


def test_nonempty_provider_projection_against_empty_authority_is_rejected():
    empty, context = _empty_generic()
    nonempty, _ = _generic()
    changed_openai = _seal_openai_plan(
        empty.openai_request_plan.model_copy(
            update={"requests": (nonempty.openai_request_plan.requests[0],)}
        )
    )
    changed = _seal_generic(
        empty.model_copy(update={"openai_request_plan": changed_openai})
    )
    assert _generic_codes(changed, context)


@pytest.mark.parametrize("index", (0, 1, 2), ids=("first", "middle", "last"))
def test_provider_message_positional_omissions_are_rejected(index):
    plan, context = _openai(False)
    request = plan.requests[0]
    changed_request = _seal_request(
        request.model_copy(
            update={
                "messages": request.messages[:index] + request.messages[index + 1 :]
            }
        )
    )
    assert "provider-mapping-missing-message" in _codes(
        _replace_request(plan, 0, changed_request), context
    )


def test_unique_extra_provider_message_is_rejected():
    plan, context = _openai(False)
    foreign, _ = _openai(True)
    request = plan.requests[0]
    changed_request = _seal_request(
        request.model_copy(
            update={"messages": request.messages + (foreign.requests[0].messages[0],)}
        )
    )
    assert "provider-mapping-extra-message" in _codes(
        _replace_request(plan, 0, changed_request), context
    )


def test_duplicate_provider_message_is_rejected():
    plan, context = _openai(False)
    request = plan.requests[0]
    changed_request = _seal_request(
        request.model_copy(
            update={"messages": request.messages + (request.messages[0],)}
        )
    )
    assert any(
        code.startswith("provider-mapping-duplicate-")
        for code in _codes(_replace_request(plan, 0, changed_request), context)
    )


def test_foreign_valid_provider_message_is_rejected():
    test_unique_extra_provider_message_is_rejected()


def test_same_plan_foreign_provider_message_is_rejected():
    plan, context = _openai(False)
    request = plan.requests[0]
    changed_request = _seal_request(
        request.model_copy(
            update={"messages": request.messages + (plan.requests[1].messages[0],)}
        )
    )
    assert "provider-mapping-extra-message" in _codes(
        _replace_request(plan, 0, changed_request), context
    )


@pytest.mark.parametrize(
    "order",
    ((1, 0, 2), (2, 1, 0), (0, 2, 1)),
    ids=("swapped", "reversed", "partial"),
)
def test_provider_request_ordering_matrix(order):
    plan, context = _openai(False)
    changed = _seal_openai_plan(
        plan.model_copy(
            update={"requests": tuple(plan.requests[index] for index in order)}
        )
    )
    assert "provider-mapping-invalid-request-order" in _codes(changed, context)


def test_corrected_request_ordinal_does_not_legitimize_reorder():
    plan, context = _openai(False)
    requests = tuple(
        _seal_request(item.model_copy(update={"request_ordinal": index}))
        for index, item in enumerate(reversed(plan.requests))
    )
    changed = _seal_openai_plan(plan.model_copy(update={"requests": requests}))
    assert "provider-mapping-invalid-request-order" in _codes(changed, context)


@pytest.mark.parametrize(
    "order",
    ((1, 0, 2), (2, 1, 0), (0, 2, 1)),
    ids=("swapped", "reversed", "partial"),
)
def test_provider_message_ordering_matrix(order):
    plan, context = _openai(False)
    request = plan.requests[0]
    changed_request = _seal_request(
        request.model_copy(
            update={"messages": tuple(request.messages[index] for index in order)}
        )
    )
    assert "provider-mapping-invalid-message-order" in _codes(
        _replace_request(plan, 0, changed_request), context
    )


def test_corrected_message_ordinal_does_not_legitimize_reorder():
    plan, context = _openai(False)
    request = plan.requests[0]
    messages = tuple(
        _seal_message(item.model_copy(update={"ordinal": index}))
        for index, item in enumerate(reversed(request.messages))
    )
    changed_request = _seal_request(request.model_copy(update={"messages": messages}))
    assert "provider-mapping-invalid-message-order" in _codes(
        _replace_request(plan, 0, changed_request), context
    )


def test_canonical_empty_valid_tuple_and_typed_generic_wrapper():
    plan, context = _empty_generic()
    assert plan.openai_request_plan.requests == ()
    assert validate_draft_provider_request_plan(plan, context) == ()


def test_canonical_empty_mutable_empty_reconstruction():
    plan, _ = _empty_generic()
    payload = plan.openai_request_plan.model_dump(mode="python")
    payload["requests"] = []
    assert OpenAIProviderRequestPlan.model_validate(payload).requests == ()


def test_canonical_empty_null_is_invalid():
    plan, _ = _empty_generic()
    with pytest.raises(ValidationError):
        OpenAIProviderRequestPlan.model_validate(
            {**plan.openai_request_plan.model_dump(), "requests": None}
        )


def test_canonical_empty_placeholder_request_is_rejected():
    test_nonempty_provider_projection_against_empty_authority_is_rejected()


def test_canonical_empty_placeholder_message_is_rejected():
    empty, context = _empty_generic()
    nonempty, _ = _generic()
    request = nonempty.openai_request_plan.requests[0]
    request = _seal_request(
        request.model_copy(update={"messages": (request.messages[0],)})
    )
    changed_openai = _seal_openai_plan(
        empty.openai_request_plan.model_copy(update={"requests": (request,)})
    )
    assert _codes(changed_openai, context)


@pytest.mark.parametrize(
    "case",
    (
        "wrong-descriptor",
        "wrong-descriptor-seals",
        "wrong-execution-lineage",
        "wrong-draft-lineage",
        "wrong-generic-reference",
        "wrong-openai-reference",
        "wrong-generic-identity",
        "wrong-generic-fingerprint",
        "wrong-openai-identity",
        "wrong-openai-fingerprint",
        "generic-concrete-mismatch",
        "nonempty-provider-projection",
    ),
)
def test_canonical_empty_adversarial_matrix(case):
    plan, context = _empty_generic()
    openai = plan.openai_request_plan
    if case == "wrong-descriptor":
        descriptor = _seal(
            plan.provider_descriptor.model_copy(
                update={
                    "provider_descriptor_reference": "provider-mapping-descriptor:foreign"
                }
            ),
            derive_provider_request_plan_descriptor_identity,
            derive_provider_request_plan_descriptor_fingerprint,
        )
        changed = _seal_generic(
            plan.model_copy(update={"provider_descriptor": descriptor})
        )
    elif case == "wrong-descriptor-seals":
        changed = _seal_generic(
            plan.model_copy(
                update={
                    "provider_descriptor": plan.provider_descriptor.model_copy(
                        update={"fingerprint": "f" * 64}
                    )
                }
            )
        )
    elif case == "wrong-execution-lineage":
        changed = _seal_generic(
            plan.model_copy(update={"execution_plan_identity": plan.identity})
        )
    elif case == "wrong-draft-lineage":
        changed = _seal_generic(
            plan.model_copy(update={"draft_reference": plan.draft_reference + "-wrong"})
        )
    elif case == "wrong-generic-reference":
        changed = _seal_generic(
            plan.model_copy(
                update={
                    "provider_request_plan_reference": "provider-request-plan:openai:wrong"
                }
            )
        )
    elif case == "wrong-openai-reference":
        changed_openai = _seal_openai_plan(
            openai.model_copy(
                update={"openai_request_plan_reference": "openai-request-plan:wrong"}
            )
        )
        changed = _seal_generic(
            plan.model_copy(update={"openai_request_plan": changed_openai})
        )
    elif case == "wrong-generic-identity":
        changed = plan.model_copy(update={"identity": plan.identity[:-1] + "e"})
    elif case == "wrong-generic-fingerprint":
        changed = plan.model_copy(update={"fingerprint": "f" * 64})
    elif case == "wrong-openai-identity":
        changed = _seal_generic(
            plan.model_copy(
                update={
                    "openai_request_plan": openai.model_copy(
                        update={"identity": openai.identity[:-1] + "e"}
                    )
                }
            )
        )
    elif case == "wrong-openai-fingerprint":
        changed = _seal_generic(
            plan.model_copy(
                update={
                    "openai_request_plan": openai.model_copy(
                        update={"fingerprint": "f" * 64}
                    )
                }
            )
        )
    else:
        nonempty, _ = _generic()
        changed = _seal_generic(
            plan.model_copy(
                update={"openai_request_plan": nonempty.openai_request_plan}
            )
        )
    assert _generic_codes(changed, context)


@pytest.mark.parametrize(
    "mutation",
    (
        "stale-plan-identity",
        "stale-plan-fingerprint",
        "stale-request-identity",
        "stale-request-fingerprint",
        "stale-message-identity",
        "stale-message-fingerprint",
        "noncanonical-reference",
        "foreign-valid-artifact",
        "duplicate-requests",
        "duplicate-messages",
        "reordered-requests",
        "reordered-messages",
        "missing-request",
        "extra-request",
        "missing-message",
        "extra-message",
        "malformed-context",
    ),
)
def test_complete_malformed_phase_6_1_authority_matrix(mutation):
    plan, context = _generic(False)
    source = context.execution_plans[0]
    requests = source.execution_requests
    if mutation == "stale-plan-identity":
        changed = source.model_copy(update={"identity": source.identity[:-1] + "e"})
    elif mutation == "stale-plan-fingerprint":
        changed = source.model_copy(update={"fingerprint": "f" * 64})
    elif mutation == "noncanonical-reference":
        changed = source.model_copy(
            update={"execution_plan_reference": "llm-execution-plan:wrong"}
        )
    elif mutation in {"missing-request", "reordered-requests"}:
        changed = source.model_copy(
            update={
                "execution_requests": (
                    requests[1:]
                    if mutation == "missing-request"
                    else tuple(reversed(requests))
                )
            }
        )
    elif mutation in {"duplicate-requests", "extra-request", "foreign-valid-artifact"}:
        foreign = UPSTREAM["_plan"]()
        extra = (
            requests[0]
            if mutation == "duplicate-requests"
            else foreign.execution_requests[0]
        )
        changed = source.model_copy(update={"execution_requests": requests + (extra,)})
    elif mutation == "malformed-context":
        malformed = context.model_copy(
            update={"execution_validation_context": object()}
        )
        with pytest.raises(DomainValidationError):
            build_openai_provider_request_plan(
                source, plan.provider_descriptor, malformed
            )
        return
    else:
        request = requests[0]
        messages = request.execution_messages
        if mutation == "stale-request-identity":
            request = request.model_copy(
                update={"identity": request.identity[:-1] + "e"}
            )
        elif mutation == "stale-request-fingerprint":
            request = request.model_copy(update={"fingerprint": "f" * 64})
        elif mutation == "stale-message-identity":
            message = messages[0].model_copy(
                update={"identity": messages[0].identity[:-1] + "e"}
            )
            request = request.model_copy(
                update={"execution_messages": (message,) + messages[1:]}
            )
        elif mutation == "stale-message-fingerprint":
            message = messages[0].model_copy(update={"fingerprint": "f" * 64})
            request = request.model_copy(
                update={"execution_messages": (message,) + messages[1:]}
            )
        elif mutation == "reordered-messages":
            request = request.model_copy(
                update={"execution_messages": tuple(reversed(messages))}
            )
        elif mutation == "missing-message":
            request = request.model_copy(update={"execution_messages": messages[1:]})
        elif mutation == "duplicate-messages":
            request = request.model_copy(
                update={"execution_messages": messages + (messages[0],)}
            )
        else:
            foreign = UPSTREAM["_plan"]().execution_requests[0].execution_messages[0]
            request = request.model_copy(
                update={"execution_messages": messages + (foreign,)}
            )
        changed = source.model_copy(
            update={"execution_requests": (request,) + requests[1:]}
        )
    malformed_context = context.model_copy(update={"execution_plans": (changed,)})
    with pytest.raises(DomainValidationError):
        build_openai_provider_request_plan(
            changed, plan.provider_descriptor, malformed_context
        )


def test_correctly_resealed_forged_execution_plan_identity_is_rejected():
    plan, context = _generic(False)
    source = context.execution_plans[0]
    forged_identity = source.identity[:-1] + (
        "e" if source.identity.endswith("f") else "f"
    )
    changed = source.model_copy(update={"identity": forged_identity})
    changed = changed.model_copy(
        update={"fingerprint": derive_draft_llm_execution_plan_fingerprint(changed)}
    )
    malformed_context = context.model_copy(update={"execution_plans": (changed,)})

    with pytest.raises(DomainValidationError) as caught:
        build_openai_provider_request_plan(
            changed, plan.provider_descriptor, malformed_context
        )

    assert "llm-execution-invalid-plan-identity" in {
        issue.code for issue in caught.value.issues
    }


def test_correctly_resealed_forged_execution_plan_fingerprint_is_rejected():
    plan, context = _generic(False)
    source = context.execution_plans[0]
    changed = source.model_copy(
        update={"draft_reference": source.draft_reference + "-forged"}
    )
    changed = changed.model_copy(
        update={"identity": derive_draft_llm_execution_plan_identity(changed)}
    )
    valid_fingerprint = derive_draft_llm_execution_plan_fingerprint(changed)
    forged_fingerprint = valid_fingerprint[:-1] + (
        "e" if valid_fingerprint.endswith("f") else "f"
    )
    changed = changed.model_copy(update={"fingerprint": forged_fingerprint})
    malformed_context = context.model_copy(update={"execution_plans": (changed,)})

    with pytest.raises(DomainValidationError) as caught:
        build_openai_provider_request_plan(
            changed, plan.provider_descriptor, malformed_context
        )

    assert "llm-execution-invalid-plan-fingerprint" in {
        issue.code for issue in caught.value.issues
    }


_HOSTILE_REFERENCES = (
    "https://user:secret@example.invalid/item",
    "item?token=private",
    "item#private",
    r"C:\private\item.json",
    "/private/item.json",
    "OPENAI_API_KEY=private",
    "control\x00value",
    "line\nbreak",
    "Traceback private stack",
    "Exception private error",
    "object:0x7ffdeadbeef",
    "x" * 500,
    "cоnfusable",
)


@pytest.mark.parametrize("hostile", _HOSTILE_REFERENCES)
def test_complete_hostile_diagnostic_objects_are_safe(hostile):
    plan, context = _openai()
    changed = _seal_openai_plan(
        plan.model_copy(update={"openai_request_plan_reference": hostile})
    )
    first = validate_openai_provider_request_plan(changed, context)
    second = validate_openai_provider_request_plan(changed, context)
    assert first == second
    payload = json.dumps(
        [asdict(item) for item in first],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    assert hostile not in payload
    assert len(payload) < 5000


def test_complete_same_process_diagnostic_equality():
    plan, context = _openai(False)
    changed = _seal_openai_plan(
        plan.model_copy(update={"requests": plan.requests + (plan.requests[0],)})
    )
    first = validate_openai_provider_request_plan(changed, context)
    second = validate_openai_provider_request_plan(changed, context)
    assert len(first) == len(second)
    assert first == second
    assert tuple(item.code for item in first) == tuple(item.code for item in second)
    assert tuple(item.field_reference for item in first) == tuple(
        item.field_reference for item in second
    )
    assert tuple(item.message_key for item in first) == tuple(
        item.message_key for item in second
    )
    assert tuple(item.artifact_reference for item in first) == tuple(
        item.artifact_reference for item in second
    )
    assert tuple(item.related_references for item in first) == tuple(
        item.related_references for item in second
    )
    assert tuple(asdict(item) for item in first) == tuple(
        asdict(item) for item in second
    )
    assert json.dumps([asdict(item) for item in first], sort_keys=True) == json.dumps(
        [asdict(item) for item in second], sort_keys=True
    )
    assert str(first) == str(second)


def test_prior_nonempty_diagnostics_remain_immutable_and_later_state_is_observed():
    plan, context = _openai(False)
    requests = list(plan.requests) + [plan.requests[0]]
    submitted = plan.model_construct(**{**plan.__dict__, "requests": requests})
    first = validate_openai_provider_request_plan(submitted, context)
    assert first
    frozen_payload = tuple(asdict(item) for item in first)
    requests.append(plan.requests[1])
    second = validate_openai_provider_request_plan(submitted, context)
    assert second != first
    assert tuple(asdict(item) for item in first) == frozen_payload
