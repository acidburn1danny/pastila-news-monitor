from __future__ import annotations

import ast
import copy
import gc
import hashlib
import pickle
import sys
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction
from inspect import Parameter, Signature
from pathlib import Path
from types import CellType, ModuleType
from weakref import ref

import pytest
from pydantic import ValidationError

import pastila_scout.provider_runtime_openai_v2 as public_api
from pastila_scout.provider_execution_openai_sdk_v2 import (
    OpenAISDKCapabilityV2,
    OpenAISDKClientV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeCompositionV2,
    OpenAIRuntimeConfigurationError,
    OpenAIRuntimeConfigV2,
    OpenAIRuntimeCredentialError,
    OpenAIRuntimeDependencyError,
    OpenAIRuntimeLifecycleError,
)
from pastila_scout.provider_runtime_openai_v2.composition import (
    _OWNERSHIP_TRACKER,
    _RUNTIME_GENERATION_BY_TARGET_ID,
    _RUNTIME_REGISTRATIONS,
    _claim_factory_handoff,
    _claim_runtime_registration_authority,
    _mint_factory_handoff,
    _OwnershipRecord,
    _OwnershipState,
    _RuntimeRegistrationAuthority,
    _RuntimeValidatedClaim,
    _terminalize_exact_registration,
    _validate_api_key,
)
from pastila_scout.provider_runtime_openai_v2.models import (
    _OpenAIRuntimeLifecycleOwnerV2,
)
from pastila_scout.provider_runtime_openai_v2.production import (
    _EnvironmentOpenAICredentialSourceV2,
    _ExplicitOpenAICredentialSourceV2,
    _OfficialOpenAISDKFactoryV2,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_runtime_openai_v2"
FROZEN_PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_openai_sdk_v2"


class _CredentialSource:
    def __init__(self) -> None:
        self.calls = 0

    def get_api_key(self) -> str:
        self.calls += 1
        return "test-key-secret"


class _Factory:
    def __init__(self) -> None:
        self.create_calls = 0
        self.close_calls = 0
        self.arguments = None

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        self.create_calls += 1
        self.arguments = (api_key, max_retries, request_timeout_seconds)
        return object()

    def close_client(self, client: object) -> None:
        self.close_calls += 1


class _Responses:
    def create(self, **arguments: object) -> object:
        raise AssertionError("SDK operation must remain unused")


class _RawClient:
    def __init__(self, responses: object, *, fail_close: bool = False) -> None:
        self.responses = responses
        self.close_calls = 0
        self.fail_close = fail_close

    def close(self) -> None:
        self.close_calls += 1
        if self.fail_close:
            raise RuntimeError("SECRET_RAW_CLOSE_FAILURE")


class _OperationalFactory(_Factory):
    def __init__(
        self,
        *,
        responses: object | None = None,
        fail_create: bool = False,
        fail_close: bool = False,
    ) -> None:
        super().__init__()
        self.responses = responses if responses is not None else _Responses()
        self.fail_create = fail_create
        self.fail_close = fail_close
        self.clients: list[_RawClient] = []

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        self.create_calls += 1
        self.arguments = (api_key, max_retries, request_timeout_seconds)
        if self.fail_create:
            raise RuntimeError("SECRET_FACTORY_FAILURE")
        client = _RawClient(self.responses, fail_close=self.fail_close)
        self.clients.append(client)
        try:
            return _mint_factory_handoff(client)
        except Exception:
            client.close()
            raise


class _Lifecycle:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def close(self) -> None:
        self.calls += 1
        if self.fail:
            raise RuntimeError("secret lifecycle failure")


@pytest.mark.parametrize("value", (None, b"key", False, 1, "", " ", " key", "key "))
def test_explicit_credential_source_rejects_invalid_values(value: object) -> None:
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        _ExplicitOpenAICredentialSourceV2(value)
    assert raised.value.args == ("invalid OpenAI credential",)
    assert repr(value) not in str(raised.value)


def test_explicit_credential_source_is_immutable_and_repr_safe() -> None:
    key = "SECRET_EXPLICIT_API_KEY"
    source = _ExplicitOpenAICredentialSourceV2(key)
    assert source.get_api_key() == key
    assert key not in repr(source)
    assert key not in str(source)
    with pytest.raises(FrozenInstanceError):
        source._api_key = "replacement"
    with pytest.raises(FrozenInstanceError):
        del source._api_key


def test_explicit_credential_source_copy_identity_and_pickle_rejection() -> None:
    key = "SECRET_CONCRETE_OPENAI_KEY"
    source = _ExplicitOpenAICredentialSourceV2(key)
    assert copy.copy(source) is source
    assert copy.deepcopy(source) is source
    assert source.get_api_key() is key
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError) as raised:
            pickle.dumps(source, protocol=protocol)
        assert raised.value.args == ("OpenAI credential sources cannot be serialized",)
        assert key not in str(raised.value)


def test_environment_credential_source_reads_only_exact_variable_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    calls: list[str] = []
    values = iter(("first-valid-key", "second-valid-key"))

    def getenv(name: str) -> object:
        calls.append(name)
        return next(values)

    monkeypatch.setattr(production_module.os, "getenv", getenv)
    source = _EnvironmentOpenAICredentialSourceV2()
    assert source.get_api_key() == "first-valid-key"
    assert source.get_api_key() == "second-valid-key"
    assert calls == ["OPENAI_API_KEY", "OPENAI_API_KEY"]


@pytest.mark.parametrize(
    ("value", "message"),
    (
        (None, "OpenAI environment credential is unavailable"),
        ("", "invalid OpenAI credential"),
        (" ", "invalid OpenAI credential"),
        ("\t", "invalid OpenAI credential"),
        ("\n", "invalid OpenAI credential"),
        (" key", "invalid OpenAI credential"),
        ("key ", "invalid OpenAI credential"),
        (b"key", "invalid OpenAI credential"),
        (False, "invalid OpenAI credential"),
        (1, "invalid OpenAI credential"),
        (1.0, "invalid OpenAI credential"),
    ),
)
def test_environment_credential_source_rejects_missing_and_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
    message: str,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    calls = 0

    def getenv(name: str) -> object:
        nonlocal calls
        calls += 1
        assert name == "OPENAI_API_KEY"
        return value

    monkeypatch.setattr(production_module.os, "getenv", getenv)
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        _EnvironmentOpenAICredentialSourceV2().get_api_key()
    assert raised.value.args == (message,)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert calls == 1


def test_environment_credential_source_is_immutable_copy_safe_and_unserializable() -> (
    None
):
    source = _EnvironmentOpenAICredentialSourceV2()
    assert copy.copy(source) is source
    assert copy.deepcopy(source) is source
    assert repr(source) == "_EnvironmentOpenAICredentialSourceV2(<private>)"
    assert str(source) == repr(source)
    assert not hasattr(source, "__dict__")
    with pytest.raises(FrozenInstanceError):
        source.value = "key"
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError) as raised:
            pickle.dumps(source, protocol=protocol)
        assert raised.value.args == ("OpenAI credential sources cannot be serialized",)


def test_environment_credential_error_traceback_contains_only_safe_locals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    marker = " SECRET_ENVIRONMENT_KEY "
    source = _EnvironmentOpenAICredentialSourceV2()
    monkeypatch.setattr(production_module.os, "getenv", lambda name: marker)
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        source.get_api_key()
    error = raised.value
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("production.py"):
            values = tuple(traceback.tb_frame.f_locals.values())
            assert marker not in values
            assert not any(value is source for value in values)
            assert not any(value is production_module.os.environ for value in values)
        traceback = traceback.tb_next
    assert marker not in str(error)


def test_environment_credential_error_isolated_from_nested_active_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    class CallerError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self) -> str:
            type(self).repr_calls += 1
            raise AssertionError("caller repr executed")

        def __str__(self) -> str:
            type(self).str_calls += 1
            raise AssertionError("caller str executed")

    monkeypatch.setattr(production_module.os, "getenv", lambda name: None)
    outer = CallerError("SECRET_OUTER")
    inner = CallerError("SECRET_INNER")
    try:
        raise outer
    except CallerError:
        try:
            raise inner
        except CallerError:
            with pytest.raises(OpenAIRuntimeCredentialError) as raised:
                _EnvironmentOpenAICredentialSourceV2().get_api_key()
    error = raised.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert CallerError.repr_calls == CallerError.str_calls == 0


def test_environment_credential_failure_graph_retains_no_sensitive_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    marker = " SECRET_RECURSIVE_ENVIRONMENT_KEY "
    source = _EnvironmentOpenAICredentialSourceV2()
    environment = production_module.os.environ
    caller_error = RuntimeError("SECRET_CALLER_ERROR")
    monkeypatch.setattr(production_module.os, "getenv", lambda name: marker)
    try:
        raise caller_error
    except RuntimeError:
        with pytest.raises(OpenAIRuntimeCredentialError) as raised:
            source.get_api_key()

    roots: list[object] = [raised.value]
    traceback = raised.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("production.py"):
            roots.extend(traceback.tb_frame.f_locals.values())
        traceback = traceback.tb_next

    seen: set[int] = set()

    def visit(value: object) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        assert value is not source
        assert value is not environment
        assert value is not caller_error
        assert value != marker
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


def test_environment_credential_source_rejects_string_subclasses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    class StringSubclass(str):
        pass

    monkeypatch.setattr(
        production_module.os,
        "getenv",
        lambda name: StringSubclass("apparently-valid-key"),
    )
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        _EnvironmentOpenAICredentialSourceV2().get_api_key()
    assert raised.value.args == ("invalid OpenAI credential",)


