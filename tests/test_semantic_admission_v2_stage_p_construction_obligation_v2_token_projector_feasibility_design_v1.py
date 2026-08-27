from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "docs" / "artifacts" / (
    "semantic-admission-v2-stage-p-construction-obligation-v2-"
    "token-projector-feasibility-design-v1.json"
)
PLAN_PATH = ROOT / "docs" / "artifacts" / (
    "semantic-admission-v2-stage-p-construction-obligation-v2-"
    "zero-inference-tokenizer-compatibility-plan-v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _identity(artifact: dict) -> str:
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def test_canonical_identities_are_reproducible() -> None:
    design = _load(DESIGN_PATH)
    plan = _load(PLAN_PATH)
    assert _identity(design) == design["canonical_identity"]
    assert _identity(plan) == plan["canonical_identity"]
    assert plan["feasibility_design_identity"] == design["canonical_identity"]


def test_reviewed_projector_and_controller_sources_are_byte_bound() -> None:
    design = _load(DESIGN_PATH)
    for relative_path, expected in design["reviewed_source_evidence"].items():
        actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual == expected


def test_design_does_not_assume_context_free_token_decoding() -> None:
    design = _load(DESIGN_PATH)
    strategies = design["projection_strategies"]
    assert strategies["strategy_a_context_free_trie"]["status"] == "CONDITIONALLY_FEASIBLE"
    assert "proves" in strategies["strategy_a_context_free_trie"]["permission_condition"]
    assert strategies["strategy_b_prefix_sensitive_full_decode"]["status"] == "SAFE_FALLBACK_DESIGN"
    assert design["token_admission_contract"]["complete_piece_simulation"] is True
    assert "only when" in design["token_admission_contract"]["eos"]


def test_design_preserves_receipts_cache_isolation_and_fail_closed_layers() -> None:
    design = _load(DESIGN_PATH)
    requirements = design["cache_identity_requirements"]
    assert "tokenizer canonical identity" in requirements
    assert any("decoded-prefix" in item for item in requirements)
    assert design["liveness_receipts"]["preserve_character_receipt"] is True
    assert "TOKENIZATION_DEAD_NO_VALID_TOKEN" in design["liveness_receipts"]["required_token_receipts"]
    assert "Schema and semantic validation" in design["token_admission_contract"]["semantic_boundary"]


def test_plan_is_exhaustive_zero_inference_and_separately_gated() -> None:
    plan = _load(PLAN_PATH)
    assert [phase["phase"] for phase in plan["separately_gated_future_phases"]] == list(range(8))
    criteria = plan["acceptance_criteria"]
    assert all(value == 0 for value in criteria.values())
    receipt = plan["current_step_receipt"]
    assert all(value == 0 for value in receipt.values())
    assert "TOKENIZER_NOT_LOADED" in plan["declared_not_reverified_tokenizer"]["status"]
    assert all(value is False for value in plan["authority"].values())


def test_design_grants_no_implementation_or_runtime_authority() -> None:
    design = _load(DESIGN_PATH)
    assert all(value is False for value in design["authority"].values())
