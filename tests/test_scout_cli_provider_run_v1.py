"""Offline tests for the explicit provider-neutral CLI command."""

from __future__ import annotations

import copy
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from pastila_scout.cli import build_parser, main
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
)
from pastila_scout.scout_cli_provider_run_v1 import composition
from pastila_scout.scout_cli_provider_run_v1.composition import (
    _EnvironmentCredentialSource,
    _OfficialSDKFactory,
    _OpenAIClientFacade,
)
from pastila_scout.scout_cli_provider_run_v1.execution import (
    _UnavailableLegacyWorkflow,
    _UnavailableProviderExecutor,
    execute_provider_run,
)
from pastila_scout.scout_cli_provider_run_v1.rendering import render_provider_run
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1
from pastila_scout.scout_workflow_execution_v1 import ScoutWorkflowExecutionError

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 7, 10, tzinfo=UTC)
PROMPT = "Exact CLI prompt"


class _FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[ProviderExecutionRequestV2] = []

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.calls.append(request)
        return _completed(request)


class _MalformedExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        del request
        self.calls += 1
        return object()  # type: ignore[return-value]


def _request(choice: ProviderChoiceV1) -> ProviderExecutionRequestV2:
    return ApplicationRequestAuthorityV1().build(
        ApplicationProviderRequestV1(
            choice,
            PROMPT,
            "cli-test-request",
            NOW,
            TimeoutPolicyV2(timeout_seconds=30.0),
            CancellationTokenV2(cancellation_requested=False),
        )
    )


def _completed(request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
    source = request.request_envelope.request_units[0].source_request_reference
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=ExecutionOutcomeV2.COMPLETED,
        finished_at=NOW,
        provider_result=ProviderResultProjectionV2(
            status=ProviderResultStatusV2.SUCCESS,
            outputs=(
                ProviderOutputInputV2(
                    source_request_reference=source,
                    ordinal=0,
                    generated_text="Generated CLI output",
                    finish_reason=ProviderFinishReasonV2.COMPLETED,
                ),
            ),
        ),
    )


def _failure(
    request: ProviderExecutionRequestV2, outcome: ExecutionOutcomeV2
) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=outcome,
        finished_at=NOW,
        failure_code=f"test-{outcome.value}",
        failure_message="Safe provider-neutral failure.",
    )


def test_command_is_registered_with_required_exact_arguments() -> None:
    parser = build_parser()
    arguments = parser.parse_args(
        ["provider-run", "--provider", "openai", "--prompt", PROMPT]
    )
    assert arguments.command == "provider-run"
    assert arguments.provider == "openai"
    assert arguments.prompt == PROMPT


@pytest.mark.parametrize(
    "arguments",
    (
        ("provider-run", "--prompt", PROMPT),
        ("provider-run", "--provider", "openai"),
        ("provider-run", "--provider", "OPENAI", "--prompt", PROMPT),
        ("provider-run", "--provider", "auto", "--prompt", PROMPT),
        ("provider-run", "--provider", "local", "--prompt", PROMPT),
    ),
)
def test_missing_and_invalid_arguments_are_rejected_by_parser(arguments) -> None:
    with pytest.raises(SystemExit) as captured:
        build_parser().parse_args(arguments)
    assert captured.value.code == 2


