from __future__ import annotations

import ast
import copy
import gc
import pickle
import subprocess
import sys
from dataclasses import fields, is_dataclass
from functools import cached_property, partial
from pathlib import Path
from types import CellType, FunctionType, MethodType, ModuleType
from typing import ClassVar

import pytest
from pydantic import ValidationError

import pastila_scout.provider_runtime_openai_smoke_v2 as public_api
from pastila_scout.provider_runtime_openai_smoke_v2 import (
    OpenAISmokeTestConfigurationError,
    OpenAISmokeTestConfigurationV2,
    OpenAISmokeTestConfirmationError,
    OpenAISmokeTestDependencyError,
    OpenAISmokeTestError,
    OpenAISmokeTestResultV2,
    OpenAISmokeTestRunnerV2,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_runtime_openai_smoke_v2"
_DEFAULT_EXECUTION_FAILURE = object()


def _configuration(*, confirm_live: bool = True) -> OpenAISmokeTestConfigurationV2:
    return OpenAISmokeTestConfigurationV2(
        confirm_live=confirm_live,
        model="gpt-contract-model",
        timeout_seconds=10,
    )


class _FakeExecutor:
    def __init__(
        self,
        events: list[str],
        *,
        response_text: str = "SMOKE_OK",
        failure: BaseException | None = None,
    ) -> None:
        self.events = events
        self.response_text = response_text
        self.failure = failure

    def execute(self) -> str:
        self.events.append("execute")
        if self.failure is not None:
            raise self.failure
        return self.response_text


class _FakeComposition:
    def __init__(
        self,
        events: list[str],
        executor: _FakeExecutor,
        *,
        close_failure: BaseException | None = None,
    ) -> None:
        self.events = events
        self.executor = executor
        self.close_failure = close_failure

    def close(self) -> None:
        self.events.append("close")
        if self.close_failure is not None:
            raise self.close_failure


class _FakeComposer:
    def __init__(
        self,
        events: list[str],
        composition: _FakeComposition,
        *,
        failure: BaseException | None = None,
    ) -> None:
        self.events = events
        self.composition = composition
        self.failure = failure
        self.arguments: tuple[str, str, float] | None = None

    def compose(
        self, *, api_key: str, model: str, timeout_seconds: float
    ) -> _FakeComposition:
        self.events.append("compose")
        self.arguments = (api_key, model, timeout_seconds)
        if self.failure is not None:
            raise self.failure
        return self.composition


class _FakeCredentialSource:
    def __init__(
        self,
        events: list[str],
        *,
        api_key: str = "injected-test-key",
        failure: BaseException | None = None,
    ) -> None:
        self.events = events
        self.api_key = api_key
        self.failure = failure

    def get_api_key(self) -> str:
        self.events.append("credential")
        if self.failure is not None:
            raise self.failure
        return self.api_key


def _valid_composer(events: list[str]) -> _FakeComposer:
    return _FakeComposer(events, _FakeComposition(events, _FakeExecutor(events)))


class _CachedPropertySource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    @cached_property
    def get_api_key(self):
        self.counters.append("cached_property")
        return lambda: "key"


class _RecordingDescriptor:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    def __get__(self, instance, owner):
        del instance, owner
        self.counters.append("descriptor")
        return lambda: "key"


class _DescriptorSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters
        type(self).get_api_key = _RecordingDescriptor(counters)  # type: ignore[attr-defined]


class _DynamicGetattrSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    def __getattr__(self, name):
        self.counters.append(name)
        return lambda: "key"


class _DynamicGetattributeSource:
    def __init__(self, counters: list[str]) -> None:
        object.__setattr__(self, "counters", counters)

    def __getattribute__(self, name):
        if name != "counters":
            object.__getattribute__(self, "counters").append(name)
        return object.__getattribute__(self, name)

    def get_api_key(self):
        return "key"


class _AsyncCredentialSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    async def get_api_key(self):
        self.counters.append("async")
        return "key"


class _GeneratorCredentialSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    def get_api_key(self):
        self.counters.append("generator")
        yield "key"


class _WrongCredentialSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    def get_api_key(self, required):
        del required
        self.counters.append("wrong")
        return "key"


class _AbstractCredentialSource:
    def __init__(self, counters: list[str]) -> None:
        self.counters = counters

    def get_api_key(self):
        self.counters.append("abstract")
        return "key"


_AbstractCredentialSource.get_api_key.__isabstractmethod__ = True


class _MissingExecutor:
    def close(self) -> None:
        raise AssertionError("cleanup must not be guessed")


class _MissingClose:
    def __init__(self) -> None:
        self.executor = _FakeExecutor([])


class _DescriptorComposition:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    @property
    def executor(self):
        self.events.append("executor-property")
        return _FakeExecutor(self.events)

    @property
    def close(self):
        self.events.append("close-property")
        return lambda: None


class _AsyncExecutor:
    async def execute(self):
        return "SMOKE_OK"


class _GeneratorExecutor:
    def execute(self):
        yield "SMOKE_OK"


class _WrongExecutor:
    def execute(self, required):
        del required
        return "SMOKE_OK"


class _AsyncCloseComposition:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.executor = _FakeExecutor(events)

    async def close(self) -> None:
        self.events.append("close")


class _WrongCloseComposition:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.executor = _FakeExecutor(events)

    def close(self, required) -> None:
        del required
        self.events.append("close")


def _runner(
    *,
    events: list[str] | None = None,
    response_text: str = "SMOKE_OK",
    credential_failure: BaseException | None = None,
    composition_failure: BaseException | None = None,
    execution_failure: BaseException | None | object = _DEFAULT_EXECUTION_FAILURE,
    close_failure: BaseException | None = None,
) -> OpenAISmokeTestRunnerV2:
    event_log = [] if events is None else events
    failure = (
        RuntimeError("offline execution failure")
        if execution_failure is _DEFAULT_EXECUTION_FAILURE
        else execution_failure
    )
    assert failure is None or isinstance(failure, BaseException)
    executor = _FakeExecutor(event_log, response_text=response_text, failure=failure)
    composition = _FakeComposition(event_log, executor, close_failure=close_failure)
    composer = _FakeComposer(event_log, composition, failure=composition_failure)
    credential = _FakeCredentialSource(event_log, failure=credential_failure)
    return OpenAISmokeTestRunnerV2(credential, composer)


def test_public_api_is_exact_and_private_contract_is_not_exported() -> None:
    assert public_api.__all__ == (
        "OpenAISmokeTestConfigurationError",
        "OpenAISmokeTestConfigurationV2",
        "OpenAISmokeTestConfirmationError",
        "OpenAISmokeTestDependencyError",
        "OpenAISmokeTestError",
        "OpenAISmokeTestResultV2",
        "OpenAISmokeTestRunnerV2",
    )
    assert (
        tuple(name for name in public_api.__all__ if hasattr(public_api, name))
        == public_api.__all__
    )
    assert not hasattr(public_api, "_OpenAISmokeTestRunnerContractV2")


def test_error_taxonomy_is_stable() -> None:
    assert issubclass(OpenAISmokeTestConfigurationError, OpenAISmokeTestError)
    assert issubclass(OpenAISmokeTestConfirmationError, OpenAISmokeTestError)
    assert issubclass(OpenAISmokeTestDependencyError, OpenAISmokeTestError)


def test_configuration_accepts_exact_minimal_policy() -> None:
    configuration = _configuration()

    assert configuration.confirm_live is True
    assert configuration.model == "gpt-contract-model"
    assert configuration.timeout_seconds == 10
    assert type(configuration.timeout_seconds) is int
    assert set(type(configuration).model_fields) == {
        "confirm_live",
        "model",
        "timeout_seconds",
    }


@pytest.mark.parametrize("value", (None, 0, 1, "true", type("B", (int,), {})(1)))
def test_configuration_requires_exact_boolean_confirmation(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=value,  # type: ignore[arg-type]
            model="gpt-contract-model",
            timeout_seconds=10,
        )


@pytest.mark.parametrize("value", (None, False, 1, "", " ", " model", "model "))
def test_configuration_rejects_invalid_model(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=True,
            model=value,  # type: ignore[arg-type]
            timeout_seconds=10,
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        False,
        True,
        0,
        -1,
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        "10",
    ),
)
def test_configuration_rejects_invalid_timeout(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=True,
            model="gpt-contract-model",
            timeout_seconds=value,  # type: ignore[arg-type]
        )


