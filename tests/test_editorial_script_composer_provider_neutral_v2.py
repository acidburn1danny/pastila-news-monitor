from __future__ import annotations

import ast
import json
import subprocess
import sys
from abc import abstractmethod
from dataclasses import FrozenInstanceError
from functools import cached_property, wraps
from inspect import Parameter, Signature
from pathlib import Path
from typing import Any

import pytest

from pastila_scout.provider_v2 import (
    DuplicateProviderRegistrationError,
    InvalidProviderAdapterError,
    InvalidProviderDescriptorError,
    ProviderAdapter,
    ProviderCapabilityUnavailableError,
    ProviderCapabilityV2,
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderOutputInputV2,
    ProviderRegistry,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    ProviderV2ValidationIssue,
    UnknownProviderError,
    build_provider_descriptor,
    build_provider_request_envelope,
    build_provider_result_envelope,
    descriptor_fingerprint,
    descriptor_identity,
    request_envelope_fingerprint,
    request_envelope_identity,
    request_message_fingerprint,
    request_message_identity,
    request_unit_fingerprint,
    request_unit_identity,
    result_envelope_fingerprint,
    result_envelope_identity,
    result_unit_fingerprint,
    result_unit_identity,
    validate_provider_descriptor,
    validate_provider_request_envelope,
    validate_provider_result_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pastila_scout"
CORE = SRC / "provider_v2"
ADAPTERS = SRC / "provider_adapters_v2"
ZERO = "0" * 64
TEST_IDENTITY = f"scout:test-artifact:{ZERO}"


def _intent(text: str = "Scrie secțiunea") -> ProviderRequestIntentV2:
    return ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:test",
        execution_plan_identity=TEST_IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:test",
        draft_fingerprint=ZERO,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference="execution-request:test",
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(role="generation", content=text, ordinal=0),
                ),
            ),
        ),
    )


def _descriptor(provider_id: str = "test-provider"):
    return build_provider_descriptor(
        provider_id=provider_id,
        display_name="Test Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=TEST_IDENTITY,
    )


def _projection(text: str = "Text românesc generat") -> ProviderResultProjectionV2:
    return ProviderResultProjectionV2(
        status=ProviderResultStatusV2.SUCCESS,
        outputs=(
            ProviderOutputInputV2(
                source_request_reference="execution-request:test",
                ordinal=0,
                generated_text=text,
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            ),
        ),
    )


def _materialize(function, annotations: dict[str, object]):
    """Publish test-owned static annotations without executing deferred bytecode."""

    function.__annotations__ = annotations
    assert object.__getattribute__(function, "__annotate__") is None
    return function


