import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_validator_is_preingestion_only_and_source_hashes_still_match():
    script = ROOT / "scripts" / "validate_humor_batch2_development_pilot14_preingestion_v1.py"
    source = script.read_text(encoding="utf-8")
    ast.parse(source)
    assert "constructor_v5_4" not in source and "semantic_rule_identity" not in source
    assert "proposition_selected\":False" in source
    assert hashlib.sha256((ROOT / "owner-source-pilot14-v1.txt").read_bytes()).hexdigest() == "aec2bccf7ec0cc9f059785d00be1fe891a5b4c64b834da0cb9743518ff9e512d"
    assert hashlib.sha256((ROOT / "owner-declaration-pilot14-v1.json").read_bytes()).hexdigest() == "6f00f326d4f40d82bb856bb1d737f4b859af8f9b0285168d36b91913f01b5580"


def test_frozen_receipt_is_pass_without_selection_or_downstream_authority():
    path = ROOT / "docs" / "artifacts" / "humor-mechanics-batch2-development-pilot14-strict-preingestion-validation-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert receipt["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert receipt["bindable_factual_statement_candidates"] == 8
    assert receipt["candidate_status"] == "PASS_NOT_YET_BOUND_OR_SELECTED"
    assert receipt["checks"]["v5_4_ontology_rule_inventory_independence"] == "PASS"
    assert receipt["deterministic_blockers"] == []
    assert receipt["proposition_selected"] is False and receipt["downstream_authority_exercised"] is False
