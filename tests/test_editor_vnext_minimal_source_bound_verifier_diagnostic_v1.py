import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("verifier", "scripts/run_editor_vnext_minimal_source_bound_verifier_diagnostic_v1.py")
V = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(V)
FIXTURES = json.loads(Path("docs/artifacts/editor-vnext-minimal-source-bound-verifier-diagnostic-v1-fixtures.json").read_text(encoding="utf-8"))


def case(name):
    return next(x for x in FIXTURES["cases"] if x["case_id"] == name)


def verify(name):
    item = case(name); return V.verify(item["source"], item["output"], item["case_id"])


def test_failure_class_to_protection_bindings():
    assert verify("duplicate-key")["verdict"] == "FAIL_PROVEN"  # structural
    assert verify("numeric-invention")["verdict"] == "FAIL_PROVEN"  # numeric
    assert verify("invented-actor")["verdict"] == "FAIL_PROVEN"  # entity novelty
    assert verify("qualification-upgrade")["verdict"] == "FAIL_PROVEN"  # narrow anchor


def test_romanian_numeric_canonicalization_avoids_false_rejection():
    assert V.canonical_numbers("2800 și 2409") == V.canonical_numbers("2.800 și 2 409")
    assert verify("numeric-ro-format")["verdict"] == "PASS_PROVEN"


def test_unproven_is_distinct_from_failure():
    assert verify("qualification-omission")["verdict"] == "UNPROVEN"
    assert verify("status-omission")["verdict"] == "UNPROVEN"
    assert verify("semantic-unsupported")["verdict"] == "UNPROVEN"


def test_minimal_receipt_does_not_persist_payload():
    result = verify("numeric-invention")
    assert result["payload_persisted"] is False
    assert "output" not in result and len(result["output_sha256"]) == 64
    assert all(set(x) <= {"code", "phase", "canonical_value", "detail"} for x in result["findings"])


def test_source_preserving_fallback_and_abstention():
    assert V.fallback("Prima propoziție. A doua propoziție.")["route"] == "SOURCE_PRESERVING_FALLBACK"
    assert V.fallback("Una. Două. Trei. Patru.")["route"] == "ABSTAIN"


def test_terminal_matrix_has_no_fixture_false_positive_or_negative():
    result = V.run(FIXTURES)
    assert result["status"] == "PASS"
    assert result["false_positive_findings"] == []
    assert result["false_negative_findings"] == []
    assert result["legacy_dependency_count"] == 0
