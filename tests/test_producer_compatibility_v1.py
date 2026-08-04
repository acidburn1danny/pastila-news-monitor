"""Focused Phase A Producer compatibility contract and inert-boundary tests."""

from __future__ import annotations

import base64
import copy
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from functools import cached_property, partial, wraps
from inspect import Signature
from pathlib import Path

import pytest

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.generation.provider_compatibility_v1 import (
    ProducerCompatibilityConfigurationError,
    ProducerCompatibilityEventCodeV1,
    ProducerCompatibilityEventV1,
    ProducerDiagnosticsObservationV1,
    ProducerExecutionFailureV1,
    ProducerExecutionLifecycleStateV1,
    ProducerExecutionRequestV1,
    ProducerFailureCodeV1,
    ProducerFinishMetadataV1,
    ProducerTokenUsageV1,
)
from pastila_scout.editor.generation.provider_compatibility_v1.composition import (
    compose_producer_compatibility_v1,
)
from pastila_scout.editor.generation.provider_compatibility_v1.models import (
    AIProviderExecutionFailureKind,
    AIProviderExecutionStatus,
    AIRetryPolicy,
)
from pastila_scout.editor.generation.provider_compatibility_v1.projection import (
    ProducerResultProjectorV1,
    correlation_id_for,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionDiagnostic,
    ControlledRevisionGatewayResult,
    ControlledRevisionInstructions,
    ControlledRevisionInvocation,
    ControlledRevisionOutputContract,
    ControlledRevisionPolicy,
    ControlledRevisionRequest,
    ControlledRevisionTarget,
    DraftPreservationRequirements,
    RevisionDiagnosticCode,
    RevisionGatewayStatus,
    RevisionTargetType,
    revision_fingerprint,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
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
)

ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 64
REVISION_FP = "sha256:" + ZERO
IDENTITY = f"scout:test-authority:{ZERO}"
FP = "sha256:" + "1" * 64
EXPECTED_API = (
    "ProducerCompatibilityConfigurationError",
    "ProducerCompatibilityClockV1",
    "ProducerCompatibilityEventCodeV1",
    "ProducerCompatibilityEventV1",
    "ProducerCompatibilityObserverV1",
    "ProducerDiagnosticAuthorityV1",
    "ProducerDiagnosticsAuthorityV1",
    "ProducerDiagnosticsObservationV1",
    "ProducerExecutionAttemptV1",
    "ProducerExecutionDiagnosticsV1",
    "ProducerExecutionFailureV1",
    "ProducerExecutionLifecycleStateV1",
    "ProducerExecutionLifecycleV1",
    "ProducerExecutionRequestV1",
    "ProducerExecutionResultV1",
    "ProducerFailureCodeV1",
    "ProducerFinishMetadataV1",
    "ProducerAttemptDiagnosticsV1",
    "ProducerTokenUsageV1",
)


def _provider_request(*, draft_fingerprint: str = ZERO) -> ProviderExecutionRequestV2:
    intent = ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:test",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:test",
        draft_fingerprint=draft_fingerprint,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference="source-request:test",
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(
                        role="generation", content="Conținut confirmat.", ordinal=0
                    ),
                ),
            ),
        ),
    )
    descriptor = build_provider_descriptor(
        provider_id="test-provider",
        display_name="Test Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id="request-test",
            requested_at=datetime(2026, 8, 4, 10, tzinfo=UTC),
            cancellation=CancellationTokenV2(cancellation_requested=False),
            metadata=(),
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
    )


def _request(
    *, invocation_fingerprint: str = REVISION_FP, draft_fingerprint: str = ZERO
) -> ProducerExecutionRequestV1:
    return ProducerExecutionRequestV1.build(
        invocation_reference="controlled-revision-invocation:test",
        invocation_fingerprint=invocation_fingerprint,
        provider_request=_provider_request(draft_fingerprint=draft_fingerprint),
        retry_policy=AIRetryPolicy(maximum_attempts=1),
    )


