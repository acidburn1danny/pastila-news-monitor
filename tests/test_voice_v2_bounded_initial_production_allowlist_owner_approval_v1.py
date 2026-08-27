import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / ".pastilaacida-voice-v2-bounded-initial-production-allowlist-owner-approval-v1-evidence"
)


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_owner_approval_binds_exact_three_entries_without_activation():
    approval = load("01-owner-approval.json")
    assert approval["owner_statement"] == "APPROVE BOUNDED INITIAL PRODUCTION ALLOWLIST"
    assert approval["approved_expression_count"] == 3
    assert approval["approved_surface_count"] == 3
    assert len(approval["approved_entries"]) == 3
    boundary = load("02-authorization-boundary.json")
    assert boundary["policy_materialized"] is False
    assert boundary["policy_installed"] is False
    assert boundary["production_activation"] == {"expressions": 0, "surfaces": 0}
    assert boundary["proof_authority_promoted"] is False


def test_next_contract_remains_blocking_and_artifacts_are_canonical():
    residual = load("03-residual-gap-transition.json")
    assert residual["owner_adjudication"] == "RESOLVED_IN_THIS_SLICE"
    assert (
        residual["materialization_and_installation"]
        == "BLOCKED_BY_EXPLICIT_NEXT_CONTRACT"
    )
    assert residual["open_blocking_gaps"] == 1
    hashes = load("04-hashes.json")
    for name, identity in hashes.items():
        assert (
            identity
            == "sha256:" + hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
        )
    for path in EVIDENCE.glob("*.json"):
        raw = path.read_bytes()
        expected = (
            json.dumps(
                json.loads(raw),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        assert raw == expected
