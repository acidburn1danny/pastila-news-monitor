from __future__ import annotations

import ast
import hashlib
import json
import math
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionCancelledError,
    ExecutionConfigurationError,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ExecutionTimeoutError,
    InternalExecutionError,
    ProviderExecutionBoundaryError,
    ProviderExecutionError,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    ProviderExecutorV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderCapabilityV2,
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderOutputInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    build_provider_descriptor,
    build_provider_request_envelope,
    request_envelope_fingerprint,
    request_envelope_identity,
    validate_provider_descriptor,
    validate_provider_request_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_v2"
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"


def _intent() -> ProviderRequestIntentV2:
    return ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:contract",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:contract",
        draft_fingerprint=ZERO,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference="source-request:contract",
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(
                        role="generation", content="Contract content", ordinal=0
                    ),
                ),
            ),
        ),
    )


def _authority():
    descriptor = build_provider_descriptor(
        provider_id="contract-provider",
        display_name="Contract Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    intent = _intent()
    return descriptor, build_provider_request_envelope(intent, descriptor)


def _context() -> ExecutionContextV2:
    return ExecutionContextV2(
        request_id="request-contract",
        requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        cancellation=CancellationTokenV2(cancellation_requested=False),
        metadata=(("purpose", "contract-test"),),
    )


def _execution_request(
    descriptor=None,
    envelope=None,
    *,
    intent=None,
    context=None,
    timeout=None,
) -> ProviderExecutionRequestV2:
    authority_descriptor, authority_envelope = _authority()
    return ProviderExecutionRequestV2(
        provider=descriptor or authority_descriptor,
        request_intent=intent or _intent(),
        request_envelope=envelope or authority_envelope,
        context=context or _context(),
        timeout_policy=timeout or TimeoutPolicyV2(timeout_seconds=20),
    )


def test_execution_request_contract_is_immutable_and_authoritative() -> None:
    descriptor, envelope = _authority()
    request = ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=_intent(),
        request_envelope=envelope,
        context=_context(),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
    )

    assert request.provider == descriptor
    assert request.provider is not descriptor
    assert request.request_intent == _intent()
    assert request.request_envelope == envelope
    assert request.request_envelope is not envelope
    assert request.context.cancellation.cancellation_requested is False
    with pytest.raises(ValidationError):
        request.timeout_policy = TimeoutPolicyV2(timeout_seconds=10)  # type: ignore[misc]


