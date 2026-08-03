from __future__ import annotations

import copy
import gc
import math
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction
from functools import cached_property
from pathlib import Path
from types import FunctionType

import pytest

import pastila_scout.provider_runtime_openai_bridged_v2 as public_api
import pastila_scout.provider_runtime_openai_bridged_v2.composition as module
from pastila_scout.provider_execution_openai_sdk_bridge_v2 import (
    OpenAIExecutionSDKBridgeClientV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_runtime_openai_bridged_v2 import (
    OpenAIBridgedRuntimeComposerV2,
    OpenAIBridgedRuntimeCompositionV2,
    OpenAIBridgedRuntimeConfigurationError,
    OpenAIBridgedRuntimeDependencyError,
    OpenAIBridgedRuntimeError,
    OpenAIBridgedRuntimeLifecycleError,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeConfigV2,
)
from pastila_scout.provider_runtime_openai_v2.composition import _mint_factory_handoff

ROOT = Path(__file__).resolve().parents[1]


class _IntSubclass(int):
    pass


class _FloatSubclass(float):
    pass


class _StringSubclass(str):
    pass


class _TupleSubclass(tuple):
    pass


class _CoercibleNumber:
    def __int__(self) -> int:
        raise AssertionError("coercion must not execute")

    def __float__(self) -> float:
        raise AssertionError("coercion must not execute")

    def __index__(self) -> int:
        raise AssertionError("coercion must not execute")


class _CredentialSource:
    def __init__(self) -> None:
        self.calls = 0

    def get_api_key(self) -> str:
        self.calls += 1
        return "synthetic-offline-key"


class _Responses:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **arguments: object) -> object:
        del arguments
        self.calls += 1
        raise AssertionError("provider execution is outside Revision 7")


class _RawClient:
    def __init__(
        self,
        responses: _Responses,
        *,
        fail_close: bool = False,
        close_callback: object = None,
    ) -> None:
        self.responses = responses
        self.fail_close = fail_close
        self.close_callback = close_callback
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        if self.close_callback is not None:
            callback = self.close_callback
            self.close_callback = None
            callback()
        if self.fail_close:
            raise RuntimeError("private close failure")


class _Factory:
    def __init__(
        self, *, fail_close: bool = False, expected_timeout: float = 13
    ) -> None:
        self.calls = 0
        self.responses = _Responses()
        self.clients: list[_RawClient] = []
        self.fail_close = fail_close
        self.expected_timeout = expected_timeout

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        assert api_key == "synthetic-offline-key"
        assert max_retries == 0
        assert request_timeout_seconds == self.expected_timeout
        self.calls += 1
        client = _RawClient(self.responses, fail_close=self.fail_close)
        self.clients.append(client)
        return _mint_factory_handoff(client)

    def close_client(self, client: object) -> None:
        del client
        raise AssertionError("factory rollback is no longer authoritative")


def _base_composer(
    *,
    fail_close: bool = False,
    model: str = "gpt-offline",
    timeout: float = 13,
) -> tuple[OpenAIRuntimeComposerV2, _CredentialSource, _Factory]:
    source = _CredentialSource()
    factory = _Factory(fail_close=fail_close, expected_timeout=timeout)
    composer = OpenAIRuntimeComposerV2(
        OpenAIRuntimeConfigV2(
            model=model, max_retries=0, request_timeout_seconds=timeout
        ),
        credential_source=source,
        sdk_factory=factory,
    )
    return composer, source, factory


def _compose_with_execution_config(
    monkeypatch,
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    stop_sequences: tuple[str, ...] = (),
    model: str = "gpt-offline",
    timeout: float = 13,
) -> tuple[OpenAIBridgedRuntimeCompositionV2, _CredentialSource, _Factory, int]:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base_composer, source, factory = _base_composer(model=model, timeout=timeout)
    base = base_composer.compose()
    sdk_client = object.__getattribute__(base, "sdk_client")
    config = OpenAIExecutionConfigV2(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        stop_sequences=stop_sequences,
    )
    object.__setattr__(
        base,
        "executor",
        OpenAIProviderExecutorV2(client=sdk_client, config=config),
    )
    bootstrap_calls = 0
    authentic = bootstrap._bootstrap_bridge

    def counted(client):
        nonlocal bootstrap_calls
        bootstrap_calls += 1
        return authentic(client)

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", counted)

    def return_base(receiver):
        del receiver
        return base

    result = module._return_or_raise_assembly(
        module._compose_isolated(return_base, base_composer)
    )
    return result, source, factory, bootstrap_calls