@pytest.mark.parametrize("choice", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_verified_chain_executes_selected_fake_once_and_preserves_prompt(
    choice,
) -> None:
    request = _request(choice)
    executor = _FakeExecutor()

    result = execute_provider_run(
        provider=choice, provider_request=request, selected_executor=executor
    )

    assert len(executor.calls) == 1
    assert (
        executor.calls[0].request_intent.request_units[0].messages[0].content == PROMPT
    )
    assert result.provider_result == _completed(request)
    assert result.provider_result is not executor.calls[0]


@pytest.mark.parametrize(
    ("choice", "runner_name"),
    (
        (ProviderChoiceV1.OPENAI, "_run_openai"),
        (ProviderChoiceV1.OLLAMA, "_run_ollama"),
    ),
)
def test_cli_end_to_end_uses_one_selected_executor(
    monkeypatch, capsys, choice, runner_name
) -> None:
    executor = _FakeExecutor()
    runner_calls = []

    def fake_runner(provider, request):
        runner_calls.append((provider, request))
        return execute_provider_run(
            provider=provider, provider_request=request, selected_executor=executor
        )

    monkeypatch.setattr(composition, runner_name, fake_runner)
    code = main(["provider-run", "--provider", choice.value, "--prompt", PROMPT])

    assert code == 0
    assert len(runner_calls) == len(executor.calls) == 1
    assert (
        executor.calls[0].request_intent.request_units[0].messages[0].content == PROMPT
    )
    assert capsys.readouterr().out == (
        f"Provider: {choice.value}\n"
        "Outcome: completed\n"
        "Status: success\n"
        "Output: Generated CLI output\n"
    )


@pytest.mark.parametrize(
    ("outcome", "exit_code"),
    (
        (ExecutionOutcomeV2.PROVIDER_FAILURE, 3),
        (ExecutionOutcomeV2.TIMEOUT, 4),
        (ExecutionOutcomeV2.CANCELLED, 5),
        (ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE, 6),
    ),
)
def test_failure_outcomes_have_stable_rendering_and_exit_codes(
    outcome, exit_code
) -> None:
    request = _request(ProviderChoiceV1.OPENAI)
    result = ScoutRuntimeResultV1(_failure(request, outcome))

    actual_code, lines = render_provider_run(ProviderChoiceV1.OPENAI, result)

    assert actual_code == exit_code
    assert lines == (
        "Provider: openai",
        f"Outcome: {outcome.value}",
        f"Failure code: test-{outcome.value}",
        "Failure: provider execution failed",
    )


def test_partial_provider_semantics_are_explicit_and_nonzero() -> None:
    request = _request(ProviderChoiceV1.OPENAI)
    source = request.request_envelope.request_units[0].source_request_reference
    result = ScoutRuntimeResultV1(
        ProviderExecutionResultV2(
            request_id=request.context.request_id,
            provider_id=request.provider.provider_id,
            request_envelope_identity=request.request_envelope.identity,
            outcome=ExecutionOutcomeV2.COMPLETED,
            finished_at=NOW,
            provider_result=ProviderResultProjectionV2(
                status=ProviderResultStatusV2.PARTIAL,
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference=source,
                        ordinal=0,
                        generated_text="Partial output",
                        finish_reason=ProviderFinishReasonV2.LENGTH,
                    ),
                ),
                failure_code="output-length",
            ),
        )
    )

    code, lines = render_provider_run(ProviderChoiceV1.OPENAI, result)

    assert code == 3
    assert lines == (
        "Provider: openai",
        "Outcome: completed",
        "Status: partial",
        "Output: Partial output",
        "Failure code: output-length",
        "Failure: provider execution was not fully successful",
    )


def test_failure_rendering_never_exposes_provider_message() -> None:
    request = _request(ProviderChoiceV1.OLLAMA)
    failure = _failure(request, ExecutionOutcomeV2.PROVIDER_FAILURE).model_copy(
        update={"failure_message": "secret credential and raw transport host"}
    )

    code, lines = render_provider_run(
        ProviderChoiceV1.OLLAMA, ScoutRuntimeResultV1(failure)
    )

    assert code == 3
    assert "secret" not in "\n".join(lines)
    assert "transport" not in "\n".join(lines)


