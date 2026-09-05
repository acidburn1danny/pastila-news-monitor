from __future__ import annotations

import copy
import functools
import inspect
import pickle
import subprocess
import sys
from dataclasses import dataclass
from functools import cached_property
from types import SimpleNamespace

import pytest
from test_editor_generation_authority_v1 import execution_request

import pastila_scout.editor_operational_execution_v1 as public
import pastila_scout.editor_operational_execution_v1.coordinator as implementation
from pastila_scout.editor.generation.controlled_generator import (
    ControlledGenerationError,
    ControlledGenerator,
)
from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    ComponentAttemptTrace,
    ControlledGenerationResult,
    EpisodeDraft,
    GenerationComponentType,
    GenerationMode,
    GenerationTrace,
    LanguageGenerationConfig,
    ManifestItemStatus,
)
from pastila_scout.editor.generation.provider import LanguageModelProvider
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeSessionV1,
)
from pastila_scout.editor_operational_execution_v1.coordinator import (
    _groups,
    _timeout_exhausted,
    _validate_provenance,
    _validate_trace,
)
from pastila_scout.editor_operational_execution_v1.models import (
    GENERATION_FAILURE_LIFECYCLE,
    EditorOperationalGenerationFailureCodeV1,
    EditorOperationalGenerationStatusV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2

EXPECTED = (
    "EditorOperationalExecutionConfigurationError",
    "EditorOperationalExecutionCoordinatorV1",
    "EditorOperationalGenerationFailureCodeV1",
    "EditorOperationalGenerationFailureV1",
    "EditorOperationalGenerationLifecycleStateV1",
    "EditorOperationalGenerationStatusV1",
    "EditorOperationalResultV1",
    "replace_completed_draft_v1",
)


class SessionFactory:
    def __init__(self):
        self.calls = 0

    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> EditorGenerationRuntimeSessionV1:
        del options, operation_reference
        self.calls += 1
        raise AssertionError("must remain inert")


class GeneratorFactory:
    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> ControlledGenerator:
        del provider, config
        raise AssertionError("must remain inert")


def observation(number, prompt, outcome):
    completed = outcome is ExecutionOutcomeV2.COMPLETED
    return EditorGenerationAttemptObservationV1(
        number,
        f"sha256:{prompt * 64}",
        f"request-{number}",
        f"{number:064x}",
        f"execution-{number}",
        f"envelope-{number}",
        "openai",
        outcome,
        f"source-{number}" if completed else None,
        ProviderFinishReasonV2.COMPLETED if completed else None,
        None if completed else outcome.value,
    )


def trace_node(prompt, component, provider):
    return ComponentAttemptTrace(
        manifest_item_id=f"item-{prompt}",
        component_type=component,
        target_id="episode",
        attempt_number=1,
        generation_mode=GenerationMode.STANDARD,
        prompt_fingerprint=f"sha256:{prompt * 64}",
        provider_identifier=provider,
        model_identifier="model",
        validation_errors=(),
        validation_warnings=(),
        retry_reason=None,
        acceptance_status=ManifestItemStatus.COMPLETED,
        state_revision_before=0,
        state_revision_after=1,
    )


def controlled_output(provider="openai", prompt="a"):
    return ControlledGenerationResult(
        draft=EpisodeDraft(
            episode_id="episode",
            opening="Opening",
            stories=(),
            transitions=(),
            closing="Closing",
            cta=None,
            assembled_text="Opening\n\nClosing",
            teleprompter_text="Opening\n\nClosing",
        ),
        trace=GenerationTrace(
            attempts=(trace_node(prompt, GenerationComponentType.STORY, provider),)
        ),
        manifest=GenerationManifest(items=()),
        final_state=EpisodeGenerationState(),
    )


def test_exact_api_and_passive_construction():
    assert public.__all__ == EXPECTED
    session = SessionFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=session,
        generator_factory=GeneratorFactory(),
    )
    assert session.calls == 0
    assert "0x" not in repr(coordinator)
    assert copy.copy(coordinator) == coordinator
    assert copy.deepcopy(coordinator) == coordinator
    with pytest.raises(TypeError):
        pickle.dumps(coordinator)


def test_invalid_request_opens_no_session():
    session = SessionFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=session,
        generator_factory=GeneratorFactory(),
    )
    result = coordinator.execute(object())
    assert session.calls == 0
    assert result.status is EditorOperationalGenerationStatusV1.FAILED
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
    )
    assert result.attempt_count == 0
    assert tuple(inspect.signature(type(result)).parameters) == (
        "source_report_id",
        "source_report_fingerprint",
        "preparation_result_fingerprint",
        "execution_request_reference",
        "execution_request_fingerprint",
        "status",
        "lifecycle",
        "draft",
        "generation_trace",
        "generation_manifest",
        "final_state_revision",
        "attempts",
        "attempt_count",
        "timeout_retry_count",
        "failure",
        "cleanup_failed",
        "result_fingerprint",
    )
    object.__setattr__(result, "lifecycle", GENERATION_FAILURE_LIFECYCLE)
    with pytest.raises(ValueError):
        copy.copy(result)


