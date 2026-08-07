from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import os
import pickle
import socket
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from test_editor_application_contracts_v1 import (
    failure as editor_failure,
)
from test_editor_application_contracts_v1 import (
    generation as editor_generation,
)
from test_editor_application_contracts_v1 import (
    invalid_execution_request_result,
)
from test_editor_application_contracts_v1 import (
    request as editor_application_request,
)
from test_editor_operational_execution_v1 import (
    controlled_output,
    execute_fake,
    observation,
)

import pastila_scout.desktop_application_v1 as public
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
    DesktopApplicationFacadeV1,
    DesktopApplicationFailureCodeV1,
    DesktopApplicationFailureV1,
    DesktopOperationKindV1,
    DesktopOperationStatusV1,
    DesktopProgressEventV1,
    DesktopProgressStageV1,
    DesktopReportReferenceV1,
    EditorDesktopRequestV1,
    EditorDesktopResultV1,
    ScoutDesktopCategoryV1,
    ScoutDesktopRequestV1,
    ScoutDesktopResultV1,
    reconstruct_scout_desktop_result,
)
from pastila_scout.editor_application_v1 import (
    EditorApplicationExitCodeV1,
    EditorApplicationFailureCodeV1,
    EditorApplicationLifecycleStateV1,
    EditorApplicationResultV1,
    EditorApplicationStatusV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

EXPECTED_API = (
    "DesktopApplicationConfigurationError",
    "DesktopApplicationExecutionError",
    "DesktopApplicationFacadeV1",
    "DesktopApplicationFailureCodeV1",
    "DesktopApplicationFailureV1",
    "DesktopOperationKindV1",
    "DesktopOperationStatusV1",
    "DesktopProgressEventV1",
    "DesktopProgressSinkV1",
    "DesktopProgressStageV1",
    "DesktopReportReferenceV1",
    "EditorDesktopOperationV1",
    "EditorDesktopRequestV1",
    "EditorDesktopResultV1",
    "ScoutDesktopCategoryV1",
    "ScoutDesktopOperationV1",
    "ScoutDesktopRequestV1",
    "ScoutDesktopResultV1",
    "reconstruct_desktop_application_failure",
    "reconstruct_desktop_progress_event",
    "reconstruct_desktop_report_reference",
    "reconstruct_editor_desktop_request",
    "reconstruct_editor_desktop_result",
    "reconstruct_scout_desktop_request",
    "reconstruct_scout_desktop_result",
)


def scout_request(**changes: object) -> ScoutDesktopRequestV1:
    values = {
        "operation_reference": "desktop-operation-1",
        "period_days": 7,
        "category": ScoutDesktopCategoryV1.POLITICA,
    }
    values.update(changes)
    return ScoutDesktopRequestV1(**values)


def scout_result(
    status: DesktopOperationStatusV1 = DesktopOperationStatusV1.COMPLETED,
    **changes: object,
) -> ScoutDesktopResultV1:
    variants = {
        DesktopOperationStatusV1.COMPLETED: {
            "sources_checked": 2,
            "sources_succeeded": 2,
            "sources_failed": 0,
            "failed_source_ids": (),
            "report_reference": DesktopReportReferenceV1(report_reference="report-1"),
            "failure": None,
        },
        DesktopOperationStatusV1.PARTIAL: {
            "sources_checked": 2,
            "sources_succeeded": 1,
            "sources_failed": 1,
            "failed_source_ids": ("source-b",),
            "report_reference": None,
            "failure": None,
        },
        DesktopOperationStatusV1.FAILED: {
            "sources_checked": 1,
            "sources_succeeded": 0,
            "sources_failed": 1,
            "failed_source_ids": ("source-a",),
            "report_reference": None,
            "failure": DesktopApplicationFailureV1(
                code=DesktopApplicationFailureCodeV1.SCOUT_EXECUTION_FAILED
            ),
        },
    }
    values: dict[str, object] = {
        "operation_reference": "desktop-operation-1",
        "status": status,
        **variants[status],
        "articles_found": 5,
        "articles_inserted": 3,
        "duplicates_skipped": 2,
        "executed_period_days": 7,
        "executed_category": ScoutDesktopCategoryV1.POLITICA,
    }
    values.update(changes)
    return ScoutDesktopResultV1(**values)


def cancelled_editor_result(reference: str) -> EditorApplicationResultV1:
    return EditorApplicationResultV1(
        reference,
        EditorApplicationStatusV1.CANCELLED,
        (
            EditorApplicationLifecycleStateV1.ACCEPTED,
            EditorApplicationLifecycleStateV1.VALIDATED,
            EditorApplicationLifecycleStateV1.CANCELLED,
        ),
        None,
        None,
        None,
        False,
        False,
        editor_failure(EditorApplicationFailureCodeV1.CANCELLED),
        EditorApplicationExitCodeV1.CANCELLED,
    )


class ScoutOperation:
    def __init__(
        self, result: object | None = None, error: BaseException | None = None
    ):
        self.result = result if result is not None else scout_result()
        self.error = error
        self.calls: list[ScoutDesktopRequestV1] = []

    def run_scout(self, *, request: ScoutDesktopRequestV1) -> ScoutDesktopResultV1:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result  # type: ignore[return-value]


class EditorOperation:
    def __init__(
        self, result: object | None = None, error: BaseException | None = None
    ):
        self.result = result
        self.error = error
        self.calls: list[EditorDesktopRequestV1] = []

    def run_editor(self, *, request: EditorDesktopRequestV1) -> EditorDesktopResultV1:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result  # type: ignore[return-value]


class Sink:
    def __init__(self, fail_at: int | None = None):
        self.events: list[DesktopProgressEventV1] = []
        self.fail_at = fail_at

    def publish(self, *, event: DesktopProgressEventV1) -> None:
        self.events.append(event)
        if self.fail_at == len(self.events):
            raise RuntimeError("private sink detail")


def facade(
    scout: ScoutOperation | None = None, editor: EditorOperation | None = None
) -> DesktopApplicationFacadeV1:
    return DesktopApplicationFacadeV1(
        scout_operation=scout or ScoutOperation(),
        editor_operation=editor or EditorOperation(),
    )


def test_exact_public_api_ownership_and_signatures() -> None:
    assert public.__all__ == EXPECTED_API
    assert all(hasattr(public, name) for name in EXPECTED_API)
    assert public.DesktopApplicationFailureV1.__module__.endswith(".models")
    assert public.DesktopApplicationFacadeV1.__module__.endswith(".services")
    assert public.DesktopApplicationExecutionError.__module__.endswith(".errors")
    assert str(inspect.signature(public.DesktopApplicationFacadeV1.run_scout)) == (
        "(self, *, request: 'ScoutDesktopRequestV1', "
        "progress_sink: 'DesktopProgressSinkV1') -> 'ScoutDesktopResultV1'"
    )


def test_closed_enum_vocabularies_copy_and_pickle() -> None:
    expected = {
        DesktopOperationKindV1: ("scout", "editor"),
        DesktopOperationStatusV1: ("completed", "partial", "failed", "cancelled"),
        DesktopProgressStageV1: (
            "accepted",
            "running",
            "completed",
            "partial",
            "failed",
            "cancelled",
        ),
        ScoutDesktopCategoryV1: (
            "Politica",
            "Social",
            "Conspiratii",
            "Economie",
            "CanCan",
            "Externe",
            "Diverse",
            "all",
        ),
        DesktopApplicationFailureCodeV1: ("scout_execution_failed",),
    }
    for enum_type, values in expected.items():
        assert tuple(item.value for item in enum_type) == values
        for member in enum_type:
            assert copy.copy(member) is member
            assert copy.deepcopy(member) is member
            with pytest.raises(TypeError):
                pickle.dumps(member)


@pytest.mark.parametrize("period", [1, 3, 7, 14, 30])
@pytest.mark.parametrize("category", tuple(ScoutDesktopCategoryV1))
def test_all_scout_request_periods_and_categories(period: int, category) -> None:
    request = scout_request(period_days=period, category=category)
    assert copy.copy(request) == request
    assert copy.deepcopy(request) == request


@pytest.mark.parametrize(
    ("changes"),
    [
        {"operation_reference": ""},
        {"operation_reference": " x"},
        {"operation_reference": "e\u0301"},
        {"operation_reference": "x\x00"},
        {"period_days": True},
        {"period_days": 2},
        {"category": "Politica"},
    ],
)
def test_scout_request_rejects_invalid_scalars(changes: dict[str, object]) -> None:
    with pytest.raises(DesktopApplicationConfigurationError) as captured:
        scout_request(**changes)
    assert str(captured.value) == "Desktop application configuration is invalid."
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


@pytest.mark.parametrize("status", tuple(DesktopOperationStatusV1)[:3])
def test_every_valid_scout_result_and_authoritative_reconstruction(status) -> None:
    result = scout_result(status)
    assert copy.copy(result) == result
    assert copy.deepcopy(result) == result
    assert "report-1" not in repr(result)
    with pytest.raises(TypeError):
        pickle.dumps(result)


@pytest.mark.parametrize(
    "changes",
    [
        {"sources_checked": True},
        {"sources_checked": -1},
        {"sources_succeeded": 1},
        {"articles_inserted": 6},
        {"duplicates_skipped": 3},
        {"failed_source_ids": ["a"]},
        {"failed_source_ids": ("a", 1)},
        {"failed_source_ids": ("a",)},
        {"executed_period_days": 2},
        {"executed_category": "Politica"},
    ],
)
def test_scout_result_rejects_invalid_counters_and_sequences(changes) -> None:
    with pytest.raises(DesktopApplicationConfigurationError):
        scout_result(**changes)


@pytest.mark.parametrize(
    "failed_source_ids",
    [
        ("zeta", "alpha"),
        ("same", "same"),
        ("id: delimiter-like", "știri"),
    ],
)
def test_scout_result_preserves_failed_source_occurrences(
    failed_source_ids: tuple[str, str],
) -> None:
    result = scout_result(
        DesktopOperationStatusV1.PARTIAL,
        sources_checked=3,
        sources_succeeded=1,
        sources_failed=2,
        failed_source_ids=failed_source_ids,
    )

    assert result.failed_source_ids is failed_source_ids
    assert (
        reconstruct_scout_desktop_result(result).failed_source_ids == failed_source_ids
    )


def test_result_status_matrix_and_failure_message_are_closed() -> None:
    assert scout_result(DesktopOperationStatusV1.PARTIAL).status.value == "partial"
    failed = scout_result(DesktopOperationStatusV1.FAILED)
    assert failed.failure.safe_message == "Scout execution failed."
    with pytest.raises(DesktopApplicationConfigurationError):
        ScoutDesktopResultV1(
            operation_reference="desktop-operation-1",
            status=DesktopOperationStatusV1.CANCELLED,
            sources_checked=0,
            sources_succeeded=0,
            sources_failed=0,
            articles_found=0,
            articles_inserted=0,
            duplicates_skipped=0,
            failed_source_ids=(),
            executed_period_days=7,
            executed_category=ScoutDesktopCategoryV1.POLITICA,
            report_reference=None,
            failure=None,
        )
    with pytest.raises(DesktopApplicationConfigurationError):
        scout_result(
            DesktopOperationStatusV1.FAILED,
            report_reference=DesktopReportReferenceV1(report_reference="report"),
        )


def test_progress_pair_matrix_and_value_safety() -> None:
    for operation in DesktopOperationKindV1:
        for stage in DesktopProgressStageV1:
            illegal = (operation, stage) in {
                (DesktopOperationKindV1.SCOUT, DesktopProgressStageV1.CANCELLED),
                (DesktopOperationKindV1.EDITOR, DesktopProgressStageV1.PARTIAL),
            }
            if illegal:
                with pytest.raises(DesktopApplicationConfigurationError):
                    DesktopProgressEventV1(
                        operation_reference="operation",
                        operation=operation,
                        stage=stage,
                    )
            else:
                event = DesktopProgressEventV1(
                    operation_reference="operation", operation=operation, stage=stage
                )
                assert copy.copy(event) == event


def test_all_concrete_values_reject_subclassing() -> None:
    values = (
        DesktopApplicationFailureV1,
        DesktopReportReferenceV1,
        ScoutDesktopRequestV1,
        EditorDesktopRequestV1,
        DesktopProgressEventV1,
        ScoutDesktopResultV1,
        EditorDesktopResultV1,
    )
    for value_type in values:
        with pytest.raises(TypeError):
            type(f"Foreign{value_type.__name__}", (value_type,), {})


def test_copied_invalid_values_are_rejected_without_hooks() -> None:
    request = scout_request()
    object.__setattr__(request, "period_days", 30)
    for operation in (copy.copy, copy.deepcopy, repr):
        with pytest.raises(DesktopApplicationConfigurationError):
            operation(request)
    with pytest.raises(DesktopApplicationConfigurationError):
        facade().run_scout(request=request, progress_sink=Sink())


def test_scout_facade_success_partial_failure_progress_and_cardinality() -> None:
    for status, terminal in (
        (DesktopOperationStatusV1.COMPLETED, DesktopProgressStageV1.COMPLETED),
        (DesktopOperationStatusV1.PARTIAL, DesktopProgressStageV1.PARTIAL),
        (DesktopOperationStatusV1.FAILED, DesktopProgressStageV1.FAILED),
    ):
        scout = ScoutOperation(scout_result(status))
        editor = EditorOperation()
        sink = Sink()
        actual = facade(scout, editor).run_scout(
            request=scout_request(), progress_sink=sink
        )
        assert actual == scout_result(status)
        assert len(scout.calls) == 1
        assert editor.calls == []
        assert [event.stage for event in sink.events] == [
            DesktopProgressStageV1.ACCEPTED,
            DesktopProgressStageV1.RUNNING,
            terminal,
        ]


def test_editor_wrapper_and_cancelled_result_are_unchanged(tmp_path: Path) -> None:
    application_request = editor_application_request(tmp_path)
    request = EditorDesktopRequestV1(application_request=application_request)
    nested = cancelled_editor_result(application_request.operation_reference)
    expected = EditorDesktopResultV1(application_result=nested)
    scout = ScoutOperation()
    editor = EditorOperation(expected)
    sink = Sink()
    actual = facade(scout, editor).run_editor(request=request, progress_sink=sink)
    assert actual.application_result == nested
    assert len(editor.calls) == 1
    assert scout.calls == []
    assert [event.stage for event in sink.events] == [
        DesktopProgressStageV1.ACCEPTED,
        DesktopProgressStageV1.RUNNING,
        DesktopProgressStageV1.CANCELLED,
    ]
    assert "content=<redacted>" in repr(actual)
    assert str(tmp_path) not in repr(actual)


def test_editor_completed_result_emits_completed_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operational, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=controlled_output(),
    )
    reference = operational.execution_request_reference
    application_request = editor_application_request(
        tmp_path, operation_reference=reference
    )
    nested = EditorApplicationResultV1(
        reference,
        EditorApplicationStatusV1.COMPLETED,
        tuple(EditorApplicationLifecycleStateV1)[:7],
        operational,
        tmp_path / "draft.json",
        f"sha256:{'a' * 64}",
        True,
        True,
        None,
        EditorApplicationExitCodeV1.COMPLETED,
    )
    editor = EditorOperation(EditorDesktopResultV1(application_result=nested))
    sink = Sink()
    actual = facade(editor=editor).run_editor(
        request=EditorDesktopRequestV1(application_request=application_request),
        progress_sink=sink,
    )
    assert actual.application_result == nested
    assert len(editor.calls) == 1
    assert [event.stage for event in sink.events] == [
        DesktopProgressStageV1.ACCEPTED,
        DesktopProgressStageV1.RUNNING,
        DesktopProgressStageV1.COMPLETED,
    ]


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        (ProviderChoiceV1.OPENAI, "gpt-4.1-mini"),
        (ProviderChoiceV1.OLLAMA, "qwen3:14b"),
    ],
)
def test_openai_and_ollama_editor_results_are_projected_unchanged(
    tmp_path: Path, provider: ProviderChoiceV1, model: str
) -> None:
    application_request = editor_application_request(
        tmp_path,
        generation_configuration=editor_generation(
            provider=provider, model_identifier=model
        ),
    )
    request = EditorDesktopRequestV1(application_request=application_request)
    expected = EditorDesktopResultV1(
        application_result=invalid_execution_request_result()
    )
    editor = EditorOperation(expected)
    actual = facade(editor=editor).run_editor(request=request, progress_sink=Sink())
    assert actual.application_result == expected.application_result
    assert editor.calls == [request]


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_sink_failure_is_fixed_safe_and_never_retries(fail_at: int) -> None:
    scout = ScoutOperation()
    sink = Sink(fail_at)
    with pytest.raises(DesktopApplicationExecutionError) as captured:
        facade(scout).run_scout(request=scout_request(), progress_sink=sink)
    assert str(captured.value) == "Desktop application execution failed."
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert len(scout.calls) == (0 if fail_at < 3 else 1)