@pytest.mark.parametrize(
    ("argument", "value"),
    (
        ("api_key", None),
        ("api_key", b"key"),
        ("api_key", False),
        ("api_key", 1),
        ("api_key", 1.0),
        ("api_key", ""),
        ("api_key", " "),
        ("api_key", "\t"),
        ("api_key", "\n"),
        ("api_key", " key"),
        ("api_key", "key "),
        ("max_retries", None),
        ("max_retries", False),
        ("max_retries", 0.0),
        ("max_retries", "0"),
        ("max_retries", -1),
        ("max_retries", 1),
        ("request_timeout_seconds", None),
        ("request_timeout_seconds", False),
        ("request_timeout_seconds", True),
        ("request_timeout_seconds", "1"),
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", -1),
        ("request_timeout_seconds", float("nan")),
        ("request_timeout_seconds", float("inf")),
        ("request_timeout_seconds", float("-inf")),
    ),
)
def test_official_factory_rejects_invalid_inputs_before_sdk_import(
    monkeypatch: pytest.MonkeyPatch,
    argument: str,
    value: object,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    import_calls = 0

    def forbidden_import(name: str) -> object:
        nonlocal import_calls
        import_calls += 1
        raise AssertionError(name)

    monkeypatch.setattr(production_module, "import_module", forbidden_import)
    arguments: dict[str, object] = {
        "api_key": "valid-key",
        "max_retries": 0,
        "request_timeout_seconds": 1.5,
    }
    arguments[argument] = value
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(**arguments)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert "valid-key" not in str(raised.value)
    assert import_calls == 0


@pytest.mark.parametrize(
    "timeout",
    (1, 30, 10**100, 10**1000, 10**10000),
    ids=("one", "thirty", "pow100", "pow1000", "pow10000"),
)
def test_arbitrary_precision_integer_timeout_reaches_constructor_exactly(
    monkeypatch: pytest.MonkeyPatch,
    timeout: int,
) -> None:
    calls: list[dict[str, object]] = []
    raw_client = _RawClient(_Responses())

    def constructor(**arguments: object) -> object:
        calls.append(arguments)
        return raw_client

    module = ModuleType("openai")
    module.OpenAI = constructor
    monkeypatch.setitem(sys.modules, "openai", module)
    config = OpenAIRuntimeConfigV2(
        model="gpt-contract-model", request_timeout_seconds=timeout
    )
    assert type(config.request_timeout_seconds) is int
    assert config.request_timeout_seconds == timeout
    _OfficialOpenAISDKFactoryV2().create_client(
        api_key="valid-key",
        max_retries=0,
        request_timeout_seconds=config.request_timeout_seconds,
    )
    assert calls == [{"api_key": "valid-key", "max_retries": 0, "timeout": timeout}]
    assert type(calls[0]["timeout"]) is int


@pytest.mark.parametrize("timeout", (0, -1, -(10**1000)))
def test_huge_nonpositive_integer_timeout_rejects_before_import(
    monkeypatch: pytest.MonkeyPatch,
    timeout: int,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    import_calls = 0

    def forbidden_import(name: str) -> object:
        nonlocal import_calls
        import_calls += 1
        raise AssertionError(name)

    monkeypatch.setattr(production_module, "import_module", forbidden_import)
    with pytest.raises(ValidationError):
        OpenAIRuntimeConfigV2(
            model="gpt-contract-model", request_timeout_seconds=timeout
        )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="valid-key",
            max_retries=0,
            request_timeout_seconds=timeout,
        )
    assert raised.value.args == ("invalid OpenAI SDK timeout",)
    assert raised.value.__context__ is None
    assert import_calls == 0


def test_copied_invalid_huge_negative_timeout_rejects_safely() -> None:
    config = OpenAIRuntimeConfigV2(
        model="gpt-contract-model", request_timeout_seconds=10**1000
    )
    copied = config.model_copy(update={"request_timeout_seconds": -(10**1000)})
    source = _CredentialSource()
    factory = _Factory()
    with pytest.raises(OpenAIRuntimeConfigurationError) as raised:
        OpenAIRuntimeComposerV2(copied, credential_source=source, sdk_factory=factory)
    assert raised.value.args == ("invalid OpenAI runtime config",)
    assert raised.value.__context__ is None
    assert source.calls == factory.create_calls == 0


@pytest.mark.parametrize("timeout", (0.000001, 0.5, 30.0, 30.25, 1e308))
def test_positive_finite_float_timeout_remains_valid(timeout: float) -> None:
    config = OpenAIRuntimeConfigV2(
        model="gpt-contract-model", request_timeout_seconds=timeout
    )
    assert type(config.request_timeout_seconds) is float
    assert config.request_timeout_seconds == timeout


def test_timeout_validation_never_coerces_hostile_numeric_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    class HostileNumber:
        float_calls = 0
        int_calls = 0
        bool_calls = 0
        comparison_calls = 0

        def __float__(self) -> float:
            type(self).float_calls += 1
            raise AssertionError("float coercion executed")

        def __int__(self) -> int:
            type(self).int_calls += 1
            raise AssertionError("integer coercion executed")

        def __bool__(self) -> bool:
            type(self).bool_calls += 1
            raise AssertionError("truthiness executed")

        def __gt__(self, other: object) -> bool:
            type(self).comparison_calls += 1
            raise AssertionError("comparison executed")

    class IntegerSubclass(int):
        pass

    class FloatSubclass(float):
        pass

    values = (
        None,
        False,
        True,
        "30",
        b"30",
        Decimal(30),
        Fraction(30, 1),
        IntegerSubclass(30),
        FloatSubclass(30.0),
        HostileNumber(),
    )
    import_calls = 0

    def forbidden_import(name: str) -> object:
        nonlocal import_calls
        import_calls += 1
        raise AssertionError(name)

    monkeypatch.setattr(production_module, "import_module", forbidden_import)
    for value in values:
        with pytest.raises(ValidationError):
            OpenAIRuntimeConfigV2(
                model="gpt-contract-model", request_timeout_seconds=value
            )
        with pytest.raises(OpenAIRuntimeDependencyError):
            _OfficialOpenAISDKFactoryV2().create_client(
                api_key="valid-key",
                max_retries=0,
                request_timeout_seconds=value,
            )
    assert import_calls == 0
    assert HostileNumber.float_calls == 0
    assert HostileNumber.int_calls == 0
    assert HostileNumber.bool_calls == 0
    assert HostileNumber.comparison_calls == 0


def test_huge_integer_timeout_propagates_through_concrete_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout = 10**1000
    calls: list[dict[str, object]] = []
    raw_client = _RawClient(_Responses())

    def constructor(**arguments: object) -> object:
        calls.append(arguments)
        return raw_client

    module = ModuleType("openai")
    module.OpenAI = constructor
    monkeypatch.setitem(sys.modules, "openai", module)
    source = _ExplicitOpenAICredentialSourceV2("valid-key")
    composer = OpenAIRuntimeComposerV2(
        OpenAIRuntimeConfigV2(
            model="gpt-contract-model", request_timeout_seconds=timeout
        ),
        credential_source=source,
        sdk_factory=_OfficialOpenAISDKFactoryV2(),
    )
    result = composer.compose()
    assert calls == [{"api_key": "valid-key", "max_retries": 0, "timeout": timeout}]
    assert type(calls[0]["timeout"]) is int
    assert raw_client.close_calls == 0
    result.close()
    assert raw_client.close_calls == 1


def test_official_factory_constructs_once_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor_calls: list[dict[str, object]] = []
    responses = _Responses()
    raw_client = _RawClient(responses)

    def openai_constructor(**arguments: object) -> object:
        constructor_calls.append(arguments)
        return raw_client

    fake_openai = ModuleType("openai")
    fake_openai.OpenAI = openai_constructor
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    import socket

    def forbid_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", forbid_network)
    factory = _OfficialOpenAISDKFactoryV2()
    handoff = factory.create_client(
        api_key="SECRET_EXPLICIT_API_KEY",
        max_retries=0,
        request_timeout_seconds=7.5,
    )
    assert constructor_calls == [
        {"api_key": "SECRET_EXPLICIT_API_KEY", "max_retries": 0, "timeout": 7.5}
    ]
    assert object.__getattribute__(handoff, "raw_client") is raw_client
    assert object.__getattribute__(handoff, "responses_resource") is responses
    assert object.__getattribute__(handoff, "close_receiver") is raw_client
    assert raw_client.close_calls == 0


def test_official_factory_missing_sdk_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    def fail_openai_import(name: str) -> object:
        assert name == "openai"
        raise ImportError("SECRET_IMPORT_FAILURE")

    monkeypatch.setattr(production_module, "import_module", fail_openai_import)
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="SECRET_EXPLICIT_API_KEY",
            max_retries=0,
            request_timeout_seconds=7.5,
        )
    assert raised.value.args == ("OpenAI SDK is unavailable",)
    assert raised.value.__context__ is None
    assert "SECRET" not in str(raised.value)


@pytest.mark.parametrize(
    ("failure", "message"),
    (
        (ModuleNotFoundError("SECRET_MISSING"), "OpenAI SDK is unavailable"),
        (ImportError("SECRET_IMPORT"), "OpenAI SDK is unavailable"),
        (RuntimeError("SECRET_BROKEN"), "OpenAI SDK could not be loaded"),
    ),
)
def test_official_factory_contains_sdk_import_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    message: str,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    def fail(name: str) -> object:
        assert name == "openai"
        raise failure

    monkeypatch.setattr(production_module, "import_module", fail)
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="SECRET_IMPORT_KEY",
            max_retries=0,
            request_timeout_seconds=1.0,
        )
    assert raised.value.args == (message,)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert "SECRET" not in str(raised.value)


@pytest.mark.parametrize("constructor", (None, object()))
def test_official_factory_rejects_incompatible_sdk(
    monkeypatch: pytest.MonkeyPatch,
    constructor: object,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    module = ModuleType("openai")
    module.OpenAI = constructor
    monkeypatch.setattr(production_module, "import_module", lambda name: module)
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="SECRET_INCOMPATIBLE_KEY",
            max_retries=0,
            request_timeout_seconds=1.0,
        )
    assert raised.value.args == ("OpenAI SDK is incompatible",)
    assert raised.value.__context__ is None


@pytest.mark.parametrize(
    "failure", (KeyboardInterrupt(), SystemExit(), GeneratorExit())
)
def test_official_factory_propagates_sdk_import_base_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.production as production_module

    def fail(name: str) -> object:
        raise failure

    monkeypatch.setattr(production_module, "import_module", fail)
    with pytest.raises(type(failure)) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="valid-key", max_retries=0, request_timeout_seconds=1.0
        )
    assert raised.value is failure


def test_official_constructor_failure_traceback_is_secret_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "SECRET_CONSTRUCTOR_KEY"
    raw_error = RuntimeError("SECRET_CONSTRUCTOR_FAILURE")

    def fail_constructor(**arguments: object) -> object:
        raise raw_error

    module = ModuleType("openai")
    module.OpenAI = fail_constructor
    monkeypatch.setitem(sys.modules, "openai", module)
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key=key, max_retries=0, request_timeout_seconds=2.5
        )
    error = raised.value
    assert error.args == ("OpenAI SDK construction failed",)
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("production.py"):
            values = tuple(traceback.tb_frame.f_locals.values())
            assert key not in values
            assert fail_constructor not in values
            assert raw_error not in values
        traceback = traceback.tb_next