def _clean_import(module: str) -> tuple[str, ...]:
    code = (
        "import importlib,json,sys;"
        f"importlib.import_module({module!r});"
        "print(json.dumps(sorted(k for k in sys.modules "
        "if k.startswith('pastila_scout.'))))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(json.loads(completed.stdout))


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return tuple(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ) + tuple(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )


def test_clean_generic_import_loads_no_provider_implementation() -> None:
    modules = _clean_import("pastila_scout.provider_v2")

    assert not any("provider_adapters_v2" in item for item in modules)
    assert not any("script_composer.openai" in item for item in modules)
    assert not any("script_composer.provider_" in item for item in modules)


@pytest.mark.parametrize("provider", ["openai", "claude", "gemini", "ollama"])
def test_clean_adapter_import_loads_only_selected_adapter(provider: str) -> None:
    modules = _clean_import(f"pastila_scout.provider_adapters_v2.{provider}")
    loaded = {
        item.rsplit(".", 1)[-1]
        for item in modules
        if item.startswith("pastila_scout.provider_adapters_v2.")
        and item.rsplit(".", 1)[-1] in {"openai", "claude", "gemini", "ollama"}
    }

    assert loaded == {provider}


def test_composition_root_intentionally_loads_all_providers() -> None:
    modules = _clean_import("pastila_scout.provider_composition_v2")

    assert all(
        f"pastila_scout.provider_adapters_v2.{provider}" in modules
        for provider in ("openai", "claude", "gemini", "ollama")
    )


def test_generic_core_has_no_provider_or_adapter_imports() -> None:
    imports = tuple(item for path in CORE.glob("*.py") for item in _imports(path))

    assert not any("provider_adapters_v2" in item for item in imports)
    assert not any("script_composer" in item for item in imports)
    assert not any(
        provider in item.lower()
        for item in imports
        for provider in ("openai", "claude", "gemini", "ollama")
    )


def test_adapters_never_import_one_another() -> None:
    for provider in ("openai", "claude", "gemini", "ollama"):
        imports = _imports(ADAPTERS / f"{provider}.py")
        assert not any(
            f".{other}" in item or item.endswith(other)
            for item in imports
            for other in ("openai", "claude", "gemini", "ollama")
            if other != provider
        )


def test_descriptor_builder_and_validator_are_authoritative() -> None:
    descriptor = _descriptor()

    assert descriptor.identity == descriptor_identity(descriptor)
    assert descriptor.fingerprint == descriptor_fingerprint(descriptor)
    assert validate_provider_descriptor(descriptor) == ()


@pytest.mark.parametrize("field", ["identity", "fingerprint"])
def test_descriptor_validator_rejects_invalid_seals(field: str) -> None:
    descriptor = _descriptor().model_copy(
        update={field: ZERO if field == "fingerprint" else TEST_IDENTITY}
    )

    assert validate_provider_descriptor(descriptor)


def test_request_builder_and_validator_reconstruct_exact_authority() -> None:
    intent, descriptor = _intent(), _descriptor()
    first = build_provider_request_envelope(intent, descriptor)
    second = build_provider_request_envelope(intent, descriptor)

    assert first == second
    assert validate_provider_request_envelope(first, intent, descriptor) == ()
    assert first.identity == request_envelope_identity(first)
    assert first.fingerprint == request_envelope_fingerprint(first)
    unit, message = first.request_units[0], first.request_units[0].messages[0]
    assert unit.identity == request_unit_identity(unit)
    assert unit.fingerprint == request_unit_fingerprint(unit)
    assert message.identity == request_message_identity(message)
    assert message.fingerprint == request_message_fingerprint(message)


def test_request_validator_rejects_resealed_semantic_substitution() -> None:
    intent, descriptor = _intent(), _descriptor()
    request = build_provider_request_envelope(intent, descriptor)
    changed = build_provider_request_envelope(_intent("Conținut străin"), descriptor)

    assert validate_provider_request_envelope(changed, intent, descriptor)
    assert changed.identity == request_envelope_identity(changed)
    assert changed.fingerprint == request_envelope_fingerprint(changed)
    assert changed != request


def test_result_builder_exposes_complete_neutral_composer_output() -> None:
    intent, descriptor, projection = _intent(), _descriptor(), _projection()
    request = build_provider_request_envelope(intent, descriptor)
    result = build_provider_result_envelope(request, intent, descriptor, projection)

    assert (
        validate_provider_result_envelope(
            result, request, intent, descriptor, projection
        )
        == ()
    )
    assert result.outputs[0].generated_text == "Text românesc generat"
    assert result.outputs[0].finish_reason is ProviderFinishReasonV2.COMPLETED
    assert result.identity == result_envelope_identity(result)
    assert result.fingerprint == result_envelope_fingerprint(result)
    assert result.outputs[0].identity == result_unit_identity(result.outputs[0])
    assert result.outputs[0].fingerprint == result_unit_fingerprint(result.outputs[0])


def test_result_validator_rejects_resealed_semantic_substitution() -> None:
    intent, descriptor = _intent(), _descriptor()
    request = build_provider_request_envelope(intent, descriptor)
    authority = _projection()
    changed_projection = _projection("Text străin")
    changed = build_provider_result_envelope(
        request, intent, descriptor, changed_projection
    )

    assert validate_provider_result_envelope(
        changed, request, intent, descriptor, authority
    )
    assert changed.identity == result_envelope_identity(changed)
    assert changed.fingerprint == result_envelope_fingerprint(changed)


def test_envelopes_contain_no_provider_specific_fields_or_dtos() -> None:
    from pastila_scout.provider_v2 import (
        ProviderRequestEnvelopeV2,
        ProviderResultEnvelopeV2,
    )

    fields = set(ProviderRequestEnvelopeV2.model_fields) | set(
        ProviderResultEnvelopeV2.model_fields
    )
    assert not fields & {"provider_id", "openai_request", "openai_result"}
    assert not any(
        provider in field
        for field in fields
        for provider in ("openai", "claude", "gemini", "ollama")
    )


def test_registry_is_authoritative_deterministic_and_immutable() -> None:
    from pastila_scout.provider_composition_v2 import build_provider_registry

    registry = build_provider_registry()

    assert registry.provider_ids == ("claude", "gemini", "ollama", "openai")
    assert registry.resolve("openai").provider_id == "openai"
    with pytest.raises(FrozenInstanceError):
        registry._adapters = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        registry._adapters["other"] = registry.resolve("openai")  # type: ignore[index]


def test_registry_rejects_duplicate_and_unknown_providers() -> None:
    from pastila_scout.provider_adapters_v2.claude import ClaudeProviderAdapter

    with pytest.raises(DuplicateProviderRegistrationError):
        ProviderRegistry((ClaudeProviderAdapter(), ClaudeProviderAdapter()))
    with pytest.raises(UnknownProviderError):
        ProviderRegistry((ClaudeProviderAdapter(),)).resolve("unknown")


def test_registry_rejects_nonconforming_adapter() -> None:
    class NotAnAdapter:
        provider_id = "invalid"
        descriptor = _descriptor("invalid")

    with pytest.raises(InvalidProviderAdapterError):
        ProviderRegistry((NotAnAdapter(),))  # type: ignore[arg-type]


def test_registry_rejects_noncallable_lifecycle_members() -> None:
    from pastila_scout.provider_adapters_v2.claude import ClaudeProviderAdapter

    class BrokenLifecycleAdapter(ClaudeProviderAdapter):
        execute = "not-callable"  # type: ignore[assignment]

    with pytest.raises(InvalidProviderAdapterError):
        ProviderRegistry((BrokenLifecycleAdapter(),))


def test_registry_rejects_invalid_descriptor_seal() -> None:
    from pastila_scout.provider_adapters_v2.claude import ClaudeProviderAdapter

    class InvalidDescriptorAdapter(ClaudeProviderAdapter):
        descriptor = ClaudeProviderAdapter.descriptor.model_copy(
            update={"fingerprint": ZERO}
        )

    with pytest.raises(InvalidProviderDescriptorError):
        ProviderRegistry((InvalidDescriptorAdapter(),))


def test_registry_rejects_cross_provider_ownership() -> None:
    from pastila_scout.provider_adapters_v2.claude import ClaudeProviderAdapter

    class CrossOwnedAdapter(ClaudeProviderAdapter):
        provider_id = "foreign"

    with pytest.raises(InvalidProviderAdapterError):
        ProviderRegistry((CrossOwnedAdapter(),))


@pytest.mark.parametrize("provider", ["claude", "gemini", "ollama"])
def test_placeholders_implement_complete_nonexecuting_lifecycle(provider: str) -> None:
    module = __import__(
        f"pastila_scout.provider_adapters_v2.{provider}",
        fromlist=[f"{provider.title()}ProviderAdapter"],
    )
    adapter = getattr(module, f"{provider.title()}ProviderAdapter")()
    intent = _intent()
    request = adapter.construct_request(intent)

    assert isinstance(adapter, ProviderAdapter)
    assert adapter.validate_request(request, intent) == ()
    with pytest.raises(ProviderCapabilityUnavailableError):
        adapter.execute(request)


def test_openai_adapter_complete_lifecycle_and_exact_v1_delegation() -> None:
    from pastila_scout.editor.script_composer.extracted_result_validation import (
        build_openai_extracted_execution_result,
    )
    from pastila_scout.editor.script_composer.provider_mapping_validation import (
        build_draft_provider_request_plan,
    )
    from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter

    adapter = OpenAIProviderAdapter()
    intent, projection = _intent(), _projection()
    request = adapter.construct_request(intent)
    extracted = adapter.extract_response(projection)
    result = adapter.project_result(request, intent, extracted)

    assert isinstance(adapter, ProviderAdapter)
    assert adapter.validate_request(request, intent) == ()
    assert adapter.validate_result(result, request, intent, projection) == ()
    assert adapter.v1_request_builder is build_draft_provider_request_plan
    assert (
        adapter.v1_extracted_result_builder is build_openai_extracted_execution_result
    )
    with pytest.raises(ProviderCapabilityUnavailableError):
        adapter.execute(request)


def test_future_provider_requires_only_adapter_and_composition_registration() -> None:
    from pastila_scout.provider_adapters_v2.base import (
        ProviderAdapterBase,
        adapter_identity,
        placeholder_descriptor,
    )

    mistral_adapter_identity = adapter_identity("mistral")

    class MistralProviderAdapter(ProviderAdapterBase):
        provider_id = "mistral"
        adapter_identity = mistral_adapter_identity
        descriptor = placeholder_descriptor(provider_id, "Mistral")

    registry = ProviderRegistry((MistralProviderAdapter(),))

    assert registry.resolve("mistral").provider_id == "mistral"


def test_frozen_script_composer_root_does_not_export_v2() -> None:
    root_init = (SRC / "editor" / "script_composer" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "provider_v2" not in root_init
    assert "provider_adapters_v2" not in root_init


def test_registry_accepts_valid_bound_and_unannotated_lifecycle_methods() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class ValidUnannotatedAdapter(ProviderAdapterBase):
        provider_id = "valid-unannotated"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request):
            del request
            raise ProviderCapabilityUnavailableError("unavailable")

    registry = ProviderRegistry((ValidUnannotatedAdapter(),))

    assert registry.resolve("valid-unannotated").provider_id == "valid-unannotated"


def test_registry_rejects_callable_missing_authoritative_argument() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class MissingArgumentAdapter(ProviderAdapterBase):
        provider_id = "missing-argument"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self):
            raise ProviderCapabilityUnavailableError("unavailable")

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method execute: callable signature",
    ):
        ProviderRegistry((MissingArgumentAdapter(),))


def test_registry_rejects_additional_required_lifecycle_argument() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class ExtraArgumentAdapter(ProviderAdapterBase):
        provider_id = "extra-argument"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request, extra):
            del request, extra
            raise ProviderCapabilityUnavailableError("unavailable")

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method execute: callable signature",
    ):
        ProviderRegistry((ExtraArgumentAdapter(),))


def test_registry_rejects_additional_required_keyword_only_argument() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class KeywordOnlyAdapter(ProviderAdapterBase):
        provider_id = "keyword-only"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request, *, required):
            del request, required
            raise ProviderCapabilityUnavailableError("unavailable")

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method execute: callable signature",
    ):
        ProviderRegistry((KeywordOnlyAdapter(),))


def test_registry_rejects_incompatible_lifecycle_return_annotation() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class WrongReturnAdapter(ProviderAdapterBase):
        provider_id = "wrong-return"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request: ProviderRequestEnvelopeV2) -> str:
            del request
            return "wrong"

    _materialize(
        WrongReturnAdapter.execute,
        {"request": ProviderRequestEnvelopeV2, "return": str},
    )

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method execute: return annotation",
    ):
        ProviderRegistry((WrongReturnAdapter(),))


def test_registry_rejects_incompatible_lifecycle_parameter_annotation() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class WrongParameterAdapter(ProviderAdapterBase):
        provider_id = "wrong-parameter"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, differently_named: str) -> ProviderResultProjectionV2:
            del differently_named
            return _projection()

    _materialize(
        WrongParameterAdapter.execute,
        {"differently_named": str, "return": ProviderResultProjectionV2},
    )

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method execute: parameter 0 annotation",
    ):
        ProviderRegistry((WrongParameterAdapter(),))


