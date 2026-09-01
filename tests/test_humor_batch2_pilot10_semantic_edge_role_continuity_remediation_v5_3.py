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


def test_v5_3_semantic_remediation_is_sealed_narrow_and_non_authorizing():
    analysis = sealed("humor-mechanics-batch2-pilot10-semantic-edge-role-continuity-root-cause-analysis-v1.json", "analysis_identity", "B2_PILOT10_SEMANTIC_EDGE_ROLE_CONTINUITY_ROOT_CAUSE_ANALYSIS_V1")
    contract = sealed("humor-mechanics-batch2-development-constructor-contract-v5-3.json", "constructor_contract_identity", "B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_3")
    governance = sealed("humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json", "governance_identity", "B2_SEMANTIC_EDGE_ROLE_CONTINUITY_GOVERNANCE_V5_3")
    schema = sealed("humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json", "schema_identity", "B2_SEMANTIC_EDGE_ROLE_CONTINUITY_CONFORMANCE_SCHEMA_V5_3")
    implementation = sealed("humor-mechanics-batch2-development-constructor-semantic-edge-enforcement-v5-3.json", "semantic_enforcement_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_SEMANTIC_EDGE_ENFORCEMENT_V5_3")
    regression = sealed("humor-mechanics-batch2-pilot10-role-incompatible-terminal-edge-regression-v1.json", "regression_identity", "B2_PILOT10_ROLE_INCOMPATIBLE_TERMINAL_EDGE_REGRESSION_V1")
    audit = sealed("humor-mechanics-batch2-semantic-edge-role-continuity-v5-3-audit-v1.json", "audit_identity", "B2_SEMANTIC_EDGE_ROLE_CONTINUITY_V5_3_AUDIT_V1")
    assert analysis["defect_phase"] == "COMBINED_PLAN_TIME_REALIZATION_TIME_AND_PRE_EMISSION_VALIDATION_TIME"
    assert analysis["continuity_distinctions"]["terminal_witness_existence"].startswith("PASS_")
    assert contract["successor_provider_emitter_integration"].startswith("UNASSIGNED")
    assert governance["g02c_authority"].startswith("UNCHANGED_AUTHORITATIVE")
    assert schema["failure_effect"].startswith("NO_REALIZATION_OR_NO_CANDIDATE")
    assert implementation["constructor_provider_emitter_invocations"] == "0/0/0"
    assert regression["candidate_persistence_or_emission"] is False
    assert audit["verdict"].endswith("ZERO_CONSTRUCTION_NO_RELEASE")
    assert audit["release_authority"] is False