def test_configuration_forbids_extra_operational_fields() -> None:
    for field in ("credential", "prompt", "headers", "max_retries"):
        with pytest.raises(ValidationError):
            OpenAISmokeTestConfigurationV2.model_validate(
                {
                    "confirm_live": True,
                    "model": "gpt-contract-model",
                    "timeout_seconds": 10,
                    field: "forbidden",
                }
            )


def test_configuration_is_immutable_and_copy_safe() -> None:
    configuration = _configuration()

    with pytest.raises(ValidationError):
        configuration.model = "changed"  # type: ignore[misc]
    assert copy.copy(configuration) == configuration
    assert copy.deepcopy(configuration) == configuration
    assert copy.copy(configuration) is not configuration
    assert copy.deepcopy(configuration) is not configuration


def test_runner_wraps_invalid_and_copied_invalid_configuration() -> None:
    runner = _runner()
    invalid = _configuration().model_copy(update={"timeout_seconds": 0})

    for value in (None, object(), invalid):
        with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
            runner.run(value)
        assert raised.value.args == ("invalid OpenAI smoke-test configuration",)
        _assert_isolated(raised.value)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("confirm_live", 1),
        ("confirm_live", "true"),
        ("model", ""),
        ("model", " padded "),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("timeout_seconds", float("nan")),
        ("timeout_seconds", object()),
    ),
)
def test_runner_defensively_rejects_complete_copied_invalid_matrix(
    field: str,
    value: object,
) -> None:
    configuration = _configuration().model_copy(update={field: value})

    with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
        _runner().run(configuration)

    assert raised.value.args == ("invalid OpenAI smoke-test configuration",)
    _assert_isolated(raised.value)
    _assert_smoke_traceback_is_safe(raised.value, configuration)


