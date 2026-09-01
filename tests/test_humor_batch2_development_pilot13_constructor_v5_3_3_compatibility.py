"""Verify Pilot 13 V5.3.3 static semantic compatibility evidence."""

import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot13_v5_3_3_compatibility_is_semantic_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("compatibility_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_V5_3_3_SOURCE_COMPATIBILITY_V1", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_V5_3_3_SOURCE_COMPATIBILITY_AUDIT_V1", core)
    assert receipt["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_3_STATIC_SEMANTIC_PLAN_NO_RELEASE"
    assert receipt["authority_binding"] == "PASS_EXACT_P5_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY_NO_P6_FALLBACK"
    assert receipt["semantic_plan_coverage"] == {"nodes": "3/3", "edges": "2/2", "terminal_edge_validated": True}
    assert len(receipt["recovered_plan_topology"]) == 3
    assert receipt["semantic_role_and_predicate_argument_signatures"] == "PASS_3_OF_3"
    assert receipt["required_role_produced_role_compatibility"] == "PASS_EACH_EDGE"
    assert receipt["action_affordance_compatibility"] == "PASS_EACH_NODE_AND_EDGE"
    assert receipt["counterfactual_dependency_and_non_arbitrariness"] == "PASS_2_OF_2_EDGES"
    assert receipt["terminal_edge_strength"] == "PASS_EQUAL_TO_INTERMEDIATE_EDGES"
    assert receipt["class_a_closure"] == "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER"
    assert receipt["class_b_state"] == "NOT_CREATED_PRE_REALIZATION"
    assert receipt["provider_schema"] == ["clause"] and receipt["provider_schema_verdict"] == "PASS_EXACT_ONE_FIELD"
    assert receipt["candidate_surface"] is None and receipt["constructor_release"] is False
    assert receipt["post_qualification_deterministic_infrastructure_defect"] == "NONE_DISCOVERED"
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["deterministic_blockers"] == []