def test_official_constructor_failure_isolated_from_nested_active_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CallerError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self) -> str:
            type(self).repr_calls += 1
            raise AssertionError("caller repr executed")

        def __str__(self) -> str:
            type(self).str_calls += 1
            raise AssertionError("caller str executed")

    def fail_constructor(**arguments: object) -> object:
        raise RuntimeError("SECRET_CONSTRUCTOR_FAILURE")

    module = ModuleType("openai")
    module.OpenAI = fail_constructor
    monkeypatch.setitem(sys.modules, "openai", module)
    outer = CallerError("SECRET_OUTER")
    inner = CallerError("SECRET_INNER")
    try:
        raise outer
    except CallerError:
        try:
            raise inner
        except CallerError:
            with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                _OfficialOpenAISDKFactoryV2().create_client(
                    api_key="SECRET_NESTED_KEY",
                    max_retries=0,
                    request_timeout_seconds=2.5,
                )
    error = raised.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert CallerError.repr_calls == CallerError.str_calls == 0


@pytest.mark.parametrize("fail_close", (False, True))
def test_official_factory_malformed_client_cleanup_precedence(
    monkeypatch: pytest.MonkeyPatch,
    fail_close: bool,
) -> None:
    raw_client = _RawClient(object(), fail_close=fail_close)
    module = ModuleType("openai")
    module.OpenAI = lambda **arguments: raw_client
    monkeypatch.setitem(sys.modules, "openai", module)
    expected = (
        OpenAIRuntimeLifecycleError if fail_close else OpenAIRuntimeDependencyError
    )
    with pytest.raises(expected) as raised:
        _OfficialOpenAISDKFactoryV2().create_client(
            api_key="valid-key", max_retries=0, request_timeout_seconds=1.0
        )
    expected_message = (
        "OpenAI SDK cleanup failed" if fail_close else "invalid OpenAI SDK client"
    )
    assert raised.value.args == (expected_message,)
    assert raw_client.close_calls == 1


def test_concrete_dependencies_compose_without_responses_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor_calls: list[dict[str, object]] = []
    responses = _Responses()
    raw_client = _RawClient(responses)

    def openai_constructor(**arguments: object) -> object:
        constructor_calls.append(arguments)
        return raw_client

    fake_openai = ModuleType("openai")
    fake_openai.OpenAI = openai_constructor
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    source = _ExplicitOpenAICredentialSourceV2("SECRET_EXPLICIT_API_KEY")
    factory = _OfficialOpenAISDKFactoryV2()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    result = composer.compose()
    assert constructor_calls == [
        {
            "api_key": "SECRET_EXPLICIT_API_KEY",
            "max_retries": 0,
            "timeout": 12.5,
        }
    ]
    assert result.closed is False
    assert raw_client.close_calls == 0
    result.close()
    assert raw_client.close_calls == 1


def _runtime_objects() -> tuple[OpenAISDKClientV2, OpenAIProviderExecutorV2]:
    sdk_client = OpenAISDKClientV2(OpenAISDKCapabilityV2(_Responses(), max_retries=0))
    executor = OpenAIProviderExecutorV2(
        client=sdk_client,
        config=OpenAIExecutionConfigV2(model="gpt-contract-model"),
    )
    return sdk_client, executor


def _composition(
    lifecycle: _Lifecycle | None = None,
) -> tuple[OpenAIRuntimeCompositionV2, _Lifecycle]:
    sdk_client, executor = _runtime_objects()
    resource = lifecycle or _Lifecycle()
    owner = _OpenAIRuntimeLifecycleOwnerV2(resource)
    return OpenAIRuntimeCompositionV2(sdk_client, executor, owner), resource


def _config() -> OpenAIRuntimeConfigV2:
    return OpenAIRuntimeConfigV2(
        model="gpt-contract-model", request_timeout_seconds=12.5
    )


def test_public_api_is_exact() -> None:
    assert public_api.__all__ == (
        "OpenAICredentialSourceV2",
        "OpenAIRuntimeComposerV2",
        "OpenAIRuntimeCompositionError",
        "OpenAIRuntimeCompositionV2",
        "OpenAIRuntimeConfigV2",
        "OpenAIRuntimeConfigurationError",
        "OpenAIRuntimeCredentialError",
        "OpenAIRuntimeDependencyError",
        "OpenAIRuntimeLifecycleError",
        "OpenAIRuntimeLifecycleV2",
        "OpenAISDKFactoryV2",
    )


def test_dependency_direction_and_capability_absence() -> None:
    forbidden_imports = {
        "asyncio",
        "dotenv",
        "httpx",
        "logging",
        "requests",
        "socket",
        "subprocess",
    }
    forbidden_text = (
        "os.environ",
        "OPENAI_KEY",
        "OPENAI_TOKEN",
        "OPENAI_SECRET",
        "load_dotenv",
        "provider_composition_v2",
        "register(",
    )
    for path in PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
        assert not imports & forbidden_imports
        assert all(value not in source for value in forbidden_text)

        environment_reads = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "getenv"
        ]
        if path.name == "production.py":
            assert len(environment_reads) == 1
            assert len(environment_reads[0].args) == 1
            assert isinstance(environment_reads[0].args[0], ast.Constant)
            assert environment_reads[0].args[0].value == "OPENAI_API_KEY"
        else:
            assert not environment_reads

    for relative in (
        "provider_v2",
        "provider_execution_v2",
        "provider_execution_openai_v2",
        "provider_execution_openai_sdk_v2",
    ):
        for path in (ROOT / "src" / "pastila_scout" / relative).glob("*.py"):
            assert "provider_runtime_openai_v2" not in path.read_text(encoding="utf-8")


def test_frozen_phase_seven_three_hashes_and_exports_are_unchanged() -> None:
    expected = {
        "__init__.py": "2e9dfe46cc32258336741fc63ab282e52dcb429c6f6991367e373549808e2f05",
        "client.py": "f42b5b30366a30755c4bba4a1bb9cd66e954cd63577d08f8053eae03ddaec889",
        "errors.py": "2b097697c5964fdab7ca30254186ad83658c241b6829ddfb46af49ae67f9dcea",
        "mapping.py": "a022a7c082ff2ea9025bcc437d2ac1412782736c38e95c59674a670bd910b510",
        "models.py": "af7a43b75215b0de3b3d30f530c3b2e9874789acea0b0bf128726f10ea87d8d4",
    }
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in FROZEN_PACKAGE.glob("*.py")
    } == expected
    import pastila_scout.provider_execution_openai_sdk_v2 as frozen_api

    assert len(frozen_api.__all__) == 10


@pytest.mark.parametrize(
    "value", (False, 0.0, "0", None, -1, 1, 2, type("I", (int,), {})(0))
)
def test_config_rejects_non_exact_retry_zero(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAIRuntimeConfigV2(
            model="gpt-contract-model", request_timeout_seconds=1, max_retries=value
        )


@pytest.mark.parametrize(
    "value", (False, True, 0, -1, 0.0, float("nan"), float("inf"), -float("inf"))
)
def test_config_rejects_invalid_timeout(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAIRuntimeConfigV2(model="gpt-contract-model", request_timeout_seconds=value)


def test_config_is_immutable_and_revalidates_copied_invalid_state() -> None:
    config = _config()
    with pytest.raises(ValidationError):
        config.request_timeout_seconds = 4  # type: ignore[misc]
    copied = config.model_copy(update={"max_retries": 1})
    with pytest.raises(OpenAIRuntimeConfigurationError):
        OpenAIRuntimeComposerV2(
            copied,
            credential_source=_CredentialSource(),
            sdk_factory=_Factory(),
        )


@pytest.mark.parametrize("value", (None, False, 1, "", " ", " model", "model "))
def test_runtime_model_is_exact_nonblank_and_unpadded(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAIRuntimeConfigV2(model=value, request_timeout_seconds=1)


def test_constructor_requires_dependencies_without_invoking_them() -> None:
    source = _CredentialSource()
    factory = _Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    assert source.calls == factory.create_calls == factory.close_calls == 0
    assert "test-key-secret" not in repr(composer)

    for source_value, factory_value in ((object(), factory), (source, object())):
        with pytest.raises(OpenAIRuntimeConfigurationError):
            OpenAIRuntimeComposerV2(
                _config(),
                credential_source=source_value,
                sdk_factory=factory_value,
            )


def test_descriptor_backed_dependencies_reject_without_execution() -> None:
    class Descriptor:
        calls = 0

        def __get__(self, instance, owner):
            Descriptor.calls += 1
            raise AssertionError("descriptor executed")

    class Source:
        get_api_key = Descriptor()

    class Factory:
        create_client = Descriptor()
        close_client = Descriptor()

    with pytest.raises(OpenAIRuntimeConfigurationError):
        OpenAIRuntimeComposerV2(
            _config(), credential_source=Source(), sdk_factory=_Factory()
        )
    with pytest.raises(OpenAIRuntimeConfigurationError):
        OpenAIRuntimeComposerV2(
            _config(), credential_source=_CredentialSource(), sdk_factory=Factory()
        )
    assert Descriptor.calls == 0


def test_factory_actual_shape_is_authoritative_and_async_is_rejected() -> None:
    class WrongFactory:
        def create_client(self) -> object:
            return object()

        def close_client(self, client: object) -> None:
            pass

    WrongFactory.create_client.__signature__ = Signature(  # type: ignore[attr-defined]
        (
            Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("kwargs", Parameter.VAR_KEYWORD),
        )
    )
    WrongFactory.create_client.__wrapped__ = _Factory.create_client  # type: ignore[attr-defined]
    with pytest.raises(OpenAIRuntimeConfigurationError):
        OpenAIRuntimeComposerV2(
            _config(), credential_source=_CredentialSource(), sdk_factory=WrongFactory()
        )

    class AsyncFactory:
        async def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return object()

        def close_client(self, client: object) -> None:
            pass

    with pytest.raises(OpenAIRuntimeConfigurationError):
        OpenAIRuntimeComposerV2(
            _config(), credential_source=_CredentialSource(), sdk_factory=AsyncFactory()
        )


@pytest.mark.parametrize("value", (None, False, 1, b"key", "", " ", " key", "key "))
def test_key_validation_is_strict_and_value_safe(value: object) -> None:
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        _validate_api_key(value)
    assert str(raised.value) == "invalid OpenAI credential"
    assert repr(value) not in str(raised.value)


def test_valid_key_probe_retains_nothing() -> None:
    assert _validate_api_key("test-key-secret") is None


def test_operational_composition_wires_exact_runtime_and_transfers_ownership() -> None:
    source = _CredentialSource()
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )

    result = composer.compose()

    assert type(result) is OpenAIRuntimeCompositionV2
    assert type(result.sdk_client) is OpenAISDKClientV2
    assert type(result.executor) is OpenAIProviderExecutorV2
    assert result.executor.client is result.sdk_client
    assert result.executor.config.model == "gpt-contract-model"
    assert source.calls == factory.create_calls == 1
    assert factory.arguments == ("test-key-secret", 0, 12.5)
    assert type(factory.arguments[1]) is int
    assert len(factory.clients) == 1
    raw_client = factory.clients[0]
    assert raw_client.close_calls == 0
    assert "test-key-secret" not in repr(result)
    assert "_RawClient" not in repr(result)
    assert result.close() is None
    assert result.closed is True
    assert raw_client.close_calls == 1
    assert result.close() is None
    assert raw_client.close_calls == 1


@pytest.mark.parametrize(
    "value",
    (None, False, 1, b"key", "", " ", " key", "key ", "key\n", "key\t"),
)
def test_operational_composer_rejects_invalid_credentials_before_factory(
    value: object,
) -> None:
    class Source:
        def __init__(self) -> None:
            self.calls = 0

        def get_api_key(self) -> object:
            self.calls += 1
            return value

    source = Source()
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeCredentialError) as raised:
        composer.compose()
    assert raised.value.args == ("invalid OpenAI credential",)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert source.calls == 1
    assert factory.create_calls == 0


def test_operational_source_and_factory_exceptions_are_fixed_and_isolated() -> None:
    class FailingSource(_CredentialSource):
        def get_api_key(self) -> str:
            self.calls += 1
            raise RuntimeError("SECRET_CREDENTIAL_FAILURE")

    source = FailingSource()
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeCredentialError) as credential_raised:
        composer.compose()
    assert credential_raised.value.args == ("OpenAI credential retrieval failed",)
    assert credential_raised.value.__context__ is None
    assert source.calls == 1
    assert factory.create_calls == 0

    source = _CredentialSource()
    factory = _OperationalFactory(fail_create=True)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as factory_raised:
        composer.compose()
    assert factory_raised.value.args == ("OpenAI SDK construction failed",)
    assert factory_raised.value.__context__ is None
    assert source.calls == factory.create_calls == 1
    assert factory.clients == []