def test_confirmation_is_required_before_non_operational_failure() -> None:
    with pytest.raises(OpenAISmokeTestConfirmationError) as raised:
        _runner().run(_configuration(confirm_live=False))

    assert raised.value.args == (
        "explicit live OpenAI smoke-test confirmation is required",
    )
    _assert_isolated(raised.value)


def test_confirmation_reaches_only_injected_offline_execution() -> None:
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        _runner().run(_configuration(confirm_live=True))

    assert raised.value.args == ("OpenAI smoke-test execution failed",)
    _assert_isolated(raised.value)


def test_confirmed_offline_happy_path_runs_exact_sequence_once() -> None:
    events: list[str] = []
    executor = _FakeExecutor(events)
    composition = _FakeComposition(events, executor)
    composer = _FakeComposer(events, composition)
    credential = _FakeCredentialSource(events)
    runner = OpenAISmokeTestRunnerV2(credential, composer)

    result = runner.run(_configuration())

    assert result == OpenAISmokeTestResultV2(success=True, response_text="SMOKE_OK")
    assert events == ["credential", "compose", "execute", "close"]
    assert composer.arguments == ("injected-test-key", "gpt-contract-model", 10)
    with pytest.raises(ValidationError):
        result.response_text = "changed"  # type: ignore[misc]


def test_credential_failure_stops_before_composition() -> None:
    events: list[str] = []
    runner = _runner(events=events, credential_failure=RuntimeError("secret"))

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    assert raised.value.args == ("OpenAI smoke-test credential source failed",)
    assert events == ["credential"]
    _assert_isolated(raised.value)


def test_composition_failure_stops_before_execution_and_close() -> None:
    events: list[str] = []
    runner = _runner(events=events, composition_failure=RuntimeError("secret"))

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    assert raised.value.args == ("OpenAI smoke-test runtime composition failed",)
    assert events == ["credential", "compose"]
    _assert_isolated(raised.value)


def test_execution_failure_still_closes_exactly_once() -> None:
    events: list[str] = []
    runner = _runner(events=events, execution_failure=RuntimeError("secret"))

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    assert raised.value.args == ("OpenAI smoke-test execution failed",)
    assert events == ["credential", "compose", "execute", "close"]
    _assert_isolated(raised.value)


@pytest.mark.parametrize("execution_fails", (False, True))
def test_close_failure_has_lifecycle_precedence(execution_fails: bool) -> None:
    events: list[str] = []
    execution_failure = RuntimeError("execution secret") if execution_fails else None
    runner = _runner(
        events=events,
        execution_failure=execution_failure,
        close_failure=RuntimeError("close secret"),
    )

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    assert raised.value.args == ("OpenAI smoke-test runtime cleanup failed",)
    assert events == ["credential", "compose", "execute", "close"]
    _assert_isolated(raised.value)


def test_dependency_failures_retain_no_injected_runtime_objects() -> None:
    events: list[str] = []
    executor = _FakeExecutor(events, failure=RuntimeError("execution secret"))
    composition = _FakeComposition(events, executor)
    composer = _FakeComposer(events, composition)
    credential = _FakeCredentialSource(events, api_key="SECRET_INJECTED_KEY")
    runner = OpenAISmokeTestRunnerV2(credential, composer)

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    _assert_smoke_traceback_is_safe(
        raised.value,
        runner,
        credential,
        composer,
        composition,
        executor,
        "SECRET_INJECTED_KEY",
        "execution secret",
    )


@pytest.mark.parametrize(
    "method_kind", ("ordinary", "inherited", "overridden", "static", "class")
)
def test_constructor_accepts_safe_credential_method_shapes(method_kind: str) -> None:
    events: list[str] = []

    class Base:
        def get_api_key(self):
            events.append("credential")
            return "key"

    if method_kind == "ordinary":
        source = Base()
    elif method_kind == "inherited":

        class Source(Base):
            pass

        source = Source()
    elif method_kind == "overridden":

        class Source(Base):
            def get_api_key(self):
                events.append("credential")
                return "key"

        source = Source()
    elif method_kind == "static":

        class Source:
            @staticmethod
            def get_api_key():
                events.append("credential")
                return "key"

        source = Source()
    else:

        class Source:
            @classmethod
            def get_api_key(cls):
                del cls
                events.append("credential")
                return "key"

        source = Source()

    runner = OpenAISmokeTestRunnerV2(source, _valid_composer(events))
    assert events == []
    assert runner.run(_configuration()).response_text == "SMOKE_OK"
    assert events == ["credential", "compose", "execute", "close"]


