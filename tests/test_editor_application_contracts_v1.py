from __future__ import annotations

import copy
import hashlib
import json
import pickle
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from test_editor_operational_execution_v1 import (
    controlled_output,
    execute_fake,
    observation,
)

import pastila_scout.editor_application_v1 as public
from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
)
from pastila_scout.editor_application_v1 import (
    EditorApplicationConfigurationError,
    EditorApplicationCoordinatorError,
    EditorApplicationExitCodeV1,
    EditorApplicationExportError,
    EditorApplicationFailureCodeV1,
    EditorApplicationFailureV1,
    EditorApplicationGenerationConfigurationAuthorityV1,
    EditorApplicationGenerationConfigurationV1,
    EditorApplicationLifecycleStateV1,
    EditorApplicationRequestV1,
    EditorApplicationResultV1,
    EditorApplicationSerializationError,
    EditorApplicationStatusV1,
    EditorEpisodeContextAuthorityV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
    EditorSelectionProfileAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2, ExecutionOutcomeV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

EXPECTED_API = (
    "EditorApplicationConfigurationError",
    "EditorApplicationCoordinatorError",
    "EditorApplicationExitCodeV1",
    "EditorApplicationExportError",
    "EditorApplicationFailureCodeV1",
    "EditorApplicationFailureV1",
    "EditorApplicationGenerationConfigurationV1",
    "EditorApplicationGenerationConfigurationAuthorityV1",
    "EditorApplicationLifecycleStateV1",
    "EditorApplicationRequestV1",
    "EditorApplicationResultV1",
    "EditorApplicationSerializationError",
    "EditorApplicationStatusV1",
    "EditorEpisodeContextAuthorityV1",
    "EditorOutputDestinationV1",
    "EditorOverwritePolicyV1",
    "EditorSelectionProfileAuthorityV1",
)


def generation_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "contract_version": "editor-application-generation-config-v1",
        "provider": ProviderChoiceV1.OPENAI,
        "model_identifier": "gpt-4.1-mini",
        "model_revision": None,
        "temperature": 0.25,
        "top_p": 1.0,
        "max_output_tokens": 1024,
        "seed": None,
        "structured_output_mode": True,
        "timeout_seconds": 30.0,
    }
    values.update(changes)
    return values


def generation(**changes: object) -> EditorApplicationGenerationConfigurationV1:
    return EditorApplicationGenerationConfigurationV1(
        *generation_values(**changes).values()
    )


def destination(tmp_path: Path) -> EditorOutputDestinationV1:
    return EditorOutputDestinationV1(
        tmp_path / "editor-output.json", EditorOverwritePolicyV1.FAIL_IF_EXISTS
    )


def request(tmp_path: Path, **changes: object) -> EditorApplicationRequestV1:
    values: dict[str, object] = {
        "scout_input": sample_scout_input(),
        "selection_profile": sample_selection_profile(),
        "episode_context": sample_episode_context(),
        "generation_configuration": generation(),
        "destination": destination(tmp_path),
        "requested_at": datetime(2026, 8, 5, 12, 0, tzinfo=UTC),
        "operation_reference": "editor-application-operation-1",
        "cancellation": CancellationTokenV2(cancellation_requested=False),
    }
    values.update(changes)
    return EditorApplicationRequestV1(*values.values())


def failure(code: EditorApplicationFailureCodeV1) -> EditorApplicationFailureV1:
    messages = {
        EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST: "Editor application request is invalid.",
        EditorApplicationFailureCodeV1.PREPARATION_FAILED: "Editor preparation failed.",
        EditorApplicationFailureCodeV1.CANCELLED: "Editor application execution was cancelled.",
    }
    return EditorApplicationFailureV1(code, messages[code], False)


def test_exact_revision_2_public_api_and_passive_import() -> None:
    assert public.__all__ == EXPECTED_API
    assert all(getattr(public, name) is not None for name in EXPECTED_API)


@pytest.mark.parametrize(
    "error_type",
    [
        EditorApplicationConfigurationError,
        EditorApplicationCoordinatorError,
        EditorApplicationSerializationError,
        EditorApplicationExportError,
    ],
)
def test_public_errors_are_fixed_safe_and_nonserializable(error_type: type) -> None:
    error = error_type()
    assert "0x" not in repr(error)
    assert not hasattr(error, "__dict__")
    assert copy.copy(error) is not error
    assert copy.deepcopy(error) is not error
    with pytest.raises(TypeError):
        pickle.dumps(error)