def test_invalid_responses_fails_before_handoff_under_factory_ownership() -> None:
    factory = _OperationalFactory(responses=object())
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()
    assert raised.value.args == ("OpenAI SDK construction failed",)
    assert raised.value.__context__ is None
    assert len(factory.clients) == 1
    assert factory.clients[0].close_calls == 1


@pytest.mark.parametrize(
    "stage", ("capability", "sdk_client", "executor", "composition")
)
def test_each_post_factory_assembly_failure_rolls_back_once(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_module
    import pastila_scout.provider_execution_openai_v2 as execution_module
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    calls = 0

    def fail(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise RuntimeError(f"SECRET_{stage.upper()}_ASSEMBLY")

    if stage == "capability":
        monkeypatch.setattr(sdk_module, "OpenAISDKCapabilityV2", fail)
    elif stage == "sdk_client":
        monkeypatch.setattr(sdk_module, "OpenAISDKClientV2", fail)
    elif stage == "executor":
        monkeypatch.setattr(execution_module, "OpenAIProviderExecutorV2", fail)
    else:
        monkeypatch.setattr(composition_module, "OpenAIRuntimeCompositionV2", fail)

    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()
    assert raised.value.args == ("OpenAI runtime assembly failed",)
    assert raised.value.__context__ is None
    assert calls == 1
    assert factory.create_calls == 1
    assert factory.clients[0].close_calls == 1


def test_operational_rollback_failure_has_safe_lifecycle_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_module

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("SECRET_CAPABILITY_ASSEMBLY")

    monkeypatch.setattr(sdk_module, "OpenAISDKCapabilityV2", fail)
    factory = _OperationalFactory(fail_close=True)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        composer.compose()
    assert raised.value.args == ("OpenAI runtime rollback failed",)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert factory.clients[0].close_calls == 1


def test_factory_result_rejects_descriptor_close_without_execution() -> None:
    class Descriptor:
        calls = 0

        def __get__(self, instance, owner):
            type(self).calls += 1
            raise AssertionError("raw client descriptor executed")

    class InvalidRawClient:
        close = Descriptor()

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            self.create_calls += 1
            client = InvalidRawClient()
            try:
                return _mint_factory_handoff(client)
            except Exception:
                self.close_client(client)
                raise

    factory = Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()
    assert raised.value.args == ("OpenAI SDK construction failed",)
    assert Descriptor.calls == 0
    assert factory.create_calls == 1
    assert factory.close_calls == 1


def test_operational_repeated_compositions_are_independent() -> None:
    source = _CredentialSource()
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    first = composer.compose()
    second = composer.compose()
    assert first is not second
    assert first.sdk_client is not second.sdk_client
    assert source.calls == factory.create_calls == 2
    assert len(factory.clients) == 2
    first.close()
    second.close()
    assert [client.close_calls for client in factory.clients] == [1, 1]


def test_handoff_is_single_client_derived_and_not_directly_constructible() -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    raw_client = _RawClient(_Responses())
    handoff = _mint_factory_handoff(raw_client)
    assert object.__getattribute__(handoff, "raw_client") is raw_client
    assert (
        object.__getattribute__(handoff, "responses_resource") is raw_client.responses
    )
    assert object.__getattribute__(handoff, "close_receiver") is raw_client
    assert object.__getattribute__(handoff, "ownership_identity") == id(raw_client)
    assert copy.copy(handoff) is copy.deepcopy(handoff) is handoff
    with pytest.raises(TypeError):
        pickle.dumps(handoff)
    with pytest.raises(TypeError):
        composition_module._OpenAISDKFactoryResultV2(raw_client, _Responses())


def test_forged_mismatched_handoff_cannot_establish_runtime_authority() -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    raw_client = _RawClient(_Responses())
    valid = _mint_factory_handoff(raw_client)
    forged = object.__new__(composition_module._OpenAISDKFactoryResultV2)
    for name in (
        "raw_client",
        "close_function",
        "close_receiver",
        "ownership_identity",
        "client_reference",
    ):
        object.__setattr__(forged, name, object.__getattribute__(valid, name))
    object.__setattr__(forged, "responses_resource", _Responses())

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            self.create_calls += 1
            return forged

    factory = Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()
    assert raised.value.args == ("invalid OpenAI SDK factory result",)
    assert raw_client.close_calls == 0
    assert id(raw_client) not in _OWNERSHIP_TRACKER


def test_duplicate_live_handoff_is_rejected_without_closing_first_owner() -> None:
    raw_client = _RawClient(_Responses())
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            self.create_calls += 1
            return handoff

    factory = Factory()
    first_composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    second_composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    first = first_composer.compose()
    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        second_composer.compose()
    assert raised.value.args == ("OpenAI runtime client is already owned",)
    assert raised.value.__context__ is None
    assert raw_client.close_calls == 0
    assert id(raw_client) in _OWNERSHIP_TRACKER
    first.close()
    assert raw_client.close_calls == 1
    assert id(raw_client) not in _OWNERSHIP_TRACKER

    reused = second_composer.compose()
    reused.close()
    assert raw_client.close_calls == 2
    assert id(raw_client) not in _OWNERSHIP_TRACKER


def test_failed_public_close_establishes_terminal_non_reusable_ownership() -> None:
    raw_client = _RawClient(_Responses(), fail_close=True)
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return handoff

    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=Factory()
    )
    result = composer.compose()
    assert id(raw_client) in _OWNERSHIP_TRACKER
    with pytest.raises(OpenAIRuntimeLifecycleError):
        result.close()
    assert raw_client.close_calls == 1
    record = _OWNERSHIP_TRACKER[id(raw_client)]
    assert record.state is _OwnershipState.TERMINAL_FAILED
    assert record.client_reference() is raw_client

    for _ in range(3):
        with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
            composer.compose()
        assert raised.value.args == ("OpenAI runtime client cleanup previously failed",)
        assert raised.value.__context__ is None
        assert raised.value.__cause__ is None
        assert raised.value.__suppress_context__ is True
        assert _OWNERSHIP_TRACKER[id(raw_client)] is record
        assert raw_client.close_calls == 1
    assert result.close() is None
    assert raw_client.close_calls == 1


def test_terminal_failed_client_rejected_across_composers_and_new_handoff() -> None:
    raw_client = _RawClient(_Responses(), fail_close=True)
    handoffs = [_mint_factory_handoff(raw_client)]

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return handoffs[-1]

    factory = Factory()
    first_composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    second_composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    first = first_composer.compose()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        first.close()
    terminal = _OWNERSHIP_TRACKER[id(raw_client)]

    handoffs.append(_mint_factory_handoff(raw_client))
    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        second_composer.compose()
    assert raised.value.args == ("OpenAI runtime client cleanup previously failed",)
    assert raw_client.close_calls == 1
    assert _OWNERSHIP_TRACKER[id(raw_client)] is terminal


def test_terminal_failed_record_disappears_after_client_collection() -> None:
    raw_client = _RawClient(_Responses(), fail_close=True)
    identity = id(raw_client)
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def __init__(self, value: object) -> None:
            super().__init__()
            self.value = value

        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return self.value

    factory = Factory(handoff)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    result = composer.compose()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        result.close()
    assert _OWNERSHIP_TRACKER[identity].state is _OwnershipState.TERMINAL_FAILED

    del result
    del composer
    del factory
    del handoff
    del raw_client
    gc.collect()
    assert identity not in _OWNERSHIP_TRACKER


def test_tracker_never_dispatches_client_hash_or_equality() -> None:
    class HostileIdentityClient(_RawClient):
        hash_calls = 0
        equality_calls = 0

        def __hash__(self) -> int:
            type(self).hash_calls += 1
            raise AssertionError("raw-client hash executed")

        def __eq__(self, other: object) -> bool:
            type(self).equality_calls += 1
            raise AssertionError("raw-client equality executed")

    raw_client = HostileIdentityClient(_Responses(), fail_close=True)
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return handoff

    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=Factory()
    )
    result = composer.compose()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        result.close()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        composer.compose()
    assert HostileIdentityClient.hash_calls == 0
    assert HostileIdentityClient.equality_calls == 0
    assert raw_client.close_calls == 1


def test_stale_weakref_callback_cannot_remove_newer_record() -> None:
    first_client = _RawClient(_Responses())
    first_handoff = _mint_factory_handoff(first_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return first_handoff

    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=Factory()
    )
    result = composer.compose()
    identity = id(first_client)
    old_record = _OWNERSHIP_TRACKER[identity]
    callback = old_record.client_reference.__callback__
    assert callback is not None

    newer_client = _RawClient(_Responses())
    newer_handoff = _mint_factory_handoff(newer_client)
    newer_reference = object.__getattribute__(newer_handoff, "client_reference")
    newer_record = _OwnershipRecord(newer_reference, _OwnershipState.LIVE)
    _OWNERSHIP_TRACKER[identity] = newer_record
    callback(old_record.client_reference)
    assert _OWNERSHIP_TRACKER[identity] is newer_record

    _OWNERSHIP_TRACKER.pop(identity)
    result.close()
    assert first_client.close_calls == 1


