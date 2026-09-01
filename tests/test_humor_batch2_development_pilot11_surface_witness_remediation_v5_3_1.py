import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_pilot11_surface_witness_root_cause_and_successor_are_sealed():
    analysis = load("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-root-cause-v1.json")
    contract = load("humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json")
    implementation = load("humor-mechanics-batch2-development-constructor-surface-witness-alignment-implementation-v5-3-1.json")
    regression = load("humor-mechanics-batch2-development-pilot11-surface-witness-regression-v1.json")
    audit = load("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-remediation-audit-v1.json")
    for value, field, namespace in (
        (analysis, "analysis_identity", "B2_DEVELOPMENT_PILOT11_V5_3_SURFACE_WITNESS_ROOT_CAUSE_V1"),
        (contract, "successor_contract_identity", "B2_CONSTRUCTOR_SURFACE_WITNESS_ALIGNMENT_CONTRACT_V5_3_1"),
        (implementation, "implementation_identity", "B2_CONSTRUCTOR_SURFACE_WITNESS_ALIGNMENT_IMPLEMENTATION_V5_3_1"),
        (regression, "regression_identity", "B2_DEVELOPMENT_PILOT11_SURFACE_WITNESS_REGRESSION_V1"),
        (audit, "audit_identity", "B2_DEVELOPMENT_PILOT11_V5_3_SURFACE_WITNESS_REMEDIATION_AUDIT_V1"),
    ):
        core = dict(value); identity = core.pop(field)
        assert identity == seal(namespace, core)
    assert analysis["exact_failed_node"] == "L1" and analysis["exact_failed_role"] == "PATIENT"
    assert analysis["surface_semantic_role_status"] == "PRESENT_BUT_UNRECOGNIZED_LEGITIMATE_ROMANIAN_CASE_INFLECTION"
    assert analysis["static_semantic_plan"] == "PASS_REMAINS_CORRECT_AND_NONCAUSAL"
    assert regression["case_genuinely_missing"] == "PASS_FAIL_CLOSED"
    assert regression["case_legitimate_surface_variation"].startswith("PASS_RECOGNIZED_ONLY")
    assert audit["candidate_bytes_created"] == 0 and audit["constructor_invocations"] == 0
    assert audit["capability_restored_or_replaced"] is False
    assert audit["v5_3_semantic_enforcement_weakened"] is False
