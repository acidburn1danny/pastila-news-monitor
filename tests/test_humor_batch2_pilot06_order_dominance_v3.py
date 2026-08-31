import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_order_dominance_remediation_is_sealed_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    cases = [("humor-mechanics-batch2-pilot06-order-dominance-root-cause-analysis-v1.json", "analysis_identity", "B2_PILOT06_ORDER_DOMINANCE_ROOT_CAUSE_ANALYSIS_V1"),
             ("humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json", "governance_identity", "B2_ORDER_ROBUST_CAUSAL_SPINE_GOVERNANCE_V3"),
             ("humor-mechanics-batch2-order-robust-causal-spine-conformance-schema-v3.json", "schema_identity", "B2_ORDER_ROBUST_CAUSAL_SPINE_CONFORMANCE_SCHEMA_V3"),
             ("humor-mechanics-batch2-pilot06-order-dominance-regression-v1.json", "regression_identity", "B2_PILOT06_ORDER_DOMINANCE_REGRESSION_V1"),
             ("humor-mechanics-batch2-order-robust-causal-spine-governance-v3-audit-v1.json", "audit_identity", "B2_ORDER_ROBUST_CAUSAL_SPINE_GOVERNANCE_V3_AUDIT_V1")]
    values = {}
    for name, field, namespace in cases:
        value = json.loads((base / name).read_text(encoding="utf-8")); core = dict(value); identity = core.pop(field)
        assert identity == seal(namespace, core); values[name] = value
    governance = values[cases[1][0]]
    assert all(governance[key] is False for key in ("construction_authority", "model_exposure_authority", "training_authority", "runtime_authority", "production_authority"))
    regression = values[cases[3][0]]
    assert regression["expected_verdict"] == "FAIL_DELAYED_DISCLOSURE_DOMINANCE"
    assert regression["candidate_modified"] is False
    audit = values[cases[4][0]]
    assert audit["verdict"] == "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION"
    assert audit["deterministic_blockers_remaining"] == []