def test_failed_rollback_is_terminal_and_reuse_skips_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pastila_scout.provider_execution_openai_sdk_v2 as sdk_module

    assembly_calls = 0

    def fail(*args: object, **kwargs: object) -> object:
        nonlocal assembly_calls
        assembly_calls += 1
        raise RuntimeError("SECRET_CAPABILITY_ASSEMBLY")

    monkeypatch.setattr(sdk_module, "OpenAISDKCapabilityV2", fail)
    raw_client = _RawClient(_Responses(), fail_close=True)
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            self.create_calls += 1
            return handoff

    factory = Factory()
    source = _CredentialSource()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeLifecycleError) as first:
        composer.compose()
    assert first.value.args == ("OpenAI runtime rollback failed",)
    assert raw_client.close_calls == assembly_calls == 1
    assert _OWNERSHIP_TRACKER[id(raw_client)].state is _OwnershipState.TERMINAL_FAILED

    with pytest.raises(OpenAIRuntimeLifecycleError) as second:
        composer.compose()
    assert second.value.args == ("OpenAI runtime client cleanup previously failed",)
    assert source.calls == factory.create_calls == 2
    assert assembly_calls == raw_client.close_calls == 1


def test_reentrant_failed_close_becomes_terminal_without_retry() -> None:
    class ReentrantRawClient(_RawClient):
        def __init__(self) -> None:
            super().__init__(_Responses(), fail_close=True)
            self.composer: OpenAIRuntimeComposerV2 | None = None
            self.nested_error: Exception | None = None

        def close(self) -> None:
            self.close_calls += 1
            assert self.composer is not None
            try:
                self.composer.compose()
            except Exception as error:  # noqa: BLE001 - verifier-owned probe
                self.nested_error = error
            raise RuntimeError("SECRET_REENTRANT_CLOSE")

    raw_client = ReentrantRawClient()
    handoff = _mint_factory_handoff(raw_client)

    class Factory(_OperationalFactory):
        def create_client(
            self,
            *,
            api_key: str,
            max_retries: int,
            request_timeout_seconds: float,
        ) -> object:
            return handoff

    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=Factory()
    )
    raw_client.composer = composer
    result = composer.compose()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        result.close()
    assert type(raw_client.nested_error) is OpenAIRuntimeLifecycleError
    assert raw_client.nested_error.args == ("OpenAI runtime client is already owned",)
    assert raw_client.close_calls == 1
    assert _OWNERSHIP_TRACKER[id(raw_client)].state is _OwnershipState.TERMINAL_FAILED
    with pytest.raises(OpenAIRuntimeLifecycleError):
        composer.compose()
    assert raw_client.close_calls == 1


def test_compose_rejects_malformed_factory_result_deterministically() -> None:
    source = _CredentialSource()
    factory = _Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(
        OpenAIRuntimeDependencyError,
        match="invalid OpenAI SDK factory result",
    ) as raised:
        composer.compose()
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert source.calls == factory.create_calls == 1
    assert factory.close_calls == 0


def test_composer_dependency_failure_traceback_contains_only_safe_outcome() -> None:
    class SecretCredentialSource(_CredentialSource):
        def __init__(self) -> None:
            super().__init__()
            self.marker = "SECRET_CREDENTIAL_SOURCE"
            self.api_key = "SECRET_API_KEY"

    class SecretFactory(_Factory):
        def __init__(self) -> None:
            super().__init__()
            self.marker = "SECRET_FACTORY_STATE"
            self.transport = "SECRET_TRANSPORT"

    source = SecretCredentialSource()
    factory = SecretFactory()
    config = _config()
    composer = OpenAIRuntimeComposerV2(
        config, credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()

    error = raised.value
    runtime_locals = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("composition.py"):
            runtime_locals.append(
                (traceback.tb_frame.f_code.co_name, dict(traceback.tb_frame.f_locals))
            )
        traceback = traceback.tb_next

    assert tuple(name for name, _ in runtime_locals) == (
        "compose",
        "_return_or_raise_composition",
    )
    assert tuple(tuple(values) for _, values in runtime_locals) == (
        ("outcome",),
        ("outcome", "error"),
    )
    forbidden = (composer, config, source, factory)
    for _, values in runtime_locals:
        assert not any(value is item for value in values.values() for item in forbidden)
        outcome = values["outcome"]
        assert type(outcome).__name__ == "_SafeCompositionFailure"
        assert outcome.category == "dependency"
        assert outcome.message == "invalid OpenAI SDK factory result"
        assert not hasattr(outcome, "__dict__")

    assert error.args == ("invalid OpenAI SDK factory result",)
    assert vars(error) == {}
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert source.calls == factory.create_calls == 1
    assert factory.close_calls == 0


def test_composer_dependency_error_graph_excludes_dependencies_and_secrets() -> None:
    markers = {
        "SECRET_CREDENTIAL_SOURCE",
        "SECRET_FACTORY_STATE",
        "SECRET_API_KEY",
        "SECRET_TRANSPORT",
    }

    class SecretCredentialSource(_CredentialSource):
        marker = "SECRET_CREDENTIAL_SOURCE"

        def __init__(self) -> None:
            super().__init__()
            self.api_key = "SECRET_API_KEY"

    class SecretFactory(_Factory):
        marker = "SECRET_FACTORY_STATE"
        transport = "SECRET_TRANSPORT"

    source = SecretCredentialSource()
    factory = SecretFactory()
    config = _config()
    composer = OpenAIRuntimeComposerV2(
        config, credential_source=source, sdk_factory=factory
    )
    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()

    error = raised.value
    roots: list[object] = [
        error.args,
        vars(error),
        error.__context__,
        error.__cause__,
    ]
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("composition.py"):
            roots.append(dict(traceback.tb_frame.f_locals))
        traceback = traceback.tb_next

    seen: set[int] = set()
    discovered: list[object] = []

    def visit(value: object) -> None:
        if value is None or id(value) in seen:
            return
        seen.add(id(value))
        discovered.append(value)
        if isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)
        elif isinstance(value, CellType):
            try:
                visit(value.cell_contents)
            except ValueError:
                pass
        else:
            slots = getattr(type(value), "__slots__", ())
            if isinstance(slots, str):
                slots = (slots,)
            for slot in slots:
                if slot not in {"__dict__", "__weakref__"} and hasattr(value, slot):
                    visit(getattr(value, slot))
            dictionary = getattr(value, "__dict__", None)
            if type(dictionary) is dict:
                visit(dictionary)

    for root in roots:
        visit(root)

    forbidden = (composer, config, source, factory)
    assert not any(value is item for value in discovered for item in forbidden)
    assert not markers.intersection(value for value in discovered if type(value) is str)


def test_dependency_error_isolated_from_nested_active_exception_graph() -> None:
    class HostileError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self) -> str:
            type(self).repr_calls += 1
            raise AssertionError("caller exception repr executed")

        def __str__(self) -> str:
            type(self).str_calls += 1
            raise AssertionError("caller exception str executed")

    source = _CredentialSource()
    source.marker = "SECRET_CREDENTIAL_SOURCE"
    factory = _Factory()
    factory.marker = "SECRET_FACTORY_STATE"
    config = _config()
    composer = OpenAIRuntimeComposerV2(
        config, credential_source=source, sdk_factory=factory
    )
    outer = HostileError("SECRET_OUTER")
    outer.headers = {"Authorization": "SECRET_API_KEY"}
    outer.transport = object()
    inner = HostileError("SECRET_INNER")
    inner.__cause__ = HostileError("SECRET_NESTED_CAUSE")

    try:
        raise outer
    except HostileError:
        try:
            raise inner
        except HostileError:
            with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                composer.compose()

    error = raised.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert error.args == ("invalid OpenAI SDK factory result",)
    assert vars(error) == {}
    runtime_locals = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("composition.py"):
            runtime_locals.append(
                (traceback.tb_frame.f_code.co_name, dict(traceback.tb_frame.f_locals))
            )
        traceback = traceback.tb_next
    assert tuple(name for name, _ in runtime_locals) == (
        "compose",
        "_return_or_raise_composition",
    )
    assert tuple(tuple(values) for _, values in runtime_locals) == (
        ("outcome",),
        ("outcome", "error"),
    )
    forbidden = (outer, inner, inner.__cause__, composer, config, source, factory)
    assert not any(
        value is item
        for _, values in runtime_locals
        for value in values.values()
        for item in forbidden
    )
    assert HostileError.repr_calls == HostileError.str_calls == 0
    assert source.calls == factory.create_calls == 1
    assert factory.close_calls == 0


def test_dependency_failures_are_fresh_across_mixed_exception_contexts() -> None:
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=_Factory()
    )
    errors = []
    for active in (False, True, False, True):
        if active:
            try:
                raise RuntimeError("SECRET_ACTIVE_DEPENDENCY")
            except RuntimeError:
                with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                    composer.compose()
        else:
            with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                composer.compose()
        errors.append(raised.value)

    assert len({id(error) for error in errors}) == len(errors)
    assert all(error.__context__ is None for error in errors)
    assert all(error.__cause__ is None for error in errors)
    assert all(error.__suppress_context__ is True for error in errors)
    assert {error.args for error in errors} == {("invalid OpenAI SDK factory result",)}


def test_mixed_dependency_and_lifecycle_failures_have_no_stale_context() -> None:
    source = _CredentialSource()
    factory = _Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    public_errors = []
    for index in range(6):
        try:
            raise RuntimeError(f"SECRET_MIXED_CONTEXT_{index}")
        except RuntimeError:
            if index % 2 == 0:
                with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                    composer.compose()
            else:
                lifecycle = _Lifecycle(fail=True)
                result, _ = _composition(lifecycle)
                with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
                    result.close()
                assert lifecycle.calls == 1
                assert result.closed is True
        public_errors.append(raised.value)

    assert len({id(error) for error in public_errors}) == len(public_errors)
    assert all(error.__context__ is None for error in public_errors)
    assert all(error.__cause__ is None for error in public_errors)
    assert all(error.__suppress_context__ is True for error in public_errors)
    assert source.calls == factory.create_calls == 3
    assert factory.close_calls == 0


