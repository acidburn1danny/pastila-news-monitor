from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2, SourceProjectionReceiptV1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_contract_v2.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-projection-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-projection-candidate-evidence/preflight.json"


def _schema_hash(model):
    value = json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def test_candidate_identity_reproduces_from_implementation_and_both_schemas():
    artifact = json.loads(ARTIFACT.read_bytes())
    implementation = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    ledger_schema = _schema_hash(ConstructionObligationLedgerV2)
    receipt_schema = _schema_hash(SourceProjectionReceiptV1)
    parts = [artifact["artifact_id"], artifact["ledger_schema_version"],
             artifact["projection_receipt_schema_version"],
             artifact["approved_migration_design_identity"],
             artifact["approved_reference_candidate_identity"], implementation,
             ledger_schema, receipt_schema]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == artifact["candidate_identity"]
    assert implementation == artifact["implementation_sha256"]
    assert ledger_schema == artifact["ledger_json_schema_sha256"]
    assert receipt_schema == artifact["projection_receipt_json_schema_sha256"]


def test_preflight_and_authority_are_zero_inference():
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["candidate_identity"]
    for key in ("subprocess_launches", "evaluator_constructions", "runner_constructions",
                "grammar_constructions", "provider_calls", "model_loads", "inference_calls"):
        assert preflight[key] == 0
    assert preflight["probe_constructed"] is False
    assert all(value is False for value in artifact["authority"].values())


def test_module_imports_no_execution_or_grammar_path():
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("evaluator", "runner", "subprocess", "provider", "constraint", "grammar", "wsl")
    assert not any(any(word in item.lower() for word in forbidden) for item in imports)
