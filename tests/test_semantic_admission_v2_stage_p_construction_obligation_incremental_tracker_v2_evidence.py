from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_incremental_tracker_v2.py"
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-request-bound-tracker-design-v1.json"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-request-bound-incremental-tracker-v1-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-request-bound-incremental-tracker-v1-candidate-evidence/preflight.json"


def test_design_and_candidate_identities_reproduce():
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    design_parts = [design["artifact_id"], design["approved_full_ledger_dfa_identity"],
                    "CONTEXT_AND_DECODER_IDENTITY_BOUND",
                    "INCREMENTAL_OR_FULL_REBUILD_NO_SILENT_DECODE_INSTABILITY",
                    "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(design_parts).encode()).hexdigest() == design["design_identity"]
    implementation = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    candidate_parts = [artifact["artifact_id"], artifact["approved_design_identity"],
                       implementation, artifact["case01_context_identity"],
                       "INCREMENTAL_FULL_REBUILD_EQUIVALENCE", "ZERO_INFERENCE"]
    assert hashlib.sha256("\n".join(candidate_parts).encode()).hexdigest() == artifact["candidate_identity"]
    assert implementation == artifact["implementation_sha256"]


def test_no_downstream_import_authority_or_activity():
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("controller", "projector", "tokenizer", "evaluator", "runner",
                 "subprocess", "provider", "wsl")
    assert not any(any(word in item.lower() for word in forbidden) for item in imports)
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["candidate_identity"]
    assert all(value is False for value in design["authority"].values())
    assert all(value is False for value in artifact["authority"].values())
    for key in ("controller_objects", "projector_objects", "tokenizer_loads",
                "evaluator_objects", "runner_objects", "subprocess_launches",
                "model_loads", "provider_calls", "inference_calls"):
        assert preflight[key] == 0
    assert preflight["probe_constructed"] is False
