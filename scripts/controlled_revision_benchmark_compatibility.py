"""Offline production compatibility composition for the frozen benchmark corpus."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderConfiguration,
    AIProviderExecutionRequest,
    AIRetryPolicy,
    AIStructuredOutputCapabilities,
    AIStructuredOutputMode,
    ProjectedAIProviderRequest,
)
from pastila_scout.editor.generation.ai_provider_adapter.openai.projector import (
    OpenAIControlledRevisionProjector,
)
from pastila_scout.editor.generation.controlled_revision_quality.scenario import (
    ScenarioCategory,
    SyntheticRevisionScenario,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionInstructions,
    ControlledRevisionInvocation,
    ControlledRevisionOutputContract,
    ControlledRevisionPolicy,
    ControlledRevisionRequest,
    ControlledRevisionTarget,
    DraftPreservationRequirements,
    RevisionTargetType,
    revision_fingerprint,
)
from scripts.openai_controlled_revision_acceptance import (
    EditorialAcceptanceSpecification,
)


@dataclass(frozen=True, slots=True)
class ProviderCompatibilityResult:
    scenario_key: str
    authorization_valid: bool
    instruction_valid: bool
    request_valid: bool
    projection_valid: bool
    acceptance_present: bool

    @property
    def compatible(self) -> bool:
        return all(
            (
                self.authorization_valid,
                self.instruction_valid,
                self.request_valid,
                self.projection_valid,
                self.acceptance_present,
            )
        )


def production_benchmark_configuration() -> AIProviderConfiguration:
    return AIProviderConfiguration(
        provider_identifier="openai",
        model_identifier="gpt-4.1-mini",
        authentication_reference="env:OPENAI_API_KEY",
        timeout_seconds=30,
        retry_policy=AIRetryPolicy(maximum_attempts=1),
        structured_output=AIStructuredOutputCapabilities(
            supported_modes=(
                AIStructuredOutputMode.JSON,
                AIStructuredOutputMode.SCHEMA_CONSTRAINED,
            )
        ),
        maximum_context_tokens=32_000,
    )


def build_production_invocation(
    scenario: SyntheticRevisionScenario,
) -> ControlledRevisionInvocation:
    scope = _fingerprint(f"{scenario.scenario_key}:scope")
    executor = _fingerprint(f"{scenario.scenario_key}:executor")
    targets = tuple(_target(value, scope) for value in scenario.authorized_components)
    policy = ControlledRevisionPolicy.build(
        maximum_revision_targets=len(targets), upstream_policy_fingerprint=scope
    )
    instructions = ControlledRevisionInstructions.build(
        editorial_instruction=scenario.revision_instruction,
        authorized_scope_fingerprint=scope,
        upstream_instructions_fingerprint=executor,
    )
    source_fingerprint = revision_fingerprint(scenario.source_draft)
    preservation = DraftPreservationRequirements.build(
        source_draft_fingerprint=source_fingerprint,
        allowed_target_fingerprints=tuple(item.target_fingerprint for item in targets),
        protected_component_fingerprints=(),
        upstream_scope_fingerprint=scope,
    )
    output = ControlledRevisionOutputContract.build(
        source_draft_fingerprint=source_fingerprint,
        preservation_fingerprint=preservation.preservation_fingerprint,
    )
    request = ControlledRevisionRequest.build(
        source_draft=scenario.source_draft,
        revision_targets=targets,
        revision_instructions=instructions,
        revision_policy=policy,
        preservation_requirements=preservation,
        expected_output_contract=output,
        planning_input_fingerprint=scope,
        executor_request_fingerprint=executor,
    )
    return ControlledRevisionInvocation.build(request=request)


def project_production_request(
    scenario: SyntheticRevisionScenario,
    invocation: ControlledRevisionInvocation | None = None,
) -> ProjectedAIProviderRequest:
    invocation = invocation or build_production_invocation(scenario)
    configuration = production_benchmark_configuration()
    execution = AIProviderExecutionRequest(
        execution_identifier=_fingerprint(f"{scenario.scenario_key}:execution"),
        invocation=invocation,
        provider_identifier=configuration.provider_identifier,
        model_identifier=configuration.model_identifier,
        correlation_identifier=invocation.invocation_fingerprint,
    )
    return OpenAIControlledRevisionProjector(configuration).project(execution)


def build_editorial_acceptance_specification(
    scenario: SyntheticRevisionScenario,
) -> EditorialAcceptanceSpecification:
    acceptance = scenario.acceptance_specification
    return EditorialAcceptanceSpecification(
        target_references=acceptance.allowed_editable_targets,
        required_facts=scenario.protected_facts,
        required_numeric_values=acceptance.required_preserved_numeric_facts,
        required_dates=acceptance.required_preserved_dates,
        required_times=(),
        required_entities=(),
        allowed_numeric_values=frozenset(acceptance.required_preserved_numeric_facts),
        forbidden_terms=(),
        require_meaningful_revision=not acceptance.expected_no_op,
        require_substantial_revision=(
            scenario.category is ScenarioCategory.SUBSTANTIAL_REWRITE
        ),
        source_authority_applicable=scenario.category
        in {ScenarioCategory.SOURCE_AUTHORITY, ScenarioCategory.ADVERSARIAL_AMBIGUITY},
    )


def validate_provider_compatibility(
    scenario: SyntheticRevisionScenario,
) -> ProviderCompatibilityResult:
    invocation = build_production_invocation(scenario)
    projected = project_production_request(scenario, invocation)
    acceptance = build_editorial_acceptance_specification(scenario)
    request = invocation.request
    target_keys = tuple(item.canonical_key for item in request.revision_targets)
    return ProviderCompatibilityResult(
        scenario_key=scenario.scenario_key,
        authorization_valid=bool(target_keys)
        and tuple(scenario.authorized_components)
        == scenario.acceptance_specification.allowed_editable_targets,
        instruction_valid=(
            request.revision_instructions.editorial_instruction
            == scenario.revision_instruction
        ),
        request_valid=request.source_draft is scenario.source_draft,
        projection_valid=(
            projected.invocation is invocation
            and projected.invocation_fingerprint == invocation.invocation_fingerprint
        ),
        acceptance_present=bool(acceptance.target_references),
    )


def _target(reference: str, scope: str) -> ControlledRevisionTarget:
    parts = reference.split(":")
    values: dict[str, object] = {
        "target_type": RevisionTargetType(parts[0]),
        "upstream_target_fingerprint": scope,
    }
    if parts[0] == "story":
        values["story_id"] = int(parts[1])
    elif parts[0] == "transition":
        values["from_story_id"] = int(parts[1])
        values["to_story_id"] = int(parts[2])
    return ControlledRevisionTarget.build(**values)


def _fingerprint(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"