def _compose(*, fail_close: bool = False):
    base, source, factory = _base_composer(fail_close=fail_close)
    composer = OpenAIBridgedRuntimeComposerV2(base)
    return composer.compose(), composer, source, factory


def test_public_api_is_exact() -> None:
    assert public_api.__all__ == (
        "OpenAIBridgedRuntimeComposerV2",
        "OpenAIBridgedRuntimeCompositionV2",
        "OpenAIBridgedRuntimeError",
        "OpenAIBridgedRuntimeConfigurationError",
        "OpenAIBridgedRuntimeDependencyError",
        "OpenAIBridgedRuntimeLifecycleError",
    )
    assert issubclass(OpenAIBridgedRuntimeConfigurationError, OpenAIBridgedRuntimeError)
    assert issubclass(OpenAIBridgedRuntimeDependencyError, OpenAIBridgedRuntimeError)
    assert issubclass(OpenAIBridgedRuntimeLifecycleError, OpenAIBridgedRuntimeError)


def test_passive_imports_are_openai_and_bootstrap_free() -> None:
    for name in (
        "pastila_scout.provider_runtime_openai_bridged_v2",
        "pastila_scout.provider_runtime_openai_bridged_v2.models",
        "pastila_scout.provider_runtime_openai_bridged_v2.errors",
        "pastila_scout.provider_runtime_openai_bridged_v2.composition",
    ):
        script = (
            "import sys;"
            f"__import__({name!r});"
            "print('openai' in sys.modules,"
            "'pastila_scout.provider_execution_openai_sdk_bridge_v2.bootstrap' "
            "in sys.modules,"
            "'pastila_scout.provider_execution_openai_sdk_v2' in sys.modules)"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stdout.strip() == "False False False"
        assert completed.stderr == ""


@pytest.mark.parametrize("invalid", [None, object()])
def test_composer_rejects_non_exact_base(invalid: object) -> None:
    with pytest.raises(
        OpenAIBridgedRuntimeConfigurationError,
        match="^invalid OpenAI bridged runtime configuration$",
    ):
        OpenAIBridgedRuntimeComposerV2(invalid)


def test_composer_rejects_base_subclass() -> None:
    class Derived(OpenAIRuntimeComposerV2):
        pass

    base, _, _ = _base_composer()
    derived = object.__new__(Derived)
    for name in OpenAIRuntimeComposerV2.__dataclass_fields__:
        object.__setattr__(derived, name, object.__getattribute__(base, name))
    with pytest.raises(OpenAIBridgedRuntimeConfigurationError):
        OpenAIBridgedRuntimeComposerV2(derived)


def test_success_graph_and_operational_counts() -> None:
    composition, _, source, factory = _compose()
    assert type(composition) is OpenAIBridgedRuntimeCompositionV2
    assert type(composition.executor) is OpenAIProviderExecutorV2
    assert type(composition.executor.client) is OpenAIExecutionSDKBridgeClientV2
    base = object.__getattribute__(composition, "_base_composition")
    assert (
        object.__getattribute__(composition.executor.client, "_sdk_client")
        is base.sdk_client
    )
    assert composition.closed is False
    assert source.calls == 1
    assert factory.calls == 1
    assert factory.responses.calls == 0


@pytest.mark.parametrize("temperature", [None, 0, 0.0, 0.1, 1, 1.0, 1.5, 2, 2.0])
def test_valid_temperature_matrix_is_accepted(monkeypatch, temperature) -> None:
    result, source, factory, bootstrap_calls = _compose_with_execution_config(
        monkeypatch, temperature=temperature
    )
    assert type(result) is OpenAIBridgedRuntimeCompositionV2
    assert result.closed is False
    assert source.calls == factory.calls == bootstrap_calls == 1
    assert factory.responses.calls == 0
    result.close()
    assert factory.clients[0].close_calls == 1


@pytest.mark.parametrize(
    "temperature",
    [
        -1,
        2.1,
        math.nan,
        math.inf,
        -math.inf,
        True,
        _IntSubclass(1),
        _FloatSubclass(1.0),
        Decimal("1.0"),
        Fraction(1, 2),
        _CoercibleNumber(),
    ],
)
def test_invalid_temperature_matrix_is_rejected_by_frozen_contract(
    temperature,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        OpenAIExecutionConfigV2(model="gpt-offline", temperature=temperature)


@pytest.mark.parametrize("token_limit", [None, 1, 2, 4096, 2**63, _IntSubclass(3)])
def test_valid_output_token_matrix_is_accepted(monkeypatch, token_limit) -> None:
    result, _, factory, bootstrap_calls = _compose_with_execution_config(
        monkeypatch, max_output_tokens=token_limit
    )
    assert bootstrap_calls == 1
    result.close()
    assert factory.clients[0].close_calls == 1


@pytest.mark.parametrize(
    "token_limit",
    [0, -1, True, 1.0, "1", _CoercibleNumber()],
)
def test_invalid_output_token_matrix_is_rejected_by_frozen_contract(
    token_limit,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        OpenAIExecutionConfigV2(model="gpt-offline", max_output_tokens=token_limit)


@pytest.mark.parametrize(
    ("temperature", "token_limit"),
    [(0, None), (2, None), (None, 1), (1.5, 4096), (0.25, 8192)],
)
def test_combined_valid_execution_controls_are_accepted(
    monkeypatch, temperature, token_limit
) -> None:
    result, source, factory, bootstrap_calls = _compose_with_execution_config(
        monkeypatch,
        temperature=temperature,
        max_output_tokens=token_limit,
    )
    assert type(result.executor) is OpenAIProviderExecutorV2
    assert source.calls == factory.calls == bootstrap_calls == 1
    assert factory.responses.calls == 0
    result.close()
    assert factory.clients[0].close_calls == 1


@pytest.mark.parametrize(
    "stop_sequences",
    [(), ("END",), ("STOP", "HALT"), ("END NOW",)],
)
def test_valid_stop_sequences_are_composition_authority(
    monkeypatch, stop_sequences
) -> None:
    result, _, factory, bootstrap_calls = _compose_with_execution_config(
        monkeypatch, stop_sequences=stop_sequences
    )
    assert bootstrap_calls == 1
    assert factory.responses.calls == 0
    result.close()


@pytest.mark.parametrize("timeout", [1, 0.5, 13, 2**31])
def test_valid_runtime_timeout_breadth_remains_accepted(monkeypatch, timeout) -> None:
    result, source, factory, bootstrap_calls = _compose_with_execution_config(
        monkeypatch, timeout=timeout, model=f"gpt-offline-{timeout}"
    )
    assert source.calls == factory.calls == bootstrap_calls == 1
    result.close()


def test_close_delegates_once_and_is_permanently_closed() -> None:
    composition, _, _, factory = _compose()
    composition.close()
    composition.close()
    assert composition.closed is True
    assert factory.clients[0].close_calls == 1


def test_close_failure_has_lifecycle_precedence_and_no_retry() -> None:
    composition, _, _, factory = _compose(fail_close=True)
    with pytest.raises(
        OpenAIBridgedRuntimeLifecycleError,
        match="^OpenAI bridged runtime lifecycle failure$",
    ) as captured:
        composition.close()
    composition.close()
    assert composition.closed is True
    assert factory.clients[0].close_calls == 1
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_copy_pickle_immutability_and_representation() -> None:
    composition, composer, _, _ = _compose()
    assert copy.copy(composer) is composer
    assert copy.deepcopy(composer) is composer
    assert copy.copy(composition) is composition
    assert copy.deepcopy(composition) is composition
    assert repr(composer) == "OpenAIBridgedRuntimeComposerV2()"
    assert repr(composition) == (
        "OpenAIBridgedRuntimeCompositionV2("
        "executor=<OpenAIProviderExecutorV2>, closed=False)"
    )
    for value in (composer, composition):
        with pytest.raises(FrozenInstanceError):
            value.extra = object()
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with pytest.raises(TypeError):
                pickle.dumps(value, protocol=protocol)


def test_postconstruction_base_compose_replacement_cannot_redirect(monkeypatch) -> None:
    base, source, factory = _base_composer()
    composer = OpenAIBridgedRuntimeComposerV2(base)
    replacement_calls = 0

    def replacement(self):
        nonlocal replacement_calls
        replacement_calls += 1
        return object()

    monkeypatch.setattr(OpenAIRuntimeComposerV2, "compose", replacement)
    result = composer.compose()
    assert type(result) is OpenAIBridgedRuntimeCompositionV2
    assert replacement_calls == 0
    assert source.calls == factory.calls == 1


def test_preconstruction_base_compose_replacement_is_rejected(monkeypatch) -> None:
    base, _, _ = _base_composer()

    def replacement(self):
        del self
        return object()

    monkeypatch.setattr(OpenAIRuntimeComposerV2, "compose", replacement)
    with pytest.raises(OpenAIBridgedRuntimeConfigurationError):
        OpenAIBridgedRuntimeComposerV2(base)


@pytest.mark.parametrize(
    "replacement_factory",
    [
        lambda original: FunctionType(
            original.__code__,
            original.__globals__,
            original.__name__,
            original.__defaults__,
            original.__closure__,
        ),
        lambda original: staticmethod(original),
        lambda original: classmethod(original),
        lambda original: property(lambda self: original),
        lambda original: cached_property(lambda self: original),
        lambda original: _CallableDescriptor(original),
        lambda original: _NonCallableDescriptor(),
    ],
    ids=(
        "copied-code",
        "staticmethod",
        "classmethod",
        "property",
        "cached-property",
        "callable-descriptor",
        "noncallable-descriptor",
    ),
)
def test_preconstruction_compose_authority_replacement_matrix_is_rejected(
    monkeypatch, replacement_factory
) -> None:
    base, _, _ = _base_composer()
    original = module._TRUSTED_BASE_COMPOSE
    monkeypatch.setattr(
        OpenAIRuntimeComposerV2,
        "compose",
        replacement_factory(original),
    )
    with pytest.raises(OpenAIBridgedRuntimeConfigurationError):
        OpenAIBridgedRuntimeComposerV2(base)


def test_bridge_bootstrap_failure_rolls_back_once(monkeypatch) -> None:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base, source, factory = _base_composer()
    composer = OpenAIBridgedRuntimeComposerV2(base)

    def failure(client):
        del client
        raise RuntimeError("private bridge failure")

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", failure)
    with pytest.raises(OpenAIBridgedRuntimeDependencyError):
        composer.compose()
    assert source.calls == factory.calls == 1
    assert factory.clients[0].close_calls == 1


def test_bridge_failure_and_rollback_failure_has_lifecycle_precedence(
    monkeypatch,
) -> None:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base, _, factory = _base_composer(fail_close=True)
    composer = OpenAIBridgedRuntimeComposerV2(base)

    def failure(client):
        del client
        raise RuntimeError("private bridge failure")

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", failure)
    with pytest.raises(OpenAIBridgedRuntimeLifecycleError):
        composer.compose()
    assert factory.clients[0].close_calls == 1


def _assert_malformed_base_rejected(monkeypatch, mutate) -> tuple[object, _Factory]:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base_composer, _, factory = _base_composer()
    base = base_composer.compose()
    bootstrap_calls = 0
    authentic = bootstrap._bootstrap_bridge

    def counted(client):
        nonlocal bootstrap_calls
        bootstrap_calls += 1
        return authentic(client)

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", counted)
    mutate(base)
    tracker_before = dict(module._LIVE_WRAPPERS)

    def return_base(receiver):
        del receiver
        return base

    outcome = module._compose_isolated(return_base, base_composer)
    assert type(outcome) is module._SafeAssemblyFailure
    assert outcome.category == "dependency"
    with pytest.raises(
        OpenAIBridgedRuntimeDependencyError,
        match="^OpenAI bridged runtime dependency failure$",
    ) as captured:
        module._return_or_raise_assembly(outcome)
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert bootstrap_calls == 0
    assert module._LIVE_WRAPPERS == tracker_before
    assert factory.clients[0].close_calls == 0
    return base, factory


def test_malformed_exact_sdk_capability_is_rejected_before_handoff(
    monkeypatch,
) -> None:
    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        object.__setattr__(sdk_client, "_sdk_capability", object())

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_missing_exact_sdk_capability_is_rejected_before_handoff(monkeypatch) -> None:
    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        object.__setattr__(sdk_client, "_sdk_capability", None)

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_sdk_capability_subclass_is_rejected_before_handoff(monkeypatch) -> None:
    from pastila_scout.provider_execution_openai_sdk_v2 import OpenAISDKCapabilityV2

    class DerivedCapability(OpenAISDKCapabilityV2):
        pass

    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        capability = object.__getattribute__(sdk_client, "_sdk_capability")
        derived = object.__new__(DerivedCapability)
        for field in ("_function", "_receiver", "max_retries"):
            object.__setattr__(
                derived, field, object.__getattribute__(capability, field)
            )
        object.__setattr__(sdk_client, "_sdk_capability", derived)

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_copied_invalid_exact_sdk_capability_is_rejected(monkeypatch) -> None:
    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        capability = object.__getattribute__(sdk_client, "_sdk_capability")
        copied = object.__new__(type(capability))
        object.__setattr__(copied, "_function", None)
        object.__setattr__(
            copied,
            "_receiver",
            object.__getattribute__(capability, "_receiver"),
        )
        object.__setattr__(copied, "max_retries", 0)
        object.__setattr__(sdk_client, "_sdk_capability", copied)

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_malformed_exact_lifecycle_function_is_rejected_before_handoff(
    monkeypatch,
) -> None:
    def mutate(base):
        lifecycle = object.__getattribute__(base, "_lifecycle")
        object.__setattr__(lifecycle, "_function", None)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("_function", None),
        ("_function", lambda: None),
        ("_receiver", None),
        ("_receiver", object()),
        ("max_retries", 1),
    ],
)
def test_malformed_capability_authority_matrix_is_rejected(
    monkeypatch, field: str, replacement: object
) -> None:
    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        capability = object.__getattribute__(sdk_client, "_sdk_capability")
        object.__setattr__(capability, field, replacement)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("_closed", True),
        ("_function", None),
        ("_function", lambda: None),
        ("_receiver", None),
        ("_receiver", object()),
        ("_success_function", None),
        ("_success_function", lambda: None),
        ("_failure_function", None),
        ("_failure_function", lambda: None),
        ("_transition_receiver", object()),
    ],
)
def test_malformed_lifecycle_authority_matrix_is_rejected(
    monkeypatch, field: str, replacement: object
) -> None:
    def mutate(base):
        lifecycle = object.__getattribute__(base, "_lifecycle")
        object.__setattr__(lifecycle, field, replacement)

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_malformed_lifecycle_ownership_identity_is_rejected(monkeypatch) -> None:
    def mutate(base):
        lifecycle = object.__getattribute__(base, "_lifecycle")
        lease = object.__getattribute__(lifecycle, "_transition_receiver")
        object.__setattr__(
            lease, "identity", object.__getattribute__(lease, "identity") + 1
        )

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_copied_invalid_exact_lifecycle_owner_is_rejected(monkeypatch) -> None:
    def mutate(base):
        lifecycle = object.__getattribute__(base, "_lifecycle")
        copied = object.__new__(type(lifecycle))
        for field in (
            "_closed",
            "_function",
            "_receiver",
            "_success_function",
            "_failure_function",
            "_transition_receiver",
        ):
            object.__setattr__(copied, field, object.__getattribute__(lifecycle, field))
        object.__setattr__(copied, "_function", None)
        object.__setattr__(base, "_lifecycle", copied)

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_cross_base_sdk_lifecycle_lineage_is_rejected(monkeypatch) -> None:
    other_composer, _, _ = _base_composer()
    other = other_composer.compose()

    def mutate(base):
        object.__setattr__(
            base, "_lifecycle", object.__getattribute__(other, "_lifecycle")
        )

    _assert_malformed_base_rejected(monkeypatch, mutate)
    other.close()


