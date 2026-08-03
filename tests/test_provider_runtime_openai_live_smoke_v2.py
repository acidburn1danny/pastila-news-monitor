from __future__ import annotations

import copy
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from functools import cached_property, partial, wraps
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.provider_runtime_openai_live_smoke_v2 as public_api
import pastila_scout.provider_runtime_openai_live_smoke_v2.runner as runner_module
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_execution_v2 import ProviderExecutionResultV2
from pastila_scout.provider_runtime_openai_bridged_v2 import (
    OpenAIBridgedRuntimeComposerV2,
)
from pastila_scout.provider_runtime_openai_bridged_v2 import (
    composition as bridged_composition,
)
from pastila_scout.provider_runtime_openai_live_smoke_v2 import (
    OpenAILiveSmokeConfigurationError,
    OpenAILiveSmokeConfigurationV2,
    OpenAILiveSmokeDependencyError,
    OpenAILiveSmokeError,
    OpenAILiveSmokeLifecycleError,
    OpenAILiveSmokeResultV2,
    OpenAILiveSmokeRunnerV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeConfigV2,
)
from pastila_scout.provider_runtime_openai_v2.composition import _mint_factory_handoff
from pastila_scout.provider_smoke_request_authority_v2 import (
    SmokeProviderExecutionRequestAuthorityV2,
    build_canonical_smoke_execution_plan,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 3, 12, tzinfo=UTC)


class _CredentialSource:
    def __init__(self) -> None:
        self.calls = 0

    def get_api_key(self) -> str:
        self.calls += 1
        return "offline-synthetic-key"


class _Responses:
    def __init__(
        self,
        *,
        text: str = "SMOKE_OK",
        fail: bool = False,
        mode: str = "success",
        execution_error: BaseException | None = None,
    ) -> None:
        self.calls = 0
        self.text = text
        self.fail = fail
        self.mode = mode
        self.execution_error = execution_error
        self.arguments: dict[str, object] | None = None

    def create(self, **arguments: object) -> object:
        self.calls += 1
        self.arguments = arguments
        if self.execution_error is not None:
            raise self.execution_error
        if self.fail:
            raise RuntimeError("private offline capability failure")
        status = "incomplete" if self.mode in {"length", "filtered"} else "completed"
        details = None
        if self.mode == "length":
            details = {"reason": "max_output_tokens"}
        elif self.mode == "filtered":
            details = {"reason": "content_filter"}
        output_count = {"zero": 0, "multiple": 2}.get(self.mode, 1)
        return {
            "id": "offline-response",
            "model": "gpt-offline",
            "created_at": NOW.timestamp(),
            "status": status,
            "incomplete_details": details,
            "output": [
                {
                    "type": "message",
                    "status": status,
                    "content": [{"type": "output_text", "text": self.text}],
                }
                for _ in range(output_count)
            ],
        }


class _RawClient:
    def __init__(
        self,
        responses: _Responses,
        *,
        fail_close: bool = False,
        close_error: BaseException | None = None,
    ) -> None:
        self.responses = responses
        self.fail_close = fail_close
        self.close_error = close_error
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error
        if self.fail_close:
            raise RuntimeError("private offline cleanup failure")


