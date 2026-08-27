from __future__ import annotations

import copy
import inspect
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import get_type_hints

import pytest

from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationAuthorityError,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeCompositionError,
    EditorGenerationRuntimeSessionFactoryV1,
    EditorGenerationRuntimeSessionV1,
)
from pastila_scout.editor_generation_runtime_v1.composition import (
    _EditorScoutWorkflowFactoryV1,
    _NonOperationalProviderExecutorV2,
    _OllamaRuntimeSessionFactoryV1,
)
from pastila_scout.editor_core_identities_v1 import (
    CORE_V1_1_MODEL_ID,
    CORE_V1_2_MODEL_ID,
)
from pastila_scout.editor_generation_runtime_v1.models import (
    EditorAdapterDependenciesV1,
    EditorOllamaRuntimeHandleV1,
    _EditorGenerationAttemptRecorderV1,
)
from pastila_scout.editor_generation_runtime_v1.protocols import (
    EditorGenerationAttemptRecorderV1,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeConfigV2,
)
from pastila_scout.provider_runtime_openai_v2.composition import _mint_factory_handoff
from pastila_scout.provider_runtime_openai_v2.production import (
    _ExplicitOpenAICredentialSourceV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)


class _Executor:
    calls = 0

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        del request
        type(self).calls += 1
        raise AssertionError("creation must not execute")


class _Lifecycle:
    closes = 0

    def close(self) -> None:
        type(self).closes += 1


class _OpenAIFactory:
    calls = 0

    def create(
        self, *, model_identifier: str, timeout_seconds: int | float  # noqa: PYI041
    ) -> OpenAIRuntimeComposerV2:
        del model_identifier, timeout_seconds
        type(self).calls += 1
        raise AssertionError("unselected OpenAI must remain untouched")


class _Responses:
    def create(self, **arguments: object) -> object:
        del arguments
        raise AssertionError("runtime construction must not execute a provider request")


class _RawOpenAIClient:
    def __init__(self) -> None:
        self.responses = _Responses()
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class _OperationalOpenAIFactory:
    calls = 0
    raw_client = _RawOpenAIClient()

    class SDKFactory:
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            del self, api_key, max_retries, request_timeout_seconds
            return _mint_factory_handoff(_OperationalOpenAIFactory.raw_client)

        def close_client(self, client: object) -> None:
            client.close()

    def create(
        self, *, model_identifier: str, timeout_seconds: int | float  # noqa: PYI041
    ) -> OpenAIRuntimeComposerV2:
        type(self).calls += 1
        return OpenAIRuntimeComposerV2(
            OpenAIRuntimeConfigV2(
                model=model_identifier, request_timeout_seconds=timeout_seconds
            ),
            credential_source=_ExplicitOpenAICredentialSourceV2("valid-key"),
            sdk_factory=self.SDKFactory(),
        )


class _OllamaFactory:
    calls = 0

    def open(
        self, options: EditorGenerationRuntimeOptionsV1
    ) -> EditorOllamaRuntimeHandleV1:
        assert options.provider is ProviderChoiceV1.OLLAMA
        type(self).calls += 1
        return EditorOllamaRuntimeHandleV1(_Executor(), _Lifecycle())


class _Legacy:
    calls = 0

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        del request
        type(self).calls += 1
        raise AssertionError("legacy execution must remain untouched")


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)


class _Cancellation:
    def snapshot(self) -> CancellationTokenV2:
        return CancellationTokenV2(cancellation_requested=False)


class _References:
    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str:
        return f"{prompt_fingerprint}:{attempt_number}"


class _AdapterFactory:
    calls = 0
    recorder = _EditorGenerationAttemptRecorderV1()

    def create(self, *, operation_reference: str) -> EditorAdapterDependenciesV1:
        assert operation_reference == "editor-operation-1"
        type(self).calls += 1
        return EditorAdapterDependenciesV1(
            _Clock(), _Cancellation(), _References(), type(self).recorder
        )


