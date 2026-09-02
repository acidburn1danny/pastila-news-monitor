import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_design_is_complete_source_blind_and_zero_rule():
    ontology = load("humor-mechanics-batch2-v5-4-general-semantic-ontology-design-v1.json")
    taxonomy = load("humor-mechanics-batch2-v5-4-general-predicate-taxonomy-v1.json")
    governance = load("humor-mechanics-batch2-v5-4-rule-admission-governance-v1.json")
    audit = load("humor-mechanics-batch2-v5-4-ontology-admission-anti-overfitting-audit-v1.json")
    assert len(ontology["entity_classes"]) == 18
    assert len(taxonomy["families"]) == 21
    assert governance["mandatory_separation"]["rule_author_may_admit"] is False
    assert governance["operational_rules_admitted"] == audit["operational_family_usable_rule_count"] == 0
    assert audit["pilot15_prepared"] is audit["blind_material_accessed"] is False


def test_coverage_targets_and_curriculum_are_precommitted_and_bounded():
    coverage = load("humor-mechanics-batch2-v5-4-semantic-coverage-methodology-v1.json")
    curriculum = load("humor-mechanics-batch2-v5-4-predetermined-rule-population-curriculum-v1.json")
    composition = load("humor-mechanics-batch2-v5-4-rule-composition-model-v1.json")
    assert coverage["status"] == "TARGETS_FROZEN_BEFORE_RULE_POPULATION"
    assert "PERCENT_OF_PILOTS_PASSING" in coverage["not_a_metric"]
    assert curriculum["status"] == "DESIGNED_NOT_EXECUTED"
    assert sum(batch["maximum_rules"] for batch in curriculum["ordering"]) == curriculum["global_rule_budget"] == 88
    assert composition["chain_budget"]["default_max_edges"] == 3


def test_rule_schema_requires_independent_review_and_complete_semantics():
    schema = load("humor-mechanics-batch2-v5-4-semantic-rule-admission-schema-v1.json")
    contract = load("humor-mechanics-batch2-v5-4-trusted-semantic-rule-contract-v1.json")
    required = set(schema["required"])
    assert {"preconditions", "transition", "result", "counterfactual", "non_substitutability", "composition", "adjudication_receipt", "rule_identity"} <= required
    assert schema["additionalProperties"] is False
    assert schema["label_has_no_authority"] is True
    assert contract["operational_rule_count"] == 0
    assert contract["rule_may_restate_causation_without_evidence"] is False


def test_design_artifacts_have_stable_content_hashes():
    names = [
        "humor-mechanics-batch2-v5-4-general-semantic-ontology-design-v1.json",
        "humor-mechanics-batch2-v5-4-general-predicate-taxonomy-v1.json",
        "humor-mechanics-batch2-v5-4-semantic-rule-admission-schema-v1.json",
        "humor-mechanics-batch2-v5-4-rule-admission-governance-v1.json",
        "humor-mechanics-batch2-v5-4-rule-composition-model-v1.json",
        "humor-mechanics-batch2-v5-4-semantic-coverage-methodology-v1.json",
        "humor-mechanics-batch2-v5-4-predetermined-rule-population-curriculum-v1.json",
        "humor-mechanics-batch2-v5-4-ontology-admission-anti-overfitting-audit-v1.json",
    ]
    assert all(len(hashlib.sha256((ART / name).read_bytes()).hexdigest()) == 64 for name in names)


def test_design_freeze_binds_exact_artifact_hashes_and_zero_authority():
    freeze = load("humor-mechanics-batch2-v5-4-general-semantic-authority-design-freeze-v1.json")
    expected = {
        "ontology_schema_identity": "humor-mechanics-batch2-v5-4-general-semantic-ontology-design-v1.json",
        "predicate_taxonomy_identity": "humor-mechanics-batch2-v5-4-general-predicate-taxonomy-v1.json",
        "trusted_semantic_rule_contract_identity": "humor-mechanics-batch2-v5-4-trusted-semantic-rule-contract-v1.json",
        "semantic_rule_schema_identity": "humor-mechanics-batch2-v5-4-semantic-rule-admission-schema-v1.json",
        "rule_admission_governance_identity": "humor-mechanics-batch2-v5-4-rule-admission-governance-v1.json",
        "composition_model_identity": "humor-mechanics-batch2-v5-4-rule-composition-model-v1.json",
        "coverage_methodology_identity": "humor-mechanics-batch2-v5-4-semantic-coverage-methodology-v1.json",
        "population_curriculum_identity": "humor-mechanics-batch2-v5-4-predetermined-rule-population-curriculum-v1.json",
        "independent_audit_identity": "humor-mechanics-batch2-v5-4-ontology-admission-anti-overfitting-audit-v1.json",
    }
    for key, name in expected.items():
        assert freeze["design_artifacts"][key] == hashlib.sha256((ART / name).read_bytes()).hexdigest()
    assert freeze["operational_rules_admitted"] == 0
    assert freeze["rule_population_executed"] is freeze["pilot15_prepared"] is False
    assert freeze["future_family_source_accessed"] is freeze["blind_material_accessed"] is False
