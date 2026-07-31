from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import pastila_scout.provider_execution_openai_v2 as public_api
from pastila_scout.editor.script_composer.extracted_result_validation import (
    build_openai_extracted_execution_result,
    validate_openai_extracted_execution_result,
)
from pastila_scout.editor.script_composer.openai_result_validation import (
    build_openai_provider_execution_result,
    validate_openai_provider_execution_result,
)
from pastila_scout.editor.script_composer.provider_mapping_validation import (
    build_draft_provider_request_plan,
    validate_draft_provider_request_plan,
)
from pastila_scout.editor.script_composer.provider_result_validation import (
    build_provider_execution_result,
    validate_provider_execution_result,
)
from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIConfigurationError,
    OpenAIExecutionBoundaryError,
    OpenAIExecutionClientV2,
    OpenAIExecutionConfigV2,
    OpenAIExecutionMessageV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
    OpenAIRequestMappingError,
    OpenAIResponseMappingError,
    build_openai_execution_request,
    project_openai_execution_response,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderCapabilityV2,
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultStatusV2,
    build_provider_descriptor,
    build_provider_request_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_openai_v2"
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"
FINISHED_AT = datetime(2026, 7, 31, 12, tzinfo=UTC)
EXPECTED_EXPORTS = {
    "OpenAIClientContractError",
    "OpenAIClientErrorCategoryV2",
    "OpenAIConfigurationError",
    "OpenAIExecutionBoundaryError",
    "OpenAIExecutionClientV2",
    "OpenAIExecutionConfigV2",
    "OpenAIExecutionMessageV2",
    "OpenAIExecutionOutputV2",
    "OpenAIExecutionRequestV2",
    "OpenAIExecutionResponseV2",
    "OpenAIProviderExecutorV2",
    "OpenAIRequestMappingError",
    "OpenAIResponseMappingError",
    "build_openai_execution_request",
    "project_openai_execution_response",
}


def _intent(*, units: int = 2) -> ProviderRequestIntentV2:
    return ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:openai-boundary",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:openai-boundary",
        draft_fingerprint=ZERO,
        request_units=tuple(
            ProviderRequestUnitInputV2(
                source_request_reference=f"source-request:{ordinal}",
                ordinal=ordinal,
                messages=(
                    ProviderMessageInputV2(
                        role="instruction" if ordinal == 0 else "generation",
                        content=f"Conținut confirmat {ordinal}",
                        ordinal=0,
                    ),
                ),
            )
            for ordinal in range(units)
        ),
    )


def _request(*, provider=None, units: int = 2) -> ProviderExecutionRequestV2:
    descriptor = provider or OpenAIProviderAdapter.descriptor
    intent = _intent(units=units)
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id="request-openai-boundary",
            requested_at=FINISHED_AT,
            cancellation=CancellationTokenV2(cancellation_requested=False),
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
    )


def _output(ordinal: int, *, reason=ProviderFinishReasonV2.COMPLETED):
    return OpenAIExecutionOutputV2(
        ordinal=ordinal,
        generated_text=f"Rezultat verificat {ordinal}",
        finish_reason=reason,
    )


def _response(
    *,
    status=ProviderResultStatusV2.SUCCESS,
    outputs=None,
    category=None,
    failure_code=None,
) -> OpenAIExecutionResponseV2:
    return OpenAIExecutionResponseV2(
        provider_request_id="provider-request-1",
        model="gpt-contract-model",
        finished_at=FINISHED_AT,
        status=status,
        outputs=(
            tuple(_output(index) for index in range(2)) if outputs is None else outputs
        ),
        failure_category=category,
        failure_code=failure_code,
    )


def test_public_contract_is_exact_and_protocol_has_no_implementation() -> None:
    assert set(public_api.__all__) == EXPECTED_EXPORTS
    assert len(public_api.__all__) == 15
    assert (
        getattr(OpenAIExecutionClientV2.complete, "__isabstractmethod__", False)
        is False
    )
    assert OpenAIExecutionClientV2.__dict__["complete"].__code__.co_consts == (None,)


