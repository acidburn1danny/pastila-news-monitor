import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"
DESIGN = ARTIFACTS / "semantic-admission-v2-stage-p-phase2-token-projector-feasibility-design-v1.json"
PLAN = ARTIFACTS / "semantic-admission-v2-stage-p-phase2-zero-inference-tokenizer-compatibility-plan-v1.json"
FREEZE = ARTIFACTS / "semantic-admission-v2-stage-p-phase2-character-controller-liveness-v1-freeze.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _identity(value):
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    return hashlib.sha256("\n".join(fields).encode()).hexdigest()


def test_controller_freeze_and_both_design_identities_rederive():
    freeze, design, plan = _load(FREEZE), _load(DESIGN), _load(PLAN)
    assert _identity(freeze) == freeze["canonical_identity"]
    assert _identity(design) == design["canonical_identity"]
    assert _identity(plan) == plan["canonical_identity"]
    assert design["frozen_character_controller_receipt"] == freeze["canonical_identity"]
    assert plan["feasibility_design_identity"] == design["canonical_identity"]
    assert freeze["status"] == "FROZEN"


def test_reviewed_sources_are_byte_bound():
    design = _load(DESIGN)
    for relative, expected in design["reviewed_source_evidence"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_full_decode_is_oracle_and_optimizations_require_exact_equivalence():
    design = _load(DESIGN)
    strategies = design["projection_strategies"]
    assert strategies["prefix_sensitive_full_decode"]["status"] == "REQUIRED_REFERENCE_ORACLE"
    assert strategies["context_free_piece_trie"]["status"] == "CONDITIONALLY_FEASIBLE"
    assert "exact allowed-token-set equality" in strategies["context_free_piece_trie"]["permission_condition"]
    assert design["token_admission_contract"]["complete_decoded_effect"] is True
    assert "terminal" in design["token_admission_contract"]["eos"]


def test_plan_covers_both_phase2_specific_languages_and_has_zero_tolerance():
    design, plan = _load(DESIGN), _load(PLAN)
    coverage = design["phase2_language_coverage"]
    assert "UTF-8-boundary-constrained decimal reference coordinates" in coverage["authority_reconciliation"]
    assert "five decision/reason tuples" in coverage["commitment_span"]
    assert [item["phase"] for item in plan["separately_gated_future_phases"]] == list(range(8))
    assert all(value == 0 for value in plan["acceptance_criteria"].values())


def test_no_tokenizer_or_implementation_authority_was_granted_or_used():
    freeze, design, plan = _load(FREEZE), _load(DESIGN), _load(PLAN)
    assert not any(freeze["authority"].values())
    assert not any(design["authority"].values())
    assert not any(plan["authority"].values())
    assert all(value == 0 for value in plan["current_step_receipt"].values())
    assert "NOT_LOADED" in plan["declared_not_reverified_tokenizer"]["status"]