def test_registry_rejects_semantic_lifecycle_impostor() -> None:
    class SemanticImpostor:
        provider_id = "semantic-impostor"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def construct_request(self):
            return "wrong"

        def validate_request(self):
            return "wrong"

        def execute(self):
            return "wrong"

        def extract_response(self):
            return "wrong"

        def project_result(self):
            return "wrong"

        def validate_result(self):
            return "wrong"

    with pytest.raises(
        InvalidProviderAdapterError,
        match="incompatible lifecycle method construct_request: callable signature",
    ):
        ProviderRegistry((SemanticImpostor(),))  # type: ignore[arg-type]


def test_registry_static_inspection_never_executes_property_lifecycle() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"count": 0}

    class PropertyAdapter(ProviderAdapterBase):
        provider_id = "property-adapter"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @property
        def execute(self):
            effects["count"] += 1
            return lambda request: None

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((PropertyAdapter(),))
        messages.append(str(captured.value))

    assert effects["count"] == 0
    assert (
        messages
        == ["incompatible lifecycle method execute: non-method lifecycle member"] * 2
    )


def test_registry_does_not_execute_raising_property_lifecycle() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"count": 0}

    class RaisingPropertyAdapter(ProviderAdapterBase):
        provider_id = "raising-property"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @property
        def execute(self):
            effects["count"] += 1
            raise RuntimeError("must not execute")

    with pytest.raises(
        InvalidProviderAdapterError, match="non-method lifecycle member"
    ):
        ProviderRegistry((RaisingPropertyAdapter(),))

    assert effects["count"] == 0


def test_registry_does_not_bind_custom_or_cached_lifecycle_descriptors() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"custom": 0, "cached": 0}

    class CallableDescriptor:
        def __get__(self, instance, owner):
            del instance, owner
            effects["custom"] += 1
            return lambda request: None

    class CustomDescriptorAdapter(ProviderAdapterBase):
        provider_id = "custom-descriptor"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)
        execute = CallableDescriptor()

    class CachedPropertyAdapter(ProviderAdapterBase):
        provider_id = "cached-property"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @cached_property
        def execute(self):
            effects["cached"] += 1
            return lambda request: None

    for adapter in (CustomDescriptorAdapter(), CachedPropertyAdapter()):
        with pytest.raises(
            InvalidProviderAdapterError, match="non-method lifecycle member"
        ):
            ProviderRegistry((adapter,))

    assert effects == {"custom": 0, "cached": 0}


def test_registry_does_not_invoke_dynamic_getattr_for_missing_lifecycle() -> None:
    effects = {"count": 0}

    class DynamicLifecycle:
        provider_id = "dynamic-getattr"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def construct_request(self, intent):
            del intent

        def validate_request(self, request, intent):
            del request, intent

        def extract_response(self, execution_result):
            del execution_result

        def project_result(self, request, intent, projection):
            del request, intent, projection

        def validate_result(self, result, request, intent, projection):
            del result, request, intent, projection

        def __getattr__(self, name):
            effects["count"] += 1
            if name == "execute":
                return lambda request: None
            raise AttributeError(name)

    with pytest.raises(
        InvalidProviderAdapterError, match="execute: missing lifecycle member"
    ):
        ProviderRegistry((DynamicLifecycle(),))  # type: ignore[arg-type]

    assert effects["count"] == 0


def test_registry_rejects_custom_getattribute_without_invoking_it() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"count": 0}

    class InterceptingAdapter(ProviderAdapterBase):
        provider_id = "intercepting"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def __getattribute__(self, name):
            if name == "execute":
                effects["count"] += 1
                return lambda request: None
            return object.__getattribute__(self, name)

    with pytest.raises(
        InvalidProviderAdapterError, match="dynamic attribute interception"
    ):
        ProviderRegistry((InterceptingAdapter(),))

    assert effects["count"] == 0


def test_registry_rejects_plain_callable_instance_lifecycle_member() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class InstanceCallableAdapter(ProviderAdapterBase):
        provider_id = "instance-callable"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def __init__(self):
            self.execute = lambda request: None

    with pytest.raises(
        InvalidProviderAdapterError, match="non-method lifecycle member"
    ):
        ProviderRegistry((InstanceCallableAdapter(),))


def test_registry_accepts_substitutable_static_and_class_methods() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class StaticMethodAdapter(ProviderAdapterBase):
        provider_id = "static-method"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @staticmethod
        def execute(payload):
            del payload
            raise ProviderCapabilityUnavailableError("unavailable")

    class ClassMethodAdapter(ProviderAdapterBase):
        provider_id = "class-method"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @classmethod
        def execute(cls, payload):
            del cls, payload
            raise ProviderCapabilityUnavailableError("unavailable")

    registry = ProviderRegistry((StaticMethodAdapter(), ClassMethodAdapter()))

    assert registry.provider_ids == ("class-method", "static-method")


def test_registry_accepts_overridden_method_without_invoking_lifecycle() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"count": 0}

    class SideEffectBodyAdapter(ProviderAdapterBase):
        provider_id = "side-effect-body"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, differently_named):
            del differently_named
            effects["count"] += 1
            raise ProviderCapabilityUnavailableError("unavailable")

    registry = ProviderRegistry((SideEffectBodyAdapter(),))

    assert registry.provider_ids == ("side-effect-body",)
    assert effects["count"] == 0


def test_registry_validates_real_decorated_wrapper_signature() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"compatible": 0, "missing": 0, "extra": 0, "keyword": 0}

    def authoritative(self, request):
        del self, request

    class CompatibleWrapper(ProviderAdapterBase):
        provider_id = "compatible-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self, request):
            del self, request
            effects["compatible"] += 1

    class MissingWrapper(ProviderAdapterBase):
        provider_id = "missing-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self):
            del self
            effects["missing"] += 1

    class ExtraWrapper(ProviderAdapterBase):
        provider_id = "extra-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self, request, extra):
            del self, request, extra
            effects["extra"] += 1

    class KeywordWrapper(ProviderAdapterBase):
        provider_id = "keyword-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self, *, request):
            del self, request
            effects["keyword"] += 1

    assert ProviderRegistry((CompatibleWrapper(),)).provider_ids == (
        "compatible-wrapper",
    )
    for adapter in (MissingWrapper(), ExtraWrapper(), KeywordWrapper()):
        with pytest.raises(
            InvalidProviderAdapterError, match="execute: callable signature"
        ):
            ProviderRegistry((adapter,))

    assert effects == {"compatible": 0, "missing": 0, "extra": 0, "keyword": 0}


def test_registry_handles_decorated_variadic_wrappers_by_real_shape() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"args": 0, "kwargs": 0}

    def authoritative(self, request):
        del self, request

    class ArgsWrapper(ProviderAdapterBase):
        provider_id = "args-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self, *args):
            del self, args
            effects["args"] += 1

    class KwargsWrapper(ProviderAdapterBase):
        provider_id = "kwargs-wrapper"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(authoritative)
        def execute(self, **kwargs):
            del self, kwargs
            effects["kwargs"] += 1

    assert ProviderRegistry((ArgsWrapper(),)).provider_ids == ("args-wrapper",)
    with pytest.raises(
        InvalidProviderAdapterError, match="execute: callable signature"
    ):
        ProviderRegistry((KwargsWrapper(),))

    assert effects == {"args": 0, "kwargs": 0}


def test_registry_rejects_incompatible_copied_wrapper_annotations() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def misleading(self: str, request: str) -> str:
        del self, request
        return "misleading"

    class WrapperAdapter(ProviderAdapterBase):
        provider_id = "copied-annotations"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(misleading)
        def execute(self, payload):
            del self, payload
            raise ProviderCapabilityUnavailableError("unavailable")

    _materialize(
        WrapperAdapter.execute,
        {"self": str, "request": str, "return": str},
    )

    with pytest.raises(InvalidProviderAdapterError, match="execute: return annotation"):
        ProviderRegistry((WrapperAdapter(),))