@pytest.mark.parametrize("bad", [object(), None, SessionFactory])
def test_invalid_dependencies_are_rejected_without_invocation(bad):
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        public.EditorOperationalExecutionCoordinatorV1(
            session_factory=bad,
            generator_factory=GeneratorFactory(),
        )


def test_operation_global_provenance_and_timeout_groups():
    attempts = (
        observation(1, "a", ExecutionOutcomeV2.COMPLETED),
        observation(2, "b", ExecutionOutcomeV2.TIMEOUT),
        observation(3, "b", ExecutionOutcomeV2.TIMEOUT),
    )
    rebuilt = _validate_provenance(attempts, "openai", None, "controlled")
    assert rebuilt == attempts
    assert tuple(len(group) for group in _groups(rebuilt)) == (1, 2)
    assert _timeout_exhausted(rebuilt)


def test_timeout_retry_before_record_remains_valid_controlled_provenance():
    attempts = (observation(1, "a", ExecutionOutcomeV2.TIMEOUT),)
    assert _validate_provenance(attempts, "openai", None, "controlled") == attempts
    assert not _timeout_exhausted(attempts)


def test_invalid_provenance_is_rejected():
    attempts = (
        observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
        observation(2, "b", ExecutionOutcomeV2.COMPLETED),
    )
    with pytest.raises(TypeError):
        _validate_provenance(attempts, "openai", None, "controlled")


def test_trace_parity_excludes_only_exact_deterministic_local_nodes():
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    trace = GenerationTrace(
        attempts=(
            trace_node("a", GenerationComponentType.STORY, "openai"),
            trace_node("b", GenerationComponentType.ASSEMBLY, "deterministic-local"),
            trace_node(
                "c",
                GenerationComponentType.TELEPROMPTER_FORMATTING,
                "deterministic-local",
            ),
        )
    )
    _validate_trace(trace, attempts, "openai")
    invalid = trace.model_copy(
        update={
            "attempts": (
                *trace.attempts,
                trace_node("d", GenerationComponentType.STORY, "unknown"),
            )
        }
    )
    with pytest.raises(TypeError):
        _validate_trace(invalid, attempts, "openai")


def test_public_failure_value_object_safety():
    failure = public.EditorOperationalGenerationFailureV1(
        EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED,
        "Editor controlled generation failed.",
    )
    assert copy.copy(failure) == failure
    assert copy.deepcopy(failure) == failure
    assert not hasattr(failure, "__dict__")
    assert "0x" not in repr(failure)
    with pytest.raises(TypeError):
        pickle.dumps(failure)


@dataclass(frozen=True)
class Preparation:
    value: str = "prepared"


class Recorder:
    def __init__(self, attempts):
        self.attempts = attempts
        self.snapshot_calls = 0

    def snapshot(self):
        self.snapshot_calls += 1
        return self.attempts


class FakeSession:
    def __init__(self, attempts, *, close_fails=False):
        self.adapter = object()
        self.attempt_recorder = Recorder(attempts)
        self.close_calls = 0
        self.close_fails = close_fails

    def close(self):
        self.close_calls += 1
        if self.close_fails:
            raise RuntimeError("private cleanup detail")


class FakeGenerator:
    def __init__(self, failure, output=None):
        self.failure = failure
        self.output = output
        self.calls = 0
        self.arguments = None

    def generate(self, **values):
        self.calls += 1
        self.arguments = values
        if self.failure is not None:
            raise self.failure
        return self.output


class RuntimeFactory:
    def __init__(self, session):
        self.session = session
        self.calls = 0
        self.arguments = None

    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> FakeSession:
        self.calls += 1
        self.arguments = (options, operation_reference)
        return self.session


class ControlledFactory:
    def __init__(self, generator):
        self.generator = generator
        self.calls = 0
        self.arguments = None

    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> FakeGenerator:
        self.calls += 1
        self.arguments = (provider, config)
        return self.generator


def runtime_request(provider):
    plan = SimpleNamespace(
        source_report_id="report",
        source_report_fingerprint="fingerprint",
        source_input=object(),
        selection_profile=object(),
        episode_context=object(),
    )
    return SimpleNamespace(
        runtime_options=object(),
        request_reference="operation",
        request_fingerprint="request-fingerprint",
        provider=SimpleNamespace(value=provider),
        generation_configuration=object(),
        plan=plan,
        flow_result=object(),
        editorial_blueprint=object(),
        commentary_blueprint=object(),
        voice_plan=object(),
        preparation=Preparation(),
    )


