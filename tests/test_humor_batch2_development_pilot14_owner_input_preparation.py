import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_pilot14_preparation_is_content_free_and_bound_to_qualified_v54():
    request = load("humor-mechanics-batch2-development-pilot14-owner-input-request-v1.json")
    audit = load("humor-mechanics-batch2-development-pilot14-owner-input-preparation-audit-v1.json")
    assert request["pilot_role"] == "GENUINE_END_TO_END_MECHANISM_TRIAL"
    assert request["v5_4_bindings"]["qualification_identity"] == "7fa2ccf198de2feafe89974a85d56c9c246a6402e2a5d57417d48f33a1bae124"
    assert all(value is False for value in request["authority_matrix"].values())
    assert request["acquisition_boundaries"]["source_acquisition_independent_of_v5_4_ontology_and_rule_inventory"] is True
    assert audit["source_content_access_count"] == 0
    assert audit["constructor_provider_observer_emitter_invocations"] == "0/0/0/0"
    assert audit["candidate_surfaces"] == 0 and audit["blind_material_accessed"] is False


def test_declaration_template_is_uncompleted_and_contains_no_owner_source_content():
    template = load("humor-mechanics-batch2-development-pilot14-owner-declaration-template-v1.json")
    assert template["pilot_id"] == "BATCH2-DEVELOPMENT-PILOT-14"
    assert template["source"]["filename"] == "owner-source-pilot14-v1.txt"
    assert "OWNER_MUST" in json.dumps(template)
    assert "30 august 2026" not in json.dumps(template, ensure_ascii=False)
    assert set(template) == {"schema_name", "schema_version", "pilot_id", "trial_role", "source",
                             "contributor", "ownership_declarations", "independent_grants",
                             "source_status_declarations", "owner_instruction", "owner_confirmation"}


def test_phase_order_keeps_release_after_semantic_licensing_and_gates_after_construction():
    phases = load("humor-mechanics-batch2-development-pilot14-owner-input-request-v1.json")["mandatory_phase_order"]
    assert phases.index("V5_4_SOURCE_COMPATIBILITY_AND_INDEPENDENT_SEMANTIC_LICENSING") < phases.index("G02B_RELEASE_DECISION")
    assert phases.index("EXACTLY_ONE_CONSTRUCTION_ATTEMPT") < phases.index("FRAGMENT_COLLISION_BEFORE_G02") < phases.index("G02")