@pytest.fixture(autouse=True)
def _reset_counts():
    _Executor.calls = 0
    _Lifecycle.closes = 0
    _OpenAIFactory.calls = 0
    _OperationalOpenAIFactory.calls = 0
    _OperationalOpenAIFactory.raw_client = _RawOpenAIClient()
    _OllamaFactory.calls = 0
    _Legacy.calls = 0
    _AdapterFactory.calls = 0
    _AdapterFactory.recorder = _EditorGenerationAttemptRecorderV1()


def _factory() -> EditorGenerationRuntimeSessionFactoryV1:
    return EditorGenerationRuntimeSessionFactoryV1(
        openai_composer_factory=_OpenAIFactory(),
        ollama_session_factory=_OllamaFactory(),
        legacy_workflow=_Legacy(),
        adapter_dependency_factory=_AdapterFactory(),
        fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
    )


def _options() -> EditorGenerationRuntimeOptionsV1:
    return EditorGenerationRuntimeOptionsV1(
        ProviderChoiceV1.OLLAMA,
        "qwen3:14b",
        None,
        0.3,
        1,
        128,
        None,
        (),
        True,
        TimeoutPolicyV2(timeout_seconds=30),
    )


def _options_for_model(model_identifier: str) -> EditorGenerationRuntimeOptionsV1:
    return EditorGenerationRuntimeOptionsV1(
        ProviderChoiceV1.OLLAMA,
        model_identifier,
        None,
        0.3,
        1,
        128,
        None,
        (),
        True,
        TimeoutPolicyV2(timeout_seconds=30),
    )


def test_exact_public_api_and_layout():
    import pastila_scout.editor_generation_runtime_v1 as runtime

    assert runtime.__all__ == (
        "EditorGenerationRuntimeCompositionError",
        "EditorGenerationRuntimeSessionFactoryV1",
        "EditorGenerationRuntimeSessionV1",
    )
    assert not hasattr(runtime, "_NonOperationalProviderExecutorV2")
    assert not hasattr(runtime, "_EditorScoutWorkflowFactoryV1")
    assert set(
        inspect.signature(EditorGenerationRuntimeSessionFactoryV1).parameters
    ) == {
        "openai_composer_factory",
        "ollama_session_factory",
        "legacy_workflow",
        "adapter_dependency_factory",
        "fingerprint_authority",
    }
    package = Path(runtime.__file__).parent
    assert sorted(path.name for path in package.glob("*.py")) == [
        "__init__.py",
        "composition.py",
        "errors.py",
        "models.py",
        "protocols.py",
    ]
    assert not hasattr(EditorGenerationRuntimeSessionV1, "__enter__")
    assert not hasattr(EditorGenerationRuntimeSessionV1, "__exit__")


def test_attempt_recorder_has_exact_normative_annotation_and_property_shape():
    descriptor = inspect.getattr_static(
        EditorGenerationRuntimeSessionV1, "attempt_recorder"
    )
    assert type(descriptor) is property
    assert descriptor.fget is not None
    assert not hasattr(descriptor.fget, "__signature__")
    assert (
        get_type_hints(descriptor.fget)["return"] is EditorGenerationAttemptRecorderV1
    )
    assert tuple(EditorGenerationRuntimeSessionV1.__slots__) == (
        "_workflow",
        "_runtime_authority",
        "_adapter",
        "_attempt_recorder",
        "_operation_reference",
        "_lifecycle",
        "_closed",
    )


def test_factory_construction_is_passive_and_object_safe():
    factory = _factory()
    assert _OpenAIFactory.calls == _OllamaFactory.calls == 0
    assert _Executor.calls == _Legacy.calls == _Lifecycle.closes == 0
    assert "_EditorScoutWorkflowFactoryV1" not in factory.__slots__
    assert copy.copy(factory) == factory
    assert copy.deepcopy(factory) == factory
    assert "0x" not in repr(factory)
    with pytest.raises(TypeError):
        pickle.dumps(factory)