def execute_fake(
    monkeypatch, attempts, *, failure=None, output=None, close_fails=False
):
    session = FakeSession(attempts, close_fails=close_fails)
    generator = FakeGenerator(failure, output)
    runtime = RuntimeFactory(session)
    factory = ControlledFactory(generator)
    monkeypatch.setattr(implementation, "EditorGenerationRuntimeSessionV1", FakeSession)
    monkeypatch.setattr(implementation, "ControlledGenerator", FakeGenerator)
    request = runtime_request(attempts[-1].provider_id if attempts else "openai")
    monkeypatch.setattr(
        implementation, "reconstruct_execution_request", lambda value: value
    )
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=runtime,
        generator_factory=factory,
    )
    result = coordinator.execute(request)
    return result, request, runtime, factory, session, generator


@pytest.mark.parametrize("provider", ["openai", "ollama"])
def test_provider_blind_controlled_generation_path(monkeypatch, provider):
    attempts = (observation(1, "a", ExecutionOutcomeV2.PROVIDER_FAILURE),)
    attempts = tuple(
        EditorGenerationAttemptObservationV1(
            item.attempt_number,
            item.prompt_fingerprint,
            item.request_reference,
            item.request_fingerprint,
            item.execution_request_id,
            item.request_envelope_identity,
            provider,
            item.outcome,
            item.source_output_reference,
            item.finish_reason,
            item.failure_code,
        )
        for item in attempts
    )
    result, request, runtime, factory, session, generator = execute_fake(
        monkeypatch,
        attempts,
        failure=ControlledGenerationError("must not be inspected"),
    )
    assert (
        result.failure.code is EditorOperationalGenerationFailureCodeV1.PROVIDER_FAILED
    )
    assert runtime.calls == factory.calls == generator.calls == 1
    assert factory.arguments[0] is session.adapter
    assert runtime.arguments == (request.runtime_options, request.request_reference)
    assert session.attempt_recorder.snapshot_calls == session.close_calls == 1
    assert generator.arguments["scout_input"] is request.plan.source_input
    assert generator.arguments["static_cta_content"] == ""
    assert generator.arguments["teleprompter_profile"] is None


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [
        (
            (observation(1, "a", ExecutionOutcomeV2.CANCELLED),),
            EditorOperationalGenerationFailureCodeV1.CANCELLED,
        ),
        (
            (
                observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
                observation(2, "a", ExecutionOutcomeV2.TIMEOUT),
            ),
            EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED,
        ),
        (
            (observation(1, "a", ExecutionOutcomeV2.TIMEOUT),),
            EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED,
        ),
        (
            (observation(2, "a", ExecutionOutcomeV2.PROVIDER_FAILURE),),
            EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID,
        ),
    ],
)
def test_terminal_failure_precedence(monkeypatch, attempts, expected):
    result, _, _, _, session, _ = execute_fake(
        monkeypatch,
        attempts,
        failure=ControlledGenerationError("same public exception"),
    )
    assert result.failure.code is expected
    assert session.attempt_recorder.snapshot_calls == 1
    assert session.close_calls == 1


def test_unexpected_generator_exception_is_not_internal(monkeypatch):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        execute_fake(
            monkeypatch, attempts, failure=RuntimeError("private dependency detail")
        )


def test_successful_generation_publishes_only_after_close(monkeypatch):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    controlled = controlled_output()
    result, _, runtime, factory, session, generator = execute_fake(
        monkeypatch, attempts, output=controlled
    )
    assert result.status is EditorOperationalGenerationStatusV1.COMPLETED
    assert result.draft == controlled.draft
    assert result.failure is None
    assert runtime.calls == factory.calls == generator.calls == 1
    assert session.attempt_recorder.snapshot_calls == session.close_calls == 1


class FailingRuntimeFactory:
    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> FakeSession:
        del options, operation_reference
        raise RuntimeError("private runtime detail")


def test_runtime_open_failure_constructs_nothing_and_needs_no_cleanup(monkeypatch):
    monkeypatch.setattr(implementation, "EditorGenerationRuntimeSessionV1", FakeSession)
    monkeypatch.setattr(implementation, "ControlledGenerator", FakeGenerator)
    monkeypatch.setattr(
        implementation, "reconstruct_execution_request", lambda value: value
    )
    generator = FakeGenerator(ControlledGenerationError("unused"))
    factory = ControlledFactory(generator)
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=FailingRuntimeFactory(), generator_factory=factory
    )
    result = coordinator.execute(runtime_request("openai"))
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED
    )
    assert factory.calls == generator.calls == 0


