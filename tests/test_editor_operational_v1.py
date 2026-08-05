"""Adversarial tests for the provider-free Editor operational foundation."""

from __future__ import annotations

import copy
import functools
import inspect
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

import pastila_scout.editor_operational_v1 as public_api
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
)
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor import SelectionEngine
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor_operational_v1 import (
    EditorOperationalConfigurationError,
    EditorOperationalCoordinatorV1,
    EditorOperationalFailureCodeV1,
    EditorOperationalFailureV1,
    EditorOperationalLifecycleStateV1,
    EditorOperationalPreparationResultV1,
)

EXPECTED_API = (
    "EditorGenerationPlanV1",
    "EditorOperationalConfigurationError",
    "EditorOperationalCoordinatorV1",
    "EditorOperationalFailureCodeV1",
    "EditorOperationalFailureV1",
    "EditorOperationalLifecycleStateV1",
    "EditorOperationalPreparationResultV1",
    "EditorSelectionEngineV1",
)


class FakeSelectionEngine:
    def __init__(self, result: object | None = None, error: Exception | None = None):
        self.calls = 0
        self.arguments = []
        self.result = result
        self.error = error

    def select(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> EditorialSelectionResult:
        self.calls += 1
        self.arguments.append((scout_input, profile, context))
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result  # type: ignore[return-value]
        return SelectionEngine().select(scout_input, profile, context)


def inputs():
    return sample_scout_input(), sample_selection_profile(), sample_episode_context()


def success():
    engine = FakeSelectionEngine()
    coordinator = EditorOperationalCoordinatorV1(engine)
    result = coordinator.prepare(*inputs())
    assert result.plan is not None
    return engine, coordinator, result


def test_exact_public_api_and_order() -> None:
    assert public_api.__all__ == EXPECTED_API
    assert (
        tuple(name for name in EXPECTED_API if hasattr(public_api, name))
        == EXPECTED_API
    )


def test_valid_preparation_calls_selection_once_with_reconstructed_inputs() -> None:
    source, profile, context = inputs()
    engine = FakeSelectionEngine()

    result = EditorOperationalCoordinatorV1(engine).prepare(source, profile, context)

    assert engine.calls == 1
    passed_source, passed_profile, passed_context = engine.arguments[0]
    assert passed_source == source and passed_source is not source
    assert passed_profile == profile and passed_profile is not profile
    assert passed_context == context and passed_context is not context
    assert result.lifecycle == (
        EditorOperationalLifecycleStateV1.ACCEPTED,
        EditorOperationalLifecycleStateV1.VALIDATED,
        EditorOperationalLifecycleStateV1.SELECTED,
        EditorOperationalLifecycleStateV1.PLANNED,
    )
    assert result.failure is None
    assert result.plan is not None
    assert result.plan.source_report_id == source.report_id
    assert result.plan.source_report_fingerprint == source.content_fingerprint


def test_real_selection_engine_is_accepted_and_deterministic() -> None:
    coordinator = EditorOperationalCoordinatorV1(SelectionEngine())
    first = coordinator.prepare(*inputs())
    second = coordinator.prepare(*inputs())

    assert first == second
    assert first.plan == second.plan


def test_invalid_input_returns_closed_failure_without_selection() -> None:
    source, profile, context = inputs()
    object.__setattr__(source, "report_id", "scout-editor-input-v1:sha256:" + "0" * 64)
    engine = FakeSelectionEngine()

    result = EditorOperationalCoordinatorV1(engine).prepare(source, profile, context)

    assert engine.calls == 0
    assert result.source_report_id == result.source_report_fingerprint == ""
    assert result.plan is None
    assert result.failure == EditorOperationalFailureV1(
        EditorOperationalFailureCodeV1.INVALID_INPUT,
        "Editor operational input is invalid.",
    )


def test_selection_exception_is_sanitized_failure() -> None:
    secret = RuntimeError("private-editorial-content")
    engine = FakeSelectionEngine(error=secret)

    result = EditorOperationalCoordinatorV1(engine).prepare(*inputs())

    assert engine.calls == 1
    assert result.plan is None
    assert result.failure is not None
    assert result.failure.code is EditorOperationalFailureCodeV1.SELECTION_FAILED
    assert result.failure.safe_message == "Editor deterministic selection failed."
    assert "private-editorial-content" not in repr(result)


def test_invalid_selection_result_has_no_partial_plan() -> None:
    engine = FakeSelectionEngine(result=object())

    result = EditorOperationalCoordinatorV1(engine).prepare(*inputs())

    assert result.plan is None
    assert result.failure is not None
    assert (
        result.failure.code is EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT
    )


@pytest.mark.parametrize(
    ("code", "message"),
    (
        (
            EditorOperationalFailureCodeV1.INVALID_INPUT,
            "Editor operational input is invalid.",
        ),
        (
            EditorOperationalFailureCodeV1.SELECTION_FAILED,
            "Editor deterministic selection failed.",
        ),
        (
            EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT,
            "Editor deterministic selection returned an invalid result.",
        ),
        (
            EditorOperationalFailureCodeV1.PLAN_CONSTRUCTION_FAILED,
            "Editor generation plan construction failed.",
        ),
    ),
)
def test_failure_contract_is_closed(code, message) -> None:
    failure = EditorOperationalFailureV1(code, message)
    assert failure.retryable is False
    with pytest.raises(ValueError):
        EditorOperationalFailureV1(code, message, True)
    with pytest.raises(ValueError):
        EditorOperationalFailureV1(code, "wrong")


def test_contradictory_result_states_are_rejected() -> None:
    _, _, result = success()
    assert result.plan is not None
    with pytest.raises(ValueError):
        EditorOperationalPreparationResultV1(
            result.source_report_id,
            result.source_report_fingerprint,
            result.lifecycle,
            result.plan,
            EditorOperationalFailureV1(
                EditorOperationalFailureCodeV1.PLAN_CONSTRUCTION_FAILED,
                "Editor generation plan construction failed.",
            ),
        )
    with pytest.raises(ValueError):
        EditorOperationalPreparationResultV1(
            result.source_report_id,
            result.source_report_fingerprint,
            (
                EditorOperationalLifecycleStateV1.ACCEPTED,
                EditorOperationalLifecycleStateV1.FAILED,
            ),
            None,
            EditorOperationalFailureV1(
                EditorOperationalFailureCodeV1.SELECTION_FAILED,
                "Editor deterministic selection failed.",
            ),
        )


def test_contracts_are_frozen_slotted_and_reject_copied_invalid_state() -> None:
    _, _, result = success()
    assert result.plan is not None
    for value in (result.plan, result, result.failure):
        if value is None:
            continue
        assert not hasattr(value, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.extra = "forbidden"  # type: ignore[attr-defined]
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            del value._seal
    object.__setattr__(result, "source_report_id", "corrupted")
    with pytest.raises(ValueError):
        copy.copy(result)


def test_copy_deepcopy_pickle_repr_and_equality_are_safe() -> None:
    engine, coordinator, result = success()
    assert result.plan is not None
    for value in (result.plan, result):
        shallow = copy.copy(value)
        deep = copy.deepcopy(value)
        assert shallow == value and shallow is not value
        assert deep == value and deep is not value
        assert "0x" not in repr(value)
        with pytest.raises(TypeError, match="does not support pickle"):
            pickle.dumps(value)
    copied = copy.copy(coordinator)
    deep = copy.deepcopy(coordinator)
    assert copied == coordinator and deep == coordinator
    assert copied.selection_engine is engine and deep.selection_engine is engine
    assert "0x" not in repr(coordinator)
    with pytest.raises(TypeError, match="does not support pickle"):
        pickle.dumps(coordinator)


def test_repr_and_equality_do_not_invoke_dependency_hooks() -> None:
    engine = FakeSelectionEngine()
    coordinator = EditorOperationalCoordinatorV1(engine)
    engine.__dict__["__repr__"] = lambda: (_ for _ in ()).throw(AssertionError())
    engine.__dict__["__eq__"] = lambda _: (_ for _ in ()).throw(AssertionError())

    assert repr(coordinator).startswith("EditorOperationalCoordinatorV1(")
    assert coordinator == EditorOperationalCoordinatorV1(engine)


def _assert_invalid_engine(engine: object) -> None:
    with pytest.raises(EditorOperationalConfigurationError) as caught:
        EditorOperationalCoordinatorV1(engine)  # type: ignore[arg-type]
    assert str(caught.value) == "Editor operational configuration is invalid."
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_malformed_dependency_shapes_are_rejected_without_invocation() -> None:
    class Missing:
        pass

    class WrongName:
        def select(
            self,
            source: ScoutEditorInputV1,
            profile: SelectionProfileV1,
            context: EpisodeContextV1,
        ) -> EditorialSelectionResult:
            raise AssertionError

    class WrongAnnotation:
        def select(self, scout_input, profile, context) -> object:
            raise AssertionError

    class Static:
        @staticmethod
        def select(scout_input, profile, context) -> EditorialSelectionResult:
            raise AssertionError

    class Class:
        @classmethod
        def select(cls, scout_input, profile, context) -> EditorialSelectionResult:
            raise AssertionError

    for value in (Missing(), WrongName(), WrongAnnotation(), Static(), Class()):
        _assert_invalid_engine(value)


def test_properties_partials_wrappers_forged_and_dynamic_methods_are_rejected() -> None:
    class Property:
        @property
        def select(self):
            raise AssertionError

    class Dynamic:
        def __getattr__(self, name):
            raise AssertionError(name)

    class InstanceOnly:
        pass

    instance_only = InstanceOnly()
    instance_only.select = FakeSelectionEngine().select

    for value in (Property(), Dynamic(), instance_only):
        _assert_invalid_engine(value)

    def valid(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> EditorialSelectionResult:
        raise AssertionError

    wrapped = functools.wraps(valid)(lambda *args: None)
    partial = functools.partial(valid, object())

    class Wrapped:
        select = wrapped

    class Partial:
        select = partial

    class Forged:
        select = valid

    Forged.select.__signature__ = inspect.signature(valid)  # type: ignore[attr-defined]
    try:
        for value in (Wrapped(), Partial(), Forged()):
            _assert_invalid_engine(value)
    finally:
        del Forged.select.__signature__  # type: ignore[attr-defined]


def test_corrupted_coordinator_fails_closed() -> None:
    engine = FakeSelectionEngine()
    coordinator = EditorOperationalCoordinatorV1(engine)
    object.__setattr__(coordinator, "selection_engine", object())

    with pytest.raises(EditorOperationalConfigurationError):
        copy.copy(coordinator)
    assert engine.calls == 0


def test_invalid_contract_tracebacks_retain_no_editor_authority() -> None:
    source, profile, context = inputs()
    selection = SelectionEngine().select(source, profile, context)
    with pytest.raises(ValueError) as caught:
        EditorOperationalPreparationResultV1(
            source.report_id,
            source.content_fingerprint,
            (
                EditorOperationalLifecycleStateV1.ACCEPTED,
                EditorOperationalLifecycleStateV1.FAILED,
            ),
            EditorOperationalCoordinatorV1(SelectionEngine())
            .prepare(source, profile, context)
            .plan,
            None,
        )
    forbidden_types = {
        "ScoutEditorInputV1",
        "SelectionProfileV1",
        "EpisodeContextV1",
        "EditorAgentOutputV1",
        "DecisionTrace",
        "EditorGenerationPlanV1",
        "EditorialSelectionResult",
        "SelectionEngine",
    }
    traceback = caught.value.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
        if "/src/pastila_scout/editor_operational_v1/" in filename:
            assert all(
                type(value).__name__ not in forbidden_types
                for value in traceback.tb_frame.f_locals.values()
            )
        traceback = traceback.tb_next
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert selection.output.status == "success"


def test_package_has_no_generation_provider_or_runtime_dependencies() -> None:
    modules = (
        sys.modules["pastila_scout.editor_operational_v1"],
        sys.modules["pastila_scout.editor_operational_v1.coordinator"],
        sys.modules["pastila_scout.editor_operational_v1.models"],
    )
    forbidden = (
        "ControlledGenerator",
        "LanguageModelProvider",
        "ProviderSelectorV1",
        "ApplicationRequestAuthorityV1",
        "ScoutWorkflowExecutionV1",
        "ScoutRuntimeExecutionBridgeV1",
    )
    assert all(not hasattr(module, name) for module in modules for name in forbidden)


def test_fresh_process_import_is_passive() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "import pastila_scout.editor_operational_v1"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""


def test_no_generation_or_side_effect_fields_exist() -> None:
    _, coordinator, result = success()
    assert result.plan is not None
    forbidden = {
        "provider",
        "executor",
        "client",
        "credential",
        "runtime",
        "retry",
        "timeout",
        "cancellation",
        "observer",
        "cleanup",
        "persistence",
        "draft",
    }
    assert forbidden.isdisjoint(result.plan.__slots__)
    assert forbidden.isdisjoint(result.__slots__)
    assert forbidden.isdisjoint(coordinator.__slots__)
