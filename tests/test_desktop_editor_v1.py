from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import pickle
import subprocess
import sys
from pathlib import Path

import pytest
from test_editor_application_contracts_v1 import request as application_request
from test_editor_application_v1 import coordinator, dependencies

import pastila_scout.desktop_editor_v1 as package
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
    DesktopApplicationFacadeV1,
    EditorDesktopRequestV1,
    EditorDesktopResultV1,
)
from pastila_scout.desktop_editor_v1 import composition
from pastila_scout.desktop_editor_v1.models import (
    _DesktopApplicationCompositionErrorV1,
)
from pastila_scout.desktop_editor_v1.service import _EditorDesktopOperationV1
from pastila_scout.editor_application_v1 import (
    EditorApplicationCoordinatorV1,
    EditorApplicationResultV1,
    EditorApplicationStatusV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "src" / "pastila_scout" / "desktop_editor_v1"
SPEC = (
    ROOT / "docs" / "windows-application" / "EditorDesktopIntegrationSpecificationV1.md"
)


def _compose():
    return composition._compose_desktop_application_facade_v1(
        config_path=Path("config/config.yaml"),
        sources_path=Path("config/sources.yaml"),
        database_path=Path("data/news_monitor.db"),
        report_directory=Path("reports"),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _operation(tmp_path, monkeypatch, *, failed=False):
    app_request, values, calls, _ = dependencies(tmp_path, monkeypatch, failed=failed)
    application = coordinator(values)
    return (
        _EditorDesktopOperationV1(application=application),
        application,
        EditorDesktopRequestV1(application_request=app_request),
        calls,
    )


def test_exact_private_layout_exports_and_signatures() -> None:
    assert package.__all__ == ()
    assert {path.name for path in PRODUCTION.iterdir() if path.suffix == ".py"} == {
        "__init__.py",
        "models.py",
        "service.py",
        "composition.py",
    }
    assert (
        inspect.signature(_EditorDesktopOperationV1).parameters["application"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    run = inspect.signature(_EditorDesktopOperationV1.run_editor)
    assert tuple(run.parameters) == ("self", "request")
    assert run.parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY
    assert tuple(
        inspect.signature(composition._compose_desktop_application_facade_v1).parameters
    ) == ("config_path", "sources_path", "database_path", "report_directory")
    with pytest.raises(TypeError):

        class Invalid(_EditorDesktopOperationV1):
            pass


def test_editor_operation_preserves_request_result_and_cardinality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation, application, request, calls = _operation(tmp_path, monkeypatch)
    seen: list[EditorApplicationResultV1] = []
    original = EditorApplicationCoordinatorV1.execute

    def execute(self, *, request):
        assert self is application
        result = original(self, request=request)
        seen.append(result)
        return result

    monkeypatch.setattr(EditorApplicationCoordinatorV1, "execute", execute)
    result = operation.run_editor(request=request)
    assert type(result) is EditorDesktopResultV1
    assert result.application_result == seen[0]
    assert (
        result.application_result.operation_reference
        == request.application_request.operation_reference
    )
    assert calls.count("execute") == 1


@pytest.mark.parametrize("failed", [False, True])
def test_editor_operation_preserves_completed_and_failed_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed: bool
) -> None:
    operation, _, request, calls = _operation(tmp_path, monkeypatch, failed=failed)
    result = operation.run_editor(request=request).application_result
    assert result.operation_reference == request.application_request.operation_reference
    assert calls.count("execute") == 1


def test_already_cancelled_request_is_passed_to_lower_authority_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation, application, _, _ = _operation(tmp_path, monkeypatch)
    nested = application_request(
        tmp_path,
        operation_reference="cancelled-operation",
        cancellation=CancellationTokenV2(cancellation_requested=True),
    )
    request = EditorDesktopRequestV1(application_request=nested)
    token = nested.cancellation
    seen = []
    original = EditorApplicationCoordinatorV1.execute

    def execute(self, *, request):
        seen.append(request.cancellation)
        return original(self, request=request)

    monkeypatch.setattr(EditorApplicationCoordinatorV1, "execute", execute)
    result = operation.run_editor(request=request)
    assert seen == [token]
    assert result.application_result.status is EditorApplicationStatusV1.CANCELLED
    assert application is object.__getattribute__(operation, "_application")


def test_wrong_reference_and_invalid_return_are_configuration_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation, _, request, _ = _operation(tmp_path, monkeypatch)

    def wrong_type(self, *, request):
        del self, request
        return object()

    monkeypatch.setattr(EditorApplicationCoordinatorV1, "execute", wrong_type)
    with pytest.raises(DesktopApplicationConfigurationError):
        operation.run_editor(request=request)


def test_invalid_inputs_and_retained_state_fail_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation, _, request, calls = _operation(tmp_path, monkeypatch)
    with pytest.raises(DesktopApplicationConfigurationError):
        operation.run_editor(request=object())  # type: ignore[arg-type]
    object.__setattr__(operation, "_identity", -1)
    with pytest.raises(DesktopApplicationConfigurationError):
        operation.run_editor(request=request)
    assert "execute" not in calls
    with pytest.raises(DesktopApplicationConfigurationError):
        _EditorDesktopOperationV1(application=object())  # type: ignore[arg-type]


def test_lower_exception_is_safe_and_process_control_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation, _, request, _ = _operation(tmp_path, monkeypatch)

    def ordinary(self, *, request):
        del self, request
        raise RuntimeError("secret-provider-path")

    monkeypatch.setattr(EditorApplicationCoordinatorV1, "execute", ordinary)
    with pytest.raises(DesktopApplicationExecutionError) as caught:
        operation.run_editor(request=request)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert "secret" not in repr(caught.value)

    for error in (KeyboardInterrupt, SystemExit, GeneratorExit):

        def controlled(self, *, request, error=error):
            del self, request
            raise error

        monkeypatch.setattr(EditorApplicationCoordinatorV1, "execute", controlled)
        with pytest.raises(error):
            operation.run_editor(request=request)


def test_composition_error_is_fixed_final_and_nontransportable() -> None:
    error = _DesktopApplicationCompositionErrorV1()
    assert str(error) == "Desktop application composition failed."
    assert "Desktop application composition failed." in repr(error)
    with pytest.raises(TypeError):

        class Invalid(_DesktopApplicationCompositionErrorV1):
            pass

    for action in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            action(error)


def test_composer_constructs_exact_graph_in_exact_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class Report:
        def __init__(self, **kwargs):
            calls.append(("report", kwargs))

    class Scout:
        def __init__(self, **kwargs):
            calls.append(("scout", kwargs))

    class Editor:
        def __init__(self, **kwargs):
            calls.append(("editor", kwargs))

    class Facade:
        def __init__(self, **kwargs):
            calls.append(("facade", kwargs))

    application = object()
    monkeypatch.setattr(composition, "_DesktopReportFacadeV1", Report)
    monkeypatch.setattr(composition, "_ScoutDesktopOperationV1", Scout)
    monkeypatch.setattr(
        composition, "_compose_editor_application_runtime_v1", lambda: application
    )
    monkeypatch.setattr(composition, "_EditorDesktopOperationV1", Editor)
    monkeypatch.setattr(composition, "DesktopApplicationFacadeV1", Facade)
    facade = _compose()
    assert [name for name, _ in calls] == ["report", "scout", "editor", "facade"]
    report, scout, editor, facade_call = (values for _, values in calls)
    assert report == {
        "report_directory": Path("reports"),
        "opener": composition._open_desktop_report_v1,
    }
    assert scout["config_path"] == Path("config/config.yaml")
    assert scout["database_path"] == Path("data/news_monitor.db")
    assert editor["application"] is application
    assert facade is not None
    assert facade_call["scout_operation"].__class__ is Scout
    assert facade_call["editor_operation"].__class__ is Editor
    assert facade_call["report_operation"].__class__ is Report
    assert scout["report_facade"] is facade_call["report_operation"]


def test_composer_is_fresh_and_report_identity_is_shared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, values, _, _ = dependencies(tmp_path, monkeypatch)
    monkeypatch.setattr(
        composition,
        "_compose_editor_application_runtime_v1",
        lambda: coordinator(values),
    )
    first = _compose()
    second = _compose()
    assert type(first) is DesktopApplicationFacadeV1
    assert first is not second
    first_scout = object.__getattribute__(first, "_scout_operation")
    first_report = object.__getattribute__(first, "_report_operation")
    assert object.__getattribute__(first_scout, "_report_facade") is first_report
    assert object.__getattribute__(
        first, "_editor_operation"
    ) is not object.__getattribute__(second, "_editor_operation")


@pytest.mark.parametrize(
    "name",
    [
        "_DesktopReportFacadeV1",
        "_ScoutDesktopOperationV1",
        "_compose_editor_application_runtime_v1",
        "_EditorDesktopOperationV1",
        "DesktopApplicationFacadeV1",
    ],
)
def test_every_composition_failure_is_reduced_safely(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    def fail(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("secret-configuration")

    monkeypatch.setattr(composition, name, fail)
    with pytest.raises(_DesktopApplicationCompositionErrorV1) as caught:
        _compose()
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert "secret" not in repr(caught.value)


def test_composition_process_control_exceptions_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for error in (KeyboardInterrupt, SystemExit, GeneratorExit):

        def controlled(*args, error=error, **kwargs):
            del args, kwargs
            raise error

        monkeypatch.setattr(composition, "_DesktopReportFacadeV1", controlled)
        with pytest.raises(error):
            _compose()


def test_composition_constructs_without_executing_any_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Passive:
        def __init__(self, **kwargs):
            self.values = kwargs

        def run_scout(self, **kwargs):
            del kwargs
            raise AssertionError("Scout executed during composition")

        def run_editor(self, **kwargs):
            del kwargs
            raise AssertionError("Editor executed during composition")

        def open_report(self, **kwargs):
            del kwargs
            raise AssertionError("report opened during composition")

    monkeypatch.setattr(composition, "_DesktopReportFacadeV1", Passive)
    monkeypatch.setattr(composition, "_ScoutDesktopOperationV1", Passive)
    monkeypatch.setattr(
        composition, "_compose_editor_application_runtime_v1", lambda: object()
    )
    monkeypatch.setattr(composition, "_EditorDesktopOperationV1", Passive)
    monkeypatch.setattr(composition, "DesktopApplicationFacadeV1", Passive)
    assert type(_compose()) is Passive


def test_phase_5_3d_can_bind_all_three_facade_operations_without_redesign() -> None:
    composer = inspect.signature(composition._compose_desktop_application_facade_v1)
    assert composer.return_annotation in (
        DesktopApplicationFacadeV1,
        "DesktopApplicationFacadeV1",
    )
    scout = inspect.signature(DesktopApplicationFacadeV1.run_scout)
    editor = inspect.signature(DesktopApplicationFacadeV1.run_editor)
    report = inspect.signature(DesktopApplicationFacadeV1.open_report)
    assert tuple(scout.parameters) == ("self", "request", "progress_sink")
    assert tuple(editor.parameters) == ("self", "request", "progress_sink")
    assert tuple(report.parameters) == ("self", "reference")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for signature in (scout, editor, report)
        for parameter in tuple(signature.parameters.values())[1:]
    )


def test_report_opener_is_exact_and_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(composition.os, "startfile", lambda path: calls.append(path))
    path = Path("report.html")
    assert composition._open_desktop_report_v1(path) is None
    assert calls == [path]
    with pytest.raises(TypeError):
        composition._open_desktop_report_v1(object())  # type: ignore[arg-type]


def test_imports_are_passive_and_forbidden_ownership_is_absent() -> None:
    forbidden = {"tkinter", "concurrent", "argparse", "subprocess", "sqlite3"}
    forbidden_fragments = ("openai", "ollama", "desktop_v1", "editor_cli")
    for path in PRODUCTION.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.names[0].name if isinstance(node, ast.Import) else node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        assert not forbidden.intersection(imports)
        assert not any(
            fragment in name for name in imports for fragment in forbidden_fragments
        )
    code = "import pastila_scout.desktop_editor_v1; import pastila_scout.desktop_editor_v1.composition"
    completed = subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=False)
    assert completed.returncode == 0


def test_frozen_authorities_and_historical_scope_are_exact() -> None:
    expected = {
        SPEC: "72B6C99E83E966E5D0E35D944C07DF062405751C91B377647A1F384F6270B1E2",
        ROOT
        / "docs/windows-application/DesktopApplicationFacadeSpecificationV1.md": "E7731DA45C34FCF9188A5974D2B8C41C0183ADCEC275333948BA560D8C32ABF0",
        ROOT
        / "docs/windows-application/DesktopShellSpecificationV1.md": "5B565CAC42AFDEB0E426B078FBC2A5C7F2836C73A4D64F723AA029787FF9AAFB",
        ROOT
        / "docs/windows-application/ScoutDesktopIntegrationSpecificationV1.md": "2DEFA01281326D99633DAEE0FA4DF017911C9E87C7B7ED767BB3FDEE585A8DD1",
        ROOT
        / "docs/windows-update/WindowsUpdateProtocolSpecificationV1.md": "9E4615576785062A5C902CA8BBA663EE1F9BF1112F98ED881F7620B0CAD568ED",
        ROOT
        / "docs/windows-update/WindowsUpdatePersistenceFormatSpecificationV1.md": "05CF922678BD9DCD4C6837B00B8896CA7A014D839C84290A7B5D70F54158DFF6",
    }
    assert {path: _sha256(path) for path in expected} == expected
    productization = (
        "docs/windows-application/WindowsDesktopProductizationSpecificationV1.md"
    )
    historical_blob = subprocess.check_output(
        ["git", "show", f"phase-5.3a-editor-desktop-spec-v1-ready:{productization}"],
        cwd=ROOT,
    )
    assert hashlib.sha256(historical_blob).hexdigest().upper() == (
        "A156A3963253ADEE7A2540B337FD358C33328219DABC0FF4803E9EF318882A3E"
    )
    v12_tag = "phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready"
    assert (
        subprocess.check_output(
            ["git", "cat-file", "-t", v12_tag], cwd=ROOT, text=True
        ).strip()
        == "tag"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{v12_tag}^{{}}"], cwd=ROOT, text=True
        ).strip()
        == "dbda63533033aa25fe2ea2e970f6943851056078"
    )
    v12_blob = subprocess.check_output(
        ["git", "show", f"{v12_tag}:{productization}"], cwd=ROOT
    )
    assert hashlib.sha256(v12_blob).hexdigest().upper() == (
        "556ECE4D3D64C163CC42B17BD0431A424FB06CFA89011BBCF89EC151EE0D593C"
    )
    maintenance_tag = (
        "phase-5-productization-single-owner-trust-policy-maintenance-r1-verified"
    )
    assert (
        subprocess.check_output(
            ["git", "cat-file", "-t", maintenance_tag], cwd=ROOT, text=True
        ).strip()
        == "tag"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{maintenance_tag}^{{}}"], cwd=ROOT, text=True
        ).strip()
        == "1b8ef121b4ff5d147b069d91a68c33156c51f3a6"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{maintenance_tag}^{{}}^"], cwd=ROOT, text=True
        ).strip()
        == "556ee1a3269329dd78745e2f6bbf8e96dfc5ac07"
    )
    maintained_blob = subprocess.check_output(
        ["git", "show", f"{maintenance_tag}:{productization}"], cwd=ROOT
    )
    assert hashlib.sha256(maintained_blob).hexdigest().upper() == (
        "D73BC2B477CE0BAE00376420CB24F7393D44A251FFA9B4E204B1C5D8DEEF9B70"
    )
    assert maintained_blob == (ROOT / productization).read_bytes()
    assert historical_blob != v12_blob
    assert v12_blob != maintained_blob
    with pytest.raises(AssertionError):
        assert hashlib.sha256(historical_blob + b"mutation").hexdigest().upper() == (
            "A156A3963253ADEE7A2540B337FD358C33328219DABC0FF4803E9EF318882A3E"
        )
    assert (
        subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True
        ).strip()
        == ""
    )
    baseline = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            "phase-5.3a-editor-desktop-spec-v1-ready",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert not any(
        path.startswith("src/pastila_scout/desktop_editor_v1/") for path in baseline
    )
