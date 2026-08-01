"""Offline architecture tests for M6C.5A Editorial QA."""

import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation import DraftAssembler
from pastila_scout.editor.generation.models import CommentaryBlockResult, DraftStory
from pastila_scout.editor.qa import (
    ApprovalStatus,
    EditorialConfidence,
    EditorialFinding,
    EditorialIssueFamily,
    EditorialQAOrchestrator,
    EditorialQAState,
    EditorialReviewManifest,
    EditorialReviewResult,
    EditorialSeverity,
    FindingLocation,
    NoOpEditorialReviewer,
    RequiredAction,
    ReviewerCapabilities,
    ReviewerCapability,
    ReviewerPlan,
    ReviewScope,
    ScriptedEditorialReviewer,
)
from pastila_scout.editor.qa.manifest import InvalidReviewManifestError
from pastila_scout.editor.qa.models import (
    EvidenceItem,
    ManifestStatus,
    ReviewExecutionStatus,
)
from pastila_scout.editor.qa.reviewer import ReviewerExecutionError


def draft():
    block = CommentaryBlockResult(
        block_type="commentary",
        text="Comentariu controlat.",
        sequence=1,
        source_fact_ids=("fact-1",),
        blueprint_intent_ids=("editorial-1",),
        voice_plan_ids=("voice-1",),
        satire_target_ids=(),
        protected_target_ids=(),
    )
    story = DraftStory(
        story_id=10,
        factual_summary="Fapt confirmat.",
        commentary_blocks=(block,),
        ending="Final controlat.",
    )
    return DraftAssembler().assemble(
        episode_id="episode-1",
        story_order=(10,),
        opening="Deschidere.",
        stories=(story,),
        transitions=(),
        closing="Închidere.",
        cta=None,
    )


def finding(
    reviewer_id="reviewer",
    severity=EditorialSeverity.WARNING,
    *,
    component="story-01",
    code="structure.example",
):
    scope = ReviewScope.EPISODE if component is None else ReviewScope.STORY
    return EditorialFinding.build(
        reviewer_id=reviewer_id,
        issue_family=EditorialIssueFamily.STRUCTURE,
        issue_code=code,
        severity=severity,
        confidence=EditorialConfidence.HIGH,
        scope=scope,
        location=FindingLocation(
            component_type=scope,
            component_id=component,
            story_position=1 if component else None,
        ),
        summary="Observație structurală.",
        explanation="Constatare structurată fără text de înlocuire.",
        evidence=(EvidenceItem(evidence_id="e1", text="Fragment scurt."),),
        recommendation="Revizuire manuală a componentei.",
        blocking=severity >= EditorialSeverity.ERROR,
        waivable=severity is not EditorialSeverity.CRITICAL,
    )


def result(reviewer_id, findings=(), *, warnings=(), status=None):
    status = status or (
        ReviewExecutionStatus.COMPLETED_WITH_WARNINGS
        if warnings
        else ReviewExecutionStatus.COMPLETED
    )
    return EditorialReviewResult.build(
        reviewer_id=reviewer_id,
        reviewer_version="1",
        status=status,
        findings=findings,
        warnings=warnings,
        reviewed_component_ids=("opening", "story-01", "closing", "teleprompter"),
    )


def reviewer(reviewer_id, responses, capabilities=(ReviewerCapability.STRUCTURE,)):
    return ScriptedEditorialReviewer(
        reviewer_id,
        responses,
        capabilities=ReviewerCapabilities(values=capabilities),
    )


def test_severity_order_confidence_and_location_validation() -> None:
    assert list(EditorialSeverity) == [
        EditorialSeverity.INFO,
        EditorialSeverity.WARNING,
        EditorialSeverity.ERROR,
        EditorialSeverity.CRITICAL,
    ]
    assert EditorialSeverity.CRITICAL > EditorialSeverity.ERROR
    assert EditorialConfidence.HIGH.value == "high"
    with pytest.raises(ValidationError, match="character_end"):
        FindingLocation(
            component_type=ReviewScope.STORY, component_id="story-01", character_end=2
        )
    with pytest.raises(ValidationError, match="both story positions"):
        FindingLocation(
            component_type=ReviewScope.TRANSITION, component_id="transition-01-02"
        )


