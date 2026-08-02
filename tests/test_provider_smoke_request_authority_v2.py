from __future__ import annotations

import copy
import gc
import inspect
import json
import pickle
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.provider_smoke_request_authority_v2 as authority_package
import pastila_scout.provider_smoke_request_authority_v2.authority as authority_module
import pastila_scout.provider_smoke_request_authority_v2.interface as authority_interface
from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_smoke_request_authority_v2 import (
    SmokeExecutionPlanV2,
    SmokeExecutionRequestAuthorityError,
    SmokeExecutionRequestConfigurationError,
    SmokeExecutionRequestDependencyError,
    SmokeProviderExecutionRequestAuthorityV2,
    build_canonical_smoke_execution_plan,
)
from pastila_scout.provider_v2 import (
    ProviderMessageInputV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    validate_provider_descriptor,
    validate_provider_request_envelope,
)
from pastila_scout.provider_v2.canonical import canonical_json, semantic_sha256

ROOT = Path(__file__).resolve().parents[1]
FIXED_PROMPT = "Reply with exactly:\n\nSMOKE_OK"
REQUESTED_AT = datetime(2026, 8, 2, 12, tzinfo=UTC)


def _valid_arguments() -> dict[str, object]:
    return {
        "execution_plan": build_canonical_smoke_execution_plan(),
        "execution_request_id": "canonical-smoke-execution-request-v2",
        "requested_at": REQUESTED_AT,
        "timeout_seconds": 20,
    }


def _assert_isolated(error: BaseException) -> None:
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


def test_public_api_is_exact_and_private_models_are_not_exported() -> None:
    assert authority_package.__all__ == (
        "SmokeExecutionPlanV2",
        "SmokeExecutionRequestAuthorityError",
        "SmokeExecutionRequestConfigurationError",
        "SmokeExecutionRequestDependencyError",
        "SmokeProviderExecutionRequestAuthorityV2",
        "build_canonical_smoke_execution_plan",
    )
    assert authority_interface.__all__ == ()


def test_error_taxonomy_is_stable() -> None:
    assert issubclass(
        SmokeExecutionRequestConfigurationError,
        SmokeExecutionRequestAuthorityError,
    )
    assert issubclass(
        SmokeExecutionRequestDependencyError,
        SmokeExecutionRequestAuthorityError,
    )


def test_builder_mints_exact_fixed_smoke_semantics() -> None:
    plan = build_canonical_smoke_execution_plan()
    assert plan.contract_version == "module-2.9-smoke-execution-plan-v2"
    assert plan.plan_reference == "canonical-smoke-plan-v2"
    assert plan.draft_reference == "canonical-smoke-draft-v2"
    assert len(plan.request_units) == 1
    unit = plan.request_units[0]
    assert unit.source_request_reference == "canonical-smoke-source-request-v2"
    assert unit.ordinal == 0
    assert len(unit.messages) == 1
    message = unit.messages[0]
    assert message.role == "generation"
    assert message.content == FIXED_PROMPT
    assert message.ordinal == 0


def test_builder_is_stable_and_canonical_json_is_deterministic() -> None:
    first = build_canonical_smoke_execution_plan()
    second = build_canonical_smoke_execution_plan()
    assert first == second
    assert first is not second
    assert canonical_json(first) == canonical_json(second)
    assert semantic_sha256(first) == semantic_sha256(second)
    assert json.loads(canonical_json(first))["plan_reference"] == (
        "canonical-smoke-plan-v2"
    )
    assert first.plan_identity == (
        "scout:smoke-execution-plan-v2:"
        "2546530aabe45c7aa407824d1f11e34a8dc37648e337b9878381ecc9cfb29406"
    )
    assert first.plan_fingerprint == (
        "7cbaa7115899fc713e1ec6aade2407d9a3737f71ee6d22db565c6df3229fb8c8"
    )
    assert first.draft_fingerprint == (
        "69a46ce7ac4ecb60cc6e85b2eabd90c15e0c25d67d3a785888461e5a41b14bd5"
    )
    assert semantic_sha256({"a": 1, "b": 2}) == semantic_sha256({"b": 2, "a": 1})