def test_lower_exception_and_invalid_result_reduce_to_one_safe_failure() -> None:
    for lower in (RuntimeError("secret lower detail"), None):
        scout = ScoutOperation(error=lower) if lower else ScoutOperation(object())
        sink = Sink()
        with pytest.raises(DesktopApplicationExecutionError) as captured:
            facade(scout).run_scout(request=scout_request(), progress_sink=sink)
        assert captured.value.args == ("Desktop application execution failed.",)
        assert captured.value.__context__ is None
        assert captured.value.__cause__ is None
        assert len(scout.calls) == 1
        assert [event.stage for event in sink.events][
            -1
        ] is DesktopProgressStageV1.FAILED


def _assert_recursive_isolation(
    error: BaseException, protected: tuple[object, ...]
) -> None:
    protected_ids = {id(item) for item in protected}
    seen: set[int] = set()

    def inspect_value(value: object) -> None:
        if value is None or id(value) in seen:
            return
        seen.add(id(value))
        assert id(value) not in protected_ids
        if isinstance(value, BaseException):
            inspect_value(value.__context__)
            inspect_value(value.__cause__)
            traceback = value.__traceback__
            while traceback is not None:
                filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
                if "/desktop_application_v1/" in filename:
                    for nested in traceback.tb_frame.f_locals.values():
                        inspect_value(nested)
                traceback = traceback.tb_next
        elif type(value) is dict:
            for key, nested in value.items():
                inspect_value(key)
                inspect_value(nested)
        elif type(value) in (tuple, list, set, frozenset):
            for nested in value:
                inspect_value(nested)

    inspect_value(error)


