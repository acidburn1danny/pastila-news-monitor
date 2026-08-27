from __future__ import annotations

import hashlib
import json
import ast
from pathlib import Path

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
    SourceSpanReferenceV1,
    resolve_source_span_v1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/immutable_source_span_reference_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-immutable-source-span-reference-v1-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-immutable-source-span-reference-v1-candidate-evidence/preflight.json"


def _schema_sha256():
    data = json.dumps(SourceSpanReferenceV1.model_json_schema(), sort_keys=True,
                      separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def test_candidate_identity_reproduces_from_exact_implementation_and_schema():
    artifact = json.loads(ARTIFACT.read_bytes())
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    schema_hash = _schema_sha256()
    parts = [artifact["artifact_id"], artifact["schema_version"], source_hash,
             schema_hash, artifact["approved_design_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == artifact["candidate_identity"]
    assert source_hash == artifact["implementation_sha256"]
    assert schema_hash == artifact["json_schema_sha256"]


def test_preflight_is_zero_inference_and_all_authority_remains_false(monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: calls.append((a, k)))
    source = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE,
                                        data="angajații".encode())
    reference = SourceSpanReferenceV1(source_role=source.role,
                                      source_sha256=source.sha256,
                                      start_utf8=0, end_utf8=len(source.data))
    assert resolve_source_span_v1(reference, expected_role=source.role,
                                  sources={source.role: source}).projected_bytes == source.data
    assert calls == []
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["candidate_identity"]
    assert preflight["subprocess_launches"] == preflight["provider_calls"] == preflight["inference_calls"] == 0
    assert preflight["probe_constructed"] is False
    assert all(value is False for value in artifact["authority"].values())


def test_module_has_no_execution_path_dependencies():
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(any(word in name.lower() for word in
                       ("evaluator", "runner", "subprocess", "provider", "wsl"))
                   for name in imports)