def test_identity_and_fingerprints_are_domain_separated() -> None:
    plan = build_canonical_smoke_execution_plan()
    assert plan.plan_identity.startswith("scout:smoke-execution-plan-v2:")
    assert len(plan.plan_identity.rsplit(":", 1)[1]) == 64
    assert len(plan.plan_fingerprint) == 64
    assert len(plan.draft_fingerprint) == 64
    assert (
        len(
            {
                plan.plan_identity.rsplit(":", 1)[1],
                plan.plan_fingerprint,
                plan.draft_fingerprint,
            }
        )
        == 3
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("contract_version", "other"),
        ("plan_reference", "other"),
        ("draft_reference", "other"),
        ("plan_identity", "scout:smoke-execution-plan-v2:" + "0" * 64),
        ("plan_fingerprint", "0" * 64),
        ("draft_fingerprint", "0" * 64),
        ("request_units", ()),
        (
            "request_units",
            (build_canonical_smoke_execution_plan().request_units[0],) * 2,
        ),
    ),
)
def test_plan_rejects_changed_authority(field: str, value: object) -> None:
    payload = build_canonical_smoke_execution_plan().model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        SmokeExecutionPlanV2.model_validate(payload, strict=True)


def test_plan_rejects_changed_message_semantics_and_extra_fields() -> None:
    payload = build_canonical_smoke_execution_plan().model_dump(mode="python")
    payload["request_units"][0]["messages"][0]["content"] = "SMOKE_OK"
    with pytest.raises(ValidationError):
        SmokeExecutionPlanV2.model_validate(payload, strict=True)
    payload = build_canonical_smoke_execution_plan().model_dump(mode="python")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        SmokeExecutionPlanV2.model_validate(payload, strict=True)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("plan_identity", "scout:smoke-execution-plan-v2:" + "0" * 64),
        ("plan_fingerprint", "0" * 64),
        ("draft_fingerprint", "0" * 64),
        ("request_units", ()),
    ),
)
def test_authority_rejects_copied_invalid_plan(field: str, value: object) -> None:
    forged = build_canonical_smoke_execution_plan().model_copy(update={field: value})
    arguments = _valid_arguments()
    arguments["execution_plan"] = forged
    with pytest.raises(SmokeExecutionRequestConfigurationError) as raised:
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    _assert_isolated(raised.value)


@pytest.mark.parametrize(
    "request_id",
    (None, b"id", True, 1, "", " ", " padded", "padded ", "x" * 201),
)
def test_request_identity_is_strict(request_id: object) -> None:
    arguments = _valid_arguments()
    arguments["execution_request_id"] = request_id
    with pytest.raises(SmokeExecutionRequestConfigurationError):
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)


@pytest.mark.parametrize(
    "requested_at",
    (
        None,
        "2026-08-02T12:00:00Z",
        REQUESTED_AT.replace(tzinfo=None),
        datetime(2026, 8, 2, 12, tzinfo=timezone(timedelta(hours=2))),
    ),
)
def test_timestamp_requires_exact_utc_datetime(requested_at: object) -> None:
    arguments = _valid_arguments()
    arguments["requested_at"] = requested_at
    with pytest.raises(SmokeExecutionRequestConfigurationError):
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)


@pytest.mark.parametrize(
    "timeout",
    (None, True, "20", 0, -1, 0.0, -1.0, float("inf"), float("-inf"), float("nan")),
)
def test_timeout_policy_is_strict(timeout: object) -> None:
    arguments = _valid_arguments()
    arguments["timeout_seconds"] = timeout
    with pytest.raises(SmokeExecutionRequestConfigurationError):
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)