@pytest.mark.parametrize(
    "source_factory",
    (
        lambda counters: type(
            "PropertySource",
            (),
            {"get_api_key": property(lambda self: counters.append("property"))},
        )(),
        lambda counters: _CachedPropertySource(counters),
        lambda counters: _DescriptorSource(counters),
        lambda counters: _DynamicGetattrSource(counters),
        lambda counters: _DynamicGetattributeSource(counters),
        lambda counters: _AsyncCredentialSource(counters),
        lambda counters: _GeneratorCredentialSource(counters),
        lambda counters: _WrongCredentialSource(counters),
        lambda counters: _AbstractCredentialSource(counters),
    ),
)
def test_constructor_rejects_unsafe_credential_authority_without_execution(
    source_factory,
) -> None:
    counters: list[str] = []
    source = source_factory(counters)

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        OpenAISmokeTestRunnerV2(source, _valid_composer(counters))

    assert raised.value.args == ("invalid OpenAI smoke-test dependency",)
    assert counters == []
    _assert_isolated(raised.value)
    _assert_smoke_traceback_is_safe(raised.value, source)


def test_constructor_rejects_instance_injected_and_forged_metadata() -> None:
    events: list[str] = []

    class Source:
        pass

    source = Source()
    source.get_api_key = lambda: "key"  # type: ignore[attr-defined]
    with pytest.raises(OpenAISmokeTestDependencyError):
        OpenAISmokeTestRunnerV2(source, _valid_composer(events))

    class ForgedSource:
        def get_api_key(self, required):
            del required
            return "key"

    ForgedSource.get_api_key.__signature__ = object()  # type: ignore[attr-defined]
    ForgedSource.get_api_key.__wrapped__ = lambda self: "key"  # type: ignore[attr-defined]
    with pytest.raises(OpenAISmokeTestDependencyError):
        OpenAISmokeTestRunnerV2(ForgedSource(), _valid_composer(events))
    assert events == []


def test_constructor_rejects_unsafe_composer_shapes_without_execution() -> None:
    events: list[str] = []

    class WrongComposer:
        async def compose(self, *, api_key, model, timeout_seconds):
            del api_key, model, timeout_seconds

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        OpenAISmokeTestRunnerV2(_FakeCredentialSource(events), WrongComposer())
    assert raised.value.args == ("invalid OpenAI smoke-test dependency",)
    assert events == []


@pytest.mark.parametrize("method_kind", ("static", "class"))
def test_static_and_class_composer_and_executor_shapes_are_supported(
    method_kind: str,
) -> None:
    events: list[str] = []

    if method_kind == "static":

        class Executor:
            @staticmethod
            def execute():
                events.append("execute")
                return "SMOKE_OK"

        class Composer:
            @staticmethod
            def compose(*, api_key, model, timeout_seconds):
                assert (api_key, model, timeout_seconds) == (
                    "injected-test-key",
                    "gpt-contract-model",
                    10,
                )
                events.append("compose")
                return _FakeComposition(events, Executor())  # type: ignore[arg-type]

    else:

        class Executor:
            @classmethod
            def execute(cls):
                del cls
                events.append("execute")
                return "SMOKE_OK"

        class Composer:
            @classmethod
            def compose(cls, *, api_key, model, timeout_seconds):
                del cls
                assert (api_key, model, timeout_seconds) == (
                    "injected-test-key",
                    "gpt-contract-model",
                    10,
                )
                events.append("compose")
                return _FakeComposition(events, Executor())  # type: ignore[arg-type]

    runner = OpenAISmokeTestRunnerV2(_FakeCredentialSource(events), Composer())
    assert runner.run(_configuration()).response_text == "SMOKE_OK"
    assert events == ["credential", "compose", "execute", "close"]


@pytest.mark.parametrize(
    "credential",
    (
        None,
        b"key",
        False,
        True,
        1,
        1.0,
        "",
        "   ",
        " padded ",
        type("S", (str,), {})("key"),
        object(),
    ),
)
def test_malformed_credential_output_never_reaches_composer(credential: object) -> None:
    events: list[str] = []
    executor = _FakeExecutor(events)
    composition = _FakeComposition(events, executor)
    composer = _FakeComposer(events, composition)
    source = _FakeCredentialSource(events, api_key=credential)  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(source, composer)

    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())

    assert raised.value.args == ("OpenAI smoke-test credential source failed",)
    assert events == ["credential"]
    assert composer.arguments is None


def test_hostile_credential_output_is_not_represented_or_coerced() -> None:
    class Hostile:
        repr_calls = 0
        str_calls = 0

        def __repr__(self):
            type(self).repr_calls += 1
            raise AssertionError("repr")

        def __str__(self):
            type(self).str_calls += 1
            raise AssertionError("str")

    events: list[str] = []
    source = _FakeCredentialSource(events, api_key=Hostile())  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(source, _valid_composer(events))
    with pytest.raises(OpenAISmokeTestDependencyError):
        runner.run(_configuration())
    assert events == ["credential"]
    assert Hostile.repr_calls == Hostile.str_calls == 0