class _Factory:
    def __init__(
        self,
        *,
        text: str = "SMOKE_OK",
        fail: bool = False,
        fail_close: bool = False,
        mode: str = "success",
        execution_error: BaseException | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        self.calls = 0
        self.responses = _Responses(
            text=text, fail=fail, mode=mode, execution_error=execution_error
        )
        self.client = _RawClient(
            self.responses, fail_close=fail_close, close_error=close_error
        )

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        assert api_key == "offline-synthetic-key"
        assert max_retries == 0
        assert request_timeout_seconds == 13
        self.calls += 1
        return _mint_factory_handoff(self.client)

    def close_client(self, client: object) -> None:
        del client
        raise AssertionError("obsolete cleanup path")


def _runner(
    *,
    text: str = "SMOKE_OK",
    fail: bool = False,
    fail_close: bool = False,
    mode: str = "success",
    execution_error: BaseException | None = None,
    close_error: BaseException | None = None,
) -> tuple[OpenAILiveSmokeRunnerV2, _CredentialSource, _Factory]:
    source = _CredentialSource()
    factory = _Factory(
        text=text,
        fail=fail,
        fail_close=fail_close,
        mode=mode,
        execution_error=execution_error,
        close_error=close_error,
    )
    base = OpenAIRuntimeComposerV2(
        OpenAIRuntimeConfigV2(
            model="gpt-offline", max_retries=0, request_timeout_seconds=13
        ),
        credential_source=source,
        sdk_factory=factory,
    )
    runner = OpenAILiveSmokeRunnerV2(
        OpenAIBridgedRuntimeComposerV2(base),
        SmokeProviderExecutionRequestAuthorityV2(),
    )
    return runner, source, factory


def _configuration(**changes: object) -> OpenAILiveSmokeConfigurationV2:
    values: dict[str, object] = {
        "confirm_live": True,
        "request_id": "offline-smoke-request",
        "requested_at": NOW,
        "timeout_seconds": 13,
    }
    values.update(changes)
    return OpenAILiveSmokeConfigurationV2(**values)


def test_public_api_is_exact() -> None:
    assert public_api.__all__ == (
        "OpenAILiveSmokeRunnerV2",
        "OpenAILiveSmokeConfigurationV2",
        "OpenAILiveSmokeResultV2",
        "OpenAILiveSmokeError",
        "OpenAILiveSmokeConfigurationError",
        "OpenAILiveSmokeDependencyError",
        "OpenAILiveSmokeLifecycleError",
    )
    assert issubclass(OpenAILiveSmokeConfigurationError, OpenAILiveSmokeError)
    assert issubclass(OpenAILiveSmokeDependencyError, OpenAILiveSmokeError)
    assert issubclass(OpenAILiveSmokeLifecycleError, OpenAILiveSmokeError)


def test_complete_offline_chain_returns_authentic_smoke_output() -> None:
    runner, source, factory = _runner()
    result = runner.run(_configuration())
    assert type(result) is OpenAILiveSmokeResultV2
    assert result == OpenAILiveSmokeResultV2(success=True, response_text="SMOKE_OK")
    assert source.calls == factory.calls == factory.responses.calls == 1
    assert factory.client.close_calls == 1
    assert factory.responses.arguments == {
        "model": "gpt-offline",
        "input": [{"role": "user", "content": "Reply with exactly:\n\nSMOKE_OK"}],
        "timeout": 13,
        "store": False,
        "stream": False,
        "background": False,
    }


@pytest.mark.parametrize("timeout", [1, 1.5, 13, 2**63])
def test_frozen_compatible_timeouts_execute(timeout: object) -> None:
    runner, _, factory = _runner()
    # The lower runtime owns its own request timeout; smoke timeout belongs to request.
    result = runner.run(_configuration(timeout_seconds=timeout))
    assert result.response_text == "SMOKE_OK"
    assert factory.client.close_calls == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"confirm_live": False},
        {"request_id": " "},
        {"request_id": " padded "},
        {"requested_at": NOW.replace(tzinfo=None)},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
    ],
)
def test_invalid_or_unconfirmed_input_never_touches_dependencies(
    changes: dict[str, object],
) -> None:
    runner, source, factory = _runner()
    if changes == {"confirm_live": False}:
        configuration = _configuration(**changes)
    else:
        values = {
            "confirm_live": True,
            "request_id": "offline-smoke-request",
            "requested_at": NOW,
            "timeout_seconds": 13,
            **changes,
        }
        with pytest.raises(ValidationError):
            OpenAILiveSmokeConfigurationV2(**values)
        return
    with pytest.raises(
        OpenAILiveSmokeConfigurationError,
        match="^explicit offline OpenAI smoke execution confirmation is required$",
    ):
        runner.run(configuration)
    assert source.calls == factory.calls == factory.responses.calls == 0
    assert factory.client.close_calls == 0


def test_copied_invalid_configuration_is_rejected_before_composition() -> None:
    runner, source, factory = _runner()
    configuration = _configuration()
    object.__setattr__(configuration, "request_id", " altered ")
    with pytest.raises(
        OpenAILiveSmokeConfigurationError,
        match="^invalid OpenAI live smoke configuration$",
    ):
        runner.run(configuration)
    assert source.calls == factory.calls == factory.responses.calls == 0


