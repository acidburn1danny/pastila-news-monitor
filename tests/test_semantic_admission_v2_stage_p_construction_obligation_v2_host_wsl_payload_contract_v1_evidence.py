from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_host_wsl_payload_contract_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_host_wsl_payload_contract_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-host-wsl-payload-contract-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-host-wsl-payload-contract-v1-evidence/preflight.json"


def test_host_wsl_payload_contract_identity_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["canonical_identity"]
    assert preflight["contract_identity"] == artifact["contract_identity"]


def test_evidence_stops_at_payload_bytes() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    authority = artifact["authority"]
    assert authority["payload_contract_implementation"] is True
    assert authority["payload_serialization_and_validation"] is True
    assert all(value is False for key, value in authority.items()
               if key not in {"payload_contract_implementation", "payload_serialization_and_validation"})
    preflight = json.loads(PREFLIGHT.read_bytes())
    allowed = {"candidate_identity", "contract_identity", "focused_tests_passed",
               "synthetic_payload_round_trips"}
    assert all(value == 0 for key, value in preflight.items() if key not in allowed)
