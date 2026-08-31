"""Verify source-only reverse-disclosure sufficiency remediation V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def verify(name: str, field: str, namespace: str) -> dict[str, Any]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    core = dict(value)
    identity = core.pop(field)
    assert seal(namespace, core) == identity
    return value


def test_reverse_disclosure_v2_is_fail_closed_and_non_authorizing() -> None:
    analysis = verify("humor-mechanics-batch2-pilot05-reverse-dependency-root-cause-analysis-v1.json", "analysis_identity", "B2_PILOT05_REVERSE_DEPENDENCY_ROOT_CAUSE_ANALYSIS_V1")
    governance = verify("humor-mechanics-batch2-reverse-disclosure-dependency-governance-v2.json", "governance_identity", "B2_REVERSE_DISCLOSURE_DEPENDENCY_GOVERNANCE_V2")
    schema = verify("humor-mechanics-batch2-reverse-disclosure-sufficiency-schema-v2.json", "schema_identity", "B2_REVERSE_DISCLOSURE_SUFFICIENCY_SCHEMA_V2")
    regression = verify("humor-mechanics-batch2-pilot05-reverse-disclosure-regression-v1.json", "regression_identity", "B2_PILOT05_REVERSE_DISCLOSURE_REGRESSION_V1")
    audit = verify("humor-mechanics-batch2-reverse-disclosure-governance-v2-audit-v1.json", "audit_identity", "B2_REVERSE_DISCLOSURE_GOVERNANCE_V2_AUDIT_V1")
    assert analysis["primary_responsibility"] == "REBALANCING_ASSIGNMENT_GOVERNANCE_BOUNDARY"
    assert governance["mandatory_pre_assignment_gate"]["evaluation_order"].startswith("BEFORE_")
    assert governance["assignment_binding_rules"]["selected_proposition_id_bound_before_release"] is True
    assert schema["candidate_surface_forbidden"] is True and schema["mechanism_label_forbidden"] is True
    assert regression["expected_preconstruction_result"] == "NO_SAFE_SELECTED_PROPOSITION"
    assert audit["verdict"] == "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION" and audit["deterministic_blockers"] == []
    assert not any((governance["construction_authority"], governance["model_exposure_authority"],
                    governance["training_authority"], governance["runtime_authority"], governance["production_authority"]))