def test_repeated_composer_failures_leave_no_dependency_module_state() -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    dependencies = []
    markers = []
    for index in range(20):
        marker = f"SECRET_COMPOSER_GLOBAL_{index}"
        markers.append(marker)
        source = _CredentialSource()
        source.marker = marker
        factory = _Factory()
        factory.marker = marker
        composer = OpenAIRuntimeComposerV2(
            _config(), credential_source=source, sdk_factory=factory
        )
        dependencies.extend((source, factory, composer))
        for _ in range(3):
            with pytest.raises(OpenAIRuntimeDependencyError) as raised:
                composer.compose()
            assert raised.value.args == ("invalid OpenAI SDK factory result",)
        assert source.calls == factory.create_calls == 3
        assert factory.close_calls == 0

    del composer, factory, source, raised
    gc.collect()
    production_globals = {
        key: value
        for key, value in vars(composition_module).items()
        if not key.startswith("__")
    }
    assert not any(
        value is dependency
        for value in production_globals.values()
        for dependency in dependencies
    )
    assert not any(
        value in markers for value in production_globals.values() if type(value) is str
    )


def test_lifecycle_contract_documents_idempotence_and_atomicity() -> None:
    interface = (PACKAGE / "interface.py").read_text(encoding="utf-8")
    docs = (
        ROOT
        / "docs"
        / "editorial-script-composer"
        / "Phase7_4_OpenAIRuntimeComposition.md"
    ).read_text(encoding="utf-8")
    assert "Idempotent owner" in interface
    assert "idempotent" in docs
    assert "partial" in docs


def test_composition_result_accepts_only_exact_coherent_runtime_objects() -> None:
    result, lifecycle = _composition()

    assert type(result.sdk_client) is OpenAISDKClientV2
    assert type(result.executor) is OpenAIProviderExecutorV2
    assert result.executor.client is result.sdk_client
    assert result.closed is False
    assert lifecycle.calls == 0


@pytest.mark.parametrize("value", (None, object(), _Responses(), lambda: None))
def test_composition_result_rejects_wrong_sdk_client(value: object) -> None:
    _, executor = _runtime_objects()
    owner = _OpenAIRuntimeLifecycleOwnerV2(_Lifecycle())
    with pytest.raises(OpenAIRuntimeConfigurationError, match="SDK client"):
        OpenAIRuntimeCompositionV2(value, executor, owner)


def test_secret_bearing_wrong_client_is_rejected_without_repr_execution() -> None:
    class SecretClient:
        repr_calls = 0

        def __repr__(self) -> str:
            SecretClient.repr_calls += 1
            return "api-key-secret"

    _, executor = _runtime_objects()
    owner = _OpenAIRuntimeLifecycleOwnerV2(_Lifecycle())
    with pytest.raises(OpenAIRuntimeConfigurationError) as raised:
        OpenAIRuntimeCompositionV2(SecretClient(), executor, owner)
    assert str(raised.value) == "invalid OpenAI runtime SDK client"
    assert SecretClient.repr_calls == 0
    assert "secret" not in str(raised.value)


@pytest.mark.parametrize("value", (None, object(), lambda: None))
def test_composition_result_rejects_wrong_executor(value: object) -> None:
    sdk_client, _ = _runtime_objects()
    owner = _OpenAIRuntimeLifecycleOwnerV2(_Lifecycle())
    with pytest.raises(OpenAIRuntimeConfigurationError, match="executor"):
        OpenAIRuntimeCompositionV2(sdk_client, value, owner)


def test_composition_result_rejects_subclasses_and_inconsistent_pair() -> None:
    class SDKSubclass(OpenAISDKClientV2):
        pass

    _, executor = _runtime_objects()
    owner = _OpenAIRuntimeLifecycleOwnerV2(_Lifecycle())
    forged_sdk = object.__new__(SDKSubclass)
    with pytest.raises(OpenAIRuntimeConfigurationError, match="SDK client"):
        OpenAIRuntimeCompositionV2(forged_sdk, executor, owner)

    other_sdk, _ = _runtime_objects()
    with pytest.raises(OpenAIRuntimeConfigurationError, match="inconsistent"):
        OpenAIRuntimeCompositionV2(other_sdk, executor, owner)


@pytest.mark.parametrize("value", (None, object(), _Lifecycle()))
def test_composition_result_rejects_unowned_lifecycle(value: object) -> None:
    sdk_client, executor = _runtime_objects()
    with pytest.raises(OpenAIRuntimeLifecycleError, match="invalid"):
        OpenAIRuntimeCompositionV2(sdk_client, executor, value)


def test_composition_repr_is_fixed_and_does_not_call_nested_repr() -> None:
    result, _ = _composition()
    sdk_calls = 0
    executor_calls = 0
    original_sdk_repr = OpenAISDKClientV2.__repr__
    original_executor_repr = OpenAIProviderExecutorV2.__repr__

    def sdk_repr(self: object) -> str:
        nonlocal sdk_calls
        sdk_calls += 1
        return "api-key-secret"

    def executor_repr(self: object) -> str:
        nonlocal executor_calls
        executor_calls += 1
        return "transport-secret"

    OpenAISDKClientV2.__repr__ = sdk_repr
    OpenAIProviderExecutorV2.__repr__ = executor_repr
    try:
        representation = repr(result)
    finally:
        OpenAISDKClientV2.__repr__ = original_sdk_repr
        OpenAIProviderExecutorV2.__repr__ = original_executor_repr

    assert representation == (
        "OpenAIRuntimeCompositionV2(sdk_client=<OpenAISDKClientV2>, "
        "executor=<OpenAIProviderExecutorV2>, closed=False)"
    )
    assert sdk_calls == executor_calls == 0
    assert "secret" not in representation
    assert "0x" not in representation


def test_composition_close_is_idempotent_and_returns_none() -> None:
    result, lifecycle = _composition()

    for _ in range(20):
        assert result.close() is None

    assert lifecycle.calls == 1
    assert result.closed is True
    assert repr(result).endswith("closed=True)")


def test_lifecycle_failure_is_safe_closed_and_not_retried() -> None:
    result, lifecycle = _composition(_Lifecycle(fail=True))

    with pytest.raises(
        OpenAIRuntimeLifecycleError, match="OpenAI runtime cleanup failed"
    ) as raised:
        result.close()
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert "secret" not in str(raised.value)
    assert lifecycle.calls == 1
    assert result.closed is True

    for _ in range(5):
        assert result.close() is None
    assert lifecycle.calls == 1


def test_lifecycle_owner_validation_executes_no_descriptor_or_lookup_code() -> None:
    class Descriptor:
        calls = 0

        def __get__(self, instance, owner):
            Descriptor.calls += 1
            raise AssertionError("descriptor executed")

    class DescriptorLifecycle:
        close = Descriptor()

    class LookupLifecycle:
        calls = 0

        def __getattribute__(self, name: str) -> object:
            type(self).calls += 1
            return object.__getattribute__(self, name)

        def close(self) -> None:
            raise AssertionError("close executed")

    with pytest.raises(OpenAIRuntimeLifecycleError):
        _OpenAIRuntimeLifecycleOwnerV2(DescriptorLifecycle())
    lookup = LookupLifecycle()
    with pytest.raises(OpenAIRuntimeLifecycleError):
        _OpenAIRuntimeLifecycleOwnerV2(lookup)
    assert Descriptor.calls == LookupLifecycle.calls == 0


def test_lifecycle_owner_rejects_wrong_async_and_forged_shapes() -> None:
    class Wrong:
        def close(self, extra: object) -> None:
            raise AssertionError("body executed")

    Wrong.close.__signature__ = Signature(  # type: ignore[attr-defined]
        (Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),)
    )
    Wrong.close.__wrapped__ = _Lifecycle.close  # type: ignore[attr-defined]
    with pytest.raises(OpenAIRuntimeLifecycleError):
        _OpenAIRuntimeLifecycleOwnerV2(Wrong())

    class Async:
        async def close(self) -> None:
            raise AssertionError("body executed")

    with pytest.raises(OpenAIRuntimeLifecycleError):
        _OpenAIRuntimeLifecycleOwnerV2(Async())


def test_lifecycle_actual_shape_remains_authoritative_with_forged_metadata() -> None:
    class Compatible:
        def close(self) -> None:
            pass

    Compatible.close.__signature__ = Signature(())  # type: ignore[attr-defined]
    Compatible.close.__wrapped__ = object()  # type: ignore[attr-defined]
    owner = _OpenAIRuntimeLifecycleOwnerV2(Compatible())
    assert owner.close() is None
    assert owner.closed is True