@pytest.mark.parametrize("invalid", [None, object()])
def test_constructor_rejects_non_exact_dependencies(invalid: object) -> None:
    base = OpenAIRuntimeComposerV2(
        OpenAIRuntimeConfigV2(
            model="gpt-offline", max_retries=0, request_timeout_seconds=13
        ),
        credential_source=_CredentialSource(),
        sdk_factory=_Factory(),
    )
    composer = OpenAIBridgedRuntimeComposerV2(base)
    authority = SmokeProviderExecutionRequestAuthorityV2()
    with pytest.raises(OpenAILiveSmokeDependencyError):
        OpenAILiveSmokeRunnerV2(
            invalid if invalid is not None else composer,
            invalid if invalid is not None else None,
        )
    # A valid pair remains accepted after rejected lookalikes.
    assert type(OpenAILiveSmokeRunnerV2(composer, authority)) is OpenAILiveSmokeRunnerV2


def test_wrong_provider_text_is_rejected_after_exact_cleanup() -> None:
    runner, source, factory = _runner(text="smoke_ok")
    with pytest.raises(
        OpenAILiveSmokeDependencyError,
        match="^OpenAI live smoke dependency failure$",
    ) as captured:
        runner.run(_configuration())
    assert source.calls == factory.calls == factory.responses.calls == 1
    assert factory.client.close_calls == 1
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_executor_failure_still_closes_once() -> None:
    runner, _, factory = _runner(fail=True)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert factory.responses.calls == factory.client.close_calls == 1


@pytest.mark.parametrize("fail_execution", [False, True])
def test_cleanup_failure_has_lifecycle_precedence(fail_execution: bool) -> None:
    runner, _, factory = _runner(fail=fail_execution, fail_close=True)
    with pytest.raises(
        OpenAILiveSmokeLifecycleError,
        match="^OpenAI live smoke lifecycle failure$",
    ):
        runner.run(_configuration())
    assert factory.client.close_calls == 1


def test_runner_copy_identity_immutability_and_pickle_rejection() -> None:
    runner, _, _ = _runner()
    assert copy.copy(runner) is runner
    assert copy.deepcopy(runner) is runner
    with pytest.raises(AttributeError):
        runner.extra = object()
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError):
            pickle.dumps(runner, protocol=protocol)
    assert repr(runner) == "OpenAILiveSmokeRunnerV2()"