def test_cleanup_failure_has_final_precedence(monkeypatch):
    attempts = (observation(1, "a", ExecutionOutcomeV2.CANCELLED),)
    result, _, _, _, session, _ = execute_fake(
        monkeypatch,
        attempts,
        failure=ControlledGenerationError("hidden"),
        close_fails=True,
    )
    assert (
        result.failure.code is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED
    )
    assert result.cleanup_failed
    assert result.draft is result.generation_trace is result.generation_manifest is None
    assert session.close_calls == 1


def test_configuration_traceback_retains_no_dependencies():
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=SessionFactory(), generator_factory=GeneratorFactory()
    )
    object.__setattr__(coordinator, "_generator_factory", object())
    with pytest.raises(public.EditorOperationalExecutionConfigurationError) as caught:
        repr(coordinator)
    traceback = caught.value.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
        if "/src/pastila_scout/editor_operational_execution_v1/" in filename:
            values = tuple(traceback.tb_frame.f_locals.values())
            assert all(item is not coordinator for item in values)
            assert not any(
                isinstance(item, (SessionFactory, GeneratorFactory)) for item in values
            )
        traceback = traceback.tb_next
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


@pytest.mark.parametrize(
    "private_cause",
    [
        "malformed-json",
        "schema-invalid",
        "structured-output-rejection",
        "malformed-lower-before-record",
        "lower-lineage-before-record",
        "hidden-adapter-failure",
        "timeout-retry-before-record",
    ],
)
def test_distinct_collapsed_controlled_generation_paths(monkeypatch, private_cause):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    if private_cause == "timeout-retry-before-record":
        attempts = (observation(1, "a", ExecutionOutcomeV2.TIMEOUT),)
    result, _, runtime, factory, session, generator = execute_fake(
        monkeypatch,
        attempts,
        failure=ControlledGenerationError(private_cause),
    )
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED
    )
    assert result.draft is result.generation_trace is result.generation_manifest is None
    assert runtime.calls == factory.calls == generator.calls == 1
    assert session.attempt_recorder.snapshot_calls == session.close_calls == 1


@pytest.mark.parametrize(
    "field",
    [
        "preparation",
        "plan",
        "flow_result",
        "editorial_blueprint",
        "commentary_blueprint",
        "voice_plan",
        "generation_configuration",
    ],
)
def test_substituted_nested_request_artifact_never_opens_session(field):
    request = execution_request()
    object.__setattr__(request, field, object())
    session = SessionFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=session, generator_factory=GeneratorFactory()
    )
    result = coordinator.execute(request)
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
    )
    assert session.calls == 0


def test_timeout_followed_by_recorded_success_completes(monkeypatch):
    attempts = (
        observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
        observation(2, "a", ExecutionOutcomeV2.COMPLETED),
    )
    controlled = controlled_output()
    result, *rest = execute_fake(monkeypatch, attempts, output=controlled)
    assert result.status is EditorOperationalGenerationStatusV1.COMPLETED
    assert result.timeout_retry_count == 1
    assert rest[-2].attempt_recorder.snapshot_calls == 1


def test_package_owned_classification_failure_is_finite_internal(monkeypatch):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    monkeypatch.setattr(
        implementation,
        "_classify",
        lambda *values: (_ for _ in ()).throw(RuntimeError("package-owned")),
    )
    result, *_ = execute_fake(monkeypatch, attempts)
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.INTERNAL_EXECUTION_FAILURE
    )


@pytest.mark.parametrize(
    ("attempts", "failure", "output"),
    [
        (
            (observation(1, "a", ExecutionOutcomeV2.CANCELLED),),
            ControlledGenerationError(),
            None,
        ),
        (
            (
                observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
                observation(2, "a", ExecutionOutcomeV2.TIMEOUT),
            ),
            ControlledGenerationError(),
            None,
        ),
        (
            (observation(1, "a", ExecutionOutcomeV2.PROVIDER_FAILURE),),
            ControlledGenerationError(),
            None,
        ),
        (
            (observation(2, "a", ExecutionOutcomeV2.PROVIDER_FAILURE),),
            ControlledGenerationError(),
            None,
        ),
    ],
)
def test_cleanup_failure_overrides_terminal_matrix(
    monkeypatch, attempts, failure, output
):
    result, _, _, _, session, _ = execute_fake(
        monkeypatch,
        attempts,
        failure=failure,
        output=output,
        close_fails=True,
    )
    assert (
        result.failure.code is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED
    )
    assert result.draft is result.generation_trace is result.generation_manifest is None
    assert session.close_calls == 1