def test_recursive_traceback_isolation_for_request_and_lower_failures() -> None:
    request = scout_request()
    object.__setattr__(request, "period_days", 30)
    scout = ScoutOperation()
    editor = EditorOperation()
    sink = Sink()
    application = facade(scout, editor)
    with pytest.raises(DesktopApplicationConfigurationError) as invalid:
        application.run_scout(request=request, progress_sink=sink)
    _assert_recursive_isolation(
        invalid.value, (request, scout, editor, sink, application)
    )

    lower = RuntimeError("private lower detail")
    request = scout_request()
    scout = ScoutOperation(error=lower)
    sink = Sink()
    application = facade(scout, editor)
    with pytest.raises(DesktopApplicationExecutionError) as failed:
        application.run_scout(request=request, progress_sink=sink)
    _assert_recursive_isolation(
        failed.value, (lower, request, scout, editor, sink, application)
    )

    request = scout_request()
    scout = ScoutOperation()
    sink = Sink(fail_at=2)
    application = facade(scout, editor)
    with pytest.raises(DesktopApplicationExecutionError) as sink_failure:
        application.run_scout(request=request, progress_sink=sink)
    _assert_recursive_isolation(
        sink_failure.value, (request, scout, editor, sink, application)
    )


def test_recursive_object_safety_failure_isolation() -> None:
    request = scout_request()
    object.__setattr__(request, "period_days", 30)
    for operation in (repr, copy.copy, copy.deepcopy):
        with pytest.raises(DesktopApplicationConfigurationError) as captured:
            operation(request)
        _assert_recursive_isolation(captured.value, (request,))

    application = facade()
    copied_invalid = facade()
    object.__setattr__(copied_invalid, "_scout_operation", ScoutOperation())
    with pytest.raises(DesktopApplicationConfigurationError) as captured:
        _ = application == copied_invalid
    _assert_recursive_isolation(captured.value, (application, copied_invalid))


