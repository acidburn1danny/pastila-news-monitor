"""Verify Pilot 10 V5.2 static compatibility is sealed and non-authorizing."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot10_v5_2_compatibility_is_sealed_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("compatibility_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_V5_2_SOURCE_COMPATIBILITY_V1", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_V5_2_SOURCE_COMPATIBILITY_AUDIT_V1", core)
    assert receipt["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_2_NO_RELEASE"
    assert receipt["selected_proposition_id"] == "P3"
    assert receipt["typed_operand_extraction"]["verdict"] == "PASS_SOURCE_SHAPE_NEUTRAL"
    assert len(receipt["proposition_derived_abstract_plan_compatibility"]) == 3
    assert receipt["realization_or_surface_witnesses_created"] is False
    assert receipt["candidate_surface"] is None and receipt["constructor_release"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["deterministic_blockers"] == []
