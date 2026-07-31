"""M6C.6B Part 2 immutable executor-registry tests."""

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_dispatch_contracts import (
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRegistry,
    build_executor_registry_report,
    render_executor_registry_report,
    serialize_executor_registry_report,
    validate_executor_registry,
)


def _descriptors():
    revision = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    ).plan
    regeneration = _planning_result(CorrectiveAction.REQUEST_REGENERATION).plan
    return (
        _descriptor(regeneration),
        _descriptor(revision),
    )


def test_registry_is_canonical_immutable_and_deterministic() -> None:
    first = CorrectiveActionExecutorRegistry.build(_descriptors())
    second = CorrectiveActionExecutorRegistry.build(reversed(_descriptors()))
    assert first == second
    assert tuple(item.executor_id for item in first.descriptors) == tuple(
        sorted(item.executor_id for item in first.descriptors)
    )
    with pytest.raises(ValidationError):
        first.descriptors = ()
    validate_executor_registry(first)


def test_registry_rejects_duplicate_executor_ids_and_descriptors() -> None:
    descriptor = _descriptors()[0]
    other = _descriptors()[1]
    duplicate_id = CorrectiveActionExecutorDescriptor.build(
        executor_id=descriptor.executor_id,
        supported_capability=other.supported_capability,
        supported_plan_types=other.supported_plan_types,
        supports_automatic_invocation=other.supports_automatic_invocation,
        supports_human_gated_invocation=other.supports_human_gated_invocation,
    )
    with pytest.raises(ValidationError, match="duplicate identifiers"):
        CorrectiveActionExecutorRegistry.build((descriptor, duplicate_id))
    with pytest.raises(ValidationError, match="duplicate identifiers"):
        CorrectiveActionExecutorRegistry.build((descriptor, descriptor))


def test_registry_lookup_uses_exact_capability_and_plan_type() -> None:
    registry = CorrectiveActionExecutorRegistry.build(_descriptors())
    descriptor = registry.descriptors[0]
    assert registry.lookup(
        descriptor.supported_capability, descriptor.supported_plan_types[0]
    ) == (descriptor,)
    other = registry.descriptors[1]
    assert (
        registry.lookup(descriptor.supported_capability, other.supported_plan_types[0])
        == ()
    )


def test_registry_fingerprint_tampering_and_unknown_version_fail_closed() -> None:
    registry = CorrectiveActionExecutorRegistry.build(_descriptors())
    with pytest.raises(ValueError):
        validate_executor_registry(
            registry.model_copy(update={"registry_fingerprint": "sha256:bad"})
        )
    with pytest.raises(ValidationError):
        CorrectiveActionExecutorRegistry.model_validate(
            {**registry.model_dump(), "registry_version": "999"}
        )


def test_registry_safe_report_and_serialization_are_deterministic() -> None:
    registry = CorrectiveActionExecutorRegistry.build(_descriptors())
    report = build_executor_registry_report(registry)
    serialized = serialize_executor_registry_report(report)
    rendered = render_executor_registry_report(report)
    assert serialized == serialize_executor_registry_report(report)
    assert report.registry_fingerprint in serialized
    assert "executor instance" not in serialized.casefold()
    assert "Descriptors: 2" in rendered