def test_execution_request_rejects_cross_provider_authority() -> None:
    descriptor, envelope = _authority()
    foreign = build_provider_descriptor(
        provider_id="foreign-provider",
        display_name="Foreign Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )

    with pytest.raises(ValidationError, match="invalid request envelope authority"):
        ProviderExecutionRequestV2(
            provider=foreign,
            request_intent=_intent(),
            request_envelope=envelope,
            context=_context(),
            timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
        )
    assert descriptor.provider_id == "contract-provider"


@pytest.mark.parametrize("field", ("identity", "fingerprint", "adapter_identity"))
def test_execution_request_rejects_intrinsically_forged_descriptor(field: str) -> None:
    descriptor, envelope = _authority()
    replacement = f"scout:forged:{'f' * 64}" if field != "fingerprint" else "e" * 64
    forged = descriptor.model_copy(update={field: replacement})

    assert validate_provider_descriptor(forged)
    with pytest.raises(ValidationError, match="invalid provider descriptor authority"):
        _execution_request(forged, envelope)


@pytest.mark.parametrize(
    "field,replacement",
    (
        ("identity", f"scout:forged:{'f' * 64}"),
        ("fingerprint", "e" * 64),
        ("descriptor_identity", f"scout:forged:{'f' * 64}"),
        ("descriptor_fingerprint", "e" * 64),
        ("execution_plan_reference", "execution-plan:forged"),
    ),
)
def test_execution_request_rejects_intrinsically_forged_envelope(
    field: str, replacement: str
) -> None:
    descriptor, envelope = _authority()
    forged = envelope.model_copy(update={field: replacement})

    with pytest.raises(ValidationError, match="invalid request envelope authority"):
        _execution_request(descriptor, forged)


def test_execution_request_rejects_consistently_forged_authority_pair() -> None:
    descriptor, envelope = _authority()
    forged_identity = f"scout:forged:{'f' * 64}"
    forged_fingerprint = "e" * 64
    forged_descriptor = descriptor.model_copy(
        update={"identity": forged_identity, "fingerprint": forged_fingerprint}
    )
    forged_envelope = envelope.model_copy(
        update={
            "descriptor_identity": forged_identity,
            "descriptor_fingerprint": forged_fingerprint,
        }
    )

    assert validate_provider_descriptor(forged_descriptor)
    assert validate_provider_request_envelope(
        forged_envelope,
        ProviderRequestIntentV2(
            execution_plan_reference="execution-plan:contract",
            execution_plan_identity=IDENTITY,
            execution_plan_fingerprint=ZERO,
            draft_reference="draft:contract",
            draft_fingerprint=ZERO,
            request_units=(
                ProviderRequestUnitInputV2(
                    source_request_reference="source-request:contract",
                    ordinal=0,
                    messages=(
                        ProviderMessageInputV2(
                            role="generation",
                            content="Contract content",
                            ordinal=0,
                        ),
                    ),
                ),
            ),
        ),
        forged_descriptor,
    )
    before = (forged_descriptor.model_dump(), forged_envelope.model_dump())
    messages = []
    for _ in range(2):
        with pytest.raises(ValidationError) as captured:
            _execution_request(forged_descriptor, forged_envelope)
        messages.append(str(captured.value))
    assert messages[0] == messages[1]
    assert "invalid provider descriptor authority" in messages[0]
    assert before == (forged_descriptor.model_dump(), forged_envelope.model_dump())


def test_execution_request_rejects_independently_valid_foreign_authority() -> None:
    descriptor, _ = _authority()
    foreign = build_provider_descriptor(
        provider_id="foreign-provider",
        display_name="Foreign Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=f"scout:foreign-adapter:{'a' * 64}",
    )
    intent = ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:foreign",
        execution_plan_identity=f"scout:foreign-plan:{'b' * 64}",
        execution_plan_fingerprint="c" * 64,
        draft_reference="draft:foreign",
        draft_fingerprint="d" * 64,
        request_units=(),
    )
    foreign_envelope = build_provider_request_envelope(intent, foreign)

    assert not validate_provider_descriptor(descriptor)
    assert not validate_provider_descriptor(foreign)
    with pytest.raises(ValidationError, match="invalid request envelope authority"):
        _execution_request(descriptor, foreign_envelope)


def test_execution_request_rejects_independently_valid_cross_adapter_authority() -> (
    None
):
    descriptor, _ = _authority()
    foreign_adapter = build_provider_descriptor(
        provider_id="contract-provider",
        display_name="Contract Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=f"scout:foreign-adapter:{'a' * 64}",
    )
    intent = ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:adapter",
        execution_plan_identity=f"scout:adapter-plan:{'b' * 64}",
        execution_plan_fingerprint="c" * 64,
        draft_reference="draft:adapter",
        draft_fingerprint="d" * 64,
        request_units=(),
    )
    foreign_envelope = build_provider_request_envelope(intent, foreign_adapter)

    with pytest.raises(ValidationError, match="invalid request envelope authority"):
        _execution_request(descriptor, foreign_envelope)


def test_execution_request_rejects_malformed_copied_descriptor_fields() -> None:
    descriptor, envelope = _authority()
    for update in (
        {"provider_id": "INVALID PROVIDER"},
        {"adapter_identity": "not-an-identity"},
    ):
        forged = descriptor.model_copy(update=update)
        assert validate_provider_descriptor(forged)
        with pytest.raises(
            ValidationError, match="invalid provider descriptor authority"
        ):
            _execution_request(forged, envelope)


def test_execution_request_requires_independent_request_intent() -> None:
    descriptor, envelope = _authority()
    with pytest.raises(ValidationError):
        ProviderExecutionRequestV2(
            provider=descriptor,
            request_envelope=envelope,
            context=_context(),
            timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
        )


