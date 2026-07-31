"""M6C.6D Part 2 deterministic preparation tests."""

from test_capability_execution_input_transport import _transport

from pastila_scout.editor.generation.revision import ControlledRevisionRequest
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    validate_executor_request_v2,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    ControlledGenerationRevisionRequestProjector,
    DraftRevisionInputResolver,
    DraftRevisionPreconditionCode,
    DraftRevisionPreconditionEvaluator,
    DraftRevisionPreparationDiagnosticCode,
    DraftRevisionPreparationOutcome,
    DraftRevisionPreparationPhase,
    DraftRevisionPreparationResultFactory,
    DraftRevisionPreparationService,
    DraftRevisionPreparationStatus,
    DraftRevisionPreservationManifestBuilder,
    DraftRevisionRequestFactory,
    build_draft_revision_executor_descriptor,
    build_draft_revision_preparation_report,
    compose_draft_revision_preparation_service,
    serialize_draft_revision_preparation_report,
    validate_draft_revision_preparation_result,
)
from pastila_scout.editor.qa.models import fingerprint


def _prepared():
    request = _transport()[3]
    service = compose_draft_revision_preparation_service(request.executor_descriptor)
    return request, service.prepare(request)


def test_valid_preparation_preserves_every_authoritative_identity():
    executor_request, result = _prepared()
    planning = executor_request.planning_input

    assert result.outcome is DraftRevisionPreparationOutcome.PREPARED
    assert result.status is DraftRevisionPreparationStatus.PREPARED
    assert result.executor_request is executor_request
    assert result.resolved_input.source_draft is planning.source_draft
    assert result.resolved_input.policy is planning.revision_policy
    assert result.resolved_input.scope is planning.revision_scope
    assert result.resolved_input.instructions is planning.revision_instructions
    assert result.revision_request.executor_request is executor_request.legacy_request
    assert result.generation_request.source_draft is planning.source_draft
    assert result.lifecycle.phases[-1] is DraftRevisionPreparationPhase.PREPARED
    validate_draft_revision_preparation_result(result)


def test_projection_is_explicit_provider_neutral_and_preserves_lineage():
    executor_request, result = _prepared()
    projected = result.generation_request

    assert isinstance(projected, ControlledRevisionRequest)
    assert projected.operation.value == "revision"
    assert projected.source_draft is result.revision_request.source_draft
    assert (
        projected.planning_input_fingerprint
        == executor_request.planning_input.input_fingerprint
    )
    assert (
        projected.executor_request_fingerprint == executor_request.request_fingerprint
    )
    assert (
        projected.revision_targets[0].upstream_target_fingerprint
        == result.revision_request.scope.targets[0].target_fingerprint
    )
    assert (
        projected.revision_instructions.upstream_instructions_fingerprint
        == result.revision_request.instructions.instructions_fingerprint
    )
    assert not hasattr(projected, "provider")
    assert not hasattr(projected, "generation_mode")


def test_preservation_manifest_is_content_free_and_deterministic():
    _, first = _prepared()
    _, second = _prepared()
    manifest = first.preservation_manifest

    assert (
        manifest.manifest_fingerprint
        == second.preservation_manifest.manifest_fingerprint
    )
    assert manifest.source_draft_fingerprint == fingerprint(
        first.resolved_input.source_draft
    )
    assert manifest.authorized_target_fingerprints == tuple(
        sorted(item.target_fingerprint for item in first.resolved_input.scope.targets)
    )
    serialized = serialize_draft_revision_preparation_report(
        build_draft_revision_preparation_report(first)
    )
    assert first.resolved_input.source_draft.assembled_text not in serialized
    assert first.resolved_input.instructions.editorial_instruction not in serialized


def test_invalid_executor_fingerprint_rejects_before_resolution():
    request = _transport()[3]
    invalid = request.model_copy(update={"request_fingerprint": "sha256:" + "0" * 64})
    service = compose_draft_revision_preparation_service(request.executor_descriptor)
    result = service.prepare(invalid)

    assert result.outcome is DraftRevisionPreparationOutcome.REJECTED
    assert (
        result.diagnostic.code
        is DraftRevisionPreparationDiagnosticCode.INVALID_EXECUTOR_REQUEST
    )
    assert result.executor_request is None
    assert result.generation_request is None
    assert result.lifecycle.phases[-1] is DraftRevisionPreparationPhase.REJECTED


def test_descriptor_substitution_fails_exact_identity_even_when_equal():
    request = _transport()[3]
    equivalent = build_draft_revision_executor_descriptor()
    assert equivalent == request.executor_descriptor
    assert equivalent is not request.executor_descriptor

    result = compose_draft_revision_preparation_service(equivalent).prepare(request)

    assert (
        result.diagnostic.code
        is DraftRevisionPreparationDiagnosticCode.DESCRIPTOR_MISMATCH
    )
    assert result.generation_request is None