@pytest.mark.parametrize("timeout", (1, 30, 10**100, 0.1, 30.25, 1e308))
def test_valid_inputs_construct_exact_provider_request(timeout: object) -> None:
    arguments = _valid_arguments()
    arguments["timeout_seconds"] = timeout
    result = SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    assert type(result) is ProviderExecutionRequestV2
    assert type(result.request_intent) is ProviderRequestIntentV2
    assert type(result.request_envelope) is ProviderRequestEnvelopeV2
    assert type(result.context) is ExecutionContextV2
    assert type(result.timeout_policy) is TimeoutPolicyV2
    assert result.provider == OpenAIProviderAdapter.descriptor
    assert result.provider.provider_id == "openai"
    assert validate_provider_descriptor(result.provider) == ()
    assert (
        validate_provider_request_envelope(
            result.request_envelope, result.request_intent, result.provider
        )
        == ()
    )
    plan = arguments["execution_plan"]
    assert isinstance(plan, SmokeExecutionPlanV2)
    assert result.request_intent.execution_plan_reference == plan.plan_reference
    assert result.request_intent.execution_plan_identity == plan.plan_identity
    assert result.request_intent.execution_plan_fingerprint == plan.plan_fingerprint
    assert result.request_intent.draft_reference == plan.draft_reference
    assert result.request_intent.draft_fingerprint == plan.draft_fingerprint
    assert len(result.request_intent.request_units) == 1
    unit = result.request_intent.request_units[0]
    assert type(unit) is ProviderRequestUnitInputV2
    assert unit.source_request_reference == "canonical-smoke-source-request-v2"
    assert unit.ordinal == 0
    assert len(unit.messages) == 1
    assert type(unit.messages[0]) is ProviderMessageInputV2
    assert unit.messages[0].role == "generation"
    assert unit.messages[0].content == FIXED_PROMPT
    assert unit.messages[0].ordinal == 0
    assert result.context.request_id == arguments["execution_request_id"]
    assert result.context.requested_at == REQUESTED_AT
    assert result.context.metadata == ()
    assert result.context.cancellation.cancellation_requested is False
    assert type(result.timeout_policy.timeout_seconds) is type(timeout)
    assert result.timeout_policy.timeout_seconds == timeout


def test_hostile_input_hooks_are_not_executed() -> None:
    calls: list[str] = []

    class Hostile:
        def __repr__(self) -> str:
            calls.append("repr")
            raise AssertionError

        def __str__(self) -> str:
            calls.append("str")
            raise AssertionError

        def __bool__(self) -> bool:
            calls.append("bool")
            raise AssertionError

        def model_dump(self, **kwargs: object) -> object:
            calls.append("model_dump")
            raise AssertionError(kwargs)

    for field in (
        "execution_plan",
        "execution_request_id",
        "requested_at",
        "timeout_seconds",
    ):
        arguments = _valid_arguments()
        arguments[field] = Hostile()
        with pytest.raises(SmokeExecutionRequestConfigurationError):
            SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    assert calls == []


def test_active_nested_exception_is_not_retained() -> None:
    caller = RuntimeError("caller secret")
    try:
        try:
            raise caller
        except RuntimeError:
            raise ValueError("nested secret")
    except ValueError:
        arguments = _valid_arguments()
        arguments["execution_plan"] = object()
        with pytest.raises(SmokeExecutionRequestConfigurationError) as raised:
            SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    _assert_isolated(raised.value)
    assert raised.value.__context__ is not caller


def test_traceback_contains_no_authority_inputs() -> None:
    plan = build_canonical_smoke_execution_plan()
    authority = SmokeProviderExecutionRequestAuthorityV2()
    with pytest.raises(SmokeExecutionRequestConfigurationError) as raised:
        authority.construct(
            execution_plan=plan.model_copy(update={"plan_fingerprint": "0" * 64}),
            execution_request_id="secret-request-id",
            requested_at=REQUESTED_AT,
            timeout_seconds=19,
        )
    traceback = raised.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").startswith(
            "pastila_scout.provider_smoke_request_authority_v2"
        ):
            values = tuple(traceback.tb_frame.f_locals.values())
            assert plan not in values
            assert authority not in values
            assert "secret-request-id" not in values
            assert REQUESTED_AT not in values
            assert 19 not in values
        traceback = traceback.tb_next