def test_resealed_envelope_forgery_is_rejected_against_independent_intent() -> None:
    descriptor, envelope = _authority()
    forged = envelope.model_copy(
        update={"execution_plan_reference": "execution-plan:forged"}
    )
    forged = forged.model_copy(update={"identity": request_envelope_identity(forged)})
    forged = forged.model_copy(
        update={"fingerprint": request_envelope_fingerprint(forged)}
    )
    before = forged.model_dump()
    messages = []
    for _ in range(2):
        with pytest.raises(
            ValidationError, match="invalid request envelope authority"
        ) as captured:
            _execution_request(descriptor, forged, intent=_intent())
        messages.append(str(captured.value))
    assert messages[0] == messages[1]
    assert "ProviderDescriptorV2(" not in messages[0]
    assert forged.model_dump() == before


def test_forged_intent_is_rejected_against_valid_envelope() -> None:
    descriptor, envelope = _authority()
    forged = _intent().model_copy(
        update={"execution_plan_reference": "execution-plan:forged"}
    )

    with pytest.raises(ValidationError, match="invalid request envelope authority"):
        _execution_request(descriptor, envelope, intent=forged)


@pytest.mark.parametrize(
    "update",
    (
        {"execution_plan_reference": ""},
        {"execution_plan_identity": "invalid"},
        {"execution_plan_fingerprint": "invalid"},
        {"draft_reference": ""},
        {"draft_fingerprint": "invalid"},
        {"request_units": (("invalid",),)},
    ),
)
def test_intrinsically_invalid_copied_intent_is_rejected(update) -> None:
    forged = _intent().model_copy(update=update)

    with pytest.raises(ValidationError, match="invalid request intent authority"):
        _execution_request(intent=forged)


def test_context_and_timeout_are_descriptive_only_and_validated() -> None:
    with pytest.raises(ValidationError, match="greater than 0"):
        TimeoutPolicyV2(timeout_seconds=0)
    with pytest.raises(ValidationError, match="timezone"):
        ExecutionContextV2(
            request_id="request-naive",
            requested_at=datetime(2026, 7, 31, 12),  # noqa: DTZ001
        )
    with pytest.raises(ValidationError, match="unique"):
        ExecutionContextV2(
            request_id="request-duplicate-metadata",
            requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
            metadata=(("key", "one"), ("key", "two")),
        )


@pytest.mark.parametrize(
    "metadata",
    (
        (("key", ""),),
        (("", "value"),),
        ((" ", "value"),),
        (("key", " "),),
        (("key", "value"), ("key", "other")),
        (("key",),),
        (("key", "value", "extra"),),
        ((1, "value"),),
        (("key", 1),),
    ),
)
def test_metadata_rejects_malformed_values_without_raw_errors(metadata) -> None:
    messages = []
    for _ in range(2):
        with pytest.raises(ValidationError) as captured:
            ExecutionContextV2(
                request_id="request-metadata",
                requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
                metadata=metadata,
            )
        messages.append(str(captured.value))
    assert messages[0] == messages[1]


def test_metadata_accepts_one_character_pairs_and_copies_mutable_input() -> None:
    supplied = [["k", "x"]]
    context = ExecutionContextV2(
        request_id="request-metadata",
        requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        metadata=supplied,
    )
    supplied[0][1] = "changed"
    supplied.append(["other", "value"])

    assert context.metadata == (("k", "x"),)
    assert isinstance(context.metadata, tuple)
    assert isinstance(context.metadata[0], tuple)


@pytest.mark.parametrize(
    "value",
    (0, -1, math.nan, math.inf, -math.inf, True, False, "1", ""),
)
def test_timeout_rejects_nonpositive_nonfinite_and_coercive_values(value) -> None:
    messages = []
    for _ in range(2):
        with pytest.raises(ValidationError) as captured:
            TimeoutPolicyV2(timeout_seconds=value)
        messages.append(str(captured.value))
    assert messages[0] == messages[1]


