from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_governance_v2_is_sealed_and_has_operational_naturalness_guards() -> None:
    value = load("humor-mechanics-batch2-successor-obligation-governance-v2.json")
    identity = value.pop("obligation_governance_identity")
    assert identity == seal("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V2", value)
    assert value["status"] == "FROZEN_SOURCE_ONLY_ZERO_CONSTRUCTION"
    text = json.dumps(value["constructor_visible_obligation"], ensure_ascii=False)
    assert "fără prefață tehnică" in text
    assert "Nu copia și nu parafraza limbajul procedural" in text
    assert "niciun conector" in text
    assert "continuare explicit fictivă" not in text
    assert "continuare fictivă" not in text
    assert value["pilot02"]["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())


def test_schema_preserves_blind_g04a_and_regression_rejects_pilot02_early() -> None:
    schema = load("humor-mechanics-batch2-successor-obligation-conformance-schema-v2.json")
    schema_identity = schema.pop("conformance_schema_identity")
    assert schema_identity == seal("B2_SUCCESSOR_OBLIGATION_CONFORMANCE_SCHEMA_V2", schema)
    assert schema["naturalness_precheck"]["does_not_replace_blind_g04a"] is True
    assert "GOVERNANCE_LANGUAGE_ABSENT" in schema["required_predicates"]
    assert "IDIOMATIC_ROMANIAN_PRECHECK_PASS" in schema["required_predicates"]

    regression = load("humor-mechanics-batch2-successor-obligation-v2-pilot02-naturalness-regression-v1.json")
    regression_identity = regression.pop("regression_identity")
    assert regression_identity == seal("B2_SUCCESSOR_OBLIGATION_V2_PILOT02_NATURALNESS_REGRESSION_V1", regression)
    assert set(regression["predicates"].values()) == {"FAIL"}
    assert regression["earliest_rejection"] == "G02C_EARLY_NATURALNESS_PRECHECK_BEFORE_G03"
    assert regression["candidate_bytes_modified"] is False


def test_root_cause_and_leakage_audit_are_sealed_and_clean() -> None:
    analysis = load("humor-mechanics-batch2-successor-obligation-naturalness-root-cause-analysis-v1.json")
    analysis_identity = analysis.pop("analysis_identity")
    assert analysis_identity == seal("B2_SUCCESSOR_OBLIGATION_NATURALNESS_ROOT_CAUSE_ANALYSIS_V1", analysis)
    assert analysis["analysis_verdict"] == "ROOT_CAUSE_CONFIRMED_AT_OBLIGATION_GOVERNANCE_BOUNDARY"
    assert analysis["source_family_causal"] is False
    assert analysis["candidate_repair_required_or_authorized"] is False

    audit = load("humor-mechanics-batch2-successor-obligation-v2-naturalness-leakage-audit-v1.json")
    audit_identity = audit.pop("audit_identity")
    assert audit_identity == seal("B2_SUCCESSOR_OBLIGATION_V2_NATURALNESS_LEAKAGE_AUDIT_V1", audit)
    assert audit["audit_verdict"] == "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION"
    assert audit["deterministic_blockers"] == []
    assert audit["checks"]["g04a_bypass"] == "PASS_EARLY_SCREEN_DOES_NOT_REPLACE_BLIND_G04A"
