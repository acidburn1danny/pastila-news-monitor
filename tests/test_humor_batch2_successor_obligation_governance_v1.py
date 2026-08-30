from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def assert_seal(record: dict, key: str, namespace: str) -> None:
    core = {k: v for k, v in record.items() if k != key}
    assert hashlib.sha256(canonical({"namespace": namespace, "value": core})).hexdigest() == record[key]


def span(seed: str, start: int) -> dict:
    return {"character_coordinates": [start, start + 1], "utf8_byte_coordinates": [start, start + 1], "sha256": hashlib.sha256(seed.encode()).hexdigest()}


def valid_receipt(schema: dict, obligation_identity: str) -> dict:
    return {
        "candidate_identity": "a" * 64,
        "obligation_identity": obligation_identity,
        "selected_proposition": {"proposition_id": "P1", "source_span": span("p", 0)},
        "continued_relation": {"subject_span": span("s", 0), "predicate_span": span("p", 1), "object_span": span("o", 2), "relation_fingerprint": "b" * 64},
        "steps": [
            {"ordinal": 1, "candidate_span": span("one", 10), "same_relation_operates": True, "locally_understandable": True},
            {"ordinal": 2, "candidate_span": span("two", 20), "same_relation_operates": True, "locally_understandable": True},
        ],
        "dependency": {"step2_requires_step1": True, "removal_test": "STEP2_STRUCTURALLY_UNAVAILABLE_WITHOUT_STEP1", "unrelated_replacement_possible": False},
        "imported_relation": {"present": False, "primary_connector": False},
        "entity_status": {"unauthorized_attribute_or_role_added": False, "human_agency_supplies_connection": False},
        "neighbor_substitution": {"comparison_or_domain_transfer": False, "magnitude_only": False, "enumeration": False, "disconnected_surprise": False},
        "verdict": "PASS",
    }


def test_identities_authority_and_gate_order() -> None:
    governance = load("humor-mechanics-batch2-successor-obligation-governance-v1.json")
    schema = load("humor-mechanics-batch2-obligation-conformance-schema-v1.json")
    regression = load("humor-mechanics-batch2-pilot01-successor-obligation-regression-v1.json")
    audit = load("humor-mechanics-batch2-successor-obligation-leakage-audit-v1.json")
    assert_seal(governance, "obligation_governance_identity", "B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V1")
    assert_seal(schema, "conformance_schema_identity", "B2_OBLIGATION_CONFORMANCE_SCHEMA_V1")
    assert_seal(regression, "regression_identity", "B2_PILOT01_SUCCESSOR_OBLIGATION_REGRESSION_V1")
    assert_seal(audit, "leakage_audit_identity", "B2_SUCCESSOR_OBLIGATION_LEAKAGE_AUDIT_V1")
    assert all(value is False for value in governance["authority_matrix"].values())
    assert governance["gate_sequence"].index("B2_G02C_OBLIGATION_CONFORMANCE") < governance["gate_sequence"].index("B2_G03_BLIND_MECHANISM_RECOVERY")
    assert governance["gate_sequence"][0] == "B2_G02B_PRECONSTRUCTION_BLINDING"


def test_constructor_view_has_no_taxonomy_or_reviewer_schema_leakage() -> None:
    governance = load("humor-mechanics-batch2-successor-obligation-governance-v1.json")
    visible = canonical(governance["constructor_visible_obligation"]).lower()
    for forbidden in (
        b"absurd_logical_extension", b"m13", b"mechanism", b"conformance_schema",
        b"relation_fingerprint", b"removal_test", b"candidate_span", b"personification",
        b"occupation", b"speech", b"emotion", b"pontaj", b"bureaucr",
    ):
        assert forbidden not in visible
    assert governance["constructor_must_not_receive"]


def test_schema_accepts_only_exact_ordered_fail_closed_receipt_shape() -> None:
    governance = load("humor-mechanics-batch2-successor-obligation-governance-v1.json")
    schema = load("humor-mechanics-batch2-obligation-conformance-schema-v1.json")
    receipt = valid_receipt(schema, governance["obligation_governance_identity"])
    jsonschema.validate(receipt, schema)
    duplicate = json.loads(json.dumps(receipt))
    duplicate["steps"][1]["ordinal"] = 1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(duplicate, schema)
    imported = json.loads(json.dumps(receipt))
    imported["imported_relation"]["present"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(imported, schema)
    anthropomorphic = json.loads(json.dumps(receipt))
    anthropomorphic["entity_status"]["human_agency_supplies_connection"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(anthropomorphic, schema)
    replaceable = json.loads(json.dumps(receipt))
    replaceable["dependency"]["unrelated_replacement_possible"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(replaceable, schema)


def test_pilot01_is_regression_only_and_fresh_family_is_required() -> None:
    governance = load("humor-mechanics-batch2-successor-obligation-governance-v1.json")
    regression = load("humor-mechanics-batch2-pilot01-successor-obligation-regression-v1.json")
    assert regression["observed_verdict"] == "FAIL"
    assert not regression["another_pilot01_attempt_allowed"]
    assert not governance["pilot01"]["another_construction_attempt"]
    assert governance["future_source_rule"]["fresh_independently_acquired_and_admitted_development_family_required"]
    assert not governance["future_source_rule"]["selection_by_target_friendly_topic_or_shape"]