def test_cleanup_failure_overrides_completed_and_internal(monkeypatch):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    completed, _, _, _, completed_session, _ = execute_fake(
        monkeypatch,
        attempts,
        output=controlled_output(),
        close_fails=True,
    )
    assert (
        completed.failure.code
        is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED
    )
    assert completed_session.close_calls == 1
    monkeypatch.setattr(
        implementation,
        "_classify",
        lambda *values: (_ for _ in ()).throw(RuntimeError("package-owned")),
    )
    internal, _, _, _, internal_session, _ = execute_fake(
        monkeypatch, attempts, close_fails=True
    )
    assert (
        internal.failure.code is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED
    )
    assert internal_session.close_calls == 1


class MissingOpen:
    pass


class WrongName:
    def open(
        self, value: EditorGenerationRuntimeOptionsV1, *, operation_reference: str
    ) -> FakeSession:
        raise AssertionError


class WrongKind:
    @staticmethod
    def open(
        options: EditorGenerationRuntimeOptionsV1, *, operation_reference: str
    ) -> FakeSession:
        raise AssertionError


class PropertyOpen:
    @property
    def open(self):
        raise AssertionError


class CachedOpen:
    @cached_property
    def open(self):
        raise AssertionError


class DynamicGetattr:
    def __getattr__(self, name):
        raise AssertionError(name)


class DynamicGetattribute:
    def __getattribute__(self, name):
        if name == "__class__":
            return object.__getattribute__(self, name)
        raise AssertionError(name)


class WrongAnnotation:
    def open(self, options: object, *, operation_reference: str) -> FakeSession:
        raise AssertionError


class WrongReturn:
    def open(
        self, options: EditorGenerationRuntimeOptionsV1, *, operation_reference: str
    ) -> object:
        raise AssertionError


class MissingAnnotation:
    def open(self, options, *, operation_reference):
        raise AssertionError


