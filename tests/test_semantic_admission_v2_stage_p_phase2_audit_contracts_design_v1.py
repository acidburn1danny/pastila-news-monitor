from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-audit-contracts-design-v1.json"


def test_phase2_design_identity_and_prompt_bytes() -> None:
    value = json.loads(DESIGN.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    for audit in ("commitment_span_audit_v1", "authority_reconciliation_audit_v1"):
        prompt = value[audit]["prompt"]
        data = (ROOT / prompt["path"]).read_bytes()
        assert len(data) == prompt["bytes"]
        assert hashlib.sha256(data).hexdigest() == prompt["sha256"]


def test_model_cannot_self_authorize_coverage() -> None:
    value = json.loads(DESIGN.read_text("utf-8"))
    commitment = value["commitment_span_audit_v1"]
    authority = value["authority_reconciliation_audit_v1"]
    assert "derived_status" in commitment["controller_receipt_schema"]["model_cannot_emit"]
    assert "derived_status" in authority["controller_receipt_schema"]["model_cannot_emit"]
    assert "record_coverage_status" in authority["controller_receipt_schema"]["model_cannot_emit"]


def test_authority_audit_cannot_launder_commitment_failure() -> None:
    value = json.loads(DESIGN.read_text("utf-8"))
    assert value["authority_reconciliation_audit_v1"]["execution_precondition"].endswith("Otherwise this audit is not called.")
    assert value["fail_closed_precedence"][3] == "COMMITMENT_FAIL_OR_INDETERMINATE -> BLOCK_NO_AUTHORITY_CALL"
    assert value["zero_inference_constrained_grammar_analysis"]["tokenizer_or_model_loaded_in_this_analysis"] is False
    assert not any(value["authority"].values())