def test_cross_base_executor_lineage_is_rejected(monkeypatch) -> None:
    other_composer, _, _ = _base_composer()
    other = other_composer.compose()

    def mutate(base):
        object.__setattr__(base, "executor", object.__getattribute__(other, "executor"))

    _assert_malformed_base_rejected(monkeypatch, mutate)
    other.close()


def test_cross_base_capability_cleanup_lineage_is_rejected(monkeypatch) -> None:
    other_composer, _, _ = _base_composer()
    other = other_composer.compose()

    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        other_sdk = object.__getattribute__(other, "sdk_client")
        object.__setattr__(
            sdk_client,
            "_sdk_capability",
            object.__getattribute__(other_sdk, "_sdk_capability"),
        )

    _assert_malformed_base_rejected(monkeypatch, mutate)
    other.close()


def test_cross_runtime_executor_configuration_is_rejected(monkeypatch) -> None:
    other_composer, _, _ = _base_composer(model="gpt-other")
    other = other_composer.compose()

    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        other_executor = object.__getattribute__(other, "executor")
        object.__setattr__(
            executor, "config", object.__getattribute__(other_executor, "config")
        )

    _assert_malformed_base_rejected(monkeypatch, mutate)
    other.close()


@pytest.mark.parametrize(
    "temperature",
    [
        -1,
        2.1,
        math.nan,
        math.inf,
        True,
        _IntSubclass(1),
        _FloatSubclass(1.0),
        _CoercibleNumber(),
    ],
)
def test_copied_invalid_exact_temperature_is_rejected_before_handoff(
    monkeypatch, temperature
) -> None:
    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        config = OpenAIExecutionConfigV2(model="gpt-offline")
        object.__setattr__(config, "temperature", temperature)
        object.__setattr__(executor, "config", config)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    "token_limit",
    [0, -1, True, _IntSubclass(1), 1.0, "1", _CoercibleNumber()],
)
def test_copied_invalid_exact_token_limit_is_rejected_before_handoff(
    monkeypatch, token_limit
) -> None:
    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        config = OpenAIExecutionConfigV2(model="gpt-offline")
        object.__setattr__(config, "max_output_tokens", token_limit)
        object.__setattr__(executor, "config", config)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    "stop_sequences",
    [
        ["END"],
        _TupleSubclass(("END",)),
        ("",),
        (" PADDED ",),
        ("END", "END"),
        (_StringSubclass("END"),),
        object(),
    ],
)
def test_copied_invalid_exact_stop_sequences_are_rejected_before_handoff(
    monkeypatch, stop_sequences
) -> None:
    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        config = OpenAIExecutionConfigV2(model="gpt-offline")
        object.__setattr__(config, "stop_sequences", stop_sequences)
        object.__setattr__(executor, "config", config)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    "model", ["gpt-other", " padded ", "", _StringSubclass("gpt-offline")]
)
def test_copied_invalid_or_incoherent_model_is_rejected_before_handoff(
    monkeypatch, model
) -> None:
    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        config = OpenAIExecutionConfigV2(model="gpt-offline")
        object.__setattr__(config, "model", model)
        object.__setattr__(executor, "config", config)

    _assert_malformed_base_rejected(monkeypatch, mutate)