def test_registry_rejects_forged_wrapped_and_signature_metadata() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def authoritative(self, request):
        del self, request

    class ForgedWrapped(ProviderAdapterBase):
        provider_id = "forged-wrapped"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self):
            del self

        execute.__wrapped__ = authoritative

    class ForgedSignature(ProviderAdapterBase):
        provider_id = "forged-signature"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self):
            del self

        execute.__signature__ = Signature(
            parameters=(
                Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
                Parameter("request", Parameter.POSITIONAL_OR_KEYWORD),
            )
        )

    messages = []
    for adapter in (ForgedWrapped(), ForgedSignature(), ForgedWrapped()):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((adapter,))
        messages.append(str(captured.value))

    assert messages == ["incompatible lifecycle method execute: callable signature"] * 3


def test_registry_accepts_compatible_decorated_static_and_class_methods() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"static": 0, "class": 0}

    def static_shape(request):
        del request

    def class_shape(cls, request):
        del cls, request

    class StaticAdapter(ProviderAdapterBase):
        provider_id = "decorated-static"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @staticmethod
        @wraps(static_shape)
        def execute(request):
            del request
            effects["static"] += 1

    class ClassAdapter(ProviderAdapterBase):
        provider_id = "decorated-class"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @classmethod
        @wraps(class_shape)
        def execute(cls, request):
            del cls, request
            effects["class"] += 1

    registry = ProviderRegistry((StaticAdapter(), ClassAdapter()))

    assert registry.provider_ids == ("decorated-class", "decorated-static")
    assert effects == {"static": 0, "class": 0}


def test_registry_rejects_structural_abstract_lifecycle_method() -> None:
    effects = {"count": 0}

    class StructuralAbstract:
        provider_id = "structural-abstract"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def construct_request(self, intent):
            del self, intent

        def validate_request(self, request, intent):
            del self, request, intent

        @abstractmethod
        def execute(self, request):
            del self, request
            effects["count"] += 1
            raise NotImplementedError

        def extract_response(self, result):
            del self, result

        def project_result(self, request, intent, projection):
            del self, request, intent, projection

        def validate_result(self, result, request, intent, projection):
            del self, result, request, intent, projection

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((StructuralAbstract(),))  # type: ignore[arg-type]
        messages.append(str(captured.value))

    assert (
        messages
        == ["incompatible lifecycle method execute: abstract lifecycle method"] * 2
    )
    assert effects["count"] == 0


def test_registry_handles_abstract_inheritance_and_concrete_override() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class AbstractBase(ProviderAdapterBase):
        @abstractmethod
        def execute(self, request):
            del self, request
            raise NotImplementedError

    AbstractBase.__abstractmethods__ = frozenset()

    class InheritedAbstract(AbstractBase):
        provider_id = "inherited-abstract"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    InheritedAbstract.__abstractmethods__ = frozenset()

    class ConcreteOverride(AbstractBase):
        provider_id = "concrete-override"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request):
            del self, request
            raise ProviderCapabilityUnavailableError("unavailable")

    class AbstractOverride(ConcreteOverride):
        provider_id = "abstract-override"
        descriptor = _descriptor(provider_id)

        @abstractmethod
        def execute(self, request):
            del self, request
            raise NotImplementedError

    AbstractOverride.__abstractmethods__ = frozenset()

    for adapter in (InheritedAbstract(), AbstractOverride()):
        with pytest.raises(
            InvalidProviderAdapterError, match="execute: abstract lifecycle method"
        ):
            ProviderRegistry((adapter,))
    assert ProviderRegistry((ConcreteOverride(),)).provider_ids == (
        "concrete-override",
    )


def test_registry_rejects_abstract_static_class_and_decorated_methods() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def decorator(function):
        @wraps(function)
        def wrapper(self, request):
            return function(self, request)

        return wrapper

    class AbstractStatic(ProviderAdapterBase):
        provider_id = "abstract-static"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @staticmethod
        @abstractmethod
        def execute(request):
            del request
            raise NotImplementedError

    class AbstractClass(ProviderAdapterBase):
        provider_id = "abstract-class"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @classmethod
        @abstractmethod
        def execute(cls, request):
            del cls, request
            raise NotImplementedError

    class DecoratedAbstract(ProviderAdapterBase):
        provider_id = "decorated-abstract"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @decorator
        @abstractmethod
        def execute(self, request):
            del self, request
            raise NotImplementedError

    for adapter_type in (AbstractStatic, AbstractClass, DecoratedAbstract):
        adapter_type.__abstractmethods__ = frozenset()
        with pytest.raises(
            InvalidProviderAdapterError, match="execute: abstract lifecycle method"
        ):
            ProviderRegistry((adapter_type(),))


def test_wrapped_metadata_never_suppresses_actual_annotation_validation() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def authority(self, request):
        del self, request

    wrapped_values = (
        authority,
        object(),
        lambda: None,
    )

    def invalid_execute(effect_counter):
        def execute(self, request) -> str:
            del self, request
            effect_counter["lifecycle"] += 1
            return "invalid"

        _materialize(execute, {"return": str})
        return execute

    for index, wrapped_value in enumerate(wrapped_values):
        effects = {"lifecycle": 0, "wrapped": 0}
        execute = invalid_execute(effects)
        execute.__wrapped__ = wrapped_value
        provider_id = f"wrapped-annotation-{index}"
        adapter_type = type(
            f"WrappedAnnotation{index}",
            (ProviderAdapterBase,),
            {
                "provider_id": provider_id,
                "adapter_identity": TEST_IDENTITY,
                "descriptor": _descriptor(provider_id),
                "execute": execute,
            },
        )
        messages = []
        for _ in range(2):
            with pytest.raises(InvalidProviderAdapterError) as captured:
                ProviderRegistry((adapter_type(),))
            messages.append(str(captured.value))
        assert (
            messages == ["incompatible lifecycle method execute: return annotation"] * 2
        )
        assert effects == {"lifecycle": 0, "wrapped": 0}


def test_cyclic_and_chained_wrapped_metadata_do_not_change_annotations() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def cyclic(self, request):
        del self, request

    cyclic.__annotations__ = {"request": "UnknownLifecycleType"}
    cyclic.__wrapped__ = cyclic

    def final(self, request):
        del self, request

    def middle(self, request):
        del self, request

    middle.__wrapped__ = final

    def chained(self, request):
        del self, request

    chained.__annotations__ = {"request": "UnknownLifecycleType"}
    chained.__wrapped__ = middle

    for index, implementation in enumerate((cyclic, chained)):
        provider_id = f"wrapped-unresolved-{index}"
        adapter_type = type(
            f"WrappedUnresolved{index}",
            (ProviderAdapterBase,),
            {
                "provider_id": provider_id,
                "adapter_identity": TEST_IDENTITY,
                "descriptor": _descriptor(provider_id),
                "execute": implementation,
            },
        )
        with pytest.raises(
            InvalidProviderAdapterError, match="execute: unresolved annotation"
        ):
            ProviderRegistry((adapter_type(),))