def test_finding_id_is_deterministic_and_contract_is_immutable() -> None:
    first = finding()
    second = finding()
    assert first.finding_id == second.finding_id
    with pytest.raises(ValidationError):
        first.summary = "changed"
    with pytest.raises(ValidationError, match="blocking"):
        EditorialFinding.build(
            **(
                first.model_dump(mode="python", exclude={"finding_id"})
                | {"blocking": True, "severity": EditorialSeverity.WARNING}
            )
        )
    with pytest.raises(ValidationError):
        EvidenceItem(evidence_id="long", text="x" * 501)


def test_manifest_is_deterministic_ordered_and_dependency_driven() -> None:
    plans = (
        ReviewerPlan(
            reviewer_id="voice",
            reviewer_version="1",
            capabilities=ReviewerCapabilities(values=(ReviewerCapability.VOICE,)),
        ),
        ReviewerPlan(
            reviewer_id="structure",
            reviewer_version="1",
            capabilities=ReviewerCapabilities(values=(ReviewerCapability.STRUCTURE,)),
        ),
    )
    first = EditorialReviewManifest.build(plans)
    second = EditorialReviewManifest.build(tuple(reversed(plans)))
    assert first == second
    assert first.items[-2].manifest_item_id == "aggregate-findings"
    assert first.items[-1].dependencies == ("aggregate-findings",)
    statuses = {
        item.manifest_item_id: ManifestStatus.COMPLETED for item in first.items[:-2]
    }
    assert first.items[-2].derived_status(statuses) is ManifestStatus.READY
    with pytest.raises(InvalidReviewManifestError):
        EditorialReviewManifest.build((plans[0], plans[0]))


def test_noop_and_scripted_reviewers_record_calls_offline() -> None:
    no_op = NoOpEditorialReviewer()
    output = EditorialQAOrchestrator((no_op,)).review(draft())
    assert len(no_op.calls) == 1
    assert not output.report.findings
    assert output.decision.status is ApprovalStatus.APPROVED
    scripted = reviewer("scripted", [result("scripted", (finding("scripted"),))])
    scripted_output = EditorialQAOrchestrator((scripted,)).review(draft())
    assert len(scripted.calls) == 1
    assert len(scripted_output.report.findings) == 1


def test_state_is_deeply_immutable_and_updates_atomically() -> None:
    state = EditorialQAState()
    review_result = result("reviewer", (finding(),))
    next_state = state.accept_result("review-reviewer-episode", review_result)
    assert next_state is not state
    assert state.revision == 0 and next_state.revision == 1
    assert not state.review_results and len(next_state.review_results) == 1
    assert all(
        isinstance(value, tuple) or not isinstance(value, (dict, list, set))
        for value in state.__dict__.values()
    )
    with pytest.raises(ValidationError):
        state.revision = 2
    with pytest.raises(ValueError, match="already completed"):
        next_state.accept_result("review-reviewer-episode", review_result)


@pytest.mark.parametrize(
    ("findings", "expected", "action"),
    [
        ((), ApprovalStatus.APPROVED, RequiredAction.NONE),
        ((finding(),), ApprovalStatus.APPROVED_WITH_WARNINGS, RequiredAction.NONE),
        (
            (finding(severity=EditorialSeverity.ERROR),),
            ApprovalStatus.REQUIRES_REGENERATION,
            RequiredAction.REGENERATE_COMPONENTS,
        ),
        (
            (finding(severity=EditorialSeverity.CRITICAL),),
            ApprovalStatus.REJECTED,
            RequiredAction.REJECT_EPISODE,
        ),
    ],
)
def test_minimal_approval_policy(findings, expected, action) -> None:
    qa_reviewer = reviewer("reviewer", [result("reviewer", findings)])
    output = EditorialQAOrchestrator((qa_reviewer,)).review(draft())
    assert output.decision.status is expected
    assert output.decision.required_action is action