def test_timestamp_is_read_once_and_produces_distinct_request_authority(
    monkeypatch, capsys
) -> None:
    timestamps = iter((NOW, NOW.replace(second=1)))
    clock_calls = []
    requests = []

    class FixedDateTime:
        @classmethod
        def now(cls, timezone):
            clock_calls.append(timezone)
            return next(timestamps)

    def fake_runner(provider, request):
        requests.append(request)
        return execute_provider_run(
            provider=provider,
            provider_request=request,
            selected_executor=_FakeExecutor(),
        )

    monkeypatch.setattr(composition, "datetime", FixedDateTime)
    monkeypatch.setattr(composition, "_run_openai", fake_runner)

    for _ in range(2):
        assert main(["provider-run", "--provider", "openai", "--prompt", PROMPT]) == 0
    capsys.readouterr()

    assert clock_calls == [UTC, UTC]
    assert requests[0].context.request_id != requests[1].context.request_id
    assert requests[0].context.requested_at == NOW
    assert requests[1].context.requested_at == NOW.replace(second=1)


def test_multiline_unicode_prompt_reaches_authority_and_executor_exactly(
    monkeypatch, capsys
) -> None:
    prompt = "Răspunde exact:\nBună ziua"
    executor = _FakeExecutor()
    observed = []
    original_authority = composition.ApplicationRequestAuthorityV1

    class CountingAuthority:
        def build(self, request):
            observed.append(request)
            return original_authority().build(request)

    def fake_runner(provider, request):
        return execute_provider_run(
            provider=provider,
            provider_request=request,
            selected_executor=executor,
        )

    monkeypatch.setattr(composition, "ApplicationRequestAuthorityV1", CountingAuthority)
    monkeypatch.setattr(composition, "_run_ollama", fake_runner)

    assert main(["provider-run", "--provider", "ollama", "--prompt", prompt]) == 0
    capsys.readouterr()
    assert len(observed) == len(executor.calls) == 1
    assert observed[0].prompt == prompt
    assert (
        executor.calls[0].request_intent.request_units[0].messages[0].content == prompt
    )


@pytest.mark.parametrize("malformed", (False, True))
def test_openai_runtime_cleanup_occurs_exactly_once(monkeypatch, malformed) -> None:
    request = _request(ProviderChoiceV1.OPENAI)
    executor = _MalformedExecutor() if malformed else _FakeExecutor()

    class Runtime:
        def __init__(self):
            self.executor = executor
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    runtime = Runtime()

    class Composer:
        def __init__(self, config, *, credential_source, sdk_factory):
            del config, credential_source, sdk_factory

        def compose(self):
            return runtime

    class BridgedComposer:
        def __init__(self, base_composer):
            self.base_composer = base_composer

        def compose(self):
            return self.base_composer.compose()

    monkeypatch.setattr(composition, "OpenAIRuntimeComposerV2", Composer)
    monkeypatch.setattr(
        composition, "_load_openai_bridged_composer", lambda: BridgedComposer
    )
    if malformed:
        with pytest.raises(ScoutWorkflowExecutionError):
            composition._run_openai(ProviderChoiceV1.OPENAI, request)
    else:
        composition._run_openai(ProviderChoiceV1.OPENAI, request)
    assert runtime.close_calls == 1


@pytest.mark.parametrize("malformed", (False, True))
def test_ollama_owned_client_cleanup_occurs_exactly_once(
    monkeypatch, malformed
) -> None:
    request = _request(ProviderChoiceV1.OLLAMA)
    executor = _MalformedExecutor() if malformed else _FakeExecutor()

    class ClientContext:
        def __init__(self):
            self.enter_calls = 0
            self.exit_calls = 0

        def __enter__(self):
            self.enter_calls += 1
            return object()

        def __exit__(self, *exception):
            del exception
            self.exit_calls += 1

    client = ClientContext()
    monkeypatch.setattr(composition.httpx, "Client", lambda: client)
    monkeypatch.setattr(composition, "OllamaHttpClientV1", lambda raw: raw)
    monkeypatch.setattr(
        composition,
        "OllamaProviderExecutorV1",
        lambda wrapped, config: executor,
    )
    if malformed:
        with pytest.raises(ScoutWorkflowExecutionError):
            composition._run_ollama(ProviderChoiceV1.OLLAMA, request)
    else:
        composition._run_ollama(ProviderChoiceV1.OLLAMA, request)
    assert client.enter_calls == client.exit_calls == 1