def test_ollama_open_builds_one_inert_path_and_no_execution():
    session = _factory().open(_options(), operation_reference="editor-operation-1")
    assert type(session) is EditorGenerationRuntimeSessionV1
    assert _OpenAIFactory.calls == 0
    assert _OllamaFactory.calls == 1
    assert _AdapterFactory.calls == 1
    assert _Executor.calls == _Legacy.calls == 0
    assert session.attempt_recorder is _AdapterFactory.recorder
    assert session.attempt_recorder.snapshot() == ()
    assert session.adapter._recorder is session.attempt_recorder
    assert session.adapter._workflow is session.workflow
    assert session.adapter._runtime is session.runtime_authority
    assert session.operation_reference == "editor-operation-1"
    assert session.is_closed is False
    session.close()
    assert session.is_closed is True
    assert _Lifecycle.closes == 1
    with pytest.raises(EditorGenerationRuntimeCompositionError, match="already closed"):
        session.close()
    assert _Lifecycle.closes == 1


def test_ordinary_ollama_routing_does_not_import_experimental_executors(monkeypatch):
    from pastila_scout.editor_generation_runtime_v1 import composition

    imported = []
    original = composition.import_module

    def observed(name):
        imported.append(name)
        assert not name.startswith("pastila_scout.experimental_core_v1_")
        return original(name)

    monkeypatch.setattr(composition, "import_module", observed)
    handle = _OllamaRuntimeSessionFactoryV1().open(_options())
    handle.lifecycle.close()

    assert "pastila_scout.provider_execution_ollama_v1" in imported


@pytest.mark.parametrize(
    ("model_identifier", "module_name", "expected_tokens"),
    (
        (CORE_V1_1_MODEL_ID, "pastila_scout.experimental_core_v1_1", None),
        (CORE_V1_2_MODEL_ID, "pastila_scout.experimental_core_v1_2", 128),
    ),
)
def test_experimental_routing_imports_only_exact_selected_executor(
    monkeypatch, model_identifier, module_name, expected_tokens
):
    from pastila_scout.editor_generation_runtime_v1 import composition

    constructed = []

    class FakeExecutor:
        def __init__(self, **kwargs):
            constructed.append(kwargs)

        def execute(self, request):
            raise AssertionError("construction must not execute")

    fake_module = type(
        "ExperimentalModule",
        (),
        {
            "ExperimentalCoreV11Executor": FakeExecutor,
            "ExperimentalCoreV12Executor": FakeExecutor,
        },
    )
    imported = []
    original = composition.import_module

    def selected(name):
        imported.append(name)
        if name == module_name:
            return fake_module
        assert not name.startswith("pastila_scout.experimental_core_v1_")
        return original(name)

    monkeypatch.setattr(composition, "import_module", selected)
    handle = _OllamaRuntimeSessionFactoryV1().open(
        _options_for_model(model_identifier)
    )
    handle.lifecycle.close()

    assert imported.count(module_name) == 1
    assert len(constructed) == 1
    assert constructed[0].get("max_output_tokens") == expected_tokens


def test_experimental_routing_closes_client_on_late_construction_failure(monkeypatch):
    from pastila_scout.editor_generation_runtime_v1 import composition

    class FakeExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def execute(self, request):
            raise AssertionError("construction must not execute")

    class FakeClient:
        instances = []

        def __init__(self):
            self.closed = False
            type(self).instances.append(self)

        def close(self):
            self.closed = True

    fake_module = type(
        "ExperimentalModule", (), {"ExperimentalCoreV12Executor": FakeExecutor}
    )
    original = composition.import_module
    monkeypatch.setattr(
        composition,
        "import_module",
        lambda name: fake_module
        if name == "pastila_scout.experimental_core_v1_2"
        else original(name),
    )
    monkeypatch.setattr(composition, "_httpx_client_type", lambda: FakeClient)
    monkeypatch.setattr(
        composition,
        "_OllamaRuntimeLifecycleV1",
        lambda client: (_ for _ in ()).throw(RuntimeError("late failure")),
    )

    with pytest.raises(EditorGenerationRuntimeCompositionError):
        _OllamaRuntimeSessionFactoryV1().open(_options_for_model(CORE_V1_2_MODEL_ID))

    assert len(FakeClient.instances) == 1
    assert FakeClient.instances[0].closed is True


