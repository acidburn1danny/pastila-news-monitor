"""Verify source-only Pilot 08 operand-closure remediation."""

import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_pilot08_operand_closure_remediation_is_sealed_and_non_authorizing():
    analysis = load("humor-mechanics-batch2-pilot08-operand-closure-root-cause-analysis-v1.json")
    contract = load("humor-mechanics-batch2-development-constructor-contract-v5.json")
    governance = load("humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json")
    schema = load("humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json")
    regression = load("humor-mechanics-batch2-pilot08-operand-closure-regression-v1.json")
    audit = load("humor-mechanics-batch2-typed-operand-closed-construction-governance-v5-audit-v1.json")
    for value, field, namespace in (
        (analysis, "analysis_identity", "B2_PILOT08_OPERAND_CLOSURE_ROOT_CAUSE_ANALYSIS_V1"),
        (contract, "constructor_contract_identity", "B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5"),
        (governance, "governance_identity", "B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_GOVERNANCE_V5"),
        (schema, "schema_identity", "B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_CONFORMANCE_SCHEMA_V5"),
        (regression, "regression_identity", "B2_PILOT08_OPERAND_CLOSURE_REGRESSION_V1"),
        (audit, "audit_identity", "B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_GOVERNANCE_V5_AUDIT_V1"),
    ):
        core = dict(value)
        identity = core.pop(field)
        assert seal(namespace, core) == identity
    assert analysis["verdict"] == "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_V4_TYPED_OPERAND_AND_STATIC_PLAN_VALIDATION_BOUNDARY"
    assert analysis["candidate_modified"] is False
    assert contract["implementation_identity"].startswith("UNASSIGNED_")
    assert contract["invocations"] == 0 and contract["candidate_surface"] is None
    assert contract["release_authority"] is False and contract["construction_authority"] is False
    assert governance["constructor_implementation_authority"] is False
    assert governance["source_acquisition_authority"] is False
    assert schema["candidate_surface_creation_authority"] is False
    assert regression["expected_v5_preconstruction_result"] == "REJECT_BEFORE_SURFACE_CREATION"
    assert audit["verdict"] == "PASS_SOURCE_ONLY_GOVERNANCE_AND_CONTRACT_REMEDIATION_ZERO_CONSTRUCTION"
    assert audit["constructor_invocations"] == audit["candidate_surfaces_created"] == 0
