"""Deterministic M6C.6D Part 2 request-preparation pipeline."""

# The public service is the approved exception-normalization boundary.
# ruff: noqa: BLE001

from typing import Protocol

from pastila_scout.editor.generation.revision import (
    ControlledRevisionInstructions,
    ControlledRevisionOutputContract,
    ControlledRevisionPolicy,
    ControlledRevisionRequest,
    ControlledRevisionTarget,
    DraftPreservationRequirements,
    RevisionTargetType,
    revision_fingerprint,
    validate_controlled_revision_request,
)
from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequestV2,
    validate_executor_request_v2,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.models import canonical_json, fingerprint

from .enums import DraftRevisionTargetType
from .models import DraftRevisionRequest
from .planning import DraftRevisionPlanningInput
from .preparation_models import (
    DraftRevisionPreconditionCode,
    DraftRevisionPreconditionEvaluation,
    DraftRevisionPreconditionFinding,
    DraftRevisionPreparationDiagnostic,
    DraftRevisionPreparationDiagnosticCode,
    DraftRevisionPreparationLifecycle,
    DraftRevisionPreparationOutcome,
    DraftRevisionPreparationPhase,
    DraftRevisionPreparationReport,
    DraftRevisionPreparationResult,
    DraftRevisionPreparationStatus,
    DraftRevisionPreservationManifest,
    ResolvedDraftRevisionInput,
)
from .validation import validate_draft_revision_request


class DraftRevisionPreparationError(ValueError):
    """Controlled preparation rejection carrying only an approved code."""

    def __init__(self, code: DraftRevisionPreparationDiagnosticCode):
        self.code = code
        super().__init__(code.value)


class ExecutorRequestValidator(Protocol):
    def __call__(self, value: CorrectiveActionExecutorRequestV2) -> None: ...


class GenerationRequestValidator(Protocol):
    def __call__(self, value: ControlledRevisionRequest) -> None: ...


class DraftRevisionInputResolver:
    """Resolve exact authorized planning objects from executor-request v2."""

    def resolve(
        self, executor_request: CorrectiveActionExecutorRequestV2
    ) -> ResolvedDraftRevisionInput:
        planning = executor_request.planning_input
        if not isinstance(planning, DraftRevisionPlanningInput):
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.SOURCE_DRAFT_UNAVAILABLE
            )
        return ResolvedDraftRevisionInput.build(
            executor_request=executor_request,
            source_draft=planning.source_draft,
            policy=planning.revision_policy,
            scope=planning.revision_scope,
            instructions=planning.revision_instructions,
            authorization_state=executor_request.execution_context.authorization_state,
            planning_input_fingerprint=planning.input_fingerprint,
        )


class DraftRevisionRequestFactory:
    """Construct the one capability request without rebuilding nested input."""

    def create(self, resolved: ResolvedDraftRevisionInput) -> DraftRevisionRequest:
        request = DraftRevisionRequest.build(
            executor_request=resolved.executor_request.legacy_request,
            source_draft=resolved.source_draft,
            policy=resolved.policy,
            scope=resolved.scope,
            instructions=resolved.instructions,
        )
        validate_draft_revision_request(request)
        return request


class DraftRevisionPreservationManifestBuilder:
    """Build a content-free structural baseline from source and typed targets."""

    def build(
        self, resolved: ResolvedDraftRevisionInput
    ) -> DraftRevisionPreservationManifest:
        source = resolved.source_draft
        targeted = {_target_key(item) for item in resolved.scope.targets}
        regions = {
            "opening": fingerprint(source.opening),
            "closing": fingerprint(source.closing),
            "cta": fingerprint(source.cta),
            **{f"story:{item.story_id}": fingerprint(item) for item in source.stories},
            **{
                f"transition:{item.from_story_id}:{item.to_story_id}": fingerprint(item)
                for item in source.transitions
            },
        }
        protected = tuple(
            (key, value)
            for key, value in regions.items()
            if _region_target_key(key) not in targeted
        )
        structural_order = (
            tuple(item.story_id for item in source.stories),
            tuple(
                (item.from_story_id, item.to_story_id) for item in source.transitions
            ),
            source.cta is not None,
        )
        return DraftRevisionPreservationManifest.build(
            source_draft_fingerprint=fingerprint(source),
            authorized_target_fingerprints=tuple(
                item.target_fingerprint for item in resolved.scope.targets
            ),
            protected_region_fingerprints=protected,
            protected_metadata_fingerprints=(
                ("episode_id", fingerprint(source.episode_id)),
            ),
            structural_order_fingerprint=fingerprint(structural_order),
            scope_fingerprint=resolved.scope.scope_fingerprint,
        )