def _result(
    outcome: ExecutionOutcomeV2,
    *,
    status: ProviderResultStatusV2 = ProviderResultStatusV2.SUCCESS,
    finish: ProviderFinishReasonV2 = ProviderFinishReasonV2.COMPLETED,
    request: ProviderExecutionRequestV2 | None = None,
) -> ProviderExecutionResultV2:
    request = request or _provider_request()
    completed = outcome is ExecutionOutcomeV2.COMPLETED
    outputs = (
        (
            ProviderOutputInputV2(
                source_request_reference="source-request:test",
                ordinal=0,
                generated_text="SMOKE_OK",
                finish_reason=finish,
            ),
        )
        if completed and status is not ProviderResultStatusV2.FAILED
        else ()
    )
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=outcome,
        finished_at=datetime(2026, 8, 4, 10, 0, 1, tzinfo=UTC),
        provider_result=(
            ProviderResultProjectionV2(
                status=status,
                outputs=outputs,
                failure_code=(
                    None if status is ProviderResultStatusV2.SUCCESS else "partial"
                ),
            )
            if completed
            else None
        ),
        failure_code=None if completed else "execution-failed",
        failure_message=None if completed else "Safe lower failure.",
    )


def _gateway() -> ControlledRevisionGatewayResult:
    source = _draft("source")
    target = ControlledRevisionTarget.build(
        target_type=RevisionTargetType.OPENING,
        upstream_target_fingerprint=FP,
    )
    policy = ControlledRevisionPolicy.build(
        maximum_revision_targets=1, upstream_policy_fingerprint=FP
    )
    instructions = ControlledRevisionInstructions.build(
        editorial_instruction="Revise the authorized opening.",
        authorized_scope_fingerprint=FP,
        upstream_instructions_fingerprint=FP,
    )
    source_fp = revision_fingerprint(source)
    preservation = DraftPreservationRequirements.build(
        source_draft_fingerprint=source_fp,
        allowed_target_fingerprints=(target.target_fingerprint,),
        protected_component_fingerprints=(
            ("closing", revision_fingerprint(source.closing)),
        ),
        upstream_scope_fingerprint=FP,
    )
    output = ControlledRevisionOutputContract.build(
        source_draft_fingerprint=source_fp,
        preservation_fingerprint=preservation.preservation_fingerprint,
    )
    request = ControlledRevisionRequest.build(
        source_draft=source,
        revision_targets=(target,),
        revision_instructions=instructions,
        revision_policy=policy,
        preservation_requirements=preservation,
        expected_output_contract=output,
        planning_input_fingerprint=FP,
        executor_request_fingerprint="sha256:" + "2" * 64,
    )
    invocation = ControlledRevisionInvocation.build(request=request)
    return ControlledRevisionGatewayResult.build(
        status=RevisionGatewayStatus.SUCCESS,
        revised_draft=_draft("revised"),
        source_draft_fingerprint=source_fp,
        revision_request_fingerprint=request.revision_request_fingerprint,
        invocation_fingerprint=invocation.invocation_fingerprint,
        output_contract_fingerprint=output.output_contract_fingerprint,
        preservation_fingerprint=preservation.preservation_fingerprint,
    )


def _draft(label: str) -> EpisodeDraft:
    opening = f"Opening {label}."
    closing = f"Closing {label}."
    text = f"{opening}\n\n{closing}"
    return EpisodeDraft(
        episode_id="episode-1",
        opening=opening,
        stories=(),
        transitions=(),
        closing=closing,
        cta=None,
        assembled_text=text,
        teleprompter_text=text,
    )


def test_public_api_is_exact_and_ordered() -> None:
    import pastila_scout.editor.generation.provider_compatibility_v1 as package

    assert package.__all__ == EXPECTED_API
    assert tuple(name for name in EXPECTED_API if not hasattr(package, name)) == ()