def test_timeout_accepts_only_supported_positive_numeric_types() -> None:
    assert TimeoutPolicyV2(timeout_seconds=1).timeout_seconds == 1
    assert TimeoutPolicyV2(timeout_seconds=1.5).timeout_seconds == 1.5


def test_timeout_rejects_arbitrary_numeric_like_objects() -> None:
    class NumericLike:
        def __float__(self) -> float:
            return 1.0

    with pytest.raises(ValidationError):
        TimeoutPolicyV2(timeout_seconds=NumericLike())


@pytest.mark.parametrize("value", ("", " ", " padded ", 1, True))
def test_context_rejects_invalid_request_identifiers(value) -> None:
    with pytest.raises(ValidationError):
        ExecutionContextV2(
            request_id=value,
            requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        )


@pytest.mark.parametrize("value", ("", " ", " padded ", 1, True))
def test_result_rejects_invalid_failure_codes(value) -> None:
    with pytest.raises(ValidationError):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=IDENTITY,
            outcome=ExecutionOutcomeV2.TIMEOUT,
            finished_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
            failure_code=value,
        )


@pytest.mark.parametrize(
    "field", ("request_id", "provider_id", "request_envelope_identity")
)
@pytest.mark.parametrize("value", ("", " ", " padded ", 1, True))
def test_result_rejects_invalid_identifiers(field: str, value) -> None:
    values = {
        "request_id": "request-contract",
        "provider_id": "contract-provider",
        "request_envelope_identity": IDENTITY,
        "outcome": ExecutionOutcomeV2.TIMEOUT,
        "finished_at": datetime(2026, 7, 31, 12, tzinfo=UTC),
        "failure_code": "timeout",
    }
    values[field] = value
    with pytest.raises(ValidationError):
        ProviderExecutionResultV2(**values)


@pytest.mark.parametrize("value", ("timeout", "unknown", 1, None))
def test_execution_outcome_requires_strict_enum_instance(value) -> None:
    with pytest.raises(ValidationError):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=IDENTITY,
            outcome=value,
            finished_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
            failure_code="timeout",
        )


@pytest.mark.parametrize("value", ("yes", "false", 1, 0, None))
def test_cancellation_requires_exact_boolean(value) -> None:
    with pytest.raises(ValidationError):
        CancellationTokenV2(cancellation_requested=value)


def test_cancellation_accepts_exact_boolean_states() -> None:
    assert (
        CancellationTokenV2(cancellation_requested=True).cancellation_requested is True
    )
    assert (
        CancellationTokenV2(cancellation_requested=False).cancellation_requested
        is False
    )


def test_cancellation_does_not_invoke_custom_boolean_conversion() -> None:
    class Truthy:
        invoked = False

        def __bool__(self) -> bool:
            self.invoked = True
            return True

    supplied = Truthy()
    with pytest.raises(ValidationError):
        CancellationTokenV2(cancellation_requested=supplied)
    assert supplied.invoked is False


@pytest.mark.parametrize("value", (-1, 0, math.nan, math.inf, -math.inf, True, "1"))
def test_copied_invalid_timeout_is_rejected_when_nested(value) -> None:
    forged = TimeoutPolicyV2(timeout_seconds=20).model_copy(
        update={"timeout_seconds": value}
    )
    with pytest.raises(ValidationError, match="invalid timeout policy"):
        _execution_request(timeout=forged)


@pytest.mark.parametrize(
    "update",
    (
        {"requested_at": datetime(2026, 7, 31, 12)},  # noqa: DTZ001
        {"request_id": ""},
        {"request_id": " "},
        {"request_id": " padded "},
        {"metadata": (("key", ""),)},
        {"metadata": (("key", " "),)},
        {"metadata": (("key", "value"), ("key", "other"))},
        {"metadata": ((1, "value"),)},
    ),
)
def test_copied_invalid_context_is_rejected_when_nested(update) -> None:
    forged = _context().model_copy(update=update)
    before = forged.model_dump(warnings=False)
    messages = []
    for _ in range(2):
        with pytest.raises(
            ValidationError, match="invalid execution context"
        ) as captured:
            _execution_request(context=forged)
        messages.append(str(captured.value))
    assert messages[0] == messages[1]
    assert "ExecutionContextV2(" not in messages[0]
    assert forged.model_dump(warnings=False) == before


