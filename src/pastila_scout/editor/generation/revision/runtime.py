"""Authoritative provider-neutral Controlled Revision execution runtime."""

# The service is the approved outer exception boundary; all exceptions are sanitized.
# ruff: noqa: BLE001

from typing import Protocol

from pydantic import ValidationError

from pastila_scout.editor.generation.models import EpisodeDraft

from .contracts import (
    ControlledRevisionDiagnostic,
    ControlledRevisionGatewayResult,
    ControlledRevisionInvocation,
    ControlledRevisionLifecycle,
    ControlledRevisionResult,
)
from .enums import (
    RevisionDiagnosticCode,
    RevisionGatewayStatus,
    RevisionLifecyclePhase,
    RevisionResultStatus,
    RevisionTargetType,
)
from .gateway import ControlledRevisionGateway
from .identity import revision_fingerprint


class InvocationValidator(Protocol):
    def __call__(self, value: ControlledRevisionInvocation) -> None: ...


class GatewayResultValidator(Protocol):
    def __call__(
        self,
        value: ControlledRevisionGatewayResult,
        invocation: ControlledRevisionInvocation | None = None,
    ) -> None: ...


class ResultValidator(Protocol):
    def __call__(
        self,
        value: ControlledRevisionResult,
        *,
        invocation: ControlledRevisionInvocation | None = None,
        gateway_result: ControlledRevisionGatewayResult | None = None,
    ) -> None: ...


class RevisedDraftValidator:
    """Reuse canonical EpisodeDraft validation without reconstructing output."""

    def validate(self, draft: EpisodeDraft) -> None:
        if not isinstance(draft, EpisodeDraft):
            raise TypeError("invalid revised draft")
        try:
            EpisodeDraft.model_validate(draft.model_dump(mode="python"))
        except ValidationError as exc:
            raise ValueError("revised draft integrity validation failed") from exc


class RevisionOutputContractValidator:
    """Validate candidate shape and immutable metadata against the output contract."""

    def validate(
        self, invocation: ControlledRevisionInvocation, revised_draft: EpisodeDraft
    ) -> None:
        request = invocation.request
        contract = request.expected_output_contract
        if (
            contract.output_type != "episode_draft"
            or contract.episode_draft_contract_version != "1"
        ):
            raise ValueError("revision output contract is unsupported")
        if contract.source_draft_fingerprint != revision_fingerprint(
            request.source_draft
        ):
            raise ValueError("revision output source lineage mismatch")
        if (
            contract.preservation_fingerprint
            != request.preservation_requirements.preservation_fingerprint
        ):
            raise ValueError("revision output preservation lineage mismatch")
        if revised_draft.episode_id != request.source_draft.episode_id:
            raise ValueError("revision output immutable episode identity changed")
        if (
            contract.require_distinct_draft_identity
            and revised_draft is request.source_draft
        ):
            raise ValueError("revision output reused source-draft identity")


