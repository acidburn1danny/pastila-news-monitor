"""M6C.6B Part 3 immutable executor-binding tests."""

import pytest
from test_corrective_action_execution_dispatch_contracts import (
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutorBinding,
    CorrectiveActionExecutorBindings,
    CorrectiveActionExecutorRegistry,
    validate_executor_bindings,
)


class _Executor:
    def __init__(self, descriptor):
        self._descriptor = descriptor

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, request):  # pragma: no cover - binding does not invoke
        raise AssertionError


def _descriptor_for(action=CorrectiveAction.REQUEST_REGENERATION):
    return _descriptor(_planning_result(action).plan)


def test_binding_preserves_exact_advertised_descriptor_identity() -> None:
    descriptor = _descriptor_for()
    binding = CorrectiveActionExecutorBinding(descriptor, _Executor(descriptor))
    assert binding.executor.descriptor is binding.descriptor


def test_binding_rejects_equivalent_but_distinct_descriptor() -> None:
    descriptor = _descriptor_for()
    equivalent = type(descriptor).model_validate(descriptor.model_dump())
    with pytest.raises(ValueError, match="identity"):
        CorrectiveActionExecutorBinding(descriptor, _Executor(equivalent))


def test_bindings_are_canonical_complete_immutable_and_deterministic() -> None:
    first = _descriptor_for(CorrectiveAction.REQUEST_REGENERATION)
    second = _descriptor_for(CorrectiveAction.REQUEST_MANUAL_REVIEW)
    registry = CorrectiveActionExecutorRegistry.build((second, first))
    bindings = CorrectiveActionExecutorBindings.build(
        registry,
        (
            CorrectiveActionExecutorBinding(second, _Executor(second)),
            CorrectiveActionExecutorBinding(first, _Executor(first)),
        ),
    )
    assert tuple(item.descriptor for item in bindings.bindings) == registry.descriptors
    assert bindings == CorrectiveActionExecutorBindings.build(
        registry, tuple(reversed(bindings.bindings))
    )
    with pytest.raises(AttributeError):
        bindings.bindings = ()
    validate_executor_bindings(bindings)


def test_bindings_reject_missing_and_foreign_descriptors() -> None:
    descriptor = _descriptor_for()
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    with pytest.raises(ValueError, match="exactly cover"):
        CorrectiveActionExecutorBindings.build(registry, ())
    foreign = _descriptor_for(CorrectiveAction.REQUEST_MANUAL_REVIEW)
    with pytest.raises(ValueError, match="exactly cover"):
        CorrectiveActionExecutorBindings.build(
            registry,
            (CorrectiveActionExecutorBinding(foreign, _Executor(foreign)),),
        )


def test_binding_fingerprint_tampering_fails_closed() -> None:
    descriptor = _descriptor_for()
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    bindings = CorrectiveActionExecutorBindings.build(
        registry, (CorrectiveActionExecutorBinding(descriptor, _Executor(descriptor)),)
    )
    tampered = object.__new__(CorrectiveActionExecutorBindings)
    for name in ("registry", "bindings", "bindings_version"):
        object.__setattr__(tampered, name, getattr(bindings, name))
    object.__setattr__(tampered, "bindings_fingerprint", "sha256:bad")
    with pytest.raises(ValueError, match="fingerprint"):
        validate_executor_bindings(tampered)