def test_request_identity_and_canonical_serialization_are_stable() -> None:
    first = _request()
    second = _request()

    assert first == second
    assert first.request_fingerprint == second.request_fingerprint
    assert first.canonical_bytes() == second.canonical_bytes()
    assert "request_reference" not in first.semantic_payload()
    assert "request_fingerprint" not in first.semantic_payload()
    assert first.request_reference.startswith(
        "scout:producer-compat:execution-request-v1:"
    )


def test_semantic_change_changes_fingerprint_and_identity_fields_do_not() -> None:
    request = _request()
    changed = ProducerExecutionRequestV1.build(
        invocation_reference="controlled-revision-invocation:changed",
        invocation_fingerprint=request.invocation_fingerprint,
        provider_request=request.provider_request,
        retry_policy=request.retry_policy,
    )

    assert changed.request_fingerprint != request.request_fingerprint
    altered_identity = copy.deepcopy(request)
    object.__setattr__(altered_identity, "request_reference", "foreign")
    object.__setattr__(altered_identity, "request_fingerprint", "f" * 64)
    assert request.semantic_payload() == altered_identity.semantic_payload()


def test_fingerprint_is_stable_across_a_clean_process() -> None:
    request = _request()
    encoded = base64.b64encode(pickle.dumps(request)).decode("ascii")
    script = (
        "import base64,pickle; "
        "from pastila_scout.editor.generation.provider_compatibility_v1 "
        "import ProducerExecutionRequestV1; "
        f"value=pickle.loads(base64.b64decode('{encoded}')); "
        "print(ProducerExecutionRequestV1.reconstruct(value).request_fingerprint)"
    )
    run = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout.strip() == request.request_fingerprint
    assert run.stderr == ""


@pytest.mark.parametrize("transport", (copy.copy, copy.deepcopy, pickle.loads))
def test_authoritative_reconstruction_rejects_copied_invalid_state(transport) -> None:
    request = _request()
    object.__setattr__(request, "invocation_reference", " padded ")
    candidate = (
        transport(pickle.dumps(request))
        if transport is pickle.loads
        else transport(request)
    )

    with pytest.raises(ValueError):
        ProducerExecutionRequestV1.reconstruct(candidate)


@pytest.mark.parametrize(
    "value",
    ("", " padded ", True, 1, ["mutable"]),
)
def test_contracts_reject_invalid_exact_values(value) -> None:
    payload = _request().model_dump(mode="python")
    payload["invocation_reference"] = value
    with pytest.raises(ValueError):
        ProducerExecutionRequestV1.model_validate(payload, strict=True)


def test_diagnostics_observation_requires_exact_correlation() -> None:
    request = _request()
    lower = request.provider_request
    observation = ProducerDiagnosticsObservationV1(
        correlation_id=correlation_id_for(request, attempt_number=1),
        attempt_number=1,
        execution_request_id=lower.context.request_id,
        request_envelope_identity=lower.request_envelope.identity,
        usage=ProducerTokenUsageV1(
            prompt_tokens=1, completion_tokens=2, total_tokens=3
        ),
    )
    assert observation.correlated_to(
        correlation_id=observation.correlation_id,
        attempt_number=1,
        execution_request_id=lower.context.request_id,
        request_envelope_identity=lower.request_envelope.identity,
    )

    stale = observation.model_copy(update={"attempt_number": 2})
    with pytest.raises(ValueError, match="stale or foreign"):
        ProducerResultProjectorV1().project(
            request=request,
            provider_result=_result(ExecutionOutcomeV2.TIMEOUT),
            observation=stale,
        )