class RevisionPreservationValidator:
    """Prove by structural comparison that only authorized regions changed."""

    def validate(
        self, invocation: ControlledRevisionInvocation, revised: EpisodeDraft
    ) -> None:
        request = invocation.request
        source = request.source_draft
        requirements = request.preservation_requirements
        targets = {_target_key(item) for item in request.revision_targets}

        if requirements.source_draft_fingerprint != revision_fingerprint(source):
            raise ValueError("revision preservation source lineage mismatch")
        if (
            tuple(sorted(item.target_fingerprint for item in request.revision_targets))
            != requirements.allowed_target_fingerprints
        ):
            raise ValueError("revision preservation target lineage mismatch")
        if revised.episode_id != source.episode_id:
            raise ValueError("protected episode identity changed")
        if requirements.require_structural_compatibility:
            self._validate_structure(source, revised)
        self._validate_untargeted_regions(source, revised, targets)
        self._validate_protected_manifest(
            source, requirements.protected_component_fingerprints
        )

    @staticmethod
    def _validate_structure(source: EpisodeDraft, revised: EpisodeDraft) -> None:
        if tuple(item.story_id for item in revised.stories) != tuple(
            item.story_id for item in source.stories
        ):
            raise ValueError("revision changed protected story structure")
        if tuple(
            (item.from_story_id, item.to_story_id) for item in revised.transitions
        ) != tuple(
            (item.from_story_id, item.to_story_id) for item in source.transitions
        ):
            raise ValueError("revision changed protected transition structure")
        if (source.cta is None) != (revised.cta is None):
            raise ValueError("revision changed protected CTA structure")
        if (
            source.cta
            and revised.cta
            and (
                source.cta.placement,
                source.cta.after_story_id,
                source.cta.static_content,
            )
            != (
                revised.cta.placement,
                revised.cta.after_story_id,
                revised.cta.static_content,
            )
        ):
            raise ValueError("revision changed protected CTA metadata")

    @staticmethod
    def _validate_untargeted_regions(source, revised, targets) -> None:
        if (
            RevisionTargetType.OPENING,
            None,
            None,
        ) not in targets and revised.opening != source.opening:
            raise ValueError("untargeted opening changed")
        if (
            RevisionTargetType.CLOSING,
            None,
            None,
        ) not in targets and revised.closing != source.closing:
            raise ValueError("untargeted closing changed")
        source_stories = {item.story_id: item for item in source.stories}
        for item in revised.stories:
            if (
                RevisionTargetType.STORY,
                item.story_id,
                None,
            ) not in targets and item != source_stories[item.story_id]:
                raise ValueError("untargeted story changed")
        source_transitions = {
            (item.from_story_id, item.to_story_id): item for item in source.transitions
        }
        for item in revised.transitions:
            key = (RevisionTargetType.TRANSITION, item.from_story_id, item.to_story_id)
            if (
                key not in targets
                and item != source_transitions[(item.from_story_id, item.to_story_id)]
            ):
                raise ValueError("untargeted transition changed")
        if (
            RevisionTargetType.CALL_TO_ACTION,
            None,
            None,
        ) not in targets and revised.cta != source.cta:
            raise ValueError("untargeted call to action changed")

    @staticmethod
    def _validate_protected_manifest(source, manifest) -> None:
        actual = _source_component_fingerprints(source)
        for component_id, expected in manifest:
            if component_id not in actual or actual[component_id] != expected:
                raise ValueError("protected component manifest is inconsistent")


class RevisionLifecycleFactory:
    """Sole owner of deterministic terminal lifecycle construction."""

    def success(self) -> ControlledRevisionLifecycle:
        return ControlledRevisionLifecycle.build(
            (
                RevisionLifecyclePhase.CREATED,
                RevisionLifecyclePhase.VALIDATED,
                RevisionLifecyclePhase.INVOKED,
                RevisionLifecyclePhase.GATEWAY_COMPLETED,
                RevisionLifecyclePhase.OUTPUT_VALIDATED,
                RevisionLifecyclePhase.COMPLETED,
            )
        )

    def failure(
        self,
        *,
        gateway_called: bool,
        gateway_returned: bool,
        output_validated: bool = False,
    ) -> ControlledRevisionLifecycle:
        phases = [RevisionLifecyclePhase.CREATED, RevisionLifecyclePhase.VALIDATED]
        if gateway_called:
            phases.append(RevisionLifecyclePhase.INVOKED)
        if gateway_returned:
            phases.append(RevisionLifecyclePhase.GATEWAY_COMPLETED)
        if output_validated:
            phases.append(RevisionLifecyclePhase.OUTPUT_VALIDATED)
        phases.append(RevisionLifecyclePhase.FAILED)
        return ControlledRevisionLifecycle.build(tuple(phases))

    def invalid_invocation(self) -> ControlledRevisionLifecycle:
        return ControlledRevisionLifecycle.build(
            (RevisionLifecyclePhase.CREATED, RevisionLifecyclePhase.FAILED)
        )