@pytest.mark.parametrize(
    "control", [KeyboardInterrupt(), SystemExit(), GeneratorExit()]
)
def test_process_control_exceptions_propagate(control: BaseException) -> None:
    with pytest.raises(type(control)):
        facade(ScoutOperation(error=control)).run_scout(
            request=scout_request(), progress_sink=Sink()
        )


@pytest.mark.parametrize(
    "invalid_type",
    ["positional", "extra", "classmethod", "staticmethod", "property"],
)
def test_dependency_shape_rejected_without_body_execution(invalid_type: str) -> None:
    calls = []

    def body(*args, **kwargs):
        calls.append((args, kwargs))

    if invalid_type == "positional":
        member = lambda self, request: body(self, request)
    elif invalid_type == "extra":
        member = lambda self, *, request, extra=None: body(request, extra)
    elif invalid_type == "classmethod":
        member = classmethod(lambda cls, *, request: body(cls, request))
    elif invalid_type == "staticmethod":
        member = staticmethod(lambda *, request: body(request))
    else:
        member = property(lambda self: body(self))
    bad_type = type("BadScout", (), {"run_scout": member})
    with pytest.raises(DesktopApplicationConfigurationError):
        DesktopApplicationFacadeV1(
            scout_operation=bad_type(), editor_operation=EditorOperation()
        )
    assert calls == []


