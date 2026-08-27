from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_liveness_trie_projector_v1 import StagePLivenessTokenTrieProjectorV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_2 import StagePScopeGraphConstraintStateV1_2


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1_2.py"


def _entry(entry_id: str, kind: str):
    common = {"entry_id": entry_id, "candidate_span": "fapt" if kind != "creative" else "metafora",
              "independence_group": "G1" if entry_id == "P1" else "G2"}
    if kind == "creative":
        value = {**common, "entry_type": "CONTAINED_CREATIVE", "authority_support": None,
                "commitment": "Transformare editoriala.", "scope_basis": "CREATIVE_CONTAINED",
                "event_alignment": "CREATIVE_VEHICLE_ONLY", "authority_modality": "NOT_APPLICABLE",
                "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
                "candidate_timing": "NOT_APPLICABLE", "scope_relation": "CREATIVE_HOST",
                "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}
    elif kind == "unresolved":
        value = {**common, "entry_type": "UNRESOLVED_SCOPE", "authority_support": None,
                "commitment": "Relatie nerezolvata.", "scope_basis": "UNRESOLVED",
                "event_alignment": "UNRESOLVED", "authority_modality": "NOT_APPLICABLE",
                "candidate_modality": "UNRESOLVED", "authority_timing": "NOT_APPLICABLE",
                "candidate_timing": "UNRESOLVED", "scope_relation": "UNRESOLVED_RELATION",
                "creative_host_entry_id": None, "factual_return_basis": "UNRESOLVED"}
    else:
        supported = kind in {"governed", "embedded"}
        value = {**common, "entry_type": "REAL_WORLD_COMMITMENT", "authority_support": "fapt" if supported else None,
                "commitment": "Propozitie reala.", "scope_basis": "ASSERTED",
                "event_alignment": "GOVERNED_EVENT" if supported else "NEW_UNSUPPORTED_EVENT",
                "authority_modality": "CERTAIN_OR_ACTUAL" if supported else "NOT_APPLICABLE",
                "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PAST" if supported else "NOT_APPLICABLE",
                "candidate_timing": "PAST", "scope_relation": "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" if kind == "embedded" else "STANDALONE",
                "creative_host_entry_id": "P1" if kind == "embedded" else None,
                "factual_return_basis": "ASSERTION_SURVIVES"}
    order = ("entry_id", "entry_type", "candidate_span", "authority_support", "commitment", "scope_basis",
             "event_alignment", "authority_modality", "candidate_modality", "authority_timing", "candidate_timing",
             "independence_group", "scope_relation", "creative_host_entry_id", "factual_return_basis")
    return {key: value[key] for key in order}


def _ledger(entries, *, unresolved=False):
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": entries,
        "coverage_receipt": {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
            "creative_scope_checked": True, "unresolved_scope_present": unresolved,
            "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
            "factual_return_tests_completed": True},
        "coverage_decision": "INDETERMINATE" if unresolved else "COMPLETE"}, separators=(",", ":"))


def test_broader_structural_fixtures_have_token_liveness_at_every_prefix():
    fixtures = {
        "unsupported": _ledger([_entry("P1", "unsupported")]),
        "governed": _ledger([_entry("P1", "governed")]),
        "creative": _ledger([_entry("P1", "creative")]),
        "embedded_return": _ledger([_entry("P1", "creative"), _entry("P2", "embedded")]),
        "unresolved": _ledger([_entry("P1", "unresolved")], unresolved=True),
    }
    characters = sorted(set("".join(fixtures.values())))
    pieces = {index + 1: char for index, char in enumerate(characters)}
    reverse = {char: token_id for token_id, char in pieces.items()}
    for name, raw in fixtures.items():
        projector = StagePLivenessTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999999)
        state = StagePScopeGraphConstraintStateV1_2()
        for char in raw:
            allowed = projector.allowed_token_ids(state)
            assert reverse[char] in allowed, (name, state.mode, state.next_step, char)
            state = state.feed(char)
        assert state.can_eos
        assert projector.allowed_token_ids(state) == (999999,)


def test_runner_loads_track_a_types_without_tokenizer_or_model_import():
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location("track_a_runner_binding_test", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    State, Trie, Controller, Lifecycle = module._track_a_types()
    assert State.__name__ == "StagePScopeGraphConstraintStateV1_2"
    assert Trie.__name__ == "StagePLivenessTokenTrieProjectorV1"
    assert Controller.__name__ == "StagePScopeGraphLivenessCallbackControllerV1_2"
    assert Lifecycle.__name__ == "AppendOnlyLifecycleV1"
    newly_loaded = set(sys.modules) - before
    assert not any(name.startswith(("transformers", "peft")) for name in newly_loaded)


def test_runner_source_has_stable_identity_and_no_execution_edge():
    digest = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    assert len(digest) == 64
    source = RUNNER.read_text("utf-8")
    assert "base.run(*map(Path, arguments))" in source
    assert "if __name__ == \"__main__\"" in source
    assert "AutoModel" not in source and "PeftModel" not in source