class ControlledRevisionResultFactory:
    """Sole owner of terminal Controlled Revision result construction."""

    def __init__(self, lifecycle_factory: RevisionLifecycleFactory):
        self.lifecycle_factory = lifecycle_factory

    def success(
        self,
        invocation: ControlledRevisionInvocation,
        gateway_result: ControlledRevisionGatewayResult,
    ) -> ControlledRevisionResult:
        return ControlledRevisionResult.build(
            status=RevisionResultStatus.SUCCESS,
            revised_draft=gateway_result.revised_draft,
            source_draft_fingerprint=gateway_result.source_draft_fingerprint,
            revision_request_fingerprint=gateway_result.revision_request_fingerprint,
            invocation_fingerprint=gateway_result.invocation_fingerprint,
            gateway_result_fingerprint=gateway_result.gateway_result_fingerprint,
            output_contract_fingerprint=gateway_result.output_contract_fingerprint,
            preservation_fingerprint=gateway_result.preservation_fingerprint,
            lifecycle=self.lifecycle_factory.success(),
        )

    def failure(
        self,
        invocation: ControlledRevisionInvocation,
        *,
        status: RevisionResultStatus,
        diagnostic_code: RevisionDiagnosticCode,
        safe_message: str,
        gateway_result: ControlledRevisionGatewayResult | None = None,
        gateway_called: bool,
        gateway_returned: bool,
        output_validated: bool = False,
        invalid_invocation: bool = False,
    ) -> ControlledRevisionResult:
        request = invocation.request
        diagnostic = ControlledRevisionDiagnostic.build(
            code=diagnostic_code, safe_message=safe_message
        )
        gateway_fp = (
            gateway_result.gateway_result_fingerprint
            if gateway_result is not None
            else revision_fingerprint(
                {
                    "gateway_result": "unavailable",
                    "invocation_fingerprint": invocation.invocation_fingerprint,
                    "gateway_called": gateway_called,
                }
            )
        )
        lifecycle = (
            self.lifecycle_factory.invalid_invocation()
            if invalid_invocation
            else self.lifecycle_factory.failure(
                gateway_called=gateway_called,
                gateway_returned=gateway_returned,
                output_validated=output_validated,
            )
        )
        return ControlledRevisionResult.build(
            status=status,
            revised_draft=None,
            source_draft_fingerprint=revision_fingerprint(request.source_draft),
            revision_request_fingerprint=request.revision_request_fingerprint,
            invocation_fingerprint=invocation.invocation_fingerprint,
            gateway_result_fingerprint=gateway_fp,
            output_contract_fingerprint=request.expected_output_contract.output_contract_fingerprint,
            preservation_fingerprint=request.preservation_requirements.preservation_fingerprint,
            lifecycle=lifecycle,
            diagnostic=diagnostic,
        )


