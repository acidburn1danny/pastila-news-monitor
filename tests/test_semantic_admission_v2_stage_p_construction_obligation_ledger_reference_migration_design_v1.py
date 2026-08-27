from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-ledger-reference-migration-design-v1.json"


def _load():
    return json.loads(DESIGN.read_bytes())


def test_design_identity_and_breaking_migration_boundary():
    value = _load()
    parts = [value["artifact_id"], value["approved_reference_candidate_identity"],
             "BREAKING_V2_REFERENCE_FIELDS_NO_V1_UNION",
             "RAW_PROJECTION_SEMANTIC_TERMINAL_RECEIPT_SEPARATION", "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["design_identity"]
    assert value["migration_strategy"]["kind"] == "BREAKING_VERSIONED_V2_CONTRACT"
    assert value["migration_strategy"]["automatic_v1_rewrite"] is False
    assert value["migration_strategy"]["backfill_frozen_raw"] is False


def test_exactly_four_provenance_fields_migrate_with_correct_roles():
    matrix = _load()["field_migration_matrix"]
    assert len(matrix) == 4
    observed = {(item["record"], item["v2_field"], item["required_source_role"])
                for item in matrix}
    assert observed == {
        ("ConstructionRecord", "candidate_span_ref", "CANDIDATE"),
        ("ScopeGraphEntry", "candidate_span_ref", "CANDIDATE"),
        ("ScopeGraphEntry", "authority_support_ref", "FACTUAL_AUTHORITY"),
        ("CreativeTargetAudit", "vehicle_span_ref", "CANDIDATE"),
    }
    authority = next(item for item in matrix if item["v2_field"] == "authority_support_ref")
    assert authority["nullable"] is True


def test_semantic_analysis_text_is_not_promoted_to_evidence():
    fields = _load()["fields_that_remain_model_authored_analysis"]
    assert {item["field"] for item in fields} == {
        "ScopeGraphEntry.commitment", "CreativeTargetAudit.semantic_target",
        "ConstructionRecord.role_basis", "ConstructionRoleAudit.literal_path_basis",
    }
    assert all("boundary" in item for item in fields)
    assert any("no provenance" in item["boundary"] for item in fields)


def test_raw_projection_semantic_receipts_are_separate_and_fail_closed():
    value = _load()
    coexistence = value["receipt_coexistence_and_precedence"]
    assert coexistence["terminal_precedence"] == [
        "TRANSPORT_OR_RAW_PERSISTENCE_FAILURE", "SCHEMA_FAILURE",
        "SOURCE_PROJECTION_FAILURE", "SEMANTIC_OR_COVERAGE_FAILURE", "PASS"]
    receipt = value["projection_receipt_v1_design"]
    assert receipt["receipt_is_not_model_output"] is True
    assert receipt["projected_text_policy"].startswith("Do not duplicate projected text")
    assert "never overwrites" in receipt["append_only_rule"]
    assert "Every required reference must resolve" in value["projection_pipeline_design"]["no_partial_admission"]


def test_case01_v1_remains_frozen_and_semantics_remain_independent():
    contract = _load()["case01_design_acceptance_contract"]
    assert any("angazații" in item and "cannot become projected evidence" in item for item in contract)
    assert any("event_alignment" in item and "independent semantic decision" in item for item in contract)
    assert any("never retroactively reclassified" in item for item in contract)


def test_design_grants_no_implementation_or_execution_authority():
    value = _load()
    assert value["scope"] == "DESIGN_ONLY_NO_LIVE_SCHEMA_GRAMMAR_PROMPT_EVALUATOR_RUNNER_OR_RUNTIME_CHANGE"
    assert all(item is False for item in value["authority"].values())
    assert any("No implementation" in item for item in value["explicit_non_goals"])