def test_passive_imports_do_not_load_sdk_or_bootstrap() -> None:
    for name in (
        "pastila_scout.provider_runtime_openai_live_smoke_v2",
        "pastila_scout.provider_runtime_openai_live_smoke_v2.runner",
        "pastila_scout.provider_runtime_openai_live_smoke_v2.models",
        "pastila_scout.provider_runtime_openai_live_smoke_v2.errors",
    ):
        script = (
            "import sys;"
            f"__import__({name!r});"
            "print('openai' in sys.modules,"
            "'pastila_scout.provider_execution_openai_sdk_v2' in sys.modules,"
            "'pastila_scout.provider_execution_openai_sdk_bridge_v2.bootstrap' "
            "in sys.modules)"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stdout.strip() == "False False False"
        assert completed.stderr == ""


def test_runner_source_has_no_direct_provider_bypass() -> None:
    source = (
        ROOT
        / "src"
        / "pastila_scout"
        / "provider_runtime_openai_live_smoke_v2"
        / "runner.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "OPENAI_API_KEY",
        "os.getenv",
        "os.environ",
        "responses.create",
        "socket",
        "httpx",
        "requests",
        "subprocess",
        "threading",
    ):
        assert forbidden not in source
    assert "ProviderExecutionResultV2(" not in source


def test_executor_is_the_only_execution_authority(monkeypatch) -> None:
    calls = 0
    authentic = OpenAIProviderExecutorV2.execute

    def counted(self, request):
        nonlocal calls
        calls += 1
        return authentic(self, request)

    runner, _, factory = _runner()
    # Existing runners pin the authentic callable, so a later class replacement is ignored.
    monkeypatch.setattr(OpenAIProviderExecutorV2, "execute", counted)
    result = runner.run(_configuration())
    assert result.response_text == "SMOKE_OK"
    assert calls == 0
    assert factory.responses.calls == 1


def _assert_malformed_composition_rejected(
    monkeypatch: pytest.MonkeyPatch,
    mutate,
) -> None:
    runner, source, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    restore = mutate(composition)
    execute_calls = 0
    authentic_execute = runner_module._TRUSTED_EXECUTE

    def counted_execute(executor, request):
        nonlocal execute_calls
        execute_calls += 1
        return authentic_execute(executor, request)

    monkeypatch.setattr(runner_module, "_TRUSTED_EXECUTE", counted_execute)
    monkeypatch.setattr(
        runner_module,
        "_TRUSTED_COMPOSE",
        lambda receiver: composition,
    )
    with pytest.raises(
        OpenAILiveSmokeDependencyError,
        match="^OpenAI live smoke dependency failure$",
    ) as captured:
        runner.run(_configuration())
    assert execute_calls == 0
    assert source.calls == factory.calls == 1
    assert factory.responses.calls == 0
    assert factory.client.close_calls == 0
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    restore()
    runner_module._TRUSTED_CLOSE(composition)


def _replace_field(target: object, name: str, value: object):
    original = object.__getattribute__(target, name)
    object.__setattr__(target, name, value)

    def restore() -> None:
        object.__setattr__(target, name, original)

    return restore


def test_lower_owned_bridged_claim_is_consumed_exactly_once() -> None:
    runner, _, factory = _runner()
    authentic_claim = runner_module._TRUSTED_CLAIM
    calls = 0

    def counted_claim(*, composition, expected_executor):
        nonlocal calls
        calls += 1
        return authentic_claim(
            composition=composition, expected_executor=expected_executor
        )

    object.__setattr__(runner, "_claim_function", counted_claim)
    result = runner.run(_configuration())
    assert result.response_text == "SMOKE_OK"
    assert calls == 1
    assert factory.responses.calls == factory.client.close_calls == 1


def test_failed_bridged_claim_skips_execution_and_guessed_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    calls = 0

    def rejected_claim(*, composition, expected_executor):
        nonlocal calls
        del composition, expected_executor
        calls += 1

    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    object.__setattr__(runner, "_claim_function", rejected_claim)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert calls == 1
    assert factory.responses.calls == factory.client.close_calls == 0
    runner_module._TRUSTED_CLOSE(composition)


def test_malformed_composition_is_rejected_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    original = composition.executor
    object.__setattr__(composition, "executor", object())
    calls = 0

    def forbidden_claim(*, composition, expected_executor):
        nonlocal calls
        del composition, expected_executor
        calls += 1

    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    object.__setattr__(runner, "_claim_function", forbidden_claim)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert calls == 0
    assert factory.responses.calls == factory.client.close_calls == 0
    object.__setattr__(composition, "executor", original)
    runner_module._TRUSTED_CLOSE(composition)


def test_terminal_bridged_registration_cannot_be_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    runner_module._TRUSTED_CLOSE(composition)
    object.__setattr__(composition, "_closed", False)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert factory.responses.calls == 0
    assert factory.client.close_calls == 1
    object.__setattr__(composition, "_closed", True)


def test_foreign_bridged_generation_is_rejected_by_lower_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    restore = _replace_field(composition, "_registration_generation", object())
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert factory.responses.calls == factory.client.close_calls == 0
    restore()
    runner_module._TRUSTED_CLOSE(composition)


def test_foreign_bridged_base_claim_is_rejected_by_lower_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_a, _, factory_a = _runner()
    runner_b, _, factory_b = _runner()
    composition_a = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner_a, "_compose_receiver")
    )
    composition_b = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner_b, "_compose_receiver")
    )
    generation_a = object.__getattribute__(composition_a, "_registration_generation")
    generation_b = object.__getattribute__(composition_b, "_registration_generation")
    registration_a = bridged_composition._BRIDGED_REGISTRATIONS[generation_a]
    registration_b = bridged_composition._BRIDGED_REGISTRATIONS[generation_b]
    base_generation = registration_a.base_generation
    original = bridged_composition._BRIDGED_BASE_CLAIM_BY_GENERATION[base_generation]
    bridged_composition._BRIDGED_BASE_CLAIM_BY_GENERATION[base_generation] = (
        registration_b.base_claim
    )
    monkeypatch.setattr(
        runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition_a
    )
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner_a.run(_configuration())
    assert factory_a.responses.calls == factory_b.responses.calls == 0
    assert factory_a.client.close_calls == factory_b.client.close_calls == 0
    bridged_composition._BRIDGED_BASE_CLAIM_BY_GENERATION[base_generation] = original
    runner_module._TRUSTED_CLOSE(composition_a)
    runner_module._TRUSTED_CLOSE(composition_b)


