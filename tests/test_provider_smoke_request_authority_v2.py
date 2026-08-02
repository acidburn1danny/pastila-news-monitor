from __future__ import annotations

import copy
import gc
import inspect
import json
import pickle
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.provider_smoke_request_authority_v2 as authority_package
import pastila_scout.provider_smoke_request_authority_v2.interface as authority_interface
from pastila_scout.provider_smoke_request_authority_v2 import (
    SmokeExecutionPlanV2,
    SmokeExecutionRequestAuthorityError,
    SmokeExecutionRequestConfigurationError,
    SmokeExecutionRequestDependencyError,
    SmokeProviderExecutionRequestAuthorityV2,
    build_canonical_smoke_execution_plan,
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


@pytest.mark.parametrize("timeout", (1, 1.5))
def test_valid_inputs_reach_only_fixed_non_operational_failure(timeout: object) -> None:
    arguments = _valid_arguments()
    arguments["timeout_seconds"] = timeout
    with pytest.raises(SmokeExecutionRequestDependencyError) as raised:
        SmokeProviderExecutionRequestAuthorityV2().construct(**arguments)
    assert raised.value.args == (
        "canonical smoke request construction is not operational",
    )
    _assert_isolated(raised.value)


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
        with pytest.raises(SmokeExecutionRequestDependencyError) as raised:
            SmokeProviderExecutionRequestAuthorityV2().construct(**_valid_arguments())
    _assert_isolated(raised.value)
    assert raised.value.__context__ is not caller


def test_traceback_contains_no_authority_inputs() -> None:
    plan = build_canonical_smoke_execution_plan()
    authority = SmokeProviderExecutionRequestAuthorityV2()
    with pytest.raises(SmokeExecutionRequestDependencyError) as raised:
        authority.construct(
            execution_plan=plan,
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


def test_package_has_no_operational_imports_or_provider_dto_construction() -> None:
    package = ROOT / "src" / "pastila_scout" / "provider_smoke_request_authority_v2"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in package.glob("*.py")
    )
    for forbidden in (
        "OPENAI_API_KEY",
        "ProviderExecutionRequestV2(",
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
    with pytest.raises(SmokeExecutionRequestDependencyError):
        authority.construct(**_valid_arguments())
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