def wrapped_open(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        raise AssertionError

    return wrapper


class WrappedOpen:
    @wrapped_open
    def open(
        self, options: EditorGenerationRuntimeOptionsV1, *, operation_reference: str
    ) -> FakeSession:
        raise AssertionError


class PartialOpen:
    def original(
        self, options: EditorGenerationRuntimeOptionsV1, *, operation_reference: str
    ) -> FakeSession:
        raise AssertionError

    open = functools.partial(original)


@pytest.mark.parametrize(
    "dependency",
    [
        MissingOpen(),
        WrongName(),
        WrongKind(),
        PropertyOpen(),
        CachedOpen(),
        DynamicGetattr(),
        DynamicGetattribute(),
        WrongAnnotation(),
        WrongReturn(),
        MissingAnnotation(),
        WrappedOpen(),
        PartialOpen(),
    ],
    ids=(
        "missing-open",
        "wrong-name",
        "static-method",
        "property",
        "cached-property",
        "dynamic-getattr",
        "dynamic-getattribute",
        "wrong-annotation",
        "wrong-return",
        "missing-annotation",
        "wrapped",
        "partial",
    ),
)
def test_representative_dependency_matrix_is_static_and_inert(dependency):
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        public.EditorOperationalExecutionCoordinatorV1(
            session_factory=dependency,
            generator_factory=GeneratorFactory(),
        )


def test_copied_invalid_result_traceback_is_neutral():
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=SessionFactory(), generator_factory=GeneratorFactory()
    )
    result = coordinator.execute(object())
    object.__setattr__(result, "lifecycle", GENERATION_FAILURE_LIFECYCLE)
    with pytest.raises(ValueError) as caught:
        copy.copy(result)
    traceback = caught.value.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
        if "/src/pastila_scout/editor_operational_execution_v1/" in filename:
            assert set(traceback.tb_frame.f_locals) <= {"error"}
        traceback = traceback.tb_next
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_fresh_process_import_is_passive():
    completed = subprocess.run(
        [sys.executable, "-c", "import pastila_scout.editor_operational_execution_v1"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""


class CountingGeneratorFactory:
    def __init__(self):
        self.calls = 0

    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> ControlledGenerator:
        del provider, config
        self.calls += 1
        raise AssertionError("must remain inert")


class WrongParameterCount:
    def open(self, options: EditorGenerationRuntimeOptionsV1) -> FakeSession:
        del options
        raise AssertionError


class WrongParameterKind:
    def open(
        self,
        *,
        options: EditorGenerationRuntimeOptionsV1,
        operation_reference: str,
    ) -> FakeSession:
        del options, operation_reference
        raise AssertionError


class ClassMethodOpen:
    @classmethod
    def open(
        cls,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> FakeSession:
        del cls, options, operation_reference
        raise AssertionError


class ForgedSignatureOpen:
    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> FakeSession:
        del options, operation_reference
        raise AssertionError


ForgedSignatureOpen.open.__signature__ = inspect.Signature()


class ForgedWrappedOpen:
    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> FakeSession:
        del options, operation_reference
        raise AssertionError


ForgedWrappedOpen.open.__wrapped__ = SessionFactory.open


@pytest.mark.parametrize(
    "dependency",
    [
        WrongParameterCount(),
        WrongParameterKind(),
        ClassMethodOpen(),
        ForgedSignatureOpen(),
        ForgedWrappedOpen(),
    ],
    ids=(
        "wrong-parameter-count",
        "wrong-parameter-kind",
        "classmethod",
        "forged-signature",
        "forged-wrapped",
    ),
)
def test_additional_dependency_shapes_are_rejected_without_invocation(dependency):
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        public.EditorOperationalExecutionCoordinatorV1(
            session_factory=dependency,
            generator_factory=GeneratorFactory(),
        )


def test_instance_level_dependency_replacement_is_rejected_without_invocation():
    dependency = SessionFactory()
    dependency.open = lambda *args, **kwargs: pytest.fail("body invoked")
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        public.EditorOperationalExecutionCoordinatorV1(
            session_factory=dependency,
            generator_factory=GeneratorFactory(),
        )
    assert dependency.calls == 0


def test_copied_invalid_dependency_state_is_rejected_without_invocation():
    dependency = SessionFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=dependency,
        generator_factory=GeneratorFactory(),
    )
    object.__setattr__(coordinator, "_session_factory", object())
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        copy.copy(coordinator)
    assert dependency.calls == 0


def test_post_construction_dependency_substitution_is_rejected_without_invocation():
    dependency = SessionFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=dependency,
        generator_factory=GeneratorFactory(),
    )
    object.__setattr__(coordinator, "_generator_factory", object())
    with pytest.raises(public.EditorOperationalExecutionConfigurationError):
        coordinator.execute(execution_request())
    assert dependency.calls == 0


@pytest.mark.parametrize(
    ("label", "field"),
    [
        ("copied-invalid-preparation", "preparation"),
        ("copied-invalid-plan", "plan"),
        ("copied-invalid-flow", "flow_result"),
        ("copied-invalid-editorial", "editorial_blueprint"),
        ("copied-invalid-commentary", "commentary_blueprint"),
        ("copied-invalid-voice", "voice_plan"),
        ("copied-invalid-config", "generation_configuration"),
        ("lineage-mismatch", "plan"),
        ("ordering-mismatch", "flow_result"),
        ("foreign-identity", "editorial_blueprint"),
    ],
)
def test_authority_and_nested_corruption_is_inert(label, field):
    request = execution_request()
    nested = copy.copy(getattr(request, field))
    object.__setattr__(request, field, nested)
    if field in {"preparation", "plan"}:
        object.__setattr__(nested, "_seal", "0" * 64)
    elif field == "flow_result":
        object.__setattr__(nested, "output", object())
    elif field == "generation_configuration":
        object.__setattr__(nested, "provider", object())
    else:
        object.__setattr__(nested, "source_report_id", f"foreign-{label}")
    session = SessionFactory()
    generator = CountingGeneratorFactory()
    coordinator = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=session, generator_factory=generator
    )
    result = coordinator.execute(request)
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
    )
    assert session.calls == generator.calls == 0
    assert result.attempt_count == 0


def test_copied_invalid_execution_request_is_inert():
    request = copy.copy(execution_request())
    object.__setattr__(request, "request_fingerprint", "0" * 64)
    session = SessionFactory()
    generator = CountingGeneratorFactory()
    result = public.EditorOperationalExecutionCoordinatorV1(
        session_factory=session, generator_factory=generator
    ).execute(request)
    assert (
        result.failure.code
        is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
    )
    assert session.calls == generator.calls == result.attempt_count == 0


def test_openai_and_ollama_success_are_operationally_equivalent(monkeypatch):
    results = []
    for provider in ("openai", "ollama"):
        item = observation(1, "a", ExecutionOutcomeV2.COMPLETED)
        attempt = EditorGenerationAttemptObservationV1(
            item.attempt_number,
            item.prompt_fingerprint,
            item.request_reference,
            item.request_fingerprint,
            item.execution_request_id,
            item.request_envelope_identity,
            provider,
            item.outcome,
            item.source_output_reference,
            item.finish_reason,
            item.failure_code,
        )
        result, _, runtime, factory, session, generator = execute_fake(
            monkeypatch,
            (attempt,),
            output=controlled_output(provider),
        )
        assert result.status is EditorOperationalGenerationStatusV1.COMPLETED
        assert result.failure is None
        assert runtime.calls == factory.calls == generator.calls == 1
        assert session.attempt_recorder.snapshot_calls == session.close_calls == 1
        results.append(result)
    first, second = results
    assert first.draft == second.draft
    assert first.generation_manifest == second.generation_manifest
    assert first.final_state_revision == second.final_state_revision
    assert first.lifecycle == second.lifecycle
    assert first.failure == second.failure
    assert first.attempt_count == second.attempt_count
    assert first.timeout_retry_count == second.timeout_retry_count
    assert first.generation_trace.attempts[0].provider_identifier == "openai"
    assert second.generation_trace.attempts[0].provider_identifier == "ollama"