def test_runner_delegates_provenance_without_inspecting_lower_trackers() -> None:
    source = (
        ROOT
        / "src"
        / "pastila_scout"
        / "provider_runtime_openai_live_smoke_v2"
        / "runner.py"
    ).read_text(encoding="utf-8")
    assert "_claim_bridged_registration_authority" in source
    for forbidden in (
        "_LIVE_WRAPPERS",
        "_tracker_identity",
        "_base_close_function",
        "_validate_base_composition",
        "_OWNERSHIP_TRACKER",
        "_BRIDGED_REGISTRATIONS",
        "_BRIDGED_BASE_CLAIM_BY_GENERATION",
    ):
        assert forbidden not in source


class _CallableClaimReplacement:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, **kwargs):
        del kwargs
        self.calls += 1
        return object()


@pytest.mark.parametrize(
    "replacement_factory",
    (
        lambda replacement: replacement,
        lambda replacement: lambda: replacement(),
        lambda replacement: wraps(runner_module._TRUSTED_CLAIM)(replacement),
        lambda replacement: staticmethod(replacement),
        lambda replacement: classmethod(replacement),
        lambda replacement: property(lambda self: replacement),
        lambda replacement: cached_property(lambda self: replacement),
        lambda replacement: partial(replacement),
        lambda replacement: object(),
    ),
)
def test_post_construction_claim_alias_substitution_cannot_redirect_authority(
    monkeypatch: pytest.MonkeyPatch,
    replacement_factory,
) -> None:
    runner, _, factory = _runner()
    replacement = _CallableClaimReplacement()
    monkeypatch.setattr(
        runner_module, "_TRUSTED_CLAIM", replacement_factory(replacement)
    )
    result = runner.run(_configuration())
    assert result.response_text == "SMOKE_OK"
    assert replacement.calls == 0
    assert factory.responses.calls == factory.client.close_calls == 1


def test_pre_construction_claim_alias_substitution_rejects_runner_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement = _CallableClaimReplacement()
    monkeypatch.setattr(runner_module, "_TRUSTED_CLAIM", replacement)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        _runner()
    assert replacement.calls == 0


def test_lower_claim_alias_substitution_does_not_redirect_existing_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    replacement = _CallableClaimReplacement()
    monkeypatch.setattr(
        bridged_composition,
        "_claim_bridged_registration_authority",
        replacement,
    )
    result = runner.run(_configuration())
    assert result.response_text == "SMOKE_OK"
    assert replacement.calls == 0
    assert factory.responses.calls == factory.client.close_calls == 1


def test_lower_claim_alias_substitution_rejects_future_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement = _CallableClaimReplacement()
    monkeypatch.setattr(
        bridged_composition,
        "_claim_bridged_registration_authority",
        replacement,
    )
    with pytest.raises(OpenAILiveSmokeDependencyError):
        _runner()
    assert replacement.calls == 0


@pytest.mark.parametrize(
    "claim_result",
    (None, object(), True, 1, "claim", _CallableClaimReplacement()),
)
def test_malformed_claim_results_never_authorize_execution(
    monkeypatch: pytest.MonkeyPatch,
    claim_result: object,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )

    def malformed_claim(**kwargs):
        del kwargs
        return claim_result

    object.__setattr__(runner, "_claim_function", malformed_claim)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert factory.responses.calls == factory.client.close_calls == 0
    runner_module._TRUSTED_CLOSE(composition)


