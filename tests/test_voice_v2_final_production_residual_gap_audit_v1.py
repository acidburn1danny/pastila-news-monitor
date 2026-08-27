import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".pastilaacida-voice-v2-final-production-residual-gap-audit-v1-evidence"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_exactly_one_blocker_remains_and_it_is_the_allowlist():
    matrix = load("01-final-residual-gap-matrix.json")
    open_rows = [
        row for row in matrix["rows"] if row["current_status"] == "OPEN_BLOCKING"
    ]
    assert matrix["open_blocking_gaps"] == 1
    assert [row["gap_id"] for row in open_rows] == [
        "PRD-16-BOUNDED-INITIAL-PRODUCTION-ALLOWLIST"
    ]


def test_proof_and_import_gaps_are_closed():
    rows = {
        row["gap_id"]: row for row in load("01-final-residual-gap-matrix.json")["rows"]
    }
    assert rows["UGP-PROOF-COVERAGE-01"]["current_status"] == "CLOSED"
    assert rows["UGP-EXPRESSION-COVERAGE-01"]["current_status"] == "CLOSED"
    assert (
        rows["PRODUCTION-IMPORT-ISOLATION-REGRESSION-01"]["current_status"] == "CLOSED"
    )


def test_audit_does_not_promote_proof_authority_or_activate():
    authority = load("03-authority-boundary-audit.json")
    manifest = load("manifest.json")
    assert authority["proof_only_authorities_production_eligible"] is False
    assert authority["production_allowlist_exists"] is False
    assert manifest["production_activation"] == {"expressions": 0, "surfaces": 0}
    assert manifest["production_readiness"] == "NOT_READY_FOR_PRODUCTION_ACTIVATION"


def test_next_action_is_owner_allowlist_adjudication():
    manifest = load("manifest.json")
    assert manifest["exact_next_governed_action"] == (
        "PASTILAACIDA_VOICE_V2_BOUNDED_INITIAL_PRODUCTION_ALLOWLIST_OWNER_ADJUDICATION_V1"
    )
