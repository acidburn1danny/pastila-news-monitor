from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.run_stage_p_construction_role_case01_probe_v1 import (
    CASE_ID, EVALUATOR_BINDING_IDENTITY, EVALUATOR_IDENTITY, PACK_RELATIVE, PACK_SHA256, construct,
)


ROOT = Path(__file__).resolve().parents[1]


def test_construct_binds_only_case01_without_launch(tmp_path, monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs)); raise AssertionError("probe execution forbidden")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    request, binding, evaluator = construct(project_root=ROOT, evidence_root=tmp_path / "evidence")
    assert CASE_ID == binding["case_id"] == "HMCV1-SASC-01"
    assert hashlib.sha256((ROOT / PACK_RELATIVE).read_bytes()).hexdigest() == PACK_SHA256
    assert binding["evaluator_binding_identity"] == EVALUATOR_BINDING_IDENTITY
    assert binding["evaluator_identity"] == evaluator.evaluator_identity == EVALUATOR_IDENTITY
    assert binding["maximum_provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False
    assert request["stage_id"] == "PROPOSITION_LEDGER"
    assert evaluator.render_prompt(request)
    assert calls == []


def test_construct_requires_fresh_exclusive_evidence_root(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    root = tmp_path / "evidence"; construct(project_root=ROOT, evidence_root=root)
    with pytest.raises(FileExistsError):
        construct(project_root=ROOT, evidence_root=root)


def test_probe_has_one_call_site_no_retry_and_no_stage_c():
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/run_stage_p_construction_role_case01_probe_v1.py").read_text("utf-8")
    assert source.count("output = evaluator(request)") == 1
    assert "retry" not in source.lower().replace('"retry_count": 0', "")
    assert '"stage_c_called": False' in source
    assert "STAGE_P_CONSTRAINT_LIVENESS_FAILURE" in source


def test_canonical_binding_identity_and_authority_denial():
    artifact = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-probe-binding-v1.json").read_text("utf-8"))
    parts = [artifact["artifact_id"], artifact["approved_evaluator_binding_identity"],
             artifact["case_id"], artifact["pack_sha256"], artifact["factual_summary_sha256"],
             artifact["candidate_sha256"], artifact["probe_runner_sha256"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == artifact["binding_identity"]
    assert not any(artifact["authority"].values())
