from __future__ import annotations

import copy
import hashlib
import inspect
import pickle
import subprocess
from abc import abstractmethod
from datetime import datetime
from functools import cached_property, wraps
from pathlib import Path

import pytest
from test_editor_application_contracts_v1 import generation, request
from test_editor_application_serialization_v1 import completed_result, failed_result
from test_editor_operational_execution_v1 import (
    GeneratorFactory,
    SessionFactory,
    runtime_request,
)

import pastila_scout.editor_application_v1 as public
import pastila_scout.editor_application_v1.application as implementation
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.blueprint_models import EditorialBlueprint
from pastila_scout.editor.commentary_models import EpisodeCommentaryBlueprint
from pastila_scout.editor.engine import SelectionEngine
from pastila_scout.editor.flow_models import FlowOptimizationResult
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.voice_models import EpisodeVoicePlan
from pastila_scout.editor_application_v1.protocols import (
    _EditorDeterministicArtifactsV1,
)
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_execution_request_authority_v1 import (
    EditorGenerationExecutionRequestAuthorityV1,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalExecutionCoordinatorV1,
    EditorOperationalGenerationFailureCodeV1,
    EditorOperationalResultV1,
)
from pastila_scout.editor_operational_execution_v1.coordinator import _failure_result
from pastila_scout.editor_operational_v1 import (
    EditorGenerationPlanV1,
    EditorOperationalCoordinatorV1,
    EditorOperationalPreparationResultV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1


class Preparation:
    def __init__(self, result: EditorOperationalPreparationResultV1, calls: list[str]):
        self.result, self.calls = result, calls

    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        del scout_input, selection_profile, episode_context
        self.calls.append("prepare")
        return self.result


class Artifacts:
    def __init__(self, result: _EditorDeterministicArtifactsV1, calls: list[str]):
        self.result, self.calls = result, calls

    def build(self, *, plan: EditorGenerationPlanV1) -> _EditorDeterministicArtifactsV1:
        del plan
        self.calls.append("artifacts")
        return self.result


class Execution:
    def __init__(self, result: EditorOperationalResultV1, calls: list[str]):
        self.result, self.calls = result, calls
        self.argument = None

    def execute(
        self, *, request: EditorGenerationExecutionRequestV1
    ) -> EditorOperationalResultV1:
        self.argument = request
        self.calls.append("execute")
        return self.result


class Authority:
    def __init__(self, calls: list[str]):
        self.delegate = EditorGenerationExecutionRequestAuthorityV1()
        self.calls = calls

    def construct(
        self,
        *,
        preparation: EditorOperationalPreparationResultV1,
        plan: EditorGenerationPlanV1,
        flow_result: FlowOptimizationResult,
        editorial_blueprint: EditorialBlueprint,
        commentary_blueprint: EpisodeCommentaryBlueprint,
        voice_plan: EpisodeVoicePlan,
        generation_configuration: LanguageGenerationConfig,
        runtime_options: EditorGenerationRuntimeOptionsV1,
        provider: ProviderChoiceV1,
        requested_at: datetime,
        request_reference: str,
        cancellation: CancellationTokenV2,
    ) -> EditorGenerationExecutionRequestV1:
        self.calls.append("authority")
        return self.delegate.construct(
            preparation=preparation,
            plan=plan,
            flow_result=flow_result,
            editorial_blueprint=editorial_blueprint,
            commentary_blueprint=commentary_blueprint,
            voice_plan=voice_plan,
            generation_configuration=generation_configuration,
            runtime_options=runtime_options,
            provider=provider,
            requested_at=requested_at,
            request_reference=request_reference,
            cancellation=cancellation,
        )


class Serializer:
    def __init__(self, calls: list[str]):
        self.delegate = public.EditorOperationalResultSerializerV1()
        self.calls = calls

    def serialize(
        self, *, result: EditorOperationalResultV1
    ) -> public.EditorSerializedOperationalResultV1:
        self.calls.append("serialize")
        return self.delegate.serialize(result=result)


class Exporter:
    def __init__(self, calls: list[str]):
        self.calls = calls
        self.arguments = None

    def publish(
        self,
        *,
        payload: bytes,
        destination: public.EditorOutputDestinationV1,
    ) -> Path:
        self.calls.append("export")
        self.arguments = (payload, destination)
        return destination.path


class MissingPreparationMethod:
    pass


class PositionalPreparationMethod:
    def prepare(
        self,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


class WrongCountPreparationMethod:
    def prepare(
        self, *, scout_input: ScoutEditorInputV1
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


class WrongPreparationAnnotations:
    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> object:
        raise AssertionError("dependency body executed")


class ClassPreparationMethod:
    @classmethod
    def prepare(
        cls,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


class PropertyPreparationMethod:
    @property
    def prepare(self):
        raise AssertionError("descriptor executed")


class CachedPropertyPreparationMethod:
    @cached_property
    def prepare(self):
        raise AssertionError("descriptor executed")


class AbstractPreparationMethod:
    @abstractmethod
    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


class WrappedPreparationMethod:
    @wraps(Preparation.prepare)
    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


class ForgedSignaturePreparationMethod:
    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        raise AssertionError("dependency body executed")


ForgedSignaturePreparationMethod.prepare.__signature__ = inspect.signature(
    Preparation.prepare
)


def dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    failed=False,
    provider=ProviderChoiceV1.OPENAI,
):
    app_request = request(
        tmp_path,
        operation_reference="operation",
        generation_configuration=generation(provider=provider),
    )
    lower = EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        app_request.scout_input,
        app_request.selection_profile,
        app_request.episode_context,
    )
    assert lower.plan is not None
    artifacts = implementation._EditorArtifactPreparerV1().build(plan=lower.plan)
    operational = (
        failed_result(monkeypatch) if failed else completed_result(monkeypatch)
    )
    calls: list[str] = []
    exporter = Exporter(calls)
    values = (
        Preparation(lower, calls),
        Artifacts(artifacts, calls),
        Authority(calls),
        Execution(operational, calls),
        Serializer(calls),
        exporter,
    )
    return app_request, values, calls, exporter


def coordinator(values) -> public.EditorApplicationCoordinatorV1:
    return public.EditorApplicationCoordinatorV1(
        preparation=values[0],
        artifacts=values[1],
        execution_request_authority=values[2],
        operational_execution=values[3],
        serializer=values[4],
        exporter=values[5],
    )


def test_exact_api_layout_and_signatures() -> None:
    assert len(public.__all__) == 21
    assert public.__all__[2] == "EditorApplicationCoordinatorV1"
    assert public.EditorApplicationCoordinatorV1.__module__.endswith(".application")
    assert not hasattr(public, "_compose_editor_application_coordinator_v1")
    signature = inspect.signature(public.EditorApplicationCoordinatorV1)
    assert tuple(signature.parameters) == (
        "preparation",
        "artifacts",
        "execution_request_authority",
        "operational_execution",
        "serializer",
        "exporter",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    execute = inspect.signature(public.EditorApplicationCoordinatorV1.execute)
    assert tuple(execute.parameters) == ("self", "request")
    assert execute.parameters["request"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize("provider", tuple(ProviderChoiceV1))
def test_successful_provider_blind_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: ProviderChoiceV1,
) -> None:
    app_request, values, calls, exporter = dependencies(
        tmp_path, monkeypatch, provider=provider
    )
    result = coordinator(values).execute(request=app_request)
    assert result.status is public.EditorApplicationStatusV1.COMPLETED
    assert result.exit_code is public.EditorApplicationExitCodeV1.COMPLETED
    assert result.exported and result.handoff_permitted
    assert result.output_path == app_request.destination.path
    assert result.payload_sha256.startswith("sha256:")
    assert calls == [
        "prepare",
        "artifacts",
        "authority",
        "execute",
        "serialize",
        "export",
    ]
    assert values[3].argument.provider is provider
    assert exporter.arguments[1] == app_request.destination
    assert type(exporter.arguments[0]) is bytes
    assert not app_request.destination.path.exists()


def test_initial_cancellation_suppresses_all_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, values, calls, _ = dependencies(tmp_path, monkeypatch)
    cancelled = request(
        tmp_path,
        operation_reference="operation",
        cancellation=CancellationTokenV2(cancellation_requested=True),
    )
    result = coordinator(values).execute(request=cancelled)
    assert result.status is public.EditorApplicationStatusV1.CANCELLED
    assert result.exit_code is public.EditorApplicationExitCodeV1.CANCELLED
    assert calls == []


def test_operational_failure_suppresses_serializer_and_exporter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_request, values, calls, _ = dependencies(tmp_path, monkeypatch, failed=True)
    result = coordinator(values).execute(request=app_request)
    assert result.status is public.EditorApplicationStatusV1.FAILED
    assert (
        result.failure.code
        is public.EditorApplicationFailureCodeV1.OPERATIONAL_EXECUTION_FAILED
    )
    assert result.operational_result is not None
    assert calls == ["prepare", "artifacts", "authority", "execute"]


@pytest.mark.parametrize(
    ("code", "expected_exit", "cancelled"),
    [
        (EditorOperationalGenerationFailureCodeV1.PROVIDER_FAILED, 3, False),
        (
            EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED,
            3,
            False,
        ),
        (EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID, 3, False),
        (EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST, 3, False),
        (EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED, 3, False),
        (EditorOperationalGenerationFailureCodeV1.CONTROLLED_RESULT_INVALID, 3, False),
        (EditorOperationalGenerationFailureCodeV1.INTERNAL_EXECUTION_FAILURE, 3, False),
        (EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED, 4, False),
        (EditorOperationalGenerationFailureCodeV1.CANCELLED, 5, True),
        (EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED, 7, False),
    ],
)
def test_complete_operational_outcome_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: EditorOperationalGenerationFailureCodeV1,
    expected_exit: int,
    cancelled: bool,
) -> None:
    if code is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST:
        operational = EditorOperationalExecutionCoordinatorV1(
            session_factory=SessionFactory(), generator_factory=GeneratorFactory()
        ).execute(object())
        assert (
            operational.source_report_id,
            operational.source_report_fingerprint,
            operational.preparation_result_fingerprint,
            operational.execution_request_reference,
            operational.execution_request_fingerprint,
        ) == ("", "", "", "", "")
    else:
        operational = _failure_result(
            runtime_request("openai"),
            code,
            cleanup_failed=code
            is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED,
            controlled_result=code
            is EditorOperationalGenerationFailureCodeV1.CONTROLLED_RESULT_INVALID,
        )
    app_request, values, calls, _ = dependencies(tmp_path, monkeypatch)
    values = (*values[:3], Execution(operational, calls), *values[4:])
    result = coordinator(values).execute(request=app_request)
    assert int(result.exit_code) == expected_exit
    if code is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST:
        assert result.operation_reference == app_request.operation_reference
        assert result.operational_result is None
        assert (
            result.failure.code
            is public.EditorApplicationFailureCodeV1.INVALID_EXECUTION_REQUEST
        )
        assert result.failure.safe_message == (
            "Editor operational execution request is invalid."
        )
        assert not result.failure.retryable
        assert result.lifecycle == (
            public.EditorApplicationLifecycleStateV1.ACCEPTED,
            public.EditorApplicationLifecycleStateV1.VALIDATED,
            public.EditorApplicationLifecycleStateV1.PREPARED,
            public.EditorApplicationLifecycleStateV1.EXECUTED,
            public.EditorApplicationLifecycleStateV1.FAILED,
        )
    else:
        assert result.operational_result == operational
    assert result.output_path is result.payload_sha256 is None
    assert not result.exported and not result.handoff_permitted
    if cancelled:
        assert result.status is public.EditorApplicationStatusV1.CANCELLED
        assert result.failure.code is public.EditorApplicationFailureCodeV1.CANCELLED
    elif code is not EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST:
        assert result.status is public.EditorApplicationStatusV1.FAILED
        assert (
            result.failure.code
            is public.EditorApplicationFailureCodeV1.OPERATIONAL_EXECUTION_FAILED
        )
    assert calls == ["prepare", "artifacts", "authority", "execute"]


@pytest.mark.parametrize("bad", [None, object(), "dependency"])
def test_invalid_dependency_is_configuration_error(bad: object) -> None:
    with pytest.raises(public.EditorApplicationConfigurationError):
        public.EditorApplicationCoordinatorV1(
            preparation=bad,
            artifacts=bad,
            execution_request_authority=bad,
            operational_execution=bad,
            serializer=bad,
            exporter=bad,
        )


@pytest.mark.parametrize(
    "invalid",
    (
        MissingPreparationMethod(),
        WrongCountPreparationMethod(),
        PositionalPreparationMethod(),
        WrongPreparationAnnotations(),
        ClassPreparationMethod(),
        PropertyPreparationMethod(),
        CachedPropertyPreparationMethod(),
        AbstractPreparationMethod(),
        WrappedPreparationMethod(),
        ForgedSignaturePreparationMethod(),
    ),
    ids=(
        "missing-method",
        "wrong-parameter-count",
        "positional-signature",
        "wrong-annotations",
        "classmethod",
        "property",
        "cached-property",
        "abstract-method",
        "wrapped-method",
        "forged-signature",
    ),
)
def test_dependency_validation_rejects_adversarial_descriptors_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    _, values, calls, _ = dependencies(tmp_path, monkeypatch)
    with pytest.raises(public.EditorApplicationConfigurationError):
        coordinator((invalid, *values[1:]))
    assert calls == []


def test_dependency_validation_rejects_instance_and_retained_state_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, values, calls, _ = dependencies(tmp_path, monkeypatch)
    replaced = copy.copy(values[0])
    object.__setattr__(replaced, "prepare", lambda **_: None)
    with pytest.raises(public.EditorApplicationConfigurationError):
        coordinator((replaced, *values[1:]))
    assert calls == []

    instance = coordinator(values)
    object.__setattr__(instance, "_preparation", copy.copy(values[0]))
    with pytest.raises(public.EditorApplicationConfigurationError):
        instance.execute(request=None)
    assert calls == []


def test_wrong_request_and_corrupted_retained_state_suppress_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, values, calls, _ = dependencies(tmp_path, monkeypatch)
    instance = coordinator(values)
    with pytest.raises(TypeError):
        instance.execute(None)
    result = instance.execute(request=None)
    assert (
        result.failure.code
        is public.EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST
    )
    assert calls == []
    object.__setattr__(instance, "_serializer", object())
    with pytest.raises(public.EditorApplicationConfigurationError):
        instance.execute(request=None)
    assert calls == []


def test_invalid_execution_request_rejects_blank_application_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_request, values, calls, _ = dependencies(tmp_path, monkeypatch)
    object.__setattr__(app_request, "operation_reference", "")
    result = coordinator(values).execute(request=app_request)
    assert (
        result.failure.code
        is public.EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST
    )
    assert result.operational_result is None
    assert calls == []


def test_invalid_execution_request_rejects_fabricated_lower_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operational = EditorOperationalExecutionCoordinatorV1(
        session_factory=SessionFactory(), generator_factory=GeneratorFactory()
    ).execute(object())
    object.__setattr__(operational, "source_report_id", "fabricated")
    app_request, values, calls, _ = dependencies(tmp_path, monkeypatch)
    values = (*values[:3], Execution(operational, calls), *values[4:])
    captured = None
    try:
        coordinator(values).execute(request=app_request)
    except public.EditorApplicationCoordinatorError as error:
        captured = error
    else:
        pytest.fail("fabricated lower lineage was accepted")
    assert captured is not None
    assert captured.__cause__ is captured.__context__ is None
    traceback = captured.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__") == implementation.__name__:
            assert all(
                value is not operational
                for value in traceback.tb_frame.f_locals.values()
            )
        traceback = traceback.tb_next
    assert calls == ["prepare", "artifacts", "authority", "execute"]


def test_object_safety(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, values, _, _ = dependencies(tmp_path, monkeypatch)
    instance = coordinator(values)
    assert not hasattr(instance, "__dict__")
    assert repr(instance) == "EditorApplicationCoordinatorV1(dependencies=<injected>)"
    copied = copy.copy(instance)
    assert copied == instance and copied is not instance
    assert copy.deepcopy(instance) == instance
    with pytest.raises(TypeError):
        pickle.dumps(instance)
    with pytest.raises(TypeError):
        type("Forged", (public.EditorApplicationCoordinatorV1,), {})


def test_private_completed_candidate_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_request, _, _, _ = dependencies(tmp_path, monkeypatch)
    operational = completed_result(monkeypatch)
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=operational
    )
    state = implementation._CompletedApplicationCandidateStateV1(
        operational, app_request.destination, serialized
    )
    completed = implementation._reconstruct_completed_application_candidate(state=state)
    assert completed.status is public.EditorApplicationStatusV1.COMPLETED
    object.__setattr__(state, "serialized", object())
    with pytest.raises(implementation._CompletedApplicationCandidateIntegrityError):
        implementation._reconstruct_completed_application_candidate(state=state)


def test_deterministic_artifact_builder_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, values, _, _ = dependencies(tmp_path, monkeypatch)
    plan = values[0].result.plan
    assert plan is not None
    preparer = implementation._EditorArtifactPreparerV1()
    calls: list[str] = []

    class RecordingDependency:
        def __init__(self, label: str, target: object):
            self.label, self.target = label, target

        def __getattr__(self, name: str):
            method = getattr(self.target, name)

            def invoke(*args, **kwargs):
                calls.append(self.label)
                return method(*args, **kwargs)

            return invoke

    for field, label in (
        ("_flow", "flow"),
        ("_editorial", "editorial"),
        ("_commentary", "commentary"),
        ("_voice", "voice"),
    ):
        object.__setattr__(
            preparer,
            field,
            RecordingDependency(label, object.__getattribute__(preparer, field)),
        )
    result = preparer.build(plan=plan)
    assert type(result) is _EditorDeterministicArtifactsV1
    assert calls == ["flow", "editorial", "commentary", "voice"]


def test_protocol_annotations_are_exact() -> None:
    assert LanguageGenerationConfig is not None
    assert EditorGenerationRuntimeOptionsV1 is not None
    assert ProviderChoiceV1 is not None
    assert datetime is not None
    assert FlowOptimizationResult is not None
    assert EditorialBlueprint is not None
    assert EpisodeCommentaryBlueprint is not None
    assert EpisodeVoicePlan is not None


def test_passive_fresh_import() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = "import pastila_scout.editor_application_v1 as p; print(len(p.__all__))"
    completed = subprocess.run(
        [str(root / ".venv/Scripts/python.exe"), "-c", probe],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout == "21\n"
    assert completed.stderr == ""


def test_revision_5_scope_and_frozen_integrity() -> None:
    root = Path(__file__).resolve().parents[1]
    revision_5 = "phase-4.3-editor-application-coordinator-r5-verified"
    prerequisite = (
        "phase-4.3-editor-application-frozen-integrity-r6-prerequisite-verified"
    )
    current_baseline = "phase-4.3-editor-command-time-runtime-composition-r1-verified"
    frozen_revision_5 = {
        "src/pastila_scout/editor_application_v1/__init__.py",
        "src/pastila_scout/editor_application_v1/application.py",
        "src/pastila_scout/editor_application_v1/protocols.py",
    }
    maintained_tests = {
        "tests/test_editor_application_v1.py",
        "tests/test_editor_application_serialization_v1.py",
        "tests/test_editor_application_export_v1.py",
    }
    correction_digest = (
        "1205ED67D66E4DAB32AA88664125022BEFEC657E841972595B56D4D401DE817D"
    )

    def names(*args: str) -> set[str]:
        return set(
            subprocess.run(
                ["git", *args], cwd=root, check=True, capture_output=True, text=True
            ).stdout.splitlines()
        )

    commits = {
        revision_5: "5d63e27cbc685c12611e0cf07003bfc2433988bf",
        prerequisite: "09ff8afade2be74bc93841e9eaffbd882697ec7d",
        current_baseline: "5c80d4edc402f661040035db11ad7d9785de1362",
    }
    for tag, expected in commits.items():
        actual = subprocess.run(
            ["git", "rev-parse", f"{tag}^{{}}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert actual == expected
    protected = frozen_revision_5 | maintained_tests
    assert names("ls-files", "--error-unmatch", *protected) == protected
    assert all((root / path).is_file() for path in protected)
    assert names("diff", "--name-only", revision_5, "--", *frozen_revision_5) == set()
    assert (
        names(
            "diff",
            "--name-only",
            prerequisite,
            "--",
            "tests/test_editor_application_serialization_v1.py",
            "tests/test_editor_application_export_v1.py",
        )
        == set()
    )
    assert names("diff", "--cached", "--name-only") == set()
    assert names("diff", "--name-only", f"{revision_5}^", revision_5) == (
        frozen_revision_5 | maintained_tests
    )
    assert names("diff", "--name-only", "--", *frozen_revision_5) == set()
    current_paths = names("diff", "--name-only") | names(
        "ls-files", "--others", "--exclude-standard"
    )
    assert current_paths.isdisjoint(frozen_revision_5)
    assert {"src/pastila_scout/future_phase_v1/service.py"}.isdisjoint(
        frozen_revision_5
    )
    test_bytes = (root / "tests/test_editor_application_v1.py").read_bytes()
    normalized = test_bytes.replace(correction_digest.encode(), b"0" * 64)
    assert normalized != test_bytes
    assert hashlib.sha256(normalized).hexdigest().upper() == correction_digest
    assert "_compose_editor_application_runtime_v1" not in public.__all__
    cli_revision = "phase-4.3-editor-cli-run-r6-verified"
    assert "src/pastila_scout/cli.py" in names(
        "diff", "--name-only", f"{cli_revision}^", cli_revision
    )
    assert names("diff", "--name-only", "--", "src/pastila_scout/cli.py") == set()