class DraftRevisionPreconditionEvaluator:
    """Evaluate all mandatory preconditions once in a canonical order."""

    def evaluate(
        self,
        resolved: ResolvedDraftRevisionInput,
        request: DraftRevisionRequest,
        manifest: DraftRevisionPreservationManifest,
    ) -> DraftRevisionPreconditionEvaluation:
        instruction = resolved.instructions.editorial_instruction.casefold()
        prohibited = (
            (not resolved.policy.allow_factual_changes)
            and any(
                term in instruction
                for term in ("schimbă faptul", "factual", "change fact")
            )
        ) or (
            (not resolved.policy.allow_structural_changes)
            and any(
                term in instruction
                for term in ("schimbă structura", "structural", "new structure")
            )
        )
        regeneration = any(
            phrase in instruction
            for phrase in (
                "rewrite everything",
                "rewrite the entire",
                "rescrie tot",
                "refă tot",
            )
        )
        checks = {
            DraftRevisionPreconditionCode.EXECUTOR_REQUEST_VALID: (True, None),
            DraftRevisionPreconditionCode.CAPABILITY_VALID: (
                request.executor_request.plan.required_capability
                is CorrectiveActionExecutionCapability.DRAFT_REVISION,
                DraftRevisionPreparationDiagnosticCode.CAPABILITY_MISMATCH,
            ),
            DraftRevisionPreconditionCode.ACTION_VALID: (
                request.executor_request.plan.source_action
                is CorrectiveAction.REQUEST_REVISION,
                DraftRevisionPreparationDiagnosticCode.ACTION_MISMATCH,
            ),
            DraftRevisionPreconditionCode.AUTHORIZATION_VALID: (
                resolved.authorization_state
                in (
                    CorrectiveActionAuthorizationState.NOT_REQUIRED,
                    CorrectiveActionAuthorizationState.GRANTED,
                ),
                DraftRevisionPreparationDiagnosticCode.REVISION_NOT_AUTHORIZED,
            ),
            DraftRevisionPreconditionCode.SOURCE_DRAFT_VALID: (
                request.source_draft is resolved.source_draft,
                DraftRevisionPreparationDiagnosticCode.SOURCE_DRAFT_UNAVAILABLE,
            ),
            DraftRevisionPreconditionCode.POLICY_VALID: (
                request.policy is resolved.policy,
                DraftRevisionPreparationDiagnosticCode.INVALID_REVISION_POLICY,
            ),
            DraftRevisionPreconditionCode.SCOPE_VALID: (
                bool(request.scope.targets),
                DraftRevisionPreparationDiagnosticCode.INVALID_REVISION_SCOPE,
            ),
            DraftRevisionPreconditionCode.TARGET_COUNT_VALID: (
                len(request.scope.targets) <= request.policy.maximum_revision_targets,
                DraftRevisionPreparationDiagnosticCode.INVALID_REVISION_SCOPE,
            ),
            DraftRevisionPreconditionCode.INSTRUCTIONS_VALID: (
                request.instructions is resolved.instructions,
                DraftRevisionPreparationDiagnosticCode.INVALID_REVISION_INSTRUCTIONS,
            ),
            DraftRevisionPreconditionCode.REQUEST_PERMITTED: (
                not prohibited,
                DraftRevisionPreparationDiagnosticCode.PROHIBITED_REVISION,
            ),
            DraftRevisionPreconditionCode.NOT_IMPLICIT_REGENERATION: (
                not regeneration,
                DraftRevisionPreparationDiagnosticCode.IMPLICIT_REGENERATION,
            ),
            DraftRevisionPreconditionCode.PRESERVATION_BASELINE_VALID: (
                manifest.source_draft_fingerprint == fingerprint(request.source_draft)
                and manifest.scope_fingerprint == request.scope.scope_fingerprint,
                DraftRevisionPreparationDiagnosticCode.PRESERVATION_BASELINE_FAILED,
            ),
            DraftRevisionPreconditionCode.PROJECTION_SUPPORTED: (True, None),
        }
        findings = tuple(
            DraftRevisionPreconditionFinding.build(
                code=code,
                passed=checks[code][0],
                diagnostic_code=None if checks[code][0] else checks[code][1],
            )
            for code in DraftRevisionPreconditionCode
        )
        return DraftRevisionPreconditionEvaluation.build(
            revision_request_fingerprint=request.request_fingerprint,
            manifest_fingerprint=manifest.manifest_fingerprint,
            findings=findings,
        )