def test_configuration_authorities_reconstruct_exact_frozen_contracts() -> None:
    profile = sample_selection_profile()
    context = sample_episode_context()
    assert EditorSelectionProfileAuthorityV1().reconstruct(profile=profile) == profile
    assert EditorEpisodeContextAuthorityV1().reconstruct(context=context) == context


def test_profile_and_context_authorities_load_and_reject_forged_state(
    tmp_path: Path,
) -> None:
    profile = sample_selection_profile()
    context = sample_episode_context()
    profile_path = tmp_path / "profile.json"
    context_path = tmp_path / "context.json"
    profile_path.write_text(profile.model_dump_json(), encoding="utf-8")
    context_path.write_text(context.model_dump_json(), encoding="utf-8")
    assert EditorSelectionProfileAuthorityV1().load(path=profile_path) == profile
    assert EditorEpisodeContextAuthorityV1().load(path=context_path) == context

    forged_profile = profile.model_copy(deep=True)
    object.__setattr__(forged_profile, "target_story_count", 0)
    with pytest.raises(EditorApplicationConfigurationError):
        EditorSelectionProfileAuthorityV1().reconstruct(profile=forged_profile)
    forged_context = context.model_copy(deep=True)
    object.__setattr__(forged_context, "language", "e\u0301")
    with pytest.raises(EditorApplicationConfigurationError):
        EditorEpisodeContextAuthorityV1().reconstruct(context=forged_context)


def test_authorities_are_safe_stateless_values() -> None:
    for authority in (
        EditorSelectionProfileAuthorityV1(),
        EditorEpisodeContextAuthorityV1(),
        EditorApplicationGenerationConfigurationAuthorityV1(),
    ):
        assert not hasattr(authority, "__dict__")
        assert "0x" not in repr(authority)
        assert copy.copy(authority) == authority
        assert copy.deepcopy(authority) == authority
        with pytest.raises(TypeError):
            pickle.dumps(authority)
        with pytest.raises(TypeError):
            type("ForgedAuthority", (type(authority),), {})


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("temperature", 1),
        ("temperature", True),
        ("temperature", float("nan")),
        ("temperature", float("inf")),
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("temperature", Decimal("1.0")),
        ("temperature", Fraction(1, 2)),
        ("temperature", type("FloatSubclass", (float,), {})(1.0)),
        ("top_p", 1),
        ("top_p", 0.5),
        ("top_p", float("nan")),
        ("max_output_tokens", True),
        ("max_output_tokens", 0),
        ("seed", 1),
        ("structured_output_mode", False),
        ("timeout_seconds", 30),
        ("timeout_seconds", 0.0),
        ("timeout_seconds", float("inf")),
        ("provider", "openai"),
        ("model_identifier", " e"),
        ("model_identifier", "e\u0301"),
    ],
)
def test_generation_configuration_rejects_invalid_numeric_authority(
    field: str, bad: object
) -> None:
    with pytest.raises(EditorApplicationConfigurationError) as caught:
        generation(**{field: bad})
    assert caught.value.__traceback__ is not None
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert caught.value.__context__ is None
    assert "0x" not in repr(caught.value)


def test_generation_configuration_materializes_exact_lower_pair() -> None:
    source = generation()
    materialized = EditorApplicationGenerationConfigurationAuthorityV1()._materialize(
        configuration=source
    )
    lower = materialized.generation_configuration
    options = materialized.runtime_options
    assert lower.provider == options.provider.value == source.provider.value
    assert lower.model_identifier == options.model_identifier == source.model_identifier
    assert lower.temperature == options.temperature == source.temperature
    assert lower.top_p == options.top_p == source.top_p == 1.0
    assert lower.max_output_tokens == options.max_output_tokens == 1024
    assert options.stop_sequences == ()
    assert lower.timeout_seconds == options.timeout_policy.timeout_seconds == 30.0


