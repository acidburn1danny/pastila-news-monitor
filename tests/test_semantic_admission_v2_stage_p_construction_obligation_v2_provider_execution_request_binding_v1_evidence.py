from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_provider_execution_request_binding_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_provider_execution_request_binding_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-provider-execution-request-binding-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-provider-execution-request-binding-v1-evidence/preflight.json"


def test_static_execution_request_binding_identity_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["canonical_identity"]
    assert preflight["binding_identity"] == artifact["binding_identity"]


def test_evidence_grants_static_construction_only() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    authority = artifact["authority"]
    assert authority["provider_execution_request_construction"] is True
    assert authority["provider_descriptor_resolution"] is True
    forbidden = (
        "provider_or_model_execution",
        "tokenizer_loading_or_characterization",
        "runner_executor_or_probe",
        "retry_repair_selection_or_fallback",
        "stage_c",
        "runtime_or_production",
    )
    assert all(authority[key] is False for key in forbidden)
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert all(
        preflight[key] == 0
        for key in (
            "provider_or_model_executions",
            "tokenizer_loads",
            "runner_executor_probe_calls",
            "retries_repairs_selections_fallbacks",
            "stage_c_operations",
            "runtime_or_production_activations",
        )
    )