def test_required_failure_requires_human_review_and_registers_no_findings() -> None:
    failed = reviewer("required", [ReviewerExecutionError("offline failure")])
    output = EditorialQAOrchestrator((failed,)).review(
        draft(), required_reviewer_ids=("required",)
    )
    assert output.decision.status is ApprovalStatus.REQUIRES_HUMAN_REVIEW
    assert output.decision.required_action is RequiredAction.REVIEW_MANUALLY
    assert not output.state.accepted_findings
    assert output.report.reviewer_failures[0].required is True


def test_optional_failure_is_visible_and_policy_controlled() -> None:
    required = NoOpEditorialReviewer("required")
    optional = reviewer("optional", [ReviewerExecutionError("offline failure")])
    output = EditorialQAOrchestrator((optional, required)).review(
        draft(), required_reviewer_ids=("required",)
    )
    assert output.decision.status is ApprovalStatus.APPROVED_WITH_WARNINGS
    assert output.report.reviewer_failures[0].required is False


def test_invalid_location_identity_and_duplicate_findings_become_failures() -> None:
    invalid_location = finding("bad", component="story-99")
    bad = reviewer("bad", [result("bad", (invalid_location,))])
    output = EditorialQAOrchestrator((bad,)).review(draft())
    assert output.decision.status is ApprovalStatus.REQUIRES_HUMAN_REVIEW
    mismatch = reviewer("expected", [result("different")])
    mismatch_output = EditorialQAOrchestrator((mismatch,)).review(draft())
    assert mismatch_output.report.reviewer_failures
    duplicate = finding("duplicate")
    with pytest.raises(ValidationError, match="unique"):
        result("duplicate", (duplicate, duplicate))


def test_aggregation_order_counts_blocking_coverage_and_trace() -> None:
    warning = finding("z-reviewer", code="structure.z")
    error = finding("a-reviewer", severity=EditorialSeverity.ERROR, code="structure.a")
    reviewers = (
        reviewer("z-reviewer", [result("z-reviewer", (warning,))]),
        reviewer("a-reviewer", [result("a-reviewer", (error,))]),
    )
    output = EditorialQAOrchestrator(reviewers).review(draft())
    assert output.report.findings == (error, warning)
    assert output.report.blocking_finding_ids == (error.finding_id,)
    assert sum(item.count for item in output.report.finding_counts) == 2
    assert sum(item.count for item in output.report.finding_groups) == 2
    assert all(item.completed for item in output.report.coverage)
    assert tuple(item.sequence_number for item in output.trace.records) == tuple(
        range(1, len(output.trace.records) + 1)
    )


def test_end_to_end_is_reproducible_and_does_not_mutate_draft() -> None:
    episode = draft()
    snapshot = episode.model_dump(mode="json")
    first = EditorialQAOrchestrator(
        (NoOpEditorialReviewer("b"), NoOpEditorialReviewer("a"))
    ).review(episode)
    second = EditorialQAOrchestrator(
        (NoOpEditorialReviewer("a"), NoOpEditorialReviewer("b"))
    ).review(episode)
    assert first.manifest.manifest_fingerprint == second.manifest.manifest_fingerprint
    assert first.report.report_fingerprint == second.report.report_fingerprint
    assert first.decision.decision_fingerprint == second.decision.decision_fingerprint
    assert episode.model_dump(mode="json") == snapshot


def test_finding_report_and_decision_fingerprints_are_cross_process_stable() -> None:
    code = """
from test_editorial_qa_architecture import draft
from pastila_scout.editor.qa import EditorialQAOrchestrator, NoOpEditorialReviewer
from pastila_scout.editor.qa.models import fingerprint
r = EditorialQAOrchestrator((NoOpEditorialReviewer('noop'),)).review(draft())
print(fingerprint({'set': {'a','b','c','d','e'}}), r.report.report_fingerprint, r.decision.decision_fingerprint)
"""
    outputs = []
    for seed in range(4):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed)
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, ("tests", environment.get("PYTHONPATH")))
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=os.getcwd(),
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        outputs.append(completed.stdout.strip())
    assert len(set(outputs)) == 1