def test_generation_json_loader_is_ordered_strict_and_token_sensitive(
    tmp_path: Path,
) -> None:
    values = generation_values(provider="openai")
    path = tmp_path / "generation.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    loaded = EditorApplicationGenerationConfigurationAuthorityV1().load(path=path)
    assert loaded == generation()

    integer_token = path.read_text(encoding="utf-8").replace("0.25", "1", 1)
    path.write_text(integer_token, encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationGenerationConfigurationAuthorityV1().load(path=path)

    duplicate = json.dumps(values)[:-1] + ', "provider": "openai"}'
    path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationGenerationConfigurationAuthorityV1().load(path=path)


def test_generation_json_loader_rejects_extra_reordered_and_oversize(
    tmp_path: Path,
) -> None:
    authority = EditorApplicationGenerationConfigurationAuthorityV1()
    path = tmp_path / "generation.json"
    values = generation_values(provider="openai")
    path.write_text(json.dumps({"extra": 1, **values}), encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError):
        authority.load(path=path)
    reversed_values = dict(reversed(tuple(values.items())))
    path.write_text(json.dumps(reversed_values), encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError):
        authority.load(path=path)
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(EditorApplicationConfigurationError):
        authority.load(path=path)


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        "null",
        json.dumps({"contract_version": "wrong"}),
        json.dumps(
            {
                key: value
                for key, value in generation_values(provider="openai").items()
                if key != "seed"
            }
        ),
    ],
)
def test_generation_json_loader_rejects_malformed_root_version_and_missing(
    tmp_path: Path, payload: str
) -> None:
    path = tmp_path / "invalid-generation.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationGenerationConfigurationAuthorityV1().load(path=path)


def test_generation_json_loader_rejects_symbolic_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "generation-target.json"
    link = tmp_path / "generation-link.json"
    target.write_text(
        json.dumps(generation_values(provider="openai")), encoding="utf-8"
    )
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda value: value == link or original(value),
    )
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationGenerationConfigurationAuthorityV1().load(path=link)


def test_request_reconstructs_nested_authority_and_preserves_external_history_ids(
    tmp_path: Path,
) -> None:
    original = request(tmp_path)
    rebuilt = copy.copy(original)
    assert rebuilt == original
    assert rebuilt is not original
    assert rebuilt.scout_input is not original.scout_input
    assert rebuilt.selection_profile is not original.selection_profile
    assert rebuilt.episode_context is not original.episode_context
    assert rebuilt.operation_reference == "editor-application-operation-1"
    assert "content=<redacted>" in repr(rebuilt)
    assert str(tmp_path) not in repr(rebuilt)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("requested_at", datetime(2026, 8, 5, 12, 0)),  # noqa: DTZ001
        ("operation_reference", " leading"),
        ("operation_reference", "e\u0301"),
        ("operation_reference", "x" * 121),
        ("cancellation", object()),
    ],
)
def test_request_rejects_invalid_live_authority(
    tmp_path: Path, field: str, bad: object
) -> None:
    with pytest.raises(EditorApplicationConfigurationError):
        request(tmp_path, **{field: bad})


def test_request_rejects_target_count_and_mandatory_lineage_mismatch(
    tmp_path: Path,
) -> None:
    context = sample_episode_context().model_copy(
        update={"target_story_count": 2, "mandatory_event_ids": (999,)}, deep=True
    )
    with pytest.raises(EditorApplicationConfigurationError):
        request(tmp_path, episode_context=context)


def test_destination_is_lexical_passive_redacted_and_strict(tmp_path: Path) -> None:
    target = tmp_path / "missing-parent" / "draft.json"
    valid = EditorOutputDestinationV1(target, EditorOverwritePolicyV1.FAIL_IF_EXISTS)
    assert valid.path == target
    assert not target.parent.exists()
    assert str(target) not in repr(valid)
    with pytest.raises(EditorApplicationConfigurationError):
        EditorOutputDestinationV1(
            Path("relative.json"), EditorOverwritePolicyV1.FAIL_IF_EXISTS
        )
    with pytest.raises(EditorApplicationConfigurationError):
        EditorOutputDestinationV1(target, "fail_if_exists")