@pytest.mark.parametrize(
    "expression",
    (
        "annotation_factory()",
        "module.annotation_factory()",
        "list[annotation_factory()]",
        "ProviderRequestEnvelopeV2 | annotation_factory()",
        "lambda: ProviderRequestEnvelopeV2",
        "[ProviderRequestEnvelopeV2 for item in values]",
        "[ProviderRequestEnvelopeV2][0]",
        "ProviderRequestEnvelopeV2 if condition else object",
        "__import__('module').ProviderRequestEnvelopeV2",
        "{'request': ProviderRequestEnvelopeV2}['request']",
        "ProviderRequestEnvelopeV2 + object",
        "(",
    ),
)
def test_unsafe_annotation_expressions_are_rejected_without_execution(
    expression: str,
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {
        "annotation_evaluation": 0,
        "lifecycle": 0,
        "module_getattr": 0,
    }

    def annotation_factory():
        effects["annotation_evaluation"] += 1
        return ProviderRequestEnvelopeV2

    def execute(self, request):
        del self, request
        effects["lifecycle"] += 1

    execute.__annotations__ = {"request": expression}
    execute.__globals__["annotation_factory"] = annotation_factory
    provider_id = "unsafe-annotation"

    class UnsafeAnnotationAdapter(ProviderAdapterBase):
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    UnsafeAnnotationAdapter.provider_id = provider_id
    UnsafeAnnotationAdapter.execute = execute

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((UnsafeAnnotationAdapter(),))
        messages.append(str(captured.value))
    assert (
        messages
        == ["incompatible lifecycle method execute: unsafe annotation expression"] * 2
    )
    assert effects == {
        "annotation_evaluation": 0,
        "lifecycle": 0,
        "module_getattr": 0,
    }


@pytest.mark.parametrize(
    "expression",
    (
        "UnknownLifecycleType",
        "unknown.ProviderRequestEnvelopeV2",
        "unknown.deep.ProviderRequestEnvelopeV2",
    ),
)
def test_unresolved_annotation_names_are_rejected_deterministically(
    expression: str,
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    def execute(self, request):
        del self, request

    execute.__annotations__ = {"request": expression}
    provider_id = "unresolved-annotation"

    class UnresolvedAnnotationAdapter(ProviderAdapterBase):
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    UnresolvedAnnotationAdapter.provider_id = provider_id
    UnresolvedAnnotationAdapter.execute = execute

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((UnresolvedAnnotationAdapter(),))
        messages.append(str(captured.value))
    assert (
        messages == ["incompatible lifecycle method execute: unresolved annotation"] * 2
    )


def test_qualified_annotation_never_invokes_module_getattr() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"module_getattr": 0, "lifecycle": 0}

    class ModuleLike:
        def __getattr__(self, name):
            del name
            effects["module_getattr"] += 1
            return ProviderRequestEnvelopeV2

    def execute(self, request):
        del self, request
        effects["lifecycle"] += 1

    execute.__annotations__ = {"request": "module.ProviderRequestEnvelopeV2"}
    execute.__globals__["module"] = ModuleLike()

    class QualifiedAnnotationAdapter(ProviderAdapterBase):
        provider_id = "qualified-annotation"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    QualifiedAnnotationAdapter.execute = execute
    with pytest.raises(
        InvalidProviderAdapterError, match="execute: unresolved annotation"
    ):
        ProviderRegistry((QualifiedAnnotationAdapter(),))
    assert effects == {"module_getattr": 0, "lifecycle": 0}


def test_unsafe_return_annotation_is_rejected_without_execution() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"annotation": 0, "lifecycle": 0}

    def annotation_factory():
        effects["annotation"] += 1
        return ProviderResultProjectionV2

    def execute(self, request):
        del self, request
        effects["lifecycle"] += 1

    execute.__annotations__ = {"return": "annotation_factory()"}
    execute.__globals__["annotation_factory"] = annotation_factory

    class UnsafeReturnAdapter(ProviderAdapterBase):
        provider_id = "unsafe-return"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    UnsafeReturnAdapter.execute = execute
    with pytest.raises(
        InvalidProviderAdapterError, match="execute: unsafe annotation expression"
    ):
        ProviderRegistry((UnsafeReturnAdapter(),))
    assert effects == {"annotation": 0, "lifecycle": 0}


def test_python314_deferred_annotations_are_rejected_without_execution() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"annotation": 0, "lifecycle": 0}

    def annotation_factory():
        effects["annotation"] += 1
        return ProviderRequestEnvelopeV2

    namespace = {
        "ProviderRequestEnvelopeV2": ProviderRequestEnvelopeV2,
        "ProviderResultProjectionV2": ProviderResultProjectionV2,
        "annotation_factory": annotation_factory,
        "effects": effects,
    }
    unsafe_code = compile(
        "def execute(self, request: annotation_factory()):\n"
        "    effects['lifecycle'] += 1\n",
        "<deferred-unsafe-annotation>",
        "exec",
        dont_inherit=True,
    )
    exec(unsafe_code, namespace)  # noqa: S102 - isolates Python 3.14 semantics
    unsafe_execute = namespace["execute"]

    class DeferredUnsafeAdapter(ProviderAdapterBase):
        provider_id = "deferred-unsafe"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    DeferredUnsafeAdapter.execute = unsafe_execute
    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((DeferredUnsafeAdapter(),))
    assert effects == {"annotation": 0, "lifecycle": 0}

    safe_code = compile(
        "def execute(self, request: ProviderRequestEnvelopeV2) "
        "-> ProviderResultProjectionV2:\n"
        "    effects['lifecycle'] += 1\n",
        "<deferred-safe-annotation>",
        "exec",
        dont_inherit=True,
    )
    exec(safe_code, namespace)  # noqa: S102 - isolates Python 3.14 semantics
    safe_execute = namespace["execute"]

    class DeferredSafeAdapter(ProviderAdapterBase):
        provider_id = "deferred-safe"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    DeferredSafeAdapter.execute = safe_execute
    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((DeferredSafeAdapter(),))
    assert effects == {"annotation": 0, "lifecycle": 0}


@pytest.mark.parametrize(
    "expression",
    (
        "ProviderRequestEnvelopeV2",
        "ProviderRequestEnvelopeV2 | None",
        "list[ProviderRequestEnvelopeV2]",
        "typing.Any",
        "factory()",
    ),
)
def test_deferred_annotator_is_never_invoked_for_any_expression(
    expression: str,
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"factory": 0, "lifecycle": 0}

    def factory():
        effects["factory"] += 1
        raise RuntimeError("must not execute")

    namespace = {
        "ProviderRequestEnvelopeV2": ProviderRequestEnvelopeV2,
        "factory": factory,
        "typing": object(),
        "effects": effects,
    }
    code = compile(
        f"def execute(self, request: {expression}):\n"
        "    effects['lifecycle'] += 1\n",
        "<revision-8-no-annotator-execution>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - constructs Python 3.14 deferred metadata
    execute = namespace["execute"]
    annotator = object.__getattribute__(execute, "__annotate__")
    adapter_type = type(
        "NeverExecuteDeferredAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "never-execute-deferred",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("never-execute-deferred"),
            "execute": execute,
        },
    )

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidProviderAdapterError) as captured:
            ProviderRegistry((adapter_type(),))
        messages.append(str(captured.value))
    assert (
        messages
        == [
            "incompatible lifecycle method execute: deferred annotations require execution"
        ]
        * 2
    )
    assert object.__getattribute__(execute, "__annotate__") is annotator
    assert effects == {"factory": 0, "lifecycle": 0}


def test_forged_code_constants_are_opaque_and_never_executed() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {
        "or": 0,
        "ror": 0,
        "getitem": 0,
        "call": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "str": 0,
        "lifecycle": 0,
    }

    class HostileConstant:
        def __or__(self, other):
            del other
            effects["or"] += 1
            return object

        def __ror__(self, other):
            del other
            effects["ror"] += 1
            return object

        def __getitem__(self, item):
            del item
            effects["getitem"] += 1
            return object

        def __call__(self):
            effects["call"] += 1
            return object

        def __eq__(self, other):
            del other
            effects["eq"] += 1
            return False

        def __hash__(self):
            effects["hash"] += 1
            return 1

        def __repr__(self):
            effects["repr"] += 1
            return "hostile"

        def __str__(self):
            effects["str"] += 1
            return "hostile"

    hostile = HostileConstant()

    def annotator(format):
        return {"request": format | 1234567}

    constants = tuple(
        hostile if item == 1234567 else item for item in annotator.__code__.co_consts
    )
    annotator.__code__ = annotator.__code__.replace(co_consts=constants)
    code_object = annotator.__code__
    constants_object = code_object.co_consts

    def execute(self, request):
        del self, request
        effects["lifecycle"] += 1

    execute.__annotate__ = annotator
    adapter_type = type(
        "HostileConstantAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "hostile-constant",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("hostile-constant"),
            "execute": execute,
        },
    )
    effects.update({key: 0 for key in effects})

    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert execute.__annotate__ is annotator
    assert annotator.__code__ is code_object
    assert annotator.__code__.co_consts is constants_object
    assert all(value == 0 for value in effects.values())