class ControlledGenerationRevisionRequestProjector:
    """Pure projection from authorized capability data into Controlled Revision."""

    def project(
        self,
        executor_request: CorrectiveActionExecutorRequestV2,
        request: DraftRevisionRequest,
        manifest: DraftRevisionPreservationManifest,
    ) -> ControlledRevisionRequest:
        targets = tuple(
            ControlledRevisionTarget.build(
                target_type=RevisionTargetType(item.target_type.value),
                story_id=item.story_id,
                from_story_id=item.from_story_id,
                to_story_id=item.to_story_id,
                upstream_target_fingerprint=item.target_fingerprint,
            )
            for item in request.scope.targets
        )
        policy = ControlledRevisionPolicy.build(
            preserve_unmodified_content=request.policy.preserve_unmodified_content,
            require_explicit_scope=request.policy.require_explicit_scope,
            allow_structural_changes=request.policy.allow_structural_changes,
            allow_factual_changes=request.policy.allow_factual_changes,
            maximum_revision_targets=request.policy.maximum_revision_targets,
            upstream_policy_fingerprint=request.policy.policy_fingerprint,
        )
        instructions = ControlledRevisionInstructions.build(
            editorial_instruction=request.instructions.editorial_instruction,
            authorized_scope_fingerprint=request.scope.scope_fingerprint,
            upstream_instructions_fingerprint=request.instructions.instructions_fingerprint,
        )
        preservation = DraftPreservationRequirements.build(
            source_draft_fingerprint=revision_fingerprint(request.source_draft),
            allowed_target_fingerprints=tuple(
                item.target_fingerprint for item in targets
            ),
            protected_component_fingerprints=(
                *manifest.protected_region_fingerprints,
                *manifest.protected_metadata_fingerprints,
            ),
            immutable_fields=("episode_id",),
            require_structural_compatibility=True,
            upstream_scope_fingerprint=request.scope.scope_fingerprint,
        )
        output_contract = ControlledRevisionOutputContract.build(
            source_draft_fingerprint=revision_fingerprint(request.source_draft),
            preservation_fingerprint=preservation.preservation_fingerprint,
        )
        return ControlledRevisionRequest.build(
            source_draft=request.source_draft,
            revision_targets=targets,
            revision_instructions=instructions,
            revision_policy=policy,
            preservation_requirements=preservation,
            expected_output_contract=output_contract,
            planning_input_fingerprint=executor_request.planning_input.input_fingerprint,
            executor_request_fingerprint=executor_request.request_fingerprint,
        )


class DraftRevisionPreparationResultFactory:
    """Sole owner of authoritative preparation-result shapes."""

    def prepared(
        self,
        *,
        executor_request,
        resolved_input,
        revision_request,
        preservation_manifest,
        precondition_evaluation,
        generation_request,
    ) -> DraftRevisionPreparationResult:
        return DraftRevisionPreparationResult.build(
            executor_request=executor_request,
            resolved_input=resolved_input,
            revision_request=revision_request,
            preservation_manifest=preservation_manifest,
            precondition_evaluation=precondition_evaluation,
            generation_request=generation_request,
            outcome=DraftRevisionPreparationOutcome.PREPARED,
            status=DraftRevisionPreparationStatus.PREPARED,
            lifecycle=DraftRevisionPreparationLifecycle.build(
                tuple(DraftRevisionPreparationPhase)[:10]
            ),
            input_request_fingerprint=executor_request.request_fingerprint,
        )

    def failure(
        self,
        *,
        request_fingerprint: str | None,
        code: DraftRevisionPreparationDiagnosticCode,
        internal: bool,
        reached_phases: tuple[DraftRevisionPreparationPhase, ...],
    ) -> DraftRevisionPreparationResult:
        terminal = (
            DraftRevisionPreparationPhase.FAILED
            if internal
            else DraftRevisionPreparationPhase.REJECTED
        )
        return DraftRevisionPreparationResult.build(
            outcome=(
                DraftRevisionPreparationOutcome.FAILED_INTERNAL
                if internal
                else DraftRevisionPreparationOutcome.REJECTED
            ),
            status=(
                DraftRevisionPreparationStatus.FAILED
                if internal
                else DraftRevisionPreparationStatus.REJECTED
            ),
            diagnostic=DraftRevisionPreparationDiagnostic.build(
                code=code,
                safe_message=(
                    "Draft revision preparation failed internally."
                    if internal
                    else "Draft revision preparation was rejected."
                ),
            ),
            lifecycle=DraftRevisionPreparationLifecycle.build(
                (*reached_phases, terminal)
            ),
            input_request_fingerprint=request_fingerprint,
        )