@pytest.mark.parametrize("value", ("yes", "false", 1, 0, None))
def test_copied_invalid_cancellation_is_rejected_when_nested(value) -> None:
    forged_token = CancellationTokenV2().model_copy(
        update={"cancellation_requested": value}
    )
    forged_context = _context().model_copy(update={"cancellation": forged_token})
    with pytest.raises(ValidationError, match="invalid execution context"):
        _execution_request(context=forged_context)


def test_execution_completion_remains_independent_of_provider_failure_semantics() -> (
    None
):
    _, envelope = _authority()
    projection = ProviderResultProjectionV2(
        status=ProviderResultStatusV2.FAILED,
        outputs=(),
        failure_code="provider-semantic-failure",
    )

    result = ProviderExecutionResultV2(
        request_id="request-contract",
        provider_id="contract-provider",
        request_envelope_identity=envelope.identity,
        outcome=ExecutionOutcomeV2.COMPLETED,
        finished_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        provider_result=projection,
    )

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.provider_result.status is ProviderResultStatusV2.FAILED


def test_copied_invalid_projection_is_rejected_at_result_boundary() -> None:
    valid = ProviderResultProjectionV2(
        status=ProviderResultStatusV2.SUCCESS,
        outputs=(
            ProviderOutputInputV2(
                source_request_reference="source-request:contract",
                ordinal=0,
                generated_text="Generated contract output",
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            ),
        ),
    )
    forged = valid.model_copy(update={"outputs": ()})
    with pytest.raises(ValidationError, match="invalid provider result projection"):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=IDENTITY,
            outcome=ExecutionOutcomeV2.COMPLETED,
            finished_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
            provider_result=forged,
        )


def test_copied_contradictory_result_is_revalidated() -> None:
    valid = ProviderExecutionResultV2(
        request_id="request-contract",
        provider_id="contract-provider",
        request_envelope_identity=IDENTITY,
        outcome=ExecutionOutcomeV2.TIMEOUT,
        finished_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        failure_code="timeout",
    )
    forged = valid.model_copy(update={"failure_code": None})

    with pytest.raises(ValidationError, match="requires a failure code"):
        ProviderExecutionResultV2.model_validate(forged)


def test_completed_execution_requires_exact_provider_projection() -> None:
    _, envelope = _authority()
    projection = ProviderResultProjectionV2(
        status=ProviderResultStatusV2.SUCCESS,
        outputs=(
            ProviderOutputInputV2(
                source_request_reference="source-request:contract",
                ordinal=0,
                generated_text="Generated contract output",
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            ),
        ),
    )
    result = ProviderExecutionResultV2(
        request_id="request-contract",
        provider_id="contract-provider",
        request_envelope_identity=envelope.identity,
        outcome=ExecutionOutcomeV2.COMPLETED,
        finished_at=datetime(2026, 7, 31, 12, 0, 1, tzinfo=UTC),
        provider_result=projection,
    )

    assert result.provider_result == projection
    assert result.provider_result is not projection
    with pytest.raises(ValidationError, match="requires a provider result"):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=envelope.identity,
            outcome=ExecutionOutcomeV2.COMPLETED,
            finished_at=datetime(2026, 7, 31, 12, 0, 1, tzinfo=UTC),
        )
    with pytest.raises(ValidationError, match="forbids failure details"):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=envelope.identity,
            outcome=ExecutionOutcomeV2.COMPLETED,
            finished_at=datetime(2026, 7, 31, 12, 0, 1, tzinfo=UTC),
            provider_result=projection,
            failure_code="contradiction",
        )