def test_authority_holder_copy_repr_and_pickle_policy() -> None:
    authority = SmokeProviderExecutionRequestAuthorityV2()
    assert copy.copy(authority) is authority
    assert copy.deepcopy(authority) is authority
    assert repr(authority) == "SmokeProviderExecutionRequestAuthorityV2()"
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError, match="cannot be serialized"):
            pickle.dumps(authority, protocol=protocol)


def test_package_has_no_runtime_sdk_network_or_credential_capability() -> None:
    package = ROOT / "src" / "pastila_scout" / "provider_smoke_request_authority_v2"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in package.glob("*.py")
    )
    for forbidden in (
        "OPENAI_API_KEY",
        "OpenAIRuntimeComposerV2",
        "OpenAI(",
        "responses.create",
        "socket",
        "httpx",
        "requests",
        "subprocess",
        "random",
        "datetime.now",
    ):
        assert forbidden not in source


def test_clean_process_import_is_inert() -> None:
    script = """
import os
import sys
reads = []
original = os.getenv
def guarded(name, *args):
    if name == 'OPENAI_API_KEY':
        reads.append(name)
        raise AssertionError('credential access')
    return original(name, *args)
os.getenv = guarded
import pastila_scout.provider_smoke_request_authority_v2 as package
assert len(package.__all__) == 6
assert reads == []
assert not any(name == 'openai' or name.startswith('openai.') for name in sys.modules)
assert 'pastila_scout.provider_runtime_openai_v2' not in sys.modules
assert 'pastila_scout.provider_runtime_openai_smoke_v2' not in sys.modules
assert 'pastila_scout.cli' not in sys.modules
print('authority-clean-import-ok')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "authority-clean-import-ok\n"
    assert result.stderr == ""


def test_module_globals_retain_no_runtime_or_request_objects() -> None:
    authority = SmokeProviderExecutionRequestAuthorityV2()
    request = authority.construct(**_valid_arguments())
    del request
    del authority
    gc.collect()
    for value in vars(authority_package).values():
        assert value.__class__.__name__ not in {
            "ProviderExecutionRequestV2",
            "OpenAIRuntimeCompositionV2",
            "OpenAIProviderExecutorV2",
        }


def test_construct_signature_is_explicit_and_keyword_only() -> None:
    parameters = inspect.signature(
        SmokeProviderExecutionRequestAuthorityV2.construct
    ).parameters
    assert tuple(parameters) == (
        "self",
        "execution_plan",
        "execution_request_id",
        "requested_at",
        "timeout_seconds",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for name, parameter in parameters.items()
        if name != "self"
    )


@pytest.mark.parametrize(
    "timeout", (10**1000, 10**10000), ids=("10-to-1000", "10-to-10000")
)
def test_frozen_incompatible_large_timeout_is_configuration_error(
    timeout: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def acquire():
        nonlocal calls
        calls += 1
        return OpenAIProviderAdapter.descriptor

    monkeypatch.setattr(authority_module, "_canonical_openai_descriptor", acquire)
    arguments = _valid_arguments()
    arguments["timeout_seconds"] = timeout
    with pytest.raises(SmokeExecutionRequestConfigurationError) as raised:
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    assert raised.value.args == ("invalid canonical smoke request authority input",)
    _assert_isolated(raised.value)
    assert calls == 0


def test_large_compatible_integer_matches_frozen_policy() -> None:
    timeout = 10**308
    frozen = TimeoutPolicyV2(timeout_seconds=timeout)
    result = SmokeProviderExecutionRequestAuthorityV2().construct(
        **{**_valid_arguments(), "timeout_seconds": timeout}
    )
    assert frozen.timeout_seconds == timeout
    assert type(result.timeout_policy.timeout_seconds) is int
    assert result.timeout_policy.timeout_seconds == timeout


def test_same_inputs_are_deterministic_and_attempt_fields_are_isolated() -> None:
    authority = SmokeProviderExecutionRequestAuthorityV2()
    arguments = _valid_arguments()
    first = authority.construct(**arguments)
    second = authority.construct(**arguments)
    assert first == second
    changed_id = authority.construct(
        **{**arguments, "execution_request_id": "another-attempt"}
    )
    changed_time = authority.construct(
        **{**arguments, "requested_at": datetime(2026, 8, 2, 13, tzinfo=UTC)}
    )
    changed_timeout = authority.construct(**{**arguments, "timeout_seconds": 41})
    for changed in (changed_id, changed_time, changed_timeout):
        assert changed.provider == first.provider
        assert changed.request_intent == first.request_intent
        assert changed.request_envelope == first.request_envelope
    assert changed_id.context.request_id != first.context.request_id
    assert changed_time.context.requested_at != first.context.requested_at
    assert changed_timeout.timeout_policy != first.timeout_policy


def test_dependency_failure_is_fixed_and_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_descriptor() -> object:
        raise RuntimeError("raw dependency secret")

    monkeypatch.setattr(
        authority_module, "_canonical_openai_descriptor", fail_descriptor
    )
    with pytest.raises(SmokeExecutionRequestDependencyError) as raised:
        SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    assert raised.value.args == ("canonical smoke request construction failed",)
    _assert_isolated(raised.value)
    assert "raw dependency secret" not in repr(raised.value)


def test_invalid_input_precedes_descriptor_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def acquire():
        nonlocal calls
        calls += 1
        return OpenAIProviderAdapter.descriptor

    monkeypatch.setattr(authority_module, "_canonical_openai_descriptor", acquire)
    arguments = _valid_arguments()
    arguments["execution_request_id"] = " padded"
    with pytest.raises(SmokeExecutionRequestConfigurationError):
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    assert calls == 0


def test_valid_input_acquires_descriptor_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def acquire():
        nonlocal calls
        calls += 1
        return OpenAIProviderAdapter.descriptor

    monkeypatch.setattr(authority_module, "_canonical_openai_descriptor", acquire)
    result = SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    assert type(result) is ProviderExecutionRequestV2
    assert calls == 1


def test_returned_request_graph_contains_no_operational_authority() -> None:
    result = SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    rendered = json.dumps(result.model_dump(mode="json"), sort_keys=True).lower()
    for forbidden in (
        "api_key",
        "credential",
        "runtime",
        "executor",
        "transport",
        "sdk",
        "model",
    ):
        assert forbidden not in rendered


def test_final_request_is_defensively_reconstructed() -> None:
    result = SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    forged = result.model_copy(
        update={
            "request_envelope": result.request_envelope.model_copy(
                update={"fingerprint": "0" * 64}
            )
        }
    )
    with pytest.raises(ValidationError):
        ProviderExecutionRequestV2.model_validate(
            forged.model_dump(mode="python"), strict=True
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "plan-reference",
        "plan-identity",
        "plan-fingerprint",
        "draft-reference",
        "draft-fingerprint",
        "source-reference",
        "unit-collection",
        "unit-ordinal",
        "message-collection",
        "message-ordinal",
        "message-role",
        "message-content",
    ),
)
def test_full_copied_invalid_plan_matrix_stops_before_descriptor(
    mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_canonical_smoke_execution_plan()
    unit = plan.request_units[0]
    message = unit.messages[0]
    if mutation == "plan-reference":
        forged = plan.model_copy(update={"plan_reference": "foreign"})
    elif mutation == "plan-identity":
        forged = plan.model_copy(update={"plan_identity": "foreign"})
    elif mutation == "plan-fingerprint":
        forged = plan.model_copy(update={"plan_fingerprint": "0" * 64})
    elif mutation == "draft-reference":
        forged = plan.model_copy(update={"draft_reference": "foreign"})
    elif mutation == "draft-fingerprint":
        forged = plan.model_copy(update={"draft_fingerprint": "0" * 64})
    elif mutation == "source-reference":
        forged = plan.model_copy(
            update={
                "request_units": (
                    unit.model_copy(update={"source_request_reference": "foreign"}),
                )
            }
        )
    elif mutation == "unit-collection":
        forged = plan.model_copy(update={"request_units": ()})
    elif mutation == "unit-ordinal":
        forged = plan.model_copy(
            update={"request_units": (unit.model_copy(update={"ordinal": 1}),)}
        )
    elif mutation == "message-collection":
        forged = plan.model_copy(
            update={"request_units": (unit.model_copy(update={"messages": ()}),)}
        )
    else:
        field, value = {
            "message-ordinal": ("ordinal", 1),
            "message-role": ("role", "context"),
            "message-content": ("content", "SMOKE_OK"),
        }[mutation]
        forged_message = message.model_copy(update={field: value})
        forged = plan.model_copy(
            update={
                "request_units": (
                    unit.model_copy(update={"messages": (forged_message,)}),
                )
            }
        )
    calls = 0

    def acquire():
        nonlocal calls
        calls += 1
        return OpenAIProviderAdapter.descriptor

    monkeypatch.setattr(authority_module, "_canonical_openai_descriptor", acquire)
    with pytest.raises(SmokeExecutionRequestConfigurationError):
        SmokeProviderExecutionRequestAuthorityV2().construct(
            **{**_valid_arguments(), "execution_plan": forged}
        )
    assert calls == 0


def test_strict_subclass_and_numeric_timeout_inputs_are_rejected() -> None:
    class TextSubclass(str):
        pass

    class DateSubclass(datetime):
        pass

    class IntSubclass(int):
        pass

    class FloatSubclass(float):
        pass

    invalid = (
        ("execution_request_id", TextSubclass("request")),
        ("requested_at", DateSubclass(2026, 8, 2, tzinfo=UTC)),
        ("timeout_seconds", IntSubclass(1)),
        ("timeout_seconds", FloatSubclass(1.0)),
        ("timeout_seconds", Decimal(1)),
        ("timeout_seconds", Fraction(1, 2)),
    )
    for field, value in invalid:
        with pytest.raises(SmokeExecutionRequestConfigurationError):
            SmokeProviderExecutionRequestAuthorityV2().construct(
                **{**_valid_arguments(), field: value}
            )


def test_frozen_envelope_builder_is_used_once(monkeypatch: pytest.MonkeyPatch) -> None:
    original = authority_module.build_provider_request_envelope
    calls = 0

    def tracked(intent, descriptor):
        nonlocal calls
        calls += 1
        return original(intent, descriptor)

    monkeypatch.setattr(authority_module, "build_provider_request_envelope", tracked)
    result = SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    assert type(result) is ProviderExecutionRequestV2
    assert calls == 1


def test_dependency_traceback_retains_no_partial_dtos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_envelope(*args: object) -> object:
        del args
        raise RuntimeError("builder secret")

    monkeypatch.setattr(
        authority_module, "build_provider_request_envelope", fail_envelope
    )
    with pytest.raises(SmokeExecutionRequestDependencyError) as raised:
        SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    _assert_isolated(raised.value)
    traceback = raised.value.__traceback__
    forbidden_names = {
        "ProviderDescriptorV2",
        "ProviderRequestIntentV2",
        "ProviderRequestEnvelopeV2",
        "ExecutionContextV2",
        "TimeoutPolicyV2",
        "ProviderExecutionRequestV2",
    }
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").startswith(
            "pastila_scout.provider_smoke_request_authority_v2"
        ):
            assert (
                not {
                    value.__class__.__name__
                    for value in traceback.tb_frame.f_locals.values()
                }
                & forbidden_names
            )
        traceback = traceback.tb_next