@pytest.mark.parametrize(
    "field", ["_authorized_function", "_invocation_kind", "_receiver"]
)
def test_malformed_base_executor_authority_is_rejected(monkeypatch, field: str) -> None:
    def mutate(base):
        executor = object.__getattribute__(base, "executor")
        object.__setattr__(executor, field, object())

    _assert_malformed_base_rejected(monkeypatch, mutate)


def test_hostile_nested_value_hooks_are_not_executed(monkeypatch) -> None:
    hostile = _HostileNestedValue()

    def mutate(base):
        sdk_client = object.__getattribute__(base, "sdk_client")
        object.__setattr__(sdk_client, "_sdk_capability", hostile)

    _assert_malformed_base_rejected(monkeypatch, mutate)
    assert hostile.calls == 0


def test_malformed_base_error_hides_active_nested_context_and_authority(
    monkeypatch,
) -> None:
    base_composer, _, factory = _base_composer()
    base = base_composer.compose()
    sdk_client = object.__getattribute__(base, "sdk_client")
    capability = object.__getattribute__(sdk_client, "_sdk_capability")
    lifecycle = object.__getattribute__(base, "_lifecycle")
    executor = object.__getattribute__(base, "executor")
    marker = object()
    object.__setattr__(sdk_client, "_sdk_capability", marker)

    def return_base(receiver):
        del receiver
        return base

    outcome = module._compose_isolated(return_base, base_composer)
    try:
        try:
            raise RuntimeError("outer caller marker")
        except RuntimeError as outer:
            try:
                raise ValueError("inner caller marker") from outer
            except ValueError:
                module._return_or_raise_assembly(outcome)
    except OpenAIBridgedRuntimeDependencyError as error:
        assert error.__context__ is None
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
        forbidden = {
            id(base),
            id(sdk_client),
            id(capability),
            id(lifecycle),
            id(executor),
            id(marker),
            id(factory),
        }
        traceback = error.__traceback__
        while traceback is not None:
            frame_path = Path(traceback.tb_frame.f_code.co_filename)
            if "src" in frame_path.parts and (
                "provider_runtime_openai_bridged_v2" in frame_path.parts
            ):
                assert forbidden.isdisjoint(
                    id(value) for value in traceback.tb_frame.f_locals.values()
                )
            traceback = traceback.tb_next
    else:
        raise AssertionError("malformed base did not raise dependency error")


