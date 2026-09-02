from copy import deepcopy
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_authority_selection_governance_v2 import (
    canonical_identity,
    validate_selection_precommitment,
    validate_selection_record,
)


def precommitment():
    value = {
        "source_population_frame_policy": {
            "enumeration_frozen_before_entropy": True,
            "inclusion_exclusion_rules_precommitted": True,
            "negative_space_inventory_required": True,
            "post_freeze_edits": "NEW_VERSION_NEW_SELECTION_EVENT",
        },
        "selection_precommitment_model": {
            "algorithm": "CANONICAL_ORDER_PLUS_PUBLIC_ENTROPY_REJECTION_SAMPLING",
            "entropy_source_controlled_by_project": False,
            "single_draw_no_resampling": True,
            "selection_before_semantic_inspection": True,
            "empty_or_invalid_draw": "FAIL_CLOSED_NO_REDRAW",
        },
        "scope_policy": {
            "frozen_before_source_selection": True,
            "semantic_coverage_dependent": False,
            "default": "ENTIRE_SELECTED_SOURCE",
            "exceptions": "PRECOMMITTED_NONSEMANTIC_RULES_ONLY",
        },
        "basis_extraction_policy": {
            "frozen_before_frame_semantic_observation": True,
            "mode": "EXHAUSTIVE_ALL_ELIGIBLE_ASSERTIONS",
            "ordering": "SOURCE_BYTE_ORDER",
            "stopping_rule": "END_OF_FROZEN_SCOPE",
            "deduplication": "RETAIN_FIRST_AND_LOG_EVERY_DUPLICATE",
            "coverage_or_relation_class_filter": False,
        },
        "trust_domain_isolation": {
            "project_owner": "V2_INFORMED_PROJECT_OWNER",
            "frame_registrar": "FRAME_REGISTRAR",
            "entropy_authority": "PUBLIC_ENTROPY_AUTHORITY",
            "selection_executor": "DETERMINISTIC_SELECTION_EXECUTOR",
            "scope_policy_owner": "SCOPE_POLICY_OWNER",
            "basis_extractor": "BASIS_EXTRACTOR",
            "admission_verifier": "ADMISSION_VERIFIER",
            "candidate_author": "CANDIDATE_AUTHOR",
            "rule_adjudicator": "RULE_ADJUDICATOR",
            "credential_evidence_required": True,
        },
        "forbidden_information": [
            "ONTOLOGY_V2",
            "CONTRACT_OR_SCHEMA_V2",
            "CURRICULUM_V2_BATCHES_OR_COVERAGE",
            "HISTORICAL_FAILURES_OR_CANDIDATES",
            "FUTURE_FAMILY_OR_MECHANISM_INFORMATION",
        ],
        "governance_identity": "",
    }
    value["governance_identity"] = canonical_identity(
        value, "governance_identity"
    )
    return value


def reseal(value):
    value["governance_identity"] = canonical_identity(
        value, "governance_identity"
    )


def test_complete_source_blind_precommitment_passes():
    validate_selection_precommitment(precommitment())


def test_frozen_governance_record_matches_executable_validator():
    path = Path(__file__).resolve().parents[1] / "docs/artifacts/semantic-contract-v2-precommitted-authority-selection-governance-v1.json"
    validate_selection_precommitment(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v["source_population_frame_policy"].update(enumeration_frozen_before_entropy=False),
        lambda v: v["source_population_frame_policy"].update(negative_space_inventory_required=False),
        lambda v: v["selection_precommitment_model"].update(entropy_source_controlled_by_project=True),
        lambda v: v["selection_precommitment_model"].update(single_draw_no_resampling=False),
        lambda v: v["selection_precommitment_model"].update(empty_or_invalid_draw="REDRAW"),
        lambda v: v["scope_policy"].update(frozen_before_source_selection=False),
        lambda v: v["scope_policy"].update(default="SELECTED_CHAPTERS"),
        lambda v: v["basis_extraction_policy"].update(mode="SELECT_USEFUL_ASSERTIONS"),
        lambda v: v["basis_extraction_policy"].update(stopping_rule="COVERAGE_REACHED"),
        lambda v: v["basis_extraction_policy"].update(deduplication="DROP_WITHOUT_LOG"),
        lambda v: v["basis_extraction_policy"].update(coverage_or_relation_class_filter=True),
        lambda v: v["trust_domain_isolation"].update(basis_extractor="CANDIDATE_AUTHOR"),
        lambda v: v["trust_domain_isolation"].update(frame_registrar="V2_INFORMED_PROJECT_OWNER"),
        lambda v: v["trust_domain_isolation"].update(credential_evidence_required=False),
        lambda v: v["forbidden_information"].remove("HISTORICAL_FAILURES_OR_CANDIDATES"),
    ],
)
def test_resealed_gaming_paths_fail_closed(mutation):
    value = precommitment()
    mutation(value)
    reseal(value)
    with pytest.raises(ValueError):
        validate_selection_precommitment(value)


def test_future_selection_record_requires_one_draw_and_negative_space():
    policy = precommitment()
    record = {
        "precommitment_identity": policy["governance_identity"],
        "frame_frozen_before_entropy": True,
        "draw_count": 1,
        "resampling": False,
        "complete_negative_space_evidence": True,
        "semantic_content_observed_before_selection": False,
        "source_acquired": False,
        "record_identity": "",
    }
    record["record_identity"] = canonical_identity(record, "record_identity")
    validate_selection_record(
        record, precommitment_identity=policy["governance_identity"]
    )
    for field, bad in (
        ("draw_count", 2),
        ("resampling", True),
        ("complete_negative_space_evidence", False),
        ("semantic_content_observed_before_selection", True),
        ("source_acquired", True),
    ):
        changed = deepcopy(record)
        changed[field] = bad
        changed["record_identity"] = canonical_identity(changed, "record_identity")
        with pytest.raises(ValueError):
            validate_selection_record(
                changed, precommitment_identity=policy["governance_identity"]
            )