class _DependencySpy:
    calls = 0

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.calls += 1
        raise AssertionError

    def observe(
        self,
        *,
        correlation_id: str,
        attempt_number: int,
        execution_request_id: str,
        request_envelope_identity: str,
        result: ProviderExecutionResultV2,
    ) -> ProducerDiagnosticsObservationV1 | None:
        self.calls += 1
        raise AssertionError

    def read_monotonic_ns(self) -> int:
        self.calls += 1
        raise AssertionError

    def emit(self, event: ProducerCompatibilityEventV1) -> None:
        self.calls += 1
        raise AssertionError

    def is_cancelled(self) -> bool:
        self.calls += 1
        raise AssertionError

    def should_retry(
        self,
        *,
        failure: ProducerExecutionFailureV1,
        attempt_number: int,
        policy: AIRetryPolicy,
    ) -> bool:
        self.calls += 1
        raise AssertionError

    def sleep(self, delay_seconds: float) -> None:
        self.calls += 1
        raise AssertionError


def test_composition_is_immutable_and_completely_inert() -> None:
    dependency = _DependencySpy()
    composition = compose_producer_compatibility_v1(
        request=_request(),
        executor=dependency,
        diagnostics_authority=dependency,
        clock=dependency,
        observer=dependency,
        cancellation_token=dependency,
        retry_decider=dependency,
        sleeper=dependency,
        projector=ProducerResultProjectorV1(),
    )

    assert dependency.calls == 0
    assert not hasattr(composition, "execute")
    with pytest.raises(AttributeError):
        composition.executor = dependency  # type: ignore[misc]


def test_composition_rejects_malformed_dependency_without_calls() -> None:
    dependency = _DependencySpy()
    with pytest.raises(ProducerCompatibilityConfigurationError) as caught:
        compose_producer_compatibility_v1(
            request=_request(),
            executor=object(),
            cancellation_token=dependency,
            retry_decider=dependency,
            sleeper=dependency,
            projector=ProducerResultProjectorV1(),
        )
    assert dependency.calls == 0
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is True


@pytest.mark.parametrize(
    "outcome,expected_code",
    (
        (
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            ProducerFailureCodeV1.PROVIDER_EXECUTION_FAILED,
        ),
        (ExecutionOutcomeV2.TIMEOUT, ProducerFailureCodeV1.PROVIDER_TIMEOUT),
        (
            ExecutionOutcomeV2.CANCELLED,
            ProducerFailureCodeV1.PRODUCER_EXECUTION_CANCELLED,
        ),
        (
            ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
            ProducerFailureCodeV1.PROVIDER_INTERNAL_FAILURE,
        ),
    ),
)
def test_projection_maps_every_execution_failure_deterministically(
    outcome, expected_code
) -> None:
    projected = ProducerResultProjectorV1().project(
        request=_request(), provider_result=_result(outcome)
    )

    assert projected.failure is not None
    assert projected.failure.diagnostic_code is expected_code
    assert projected.attempts[0].failure == projected.failure
    assert projected.diagnostics.attempt_count == 1


def test_projection_preserves_known_safe_lower_failure_mapping() -> None:
    result = _result(ExecutionOutcomeV2.PROVIDER_FAILURE).model_copy(
        update={"failure_code": "provider_rate_limited"}
    )
    projected = ProducerResultProjectorV1().project(
        request=_request(), provider_result=result
    )
    assert projected.failure is not None
    assert (
        projected.failure.diagnostic_code is ProducerFailureCodeV1.PROVIDER_RATE_LIMITED
    )
    assert projected.failure.source_failure_code == "provider_rate_limited"


def test_projection_maps_partial_length_and_content_filter() -> None:
    projector = ProducerResultProjectorV1()
    length = projector.project(
        request=_request(),
        provider_result=_result(
            ExecutionOutcomeV2.COMPLETED,
            status=ProviderResultStatusV2.PARTIAL,
            finish=ProviderFinishReasonV2.LENGTH,
        ),
    )
    filtered = projector.project(
        request=_request(),
        provider_result=_result(
            ExecutionOutcomeV2.COMPLETED,
            status=ProviderResultStatusV2.PARTIAL,
            finish=ProviderFinishReasonV2.CONTENT_FILTERED,
        ),
    )
    assert (
        length.failure.diagnostic_code is ProducerFailureCodeV1.PROVIDER_LENGTH_LIMITED
    )
    assert (
        filtered.failure.diagnostic_code
        is ProducerFailureCodeV1.PROVIDER_CONTENT_FILTERED
    )