def test_malformed_matrix_leaves_no_bridged_module_global_history(
    monkeypatch,
) -> None:
    base, factory = _assert_malformed_base_rejected(
        monkeypatch,
        lambda value: object.__setattr__(
            object.__getattribute__(value, "sdk_client"),
            "_sdk_capability",
            object(),
        ),
    )
    markers = {id(base), id(factory), id(object.__getattribute__(base, "sdk_client"))}
    del base, factory
    gc.collect()
    assert all(id(value) not in markers for value in vars(module).values())
    assert all(
        value is not module._RESERVATION for value in module._LIVE_WRAPPERS.values()
    )


@pytest.mark.parametrize(
    "exception_type", [KeyboardInterrupt, SystemExit, GeneratorExit]
)
def test_baseexception_during_deep_validation_propagates_without_handoff(
    monkeypatch, exception_type
) -> None:
    from pastila_scout.provider_execution_openai_sdk_v2 import client as sdk_module

    base_composer, _, factory = _base_composer()
    base = base_composer.compose()
    expected = exception_type()
    tracker_before = dict(module._LIVE_WRAPPERS)

    def interrupt(value):
        del value
        raise expected

    monkeypatch.setattr(sdk_module, "_validated_create_authority", interrupt)

    def return_base(receiver):
        del receiver
        return base

    with pytest.raises(exception_type) as captured:
        module._compose_isolated(return_base, base_composer)
    assert captured.value is expected
    assert module._LIVE_WRAPPERS == tracker_before
    assert factory.clients[0].close_calls == 0