_REVISION_3D_PRODUCTION_PATHS = frozenset(
    {
        "src/pastila_scout/editor_operational_execution_v1/__init__.py",
        "src/pastila_scout/editor_operational_execution_v1/coordinator.py",
        "src/pastila_scout/editor_operational_execution_v1/errors.py",
        "src/pastila_scout/editor_operational_execution_v1/models.py",
        "src/pastila_scout/editor_operational_execution_v1/protocols.py",
    }
)
_REVISION_3D_TEST_PATH = "tests/test_editor_operational_execution_v1.py"
_REVISION_3D_PATHS = _REVISION_3D_PRODUCTION_PATHS | {_REVISION_3D_TEST_PATH}
_REVISION_3D_TAG = "phase-4.2-editor-operational-execution-r3d-verified"
def _revision_3d_snapshot_is_valid(
    *, tracked, existing, tag_changed, working_changed, staged, untracked
):
    del tag_changed  # Historical changes are expected after a verified revision tag.
    return (
        _REVISION_3D_PATHS.issubset(tracked)
        and _REVISION_3D_PATHS.issubset(existing)
        and not (_REVISION_3D_PRODUCTION_PATHS & working_changed)
        and not (_REVISION_3D_PATHS & staged)
        and not (_REVISION_3D_PATHS & untracked)
    )


def _git_names(root, *arguments):
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(completed.stdout.splitlines())


def test_frozen_repository_integrity_is_exact():
    path_type = __import__("pathlib").Path
    root_path = path_type(__file__).resolve().parents[1]
    root = str(root_path)
    paths = tuple(sorted(_REVISION_3D_PATHS))
    production = tuple(sorted(_REVISION_3D_PRODUCTION_PATHS))
    tracked = _git_names(root, "ls-files", "--", *paths)
    existing = {path for path in _REVISION_3D_PATHS if (root_path / path).is_file()}
    tag_changed = _git_names(
        root, "diff", "--name-only", _REVISION_3D_TAG, "--", *production
    )
    working_changed = _git_names(root, "diff", "--name-only", "--", *production)
    staged = _git_names(root, "diff", "--cached", "--name-only", "--", *paths)
    untracked = _git_names(root, "ls-files", "--others", "--exclude-standard")
    assert _revision_3d_snapshot_is_valid(
        tracked=tracked,
        existing=existing,
        tag_changed=tag_changed,
        working_changed=working_changed,
        staged=staged,
        untracked=untracked,
    )


def test_revision_3d_integrity_snapshot_rejects_mutation_without_git_writes():
    valid = {
        "tracked": set(_REVISION_3D_PATHS),
        "existing": set(_REVISION_3D_PATHS),
        "tag_changed": set(),
        "working_changed": set(),
        "staged": set(),
        "untracked": {"future/additive/package.py"},
    }
    assert _revision_3d_snapshot_is_valid(**valid)
    for key, path in (
        ("working_changed", next(iter(_REVISION_3D_PRODUCTION_PATHS))),
        ("staged", _REVISION_3D_TEST_PATH),
        ("untracked", _REVISION_3D_TEST_PATH),
    ):
        invalid = {name: set(values) for name, values in valid.items()}
        invalid[key].add(path)
        assert not _revision_3d_snapshot_is_valid(**invalid)
    for key in ("tracked", "existing"):
        invalid = {name: set(values) for name, values in valid.items()}
        invalid[key].remove(_REVISION_3D_TEST_PATH)
        assert not _revision_3d_snapshot_is_valid(**invalid)


def _assert_recursive_public_isolation(value, protected):
    protected_ids = {id(item) for item in protected}
    seen = set()

    def inspect_value(item):
        if id(item) in seen:
            return
        seen.add(id(item))
        assert id(item) not in protected_ids
        if isinstance(item, BaseException):
            inspect_value(item.__context__)
            inspect_value(item.__cause__)
            traceback = item.__traceback__
            while traceback is not None:
                filename = traceback.tb_frame.f_code.co_filename.replace("\\", "/")
                if "/src/pastila_scout/editor_operational_execution_v1/" in filename:
                    for nested in traceback.tb_frame.f_locals.values():
                        inspect_value(nested)
                traceback = traceback.tb_next
        elif isinstance(item, dict):
            for key, nested in item.items():
                inspect_value(key)
                inspect_value(nested)
        elif isinstance(item, (tuple, list, set, frozenset)):
            for nested in item:
                inspect_value(nested)

    inspect_value(value)