def test_private_workflow_and_inert_executor_are_passive():
    workflow_factory = _EditorScoutWorkflowFactoryV1(legacy_workflow=_Legacy())
    assert copy.copy(workflow_factory) is workflow_factory
    assert copy.deepcopy(workflow_factory) is workflow_factory
    with pytest.raises(TypeError):
        pickle.dumps(workflow_factory)
    inert = _NonOperationalProviderExecutorV2(provider=ProviderChoiceV1.OPENAI)
    assert copy.copy(inert) is inert
    assert copy.deepcopy(inert) is inert
    assert "openai" in repr(inert)
    with pytest.raises(TypeError):
        pickle.dumps(inert)
    assert not hasattr(inert, "__dict__")
    assert not hasattr(workflow_factory, "__dict__")


def test_invalid_provider_options_and_invalid_dependencies_fail_closed():
    with pytest.raises(EditorGenerationRuntimeCompositionError):
        EditorGenerationRuntimeSessionFactoryV1(
            openai_composer_factory=object(),
            ollama_session_factory=_OllamaFactory(),
            legacy_workflow=_Legacy(),
            adapter_dependency_factory=_AdapterFactory(),
            fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
        )
    with pytest.raises(EditorGenerationAuthorityError):
        EditorGenerationRuntimeOptionsV1(
            "OLLAMA",
            "qwen3:14b",
            None,
            0.3,
            1,
            128,
            None,
            (),
            True,
            TimeoutPolicyV2(timeout_seconds=30),
        )


def test_recorder_rejects_gaps_without_mutation():
    recorder = _EditorGenerationAttemptRecorderV1()
    assert recorder.snapshot() == ()
    assert EditorGenerationAttemptObservationV1.__name__.endswith("V1")


def test_openai_selected_path_builds_one_session_without_execution(monkeypatch):
    del monkeypatch
    raw_client = _OperationalOpenAIFactory.raw_client
    options = EditorGenerationRuntimeOptionsV1(
        ProviderChoiceV1.OPENAI,
        "gpt-4.1-mini",
        None,
        0.3,
        1,
        128,
        None,
        (),
        True,
        TimeoutPolicyV2(timeout_seconds=30),
    )
    factory = EditorGenerationRuntimeSessionFactoryV1(
        openai_composer_factory=_OperationalOpenAIFactory(),
        ollama_session_factory=_OllamaFactory(),
        legacy_workflow=_Legacy(),
        adapter_dependency_factory=_AdapterFactory(),
        fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
    )
    session = factory.open(options, operation_reference="editor-operation-1")
    assert _OperationalOpenAIFactory.calls == 1
    assert _OllamaFactory.calls == 0
    assert _Executor.calls == _Legacy.calls == 0
    selected = session.workflow.runtime_bridge.composition.selector.executor
    assert selected.config.model == "gpt-4.1-mini"
    session.close()
    assert raw_client.close_calls == 1


@pytest.mark.parametrize(
    "stage", ("workflow_factory", "workflow", "authority", "adapter")
)
def test_atomic_rollback_for_late_construction_stages(monkeypatch, stage):
    from pastila_scout.editor_generation_runtime_v1 import composition

    failure = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unsafe"))
    if stage == "workflow_factory":
        monkeypatch.setattr(composition, "_EditorScoutWorkflowFactoryV1", failure)
    elif stage == "workflow":
        monkeypatch.setattr(
            composition._EditorScoutWorkflowFactoryV1, "create", failure
        )
    elif stage == "authority":
        monkeypatch.setattr(composition, "_runtime_authority", failure)
    else:
        monkeypatch.setattr(
            composition, "EditorNeutralLanguageModelProviderV1", failure
        )
    with pytest.raises(EditorGenerationRuntimeCompositionError) as caught:
        _factory().open(_options(), operation_reference="editor-operation-1")
    assert str(caught.value) == "Editor generation runtime composition failed."
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert _Lifecycle.closes == 1
    assert _Executor.calls == _Legacy.calls == 0