@pytest.mark.parametrize(
    "exception_type", [KeyboardInterrupt, SystemExit, GeneratorExit]
)
def test_bridge_baseexception_propagates_after_required_rollback(
    monkeypatch, exception_type
) -> None:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base, _, factory = _base_composer()
    composer = OpenAIBridgedRuntimeComposerV2(base)
    expected = exception_type()
    registrations_before = dict(module._LIVE_WRAPPERS)

    def failure(client):
        del client
        raise expected

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", failure)
    with pytest.raises(exception_type) as captured:
        composer.compose()
    assert captured.value is expected
    assert factory.clients[0].close_calls == 1
    assert module._LIVE_WRAPPERS == registrations_before


def test_duplicate_live_base_rejects_without_closing_first() -> None:
    base_composer, _, factory = _base_composer()
    base = base_composer.compose()

    def return_base(receiver):
        del receiver
        return base

    first = module._compose_isolated(return_base, base_composer)
    second = module._compose_isolated(return_base, base_composer)
    assert type(first) is OpenAIBridgedRuntimeCompositionV2
    assert type(second) is module._SafeAssemblyFailure
    assert second.category == "duplicate"
    assert base.closed is False
    assert factory.clients[0].close_calls == 0
    first.close()


def test_cross_composer_duplicate_live_base_is_rejected() -> None:
    base_composer, _, factory = _base_composer()
    base = base_composer.compose()

    def return_base(receiver):
        del receiver
        return base

    first = module._compose_isolated(return_base, base_composer)
    second = module._compose_isolated(return_base, base_composer)
    assert type(first) is OpenAIBridgedRuntimeCompositionV2
    assert type(second) is module._SafeAssemblyFailure
    assert second.category == "duplicate"
    assert factory.clients[0].close_calls == 0
    first.close()


