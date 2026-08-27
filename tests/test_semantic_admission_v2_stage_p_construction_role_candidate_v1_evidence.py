from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_role_request_candidate_v1 import (
    APPROVED_DESIGN_IDENTITY,
    StagePConstructionRoleRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-candidate-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-role-v1-evidence/preflight.json"


def test_candidate_and_dependency_identities_are_exact() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    candidate = StagePConstructionRoleRequestCandidateV1(project_root=ROOT)
    assert value["candidate_identity"] == candidate.candidate_identity
    assert value["approved_design_identity"] == APPROVED_DESIGN_IDENTITY
    assert value["dependencies"] == {
        "prompt_identity": candidate.prompt_identity,
        "schema_identity": candidate.schema_identity,
        "constraint_identity": candidate.constraint_identity,
        "grammar_identity": candidate.grammar_identity,
        "tokenizer_identity": candidate.tokenizer_identity,
    }


def test_preflight_preserves_zero_inference_and_no_authority() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS"
    assert evidence["candidate_identity"] == value["candidate_identity"]
    assert evidence["approved_design_identity"] == value["approved_design_identity"]
    assert evidence["real_tokenizer"]["result"] == "PASS"
    assert evidence["real_tokenizer"]["terminal_can_eos"] is True
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls", "stage_c_calls"):
        assert evidence[key] == 0
    assert evidence["case01_executed"] is False
    assert not any(value["authority"].values())