@pytest.mark.parametrize(
    "composition", (None, object(), _MissingExecutor(), _MissingClose())
)
def test_malformed_composition_handoff_is_rejected_without_guessed_cleanup(
    composition: object,
) -> None:
    events: list[str] = []
    composer = _FakeComposer(events, composition)  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(_FakeCredentialSource(events), composer)
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())
    assert raised.value.args == ("OpenAI smoke-test runtime composition failed",)
    assert events == ["credential", "compose"]


def test_descriptor_backed_composition_authorities_are_not_executed() -> None:
    events: list[str] = []
    composition = _DescriptorComposition(events)
    composer = _FakeComposer(events, composition)  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(_FakeCredentialSource(events), composer)
    with pytest.raises(OpenAISmokeTestDependencyError):
        runner.run(_configuration())
    assert events == ["credential", "compose"]


@pytest.mark.parametrize(
    "composition_type", (_AsyncCloseComposition, _WrongCloseComposition)
)
def test_incompatible_close_authority_is_rejected_before_ownership(
    composition_type,
) -> None:
    events: list[str] = []
    composition = composition_type(events)
    runner = OpenAISmokeTestRunnerV2(
        _FakeCredentialSource(events),
        _FakeComposer(events, composition),  # type: ignore[arg-type]
    )
    with pytest.raises(OpenAISmokeTestDependencyError):
        runner.run(_configuration())
    assert events == ["credential", "compose"]


@pytest.mark.parametrize(
    "executor", (_AsyncExecutor(), _GeneratorExecutor(), _WrongExecutor())
)
def test_malformed_executor_authority_is_rejected_before_ownership(
    executor: object,
) -> None:
    events: list[str] = []
    composition = _FakeComposition(events, executor)  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(
        _FakeCredentialSource(events), _FakeComposer(events, composition)
    )
    with pytest.raises(OpenAISmokeTestDependencyError):
        runner.run(_configuration())
    assert events == ["credential", "compose"]


@pytest.mark.parametrize(
    "output",
    (
        None,
        object(),
        b"text",
        False,
        True,
        1,
        "",
        "   ",
        type("S", (str,), {})("text"),
        {},
        [],
        ("a", "b"),
    ),
)
def test_malformed_execution_outputs_fail_and_close_once(output: object) -> None:
    events: list[str] = []

    class Executor:
        def execute(self):
            events.append("execute")
            return output

    composition = _FakeComposition(events, Executor())  # type: ignore[arg-type]
    runner = OpenAISmokeTestRunnerV2(
        _FakeCredentialSource(events), _FakeComposer(events, composition)
    )
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(_configuration())
    assert raised.value.args == ("OpenAI smoke-test execution failed",)
    assert events == ["credential", "compose", "execute", "close"]


def test_public_result_defensively_revalidates_copied_invalid_instances() -> None:
    valid = OpenAISmokeTestResultV2(success=True, response_text="SMOKE_OK")
    for update in (
        {"success": "yes"},
        {"response_text": ""},
        {"response_text": object()},
    ):
        forged = valid.model_copy(update=update)
        with pytest.raises(ValidationError):
            OpenAISmokeTestResultV2.model_validate(forged)


@pytest.mark.parametrize("stage", ("credential", "compose", "execute", "close"))
@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
def test_base_exceptions_propagate_with_sanitized_smoke_tracebacks(
    stage: str, error_type: type[BaseException]
) -> None:
    marker = "BASE_EXCEPTION_SECRET"
    events: list[str] = []
    failure = error_type(marker)
    runner = _runner(
        events=events,
        credential_failure=failure if stage == "credential" else None,  # type: ignore[arg-type]
        composition_failure=failure if stage == "compose" else None,  # type: ignore[arg-type]
        execution_failure=failure if stage == "execute" else None,  # type: ignore[arg-type]
        close_failure=failure if stage == "close" else None,  # type: ignore[arg-type]
    )
    with pytest.raises(error_type) as raised:
        runner.run(_configuration())
    assert raised.value is failure
    _assert_smoke_traceback_is_safe(raised.value, runner)
    for frame_name, local_values in _smoke_traceback_locals(raised.value):
        if frame_name == "run":
            assert tuple(local_values) == ("outcome",)


def test_pinned_authorities_ignore_ordinary_method_replacement() -> None:
    events: list[str] = []
    source = _FakeCredentialSource(events)
    composer = _valid_composer(events)
    runner = OpenAISmokeTestRunnerV2(source, composer)
    original_source_method = _FakeCredentialSource.get_api_key
    original_composer_method = _FakeComposer.compose
    source.get_api_key = lambda: "replacement"  # type: ignore[method-assign]
    composer.compose = lambda **kwargs: (_ for _ in ()).throw(AssertionError(kwargs))  # type: ignore[method-assign]
    _FakeCredentialSource.get_api_key = lambda self: "class replacement"  # type: ignore[method-assign]
    _FakeComposer.compose = lambda self, **kwargs: (_ for _ in ()).throw(  # type: ignore[method-assign]
        AssertionError(kwargs)
    )
    try:
        assert runner.run(_configuration()).response_text == "SMOKE_OK"
    finally:
        _FakeCredentialSource.get_api_key = original_source_method
        _FakeComposer.compose = original_composer_method
    assert events == ["credential", "compose", "execute", "close"]