def test_closed_base_is_rejected_without_cleanup_retry() -> None:
    base_composer, _, factory = _base_composer()
    base = base_composer.compose()
    base.close()

    def return_base(receiver):
        del receiver
        return base

    result = module._compose_isolated(return_base, base_composer)
    assert type(result) is module._SafeAssemblyFailure
    assert result.category == "dependency"
    assert factory.clients[0].close_calls == 1


def test_abandoned_wrapper_releases_live_registration() -> None:
    base_composer, _, _ = _base_composer()
    base = base_composer.compose()

    def return_base(receiver):
        del receiver
        return base

    result = module._compose_isolated(return_base, base_composer)
    assert type(result) is OpenAIBridgedRuntimeCompositionV2
    identity = id(base)
    assert identity in module._LIVE_WRAPPERS
    del result
    gc.collect()
    assert identity not in module._LIVE_WRAPPERS


def test_repeated_composition_uses_fresh_independent_bases() -> None:
    base, source, factory = _base_composer()
    composer = OpenAIBridgedRuntimeComposerV2(base)
    first = composer.compose()
    second = composer.compose()
    assert first is not second
    assert object.__getattribute__(
        first, "_base_composition"
    ) is not object.__getattribute__(second, "_base_composition")
    assert source.calls == factory.calls == 2
    first.close()
    second.close()
    assert [client.close_calls for client in factory.clients] == [1, 1]