def test_completed_success_projects_gateway_and_preserves_output_order() -> None:
    gateway = _gateway()
    request = _request(
        invocation_fingerprint=gateway.invocation_fingerprint,
        draft_fingerprint=gateway.source_draft_fingerprint[7:],
    )
    projected = ProducerResultProjectorV1().project(
        request=request,
        provider_result=_result(
            ExecutionOutcomeV2.COMPLETED, request=request.provider_request
        ),
        gateway_result=gateway,
    )

    assert projected.failure is None
    assert projected.gateway_result is not None
    assert projected.attempts[0].diagnostics.finish_metadata[0].ordinal == 0


def test_projection_rejects_foreign_and_malformed_lower_results() -> None:
    result = _result(ExecutionOutcomeV2.TIMEOUT)
    foreign = result.model_copy(update={"request_id": "foreign"})
    with pytest.raises(ValueError, match="lineage"):
        ProducerResultProjectorV1().project(request=_request(), provider_result=foreign)

    object.__setattr__(result, "provider_id", " padded ")
    with pytest.raises(ValueError, match="invalid retained"):
        ProducerResultProjectorV1().project(request=_request(), provider_result=result)


def test_clean_process_import_is_passive_and_does_not_load_openai() -> None:
    script = (
        "import sys; "
        "import pastila_scout.editor.generation.provider_compatibility_v1 as p; "
        "print(len(p.__all__), int('openai' in sys.modules))"
    )
    run = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout.strip() == "19 0"
    assert run.stderr == ""


def test_failure_table_is_fixed_and_complete() -> None:
    from pastila_scout.editor.generation.provider_compatibility_v1.models import (
        ProducerExecutionFailureV1,
    )

    for code in ProducerFailureCodeV1:
        failure = ProducerExecutionFailureV1.from_code(code)
        assert failure.diagnostic_code is code
        assert failure.safe_message.endswith(".")
        assert "traceback" not in failure.safe_message.lower()
    assert len(tuple(ProducerFailureCodeV1)) == 18


def _compose_with_executor(executor):
    dependency = _DependencySpy()
    return compose_producer_compatibility_v1(
        request=_request(),
        executor=executor,
        cancellation_token=dependency,
        retry_decider=dependency,
        sleeper=dependency,
        projector=ProducerResultProjectorV1(),
    )


def test_composition_rejects_wrong_callable_shapes_without_invocation() -> None:
    calls = []

    class WrongArity:
        def execute(self) -> ProviderExecutionResultV2:
            calls.append("wrong-arity")
            raise AssertionError

    class ExtraRequired:
        def execute(
            self, request: ProviderExecutionRequestV2, extra: object
        ) -> ProviderExecutionResultV2:
            calls.append("extra")
            raise AssertionError

    class KeywordOnly:
        def execute(
            self, *, request: ProviderExecutionRequestV2
        ) -> ProviderExecutionResultV2:
            calls.append("keyword")
            raise AssertionError

    class PropertyExecutor:
        @property
        def execute(self):
            calls.append("property")
            raise AssertionError

    class CachedExecutor:
        @cached_property
        def execute(self):
            calls.append("cached")
            raise AssertionError

    class StaticExecutor:
        @staticmethod
        def execute(
            request: ProviderExecutionRequestV2,
        ) -> ProviderExecutionResultV2:
            calls.append("static")
            raise AssertionError

    class ClassExecutor:
        @classmethod
        def execute(
            cls, request: ProviderExecutionRequestV2
        ) -> ProviderExecutionResultV2:
            calls.append("class")
            raise AssertionError

    def partial_target(
        self, request: ProviderExecutionRequestV2
    ) -> ProviderExecutionResultV2:
        calls.append("partial")
        raise AssertionError

    class PartialExecutor:
        execute = partial(partial_target)

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            calls.append("wrapped")
            return function(*args, **kwargs)

        return wrapper

    class WrappedExecutor:
        @decorator
        def execute(
            self, request: ProviderExecutionRequestV2
        ) -> ProviderExecutionResultV2:
            raise AssertionError

    class ForgedSignature:
        def execute(self) -> ProviderExecutionResultV2:
            calls.append("forged")
            raise AssertionError

    ForgedSignature.execute.__signature__ = Signature()  # type: ignore[attr-defined]

    class DynamicExecutor:
        def __getattr__(self, name):
            calls.append(name)
            return partial_target

    for executor in (
        WrongArity(),
        ExtraRequired(),
        KeywordOnly(),
        PropertyExecutor(),
        CachedExecutor(),
        StaticExecutor(),
        ClassExecutor(),
        PartialExecutor(),
        WrappedExecutor(),
        ForgedSignature(),
        DynamicExecutor(),
    ):
        with pytest.raises(ProducerCompatibilityConfigurationError):
            _compose_with_executor(executor)
    assert calls == []