@pytest.mark.parametrize(
    "symbol",
    (
        "ProviderExecutorRegistrationV1",
        "ProviderSelectorV1",
        "ScoutRuntimeCompositionV1",
        "_EditorScoutWorkflowFactoryV1",
        "_runtime_authority",
        "EditorNeutralLanguageModelProviderV1",
        "EditorGenerationRuntimeSessionV1",
    ),
)
def test_stage_by_stage_failure_after_resource_acquisition_rolls_back(
    monkeypatch, symbol
):
    from pastila_scout.editor_generation_runtime_v1 import composition

    def failure(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("unsafe stage failure")

    monkeypatch.setattr(composition, symbol, failure)
    with pytest.raises(EditorGenerationRuntimeCompositionError) as caught:
        _factory().open(_options(), operation_reference="editor-operation-1")
    assert caught.value.args == ("Editor generation runtime composition failed.",)
    assert caught.value.__context__ is caught.value.__cause__ is None
    assert _Lifecycle.closes == 1
    assert _Executor.calls == _Legacy.calls == 0


@pytest.mark.parametrize(
    "dependency",
    (
        object(),
        property(lambda self: None),
        staticmethod(lambda: None),
        classmethod(lambda cls: None),
    ),
)
def test_dependency_shape_attacks_fail_without_invocation(dependency):
    with pytest.raises(EditorGenerationRuntimeCompositionError) as caught:
        EditorGenerationRuntimeSessionFactoryV1(
            openai_composer_factory=dependency,
            ollama_session_factory=_OllamaFactory(),
            legacy_workflow=_Legacy(),
            adapter_dependency_factory=_AdapterFactory(),
            fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
        )
    assert caught.value.args == ("Editor generation runtime composition failed.",)
    assert caught.value.__context__ is caught.value.__cause__ is None


def _package_traceback_values(error):
    values = []
    traceback = error.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
        if "/src/pastila_scout/editor_generation_runtime_v1/" in filename:
            values.extend(traceback.tb_frame.f_locals.values())
        traceback = traceback.tb_next
    return values


def test_recursive_traceback_isolation_for_open_cleanup_and_second_close(monkeypatch):
    sentinel = _Executor()

    class FailingLifecycle:
        def close(self) -> None:
            raise RuntimeError("unsafe lower cleanup")

    from pastila_scout.editor_generation_runtime_v1 import composition

    monkeypatch.setattr(
        composition,
        "_selected_runtime",
        lambda *args: (sentinel, FailingLifecycle()),
    )
    monkeypatch.setattr(
        composition,
        "_runtime_authority",
        lambda *args: (_ for _ in ()).throw(RuntimeError("unsafe lower")),
    )
    with pytest.raises(EditorGenerationRuntimeCompositionError) as caught:
        _factory().open(_options(), operation_reference="editor-operation-1")
    assert sentinel not in _package_traceback_values(caught.value)
    assert caught.value.__context__ is caught.value.__cause__ is None

    monkeypatch.undo()
    session = _factory().open(_options(), operation_reference="editor-operation-1")
    session.close()
    with pytest.raises(EditorGenerationRuntimeCompositionError) as closed:
        session.close()
    assert session not in _package_traceback_values(closed.value)
    assert closed.value.__context__ is closed.value.__cause__ is None


def test_passive_import_in_fresh_process():
    result = subprocess.run(
        [
            sys.executable,
            "-Werror",
            "-c",
            "import pastila_scout.editor_generation_runtime_v1",
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""
