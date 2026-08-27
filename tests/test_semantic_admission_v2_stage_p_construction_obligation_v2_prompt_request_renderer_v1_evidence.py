from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-prompt-v1.txt"
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_request_renderer_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_request_renderer_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-prompt-request-renderer-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-prompt-request-renderer-v1-evidence/preflight.json"


def test_prompt_renderer_identity_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(PROMPT.read_bytes()).hexdigest() == artifact["prompt_sha256"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["renderer_implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"] == artifact["canonical_identity"]


def test_evidence_grants_only_prompt_and_pure_rendering() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    allowed_key = "prompt_bytes_and_pure_rendering"
    assert artifact["authority"][allowed_key] is True
    assert all(value is False for key, value in artifact["authority"].items()
               if key != allowed_key)
    allowed = {"candidate_identity", "focused_tests_passed", "synthetic_rendered_requests"}
    assert all(value == 0 for key, value in preflight.items() if key not in allowed)
