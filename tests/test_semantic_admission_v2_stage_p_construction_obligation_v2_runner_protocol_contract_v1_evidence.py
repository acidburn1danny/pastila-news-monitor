from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_contract_v1 import RUNNER_PROTOCOL_IDENTITY, SCHEMA_IDENTITIES


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runner_protocol_contract_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_contract_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runner-protocol-contract-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-runner-protocol-contract-v1-evidence/preflight.json"


def test_runner_protocol_identity_schemas_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert artifact["runner_protocol_identity"] == RUNNER_PROTOCOL_IDENTITY
    assert artifact["schema_identities"] == SCHEMA_IDENTITIES
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"] == artifact["canonical_identity"]


def test_evidence_grants_schema_projection_only() -> None:
    artifact = json.loads(ARTIFACT.read_bytes()); authority = artifact["authority"]
    allowed = {"schema_contract_implementation", "canonical_schema_projection"}
    assert all(authority[key] is True for key in allowed)
    assert all(value is False for key, value in authority.items() if key not in allowed)
    preflight = json.loads(PREFLIGHT.read_bytes())
    allowed_preflight = {"candidate_identity", "runner_protocol_identity",
                         "focused_tests_passed", "canonical_schema_count"}
    assert all(value == 0 for key, value in preflight.items() if key not in allowed_preflight)