def test_copied_invalid_state_is_rejected(tmp_path: Path) -> None:
    configuration = generation()
    object.__setattr__(configuration, "temperature", 1.5)
    with pytest.raises(EditorApplicationConfigurationError):
        copy.copy(configuration)
    destination_value = destination(tmp_path)
    object.__setattr__(destination_value, "path", Path("relative"))
    with pytest.raises(EditorApplicationConfigurationError):
        copy.deepcopy(destination_value)
    application_request = request(tmp_path)
    object.__setattr__(application_request, "operation_reference", "tampered")
    with pytest.raises(EditorApplicationConfigurationError):
        repr(application_request)


def test_recursive_traceback_isolation_clears_protected_authority(
    tmp_path: Path,
) -> None:
    secret = "protected-model-credential-like-value"
    path = tmp_path / "generation-secret.json"
    values = generation_values(provider="openai", model_identifier=secret)
    path.write_text(json.dumps({"unexpected": secret, **values}), encoding="utf-8")
    with pytest.raises(EditorApplicationConfigurationError) as caught:
        EditorApplicationGenerationConfigurationAuthorityV1().load(path=path)
    error = caught.value
    assert error.__context__ is None
    assert error.__cause__ is None
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").startswith(
            "pastila_scout.editor_application_v1"
        ):
            rendered = repr(traceback.tb_frame.f_locals)
            assert secret not in rendered
            assert str(path) not in rendered
        traceback = traceback.tb_next


def test_new_models_are_frozen_slotted_copy_safe_and_pickle_rejecting(
    tmp_path: Path,
) -> None:
    values = [generation(), destination(tmp_path), request(tmp_path)]
    for value in values:
        assert not hasattr(value, "__dict__")
        assert copy.copy(value) == value
        assert copy.copy(value) is not value
        assert copy.deepcopy(value) == value
        with pytest.raises(TypeError):
            pickle.dumps(value)


@pytest.mark.parametrize(
    "model",
    [
        EditorApplicationFailureV1,
        EditorApplicationGenerationConfigurationV1,
        EditorOutputDestinationV1,
        EditorApplicationRequestV1,
        EditorApplicationResultV1,
    ],
)
def test_application_values_reject_subclasses(model: type) -> None:
    with pytest.raises(TypeError):
        type("ForgedApplicationValue", (model,), {})


def test_failure_contract_is_closed_and_safe() -> None:
    valid = failure(EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST)
    assert (
        repr(valid) == "EditorApplicationFailureV1(code='invalid_application_request')"
    )
    assert copy.copy(valid) == valid
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationFailureV1(
            EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST,
            "attacker-controlled detail",
            False,
        )
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationFailureV1(
            EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST,
            "Editor application request is invalid.",
            True,
        )


def test_result_invalid_input_and_initial_cancellation_are_closed() -> None:
    invalid = EditorApplicationResultV1(
        None,
        EditorApplicationStatusV1.FAILED,
        (
            EditorApplicationLifecycleStateV1.ACCEPTED,
            EditorApplicationLifecycleStateV1.FAILED,
        ),
        None,
        None,
        None,
        False,
        False,
        failure(EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST),
        EditorApplicationExitCodeV1.INVALID_INPUT,
    )
    cancelled = EditorApplicationResultV1(
        "operation-1",
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
        failure(EditorApplicationFailureCodeV1.CANCELLED),
        EditorApplicationExitCodeV1.CANCELLED,
    )
    assert copy.copy(invalid) == invalid
    assert copy.deepcopy(cancelled) == cancelled
    assert "0x" not in repr(invalid)
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationResultV1(
            None,
            EditorApplicationStatusV1.FAILED,
            invalid.lifecycle,
            None,
            Path("secret"),
            None,
            False,
            False,
            invalid.failure,
            EditorApplicationExitCodeV1.INVALID_INPUT,
        )


def test_result_accepts_nested_destination_reconstruction_failure() -> None:
    destination_failure = EditorApplicationFailureV1(
        EditorApplicationFailureCodeV1.INVALID_DESTINATION,
        "Editor output destination is invalid.",
        False,
    )
    result = EditorApplicationResultV1(
        None,
        EditorApplicationStatusV1.FAILED,
        (
            EditorApplicationLifecycleStateV1.ACCEPTED,
            EditorApplicationLifecycleStateV1.FAILED,
        ),
        None,
        None,
        None,
        False,
        False,
        destination_failure,
        EditorApplicationExitCodeV1.INVALID_INPUT,
    )
    assert result.operation_reference is None
    assert result.failure == destination_failure