class SnapshotFailureRecorder(Recorder):
    def snapshot(self):
        self.snapshot_calls += 1
        raise RuntimeError("private snapshot detail")


class SnapshotFailureSession(FakeSession):
    def __init__(self, attempts):
        super().__init__(attempts)
        self.attempt_recorder = SnapshotFailureRecorder(attempts)


class GeneratorConstructionFailureFactory:
    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> FakeGenerator:
        del provider, config
        raise RuntimeError("private construction detail")


@pytest.mark.parametrize(
    "origin",
    [
        "invalid-request",
        "runtime-open",
        "generator-construction",
        "generator-execution",
        "snapshot",
        "provenance",
        "manifest-reconstruction",
        "final-state-reconstruction",
        "result-reconstruction",
        "cleanup",
    ],
)
def test_recursive_traceback_and_failure_graph_isolation(monkeypatch, origin):
    attempts = (observation(1, "a", ExecutionOutcomeV2.COMPLETED),)
    protected = []
    with monkeypatch.context() as patcher:
        if origin == "invalid-request":
            session = SessionFactory()
            coordinator = public.EditorOperationalExecutionCoordinatorV1(
                session_factory=session, generator_factory=GeneratorFactory()
            )
            protected.extend((session, coordinator))
            published = coordinator.execute(object())
        elif origin == "runtime-open":
            patcher.setattr(
                implementation, "EditorGenerationRuntimeSessionV1", FakeSession
            )
            patcher.setattr(implementation, "ControlledGenerator", FakeGenerator)
            patcher.setattr(
                implementation, "reconstruct_execution_request", lambda value: value
            )
            runtime = FailingRuntimeFactory()
            factory = ControlledFactory(FakeGenerator(None))
            coordinator = public.EditorOperationalExecutionCoordinatorV1(
                session_factory=runtime, generator_factory=factory
            )
            protected.extend((runtime, factory, coordinator))
            published = coordinator.execute(runtime_request("openai"))
        elif origin == "generator-construction":
            session = FakeSession(attempts)
            runtime = RuntimeFactory(session)
            factory = GeneratorConstructionFailureFactory()
            patcher.setattr(
                implementation, "EditorGenerationRuntimeSessionV1", FakeSession
            )
            patcher.setattr(implementation, "ControlledGenerator", FakeGenerator)
            patcher.setattr(
                implementation, "reconstruct_execution_request", lambda value: value
            )
            coordinator = public.EditorOperationalExecutionCoordinatorV1(
                session_factory=runtime, generator_factory=factory
            )
            protected.extend((session, runtime, factory, coordinator))
            with pytest.raises(
                public.EditorOperationalExecutionConfigurationError
            ) as caught:
                coordinator.execute(runtime_request("openai"))
            published = caught.value
        elif origin == "generator-execution":
            with pytest.raises(
                public.EditorOperationalExecutionConfigurationError
            ) as caught:
                execute_fake(
                    patcher, attempts, failure=RuntimeError("private generation detail")
                )
            published = caught.value
        elif origin == "snapshot":
            session = SnapshotFailureSession(attempts)
            generator = FakeGenerator(ControlledGenerationError())
            runtime = RuntimeFactory(session)
            factory = ControlledFactory(generator)
            patcher.setattr(
                implementation, "EditorGenerationRuntimeSessionV1", FakeSession
            )
            patcher.setattr(implementation, "ControlledGenerator", FakeGenerator)
            patcher.setattr(
                implementation, "reconstruct_execution_request", lambda value: value
            )
            coordinator = public.EditorOperationalExecutionCoordinatorV1(
                session_factory=runtime, generator_factory=factory
            )
            protected.extend((session, generator, runtime, factory, coordinator))
            published = coordinator.execute(runtime_request("openai"))
        else:
            output = controlled_output()
            close_fails = origin == "cleanup"
            if origin == "provenance":
                patcher.setattr(
                    implementation,
                    "_validate_provenance",
                    lambda *args: (_ for _ in ()).throw(RuntimeError("private")),
                )
            elif origin == "manifest-reconstruction":
                object.__setattr__(output, "manifest", object())
            elif origin == "final-state-reconstruction":
                object.__setattr__(output, "final_state", object())
            elif origin == "result-reconstruction":
                patcher.setattr(
                    implementation,
                    "_completed_result",
                    lambda *args: (_ for _ in ()).throw(RuntimeError("private")),
                )
            published, request, runtime, factory, session, generator = execute_fake(
                patcher, attempts, output=output, close_fails=close_fails
            )
            protected.extend((request, runtime, factory, session, generator))
    _assert_recursive_public_isolation(published, protected)
    if isinstance(published, BaseException):
        assert published.__context__ is None
        assert published.__cause__ is None
