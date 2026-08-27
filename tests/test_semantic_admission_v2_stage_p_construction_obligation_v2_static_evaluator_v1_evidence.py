from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_static_evaluator_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_static_evaluator_v1.py"
CONTRACT = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_contract_v2.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-static-evaluator-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-static-evaluator-v1-evidence/preflight.json"


def test_static_evaluator_identity_and_dependencies_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    assert hashlib.sha256(CONTRACT.read_bytes()).hexdigest() == artifact["v2_contract_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"] == artifact["canonical_identity"]


def test_evidence_grants_only_injected_static_validation() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert artifact["authority"]["injected_result_static_validation"] is True
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "injected_result_static_validation")
    allowed = {"candidate_identity", "focused_tests_passed",
               "synthetic_injected_result_evaluations"}
    assert all(value == 0 for key, value in preflight.items() if key not in allowed)
