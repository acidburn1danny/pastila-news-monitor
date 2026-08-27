from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_compatibility_audit_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-compatibility-audit-v1.json"


def test_evidence_identity_and_harness_binding_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash == artifact["audit_harness_sha256"]
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]


def test_partial_result_does_not_claim_projector_equivalence() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    assert artifact["result"] == "PARTIAL_COMPLETE_DFA_PHASE_BLOCKED"
    assert artifact["completed_phases"] == [0, 1, 2, 3, 4]
    assert artifact["strategy_disposition"]["context_free_projector_equivalence"] == "UNPROVEN"
    assert artifact["strategy_disposition"]["context_free_trie_authorized"] is False
    assert artifact["blocked_phase"]["phase"] == 5


def test_receipt_is_tokenizer_only_zero_inference() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    receipt = artifact["execution_receipt"]
    assert receipt["tokenizer_loads"] == 1
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls",
                "projector_objects", "probe_constructions", "probe_executions"):
        assert receipt[key] == 0
    assert all(value is False for value in artifact["authority"].values())


def test_harness_contains_no_model_or_generation_import() -> None:
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(name.startswith(("torch", "peft", "accelerate")) for name in imported)
