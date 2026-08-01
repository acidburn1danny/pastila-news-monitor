from __future__ import annotations

import ast
import copy
import gc
import hashlib
import pickle
from dataclasses import FrozenInstanceError, replace
from inspect import Parameter, Signature
from pathlib import Path
from types import CellType

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
from pastila_scout.provider_runtime_openai_v2.composition import _validate_api_key
from pastila_scout.provider_runtime_openai_v2.models import (
    _OpenAIRuntimeLifecycleOwnerV2,
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

    def create_client(self, *, api_key: str, max_retries: int) -> object:
        self.create_calls += 1
        return object()

    def close_client(self, client: object) -> None:
        self.close_calls += 1


class _Responses:
    def create(self, **arguments: object) -> object:
        raise AssertionError("SDK operation must remain unused")


class _Lifecycle:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def close(self) -> None:
        self.calls += 1
        if self.fail:
            raise RuntimeError("secret lifecycle failure")


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
    return OpenAIRuntimeConfigV2(request_timeout_seconds=12.5)


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
        "OPENAI_API_KEY",
        "os.getenv",
        "os.environ",
        "OpenAI(",
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
        OpenAIRuntimeConfigV2(request_timeout_seconds=1, max_retries=value)


@pytest.mark.parametrize(
    "value", (False, True, 0, -1, 0.0, float("nan"), float("inf"), -float("inf"))
)
def test_config_rejects_invalid_timeout(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAIRuntimeConfigV2(request_timeout_seconds=value)


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
        async def create_client(self, *, api_key: str, max_retries: int) -> object:
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


def test_compose_is_deterministically_non_operational() -> None:
    source = _CredentialSource()
    factory = _Factory()
    composer = OpenAIRuntimeComposerV2(
        _config(), credential_source=source, sdk_factory=factory
    )
    with pytest.raises(
        OpenAIRuntimeDependencyError,
        match="OpenAI runtime composition is not implemented",
    ) as raised:
        composer.compose()
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert source.calls == factory.create_calls == factory.close_calls == 0


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
        "_return_or_raise_dependency",
    )
    assert tuple(tuple(values) for _, values in runtime_locals) == (
        ("outcome",),
        ("outcome", "error"),
    )
    forbidden = (composer, config, source, factory)
    for _, values in runtime_locals:
        assert not any(value is item for value in values.values() for item in forbidden)
        outcome = values["outcome"]
        assert type(outcome).__name__ == "_SafeDependencyFailureOutcome"
        assert outcome.category == "dependency"
        assert outcome.message == "OpenAI runtime composition is not implemented"
        assert not hasattr(outcome, "__dict__")

    assert error.args == ("OpenAI runtime composition is not implemented",)
    assert vars(error) == {}
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert source.calls == factory.create_calls == factory.close_calls == 0


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
    assert error.args == ("OpenAI runtime composition is not implemented",)
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
        "_return_or_raise_dependency",
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
    assert source.calls == factory.create_calls == factory.close_calls == 0


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
    assert {error.args for error in errors} == {
        ("OpenAI runtime composition is not implemented",)
    }


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
    assert source.calls == factory.create_calls == factory.close_calls == 0


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
            assert raised.value.args == (
                "OpenAI runtime composition is not implemented",
            )
        assert source.calls == factory.create_calls == factory.close_calls == 0

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
