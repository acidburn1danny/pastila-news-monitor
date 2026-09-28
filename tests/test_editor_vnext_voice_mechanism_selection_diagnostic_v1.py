import json
from pathlib import Path

from scripts.audit_editor_vnext_voice_mechanism_selection_diagnostic_v1 import audit
from scripts.build_editor_vnext_voice_mechanism_selection_diagnostic_v1 import build


def test_result_is_reproducible_and_inventory_is_grounded():
    assert audit()["status"] == "PASS"
    assert json.loads(Path("docs/artifacts/editor-vnext-voice-mechanism-selection-diagnostic-v1.json").read_text(encoding="utf-8")) == build()


def test_deterministic_subset_is_not_overclaimed():
    result = build(); option = result["options"]["A_CLEAN_DETERMINISTIC_SUBSET"]
    assert option["commentary_generalization_demonstrated"] is False
    assert option["reusable_implementation_without_legacy_state"] == []
    assert option["verdict"].startswith("STOP")


def test_model_target_preserves_factual_contract_and_requires_new_gate():
    result = build(); option = result["options"]["B_MODEL_BASED_CREATIVE_REALIZER"]
    assert option["factual_setup_mutation_allowed"] is False
    assert option["new_factual_claims_allowed"] is False
    assert option["commentary_generalization_expected"] == "PLAUSIBLE_NOT_YET_DEMONSTRATED"
    assert result["decision"]["voice_runtime_materialization_authorized"] is False


def test_interim_state_cannot_complete_global_migration():
    result = build(); option = result["options"]["C_VOICE_OUTSIDE_VNEXT_TEMPORARILY"]
    assert "global migration cannot pass" in option["implication"]
    assert result["legacy_dependency_count"] == 0