def _non_success_gateway(status: RevisionGatewayStatus):
    successful = _gateway()
    diagnostic = ControlledRevisionDiagnostic.build(
        code=RevisionDiagnosticCode.REVISION_GATEWAY_FAILURE,
        safe_message="Revision gateway failed.",
    )
    payload = successful.model_dump(
        mode="python", exclude={"gateway_result_fingerprint"}
    )
    payload.update(status=status, revised_draft=None, diagnostic=diagnostic)
    return ControlledRevisionGatewayResult.build(**payload)


@pytest.mark.parametrize(
    "gateway",
    (
        _non_success_gateway(RevisionGatewayStatus.FAILURE),
        _non_success_gateway(RevisionGatewayStatus.UNSUPPORTED),
    ),
)
def test_non_success_gateway_never_authorizes_success(gateway) -> None:
    projected = ProducerResultProjectorV1().project(
        request=_request(invocation_fingerprint=gateway.invocation_fingerprint),
        provider_result=_result(ExecutionOutcomeV2.COMPLETED),
        gateway_result=gateway,
    )
    assert projected.status is AIProviderExecutionStatus.FAILED
    assert projected.failure is not None
    assert (
        projected.failure.diagnostic_code
        is ProducerFailureCodeV1.GATEWAY_PROJECTION_FAILED
    )
    assert projected.gateway_result is None


def test_foreign_and_copied_invalid_gateways_never_authorize_success() -> None:
    gateway = _gateway()
    foreign = ControlledRevisionGatewayResult.build(
        **{
            **gateway.model_dump(mode="python", exclude={"gateway_result_fingerprint"}),
            "invocation_fingerprint": "sha256:" + "9" * 64,
        }
    )
    invalid = copy.deepcopy(gateway)
    object.__setattr__(invalid, "revised_draft", None)
    for candidate in (
        foreign,
        invalid,
        copy.copy(invalid),
        pickle.loads(pickle.dumps(invalid)),
    ):
        projected = ProducerResultProjectorV1().project(
            request=_request(invocation_fingerprint=gateway.invocation_fingerprint),
            provider_result=_result(ExecutionOutcomeV2.COMPLETED),
            gateway_result=candidate,
        )
        assert projected.status is AIProviderExecutionStatus.FAILED
        assert projected.gateway_result is None


def test_coordinated_foreign_gateway_draft_lineage_is_rejected() -> None:
    gateway = _gateway()
    foreign = ControlledRevisionGatewayResult.build(
        **{
            **gateway.model_dump(mode="python", exclude={"gateway_result_fingerprint"}),
            "source_draft_fingerprint": "sha256:" + "8" * 64,
        }
    )
    request = _request(
        invocation_fingerprint=gateway.invocation_fingerprint,
        draft_fingerprint=gateway.source_draft_fingerprint[7:],
    )
    projected = ProducerResultProjectorV1().project(
        request=request,
        provider_result=_result(
            ExecutionOutcomeV2.COMPLETED, request=request.provider_request
        ),
        gateway_result=foreign,
    )
    assert projected.status is AIProviderExecutionStatus.FAILED
    assert projected.gateway_result is None


