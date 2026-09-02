from copy import deepcopy
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_authority_objective_selection_v2 import (
    canonical_identity,
    derive_entropy_round,
    validate_objective_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/artifacts/semantic-contract-v2-objective-owner-executable-authority-selection-governance-v1.json"


def policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def reseal(value):
    value["governance_identity"] = canonical_identity(value, "governance_identity")


def test_frozen_owner_executable_policy_is_canonical_and_valid():
    value = policy()
    assert value["governance_identity"] == canonical_identity(value, "governance_identity")
    validate_objective_policy(value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v["registry_union"].update(operation="OWNER_CHOOSES_ONE"),
        lambda v: v["registry_union"].update(roots=["OPENALEX_PUBLIC_SNAPSHOT"]),
        lambda v: v["registry_union"].update(snapshot_rule="OWNER_SELECTED_SNAPSHOT"),
        lambda v: v["frame_derivation"].update(semantic_query_or_keyword_filter=True),
        lambda v: v["frame_derivation"].update(v2_relation_or_coverage_filter=True),
        lambda v: v["frame_derivation"].update(complete_negative_space=False),
        lambda v: v["frame_derivation"].update(owner_discretion="ALLOW_EXCLUSIONS"),
        lambda v: v["entropy_anchor"].update(network="LOCAL_PRNG"),
        lambda v: v["entropy_anchor"].update(chain_hash="0" * 64),
        lambda v: v["entropy_anchor"].update(round_rule="OWNER_CHOOSES_ROUND"),
        lambda v: v["entropy_anchor"].update(cryptographic_verification_required=False),
        lambda v: v["selection"].update(draws=2),
        lambda v: v["selection"].update(redraw=True),
        lambda v: v["selection"].update(post_draw_eligibility_failure="DRAW_AGAIN"),
        lambda v: v["scope"].update(rule="SELECTED_CHAPTERS"),
        lambda v: v["scope"].update(semantic_exclusions=True),
        lambda v: v["extraction"].update(phase_two="VISIT_SELECTED_SEGMENTS"),
        lambda v: v["extraction"].update(coverage_visible=True),
        lambda v: v["extraction"].update(stopping_rule="COVERAGE_REACHED"),
        lambda v: v["extraction"].update(all_decisions_logged=False),
        lambda v: v["evidence"].update(replay_from_public_inputs=False),
        lambda v: v["evidence"].update(identity_labels_as_independence_proof=True),
        lambda v: v["owner_execution"].update(v2_informed=False),
        lambda v: v["owner_execution"].update(may_choose_frame_source_scope_segment_or_redraw=True),
        lambda v: v["owner_execution"].update(may_abort_after_observing_result=True),
    ],
)
def test_resealed_owner_control_and_shaping_variants_fail_closed(mutation):
    value = deepcopy(policy())
    mutation(value)
    reseal(value)
    with pytest.raises(ValueError):
        validate_objective_policy(value)


def test_future_entropy_round_is_deterministic_and_strictly_future():
    genesis = 1692803367
    period = 3
    commit_time = 1790000000
    round_number = derive_entropy_round(
        frame_commit_unix_seconds=commit_time,
        genesis_time=genesis,
        period=period,
    )
    round_time = genesis + (round_number - 1) * period
    assert round_time >= commit_time + 86400
    assert round_time - (commit_time + 86400) < period
    assert round_number == derive_entropy_round(
        frame_commit_unix_seconds=commit_time,
        genesis_time=genesis,
        period=period,
    )


def test_no_source_or_authority_action_is_encoded():
    value = policy()
    assert value["source_population_created"] is False
    assert value["source_selected_or_acquired"] is False
    assert value["semantic_content_accessed"] is False
    assert value["authority_basis_created_or_admitted"] is False
    assert value["curriculum_population_started"] is False
    assert value["pilot15_prepared"] is False
    assert value["blind_or_future_family_access"] is False