@pytest.mark.parametrize(
    "config",
    (
        OpenAIExecutionConfigV2(model="gpt-offline", temperature=None),
        OpenAIExecutionConfigV2(model="gpt-offline", temperature=0),
        OpenAIExecutionConfigV2(model="gpt-offline", temperature=2),
        OpenAIExecutionConfigV2(model="gpt-offline", temperature=1.5),
        OpenAIExecutionConfigV2(model="gpt-offline", max_output_tokens=1),
        OpenAIExecutionConfigV2(model="gpt-offline", max_output_tokens=4096),
        OpenAIExecutionConfigV2(model="gpt-offline", max_output_tokens=1_000_000),
        OpenAIExecutionConfigV2(model="gpt-offline", stop_sequences=()),
        OpenAIExecutionConfigV2(
            model="gpt-offline",
            temperature=1.5,
            max_output_tokens=4096,
        ),
    ),
)
def test_same_model_valid_execution_controls_remain_supported(
    monkeypatch: pytest.MonkeyPatch,
    config: OpenAIExecutionConfigV2,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    object.__setattr__(composition.executor, "config", config)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    result = runner.run(_configuration())
    assert result.response_text == "SMOKE_OK"
    assert factory.responses.calls == factory.client.close_calls == 1


def test_foreign_valid_model_is_rejected_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    object.__setattr__(
        composition.executor,
        "config",
        OpenAIExecutionConfigV2(model="foreign-model"),
    )
    claim_calls = 0
    authentic_claim = object.__getattribute__(runner, "_claim_function")

    def counted_claim(**kwargs):
        nonlocal claim_calls
        claim_calls += 1
        return authentic_claim(**kwargs)

    object.__setattr__(runner, "_claim_function", counted_claim)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert claim_calls == 0
    assert factory.responses.calls == factory.client.close_calls == 0
    object.__setattr__(
        composition.executor, "config", OpenAIExecutionConfigV2(model="gpt-offline")
    )
    runner_module._TRUSTED_CLOSE(composition)


@pytest.mark.parametrize(
    ("base_model", "bridged_model", "succeeds"),
    (
        ("foreign-model", "gpt-offline", False),
        ("gpt-offline", "foreign-model", False),
        ("foreign-model", "foreign-model", False),
        ("foreign-a", "foreign-b", False),
        ("gpt-offline", "gpt-offline", True),
    ),
)
def test_producing_runtime_model_is_independent_three_way_authority(
    monkeypatch: pytest.MonkeyPatch,
    base_model: str,
    bridged_model: str,
    succeeds: bool,
) -> None:
    runner, _, factory = _runner()
    assert object.__getattribute__(runner, "_runtime_model") == "gpt-offline"
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    base = object.__getattribute__(composition, "_base_composition")
    authentic = OpenAIExecutionConfigV2(model="gpt-offline")
    object.__setattr__(
        base.executor, "config", OpenAIExecutionConfigV2(model=base_model)
    )
    object.__setattr__(
        composition.executor,
        "config",
        OpenAIExecutionConfigV2(model=bridged_model),
    )
    claim_calls = 0
    authentic_claim = object.__getattribute__(runner, "_claim_function")

    def counted_claim(**kwargs):
        nonlocal claim_calls
        claim_calls += 1
        return authentic_claim(**kwargs)

    object.__setattr__(runner, "_claim_function", counted_claim)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    if succeeds:
        result = runner.run(_configuration())
        assert result.response_text == "SMOKE_OK"
        assert claim_calls == 1
        assert factory.responses.calls == factory.client.close_calls == 1
        return
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert claim_calls == 0
    assert factory.responses.calls == factory.client.close_calls == 0
    object.__setattr__(base.executor, "config", authentic)
    object.__setattr__(composition.executor, "config", authentic)
    runner_module._TRUSTED_CLOSE(composition)


def test_runner_pins_model_before_producing_composer_can_be_mutated() -> None:
    runner, _, _ = _runner()
    composer = object.__getattribute__(runner, "_compose_receiver")
    base_composer = object.__getattribute__(composer, "_base_runtime_composer")
    original = object.__getattribute__(base_composer, "config")
    object.__setattr__(
        base_composer,
        "config",
        original.model_copy(update={"model": "foreign-model"}),
    )
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    object.__setattr__(base_composer, "config", original)


class _ModelSubclass(str):
    pass


@pytest.mark.parametrize("model", (_ModelSubclass("gpt-offline"), "", " padded ", 1))
def test_copied_invalid_models_reject_before_claim(
    monkeypatch: pytest.MonkeyPatch,
    model: object,
) -> None:
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    config = OpenAIExecutionConfigV2(model="gpt-offline")
    object.__setattr__(config, "model", model)
    object.__setattr__(composition.executor, "config", config)
    claim_calls = 0

    def forbidden_claim(**kwargs):
        nonlocal claim_calls
        del kwargs
        claim_calls += 1

    object.__setattr__(runner, "_claim_function", forbidden_claim)
    monkeypatch.setattr(runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert claim_calls == 0
    assert factory.responses.calls == factory.client.close_calls == 0
    object.__setattr__(
        composition.executor, "config", OpenAIExecutionConfigV2(model="gpt-offline")
    )
    runner_module._TRUSTED_CLOSE(composition)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("client", object()),
        ("_authorized_function", lambda *args, **kwargs: None),
        ("_receiver", object()),
        ("_invocation_kind", "static"),
    ],
)
def test_original_major_executor_authority_mutations_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: object,
) -> None:
    def mutate(composition):
        return _replace_field(composition.executor, field, replacement)

    _assert_malformed_composition_rejected(monkeypatch, mutate)


