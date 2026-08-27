from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-creative-host-suppression-remediation-design-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-creative-host-suppression-remediation-design-v1-evidence/preflight.json"


def test_design_identity_is_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    parts = [value["artifact_id"], value["source_owner_review_identity"],
        "MANDATORY_CONSTRUCTION_ROLE_AUDIT", "LEGITIMATE_LITERAL_PATH",
        "MATERIAL_CREATIVE_REQUIRES_HOST", "UNRESOLVED_FAIL_CLOSED",
        "NO_IMPLEMENTATION", "NO_RERUN", "NO_STAGE_C"]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_design_breaks_circular_trigger_without_forcing_creativity():
    value = json.loads(ARTIFACT.read_text("utf-8")); audit = value["bounded_candidate_design"]["construction_role_audit"]
    disposition = next(field for field in audit["fields"] if field["name"] == "overall_disposition")
    assert "NO_MATERIAL_CREATIVE_CONSTRUCTION" in disposition["enum"]
    roles = next(field for field in audit["record_fields"] if field["name"] == "construction_role")["enum"]
    assert {"LITERAL_ONLY", "MATERIAL_CREATIVE_OR_EDITORIAL", "MIXED_CREATIVE_AND_REAL_WORLD",
            "NON_MATERIAL_RHETORICAL_COLOR", "UNRESOLVED"} == set(roles)
    rules = "\n".join(value["deterministic_coherence_requirements"])
    assert "proposition-role selection cannot disable" in rules


def test_false_positive_controls_and_paired_fixtures_are_explicit():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    controls = "\n".join(value["false_positive_controls"])
    assert "literal governed facts" in controls and "Non-material rhetorical color" in controls
    pairs = {item["pair"] for item in value["paired_zero_inference_fixture_matrix"]}
    assert "LITERAL_REPORT_VS_METAPHORICAL_REPORT" in pairs
    assert "VALID_LITERAL_COMMITMENT_VS_FIGURATIVE_SPAN_COPY" in pairs
    assert len(pairs) == 7


def test_design_authorizes_no_implementation_or_execution():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "DESIGN_COMPLETE"
    assert all(flag is False for flag in value["authority"].values())
    for key in ("implementation", "schema_or_prompt_change", "model_calls", "provider_calls",
                "inference_calls", "case01_reruns", "stage_c_calls"):
        assert evidence[key] in (False, 0)
