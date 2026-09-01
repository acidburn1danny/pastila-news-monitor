from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_voice_template_remediation_is_sealed_and_non_authorizing() -> None:
    cases = [
        ("humor-mechanics-batch2-pilot07-cross-pilot-voice-template-root-cause-analysis-v1.json", "analysis_identity", "B2_PILOT07_CROSS_PILOT_VOICE_TEMPLATE_ROOT_CAUSE_ANALYSIS_V1"),
        ("humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json", "governance_identity", "B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_GOVERNANCE_V4"),
        ("humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json", "schema_identity", "B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_CONFORMANCE_SCHEMA_V4"),
        ("humor-mechanics-batch2-pilot07-cross-pilot-voice-template-regression-v1.json", "regression_identity", "B2_PILOT07_CROSS_PILOT_VOICE_TEMPLATE_REGRESSION_V1"),
        ("humor-mechanics-batch2-template-diverse-creative-marking-governance-v4-audit-v1.json", "audit_identity", "B2_TEMPLATE_DIVERSE_CREATIVE_MARKING_GOVERNANCE_V4_AUDIT_V1"),
    ]
    values = {}
    for name, field, namespace in cases:
        value = json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))
        core = dict(value)
        identity = core.pop(field)
        assert identity == seal(namespace, core)
        values[name] = value

    analysis = values[cases[0][0]]
    assert analysis["verdict"] == "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_TEMPLATE_AND_CROSS_PILOT_COLLISION_GOVERNANCE_BOUNDARY"
    assert analysis["exact_fragment_evidence"]["distinct_candidate_family_count"] == 3
    assert analysis["candidate_modified"] is False

    governance = values[cases[1][0]]
    assert governance["constructor_boundary"]["historical_v1_status"] == "HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_CONSTRUCTOR_RELEASE"
    assert governance["constructor_boundary"]["historical_v1_behavior_must_remain_byte_exact"] is True
    assert all(
        governance[key] is False
        for key in (
            "construction_authority",
            "source_acquisition_authority",
            "model_exposure_authority",
            "training_authority",
            "runtime_authority",
            "production_authority",
        )
    )

    regression = values[cases[3][0]]
    assert regression["expected_verdict"] == "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION"
    assert regression["candidate_modified"] is False
    assert regression["historical_constructor_modified"] is False

    audit = values[cases[4][0]]
    assert audit["verdict"] == "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION"
    assert audit["deterministic_blockers_remaining"] == []
    assert audit["candidate_or_source_created"] is False
    assert audit["candidate_or_historical_constructor_modified"] is False