def test_nested_planning_tampering_and_unknown_versions_fail_closed():
    request = _transport()[3]
    planning = request.planning_input.model_copy(
        update={"input_fingerprint": "sha256:" + "0" * 64}
    )
    invalid = request.model_copy(update={"planning_input": planning})
    service = compose_draft_revision_preparation_service(request.executor_descriptor)
    result = service.prepare(invalid)
    assert (
        result.diagnostic.code
        is DraftRevisionPreparationDiagnosticCode.INVALID_EXECUTOR_REQUEST
    )

    unknown = request.model_copy(update={"request_version": "999"})
    result = service.prepare(unknown)
    assert (
        result.diagnostic.code
        is DraftRevisionPreparationDiagnosticCode.INVALID_EXECUTOR_REQUEST
    )


def test_preconditions_are_complete_canonical_and_fail_closed():
    _, result = _prepared()
    evaluation = result.precondition_evaluation

    assert evaluation.passed
    assert tuple(item.code for item in evaluation.findings) == tuple(
        DraftRevisionPreconditionCode
    )
    assert all(item.passed for item in evaluation.findings)

    prohibited = result.resolved_input.instructions.model_copy(
        update={"editorial_instruction": "Schimbă faptul principal."}
    )
    resolved = result.resolved_input.model_copy(update={"instructions": prohibited})
    request = result.revision_request.model_copy(update={"instructions": prohibited})
    rejected = DraftRevisionPreconditionEvaluator().evaluate(
        resolved, request, result.preservation_manifest
    )
    finding = next(
        item
        for item in rejected.findings
        if item.code is DraftRevisionPreconditionCode.REQUEST_PERMITTED
    )
    assert not rejected.passed
    assert (
        finding.diagnostic_code
        is DraftRevisionPreparationDiagnosticCode.PROHIBITED_REVISION
    )


class Spy:
    def __init__(self, wrapped=None, error=None):
        self.wrapped = wrapped
        self.error = error
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        if self.error:
            raise self.error
        return self.wrapped(*args)

    def resolve(self, *args):
        return self.__call__(*args)

    def build(self, *args):
        return self.__call__(*args)

    def create(self, *args):
        return self.__call__(*args)

    def evaluate(self, *args):
        return self.__call__(*args)

    def project(self, *args):
        return self.__call__(*args)


def _spied_service(request, *, validator_error=None, projector_error=None):
    resolver = Spy(DraftRevisionInputResolver().resolve)
    manifest = Spy(DraftRevisionPreservationManifestBuilder().build)
    factory = Spy(DraftRevisionRequestFactory().create)
    evaluator = Spy(DraftRevisionPreconditionEvaluator().evaluate)
    projector = Spy(
        ControlledGenerationRevisionRequestProjector().project,
        error=projector_error,
    )
    validator = Spy(validate_executor_request_v2, error=validator_error)
    projection_validator = Spy(lambda value: None)
    service = DraftRevisionPreparationService(
        registered_descriptor=request.executor_descriptor,
        executor_request_validator=validator,
        input_resolver=resolver,
        preservation_builder=manifest,
        request_factory=factory,
        precondition_evaluator=evaluator,
        projector=projector,
        generation_request_validator=projection_validator,
        result_factory=DraftRevisionPreparationResultFactory(),
    )
    return service, (
        validator,
        resolver,
        manifest,
        factory,
        evaluator,
        projector,
        projection_validator,
    )


def test_dependency_call_counts_invalid_request_and_projection_failure():
    request = _transport()[3]
    service, spies = _spied_service(request, validator_error=ValueError("sentinel"))
    result = service.prepare(request)
    assert result.outcome is DraftRevisionPreparationOutcome.REJECTED
    assert tuple(item.calls for item in spies) == (1, 0, 0, 0, 0, 0, 0)

    service, spies = _spied_service(request, projector_error=ValueError("sentinel"))
    result = service.prepare(request)
    assert result.outcome is DraftRevisionPreparationOutcome.REJECTED
    assert tuple(item.calls for item in spies) == (1, 1, 1, 1, 1, 1, 0)
    assert result.generation_request is None


def test_unexpected_evaluator_failure_is_sanitized_internal_failure():
    request = _transport()[3]
    service, spies = _spied_service(request)
    spies[4].error = RuntimeError("OPENAI_API_KEY=secret C:\\private")
    result = service.prepare(request)
    report = serialize_draft_revision_preparation_report(
        build_draft_revision_preparation_report(result)
    )

    assert result.outcome is DraftRevisionPreparationOutcome.FAILED_INTERNAL
    assert result.status is DraftRevisionPreparationStatus.FAILED
    assert (
        result.diagnostic.code
        is DraftRevisionPreparationDiagnosticCode.PREPARATION_INTERNAL_FAILURE
    )
    assert "secret" not in repr(result)
    assert "secret" not in report
    assert result.generation_request is None


def test_preparation_is_deterministic_and_never_invokes_generation():
    request, first = _prepared()
    second = compose_draft_revision_preparation_service(
        request.executor_descriptor
    ).prepare(request)

    assert first.preparation_fingerprint == second.preparation_fingerprint
    assert (
        first.generation_request.revision_request_fingerprint
        == second.generation_request.revision_request_fingerprint
    )
    assert first.lifecycle == second.lifecycle
    assert "gateway" not in vars(
        compose_draft_revision_preparation_service(request.executor_descriptor)
    )