@pytest.mark.parametrize("method_kind", ("instance", "static", "class", "inherited"))
def test_all_deferred_method_forms_are_rejected_without_execution(
    method_kind: str,
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"lifecycle": 0}
    namespace = {"effects": effects}
    parameters = "request" if method_kind == "static" else "self, request"
    code = compile(
        f"def execute({parameters}: object):\n" "    effects['lifecycle'] += 1\n",
        "<revision-8-method-kind>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - constructs Python 3.14 deferred metadata
    execute = namespace["execute"]
    member = execute
    if method_kind == "static":
        member = staticmethod(execute)
    elif method_kind == "class":
        member = classmethod(execute)

    base_type = ProviderAdapterBase
    attributes: dict[str, object] = {
        "provider_id": f"deferred-{method_kind}",
        "adapter_identity": TEST_IDENTITY,
        "descriptor": _descriptor(f"deferred-{method_kind}"),
        "execute": member,
    }
    if method_kind == "inherited":
        base_type = type("DeferredBase", (ProviderAdapterBase,), {"execute": execute})
        attributes.pop("execute")
    adapter_type = type("DeferredMethodAdapter", (base_type,), attributes)

    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert effects == {"lifecycle": 0}


def test_registry_contains_no_deferred_annotation_execution_path() -> None:
    source = (CORE / "registry.py").read_text(encoding="utf-8")

    forbidden = (
        "annotationlib",
        "VALUE_WITH_FAKE_GLOBALS",
        "get_type_hints",
        "ForwardRef",
        "_invoke_sanitized_annotator",
        "_validate_deferred_annotator",
        "get_instructions",
    )
    assert all(item not in source for item in forbidden)
    assert "annotator(" not in source


def test_protocol_authority_annotator_is_not_invoked(monkeypatch) -> None:
    from pastila_scout.provider_composition_v2 import build_provider_registry

    effects = {"annotator": 0}

    def annotator(format):
        del format
        effects["annotator"] += 1
        raise RuntimeError("must not execute")

    monkeypatch.setattr(ProviderAdapter.execute, "__annotate__", annotator)

    assert build_provider_registry().provider_ids == (
        "claude",
        "gemini",
        "ollama",
        "openai",
    )
    assert effects == {"annotator": 0}


def test_safe_static_annotations_preserve_compatible_lifecycle_authority() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class SafeAnnotations(ProviderAdapterBase):
        provider_id = "safe-annotations"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(
            self, request: ProviderRequestEnvelopeV2
        ) -> ProviderResultProjectionV2:
            del self, request
            raise ProviderCapabilityUnavailableError("unavailable")

    class AnyAnnotations(ProviderAdapterBase):
        provider_id = "any-annotations"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request: Any) -> Any:
            del self, request
            raise ProviderCapabilityUnavailableError("unavailable")

    class ObjectParameter(ProviderAdapterBase):
        provider_id = "object-parameter"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request: object) -> ProviderResultProjectionV2:
            del self, request
            raise ProviderCapabilityUnavailableError("unavailable")

    class GenericReturn(ProviderAdapterBase):
        provider_id = "generic-return"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def validate_request(
            self,
            request: ProviderRequestEnvelopeV2,
            intent: ProviderRequestIntentV2,
        ) -> tuple[ProviderV2ValidationIssue, ...]:
            del self, request, intent
            return ()

    _materialize(
        SafeAnnotations.execute,
        {
            "request": ProviderRequestEnvelopeV2,
            "return": ProviderResultProjectionV2,
        },
    )
    _materialize(AnyAnnotations.execute, {"request": Any, "return": Any})
    _materialize(
        ObjectParameter.execute,
        {"request": object, "return": ProviderResultProjectionV2},
    )
    _materialize(
        GenericReturn.validate_request,
        {
            "request": ProviderRequestEnvelopeV2,
            "intent": ProviderRequestIntentV2,
            "return": tuple[ProviderV2ValidationIssue, ...],
        },
    )

    registry = ProviderRegistry(
        (SafeAnnotations(), AnyAnnotations(), ObjectParameter(), GenericReturn())
    )
    assert registry.provider_ids == (
        "any-annotations",
        "generic-return",
        "object-parameter",
        "safe-annotations",
    )


def test_safe_union_and_none_are_parsed_then_checked_for_compatibility() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class SafeUnion(ProviderAdapterBase):
        provider_id = "safe-union"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request):
            del self, request

    SafeUnion.execute.__annotations__ = {"request": "ProviderRequestEnvelopeV2 | None"}

    with pytest.raises(
        InvalidProviderAdapterError, match="execute: parameter 0 annotation"
    ):
        ProviderRegistry((SafeUnion(),))


def test_decorated_static_class_and_instance_annotations_remain_authoritative() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"annotation": 0, "lifecycle": 0}

    def instance_shape(
        self, request: ProviderRequestEnvelopeV2
    ) -> ProviderResultProjectionV2:
        del self, request
        raise NotImplementedError

    class DecoratedInstance(ProviderAdapterBase):
        provider_id = "decorated-safe-instance"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @wraps(instance_shape)
        def execute(self, request):
            del self, request
            effects["lifecycle"] += 1

    class DecoratedStatic(ProviderAdapterBase):
        provider_id = "decorated-safe-static"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @staticmethod
        def execute(
            request: ProviderRequestEnvelopeV2,
        ) -> ProviderResultProjectionV2:
            del request
            effects["lifecycle"] += 1

    class DecoratedClass(ProviderAdapterBase):
        provider_id = "decorated-safe-class"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        @classmethod
        def execute(
            cls, request: ProviderRequestEnvelopeV2
        ) -> ProviderResultProjectionV2:
            del cls, request
            effects["lifecycle"] += 1

    annotations = {
        "request": ProviderRequestEnvelopeV2,
        "return": ProviderResultProjectionV2,
    }
    _materialize(DecoratedInstance.execute, annotations)
    _materialize(DecoratedStatic.__dict__["execute"].__func__, annotations)
    _materialize(DecoratedClass.__dict__["execute"].__func__, annotations)

    assert ProviderRegistry(
        (DecoratedInstance(), DecoratedStatic(), DecoratedClass())
    ).provider_ids == (
        "decorated-safe-class",
        "decorated-safe-instance",
        "decorated-safe-static",
    )
    assert effects == {"annotation": 0, "lifecycle": 0}


@pytest.mark.parametrize("method_kind", ("instance", "static", "class"))
def test_unsafe_annotations_on_all_method_kinds_never_execute(method_kind: str) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"annotation": 0, "lifecycle": 0}

    def factory():
        effects["annotation"] += 1
        return ProviderRequestEnvelopeV2

    if method_kind == "instance":

        def execute(self, request):
            del self, request
            effects["lifecycle"] += 1

        implementation = execute
    elif method_kind == "static":

        def execute(request):
            del request
            effects["lifecycle"] += 1

        implementation = staticmethod(execute)
    else:

        def execute(cls, request):
            del cls, request
            effects["lifecycle"] += 1

        implementation = classmethod(execute)
    execute.__annotations__ = {"request": "factory()"}
    execute.__globals__["factory"] = factory
    provider_id = f"unsafe-{method_kind}"
    adapter_type = type(
        f"Unsafe{method_kind.title()}",
        (ProviderAdapterBase,),
        {
            "provider_id": provider_id,
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor(provider_id),
            "execute": implementation,
        },
    )
    with pytest.raises(
        InvalidProviderAdapterError, match="execute: unsafe annotation expression"
    ):
        ProviderRegistry((adapter_type(),))
    assert effects == {"annotation": 0, "lifecycle": 0}


def test_annotation_mapping_and_custom_annotation_objects_are_not_mutated_or_rendered() -> (
    None
):
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"repr": 0, "lifecycle": 0}

    class OpaqueAnnotation:
        def __repr__(self):
            effects["repr"] += 1
            return "opaque"

    annotation = OpaqueAnnotation()
    annotations = {"request": annotation}

    def execute(self, request):
        del self, request
        effects["lifecycle"] += 1

    execute.__annotations__ = annotations

    class OpaqueAdapter(ProviderAdapterBase):
        provider_id = "opaque-annotation"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

    OpaqueAdapter.execute = execute
    with pytest.raises(
        InvalidProviderAdapterError, match="execute: unsafe annotation expression"
    ):
        ProviderRegistry((OpaqueAdapter(),))
    assert execute.__annotations__ is annotations
    assert execute.__annotations__ == {"request": annotation}
    assert effects == {"repr": 0, "lifecycle": 0}