def test_public_configuration_error_traceback_contains_no_authorities() -> None:
    dependency = _DependencySpy()
    request = _request()
    projector = ProducerResultProjectorV1()
    try:
        compose_producer_compatibility_v1(
            request=request,
            executor=object(),
            diagnostics_authority=dependency,
            clock=dependency,
            observer=dependency,
            cancellation_token=dependency,
            retry_decider=dependency,
            sleeper=dependency,
            projector=projector,
        )
    except ProducerCompatibilityConfigurationError as error:
        retained = []
        traceback = error.__traceback__
        while traceback:
            if "provider_compatibility_v1" in traceback.tb_frame.f_code.co_filename:
                retained.extend(traceback.tb_frame.f_locals.values())
            traceback = traceback.tb_next
        assert all(
            value is not target
            for value in retained
            for target in (dependency, request, projector)
        )
        assert error.__context__ is None
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
    else:
        raise AssertionError("invalid composition was accepted")


def test_public_contract_types_are_normative_and_not_private() -> None:
    gateway = _gateway()
    request = _request(
        invocation_fingerprint=gateway.invocation_fingerprint,
        draft_fingerprint=gateway.source_draft_fingerprint[7:],
    )
    result = ProducerResultProjectorV1().project(
        request=request,
        provider_result=_result(
            ExecutionOutcomeV2.COMPLETED, request=request.provider_request
        ),
        gateway_result=gateway,
    )
    assert type(result.status) is AIProviderExecutionStatus
    assert type(_request().retry_policy) is AIRetryPolicy
    failure = ProducerExecutionFailureV1.from_code(
        ProducerFailureCodeV1.PROVIDER_TIMEOUT,
        source_outcome=ExecutionOutcomeV2.TIMEOUT,
        source_failure_code="provider_timeout",
    )
    assert type(failure.failure_kind) is AIProviderExecutionFailureKind
    for model in (ProducerExecutionRequestV1, type(result), ProducerExecutionFailureV1):
        assert all("_Producer" not in str(item.type) for item in fields(model))
        assert "_Producer" not in str(model.model_json_schema())


def test_every_public_contract_is_genuinely_slot_only_and_frozen() -> None:
    failure_result = ProducerResultProjectorV1().project(
        request=_request(), provider_result=_result(ExecutionOutcomeV2.TIMEOUT)
    )
    attempt = failure_result.attempts[0]
    objects = (
        _request().retry_policy,
        ProducerTokenUsageV1(prompt_tokens=1),
        ProducerFinishMetadataV1(
            source_request_reference="source-request:test",
            ordinal=0,
            finish_reason=ProviderFinishReasonV2.COMPLETED,
        ),
        failure_result.failure,
        attempt.diagnostics,
        failure_result.diagnostics,
        ProducerDiagnosticsObservationV1(
            correlation_id="1" * 64,
            attempt_number=1,
            execution_request_id="request",
            request_envelope_identity="envelope",
        ),
        _request(),
        attempt,
        failure_result.lifecycle,
        failure_result,
        ProducerCompatibilityEventV1(
            event_code=next(iter(ProducerCompatibilityEventCodeV1)),
            request_reference=_request().request_reference,
            attempt_number=None,
            diagnostic_code=None,
            lifecycle_state=ProducerExecutionLifecycleStateV1.ACCEPTED,
        ),
    )
    flattened = tuple(item for item in objects if not isinstance(item, tuple))
    foreign_name = "foreign"
    for value in flattened:
        assert not hasattr(value, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(value, fields(value)[0].name, getattr(value, fields(value)[0].name))
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(value, foreign_name, True)
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            delattr(value, fields(value)[0].name)
        assert type(value).reconstruct(pickle.loads(pickle.dumps(value))) == value