def test_lifecycle_rejects_property_class_static_and_callable_attribute() -> None:
    calls = 0

    def raising_property(self: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("property executed")

    class PropertyLifecycle:
        close = property(raising_property)

    class ClassLifecycle:
        @classmethod
        def close(cls) -> None:
            raise AssertionError("body executed")

    class StaticLifecycle:
        @staticmethod
        def close() -> None:
            raise AssertionError("body executed")

    class CallableLifecycle:
        def __init__(self) -> None:
            self.close = lambda: pytest.fail("callable attribute executed")

    for value in (
        PropertyLifecycle(),
        ClassLifecycle(),
        StaticLifecycle(),
        CallableLifecycle(),
    ):
        with pytest.raises(OpenAIRuntimeLifecycleError):
            _OpenAIRuntimeLifecycleOwnerV2(value)
    assert calls == 0


def test_supported_copy_paths_preserve_valid_ownership() -> None:
    result, lifecycle = _composition()
    shallow = copy.copy(result)
    deep = copy.deepcopy(result)

    assert shallow is result
    assert deep is result
    assert copy.deepcopy(deep) is result
    assert "secret" not in repr(shallow)
    assert "secret" not in repr(deep)
    with pytest.raises(TypeError):
        replace(result, sdk_client=object())

    shallow.close()
    deep.close()
    result.close()
    assert lifecycle.calls == 1


def test_copy_after_success_and_failure_preserves_identity_and_state() -> None:
    success, success_lifecycle = _composition()
    success.close()
    assert copy.copy(success) is success
    assert copy.deepcopy(success) is success
    assert success.closed is True
    assert success_lifecycle.calls == 1

    failed, failed_lifecycle = _composition(_Lifecycle(fail=True))
    with pytest.raises(OpenAIRuntimeLifecycleError):
        failed.close()
    assert copy.copy(failed) is failed
    assert copy.deepcopy(failed) is failed
    assert failed.close() is None
    assert failed_lifecycle.calls == 1


def test_private_owner_copy_policy_preserves_identity() -> None:
    lifecycle = _Lifecycle()
    owner = _OpenAIRuntimeLifecycleOwnerV2(lifecycle)

    assert copy.copy(owner) is owner
    assert copy.deepcopy(owner) is owner
    owner.close()
    copy.deepcopy(owner).close()
    assert lifecycle.calls == 1


@pytest.mark.parametrize(
    "order",
    ((0, 1, 2), (2, 0, 1), (1, 2, 0)),
)
def test_all_copy_alias_close_permutations_are_globally_once(order) -> None:
    result, lifecycle = _composition()
    aliases = (result, copy.copy(result), copy.deepcopy(result))
    assert aliases == (result, result, result)

    for index in order:
        assert aliases[index].close() is None

    assert lifecycle.calls == 1
    assert result.closed is True


def test_copy_hooks_do_not_reach_nested_runtime_state() -> None:
    class CopyObservedLifecycle(_Lifecycle):
        copy_calls = 0

        def __copy__(self):
            type(self).copy_calls += 1
            raise AssertionError("nested copy executed")

        def __deepcopy__(self, memo):
            type(self).copy_calls += 1
            raise AssertionError("nested deepcopy executed")

    lifecycle = CopyObservedLifecycle()
    result, _ = _composition(lifecycle)
    owner = object.__getattribute__(result, "_lifecycle")

    assert copy.copy(result) is copy.deepcopy(result) is result
    assert copy.copy(owner) is copy.deepcopy(owner) is owner
    assert CopyObservedLifecycle.copy_calls == 0


def test_replacement_and_serialization_are_deterministically_unsupported() -> None:
    result, _ = _composition()
    owner = object.__getattribute__(result, "_lifecycle")

    with pytest.raises(TypeError):
        replace(result)
    with pytest.raises(TypeError, match="not serializable"):
        pickle.dumps(result)
    with pytest.raises(TypeError, match="not serializable"):
        pickle.dumps(owner)


def test_cleanup_failure_traceback_contains_only_safe_adapter_locals() -> None:
    class SecretLifecycle:
        def __init__(self) -> None:
            self.api_key = "SECRET_CREDENTIAL"
            self.transport = "SECRET_TRANSPORT"
            self.calls = 0

        def close(self) -> None:
            self.calls += 1
            raise RuntimeError("SECRET_CLEANUP_FAILURE")

    result, lifecycle = _composition(SecretLifecycle())
    owner = object.__getattribute__(result, "_lifecycle")
    sdk_client = result.sdk_client
    executor = result.executor

    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        result.close()

    error = raised.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert error.args == ("OpenAI runtime cleanup failed",)
    assert vars(error) == {}
    traceback = error.__traceback__
    adapter_locals = []
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("models.py"):
            adapter_locals.append(dict(traceback.tb_frame.f_locals))
        traceback = traceback.tb_next
    assert adapter_locals
    forbidden = (result, owner, sdk_client, executor, lifecycle)
    for local_values in adapter_locals:
        assert not any(
            value is item for value in local_values.values() for item in forbidden
        )
        rendered = repr(local_values)
        assert "SECRET_" not in rendered
        assert "receiver" not in local_values
        assert "function" not in local_values


def test_lifecycle_error_isolated_from_nested_active_exception_graph() -> None:
    class HostileError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self) -> str:
            type(self).repr_calls += 1
            raise AssertionError("caller exception repr executed")

        def __str__(self) -> str:
            type(self).str_calls += 1
            raise AssertionError("caller exception str executed")

    class SecretFailingLifecycle(_Lifecycle):
        def __init__(self) -> None:
            super().__init__()
            self.marker = "SECRET_CLEANUP_RECEIVER"
            self.transport = "SECRET_TRANSPORT"

        def close(self) -> None:
            self.calls += 1
            raise RuntimeError("SECRET_RAW_CLEANUP")

    lifecycle = SecretFailingLifecycle()
    result, _ = _composition(lifecycle)
    owner = object.__getattribute__(result, "_lifecycle")
    outer = HostileError("SECRET_OUTER")
    outer.body = "SECRET_BODY"
    inner = HostileError("SECRET_INNER")
    inner.__context__ = HostileError("SECRET_NESTED_CONTEXT")

    try:
        raise outer
    except HostileError:
        try:
            raise inner
        except HostileError:
            with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
                result.close()

    error = raised.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert error.args == ("OpenAI runtime cleanup failed",)
    assert vars(error) == {}
    runtime_locals = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("models.py"):
            runtime_locals.append(
                (traceback.tb_frame.f_code.co_name, dict(traceback.tb_frame.f_locals))
            )
        traceback = traceback.tb_next
    assert tuple(name for name, _ in runtime_locals) == (
        "close",
        "_return_or_raise_cleanup",
    )
    assert tuple(tuple(values) for _, values in runtime_locals) == (
        ("outcome",),
        ("outcome", "error"),
    )
    forbidden = (outer, inner, inner.__context__, result, owner, lifecycle)
    assert not any(
        value is item
        for _, values in runtime_locals
        for value in values.values()
        for item in forbidden
    )
    assert lifecycle.calls == 1
    assert result.closed is True
    assert result.close() is None
    assert lifecycle.calls == 1
    assert HostileError.repr_calls == HostileError.str_calls == 0


def test_reentrant_alias_close_is_once_even_when_callback_fails() -> None:
    class ReentrantLifecycle:
        def __init__(self) -> None:
            self.result = None
            self.calls = 0

        def close(self) -> None:
            self.calls += 1
            assert self.result is not None
            copy.deepcopy(self.result).close()
            raise RuntimeError("SECRET_REENTRANT_FAILURE")

    lifecycle = ReentrantLifecycle()
    result, _ = _composition(lifecycle)
    lifecycle.result = result
    alias = copy.deepcopy(result)

    with pytest.raises(OpenAIRuntimeLifecycleError):
        alias.close()
    assert lifecycle.calls == 1
    assert result.closed is True
    assert result.close() is None
    assert lifecycle.calls == 1


def test_repeated_failures_leave_no_runtime_state_in_module_globals() -> None:
    import pastila_scout.provider_runtime_openai_v2.models as models_module

    markers = []
    for index in range(20):
        marker = f"SECRET_GLOBAL_{index}"
        markers.append(marker)

        class FailingLifecycle:
            def __init__(self, value: str) -> None:
                self.marker = value

            def close(self) -> None:
                raise RuntimeError(self.marker)

        result, _ = _composition(FailingLifecycle(marker))
        with pytest.raises(OpenAIRuntimeLifecycleError):
            result.close()

    rendered = repr(
        {
            key: value
            for key, value in vars(models_module).items()
            if not key.startswith("__")
        }
    )
    assert not any(marker in rendered for marker in markers)


def test_composer_is_immutable() -> None:
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=_Factory()
    )
    with pytest.raises(FrozenInstanceError):
        composer.config = _config()  # type: ignore[misc]


def _registered_runtime_composition(
    *, fail_close: bool = False
) -> tuple[OpenAIRuntimeCompositionV2, _RawClient]:
    factory = _OperationalFactory(fail_close=fail_close)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )
    composition = composer.compose()
    return composition, factory.clients[0]


def test_runtime_registration_authority_is_unique_sealed_and_safe() -> None:
    first, first_raw = _registered_runtime_composition()
    second, second_raw = _registered_runtime_composition()
    first_generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(first_raw)]
    second_generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(second_raw)]
    assert first_generation is not second_generation
    first_record = _RUNTIME_REGISTRATIONS[first_generation]
    authority = first_record.authority
    assert type(authority) is _RuntimeRegistrationAuthority
    assert copy.copy(authority) is authority
    assert copy.deepcopy(authority) is authority
    assert repr(authority) == "_RuntimeRegistrationAuthority(<private>)"
    assert not hasattr(authority, "__dict__")
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(
            TypeError, match="^runtime registration authorities cannot be serialized$"
        ):
            pickle.dumps(authority, protocol=protocol)
    first.close()
    second.close()


def test_runtime_registration_claim_is_atomic_and_single_use() -> None:
    composition, raw = _registered_runtime_composition()
    sdk_client = object.__getattribute__(composition, "sdk_client")
    claim = _claim_runtime_registration_authority(
        composition=composition, expected_sdk_client=sdk_client
    )
    assert type(claim) is _RuntimeValidatedClaim
    assert copy.copy(claim) is claim
    assert copy.deepcopy(claim) is claim
    assert repr(claim) == "_RuntimeValidatedClaim(<private>)"
    assert (
        _claim_runtime_registration_authority(
            composition=composition, expected_sdk_client=sdk_client
        )
        is None
    )
    composition.close()
    assert id(raw) not in _RUNTIME_GENERATION_BY_TARGET_ID


def test_runtime_registration_rejects_coordinated_weakref_substitution() -> None:
    composition, raw = _registered_runtime_composition()
    lifecycle = object.__getattribute__(composition, "_lifecycle")
    lease = object.__getattribute__(lifecycle, "_transition_receiver")
    generation = object.__getattribute__(lease, "generation")
    compatibility = _OWNERSHIP_TRACKER[id(raw)]
    replacement = ref(raw)
    original_lease_reference = object.__getattribute__(lease, "client_reference")
    original_record_reference = object.__getattribute__(
        compatibility, "client_reference"
    )
    object.__setattr__(lease, "client_reference", replacement)
    object.__setattr__(compatibility, "client_reference", replacement)
    try:
        assert (
            _claim_runtime_registration_authority(
                composition=composition,
                expected_sdk_client=object.__getattribute__(composition, "sdk_client"),
            )
            is None
        )
        assert _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)] is generation
    finally:
        object.__setattr__(lease, "client_reference", original_lease_reference)
        object.__setattr__(compatibility, "client_reference", original_record_reference)
    composition.close()


def test_runtime_registration_terminal_failure_is_generation_owned() -> None:
    composition, raw = _registered_runtime_composition(fail_close=True)
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    with pytest.raises(OpenAIRuntimeLifecycleError):
        composition.close()
    registration = _RUNTIME_REGISTRATIONS[generation]
    assert registration.state is _OwnershipState.TERMINAL_FAILED
    assert _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)] is generation


@pytest.mark.parametrize(
    "mutation",
    ("lease_generation", "owner", "authority_generation", "callback", "weakref"),
)
def test_runtime_registration_claim_rejects_foreign_provenance(
    mutation: str,
) -> None:
    composition, _raw = _registered_runtime_composition()
    lifecycle = object.__getattribute__(composition, "_lifecycle")
    lease = object.__getattribute__(lifecycle, "_transition_receiver")
    generation = object.__getattribute__(lease, "generation")
    authority = _RUNTIME_REGISTRATIONS[generation].authority
    if mutation == "lease_generation":
        target, field, replacement = lease, "generation", object()
    elif mutation == "owner":
        target, field, replacement = authority, "_owner", object()
    elif mutation == "authority_generation":
        target, field, replacement = authority, "_generation", object()
    elif mutation == "callback":
        target, field, replacement = authority, "_callback", lambda _: None
    else:
        target, field = authority, "_target_reference"
        replacement = ref(_RawClient(_Responses()))
    original = object.__getattribute__(target, field)
    object.__setattr__(target, field, replacement)
    try:
        assert (
            _claim_runtime_registration_authority(
                composition=composition,
                expected_sdk_client=object.__getattribute__(composition, "sdk_client"),
            )
            is None
        )
    finally:
        object.__setattr__(target, field, original)
    composition.close()