def test_completed_and_sole_internal_result_invariants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    operational, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=controlled_output(),
    )
    reference = operational.execution_request_reference
    completed = EditorApplicationResultV1(
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
    assert copy.copy(completed) == completed
    internal = EditorApplicationResultV1(
        reference,
        EditorApplicationStatusV1.FAILED,
        (
            EditorApplicationLifecycleStateV1.ACCEPTED,
            EditorApplicationLifecycleStateV1.VALIDATED,
            EditorApplicationLifecycleStateV1.PREPARED,
            EditorApplicationLifecycleStateV1.EXECUTED,
            EditorApplicationLifecycleStateV1.SERIALIZED,
            EditorApplicationLifecycleStateV1.FAILED,
        ),
        operational,
        None,
        None,
        False,
        False,
        EditorApplicationFailureV1(
            EditorApplicationFailureCodeV1.INTERNAL_APPLICATION_FAILURE,
            "Editor application execution failed.",
            False,
        ),
        EditorApplicationExitCodeV1.CLEANUP_OR_INTERNAL_FAILURE,
    )
    assert internal.operational_result == operational
    with pytest.raises(EditorApplicationConfigurationError):
        EditorApplicationResultV1(
            "foreign-operation",
            completed.status,
            completed.lifecycle,
            operational,
            completed.output_path,
            completed.payload_sha256,
            True,
            True,
            None,
            completed.exit_code,
        )


def test_no_provider_execution_or_runtime_side_effects_are_owned() -> None:
    assert not any(
        name in vars(public)
        for name in ("OpenAI", "Ollama", "ProviderSelectorV1", "ControlledGenerator")
    )


def test_fresh_process_determinism_and_network_passivity() -> None:
    probe = (
        "import socket;"
        "socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network'));"
        "import pastila_scout.editor_application_v1 as p;"
        "from pastila_scout.provider_selection_v1 import ProviderChoiceV1;"
        "c=p.EditorApplicationGenerationConfigurationV1("
        "'editor-application-generation-config-v1',ProviderChoiceV1.OPENAI,"
        "'model',None,0.25,1.0,100,None,True,30.0);"
        "print(repr(c));print(tuple(x.value for x in p.EditorApplicationExitCodeV1))"
    )
    root = Path(__file__).resolve().parents[1]
    outputs = []
    for seed in ("1", "8675309"):
        environment = {"PYTHONHASHSEED": seed}
        completed = subprocess.run(
            [str(root / ".venv" / "Scripts" / "python.exe"), "-c", probe],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stderr == ""
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


def test_current_revision_git_scope_and_frozen_specification_are_exact() -> None:
    root = Path(__file__).resolve().parents[1]

    def names(*arguments: str) -> set[str]:
        return set(
            subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )

    expected_additions = {
        "src/pastila_scout/editor_application_v1/__init__.py",
        "src/pastila_scout/editor_application_v1/configuration.py",
        "src/pastila_scout/editor_application_v1/errors.py",
        "src/pastila_scout/editor_application_v1/models.py",
        "tests/test_editor_application_contracts_v1.py",
    }
    assert names("ls-files", "--others", "--exclude-standard") == expected_additions
    assert names("diff", "--name-only") == {
        "tests/test_editor_generation_execution_request_authority_v1.py"
    }
    assert names("diff", "--cached", "--name-only") == set()
    specification = (
        root
        / "docs"
        / "editorial-application"
        / "EditorApplicationCompositionSpecificationV1.md"
    )
    assert (
        names(
            "diff",
            "--name-only",
            "phase-4.3-editor-application-composition-spec-v4-ready",
            "--",
            specification.relative_to(root).as_posix(),
        )
        == set()
    )
    assert hashlib.sha256(specification.read_bytes()).hexdigest().upper() == (
        "3E6F08B53A2A39894C79C965EFE9B33DAEA492F1EAD9BA1750E86BD080EF0A0C"
    )
