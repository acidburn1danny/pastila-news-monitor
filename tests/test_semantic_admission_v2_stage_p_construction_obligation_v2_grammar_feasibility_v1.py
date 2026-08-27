from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import SourceSpanReferenceV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2,
)


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-constrained-grammar-feasibility-design-v1.json"
ANALYSIS = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-zero-inference-compatibility-analysis-v1.json"
PACK = ROOT / "docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json"


def _load(path):
    return json.loads(path.read_bytes())


def _boundaries(text):
    result = [0]; total = 0
    for character in text:
        total += len(character.encode("utf-8")); result.append(total)
    return result


def test_design_identity_and_conditional_blocker():
    value = _load(DESIGN)
    parts = [value["artifact_id"], value["source_v2_candidate_identity"],
             "REQUEST_BOUND_UTF8_BOUNDARY_CHOICES", "EXPLICIT_RAW_SCHEMA_IDENTITY_REMEDIATED",
             "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["design_identity"]
    assert value["feasibility_conclusion"] == "FEASIBLE_FOR_A_SEPARATELY_AUTHORIZED_ZERO_INFERENCE_GRAMMAR_CANDIDATE"
    assert value["raw_identity_hardening"]["remediated"] is True


def test_analysis_identity_and_exact_component_hashes():
    value = _load(ANALYSIS)
    parts = [value["artifact_id"], value["source_v2_candidate_identity"],
             "FEASIBLE_FOR_SEPARATE_ZERO_INFERENCE_CANDIDATE", "CASE01_5_REFERENCES_135_123_BOUNDARIES",
             "ZERO_INFERENCE"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["analysis_identity"]
    for name, expected in value["inspected_existing_components"].items():
        filename = {
            "constraint_sha256": "stage_p_construction_obligation_constraint_v1.py",
            "incremental_tracker_sha256": "stage_p_construction_obligation_incremental_tracker_v1.py",
            "callback_controller_sha256": "stage_p_construction_obligation_callback_controller_v1.py",
            "trie_projector_sha256": "stage_p_trie_projector_v1.py",
        }[name]
        path = ROOT / "src/pastila_scout/semantic_admission_v2" / filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_schema_presence_gap_is_observed_not_assumed():
    analysis = _load(ANALYSIS)
    ledger_required = ConstructionObligationLedgerV2.model_json_schema()["required"]
    reference_required = SourceSpanReferenceV1.model_json_schema()["required"]
    assert ledger_required == analysis["schema_presence_findings"]["ledger_required_fields"]
    assert all(item in ledger_required for item in ("schema_name", "schema_version"))
    assert analysis["schema_presence_findings"]["ledger_identity_fields_missing_from_required"] == []
    assert reference_required == analysis["schema_presence_findings"]["reference_required_fields"]


def test_case01_boundary_measurements_reproduce_from_captured_bytes():
    pack = _load(PACK); case = next(x for x in pack["cases"] if x["case_id"] == "HMCV1-SASC-01")
    observed = _load(ANALYSIS)["case01_static_measurements"]
    candidate = _boundaries(case["candidate"]); authority = _boundaries(case["factual_summary"])
    assert (len(case["candidate"].encode()), len(candidate), len(candidate) - 1,
            (len(candidate) - 1) * len(candidate) // 2) == (
                observed["candidate_utf8_bytes"], observed["candidate_utf8_boundaries"],
                observed["candidate_start_choices"], observed["candidate_nonempty_boundary_pairs"])
    assert (len(case["factual_summary"].encode()), len(authority), len(authority) - 1,
            (len(authority) - 1) * len(authority) // 2) == (
                observed["factual_authority_utf8_bytes"],
                observed["factual_authority_utf8_boundaries"],
                observed["factual_authority_start_choices"],
                observed["factual_authority_nonempty_boundary_pairs"])


def test_no_implementation_or_execution_authority_and_zero_objects():
    design = _load(DESIGN); analysis = _load(ANALYSIS)
    assert all(value is False for value in design["authority"].values())
    assert all(value is False for value in analysis["authority"].values())
    operations = analysis["tests_and_operations_performed"]
    for key in ("grammar_objects_constructed", "tracker_objects_constructed",
                "controller_objects_constructed", "projector_objects_constructed",
                "evaluator_objects_constructed", "runner_objects_constructed",
                "tokenizer_loads", "model_loads", "provider_calls", "inference_calls"):
        assert operations[key] == 0
    assert operations["probe_constructed"] is False