class DraftRevisionPreparationService:
    """The only public M6C.6D Part 2 preparation entry point."""

    def __init__(
        self,
        *,
        registered_descriptor: CorrectiveActionExecutorDescriptor,
        executor_request_validator: ExecutorRequestValidator,
        input_resolver: DraftRevisionInputResolver,
        preservation_builder: DraftRevisionPreservationManifestBuilder,
        request_factory: DraftRevisionRequestFactory,
        precondition_evaluator: DraftRevisionPreconditionEvaluator,
        projector: ControlledGenerationRevisionRequestProjector,
        generation_request_validator: GenerationRequestValidator,
        result_factory: DraftRevisionPreparationResultFactory,
    ):
        self.registered_descriptor = registered_descriptor
        self.executor_request_validator = executor_request_validator
        self.input_resolver = input_resolver
        self.preservation_builder = preservation_builder
        self.request_factory = request_factory
        self.precondition_evaluator = precondition_evaluator
        self.projector = projector
        self.generation_request_validator = generation_request_validator
        self.result_factory = result_factory

    def prepare(
        self, executor_request: CorrectiveActionExecutorRequestV2
    ) -> DraftRevisionPreparationResult:
        phases = [
            DraftRevisionPreparationPhase.RECEIVED,
            DraftRevisionPreparationPhase.VALIDATING_EXECUTOR_REQUEST,
        ]
        request_fp = getattr(executor_request, "request_fingerprint", None)
        try:
            try:
                self.executor_request_validator(executor_request)
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.INVALID_EXECUTOR_REQUEST
                ) from exc
            self._validate_authoritative_request(executor_request)
            phases.append(DraftRevisionPreparationPhase.RESOLVING_INPUT)
            try:
                resolved = self.input_resolver.resolve(executor_request)
            except DraftRevisionPreparationError:
                raise
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.SOURCE_DRAFT_UNAVAILABLE
                ) from exc
            phases.append(DraftRevisionPreparationPhase.VALIDATING_SCOPE)
            phases.append(DraftRevisionPreparationPhase.BUILDING_PRESERVATION_BASELINE)
            try:
                manifest = self.preservation_builder.build(resolved)
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.PRESERVATION_BASELINE_FAILED
                ) from exc
            phases.append(DraftRevisionPreparationPhase.BUILDING_REVISION_REQUEST)
            try:
                request = self.request_factory.create(resolved)
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.INVALID_REVISION_SCOPE
                ) from exc
            phases.append(DraftRevisionPreparationPhase.EVALUATING_PRECONDITIONS)
            evaluation = self.precondition_evaluator.evaluate(
                resolved, request, manifest
            )
            if not evaluation.passed:
                first = next(item for item in evaluation.findings if not item.passed)
                raise DraftRevisionPreparationError(first.diagnostic_code)
            phases.append(DraftRevisionPreparationPhase.PROJECTING_GENERATION_REQUEST)
            try:
                generation_request = self.projector.project(
                    executor_request, request, manifest
                )
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.GENERATION_PROJECTION_UNSUPPORTED
                ) from exc
            phases.append(DraftRevisionPreparationPhase.VALIDATING_PROJECTION)
            try:
                self.generation_request_validator(generation_request)
            except Exception as exc:
                raise DraftRevisionPreparationError(
                    DraftRevisionPreparationDiagnosticCode.GENERATION_PROJECTION_UNSUPPORTED
                ) from exc
            return self.result_factory.prepared(
                executor_request=executor_request,
                resolved_input=resolved,
                revision_request=request,
                preservation_manifest=manifest,
                precondition_evaluation=evaluation,
                generation_request=generation_request,
            )
        except DraftRevisionPreparationError as exc:
            return self.result_factory.failure(
                request_fingerprint=request_fp,
                code=exc.code,
                internal=False,
                reached_phases=tuple(phases),
            )
        except Exception:
            return self.result_factory.failure(
                request_fingerprint=request_fp,
                code=DraftRevisionPreparationDiagnosticCode.PREPARATION_INTERNAL_FAILURE,
                internal=True,
                reached_phases=tuple(phases),
            )

    def _validate_authoritative_request(self, request):
        if request.executor_descriptor is not self.registered_descriptor:
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.DESCRIPTOR_MISMATCH
            )
        legacy_plan = request.legacy_request.plan
        if legacy_plan.plan_type is not CorrectiveActionExecutionPlanType.REVISE_DRAFT:
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.ACTION_MISMATCH
            )
        if (
            legacy_plan.required_capability
            is not CorrectiveActionExecutionCapability.DRAFT_REVISION
        ):
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.CAPABILITY_MISMATCH
            )
        if legacy_plan.source_action is not CorrectiveAction.REQUEST_REVISION:
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.ACTION_MISMATCH
            )
        if request.execution_context.authorization_state not in (
            CorrectiveActionAuthorizationState.NOT_REQUIRED,
            CorrectiveActionAuthorizationState.GRANTED,
        ):
            raise DraftRevisionPreparationError(
                DraftRevisionPreparationDiagnosticCode.REVISION_NOT_AUTHORIZED
            )