@pytest.mark.parametrize(
    "outcome",
    (
        ExecutionOutcomeV2.PROVIDER_FAILURE,
        ExecutionOutcomeV2.TIMEOUT,
        ExecutionOutcomeV2.CANCELLED,
        ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
    ),
)
def test_noncompleted_execution_requires_failure_without_provider_result(
    outcome: ExecutionOutcomeV2,
) -> None:
    _, envelope = _authority()
    result = ProviderExecutionResultV2(
        request_id="request-contract",
        provider_id="contract-provider",
        request_envelope_identity=envelope.identity,
        outcome=outcome,
        finished_at=datetime(2026, 7, 31, 12, 0, 1, tzinfo=UTC),
        failure_code="execution-unavailable",
    )

    assert result.provider_result is None
    with pytest.raises(ValidationError, match="requires a failure code"):
        ProviderExecutionResultV2.model_validate(
            result.model_copy(update={"failure_code": None}).model_dump()
        )
    projection = ProviderResultProjectionV2(
        status=ProviderResultStatusV2.FAILED,
        outputs=(),
        failure_code="provider-semantic-failure",
    )
    with pytest.raises(ValidationError, match="forbids a provider result"):
        ProviderExecutionResultV2(
            request_id="request-contract",
            provider_id="contract-provider",
            request_envelope_identity=envelope.identity,
            outcome=outcome,
            finished_at=datetime(2026, 7, 31, 12, 0, 1, tzinfo=UTC),
            provider_result=projection,
            failure_code="execution-failure",
        )


def test_execution_error_hierarchy_is_provider_neutral() -> None:
    errors = (
        ExecutionTimeoutError,
        ExecutionCancelledError,
        ProviderExecutionError,
        InternalExecutionError,
        ExecutionConfigurationError,
    )

    assert all(issubclass(error, ProviderExecutionBoundaryError) for error in errors)
    assert all("openai" not in error.__name__.lower() for error in errors)


def test_executor_is_a_contract_without_implementation() -> None:
    assert ProviderExecutorV2._is_protocol is True
    assert set(ProviderExecutorV2.__dict__) & {"execute"} == {"execute"}
    assert ProviderExecutorV2.__dict__["execute"].__code__.co_code


def test_public_exports_are_contracts_only() -> None:
    import pastila_scout.provider_execution_v2 as package

    assert package.__all__ == (
        "CancellationTokenV2",
        "ExecutionCancelledError",
        "ExecutionConfigurationError",
        "ExecutionContextV2",
        "ExecutionOutcomeV2",
        "ExecutionTimeoutError",
        "InternalExecutionError",
        "ProviderExecutionBoundaryError",
        "ProviderExecutionError",
        "ProviderExecutionRequestV2",
        "ProviderExecutionResultV2",
        "ProviderExecutorV2",
        "TimeoutPolicyV2",
    )


def test_execution_package_import_is_isolated() -> None:
    code = (
        "import importlib,json,sys;"
        "importlib.import_module('pastila_scout.provider_execution_v2');"
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
    loaded = tuple(json.loads(completed.stdout))

    assert not any("provider_adapters_v2" in item for item in loaded)
    assert "pastila_scout.provider_composition_v2" not in loaded
    assert not any("editor.script_composer" in item for item in loaded)


def test_dependency_direction_and_explicit_non_goals() -> None:
    forbidden_imports = {
        "aiohttp",
        "asyncio",
        "httpx",
        "logging",
        "openai",
        "requests",
        "sqlite3",
    }
    forbidden_names = {
        "API_KEY",
        "backoff",
        "credential",
        "environment",
        "retry",
        "stream",
        "telemetry",
    }

    for path in PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert not any(item.split(".", 1)[0] in forbidden_imports for item in imports)
        assert "provider_adapters_v2" not in source
        assert "provider_composition_v2" not in source
        assert not any(name.lower() in source.lower() for name in forbidden_names)


def test_phase_71_integrity_manifest_remains_exact() -> None:
    manifest = (
        ROOT / "docs" / "editorial-script-composer" / "Phase7_1_Revision8_Integrity.md"
    ).read_text(encoding="utf-8")
    rows = []
    for line in manifest.splitlines():
        if line.startswith("| `src/"):
            path, digest = tuple(
                part.strip().strip("`") for part in line.split("|")[1:3]
            )
            rows.append((path, digest))

    assert len(rows) == 15
    assert all(
        hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
        for path, digest in rows
    )