def test_repeated_success_returns_fresh_results_without_runner_history() -> None:
    events: list[str] = []
    runner = _runner(events=events, execution_failure=None)
    first = runner.run(_configuration())
    second = runner.run(_configuration())
    assert first == second
    assert first is not second
    assert events == ["credential", "compose", "execute", "close"] * 2
    assert repr(runner) == "OpenAISmokeTestRunnerV2()"


def test_reentrant_run_uses_independent_per_call_state_and_cleanup() -> None:
    events: list[str] = []

    class Credential:
        def __init__(self) -> None:
            self.runner: OpenAISmokeTestRunnerV2 | None = None
            self.inside = False
            self.nested_result: OpenAISmokeTestResultV2 | None = None

        def get_api_key(self):
            events.append("credential")
            if not self.inside:
                self.inside = True
                assert self.runner is not None
                self.nested_result = self.runner.run(_configuration())
                self.inside = False
            return "key"

    class Composer:
        def compose(self, *, api_key, model, timeout_seconds):
            assert (api_key, model, timeout_seconds) == (
                "key",
                "gpt-contract-model",
                10,
            )
            events.append("compose")
            return _FakeComposition(events, _FakeExecutor(events))

    credential = Credential()
    runner = OpenAISmokeTestRunnerV2(credential, Composer())
    credential.runner = runner
    outer = runner.run(_configuration())

    assert outer.response_text == "SMOKE_OK"
    assert credential.nested_result is not None
    assert credential.nested_result.response_text == "SMOKE_OK"
    assert events == [
        "credential",
        "credential",
        "compose",
        "execute",
        "close",
        "compose",
        "execute",
        "close",
    ]


@pytest.mark.parametrize("confirmed", (False, True))
def test_errors_are_isolated_from_nested_active_exceptions(confirmed: bool) -> None:
    outer = RuntimeError("caller outer")
    inner = RuntimeError("caller inner")
    try:
        raise outer
    except RuntimeError:
        try:
            raise inner
        except RuntimeError:
            with pytest.raises(OpenAISmokeTestError) as raised:
                _runner().run(_configuration(confirm_live=confirmed))

    _assert_isolated(raised.value)
    assert raised.value.__context__ is not outer
    assert raised.value.__context__ is not inner


def test_runner_traceback_and_recursive_graph_retain_no_configuration() -> None:
    runner = _runner()
    configuration = _configuration()
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(configuration)

    roots: list[object] = [raised.value]
    traceback = raised.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
            roots.extend(traceback.tb_frame.f_locals.values())
        traceback = traceback.tb_next
    seen: set[int] = set()

    def visit(value: object) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        assert value is not configuration
        assert value is not runner
        if isinstance(value, BaseException):
            visit(value.args)
            if value.__context__ is not None:
                visit(value.__context__)
            if value.__cause__ is not None:
                visit(value.__cause__)
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    for root in roots:
        visit(root)


@pytest.mark.parametrize(
    ("confirmed", "error_type"),
    (
        (False, OpenAISmokeTestConfirmationError),
        (True, OpenAISmokeTestDependencyError),
    ),
)
def test_confirmation_scalar_and_configuration_fields_leave_no_traceback_state(
    confirmed: bool,
    error_type: type[OpenAISmokeTestError],
) -> None:
    configuration = OpenAISmokeTestConfigurationV2(
        confirm_live=confirmed,
        model="SECRET_MODEL_MARKER_R2",
        timeout_seconds=987654321,
    )

    with pytest.raises(error_type) as raised:
        _runner().run(configuration)

    _assert_smoke_traceback_is_safe(
        raised.value,
        configuration,
        "SECRET_MODEL_MARKER_R2",
        987654321,
    )
    for frame_name, local_values in _smoke_traceback_locals(raised.value):
        assert not {"confirmed", "confirm_live", "model", "timeout_seconds"} & set(
            local_values
        )
        if frame_name == "run":
            assert tuple(local_values) == ("outcome",)