def test_config_is_strict_immutable_and_contains_no_transport_or_secret_fields() -> (
    None
):
    config = OpenAIExecutionConfigV2(
        model="gpt-contract-model", temperature=0.25, max_output_tokens=400
    )
    assert config.stop_sequences == ()
    assert set(OpenAIExecutionConfigV2.model_fields) == {
        "model",
        "temperature",
        "max_output_tokens",
        "stop_sequences",
    }
    with pytest.raises(ValidationError):
        config.model = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        OpenAIExecutionConfigV2(model="gpt", api_key="secret")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "changes",
    (
        {"model": " "},
        {"model": " padded "},
        {"temperature": True},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"temperature": 3},
        {"max_output_tokens": True},
        {"max_output_tokens": 0},
        {"stop_sequences": ("",)},
        {"stop_sequences": ("stop", "stop")},
    ),
)
def test_config_rejects_invalid_generation_controls(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        OpenAIExecutionConfigV2.model_validate(
            {"model": "gpt-contract-model", **changes}
        )


def test_request_mapping_is_deterministic_ordered_and_non_mutating() -> None:
    authority = _request()
    before = authority.model_dump(mode="json")
    config = OpenAIExecutionConfigV2(model="gpt-contract-model", temperature=0)

    first = build_openai_execution_request(authority, config)
    second = build_openai_execution_request(authority, config)

    assert first == second
    assert first.provider_id == "openai"
    assert tuple(message.role for message in first.messages) == ("system", "user")
    assert tuple(message.ordinal for message in first.messages) == (0, 1)
    assert first.messages[0].content == "Conținut confirmat 0"
    assert authority.model_dump(mode="json") == before


@pytest.mark.parametrize("provider_id", ("claude", "gemini", "ollama"))
def test_request_mapping_rejects_every_non_openai_authority(provider_id: str) -> None:
    descriptor = build_provider_descriptor(
        provider_id=provider_id,
        display_name=provider_id.title(),
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    with pytest.raises(OpenAIRequestMappingError, match="OpenAI authority"):
        build_openai_execution_request(
            _request(provider=descriptor), OpenAIExecutionConfigV2(model="gpt-model")
        )


def test_request_mapping_revalidates_copied_authority_and_config() -> None:
    authority = _request().model_copy(
        update={
            "provider": OpenAIProviderAdapter.descriptor.model_copy(
                update={"fingerprint": "f" * 64}
            )
        }
    )
    with pytest.raises(OpenAIRequestMappingError, match="invalid provider execution"):
        build_openai_execution_request(authority, OpenAIExecutionConfigV2(model="gpt"))

    forged = OpenAIExecutionConfigV2(model="gpt").model_copy(update={"model": " "})
    with pytest.raises(OpenAIConfigurationError):
        build_openai_execution_request(_request(), forged)


def test_request_dto_rejects_invalid_order_nested_copy_and_transport_fields() -> None:
    message = OpenAIExecutionMessageV2(role="user", content="valid", ordinal=0)
    forged = message.model_copy(update={"content": " "})
    base = {
        "execution_request_id": "request",
        "request_envelope_identity": IDENTITY,
        "model": "gpt-model",
        "messages": (forged,),
        "timeout_seconds": 20,
        "cancellation_requested": False,
    }
    with pytest.raises(ValidationError):
        OpenAIExecutionRequestV2(**base)
    with pytest.raises(ValidationError):
        OpenAIExecutionRequestV2(**{**base, "messages": (message,), "endpoint": "x"})
    with pytest.raises(ValidationError):
        OpenAIExecutionRequestV2(
            **{**base, "messages": (message.model_copy(update={"ordinal": 1}),)}
        )


def _direct_openai_request_payload() -> dict[str, object]:
    return build_openai_execution_request(
        _request(), OpenAIExecutionConfigV2(model="gpt-model")
    ).model_dump(mode="python")


@pytest.mark.parametrize(
    "stop_sequences",
    ((), ("stop",), ("first", "second"), ["first", "second"]),
)
def test_direct_request_accepts_valid_stop_sequences_in_caller_order(
    stop_sequences,
) -> None:
    value = OpenAIExecutionRequestV2(
        **{**_direct_openai_request_payload(), "stop_sequences": stop_sequences}
    )
    assert value.stop_sequences == tuple(stop_sequences)


@pytest.mark.parametrize(
    "stop_sequences",
    (
        ("",),
        (" ",),
        (" leading",),
        ("trailing ",),
        ("duplicate", "duplicate"),
        (1,),
        (True,),
        (b"bytes",),
    ),
)
def test_config_and_direct_request_reject_identical_invalid_stop_sequences(
    stop_sequences,
) -> None:
    messages = []
    for model in (OpenAIExecutionConfigV2, OpenAIExecutionRequestV2):
        payload = (
            {"model": "gpt-model", "stop_sequences": stop_sequences}
            if model is OpenAIExecutionConfigV2
            else {
                **_direct_openai_request_payload(),
                "stop_sequences": stop_sequences,
            }
        )
        for _ in range(2):
            with pytest.raises(ValidationError) as captured:
                model.model_validate(payload)
            messages.append(str(captured.value))
    assert messages[0] == messages[1]
    assert messages[2] == messages[3]


def test_request_defensively_copies_mutable_stop_sequences() -> None:
    caller = ["first", "second"]
    value = OpenAIExecutionRequestV2(
        **{**_direct_openai_request_payload(), "stop_sequences": caller}
    )
    caller.append("third")
    assert value.stop_sequences == ("first", "second")


@pytest.mark.parametrize("stop_sequences", (("",), ("duplicate", "duplicate")))
def test_copied_request_with_invalid_stop_sequences_is_rejected_on_reconstruction(
    stop_sequences,
) -> None:
    valid = OpenAIExecutionRequestV2.model_validate(_direct_openai_request_payload())
    copied = valid.model_copy(update={"stop_sequences": stop_sequences})
    before = copied.model_dump(mode="json")

    for _ in range(2):
        with pytest.raises(ValidationError, match="stop sequences"):
            OpenAIExecutionRequestV2.model_validate(copied)
    assert copied.model_dump(mode="json") == before


def test_message_and_request_scalars_are_strict_and_ordinals_are_unique() -> None:
    with pytest.raises(ValidationError):
        OpenAIExecutionMessageV2(role="tool", content="valid", ordinal=0)
    with pytest.raises(ValidationError):
        OpenAIExecutionMessageV2(role="user", content=" ", ordinal=0)
    messages = (
        OpenAIExecutionMessageV2(role="user", content="one", ordinal=0),
        OpenAIExecutionMessageV2(role="user", content="two", ordinal=0),
    )
    with pytest.raises(ValidationError, match="ordinals"):
        OpenAIExecutionRequestV2(
            execution_request_id="request",
            request_envelope_identity=IDENTITY,
            model="gpt-model",
            messages=messages,
            timeout_seconds=20,
            cancellation_requested=False,
        )
    valid = messages[:1]
    with pytest.raises(ValidationError):
        OpenAIExecutionRequestV2(
            execution_request_id="request",
            request_envelope_identity=IDENTITY,
            model="gpt-model",
            messages=valid,
            timeout_seconds=True,
            cancellation_requested=False,
        )


def test_success_response_projects_exact_frozen_provider_semantics() -> None:
    result = project_openai_execution_response(_response(), _request())
    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.provider_result is not None
    assert result.provider_result.status is ProviderResultStatusV2.SUCCESS
    assert tuple(
        item.source_request_reference for item in result.provider_result.outputs
    ) == ("source-request:0", "source-request:1")


def test_partial_and_provider_failed_semantics_remain_completed_execution() -> None:
    partial = _response(
        status=ProviderResultStatusV2.PARTIAL,
        outputs=(_output(0, reason=ProviderFinishReasonV2.LENGTH),),
        failure_code="length",
    )
    failed = _response(
        status=ProviderResultStatusV2.FAILED,
        outputs=(),
        failure_code="provider-rejected",
    )
    assert (
        project_openai_execution_response(partial, _request()).outcome
        is ExecutionOutcomeV2.COMPLETED
    )
    assert (
        project_openai_execution_response(failed, _request()).outcome
        is ExecutionOutcomeV2.COMPLETED
    )


def test_content_filter_is_provider_semantics_not_execution_failure() -> None:
    response = _response(
        status=ProviderResultStatusV2.PARTIAL,
        outputs=(_output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),),
        category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
        failure_code="content-filtered",
    )
    result = project_openai_execution_response(response, _request())
    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.provider_result is not None
    assert result.provider_result.status is ProviderResultStatusV2.PARTIAL


@pytest.mark.parametrize(
    "finish_reason",
    (
        ProviderFinishReasonV2.COMPLETED,
        ProviderFinishReasonV2.LENGTH,
        ProviderFinishReasonV2.FAILED,
        ProviderFinishReasonV2.UNKNOWN,
    ),
)
def test_content_filter_category_rejects_every_foreign_finish_reason(
    finish_reason: ProviderFinishReasonV2,
) -> None:
    with pytest.raises(
        ValidationError,
        match="content-filter category conflicts with output finish reason",
    ):
        _response(
            status=ProviderResultStatusV2.PARTIAL,
            outputs=(_output(0, reason=finish_reason),),
            category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
            failure_code="content-filtered",
        )


def test_multiple_content_filtered_outputs_are_accepted_without_text_rewriting() -> (
    None
):
    outputs = (
        OpenAIExecutionOutputV2(
            ordinal=0,
            generated_text="Text parțial unu",
            finish_reason=ProviderFinishReasonV2.CONTENT_FILTERED,
        ),
        OpenAIExecutionOutputV2(
            ordinal=1,
            generated_text="Text parțial doi",
            finish_reason=ProviderFinishReasonV2.CONTENT_FILTERED,
        ),
    )
    response = _response(
        status=ProviderResultStatusV2.PARTIAL,
        outputs=outputs,
        category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
        failure_code="content-filtered",
    )
    result = project_openai_execution_response(response, _request())

    assert tuple(item.generated_text for item in response.outputs) == (
        "Text parțial unu",
        "Text parțial doi",
    )
    assert result.provider_result is not None
    assert tuple(item.finish_reason for item in result.provider_result.outputs) == (
        ProviderFinishReasonV2.CONTENT_FILTERED,
        ProviderFinishReasonV2.CONTENT_FILTERED,
    )


@pytest.mark.parametrize(
    "other_reason",
    (ProviderFinishReasonV2.LENGTH, ProviderFinishReasonV2.COMPLETED),
)
def test_content_filter_category_rejects_mixed_output_reasons(
    other_reason: ProviderFinishReasonV2,
) -> None:
    with pytest.raises(ValidationError, match="content-filter category conflicts"):
        _response(
            status=ProviderResultStatusV2.PARTIAL,
            outputs=(
                _output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),
                _output(1, reason=other_reason),
            ),
            category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
            failure_code="content-filtered",
        )