class ControlledRevisionExecutionService:
    """The only production runtime entry point for Controlled Revision."""

    def __init__(
        self,
        *,
        gateway: ControlledRevisionGateway,
        invocation_validator: InvocationValidator,
        gateway_result_validator: GatewayResultValidator,
        revised_draft_validator: RevisedDraftValidator,
        output_contract_validator: RevisionOutputContractValidator,
        preservation_validator: RevisionPreservationValidator,
        result_factory: ControlledRevisionResultFactory,
        result_validator: ResultValidator,
    ):
        self.gateway = gateway
        self.invocation_validator = invocation_validator
        self.gateway_result_validator = gateway_result_validator
        self.revised_draft_validator = revised_draft_validator
        self.output_contract_validator = output_contract_validator
        self.preservation_validator = preservation_validator
        self.result_factory = result_factory
        self.result_validator = result_validator

    def execute(
        self, invocation: ControlledRevisionInvocation
    ) -> ControlledRevisionResult:
        try:
            self.invocation_validator(invocation)
        except Exception:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.CONTRACT_FAILURE,
                code=RevisionDiagnosticCode.INVALID_REVISION_REQUEST,
                message="Controlled revision invocation is invalid.",
                gateway_called=False,
                gateway_returned=False,
                invalid_invocation=True,
            )

        try:
            gateway_result = self.gateway.revise(invocation)
        except Exception:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.GATEWAY_FAILURE,
                code=RevisionDiagnosticCode.REVISION_GATEWAY_FAILURE,
                message="Controlled revision gateway failed.",
                gateway_called=True,
                gateway_returned=False,
            )

        if not isinstance(gateway_result, ControlledRevisionGatewayResult):
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.CONTRACT_FAILURE,
                code=RevisionDiagnosticCode.INVALID_REVISION_GATEWAY_RESULT,
                message="Controlled revision gateway result is invalid.",
                gateway_called=True,
                gateway_returned=True,
            )
        try:
            self.gateway_result_validator(gateway_result, invocation)
        except Exception as exc:
            code = (
                RevisionDiagnosticCode.REVISION_LINEAGE_MISMATCH
                if "lineage" in str(exc).casefold()
                else RevisionDiagnosticCode.INVALID_REVISION_GATEWAY_RESULT
            )
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.CONTRACT_FAILURE,
                code=code,
                message=(
                    "Controlled revision gateway lineage is invalid."
                    if code is RevisionDiagnosticCode.REVISION_LINEAGE_MISMATCH
                    else "Controlled revision gateway result is invalid."
                ),
                gateway_result=gateway_result,
                gateway_called=True,
                gateway_returned=True,
            )
        if gateway_result.status is not RevisionGatewayStatus.SUCCESS:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.GATEWAY_FAILURE,
                code=RevisionDiagnosticCode.REVISION_GATEWAY_FAILURE,
                message="Controlled revision gateway reported failure.",
                gateway_result=gateway_result,
                gateway_called=True,
                gateway_returned=True,
            )

        revised = gateway_result.revised_draft
        try:
            self.revised_draft_validator.validate(revised)
            self.output_contract_validator.validate(invocation, revised)
        except Exception:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.REJECTED,
                code=RevisionDiagnosticCode.REVISION_OUTPUT_INVALID,
                message="Controlled revision output is invalid.",
                gateway_result=gateway_result,
                gateway_called=True,
                gateway_returned=True,
            )
        try:
            self.preservation_validator.validate(invocation, revised)
        except Exception:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.REJECTED,
                code=RevisionDiagnosticCode.INVALID_PRESERVATION_REQUIREMENTS,
                message="Controlled revision preservation validation failed.",
                gateway_result=gateway_result,
                gateway_called=True,
                gateway_returned=True,
                output_validated=True,
            )
        try:
            result = self.result_factory.success(invocation, gateway_result)
            self.result_validator(
                result, invocation=invocation, gateway_result=gateway_result
            )
            return result
        except Exception:
            return self._validated_failure(
                invocation,
                status=RevisionResultStatus.CONTRACT_FAILURE,
                code=RevisionDiagnosticCode.REVISION_LIFECYCLE_INVALID,
                message="Controlled revision finalization failed.",
                gateway_result=gateway_result,
                gateway_called=True,
                gateway_returned=True,
                output_validated=True,
            )

    def _validated_failure(self, invocation, **values):
        values["diagnostic_code"] = values.pop("code")
        values["safe_message"] = values.pop("message")
        result = self.result_factory.failure(invocation, **values)
        self.result_validator(result, invocation=invocation)
        return result


def _target_key(target):
    return (
        target.target_type,
        target.story_id or target.from_story_id,
        target.to_story_id,
    )


def _source_component_fingerprints(draft: EpisodeDraft) -> dict[str, str]:
    values = {
        "episode_id": revision_fingerprint(draft.episode_id),
        "opening": revision_fingerprint(draft.opening),
        "closing": revision_fingerprint(draft.closing),
        "cta": revision_fingerprint(draft.cta),
    }
    values.update(
        {f"story:{item.story_id}": revision_fingerprint(item) for item in draft.stories}
    )
    values.update(
        {
            f"transition:{item.from_story_id}:{item.to_story_id}": revision_fingerprint(
                item
            )
            for item in draft.transitions
        }
    )
    return values