def test_concrete_override_replaces_inherited_unsafe_annotation_authority() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    class UnsafeBase(ProviderAdapterBase):
        def execute(self, request):
            del self, request

    UnsafeBase.execute.__annotations__ = {"request": "factory()"}

    class ConcreteOverride(UnsafeBase):
        provider_id = "safe-concrete-override"
        adapter_identity = TEST_IDENTITY
        descriptor = _descriptor(provider_id)

        def execute(self, request: ProviderRequestEnvelopeV2):
            del self, request

    _materialize(ConcreteOverride.execute, {"request": ProviderRequestEnvelopeV2})

    assert ProviderRegistry((ConcreteOverride(),)).provider_ids == (
        "safe-concrete-override",
    )


def test_hostile_resolved_annotation_objects_are_rejected_without_special_methods() -> (
    None
):
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {
        "subclasscheck": 0,
        "instancecheck": 0,
        "getattribute": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "str": 0,
        "or": 0,
        "ror": 0,
        "getitem": 0,
        "call": 0,
        "lifecycle": 0,
    }

    class HostileMeta(type):
        def __subclasscheck__(cls, subclass):
            del cls, subclass
            effects["subclasscheck"] += 1
            return True

        def __instancecheck__(cls, instance):
            del cls, instance
            effects["instancecheck"] += 1
            return True

        def __getattribute__(cls, name):
            effects["getattribute"] += 1
            return super().__getattribute__(name)

    class HostileClass(metaclass=HostileMeta):
        pass

    class HostileObject:
        def __eq__(self, other):
            del other
            effects["eq"] += 1
            return True

        def __hash__(self):
            effects["hash"] += 1
            return 0

        def __repr__(self):
            effects["repr"] += 1
            return "hostile"

        def __str__(self):
            effects["str"] += 1
            return "hostile"

        def __or__(self, other):
            del other
            effects["or"] += 1
            return self

        def __ror__(self, other):
            del other
            effects["ror"] += 1
            return self

        def __getitem__(self, item):
            del item
            effects["getitem"] += 1
            return self

        def __call__(self):
            effects["call"] += 1
            return self

    hostile_values = (HostileClass, HostileObject())
    effects.update({key: 0 for key in effects})
    for index, annotation in enumerate(hostile_values):

        def execute(self, request):
            del self, request
            effects["lifecycle"] += 1

        execute.__annotations__ = {"request": annotation}
        provider_id = f"hostile-resolved-{index}"
        adapter_type = type(
            f"HostileResolved{index}",
            (ProviderAdapterBase,),
            {
                "provider_id": provider_id,
                "adapter_identity": TEST_IDENTITY,
                "descriptor": _descriptor(provider_id),
                "execute": execute,
            },
        )
        with pytest.raises(
            InvalidProviderAdapterError, match="execute: unsafe annotation expression"
        ):
            ProviderRegistry((adapter_type(),))
    assert all(value == 0 for value in effects.values())


@pytest.mark.parametrize(
    ("annotation_name", "accepted"),
    (
        ("ProviderRequestEnvelopeV2", True),
        ("ProviderResultEnvelopeV2", False),
        ("Any", True),
        ("object", True),
        ("list", False),
        ("tuple", False),
        ("dict", False),
        ("set", False),
        ("frozenset", False),
        ("str", False),
        ("int", False),
        ("float", False),
        ("bool", False),
        ("bytes", False),
    ),
)
def test_deferred_trusted_names_ignore_hostile_global_shadowing(
    annotation_name: str, accepted: bool
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {
        "or": 0,
        "ror": 0,
        "class_getitem": 0,
        "getitem": 0,
        "getattr": 0,
        "getattribute": 0,
        "subclasscheck": 0,
        "instancecheck": 0,
        "eq": 0,
        "hash": 0,
        "repr": 0,
        "str": 0,
        "call": 0,
        "lifecycle": 0,
    }

    class Hostile:
        def __getattribute__(self, name):
            if name != "_effects":
                effects["getattribute"] += 1
            return object.__getattribute__(self, name)

        def __getattr__(self, name):
            del name
            effects["getattr"] += 1
            return self

        def __or__(self, other):
            del other
            effects["or"] += 1
            return self

        def __ror__(self, other):
            del other
            effects["ror"] += 1
            return self

        def __getitem__(self, item):
            del item
            effects["getitem"] += 1
            return self

        def __eq__(self, other):
            del other
            effects["eq"] += 1
            return True

        def __hash__(self):
            effects["hash"] += 1
            return 0

        def __repr__(self):
            effects["repr"] += 1
            return "hostile"

        def __str__(self):
            effects["str"] += 1
            return "hostile"

        def __call__(self):
            effects["call"] += 1
            return self

    hostile = Hostile()
    namespace = {annotation_name: hostile, "effects": effects}
    code = compile(
        f"def execute(self, request: {annotation_name}):\n"
        "    effects['lifecycle'] += 1\n",
        "<hostile-global-shadow>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    effects.update({key: 0 for key in effects})
    execute = namespace["execute"]
    provider_id = f"shadow-{annotation_name.lower()}"
    adapter_type = type(
        "ShadowedAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": provider_id,
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor(provider_id),
            "execute": execute,
        },
    )
    del accepted
    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert all(value == 0 for value in effects.values())


@pytest.mark.parametrize(
    "expression",
    (
        "ProviderRequestEnvelopeV2 | None",
        "list[ProviderRequestEnvelopeV2]",
    ),
)
def test_deferred_union_and_generic_use_only_registry_owned_objects(
    expression: str,
) -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"or": 0, "class_getitem": 0, "lifecycle": 0}

    class HostileUnion:
        def __or__(self, other):
            del other
            effects["or"] += 1
            return object

    class HostileGeneric:
        @classmethod
        def __class_getitem__(cls, item):
            del cls, item
            effects["class_getitem"] += 1
            return object

    namespace = {
        "ProviderRequestEnvelopeV2": HostileUnion(),
        "list": HostileGeneric,
        "effects": effects,
    }
    code = compile(
        f"def execute(self, request: {expression}):\n"
        "    effects['lifecycle'] += 1\n",
        "<hostile-composite-shadow>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    provider_id = "shadowed-composite"
    adapter_type = type(
        "ShadowedComposite",
        (ProviderAdapterBase,),
        {
            "provider_id": provider_id,
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor(provider_id),
            "execute": namespace["execute"],
        },
    )
    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert effects == {"or": 0, "class_getitem": 0, "lifecycle": 0}


def test_deferred_qualified_any_ignores_hostile_typing_global() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"getattribute": 0, "getattr": 0, "getitem": 0, "lifecycle": 0}

    class HostileTyping:
        def __getattribute__(self, name):
            effects["getattribute"] += 1
            return object.__getattribute__(self, name)

        def __getattr__(self, name):
            del name
            effects["getattr"] += 1
            return object

        def __getitem__(self, item):
            del item
            effects["getitem"] += 1
            return object

    namespace = {"typing": HostileTyping(), "effects": effects}
    code = compile(
        "def execute(self, request: typing.Any):\n" "    effects['lifecycle'] += 1\n",
        "<hostile-typing-shadow>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    effects.update({key: 0 for key in effects})
    adapter_type = type(
        "HostileTypingAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "hostile-typing",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("hostile-typing"),
            "execute": namespace["execute"],
        },
    )

    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert all(value == 0 for value in effects.values())


