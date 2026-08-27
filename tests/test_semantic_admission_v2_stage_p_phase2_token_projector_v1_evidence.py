import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-token-projector-v1-candidate.json"


def _candidate():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_candidate_identity_and_source_evidence_are_reproducible():
    candidate = _candidate()
    fields = candidate["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == candidate["canonical_identity"]
    source = candidate["candidate_source"]
    assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    tests = candidate["deterministic_synthetic_evidence"]
    assert hashlib.sha256((ROOT / tests["test_path"]).read_bytes()).hexdigest() == tests["test_sha256"]


def test_candidate_stops_at_the_authorized_boundary():
    candidate = _candidate()
    assert candidate["authority"]["candidate_only"] is True
    assert not any(value for key, value in candidate["authority"].items() if key != "candidate_only")
    activity = candidate["zero_inference_activity"]
    assert all(value == 0 for key, value in activity.items() if key != "reason_no_new_load")
    assert candidate["status"] == "OWNER_REVIEW_REQUIRED"


def test_required_dual_audit_evidence_is_explicit():
    evidence = _candidate()["deterministic_synthetic_evidence"]
    assert evidence["audit_lanes"] == ["COMMITMENT_SPAN", "AUTHORITY_RECONCILIATION"]
    for key in (
        "incremental_full_rebuild_allowed_set_equivalence",
        "complete_piece_full_rebuild_oracle_equivalence",
        "overlapping_terminal_and_prefix_pieces_checked",
        "unicode_scalar_and_json_escape_coverage",
        "request_bound_utf8_reference_coverage",
        "request_context_isolation",
        "fail_closed_no_legal_token_receipt_checked",
    ):
        assert evidence[key] is True