def test_nested_compose_during_bridge_bootstrap_keeps_ownership_independent(
    monkeypatch,
) -> None:
    from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

    base, source, factory = _base_composer()
    composer = OpenAIBridgedRuntimeComposerV2(base)
    authentic = bootstrap._bootstrap_bridge
    nested: list[OpenAIBridgedRuntimeCompositionV2] = []
    entered = False

    def reentrant(client):
        nonlocal entered
        if not entered:
            entered = True
            nested.append(composer.compose())
        return authentic(client)

    monkeypatch.setattr(bootstrap, "_bootstrap_bridge", reentrant)
    outer = composer.compose()
    inner = nested.pop()
    assert type(outer) is OpenAIBridgedRuntimeCompositionV2
    assert type(inner) is OpenAIBridgedRuntimeCompositionV2
    assert object.__getattribute__(
        outer, "_base_composition"
    ) is not object.__getattribute__(inner, "_base_composition")
    assert source.calls == factory.calls == 2
    outer.close()
    inner.close()
    assert [client.close_calls for client in factory.clients] == [1, 1]


def test_reentrant_close_through_alias_delegates_once() -> None:
    composition, _, _, factory = _compose()
    factory.clients[0].close_callback = composition.close
    alias = copy.copy(composition)
    alias.close()
    assert composition.closed is True
    assert factory.clients[0].close_calls == 1


def test_direct_composition_construction_rejects() -> None:
    with pytest.raises(OpenAIBridgedRuntimeConfigurationError):
        OpenAIBridgedRuntimeCompositionV2(object())


def test_public_errors_hide_active_caller_context() -> None:
    try:
        raise ValueError("caller secret")
    except ValueError:
        with pytest.raises(OpenAIBridgedRuntimeConfigurationError) as captured:
            OpenAIBridgedRuntimeComposerV2(object())
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_no_lower_layer_imports_new_package() -> None:
    marker = "provider_runtime_openai_bridged_v2"
    for path in (ROOT / "src" / "pastila_scout").rglob("*.py"):
        if marker in path.as_posix():
            continue
        assert marker not in path.read_text(encoding="utf-8")


class _CallableDescriptor:
    def __init__(self, function: object) -> None:
        self.function = function

    def __get__(self, instance: object, owner: object) -> object:
        del instance, owner
        return self.function

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self.function(*args, **kwargs)


class _NonCallableDescriptor:
    def __get__(self, instance: object, owner: object) -> object:
        del instance, owner
        return object()


class _HostileNestedValue:
    def __init__(self) -> None:
        object.__setattr__(self, "calls", 0)

    def _called(self):
        object.__setattr__(self, "calls", object.__getattribute__(self, "calls") + 1)
        raise AssertionError("hostile nested hook executed")

    __repr__ = _called
    __str__ = _called
    __bool__ = _called
    __hash__ = _called

    def __eq__(self, other: object) -> bool:
        del other
        return self._called()

    def __getattr__(self, name: str) -> object:
        del name
        return self._called()