def test_adapter_global_mutation_cannot_change_annotation_authority() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"or": 0, "getitem": 0, "getattr": 0, "lifecycle": 0}

    class Hostile:
        def __or__(self, other):
            del other
            effects["or"] += 1
            return self

        def __getitem__(self, item):
            del item
            effects["getitem"] += 1
            return self

        def __getattr__(self, name):
            del name
            effects["getattr"] += 1
            return self

    namespace = {"effects": effects}
    code = compile(
        "def execute(self, request: ProviderRequestEnvelopeV2):\n"
        "    effects['lifecycle'] += 1\n",
        "<adapter-global-mutation>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    _materialize(namespace["execute"], {"request": "ProviderRequestEnvelopeV2"})
    adapter_type = type(
        "GlobalMutationAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "global-mutation",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("global-mutation"),
            "execute": namespace["execute"],
        },
    )
    original = ProviderRegistry((adapter_type(),)).provider_ids
    hostile = Hostile()
    namespace.update(
        {
            "ProviderRequestEnvelopeV2": hostile,
            "list": hostile,
            "typing": hostile,
        }
    )
    shadowed = ProviderRegistry((adapter_type(),)).provider_ids

    assert original == shadowed == ("global-mutation",)
    assert all(value == 0 for value in effects.values())


def test_deferred_indirect_hostile_alias_is_rejected_without_execution() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"getattribute": 0, "repr": 0, "lifecycle": 0}

    class HostileAlias:
        def __getattribute__(self, name):
            effects["getattribute"] += 1
            return object.__getattribute__(self, name)

        def __repr__(self):
            effects["repr"] += 1
            return "hostile"

    namespace = {"Alias": HostileAlias(), "effects": effects}
    code = compile(
        "def execute(self, request: Alias):\n" "    effects['lifecycle'] += 1\n",
        "<hostile-indirect-alias>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    effects.update({key: 0 for key in effects})
    adapter_type = type(
        "HostileAliasAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "hostile-alias",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("hostile-alias"),
            "execute": namespace["execute"],
        },
    )

    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((adapter_type(),))
    assert all(value == 0 for value in effects.values())


def test_deferred_annotation_ignores_hostile_builtins_and_rejects_closures() -> None:
    from pastila_scout.provider_adapters_v2.base import ProviderAdapterBase

    effects = {"getitem": 0, "lifecycle": 0}

    class HostileBuiltins(dict):
        def __getitem__(self, key):
            del key
            effects["getitem"] += 1
            return object

    namespace = {"__builtins__": HostileBuiltins(), "effects": effects}
    code = compile(
        "def execute(self, request: object):\n" "    effects['lifecycle'] += 1\n",
        "<hostile-builtins-shadow>",
        "exec",
        dont_inherit=True,
    )
    exec(code, namespace)  # noqa: S102 - isolates Python 3.14 deferred annotations
    _materialize(namespace["execute"], {"request": "object"})
    effects.update({key: 0 for key in effects})
    provider_id = "hostile-builtins"
    adapter_type = type(
        "HostileBuiltinsAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": provider_id,
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor(provider_id),
            "execute": namespace["execute"],
        },
    )
    assert ProviderRegistry((adapter_type(),)).provider_ids == (provider_id,)
    assert effects == {"getitem": 0, "lifecycle": 0}

    closure_namespace = {}
    closure_code = compile(
        "def outer():\n"
        "    ProviderRequestEnvelopeV2 = object\n"
        "    def execute(self, request: ProviderRequestEnvelopeV2):\n"
        "        return None\n"
        "    return execute\n",
        "<closure-annotation-shadow>",
        "exec",
        dont_inherit=True,
    )
    exec(closure_code, closure_namespace)  # noqa: S102 - Python 3.14 closure probe
    closure_execute = closure_namespace["outer"]()
    closure_type = type(
        "ClosureAnnotationAdapter",
        (ProviderAdapterBase,),
        {
            "provider_id": "closure-annotation",
            "adapter_identity": TEST_IDENTITY,
            "descriptor": _descriptor("closure-annotation"),
            "execute": closure_execute,
        },
    )
    with pytest.raises(
        InvalidProviderAdapterError,
        match="execute: deferred annotations require execution",
    ):
        ProviderRegistry((closure_type(),))


def test_success_projection_requires_completed_output() -> None:
    assert _projection().status is ProviderResultStatusV2.SUCCESS

    with pytest.raises(ValueError, match="successful result requires output"):
        ProviderResultProjectionV2(status=ProviderResultStatusV2.SUCCESS, outputs=())
    for finish_reason in (
        ProviderFinishReasonV2.FAILED,
        ProviderFinishReasonV2.CONTENT_FILTERED,
    ):
        with pytest.raises(
            ValueError, match="successful result requires completed outputs"
        ):
            ProviderResultProjectionV2(
                status=ProviderResultStatusV2.SUCCESS,
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference="execution-request:test",
                        ordinal=0,
                        generated_text="Text",
                        finish_reason=finish_reason,
                    ),
                ),
            )
    with pytest.raises(
        ValueError, match="successful result cannot contain failure_code"
    ):
        ProviderResultProjectionV2(
            status=ProviderResultStatusV2.SUCCESS,
            outputs=_projection().outputs,
            failure_code="contradiction",
        )


def test_failed_projection_requires_failure_code_and_forbids_outputs() -> None:
    with pytest.raises(ValueError, match="non-successful result requires failure_code"):
        ProviderResultProjectionV2(status=ProviderResultStatusV2.FAILED, outputs=())
    for finish_reason in (
        ProviderFinishReasonV2.COMPLETED,
        ProviderFinishReasonV2.FAILED,
    ):
        with pytest.raises(ValueError, match="failed result cannot contain outputs"):
            ProviderResultProjectionV2(
                status=ProviderResultStatusV2.FAILED,
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference="execution-request:test",
                        ordinal=0,
                        generated_text="Successful-looking text",
                        finish_reason=finish_reason,
                    ),
                ),
                failure_code="provider-failed",
            )


def test_partial_projection_requires_genuinely_partial_output() -> None:
    with pytest.raises(ValueError, match="partial result requires output"):
        ProviderResultProjectionV2(
            status=ProviderResultStatusV2.PARTIAL,
            outputs=(),
            failure_code="partial",
        )
    with pytest.raises(ValueError, match="partial result cannot be fully completed"):
        ProviderResultProjectionV2(
            status=ProviderResultStatusV2.PARTIAL,
            outputs=_projection().outputs,
            failure_code="partial",
        )
    failed_output = ProviderOutputInputV2(
        source_request_reference="execution-request:test",
        ordinal=0,
        generated_text="Diagnostic text",
        finish_reason=ProviderFinishReasonV2.FAILED,
    )
    with pytest.raises(ValueError, match="partial result cannot be wholly failed"):
        ProviderResultProjectionV2(
            status=ProviderResultStatusV2.PARTIAL,
            outputs=(failed_output,),
            failure_code="partial",
        )

    partial = ProviderResultProjectionV2(
        status=ProviderResultStatusV2.PARTIAL,
        outputs=(
            failed_output.model_copy(
                update={"finish_reason": ProviderFinishReasonV2.LENGTH}
            ),
        ),
        failure_code="length-limited",
    )

    assert partial.outputs[0].finish_reason is ProviderFinishReasonV2.LENGTH


def test_resealed_contradictory_result_envelope_is_rejected_deterministically() -> None:
    intent, descriptor, projection = _intent(), _descriptor(), _projection()
    request = build_provider_request_envelope(intent, descriptor)
    valid = build_provider_result_envelope(request, intent, descriptor, projection)
    output = valid.outputs[0].model_copy(
        update={"finish_reason": ProviderFinishReasonV2.FAILED}
    )
    output = output.model_copy(update={"identity": result_unit_identity(output)})
    output = output.model_copy(update={"fingerprint": result_unit_fingerprint(output)})
    contradictory = valid.model_copy(update={"outputs": (output,)})
    contradictory = contradictory.model_copy(
        update={"identity": result_envelope_identity(contradictory)}
    )
    contradictory = contradictory.model_copy(
        update={"fingerprint": result_envelope_fingerprint(contradictory)}
    )
    before = contradictory.model_dump(mode="python")

    first = validate_provider_result_envelope(
        contradictory, request, intent, descriptor, projection
    )
    second = validate_provider_result_envelope(
        contradictory, request, intent, descriptor, projection
    )

    assert tuple(item.code for item in first) == (
        "provider-v2-invalid-result-envelope",
    )
    assert first == second
    assert contradictory.model_dump(mode="python") == before
