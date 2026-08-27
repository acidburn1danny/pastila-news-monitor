from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_projector_binding_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_projector_binding_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-static-projector-binding-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-static-projector-binding-v1-evidence/preflight.json"


def test_static_binding_identity_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"] == artifact["canonical_identity"]


def test_preflight_has_no_execution_activity_or_authority() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert artifact["authority"]["static_projector_construction_from_injected_data"] is True
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "static_projector_construction_from_injected_data")
    allowed_nonzero = {"focused_tests_passed", "projector_objects_constructed_from_synthetic_token_pieces"}
    assert all(value == 0 for key, value in preflight.items()
               if key not in allowed_nonzero | {"candidate_identity"})