def compose_draft_revision_preparation_service(
    registered_descriptor: CorrectiveActionExecutorDescriptor,
) -> DraftRevisionPreparationService:
    """Compose one deterministic preparation service; invokes no gateway."""

    return DraftRevisionPreparationService(
        registered_descriptor=registered_descriptor,
        executor_request_validator=validate_executor_request_v2,
        input_resolver=DraftRevisionInputResolver(),
        preservation_builder=DraftRevisionPreservationManifestBuilder(),
        request_factory=DraftRevisionRequestFactory(),
        precondition_evaluator=DraftRevisionPreconditionEvaluator(),
        projector=ControlledGenerationRevisionRequestProjector(),
        generation_request_validator=validate_controlled_revision_request,
        result_factory=DraftRevisionPreparationResultFactory(),
    )


def validate_draft_revision_preparation_result(
    value: DraftRevisionPreparationResult,
) -> None:
    if not isinstance(value, DraftRevisionPreparationResult):
        raise TypeError("invalid draft-revision preparation result")
    value.invariants()
    if value.revision_request:
        validate_draft_revision_request(value.revision_request)
    if value.generation_request:
        validate_controlled_revision_request(value.generation_request)


def build_draft_revision_preparation_report(
    result: DraftRevisionPreparationResult,
) -> DraftRevisionPreparationReport:
    resolved = result.resolved_input
    return DraftRevisionPreparationReport.build(
        executor_id=(
            result.executor_request.executor_descriptor.executor_id
            if result.executor_request
            else None
        ),
        capability="draft_revision",
        action="request_revision",
        target_count=len(resolved.scope.targets) if resolved else 0,
        source_draft_fingerprint=(
            fingerprint(resolved.source_draft) if resolved else None
        ),
        policy_fingerprint=(resolved.policy.policy_fingerprint if resolved else None),
        scope_fingerprint=(resolved.scope.scope_fingerprint if resolved else None),
        preservation_manifest_fingerprint=(
            result.preservation_manifest.manifest_fingerprint
            if result.preservation_manifest
            else None
        ),
        generation_request_fingerprint=(
            result.generation_request.revision_request_fingerprint
            if result.generation_request
            else None
        ),
        outcome=result.outcome,
        status=result.status,
        diagnostic_code=result.diagnostic.code if result.diagnostic else None,
        lifecycle=tuple(item.value for item in result.lifecycle.phases),
        preparation_fingerprint=result.preparation_fingerprint,
    )


def serialize_draft_revision_preparation_report(
    report: DraftRevisionPreparationReport,
) -> str:
    return canonical_json(report)


def _target_key(target):
    return (
        target.target_type,
        target.story_id or target.from_story_id,
        target.to_story_id,
    )


def _region_target_key(region):
    if region == "opening":
        return (DraftRevisionTargetType.OPENING, None, None)
    if region == "closing":
        return (DraftRevisionTargetType.CLOSING, None, None)
    if region == "cta":
        return (DraftRevisionTargetType.CALL_TO_ACTION, None, None)
    if region.startswith("story:"):
        return (DraftRevisionTargetType.STORY, int(region.split(":")[1]), None)
    _, source, target = region.split(":")
    return (DraftRevisionTargetType.TRANSITION, int(source), int(target))
