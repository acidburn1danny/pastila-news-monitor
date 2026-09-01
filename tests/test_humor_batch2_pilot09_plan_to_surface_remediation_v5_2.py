import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sealed(name, field, namespace):
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    core = dict(value); identity = core.pop(field)
    assert identity == seal(namespace, core)
    return value


def test_v5_2_remediation_is_sealed_narrow_and_non_authorizing():
    analysis = sealed("humor-mechanics-batch2-pilot09-plan-to-surface-root-cause-analysis-v1.json", "analysis_identity", "B2_PILOT09_PLAN_TO_SURFACE_ROOT_CAUSE_ANALYSIS_V1")
    contract = sealed("humor-mechanics-batch2-development-constructor-contract-v5-2.json", "constructor_contract_identity", "B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_2")
    governance = sealed("humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json", "governance_identity", "B2_PLAN_WITNESSED_REALIZATION_GOVERNANCE_V5_2")
    schema = sealed("humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json", "schema_identity", "B2_PLAN_WITNESSED_REALIZATION_CONFORMANCE_SCHEMA_V5_2")
    implementation = sealed("humor-mechanics-batch2-development-constructor-plan-to-surface-enforcement-v5-2.json", "enforcement_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_PLAN_TO_SURFACE_ENFORCEMENT_V5_2")
    regression = sealed("humor-mechanics-batch2-pilot09-plan-to-surface-regression-v1.json", "regression_identity", "B2_PILOT09_PLAN_TO_SURFACE_REGRESSION_V1")
    audit = sealed("humor-mechanics-batch2-plan-witnessed-realization-v5-2-audit-v1.json", "audit_identity", "B2_PLAN_WITNESSED_REALIZATION_V5_2_AUDIT_V1")
    assert analysis["exact_causal_boundary"].endswith("PRE_CANDIDATE_EMISSION")
    assert contract["realization_provider_identity"].startswith("UNASSIGNED")
    assert governance["coverage_requirements"] == {"causal_nodes": "N_OF_N", "causal_edges": "E_OF_E", "terminal_results": "1_OF_1"}
    assert schema["failure_effect"] == "NO_CANDIDATE_IDENTITY_NO_PERSISTENCE_NO_G02_ELIGIBILITY"
    assert implementation["constructor_invocations"] == implementation["candidate_surfaces_created"] == 0
    assert regression["expected_node_coverage"] == "0_OF_3_EXPLICIT_WITNESSES"
    assert audit["verdict"].endswith("ZERO_CONSTRUCTION_NO_RELEASE")
    assert audit["release_authority"] is False