def test_hostile_copied_fields_execute_no_hooks_or_representations() -> None:
    class Hostile:
        calls: ClassVar[dict[str, int]] = {
            "bool": 0,
            "eq": 0,
            "float": 0,
            "int": 0,
            "repr": 0,
            "str": 0,
            "lt": 0,
            "gt": 0,
        }

        def _called(self, name: str):
            type(self).calls[name] += 1
            raise AssertionError(f"{name} hook executed")

        def __bool__(self):
            return self._called("bool")

        def __eq__(self, other):
            del other
            return self._called("eq")

        def __float__(self):
            return self._called("float")

        def __int__(self):
            return self._called("int")

        def __repr__(self):
            return self._called("repr")

        def __str__(self):
            return self._called("str")

        def __lt__(self, other):
            del other
            return self._called("lt")

        def __gt__(self, other):
            del other
            return self._called("gt")

    for field in ("confirm_live", "model", "timeout_seconds"):
        hostile = Hostile()
        configuration = _configuration().model_copy(update={field: hostile})
        with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
            _runner().run(configuration)
        _assert_smoke_traceback_is_safe(raised.value, configuration, hostile)
    assert set(Hostile.calls.values()) == {0}


def test_runner_is_immutable_stateless_and_copy_safe() -> None:
    runner = _runner()

    assert not hasattr(runner, "__dict__")
    assert copy.copy(runner) is runner
    assert copy.deepcopy(runner) is runner
    memo: dict[int, object] = {}
    assert copy.deepcopy(runner, memo) is runner
    assert memo[id(runner)] is runner
    assert copy.deepcopy((runner, {"runner": runner}))[0] is runner
    with pytest.raises(AttributeError, match="OpenAI smoke-test runner is immutable"):
        runner.state = "forbidden"  # type: ignore[attr-defined]
    with pytest.raises(AttributeError, match="OpenAI smoke-test runner is immutable"):
        del runner.state  # type: ignore[attr-defined]


def test_runner_representation_is_fixed_and_state_free() -> None:
    first = _runner()
    second = _runner()

    assert repr(first) == str(first) == "OpenAISmokeTestRunnerV2()"
    assert repr(second) == repr(first)
    assert "0x" not in repr(first)


def test_runner_rejects_every_pickle_protocol() -> None:
    runner = _runner()

    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError) as raised:
            pickle.dumps(runner, protocol=protocol)
        assert raised.value.args == ("OpenAI smoke-test runners cannot be serialized",)
        _assert_isolated(raised.value)


def test_repeated_calls_are_fresh_deterministic_and_stateless() -> None:
    runner = _runner()
    cases = (
        (_configuration(confirm_live=False), OpenAISmokeTestConfirmationError),
        (_configuration(confirm_live=True), OpenAISmokeTestDependencyError),
        (
            _configuration().model_copy(update={"model": ""}),
            OpenAISmokeTestConfigurationError,
        ),
        (_configuration(confirm_live=False), OpenAISmokeTestConfirmationError),
        (_configuration(confirm_live=True), OpenAISmokeTestDependencyError),
    )
    errors: list[OpenAISmokeTestError] = []

    for configuration, error_type in cases:
        with pytest.raises(error_type) as raised:
            runner.run(configuration)
        errors.append(raised.value)
        _assert_smoke_traceback_is_safe(raised.value, configuration)

    assert len({id(error) for error in errors}) == len(errors)
    assert not hasattr(runner, "__dict__")
    assert repr(runner) == "OpenAISmokeTestRunnerV2()"


@pytest.mark.parametrize("path", ("invalid", "unconfirmed", "confirmed"))
def test_all_error_paths_isolate_hostile_nested_caller_context(path: str) -> None:
    class HostileCallerError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self):
            type(self).repr_calls += 1
            raise AssertionError("caller repr executed")

        def __str__(self):
            type(self).str_calls += 1
            raise AssertionError("caller str executed")

    if path == "invalid":
        configuration = _configuration().model_copy(update={"model": ""})
    else:
        configuration = _configuration(confirm_live=path == "confirmed")
    outer = HostileCallerError("outer")
    inner = HostileCallerError("inner")
    try:
        raise outer from RuntimeError("nested cause")
    except HostileCallerError:
        try:
            raise inner
        except HostileCallerError:
            with pytest.raises(OpenAISmokeTestError) as raised:
                _runner().run(configuration)

    _assert_isolated(raised.value)
    _assert_smoke_traceback_is_safe(
        raised.value, configuration, outer, inner, "outer", "inner"
    )
    assert HostileCallerError.repr_calls == HostileCallerError.str_calls == 0


def test_mixed_failures_leave_no_smoke_module_global_history() -> None:
    import pastila_scout.provider_runtime_openai_smoke_v2.models as models_module
    import pastila_scout.provider_runtime_openai_smoke_v2.runner as runner_module

    marker = "GLOBAL_MODEL_MARKER_R2"
    runner = _runner()
    configurations = (
        OpenAISmokeTestConfigurationV2(
            confirm_live=False, model=marker, timeout_seconds=123456789
        ),
        OpenAISmokeTestConfigurationV2(
            confirm_live=True, model=marker, timeout_seconds=123456789
        ),
        _configuration().model_copy(update={"model": ""}),
    )
    for configuration in configurations:
        with pytest.raises(OpenAISmokeTestError):
            runner.run(configuration)
    del configuration
    del configurations
    del runner
    gc.collect()

    for module in (models_module, runner_module):
        for value in vars(module).values():
            assert not isinstance(value, OpenAISmokeTestRunnerV2)
            assert not isinstance(value, OpenAISmokeTestConfigurationV2)
            if type(value) is str:
                assert value != marker