def _assert_no_runtime_registration(raw: object) -> None:
    assert id(raw) not in _RUNTIME_GENERATION_BY_TARGET_ID
    assert id(raw) not in _OWNERSHIP_TRACKER
    assert all(
        record.authority._target_reference() is not raw
        for record in _RUNTIME_REGISTRATIONS.values()
    )


@pytest.mark.parametrize("stage", ("lease", "lifecycle"))
def test_post_registration_construction_failure_rolls_back_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    calls = 0

    def fail(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise RuntimeError(f"SECRET_{stage.upper()}_CONSTRUCTION_FAILURE")

    if stage == "lease":
        monkeypatch.setattr(composition_module, "_OwnershipLease", fail)
    else:
        monkeypatch.setattr(
            _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
        )
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(OpenAIRuntimeDependencyError) as raised:
        composer.compose()

    raw = factory.clients[0]
    assert raised.value.args == ("OpenAI runtime assembly failed",)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert calls == raw.close_calls == 1
    _assert_no_runtime_registration(raw)


def test_post_registration_construction_rollback_failure_is_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("SECRET_LIFECYCLE_CONSTRUCTION_FAILURE")

    monkeypatch.setattr(
        _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
    )
    factory = _OperationalFactory(fail_close=True)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        composer.compose()

    raw = factory.clients[0]
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    assert raised.value.args == ("OpenAI runtime rollback failed",)
    assert raw.close_calls == 1
    assert _RUNTIME_REGISTRATIONS[generation].state is _OwnershipState.TERMINAL_FAILED
    assert _OWNERSHIP_TRACKER[id(raw)].state is _OwnershipState.TERMINAL_FAILED


@pytest.mark.parametrize(
    "exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_lifecycle_construction_baseexception_rolls_back_then_propagates(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
) -> None:
    marker = exception_type("verifier construction interrupt")

    def fail(*args: object, **kwargs: object) -> object:
        raise marker

    monkeypatch.setattr(
        _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
    )
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(exception_type) as raised:
        composer.compose()

    raw = factory.clients[0]
    assert raised.value is marker
    assert raw.close_calls == 1
    _assert_no_runtime_registration(raw)


def test_lifecycle_construction_baseexception_yields_to_rollback_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = KeyboardInterrupt("verifier construction interrupt")

    def fail(*args: object, **kwargs: object) -> object:
        raise marker

    monkeypatch.setattr(
        _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
    )
    factory = _OperationalFactory(fail_close=True)
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(OpenAIRuntimeLifecycleError) as raised:
        composer.compose()

    raw = factory.clients[0]
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    assert raised.value.args == ("OpenAI runtime rollback failed",)
    assert raised.value.__context__ is None
    assert raw.close_calls == 1
    assert _RUNTIME_REGISTRATIONS[generation].state is _OwnershipState.TERMINAL_FAILED


@pytest.mark.parametrize(
    "exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_composition_construction_baseexception_rolls_back_then_propagates(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
) -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    marker = exception_type("verifier composition interrupt")

    def fail(*args: object, **kwargs: object) -> object:
        raise marker

    monkeypatch.setattr(composition_module, "OpenAIRuntimeCompositionV2", fail)
    factory = _OperationalFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(exception_type) as raised:
        composer.compose()

    raw = factory.clients[0]
    assert raised.value is marker
    assert raw.close_calls == 1
    _assert_no_runtime_registration(raw)


@pytest.mark.parametrize(
    "exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_rollback_baseexception_establishes_terminal_no_retry_tombstone(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
) -> None:
    marker = exception_type("verifier rollback interrupt")

    class InterruptingRaw(_RawClient):
        def close(self) -> None:
            self.close_calls += 1
            raise marker

    class InterruptingFactory(_OperationalFactory):
        def create_client(self, **kwargs: object) -> object:
            self.create_calls += 1
            raw = InterruptingRaw(self.responses)
            self.clients.append(raw)
            return _mint_factory_handoff(raw)

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("SECRET_LIFECYCLE_CONSTRUCTION_FAILURE")

    monkeypatch.setattr(
        _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
    )
    factory = InterruptingFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(exception_type) as raised:
        composer.compose()

    raw = factory.clients[0]
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    registration = _RUNTIME_REGISTRATIONS[generation]
    compatibility = _OWNERSHIP_TRACKER[id(raw)]
    assert raised.value is marker
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert raw.close_calls == 1
    assert registration.state is _OwnershipState.TERMINAL_FAILED
    assert compatibility.state is _OwnershipState.TERMINAL_FAILED
    assert _claim_factory_handoff(_mint_factory_handoff(raw)).category == "lifecycle"
    assert raw.close_calls == 1


def test_terminal_transition_is_idempotent_and_rejects_foreign_authority() -> None:
    composition, raw = _registered_runtime_composition()
    lifecycle = object.__getattribute__(composition, "_lifecycle")
    lease = object.__getattribute__(lifecycle, "_transition_receiver")
    generation = object.__getattribute__(lease, "generation")
    reference = object.__getattribute__(lease, "client_reference")
    authority = _RUNTIME_REGISTRATIONS[generation].authority

    assert _terminalize_exact_registration(id(raw), generation, reference)
    assert _terminalize_exact_registration(id(raw), generation, reference)
    assert _RUNTIME_REGISTRATIONS[generation].authority is authority
    assert _RUNTIME_REGISTRATIONS[generation].state is _OwnershipState.TERMINAL_FAILED
    assert not _terminalize_exact_registration(id(raw), object(), reference)
    assert _RUNTIME_REGISTRATIONS[generation].authority is authority
    assert raw.close_calls == 0


def test_terminal_tombstone_is_removed_only_after_target_collection() -> None:
    import weakref

    composition, raw = _registered_runtime_composition()
    lifecycle = object.__getattribute__(composition, "_lifecycle")
    lease = object.__getattribute__(lifecycle, "_transition_receiver")
    generation = object.__getattribute__(lease, "generation")
    reference = object.__getattribute__(lease, "client_reference")
    callback = reference.__callback__
    identity = id(raw)
    raw_reference = weakref.ref(raw)

    assert _terminalize_exact_registration(identity, generation, reference)
    callback(reference)
    assert generation in _RUNTIME_REGISTRATIONS
    object.__setattr__(lifecycle, "_receiver", None)
    object.__setattr__(lifecycle, "_transition_receiver", None)
    object.__setattr__(composition, "_lifecycle", None)
    del lease
    del lifecycle
    del composition
    del raw
    gc.collect()

    assert raw_reference() is None
    assert generation not in _RUNTIME_REGISTRATIONS
    assert identity not in _RUNTIME_GENERATION_BY_TARGET_ID
    assert identity not in _OWNERSHIP_TRACKER


@pytest.mark.parametrize("stage", ("lease", "lifecycle", "composition"))
@pytest.mark.parametrize(
    "cleanup_exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_each_construction_stage_cleanup_baseexception_is_terminal_and_no_retry(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    cleanup_exception_type: type[BaseException],
) -> None:
    import pastila_scout.provider_runtime_openai_v2.composition as composition_module

    cleanup_marker = cleanup_exception_type(f"{stage} cleanup interrupt")

    class InterruptingRaw(_RawClient):
        def close(self) -> None:
            self.close_calls += 1
            raise cleanup_marker

    class InterruptingFactory(_OperationalFactory):
        def create_client(self, **kwargs: object) -> object:
            self.create_calls += 1
            raw = InterruptingRaw(self.responses)
            self.clients.append(raw)
            return _mint_factory_handoff(raw)

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError(f"SECRET_{stage.upper()}_CONSTRUCTION_FAILURE")

    if stage == "lease":
        monkeypatch.setattr(composition_module, "_OwnershipLease", fail)
    elif stage == "lifecycle":
        monkeypatch.setattr(
            _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
        )
    else:
        monkeypatch.setattr(composition_module, "OpenAIRuntimeCompositionV2", fail)
    factory = InterruptingFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(cleanup_exception_type) as raised:
        composer.compose()

    raw = factory.clients[0]
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    assert raised.value is cleanup_marker
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert _RUNTIME_REGISTRATIONS[generation].state is _OwnershipState.TERMINAL_FAILED
    assert _OWNERSHIP_TRACKER[id(raw)].state is _OwnershipState.TERMINAL_FAILED
    assert _claim_factory_handoff(_mint_factory_handoff(raw)).category == "lifecycle"
    assert raw.close_calls == 1


@pytest.mark.parametrize(
    "construction_exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
@pytest.mark.parametrize(
    "cleanup_exception_type", (KeyboardInterrupt, SystemExit, GeneratorExit)
)
def test_cleanup_baseexception_precedes_construction_baseexception_without_context(
    monkeypatch: pytest.MonkeyPatch,
    construction_exception_type: type[BaseException],
    cleanup_exception_type: type[BaseException],
) -> None:
    construction_marker = construction_exception_type("construction interrupt")
    cleanup_marker = cleanup_exception_type("cleanup interrupt")

    class InterruptingRaw(_RawClient):
        def close(self) -> None:
            self.close_calls += 1
            raise cleanup_marker

    class InterruptingFactory(_OperationalFactory):
        def create_client(self, **kwargs: object) -> object:
            self.create_calls += 1
            raw = InterruptingRaw(self.responses)
            self.clients.append(raw)
            return _mint_factory_handoff(raw)

    def fail(*args: object, **kwargs: object) -> object:
        raise construction_marker

    monkeypatch.setattr(
        _OpenAIRuntimeLifecycleOwnerV2, "_from_pinned", classmethod(fail)
    )
    factory = InterruptingFactory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=_CredentialSource(), sdk_factory=factory
    )

    with pytest.raises(cleanup_exception_type) as raised:
        composer.compose()

    raw = factory.clients[0]
    generation = _RUNTIME_GENERATION_BY_TARGET_ID[id(raw)]
    assert raised.value is cleanup_marker
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert _RUNTIME_REGISTRATIONS[generation].state is _OwnershipState.TERMINAL_FAILED
    assert raw.close_calls == 1