def test_original_major_all_executor_mutations_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foreign = lambda *args, **kwargs: None

    def mutate(composition):
        executor = composition.executor
        originals = {
            name: object.__getattribute__(executor, name)
            for name in ("client", "_authorized_function", "_receiver")
        }
        object.__setattr__(executor, "client", object())
        object.__setattr__(executor, "_authorized_function", foreign)
        object.__setattr__(executor, "_receiver", object())

        def restore() -> None:
            for name, value in originals.items():
                object.__setattr__(executor, name, value)

        return restore

    _assert_malformed_composition_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    "field",
    ("_complete_function", "_mapper_function", "_sdk_client", "_sdk_request_type"),
)
def test_copied_invalid_bridge_authority_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    def mutate(composition):
        bridge = composition.executor.client
        return _replace_field(bridge, field, object())

    _assert_malformed_composition_rejected(monkeypatch, mutate)


def test_copied_invalid_execution_config_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(composition):
        executor = composition.executor
        config = OpenAIExecutionConfigV2(model="gpt-offline")
        object.__setattr__(config, "stop_sequences", ["STOP"])
        return _replace_field(executor, "config", config)

    _assert_malformed_composition_rejected(monkeypatch, mutate)


def test_closed_copied_invalid_composition_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(composition):
        return _replace_field(composition, "_closed", True)

    _assert_malformed_composition_rejected(monkeypatch, mutate)


def test_cross_composition_executor_lineage_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_a, _, factory_a = _runner()
    runner_b, _, factory_b = _runner()
    composition_a = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner_a, "_compose_receiver")
    )
    composition_b = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner_b, "_compose_receiver")
    )
    original = composition_a.executor
    object.__setattr__(composition_a, "executor", composition_b.executor)
    monkeypatch.setattr(
        runner_module, "_TRUSTED_COMPOSE", lambda receiver: composition_a
    )
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner_a.run(_configuration())
    assert factory_a.responses.calls == factory_b.responses.calls == 0
    assert factory_a.client.close_calls == factory_b.client.close_calls == 0
    object.__setattr__(composition_a, "executor", original)
    runner_module._TRUSTED_CLOSE(composition_a)
    runner_module._TRUSTED_CLOSE(composition_b)


@pytest.mark.parametrize(
    ("text", "mode", "fail"),
    [
        ("smoke_ok", "success", False),
        (" SMOKE_OK", "success", False),
        ("SMOKE_OK ", "success", False),
        ("SMOKE_OK extra", "success", False),
        ("SMOKE_OK", "zero", False),
        ("SMOKE_OK", "multiple", False),
        ("SMOKE_OK", "length", False),
        ("SMOKE_OK", "filtered", False),
        ("SMOKE_OK", "success", True),
    ],
)
def test_complete_provider_result_rejection_matrix_closes_once(
    text: str,
    mode: str,
    fail: bool,
) -> None:
    runner, _, factory = _runner(text=text, mode=mode, fail=fail)
    with pytest.raises(OpenAILiveSmokeDependencyError):
        runner.run(_configuration())
    assert factory.responses.calls == 1
    assert factory.client.close_calls == 1


@pytest.mark.parametrize(
    "exception_type", [KeyboardInterrupt, SystemExit, GeneratorExit]
)
def test_execution_base_exception_propagates_after_one_close(exception_type) -> None:
    error = exception_type("execution control flow")
    runner, _, factory = _runner(execution_error=error)
    with pytest.raises(exception_type) as captured:
        runner.run(_configuration())
    assert captured.value is error
    assert factory.responses.calls == 1
    assert factory.client.close_calls == 1


@pytest.mark.parametrize(
    "exception_type", [KeyboardInterrupt, SystemExit, GeneratorExit]
)
def test_cleanup_base_exception_has_precedence(exception_type) -> None:
    error = exception_type("cleanup control flow")
    runner, _, factory = _runner(close_error=error)
    with pytest.raises(exception_type) as captured:
        runner.run(_configuration())
    assert captured.value is error
    assert factory.responses.calls == 1
    assert factory.client.close_calls == 1


