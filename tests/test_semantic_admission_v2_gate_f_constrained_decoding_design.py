from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.models import GateResponseV2, REASON_CODES_V2

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-constrained-decoding-v1-spec.json"
EVIDENCE = ROOT / ".semantic-admission-v2-gate-f-constrained-decoding-v1-evidence/tokenizer-feasibility.json"


def test_constraint_spec_preserves_frozen_gate_f_schema_vocabulary() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    expected = {code for code in REASON_CODES_V2 if code.startswith("FSEM_")} | {"ADMISSION_INDETERMINATE"}
    assert set(spec["selected_design"]["reason_codes"]) == expected
    assert spec["selected_design"]["decision_values"] == ["PASS", "FAIL", "INDETERMINATE"]
    assert spec["selected_design"]["field_order"] == ["gate_id", "decision", "reason_records"]
    assert spec["run3_authorized"] is spec["runtime_authority"] is spec["training_authority"] is False


def test_constraint_design_keeps_strict_parser_and_forbids_repair() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert "OUTPUT_REPAIR" in spec["prohibited"]
    assert "MARKDOWN_FENCE_STRIPPING" in spec["prohibited"]
    assert "FALLBACK_TO_UNCONSTRAINED_DECODING" in spec["prohibited"]
    assert any("unchanged GateResponseV2" in item for item in spec["independent_postconditions"])


def test_tokenizer_feasibility_supports_raw_object_boundary() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["transformers_native_prefix_constraint_available"] is True
    assert evidence["opening_brace_token_count"] > 0
    assert evidence["fence_token_count"] > 0
    assert evidence["first_step_can_exclude_all_fence_tokens"] is True
    assert evidence["all_canonical_samples_round_trip_exact"] is True
    assert evidence["model_loaded"] is False
    assert evidence["model_calls"] == evidence["provider_calls"] == 0


def test_canonical_schema_examples_still_validate_with_current_parser() -> None:
    values = [
        {"gate_id": "FACTUAL_SEMANTIC", "decision": "PASS", "reason_records": []},
        {"gate_id": "FACTUAL_SEMANTIC", "decision": "FAIL", "reason_records": [{"code": "FSEM_UNSUPPORTED_CAUSALITY", "status": "DECISIVE", "candidate_span": "x", "authority_support": None, "unsupported_proposition": "y", "confidence": 0.9}]},
        {"gate_id": "FACTUAL_SEMANTIC", "decision": "INDETERMINATE", "reason_records": [{"code": "ADMISSION_INDETERMINATE", "status": "DECISIVE", "candidate_span": None, "authority_support": None, "unsupported_proposition": "y", "confidence": 0.5}]},
    ]
    for value in values:
        GateResponseV2.model_validate_json(json.dumps(value, separators=(",", ":")), strict=True)