@pytest.mark.parametrize(
    "category",
    (
        None,
        OpenAIClientErrorCategoryV2.TIMEOUT,
        OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE,
    ),
)
def test_filtered_finish_reason_requires_content_filter_category(category) -> None:
    with pytest.raises(ValidationError):
        _response(
            status=(
                ProviderResultStatusV2.PARTIAL
                if category is None
                else ProviderResultStatusV2.FAILED
            ),
            outputs=(_output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),),
            category=category,
            failure_code="content-filtered",
        )


@pytest.mark.parametrize(
    "status,outputs,failure_code",
    (
        (ProviderResultStatusV2.PARTIAL, (), "content-filtered"),
        (
            ProviderResultStatusV2.SUCCESS,
            (_output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),),
            "content-filtered",
        ),
        (ProviderResultStatusV2.FAILED, (), "content-filtered"),
        (
            ProviderResultStatusV2.PARTIAL,
            (_output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),),
            None,
        ),
    ),
)
def test_content_filter_category_rejects_incomplete_semantic_state(
    status, outputs, failure_code
) -> None:
    with pytest.raises(ValidationError):
        _response(
            status=status,
            outputs=outputs,
            category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
            failure_code=failure_code,
        )


def test_projection_reconstructs_copied_content_filter_contradictions() -> None:
    valid = _response(
        status=ProviderResultStatusV2.PARTIAL,
        outputs=(_output(0, reason=ProviderFinishReasonV2.CONTENT_FILTERED),),
        category=OpenAIClientErrorCategoryV2.CONTENT_FILTERED,
        failure_code="content-filtered",
    )
    contradictory_category = valid.model_copy(
        update={"outputs": (_output(0, reason=ProviderFinishReasonV2.LENGTH),)}
    )
    contradictory_output = valid.model_copy(update={"failure_category": None})

    for response in (contradictory_category, contradictory_output):
        before = response.model_dump(mode="json")
        messages = []
        for _ in range(2):
            with pytest.raises(OpenAIResponseMappingError) as captured:
                project_openai_execution_response(response, _request())
            messages.append(str(captured.value))
        assert messages[0] == messages[1]
        assert response.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "category,outcome",
    (
        (
            OpenAIClientErrorCategoryV2.AUTHENTICATION,
            ExecutionOutcomeV2.PROVIDER_FAILURE,
        ),
        (OpenAIClientErrorCategoryV2.RATE_LIMITED, ExecutionOutcomeV2.PROVIDER_FAILURE),
        (
            OpenAIClientErrorCategoryV2.INVALID_REQUEST,
            ExecutionOutcomeV2.PROVIDER_FAILURE,
        ),
        (
            OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE,
            ExecutionOutcomeV2.PROVIDER_FAILURE,
        ),
        (OpenAIClientErrorCategoryV2.TIMEOUT, ExecutionOutcomeV2.TIMEOUT),
        (OpenAIClientErrorCategoryV2.CANCELLED, ExecutionOutcomeV2.CANCELLED),
        (
            OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE,
            ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
        ),
        (
            OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR,
            ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
        ),
    ),
)
def test_client_categories_map_to_one_execution_outcome(category, outcome) -> None:
    response = _response(
        status=ProviderResultStatusV2.FAILED,
        outputs=(),
        category=category,
        failure_code=f"client-{category.value}",
    )
    result = project_openai_execution_response(response, _request())
    assert result.outcome is outcome
    assert result.provider_result is None


