"""Deterministic structural aggregation and minimal approval policy."""

from collections import Counter

from pastila_scout.editor.qa.models import (
    ApprovalStatus,
    CoverageEntry,
    EditorialApprovalDecision,
    EditorialApprovalPolicy,
    EditorialReviewReport,
    EditorialSeverity,
    FindingCount,
    FindingGroup,
    RequiredAction,
    fingerprint,
)


class FindingAggregationError(ValueError):
    pass


class FindingAggregator:
    """Aggregate findings structurally without semantic merging or rewriting."""

    def aggregate(self, *, draft, manifest, state):
        component_order = _component_order(draft)
        findings = tuple(
            sorted(
                state.accepted_findings,
                key=lambda item: (
                    -int(item.severity),
                    component_order.get(item.location.component_id, -1),
                    item.scope.value,
                    item.reviewer_id,
                    item.issue_code,
                    item.finding_id,
                ),
            )
        )
        ids = [item.finding_id for item in findings]
        if len(ids) != len(set(ids)):
            raise FindingAggregationError("duplicate finding IDs")
        counts = Counter(item.severity for item in findings)
        finding_counts = tuple(
            FindingCount(severity=severity, count=counts[severity])
            for severity in EditorialSeverity
        )
        group_counts = Counter(
            (
                item.severity,
                item.scope,
                item.location.component_id,
                item.reviewer_id,
            )
            for item in findings
        )
        finding_groups = tuple(
            FindingGroup(
                severity=key[0],
                scope=key[1],
                component_id=key[2],
                reviewer_id=key[3],
                count=count,
            )
            for key, count in sorted(
                group_counts.items(),
                key=lambda item: (
                    -int(item[0][0]),
                    component_order.get(item[0][2], -1),
                    item[0][1].value,
                    item[0][3],
                ),
            )
        )
        blocking_ids = tuple(item.finding_id for item in findings if item.blocking)
        results = {item.reviewer_id: item for item in state.review_results}
        failures = {item.manifest_item_id for item in state.reviewer_failures}
        coverage = tuple(
            CoverageEntry(
                reviewer_id=item.reviewer_id,
                scope=item.scope,
                component_ids=item.target_component_ids,
                completed=item.reviewer_id in results
                and item.manifest_item_id not in failures,
                required=item.required,
            )
            for item in manifest.items
            if item.operation == "review"
        )
        draft_fingerprint = fingerprint(draft)
        payload = {
            "episode_draft_fingerprint": draft_fingerprint,
            "manifest_fingerprint": manifest.manifest_fingerprint,
            "review_results": state.review_results,
            "findings": findings,
            "finding_counts": finding_counts,
            "finding_groups": finding_groups,
            "blocking_finding_ids": blocking_ids,
            "reviewer_failures": state.reviewer_failures,
            "warnings": state.warnings,
            "coverage": coverage,
        }
        report_fingerprint = fingerprint(payload)
        return EditorialReviewReport(
            report_id="qa-report:" + report_fingerprint,
            episode_draft_fingerprint=draft_fingerprint,
            manifest_fingerprint=manifest.manifest_fingerprint,
            review_results=state.review_results,
            findings=findings,
            finding_counts=finding_counts,
            finding_groups=finding_groups,
            blocking_finding_ids=blocking_ids,
            reviewer_failures=state.reviewer_failures,
            warnings=state.warnings,
            coverage=coverage,
            report_fingerprint=report_fingerprint,
        )


class ApprovalPolicyEngine:
    """Apply the minimal deterministic M6C.5A approval policy."""

    def decide(self, report, policy=None):
        policy = policy or EditorialApprovalPolicy()
        required_failure = any(item.required for item in report.reviewer_failures)
        critical = tuple(
            item
            for item in report.findings
            if item.severity is EditorialSeverity.CRITICAL
        )
        errors = tuple(
            item
            for item in report.findings
            if item.severity is EditorialSeverity.ERROR and item.blocking
        )
        warnings = tuple(
            item
            for item in report.findings
            if item.severity is EditorialSeverity.WARNING
        )
        optional_failure = any(not item.required for item in report.reviewer_failures)
        if required_failure:
            status = policy.required_failure_status
            action = RequiredAction.REVIEW_MANUALLY
            reasons = ("required_reviewer_failed",)
        elif critical:
            status = policy.critical_status
            action = RequiredAction.REJECT_EPISODE
            reasons = ("critical_finding",)
        elif errors:
            status = ApprovalStatus.REQUIRES_REGENERATION
            action = RequiredAction.REGENERATE_COMPONENTS
            reasons = ("blocking_error",)
        elif warnings or optional_failure or report.warnings:
            status = ApprovalStatus.APPROVED_WITH_WARNINGS
            action = RequiredAction.NONE
            reasons = ("non_blocking_warning",)
        else:
            status = ApprovalStatus.APPROVED
            action = RequiredAction.NONE
            reasons = ("no_blocking_findings",)
        warning_ids = tuple(item.finding_id for item in warnings)
        targets = tuple(
            dict.fromkeys(
                item.location.component_id
                for item in (*critical, *errors)
                if item.location.component_id is not None
            )
        )
        payload = {
            "status": status,
            "reason_codes": reasons,
            "blocking_finding_ids": report.blocking_finding_ids,
            "warning_finding_ids": warning_ids,
            "required_action": action,
            "target_component_ids": targets,
            "decision_policy_id": policy.policy_id,
            "decision_policy_version": policy.policy_version,
        }
        return EditorialApprovalDecision(
            **payload,
            decision_fingerprint=fingerprint(payload),
        )


def _component_order(draft):
    values = {None: -1, "opening": 0}
    index = 1
    for position, _story in enumerate(draft.stories, 1):
        values[f"story-{position:02d}"] = index
        index += 1
        if position <= len(draft.transitions):
            values[f"transition-{position:02d}-{position + 1:02d}"] = index
            index += 1
    if draft.cta is not None:
        values["cta"] = index
        index += 1
    values["closing"] = index
    values["teleprompter"] = index + 1
    return values
