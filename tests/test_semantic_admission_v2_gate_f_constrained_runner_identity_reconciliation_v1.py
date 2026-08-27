from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence/manifest.json"
RECONCILIATION = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-constrained-runner-identity-reconciliation-v1.json"

PATHS = {
    "constrained_wsl_runner": "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py",
    "constrained_host_executor": "src/pastila_scout/semantic_admission_v2/constrained_core_executor_v1.py",
    "tests": "tests/test_semantic_admission_v2_gate_f_constrained_runner_v1.py",
    "host_preflight_runner": "scripts/preflight_semantic_admission_v2_gate_f_constrained_runner_v1.py",
    "wsl-lifecycle-preflight.json": ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence/wsl-lifecycle-preflight.json",
    "host-zero-inference-preflight.json": ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence/host-zero-inference-preflight.json",
    "test-attempt1-failure.json": ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence/test-attempt1-failure.json",
    "report.md": ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence/report.md",
}


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_historical_identity_and_expected_hashes_remain_immutable() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    assert manifest["canonical_identity"] == "56954793dafaec12845efa57b8432eede593f8dc3bef9e09e46a5d9e34bdb5ac"
    hashes = manifest["artifact_hashes_sha256"]
    assert hashes["constrained_host_executor"] == "c27ec5bd143783e84a39ac93ed6352c0b4b67425f63308bc1c9f0a270ac03b4c"
    assert hashes["tests"] == "1dc52df165fa8ca55450b08aeeee3fce2f6b5724c85012c523a15871f5d2c951"


def test_exactly_two_historical_artifacts_differ_and_six_match() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    mismatches = [key for key, expected in manifest["artifact_hashes_sha256"].items() if _sha(PATHS[key]) != expected]
    assert mismatches == ["constrained_host_executor", "tests"]


def test_current_git_artifacts_are_bound_without_equivalence_claim() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    provenance = receipt["normalization_provenance"]
    assert provenance["commit"] == "14bf5fa3084b4a5907c7ffe549f6cf7a219b6dcb"
    assert _sha(provenance["host_executor"]["path"]) == provenance["host_executor"]["sha256"]
    assert _sha(provenance["focused_test"]["path"]) == provenance["focused_test"]["sha256"]
    assert all(value is False for value in receipt["identity_distinction"].values())


def test_reconciliation_identity_is_canonical_and_distinct() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    claimed = receipt.pop("reconciliation_identity")
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert claimed == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert claimed.removeprefix("sha256:") != receipt["historical_bundle"]["canonical_identity"]


def test_reconciliation_grants_no_execution_or_runtime_authority() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    assert all(value is False for value in receipt["authority"].values())
    assert receipt["legacy_artifact_availability"]["reconstruction_or_fabrication_permitted"] is False