def test_forged_wrapping_instance_replacement_and_substitution_are_rejected() -> None:
    scout = ScoutOperation()
    scout.run_scout = lambda *, request: scout_result()  # type: ignore[method-assign]
    with pytest.raises(DesktopApplicationConfigurationError):
        facade(scout)
    scout = ScoutOperation()
    ScoutOperation.run_scout.__wrapped__ = ScoutOperation.run_scout  # type: ignore[attr-defined]
    try:
        with pytest.raises(DesktopApplicationConfigurationError):
            facade(scout)
    finally:
        del ScoutOperation.run_scout.__wrapped__  # type: ignore[attr-defined]
    ScoutOperation.run_scout.__signature__ = inspect.Signature()  # type: ignore[attr-defined]
    try:
        with pytest.raises(DesktopApplicationConfigurationError):
            facade(ScoutOperation())
    finally:
        del ScoutOperation.run_scout.__signature__  # type: ignore[attr-defined]
    valid = facade()
    object.__setattr__(valid, "_scout_operation", ScoutOperation())
    with pytest.raises(DesktopApplicationConfigurationError):
        valid.run_scout(request=scout_request(), progress_sink=Sink())


def test_dynamic_attribute_hooks_missing_methods_and_invalid_sink_are_rejected() -> (
    None
):
    class DynamicScout(ScoutOperation):
        def __getattribute__(self, name: str) -> object:
            return object.__getattribute__(self, name)

    class MissingScout:
        pass

    class DynamicFallbackScout(ScoutOperation):
        def __getattr__(self, name: str) -> object:
            raise AttributeError(name)

    class InvalidSink:
        publish = staticmethod(lambda *, event: None)

    for dependency in (DynamicScout(), DynamicFallbackScout(), MissingScout()):
        with pytest.raises(DesktopApplicationConfigurationError):
            facade(dependency)  # type: ignore[arg-type]
    scout = ScoutOperation()
    with pytest.raises(DesktopApplicationConfigurationError):
        facade(scout).run_scout(
            request=scout_request(), progress_sink=InvalidSink()  # type: ignore[arg-type]
        )
    assert scout.calls == []


