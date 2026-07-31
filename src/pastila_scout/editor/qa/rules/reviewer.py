"""M6C.5A adapter for the deterministic rule engine."""

from pastila_scout.editor.qa.models import (
    EditorialReviewRequest,
    EditorialReviewResult,
    ReviewerCapabilities,
    ReviewerCapability,
    ReviewExecutionStatus,
)
from pastila_scout.editor.qa.rules.concrete import build_supported_rules
from pastila_scout.editor.qa.rules.context import RuleContext
from pastila_scout.editor.qa.rules.engine import RuleEngine
from pastila_scout.editor.qa.rules.policy import DeterministicEditorialRulePolicy
from pastila_scout.editor.qa.rules.registry import RuleRegistry


class DeterministicRulesReviewer:
    """Ordinary offline reviewer; it performs no aggregation or approval."""

    reviewer_id = "deterministic-editorial-rules"
    reviewer_version = "1.0.0"
    capabilities = ReviewerCapabilities(
        values=(
            ReviewerCapability.STRUCTURE,
            ReviewerCapability.RUNTIME,
            ReviewerCapability.CALLBACK,
            ReviewerCapability.LANGUAGE,
            ReviewerCapability.VOICE,
            ReviewerCapability.TRANSITION,
        )
    )

    def __init__(self, policy: DeterministicEditorialRulePolicy | None = None):
        self.policy = policy or DeterministicEditorialRulePolicy()
        self.registry = RuleRegistry(build_supported_rules())
        self.rule_set = self.registry.select()
        self.engine = RuleEngine()
        self.last_execution_result = None

    def review(self, request: EditorialReviewRequest) -> EditorialReviewResult:
        context = RuleContext.from_request(request, self.policy)
        execution = self.engine.execute(context, self.registry, self.rule_set)
        self.last_execution_result = execution
        if execution.failed_rule_count:
            status = ReviewExecutionStatus.REQUIRES_REVIEW
        elif execution.skipped_rule_count:
            status = ReviewExecutionStatus.COMPLETED_WITH_WARNINGS
        else:
            status = ReviewExecutionStatus.COMPLETED
        warnings = tuple(
            f"{record.execution_key}:{record.failure_code.value}"
            for record in execution.failed_rules
        ) + tuple(
            f"{record.execution_key}:{record.reason_code.value}"
            for record in execution.skipped_rules
        )
        return EditorialReviewResult.build(
            reviewer_id=self.reviewer_id,
            reviewer_version=self.reviewer_version,
            status=status,
            findings=execution.findings,
            warnings=warnings,
            reviewed_component_ids=request.component_ids,
        )