def test_package_contains_no_operational_capabilities_or_reverse_dependencies() -> None:
    forbidden_imports = {
        "dotenv",
        "httpx",
        "openai",
        "os",
        "requests",
        "socket",
        "urllib",
    }
    forbidden_calls = {"complete", "create", "create_client", "request"}
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not imports & forbidden_imports
        assert not calls & forbidden_calls

    for package in (
        "provider_v2",
        "provider_execution_v2",
        "provider_execution_openai_v2",
        "provider_execution_openai_sdk_v2",
        "provider_runtime_openai_v2",
    ):
        for path in (ROOT / "src" / "pastila_scout" / package).glob("*.py"):
            assert "provider_runtime_openai_smoke_v2" not in path.read_text(
                encoding="utf-8"
            )


def test_real_cli_has_no_smoke_import_registration_or_dispatch() -> None:
    source = (ROOT / "src" / "pastila_scout" / "cli.py").read_text(encoding="utf-8")

    assert "provider_runtime_openai_smoke_v2" not in source
    assert "confirm-live" not in source
    assert "openai smoke" not in source
    assert "openai_smoke" not in source


def test_documentation_records_canonical_and_expanded_selector_accounting() -> None:
    document = (
        ROOT / "docs" / "editorial-script-composer" / "Phase7_5_OpenAISmokeTest.md"
    ).read_text(encoding="utf-8")

    assert (
        'pytest -k "editorial_script_composer or provider_execution or '
        'provider_runtime_openai_v2"' in document
    )
    assert (
        'pytest -k "editorial_script_composer or provider_execution or '
        'provider_runtime_openai_v2 or provider_runtime_openai_smoke_v2"' in document
    )
    assert "excludes the focused smoke tests" in document


def test_clean_process_import_is_inert() -> None:
    script = """
import contextlib
import io
import os
import sys
import warnings

credential_reads = []
original_getenv = os.getenv
def guarded_getenv(name, *args, **kwargs):
    if name == "OPENAI_API_KEY":
        credential_reads.append(name)
        raise AssertionError("credential access")
    return original_getenv(name, *args, **kwargs)
os.getenv = guarded_getenv
stdout = io.StringIO()
stderr = io.StringIO()
before = set(sys.modules)
with warnings.catch_warnings(record=True) as caught:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        import pastila_scout.provider_runtime_openai_smoke_v2 as api
loaded = set(sys.modules) - before
assert credential_reads == []
assert stdout.getvalue() == ""
assert stderr.getvalue() == ""
assert caught == []
assert "openai" not in loaded
assert "pastila_scout.provider_runtime_openai_v2" not in loaded
assert len(api.__all__) == 7
"""
    subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True)


def _assert_isolated(error: BaseException) -> None:
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


def _smoke_traceback_locals(
    error: BaseException,
) -> list[tuple[str, dict[str, object]]]:
    frames: list[tuple[str, dict[str, object]]] = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
            frames.append(
                (traceback.tb_frame.f_code.co_name, dict(traceback.tb_frame.f_locals))
            )
        traceback = traceback.tb_next
    return frames


def _assert_smoke_traceback_is_safe(error: BaseException, *forbidden: object) -> None:
    roots: list[object] = [error]
    for _, local_values in _smoke_traceback_locals(error):
        roots.append(local_values)
    seen: set[int] = set()

    def visit(value: object) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        assert all(value is not item for item in forbidden)
        if type(value) is str:
            assert all(type(item) is not str or value != item for item in forbidden)
        if type(value) is int and type(value) is not bool:
            assert all(type(item) is not int or value != item for item in forbidden)
        if isinstance(value, BaseException):
            visit(value.args)
            visit(value.__dict__)
            if value.__context__ is not None:
                visit(value.__context__)
            if value.__cause__ is not None:
                visit(value.__cause__)
            traceback = value.__traceback__
            while traceback is not None:
                if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
                    visit(dict(traceback.tb_frame.f_locals))
                traceback = traceback.tb_next
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)
        elif isinstance(value, partial):
            visit(value.func)
            visit(value.args)
            visit(value.keywords)
        elif isinstance(value, MethodType):
            visit(value.__self__)
            visit(value.__func__)
        elif isinstance(value, CellType):
            visit(value.cell_contents)
        elif isinstance(value, FunctionType):
            if value.__closure__ is not None:
                visit(value.__closure__)
        elif is_dataclass(value) and not isinstance(value, type):
            for item in fields(value):
                visit(getattr(value, item.name))
        elif not isinstance(value, (type, ModuleType)):
            for slot in getattr(type(value), "__slots__", ()):
                if type(slot) is str and hasattr(value, slot):
                    visit(getattr(value, slot))

    for root in roots:
        visit(root)