def test_response_mapping_rejects_undercoverage_extra_outputs_and_foreign_authority() -> (
    None
):
    under = _response(outputs=(_output(0),))
    with pytest.raises(OpenAIResponseMappingError, match="projection"):
        project_openai_execution_response(under, _request())
    extra = _response(outputs=(_output(0), _output(1), _output(2)))
    with pytest.raises(OpenAIResponseMappingError, match="projection"):
        project_openai_execution_response(extra, _request())
    foreign = build_provider_descriptor(
        provider_id="claude",
        display_name="Claude",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    with pytest.raises(OpenAIResponseMappingError, match="OpenAI authority"):
        project_openai_execution_response(_response(), _request(provider=foreign))


def test_response_revalidates_copied_nested_output_and_semantics() -> None:
    forged_output = _output(0).model_copy(update={"generated_text": ""})
    response = _response().model_copy(update={"outputs": (forged_output, _output(1))})
    with pytest.raises(ValidationError):
        OpenAIExecutionResponseV2.model_validate(response)
    with pytest.raises(ValidationError):
        _response(
            status=ProviderResultStatusV2.SUCCESS,
            category=OpenAIClientErrorCategoryV2.TIMEOUT,
            failure_code="timeout",
        )


def test_response_dto_rejects_duplicate_ordinals_raw_enums_and_sdk_payloads() -> None:
    duplicate = (_output(0), _output(0))
    with pytest.raises(ValidationError, match="ordinals"):
        _response(outputs=duplicate)
    with pytest.raises(ValidationError):
        OpenAIExecutionOutputV2(
            ordinal=0, generated_text="text", finish_reason="completed"
        )
    with pytest.raises(ValidationError):
        OpenAIExecutionResponseV2(
            **_response().model_dump(mode="python"), raw_response=object()
        )


def test_lookalike_openai_provider_is_rejected() -> None:
    descriptor = build_provider_descriptor(
        provider_id="openai-compatible",
        display_name="OpenAI Compatible",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    with pytest.raises(OpenAIRequestMappingError, match="OpenAI authority"):
        build_openai_execution_request(
            _request(provider=descriptor), OpenAIExecutionConfigV2(model="gpt")
        )


def test_error_taxonomy_derives_from_provider_neutral_boundary() -> None:
    assert issubclass(OpenAIExecutionBoundaryError, Exception)
    assert issubclass(OpenAIRequestMappingError, OpenAIExecutionBoundaryError)
    assert issubclass(OpenAIResponseMappingError, OpenAIExecutionBoundaryError)
    assert issubclass(OpenAIConfigurationError, OpenAIExecutionBoundaryError)


def test_package_has_no_execution_implementation_or_forbidden_dependencies() -> None:
    forbidden_imports = {
        "openai",
        "httpx",
        "requests",
        "aiohttp",
        "asyncio",
        "threading",
        "logging",
        "sqlite3",
        "os",
        "dotenv",
        "urllib",
        "socket",
        "ssl",
        "random",
        "uuid",
    }
    forbidden_calls = {"run", "invoke", "request", "stream"}
    execute_definitions = []
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not imports & forbidden_imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.name not in forbidden_calls
                if node.name == "execute":
                    execute_definitions.append(path.name)
    assert execute_definitions == ["executor.py"]


def test_clean_process_import_does_not_load_sdk_or_transport_modules() -> None:
    modules = (
        "pastila_scout.provider_execution_openai_v2",
        "pastila_scout.provider_execution_openai_v2.models",
        "pastila_scout.provider_execution_openai_v2.interface",
        "pastila_scout.provider_execution_openai_v2.mapping",
        "pastila_scout.provider_execution_openai_v2.errors",
        "pastila_scout.provider_execution_openai_v2.executor",
    )
    for module in modules:
        script = (
            f"import sys; import {module}; "
            "forbidden={'openai','httpx','requests','aiohttp','asyncio'}; "
            "assert not (forbidden & set(sys.modules))"
        )
        subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True)


def test_frozen_layers_do_not_reverse_import_openai_execution_boundary() -> None:
    frozen = (
        ROOT / "src" / "pastila_scout" / "provider_v2",
        ROOT / "src" / "pastila_scout" / "provider_execution_v2",
        ROOT / "src" / "pastila_scout" / "provider_execution_testing_v2",
        ROOT / "src" / "pastila_scout" / "provider_adapters_v2",
        ROOT / "src" / "pastila_scout" / "provider_composition_v2",
    )
    for package in frozen:
        for path in package.glob("*.py"):
            assert "provider_execution_openai_v2" not in path.read_text(
                encoding="utf-8"
            )


def test_frozen_baseline_exports_hashes_and_callable_identities_are_unchanged() -> None:
    import pastila_scout.provider_execution_testing_v2 as testing_v2
    import pastila_scout.provider_execution_v2 as execution_v2
    from pastila_scout import provider_v2

    assert (
        len(provider_v2.__all__),
        len(execution_v2.__all__),
        len(testing_v2.__all__),
    ) == (
        42,
        13,
        2,
    )
    manifest = (
        ROOT / "docs" / "editorial-script-composer" / "Phase7_1_Revision8_Integrity.md"
    ).read_text(encoding="utf-8")
    rows = re.findall(r"\| `([^`]+\.py)` \| `([0-9a-f]{64})` \|", manifest)
    assert len(rows) == 15
    assert all(
        hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in rows
    )
    assert (
        OpenAIProviderAdapter.v1_request_builder,
        OpenAIProviderAdapter.v1_request_validator,
        OpenAIProviderAdapter.v1_extracted_result_builder,
        OpenAIProviderAdapter.v1_extracted_result_validator,
        OpenAIProviderAdapter.v1_concrete_result_builder,
        OpenAIProviderAdapter.v1_concrete_result_validator,
        OpenAIProviderAdapter.v1_generic_result_builder,
        OpenAIProviderAdapter.v1_generic_result_validator,
    ) == (
        build_draft_provider_request_plan,
        validate_draft_provider_request_plan,
        build_openai_extracted_execution_result,
        validate_openai_extracted_execution_result,
        build_openai_provider_execution_result,
        validate_openai_provider_execution_result,
        build_provider_execution_result,
        validate_provider_execution_result,
    )
