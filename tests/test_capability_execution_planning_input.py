"""M6C.6A.1 versioned capability planning-input compatibility tests."""

import json

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_dispatch_contracts import _planning_result

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanPolicy,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanRequestV2,
    CorrectiveActionExecutionPlanResultV2,
    CorrectiveActionExecutionPlanV2,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_revision import (
    DraftRevisionInstructions,
    DraftRevisionPlanningInput,
    DraftRevisionScope,
    DraftRevisionTarget,
    build_draft_revision_planning_input_report,
    build_standard_draft_revision_policy,
    serialize_draft_revision_planning_input_report,
)


def _lineage():
    legacy_result = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    legacy_plan = legacy_result.plan
    planning_policy = CorrectiveActionExecutionPlanPolicy.build(
        revision_requires_human_authorization=False
    )
    legacy_request = CorrectiveActionExecutionPlanRequest.build(
        legacy_plan.decision_result, planning_policy
    )
    assert legacy_request.request_fingerprint == legacy_plan.request_fingerprint
    source = legacy_plan.decision_result.integration_result.generation_result.draft
    revision_policy = build_standard_draft_revision_policy()
    scope = DraftRevisionScope.build(
        targets=(DraftRevisionTarget.build(target_type="opening"),),
        maximum_targets=revision_policy.maximum_revision_targets,
    )
    instructions = DraftRevisionInstructions.build(
        scope_fingerprint=scope.scope_fingerprint,
        editorial_instruction="Clarifică numai introducerea autorizată.",
    )
    planning_input = DraftRevisionPlanningInput.build(
        source_lineage_fingerprint=legacy_plan.decision_result.result_fingerprint,
        authorization_policy_fingerprint=planning_policy.policy_fingerprint,
        source_draft=source,
        revision_policy=revision_policy,
        revision_scope=scope,
        revision_instructions=instructions,
    )
    request_v2 = CorrectiveActionExecutionPlanRequestV2.build(
        legacy_request=legacy_request, planning_input=planning_input
    )
    plan_v2 = CorrectiveActionExecutionPlanV2.build(
        request=request_v2,
        legacy_plan=legacy_plan,
        planning_input=planning_input,
    )
    result_v2 = CorrectiveActionExecutionPlanResultV2.build(
        legacy_result=legacy_result, plan=plan_v2
    )
    return (
        legacy_request,
        legacy_plan,
        legacy_result,
        planning_input,
        request_v2,
        plan_v2,
        result_v2,
    )


def test_v1_contracts_and_serialization_remain_bit_identical():
    legacy_request, legacy_plan, legacy_result, *_ = _lineage()
    request_before = json.dumps(legacy_request.model_dump(mode="json"), sort_keys=True)
    plan_before = json.dumps(legacy_plan.model_dump(mode="json"), sort_keys=True)
    result_before = json.dumps(legacy_result.model_dump(mode="json"), sort_keys=True)

    rebuilt_request = CorrectiveActionExecutionPlanRequest.build(
        legacy_request.decision_result, legacy_request.planning_policy
    )
    assert rebuilt_request.request_fingerprint == legacy_request.request_fingerprint
    assert (
        json.dumps(rebuilt_request.model_dump(mode="json"), sort_keys=True)
        == request_before
    )
    assert "planning_input" not in request_before
    assert "planning_input" not in plan_before
    assert "planning_input" not in result_before


def test_v2_preserves_exact_input_and_nested_domain_identities():
    _, _, _, planning_input, request, plan, result = _lineage()

    assert request.planning_input is planning_input
    assert plan.planning_input is request.planning_input
    assert result.planning_input is planning_input
    assert result.plan is plan
    assert plan.planning_input.revision_policy is planning_input.revision_policy
    assert plan.planning_input.revision_scope is planning_input.revision_scope
    assert (
        plan.planning_input.revision_instructions
        is planning_input.revision_instructions
    )
    authoritative = request.decision_result.integration_result.generation_result.draft
    assert planning_input.source_draft is authoritative


def test_v2_fingerprints_are_deterministic_and_commit_to_input():
    first = _lineage()
    second = _lineage()
    assert first[3].input_fingerprint == second[3].input_fingerprint
    assert first[4].request_fingerprint == second[4].request_fingerprint
    assert first[5].plan_fingerprint == second[5].plan_fingerprint
    assert first[6].result_fingerprint == second[6].result_fingerprint


def test_action_and_authorization_policy_mismatches_fail_closed():
    legacy_request, _, _, planning_input, *_ = _lineage()
    bad = planning_input.model_copy(
        update={"source_lineage_fingerprint": "sha256:" + "0" * 64}
    )
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlanRequestV2.build(
            legacy_request=legacy_request, planning_input=bad
        )

    wrong_policy = planning_input.model_copy(
        update={"authorization_policy_fingerprint": "sha256:" + "1" * 64}
    )
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlanRequestV2.build(
            legacy_request=legacy_request, planning_input=wrong_policy
        )


def test_unknown_versions_and_tampered_input_fail_closed():
    _, _, _, planning_input, request, *_ = _lineage()
    payload = planning_input.model_dump(mode="python")
    payload["contract_version"] = "999"
    with pytest.raises(ValidationError, match="unsupported"):
        DraftRevisionPlanningInput.model_validate(payload)
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlanRequestV2.model_validate(
            {
                **request.model_dump(mode="python"),
                "request_fingerprint": "sha256:" + "0" * 64,
            }
        )


def test_implicit_regeneration_is_rejected_at_capability_ingress():
    legacy_request, legacy_plan, _, _, *_ = _lineage()
    source = legacy_plan.decision_result.integration_result.generation_result.draft
    policy = build_standard_draft_revision_policy()
    targets = (
        DraftRevisionTarget.build(target_type="opening"),
        DraftRevisionTarget.build(target_type="closing"),
    )
    scope = DraftRevisionScope.build(
        targets=targets, maximum_targets=policy.maximum_revision_targets
    )
    instructions = DraftRevisionInstructions.build(
        scope_fingerprint=scope.scope_fingerprint,
        editorial_instruction="Rescrie tot materialul.",
    )
    with pytest.raises(ValidationError, match="regeneration"):
        DraftRevisionPlanningInput.build(
            source_lineage_fingerprint=legacy_plan.decision_result.result_fingerprint,
            authorization_policy_fingerprint=legacy_request.planning_policy.policy_fingerprint,
            source_draft=source,
            revision_policy=policy,
            revision_scope=scope,
            revision_instructions=instructions,
        )


def test_safe_report_is_deterministic_and_excludes_content():
    *_, planning_input, _request_v2, _plan_v2, _result_v2 = _lineage()
    report = build_draft_revision_planning_input_report(planning_input)
    serialized = serialize_draft_revision_planning_input_report(report)

    assert serialized == serialize_draft_revision_planning_input_report(report)
    assert planning_input.revision_instructions.editorial_instruction not in serialized
    assert planning_input.source_draft.assembled_text not in serialized
    assert report["target_count"] == 1
