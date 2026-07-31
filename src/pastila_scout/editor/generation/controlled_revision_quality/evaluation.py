"""Deterministic scenario evaluation and bounded failure precedence."""

from __future__ import annotations

from .evaluators import (
    meaning_preserved,
    no_op_compliant,
    preserves_numeric_values,
    preserves_quotes,
    preserves_structure,
    preserves_temporal_values,
    proportional_revision,
)
from .results import DimensionScores, ScenarioEvaluation
from .scenario import FailureCategory, SyntheticRevisionScenario


def evaluate_scenario(scenario: SyntheticRevisionScenario) -> ScenarioEvaluation:
    candidate = scenario.candidate
    text = candidate.draft.assembled_text if candidate.draft else ""
    dimensions = DimensionScores(
        structural_validity=(
            candidate.json_valid
            and candidate.draft is not None
            and candidate.structural_failure is None
        ),
        dto_validity=candidate.dto_valid,
        authorization_validity=candidate.authorization_valid,
        reconstruction_validity=candidate.reconstruction_valid,
        episode_draft_validity=candidate.domain_valid and candidate.draft is not None,
        editorial_acceptance=candidate.editorial_accepted,
        meaning_preservation=(
            meaning_preserved(scenario, text) and candidate.source_authority_preserved
        ),
        protected_structure_preservation=preserves_structure(
            scenario.source_draft, candidate.draft
        ),
        quote_preservation=preserves_quotes(text, scenario.protected_quotes),
        numeric_fact_preservation=preserves_numeric_values(
            text, scenario.protected_numeric_values
        ),
        temporal_fact_preservation=preserves_temporal_values(
            text, scenario.protected_dates
        ),
        source_authority_preservation=candidate.source_authority_preserved,
        no_op_compliance=no_op_compliant(scenario, text),
        instruction_compliance=candidate.instruction_followed,
        revision_proportionality=proportional_revision(scenario, text),
    )
    usable = all(
        (
            candidate.structural_failure is None,
            dimensions.dto_validity,
            dimensions.authorization_validity,
            dimensions.reconstruction_validity,
            dimensions.episode_draft_validity,
            dimensions.editorial_acceptance,
            dimensions.meaning_preservation,
            dimensions.protected_structure_preservation,
        )
    )
    failure = _failure_category(scenario, dimensions, usable)
    return ScenarioEvaluation(
        scenario_key=scenario.scenario_key,
        category=scenario.category,
        dimensions=dimensions,
        usable_revision=usable,
        failure_category=failure,
        consistency_passed=(
            usable == scenario.expected_usable
            and failure is scenario.expected_failure_category
        ),
    )


def _failure_category(scenario, scores, usable):
    candidate = scenario.candidate
    if candidate.structural_failure is not None:
        return candidate.structural_failure
    checks = (
        (not candidate.json_valid, FailureCategory.INVALID_JSON),
        (not candidate.dto_valid, FailureCategory.DTO_REJECTION),
        (not candidate.authorization_valid, FailureCategory.UNAUTHORIZED_REFERENCE),
        (not candidate.reconstruction_valid, FailureCategory.RECONSTRUCTION_FAILURE),
        (not candidate.domain_valid, FailureCategory.DOMAIN_VALIDATION_FAILURE),
        (
            not scores.protected_structure_preservation,
            FailureCategory.PROTECTED_STRUCTURE_MUTATION,
        ),
        (not scores.quote_preservation, FailureCategory.QUOTE_MUTATION),
        (not scores.numeric_fact_preservation, FailureCategory.NUMERIC_FACT_MUTATION),
        (not scores.temporal_fact_preservation, FailureCategory.TEMPORAL_FACT_MUTATION),
        (
            not scores.source_authority_preservation,
            FailureCategory.SOURCE_AUTHORITY_DRIFT,
        ),
        (not scores.meaning_preservation, FailureCategory.MEANING_DRIFT),
        (not scores.instruction_compliance, FailureCategory.INSTRUCTION_NOT_FOLLOWED),
        (not scores.no_op_compliance, FailureCategory.UNNECESSARY_REWRITE),
        (not scores.revision_proportionality, FailureCategory.EDITORIAL_OVER_REVISION),
        (not candidate.editorial_accepted, FailureCategory.EDITORIAL_UNDER_REVISION),
        (not candidate.improved, FailureCategory.VALID_BUT_NOT_IMPROVED),
    )
    return next(
        (category for failed, category in checks if failed),
        FailureCategory.USABLE_REVISION if usable else FailureCategory.DTO_REJECTION,
    )
