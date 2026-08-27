from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-compatibility-revalidation-v1.json"


def _load() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def test_revalidation_identity_and_bound_files_reproduce() -> None:
    artifact = _load()
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    paths = {
        "compatibility_harness_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_compatibility_audit_v1.py",
        "dfa_harness_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_dfa_audit_v1.py",
        "historical_compatibility_artifact_sha256": "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-compatibility-audit-v1.json",
        "historical_dfa_artifact_sha256": "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-dfa-audit-v1.json",
    }
    for field, relative in paths.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == artifact["bindings"][field]


def test_all_phases_pass_without_execution_authority() -> None:
    artifact = _load()
    results = artifact["phase_results"]
    assert results["phases_executed"] == list(range(8))
    assert results["prefix_token_checks"] == 10 * 131072
    assert results["false_accepts"] == results["false_rejects"] == 0
    assert results["contextual_piece_rewrites"] == 0
    assert results["contextual_suffix_mismatches"] == 0
    assert results["eos_only_at_terminal"] is True
    assert artifact["activity"]["model_loads"] == 0
    assert artifact["activity"]["inference_calls"] == 0
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "token_projection_candidate_development")
