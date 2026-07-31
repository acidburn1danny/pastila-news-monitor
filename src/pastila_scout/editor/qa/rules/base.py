"""Rule protocol and shared deterministic applicability behavior."""

from typing import Protocol

from pastila_scout.editor.qa.models import (
    EditorialFinding,
    EditorialSeverity,
    ReviewScope,
)
from pastila_scout.editor.qa.rules.context import RuleContext
from pastila_scout.editor.qa.rules.models import (
    RuleApplicability,
    RuleApplicabilityReason,
    RuleApplicabilityStatus,
    RuleCapability,
    RuleCategory,
)


class EditorialRule(Protocol):
    rule_id: str
    rule_version: str
    category: RuleCategory
    description: str
    default_severity: EditorialSeverity
    blocking: bool
    supported_scopes: tuple[ReviewScope, ...]
    capabilities: tuple[RuleCapability, ...]

    def applicability(self, context: RuleContext) -> RuleApplicability: ...

    def evaluate(self, context: RuleContext) -> tuple[EditorialFinding, ...]: ...


def scope_applicability(rule: EditorialRule, context: RuleContext) -> RuleApplicability:
    if context.requested_scope not in (ReviewScope.EPISODE, *rule.supported_scopes):
        return RuleApplicability(
            status=RuleApplicabilityStatus.SKIPPED,
            reason_code=RuleApplicabilityReason.SCOPE_NOT_SUPPORTED,
        )
    targets = tuple(
        item.component_id for item in context.target_entries(rule.supported_scopes)
    )
    if context.requested_scope is not ReviewScope.EPISODE and not targets:
        return RuleApplicability(
            status=RuleApplicabilityStatus.SKIPPED,
            reason_code=RuleApplicabilityReason.NO_TARGET_COMPONENTS,
        )
    return RuleApplicability(
        status=RuleApplicabilityStatus.APPLICABLE,
        target_component_ids=targets,
    )
