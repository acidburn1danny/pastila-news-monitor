"""M6C.6B Part 2 deterministic capability-resolution tests."""

import pytest
from test_corrective_action_execution_dispatch_contracts import (
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CapabilityResolutionResult,
    CapabilityResolutionStatus,
    CapabilityResolver,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRegistry,
    build_capability_resolution_report,
    render_capability_resolution_report,
    serialize_capability_resolution_report,
    validate_capability_resolution_result,
)


def _revision_result():
    return _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )


def test_zero_match_fails_closed() -> None:
    result = CapabilityResolver().resolve(
        _revision_result(), CorrectiveActionExecutorRegistry.build(())
    )
    assert result.status is CapabilityResolutionStatus.ZERO_MATCH
    assert result.matching_descriptor_count == 0
    assert result.descriptor is None


def test_exact_match_preserves_planning_and_descriptor_identity() -> None:
    plan_result = _revision_result()
    descriptor = _descriptor(plan_result.plan)
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    result = CapabilityResolver().resolve(plan_result, registry)
    assert result.status is CapabilityResolutionStatus.EXACT_MATCH
    assert result.plan_result is plan_result
    assert result.registry is registry
    assert result.descriptor is descriptor
    validate_capability_resolution_result(result)


def test_ambiguous_match_is_reported_without_selecting_an_executor() -> None:
    plan_result = _revision_result()
    first = _descriptor(plan_result.plan)
    second = CorrectiveActionExecutorDescriptor.build(
        executor_id="alternate-draft-revision.v1",
        supported_capability=first.supported_capability,
        supported_plan_types=first.supported_plan_types,
        supports_automatic_invocation=True,
        supports_human_gated_invocation=True,
    )
    registry = CorrectiveActionExecutorRegistry.build((first, second))
    result = CapabilityResolver().resolve(plan_result, registry)
    assert result.status is CapabilityResolutionStatus.AMBIGUOUS_MATCH
    assert result.matching_descriptor_count == 2
    assert result.descriptor is None


def test_none_capability_never_resolves() -> None:
    result = CapabilityResolver().resolve(
        _planning_result(CorrectiveAction.CONTINUE_WORKFLOW),
        CorrectiveActionExecutorRegistry.build(()),
    )
    assert result.status is CapabilityResolutionStatus.CAPABILITY_NONE


def test_explicit_plan_compatibility_is_required_by_descriptor_contract() -> None:
    revision = _revision_result().plan
    regeneration = _planning_result(CorrectiveAction.REQUEST_REGENERATION).plan
    with pytest.raises(ValueError, match="capability and plan types"):
        CorrectiveActionExecutorDescriptor.build(
            executor_id="incompatible.v1",
            supported_capability=revision.required_capability,
            supported_plan_types=(regeneration.plan_type,),
            supports_automatic_invocation=True,
            supports_human_gated_invocation=True,
        )


def test_invalid_registry_and_plan_fingerprints_fail_closed() -> None:
    plan_result = _revision_result()
    registry = CorrectiveActionExecutorRegistry.build((_descriptor(plan_result.plan),))
    bad_registry = registry.model_copy(update={"registry_fingerprint": "sha256:bad"})
    bad_plan = plan_result.model_copy(update={"result_fingerprint": "sha256:bad"})
    resolver = CapabilityResolver()
    assert (
        resolver.resolve(plan_result, bad_registry).status
        is CapabilityResolutionStatus.INVALID_REGISTRY
    )
    assert (
        resolver.resolve(bad_plan, registry).status
        is CapabilityResolutionStatus.INTEGRITY_FAILURE
    )


def test_resolution_and_safe_report_are_deterministic() -> None:
    plan_result = _revision_result()
    registry = CorrectiveActionExecutorRegistry.build((_descriptor(plan_result.plan),))
    resolver = CapabilityResolver()
    first = resolver.resolve(plan_result, registry)
    second = resolver.resolve(plan_result, registry)
    assert first == second
    report = build_capability_resolution_report(first)
    serialized = serialize_capability_resolution_report(report)
    rendered = render_capability_resolution_report(report)
    assert serialized == serialize_capability_resolution_report(report)
    assert "finding" not in serialized and "provider" not in serialized
    assert "Resolution: exact_match" in rendered


def test_tampered_resolution_fingerprint_and_unknown_status_are_rejected() -> None:
    plan_result = _revision_result()
    registry = CorrectiveActionExecutorRegistry.build((_descriptor(plan_result.plan),))
    result = CapabilityResolver().resolve(plan_result, registry)
    with pytest.raises(ValueError):
        validate_capability_resolution_result(
            result.model_copy(update={"resolution_fingerprint": "sha256:bad"})
        )
    values = result.model_dump(mode="python")
    values["status"] = "first_match"
    with pytest.raises(ValueError):
        CapabilityResolutionResult.model_validate(values)


def test_resolution_layer_has_no_invocation_surface() -> None:
    assert not hasattr(CapabilityResolver, "dispatch")
    assert not hasattr(CapabilityResolver, "execute")
    assert "register" not in CorrectiveActionExecutorRegistry.__dict__
    assert "unregister" not in CorrectiveActionExecutorRegistry.__dict__
