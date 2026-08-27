from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_zero_model_callback_adapter_v1.py"
TEST=ROOT/"tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_zero_model_callback_adapter_v1.py"
ARTIFACT=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-zero-model-callback-adapter-v1.json"
PREFLIGHT=ROOT/".semantic-admission-v2-stage-p-construction-obligation-v2-zero-model-callback-adapter-v1-evidence/preflight.json"

def test_callback_adapter_identity_and_files_reproduce():
    artifact=json.loads(ARTIFACT.read_bytes())
    material="\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest()==artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest()==artifact["focused_test_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"]==artifact["canonical_identity"]

def test_evidence_stops_before_runtime_callback():
    artifact=json.loads(ARTIFACT.read_bytes()); authority=artifact["authority"]
    allowed={"synthetic_token_projection","receipt_construction"}
    assert all(authority[key] is True for key in allowed)
    assert all(value is False for key,value in authority.items() if key not in allowed)
    preflight=json.loads(PREFLIGHT.read_bytes())
    allowed_preflight={"candidate_identity","adapter_identity","focused_tests_passed","synthetic_projection_calls"}
    assert all(value==0 for key,value in preflight.items() if key not in allowed_preflight)
