"""Verify Pilot 12 V5.3.1 static semantic compatibility evidence."""

import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot12_v5_3_1_compatibility_is_semantic_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("compatibility_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_V5_3_1_SOURCE_COMPATIBILITY_V1", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_V5_3_1_SOURCE_COMPATIBILITY_AUDIT_V1", core)
    assert receipt["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_1_STATIC_SEMANTIC_PLAN_NO_RELEASE"
    assert receipt["authority_binding"] == "PASS_EXACT_P5_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY_NO_P6_FALLBACK"
    assert receipt["semantic_plan_coverage"] == {"nodes": "3/3", "edges": "2/2", "terminal_edge_validated": True}
    assert receipt["counterfactual_dependency_and_non_arbitrariness"] == "PASS_2_OF_2_EDGES"
    assert receipt["privileged_role_or_affordance_derivation"] == "ABSENT"
    assert receipt["alignment_semantics"].startswith("PASS_STATIC_CONSTRAINT_ONLY")
    assert receipt["realization_or_surface_witnesses_created"] is False
    assert receipt["candidate_surface"] is None and receipt["constructor_release"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["deterministic_blockers"] == []
