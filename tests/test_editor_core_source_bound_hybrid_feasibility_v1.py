import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BOUNDARY = load_module("hybrid_fixture", "scripts/fixture_editor_core_source_bound_hybrid_feasibility_v1.py")


def test_byte_exact_rebuild_and_fixture_boundary():
    before = Path("docs/artifacts/editor-core-source-bound-hybrid-feasibility-v1-manifest.json").read_bytes()
    build = subprocess.run(
        [sys.executable, "-B", "scripts/build_editor_core_source_bound_hybrid_feasibility_v1.py"],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(build.stdout)["status"] == "PASS_BUILD"
    assert Path("docs/artifacts/editor-core-source-bound-hybrid-feasibility-v1-manifest.json").read_bytes() == before
    result = BOUNDARY.run()
    assert result["status"] == "PASS_FIXTURE_ONLY"
    assert result["ledgers"] == 48 and result["valid_extractive_proposals"] == 48
    assert result["model_loaded"] is False and result["inference_performed"] is False
    assert result["optimizer_created"] is False and result["training_performed"] is False


def test_all_atoms_and_obligations_are_source_bound():
    ledgers = BOUNDARY.load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    assert len(ledgers) == 48
    assert sum(len(row["atoms"]) for row in ledgers) == 144
    assert sum(len(row["obligations"]) for row in ledgers) == 192
    for ledger in ledgers:
        BOUNDARY.validate_ledger(ledger)
        required = set(ledger["realization_contract"]["required_atom_ids"])
        assert required
        assert all(set(obligation["support_atom_ids"]) <= required for obligation in ledger["obligations"])


def test_verifier_rejects_drift_and_returns_valid_fallback():
    ledger = BOUNDARY.load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")[0]
    proposal = BOUNDARY.extractive_proposal(ledger)
    proposal["sentences"][0]["text"] += " Birocrația confirmă 999999 de cazuri."
    result = BOUNDARY.execute_with_fallback(ledger, proposal)
    assert result["route"] == "EXTRACTIVE_FALLBACK"
    assert result["fallback"]["accepted"]
    assert "UNAUTHORIZED_CONTENT_TOKEN" in result["primary"]["reasons"]
    assert "UNAUTHORIZED_NUMBER" in result["primary"]["reasons"]


def test_protocol_keeps_all_execution_and_selection_authority_closed():
    protocol = json.loads(Path("docs/artifacts/editor-core-source-bound-hybrid-feasibility-v1-protocol.json").read_text(encoding="utf-8"))
    assert protocol["parent"] == "R2_STEP_9"
    assert protocol["successor_training"] == "SUSPENDED"
    assert protocol["fixture_selection_uses_oracle"] is True
    assert protocol["autonomous_ledger_construction_claimed"] is False
    assert protocol["real_route_requires_independent_selection_curation"] is True
    for key in (
        "model_load_authorized", "inference_authorized", "optimizer_creation_authorized",
        "training_authorized", "successor_candidate_authorized", "parent_selection_authority",
        "promotion_authorized", "release_authorized", "voice_or_chief_editor_objective",
    ):
        assert protocol[key] is False


def test_terminal_rules_are_fail_closed_and_precedence_is_explicit():
    rules = json.loads(Path("docs/artifacts/editor-core-source-bound-hybrid-feasibility-v1-terminal-rules.json").read_text(encoding="utf-8"))
    assert rules["precedence"] == "STOP_THEN_REVISE_THEN_CONTINUE"
    assert "ANY_ACCEPTED_NOVEL_ACTOR_OR_NUMBER" in rules["STOP"]
    assert "TRAINABLE_RESIDUAL_ISOLATED_TO_REALIZATION_NOT_FACT_SELECTION" in rules["CONTINUE"]
    assert rules["parent_selection_authority"] is False
