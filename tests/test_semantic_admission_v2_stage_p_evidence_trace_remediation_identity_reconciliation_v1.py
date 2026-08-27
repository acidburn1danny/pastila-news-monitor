from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / ".semantic-admission-v2-stage-p-evidence-trace-remediation-v1-evidence/manifest.json"
RECONCILIATION = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-evidence-trace-remediation-identity-reconciliation-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_manifest_identity_and_expected_hashes_remain_immutable() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    values = [manifest["source_design_identity"]]
    values.extend(item["sha256"].lower() for item in manifest["artifacts"])
    identity = hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()
    assert identity == manifest["canonical_identity"] == "5024d765392e904855cba46b1861c15b23e98a33e72228998457c47cb96e71b3"
    expected = {item["path"]: item["sha256"] for item in manifest["artifacts"]}
    assert expected["tests/test_semantic_admission_v2_stage_p_phase_receipt_v2.py"] == "c2f305c68e2aadc5ab18aff1d613e3fb4de4684a4875691af561aa95bd6f52ef"
    assert expected["tests/test_semantic_admission_v2_durable_lifecycle_reconciliation_v1.py"] == "f3cf9e64dab56d177a96a552484dec08fd85111970f5a44105009554bcabbf77"


def test_only_the_two_recorded_historical_test_sources_differ() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    mismatches = [item["path"] for item in manifest["artifacts"] if _sha(ROOT / item["path"]) != item["sha256"]]
    assert mismatches == [
        "tests/test_semantic_admission_v2_stage_p_phase_receipt_v2.py",
        "tests/test_semantic_admission_v2_durable_lifecycle_reconciliation_v1.py",
    ]


def test_current_sources_and_provenance_are_bound_without_equivalence_claim() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    for item in receipt["unavailable_historical_sources"]:
        assert _sha(ROOT / item["path"]) == item["current_sha256"]
        assert item["expected_sha256"] != item["current_sha256"]
        assert item["expected_bytes_available_from_git"] is False
        assert item["expected_bytes_available_from_repository_content"] is False
    distinction = receipt["identity_distinction"]
    assert distinction["byte_equivalence_claimed"] is False
    assert distinction["semantic_equivalence_claimed"] is False
    assert distinction["silent_hash_rebinding"] is False


def test_reconciliation_identity_is_canonical_and_separate() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    claimed = receipt.pop("reconciliation_identity")
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert claimed == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert claimed.removeprefix("sha256:") != receipt["historical_bundle"]["canonical_identity"]


def test_reconciliation_grants_no_execution_or_semantic_authority() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    assert all(value is False for value in receipt["authority"].values())
    assert receipt["availability_audit"]["reconstruction_or_fabrication_permitted"] is False
