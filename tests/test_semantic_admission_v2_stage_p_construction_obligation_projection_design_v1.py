from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-projection-remediation-design-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-projection-design-v1-evidence/preflight.json"


def test_design_identity_and_decision_are_canonical():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["source_failure_review_identity"] == "730b2e3ac7a067a51852edbcc57ba2fe9810264a85e35b090395b1a2a4bcff9a"
    parts = [value["artifact_id"], value["source_frozen_run_identity"], value["failure_class"],
             "FORWARD_OBLIGATION_PROJECTION", "ROLE_RELATION_HOST_CONDITIONING",
             "REQUIRED_ID_CLOSURE_GUARD", "LITERAL_PATH_PRESERVED", "UNRESOLVED_FAIL_CLOSED",
             "NO_IMPLEMENTATION", "NO_RERUN", "NO_STAGE_C"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["design_identity"]
    assert value["decision"] == "REMEDIATE_WITH_FORWARD_OBLIGATION_PROJECTION_BEFORE_ANY_FURTHER_PROBE"


def test_design_preserves_literal_freedom_and_conditions_forward_roles():
    value = json.loads(ARTIFACT.read_text("utf-8")); candidate = value["remediation_candidate"]
    assert "first-class valid path" in candidate["literal_path"]
    points = {item["point"]: item["rule"] for item in candidate["projection_points"]}
    assert "CONTAINED_CREATIVE" in points["ENTRY_TYPE"]
    assert "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" in points["SCOPE_RELATION"]
    assert "exact host identifier" in points["CREATIVE_HOST_ENTRY_ID"]
    assert "Do not permit closing" in points["ENTRY_COLLECTION_CLOSE"]
    assert len(value["acceptance_contract"]["paired_zero_inference_fixtures"]) == 10


def test_design_is_nonexecuting_and_denies_all_authority():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert not any(value["authority"].values())
    assert evidence["result"] == "DESIGN_COMPLETE" and not evidence["implementation"]
    assert evidence["model_calls"] == evidence["provider_calls"] == evidence["inference_calls"] == 0
    assert evidence["reruns"] == evidence["stage_c_calls"] == 0
