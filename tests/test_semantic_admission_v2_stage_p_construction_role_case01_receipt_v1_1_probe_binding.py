from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.run_stage_p_construction_role_case01_receipt_v1_1_probe import (
    CASE_ID, EVALUATOR_IDENTITY, PACK_RELATIVE, PACK_SHA256,
    RECEIPT_PROPAGATION_CANDIDATE_IDENTITY, construct,
)


ROOT = Path(__file__).resolve().parents[1]


def test_construct_binds_v1_1_only_to_case01_without_launch(tmp_path, monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs)); raise AssertionError("probe execution forbidden")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    request, binding, evaluator = construct(project_root=ROOT, evidence_root=tmp_path / "evidence")
    assert CASE_ID == binding["case_id"] == "HMCV1-SASC-01"
    assert hashlib.sha256((ROOT / PACK_RELATIVE).read_bytes()).hexdigest() == PACK_SHA256
    assert binding["receipt_propagation_candidate_identity"] == RECEIPT_PROPAGATION_CANDIDATE_IDENTITY
    assert binding["evaluator_identity"] == evaluator.evaluator_identity == EVALUATOR_IDENTITY
    assert binding["maximum_provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False
    assert request["stage_id"] == "PROPOSITION_LEDGER" and evaluator.render_prompt(request)
    assert calls == []


def test_construct_requires_new_exclusive_root(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    root = tmp_path / "evidence"; construct(project_root=ROOT, evidence_root=root)
    with pytest.raises(FileExistsError):
        construct(project_root=ROOT, evidence_root=root)


def test_wrapper_has_one_call_site_typed_branch_and_no_stage_c():
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/run_stage_p_construction_role_case01_receipt_v1_1_probe.py").read_text("utf-8")
    assert source.count("output = evaluator(request)") == 1
    assert source.count("except StagePConstraintLivenessExecutionErrorV1") == 1
    assert '"STAGE_P_CONSTRAINT_LIVENESS_FAILURE"' in source
    assert "retry" not in source.lower().replace('"retry_count": 0', "")
    assert '"stage_c_called": False' in source


def test_binding_identity_and_authority_denial_are_canonical():
    artifact = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-probe-binding.json").read_text("utf-8"))
    parts = [artifact["artifact_id"], artifact["approved_receipt_propagation_candidate_identity"],
             artifact["evaluator_v1_1_identity"], artifact["case_id"], artifact["pack_sha256"],
             artifact["factual_summary_sha256"], artifact["candidate_sha256"],
             artifact["probe_wrapper_sha256"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == artifact["binding_identity"]
    assert not any(artifact["authority"].values())