def test_facade_equality_never_invokes_dependency_equality_hooks() -> None:
    calls = []

    class EqualityScout(ScoutOperation):
        def __eq__(self, other: object) -> bool:
            calls.append(other)
            raise AssertionError("dependency equality executed")

    scout = EqualityScout()
    editor = EditorOperation()
    first = facade(scout, editor)
    second = facade(scout, editor)
    assert first == second
    assert first != facade(EqualityScout(), editor)
    assert calls == []


def test_facade_object_safety_uses_dependency_identity_without_hooks() -> None:
    scout = ScoutOperation()
    editor = EditorOperation()
    value = facade(scout, editor)
    assert repr(value) == "DesktopApplicationFacadeV1(dependencies=<injected>)"
    assert value == copy.copy(value) == copy.deepcopy(value)
    assert value != facade(ScoutOperation(), editor)
    with pytest.raises(TypeError):
        pickle.dumps(value)


def test_passive_import_and_forbidden_import_graph() -> None:
    root = Path(__file__).resolve().parents[1]
    package = root / "src/pastila_scout/desktop_application_v1"
    forbidden = {
        "argparse",
        "sqlite3",
        "socket",
        "subprocess",
        "tkinter",
        "pastila_scout.provider_execution_openai_v2",
        "pastila_scout.provider_execution_ollama_v1",
        "pastila_scout.editor_generation_runtime_v1",
    }
    imports = set()
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    assert not any(
        imported == denied or imported.startswith(f"{denied}.")
        for imported in imports
        for denied in forbidden
    )
    probe = subprocess.run(
        [sys.executable, "-I", "-c", "import pastila_scout.desktop_application_v1"],
        cwd=root,
        env={"PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr


def test_construction_is_passive_under_denied_runtime_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args, **kwargs):
        del args, kwargs
        raise AssertionError("passive construction touched a runtime boundary")

    monkeypatch.setattr(os, "getenv", denied)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(sqlite3, "connect", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(threading.Thread, "start", denied)
    value = facade(ScoutOperation(), EditorOperation())
    assert repr(value) == "DesktopApplicationFacadeV1(dependencies=<injected>)"


def test_scope_cardinality_and_frozen_specifications() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = "phase-5.1a-desktop-application-facade-spec-v1-ready"
    verified = "phase-5.1b-desktop-application-facade-r1-verified"
    production = {
        "src/pastila_scout/desktop_application_v1/__init__.py",
        "src/pastila_scout/desktop_application_v1/errors.py",
        "src/pastila_scout/desktop_application_v1/models.py",
        "src/pastila_scout/desktop_application_v1/services.py",
    }
    focused_test = "tests/test_desktop_application_v1.py"
    required_hashes = {
        "src/pastila_scout/desktop_application_v1/__init__.py": (
            "E497311162A5F00FE9141805E8FD48F2829483D206EE104D2FF1872B8D6692E5"
        ),
        "src/pastila_scout/desktop_application_v1/errors.py": (
            "191E87DFFF5CAE4BB980E376EC56139DF1D4AB0E72A127689F2DD0AFE43D7A6D"
        ),
        "src/pastila_scout/desktop_application_v1/models.py": (
            "4DEDC9462E85D56383BCFCD15CE1B05D67C5E5A6D10E76F57F88A5E445C48BBD"
        ),
        "src/pastila_scout/desktop_application_v1/services.py": (
            "0D789E87433F21E12C85FCBDACF55A722D7C23B8F13F0A3A81326E6EB2B410E7"
        ),
        "tests/test_desktop_application_v1.py": (
            "D94F1B6012C97DD2CA182E04E44B6FB0B9E0763FD23B57AFA217D34632484782"
        ),
    }

    def names(*arguments: str) -> set[str]:
        return {
            item.replace("\\", "/")
            for item in subprocess.run(
                ["git", *arguments],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        }

    def phase_production(paths: set[str]) -> set[str]:
        prefix = "src/pastila_scout/desktop_application_v1/"
        return {path for path in paths if path.startswith(prefix)}

    assert (
        subprocess.run(
            ["git", "rev-parse", f"{baseline}^{{}}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        == "73823596b0131deb0234c610e5f73daf18422f7e"
    )
    assert (
        subprocess.run(
            ["git", "rev-parse", f"{verified}^{{}}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        == "64ae9c9ddf26797e3fe887b28d86c1352bd411f6"
    )
    assert names("diff", "--cached", "--name-only") == set()
    historical_delta = names("diff", "--name-only", f"{verified}^", verified)
    assert phase_production(historical_delta) == production
    assert historical_delta - production == {focused_test}
    for path, expected_hash in required_hashes.items():
        historical = subprocess.run(
            ["git", "show", f"{verified}:{path}"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(historical).hexdigest().upper() == expected_hash
    hypothetical_future = historical_delta | {
        "src/pastila_scout/future_phase_v1/service.py"
    }
    assert phase_production(hypothetical_future) == production
    hypothetical_expansion = historical_delta | {
        "src/pastila_scout/desktop_application_v1/unauthorized.py"
    }
    assert phase_production(hypothetical_expansion) != production
    historical_specification = subprocess.run(
        [
            "git",
            "show",
            f"{baseline}:docs/windows-application/DesktopApplicationFacadeSpecificationV1.md",
        ],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    assert hashlib.sha256(historical_specification).hexdigest().upper() == (
        "DB992030BA19FD2C80F6DA7627D3CEC8F4FC2DB9634A5F9892527C4E37FBCD7E"
    )
