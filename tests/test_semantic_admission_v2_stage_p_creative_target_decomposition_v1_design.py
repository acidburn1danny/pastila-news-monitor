from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-creative-target-decomposition-v1-design.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-creative-target-decomposition-v1-design-evidence/preflight.json"


def test_design_identity_and_source_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    parts = [value["artifact_id"], value["source_failure_analysis_identity"],
             "SCOPE_GRAPH_V1_1_PRESERVED", "CREATIVE_TARGET_AUDIT_ADDED",
             "ZERO_INFERENCE_ONLY", "NO_IMPLEMENTATION", "NO_STAGE_C"]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_target_audit_has_three_way_semantic_resolution():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = {item["name"]: item for item in value["candidate_contract_delta"]["audit_record_fields"]}
    assert fields["target_class"]["enum"] == [
        "NONFACTUAL_EDITORIAL_OR_CREATIVE", "REAL_WORLD_PROPOSITION", "UNRESOLVED_TARGET"]
    assert fields["resolution"]["enum"] == [
        "RETAINED_NONFACTUAL", "RECONCILED_TO_LEDGER", "FAIL_CLOSED_UNRESOLVED"]
    assert "proposition_entry_id" in fields and "creative_host_entry_id" in fields


def test_design_preserves_nonfactual_creativity_and_fail_closed_behavior():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    rules = "\n".join(value["deterministic_coherence_rules"])
    prompt = "\n".join(value["prompt_candidate_requirements"])
    assert "NONFACTUAL_EDITORIAL_OR_CREATIVE" in rules
    assert "UNRESOLVED_TARGET" in rules and "INDETERMINATE" in rules
    assert "Do not label a target factual merely because authority corroborates it" in prompt
    assert value["case01_hidden_acceptance_contract"]["prohibited_shortcut"].endswith("false complete.")


def test_fixture_matrix_covers_required_contrasts():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    classes = {item["class"] for item in value["zero_inference_fixture_matrix"]}
    assert {"PURE_CONTAINED_CREATIVE", "GOVERNED_EMBEDDED_RETURN",
            "UNSUPPORTED_EMBEDDED_RETURN", "NORMATIVE_OR_EVALUATIVE_TARGET",
            "AMBIGUOUS_MIXED_SCOPE", "ENTITY_REUSE_WITHOUT_RETURN",
            "MULTIPLE_TARGETS_ONE_HOST", "TARGET_GLOSS_LEAK"} == classes


def test_no_implementation_or_execution_authority():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert all(flag is False for flag in value["implementation_boundary"].values())
    assert evidence["result"] == "DESIGN_COMPLETE"
    for key in ("schema_or_prompt_created", "request_or_runner_modified", "model_calls",
                "provider_calls", "inference_calls", "case01_rerun", "stage_c_calls"):
        assert evidence[key] in (False, 0)