@pytest.mark.parametrize(
    "dependency",
    (
        _EnvironmentCredentialSource(),
        _OfficialSDKFactory(),
        _UnavailableLegacyWorkflow(),
        _UnavailableProviderExecutor(),
    ),
)
def test_internal_dependencies_have_safe_identity_copy_and_pickle_policies(
    dependency,
) -> None:
    assert copy.copy(dependency) is dependency
    assert copy.deepcopy(dependency) is dependency
    assert "0x" not in repr(dependency)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(dependency)


def test_cli_sdk_factory_materializes_lazy_responses_for_verified_handoff() -> None:
    composer = composition.OpenAIRuntimeComposerV2(
        composition.OpenAIRuntimeConfigV2(
            model="gpt-4.1-mini",
            enabled=True,
            max_retries=0,
            request_timeout_seconds=30.0,
        ),
        credential_source=type(
            "CredentialSource",
            (),
            {"get_api_key": lambda self: "sk-offline-placeholder"},
        )(),
        sdk_factory=_OfficialSDKFactory(),
    )

    runtime = composer.compose()
    runtime.close()


def test_sdk_client_facade_has_safe_identity_copy_and_pickle_policies() -> None:
    class RawClient:
        def __init__(self):
            self.responses = object()

        def close(self):
            pass

    facade = _OpenAIClientFacade(RawClient())

    assert copy.copy(facade) is facade
    assert copy.deepcopy(facade) is facade
    assert "0x" not in repr(facade)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(facade)


def test_malformed_executor_result_is_safe_with_no_retry_or_fallback(
    monkeypatch, capsys
) -> None:
    calls = []
    executor = _MalformedExecutor()

    def malformed(provider, request):
        calls.append((provider, request))
        return execute_provider_run(
            provider=provider,
            provider_request=request,
            selected_executor=executor,
        )

    monkeypatch.setattr(composition, "_run_openai", malformed)
    assert main(["provider-run", "--provider", "openai", "--prompt", PROMPT]) == 2
    assert len(calls) == executor.calls == 1
    assert capsys.readouterr().out == "Provider run error: execution failed\n"


def test_missing_openai_credential_fails_safely_before_sdk_construction(
    monkeypatch, capsys
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert main(["provider-run", "--provider", "openai", "--prompt", PROMPT]) == 2
    assert capsys.readouterr().out == "Provider run error: execution failed\n"


def test_invalid_prompt_and_ollama_unavailability_are_safe(monkeypatch, capsys) -> None:
    assert main(["provider-run", "--provider", "ollama", "--prompt", " padded"]) == 2
    assert capsys.readouterr().out == "Provider run error: execution failed\n"

    def unavailable(provider, request):
        del provider, request
        raise RuntimeError("raw connection detail")

    monkeypatch.setattr(composition, "_run_ollama", unavailable)
    assert main(["provider-run", "--provider", "ollama", "--prompt", PROMPT]) == 2
    assert capsys.readouterr().out == "Provider run error: execution failed\n"


def test_help_is_passive_and_does_not_import_new_composition() -> None:
    script = """
import sys
from pastila_scout.cli import main
try:
    main(['--help'])
except SystemExit as error:
    assert error.code == 0
assert 'pastila_scout.scout_cli_provider_run_v1' not in sys.modules
assert 'pastila_scout.scout_cli_provider_run_v1.composition' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-W", "error", "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "provider-run" in completed.stdout


def test_existing_command_parser_semantics_remain_available() -> None:
    parser = build_parser()
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["poll-once"]).command == "poll-once"
    assert parser.parse_args(["validate-config"]).command == "validate-config"