def test_execution_base_exception_plus_ordinary_cleanup_failure_is_lifecycle() -> None:
    runner, _, factory = _runner(
        execution_error=KeyboardInterrupt("execution"),
        close_error=RuntimeError("cleanup"),
    )
    with pytest.raises(
        OpenAILiveSmokeLifecycleError,
        match="^OpenAI live smoke lifecycle failure$",
    ):
        runner.run(_configuration())
    assert factory.responses.calls == 1
    assert factory.client.close_calls == 1


def test_three_repeated_successful_runs_are_independent() -> None:
    runner, source, factory = _runner()
    assert [runner.run(_configuration()).response_text for _ in range(3)] == [
        "SMOKE_OK",
        "SMOKE_OK",
        "SMOKE_OK",
    ]
    assert source.calls == factory.calls == factory.responses.calls == 3
    assert factory.client.close_calls == 3


def test_copied_invalid_request_lineage_matrix_is_rejected() -> None:
    configuration = _configuration()
    plan = build_canonical_smoke_execution_plan()
    authority = SmokeProviderExecutionRequestAuthorityV2()
    request = authority.construct(
        execution_plan=plan,
        execution_request_id=configuration.request_id,
        requested_at=configuration.requested_at,
        timeout_seconds=configuration.timeout_seconds,
    )
    mutations = (
        ("context.request_id", "foreign-request"),
        ("provider.provider_id", "foreign"),
        ("request_intent.execution_plan_reference", "foreign-plan"),
        (
            "request_intent.execution_plan_identity",
            "scout:smoke-execution-plan-v2:" + "0" * 64,
        ),
        ("request_intent.execution_plan_fingerprint", "0" * 64),
        ("request_intent.draft_reference", "foreign-draft"),
        ("request_intent.draft_fingerprint", "0" * 64),
        ("request_intent.request_units.0.source_request_reference", "foreign-source"),
        ("request_envelope.identity", "scout:provider-request-envelope-v2:" + "0" * 64),
        ("request_intent.request_units.0.messages.0.ordinal", 1),
        ("request_intent.request_units.0.messages.0.role", "system"),
        ("request_intent.request_units.0.messages.0.content", "foreign-content"),
        ("context.metadata", (("foreign", "metadata"),)),
        ("timeout_policy.timeout_seconds", 99),
    )
    for path, replacement in mutations:
        malformed = request.model_copy(deep=True)
        target: object = malformed
        pieces = path.split(".")
        for piece in pieces[:-1]:
            target = (
                target[int(piece)]
                if piece.isdigit()
                else object.__getattribute__(target, piece)
            )
        object.__setattr__(target, pieces[-1], replacement)
        assert runner_module._validated_request(malformed, plan, configuration) is None


def test_copied_invalid_result_lineage_matrix_is_rejected() -> None:
    configuration = _configuration()
    plan = build_canonical_smoke_execution_plan()
    runner, _, factory = _runner()
    composition = runner_module._TRUSTED_COMPOSE(
        object.__getattribute__(runner, "_compose_receiver")
    )
    request = runner_module._TRUSTED_CONSTRUCT(
        object.__getattribute__(runner, "_request_receiver"),
        execution_plan=plan,
        execution_request_id=configuration.request_id,
        requested_at=configuration.requested_at,
        timeout_seconds=configuration.timeout_seconds,
    )
    result = runner_module._TRUSTED_EXECUTE(composition.executor, request)
    assert type(result) is ProviderExecutionResultV2
    mutations = (
        ("request_id", "foreign-request"),
        ("provider_id", "foreign-provider"),
        (
            "request_envelope_identity",
            "scout:provider-request-envelope-v2:" + "0" * 64,
        ),
    )
    for field, replacement in mutations:
        malformed = result.model_copy(deep=True)
        object.__setattr__(malformed, field, replacement)
        assert runner_module._validated_result_text(malformed, request) is None
    malformed = result.model_copy(deep=True)
    object.__setattr__(
        malformed.provider_result.outputs[0], "generated_text", "SMOKE_OK "
    )
    assert runner_module._validated_result_text(malformed, request) is None
    runner_module._TRUSTED_CLOSE(composition)
    assert factory.responses.calls == factory.client.close_calls == 1
