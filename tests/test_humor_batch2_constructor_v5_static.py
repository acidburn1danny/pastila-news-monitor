"""Static and typed-plan tests that never invoke Constructor V5."""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.humor_batch2_development_constructor_v5 import TypedPlanNode, _derive_plan, _validate_plan

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
MODULE = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v5.py"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_v5_typed_plan_closes_without_surface_creation():
    plan = _derive_plan()
    _validate_plan(plan, frozenset({"FACT_SUBJECT", "FACT_RELATION", "FACT_OBJECT"}))
    assert len(plan) == 3


@pytest.mark.parametrize(
    "bad_node",
    [
        TypedPlanNode("L1", "FACT_OBJECT", "PREPOSITIONAL_PHRASE", "MOVE", "FACT_SUBJECT", (), (), "P5", True),
        TypedPlanNode("L1", "FACT_OBJECT.", "NOMINAL_HEAD", "MOVE", "FACT_SUBJECT", (), (), "P5", True),
        TypedPlanNode("L1", "MISSING", "NOMINAL_HEAD", "MOVE", "FACT_SUBJECT", (), (), "P5", True),
    ],
)
def test_v5_rejects_pilot08_operand_failure_shapes(bad_node):
    tail = _derive_plan()[1:]
    with pytest.raises(ValueError):
        _validate_plan((bad_node, *tail), frozenset({"FACT_SUBJECT", "FACT_RELATION", "FACT_OBJECT"}))


def test_v5_frozen_implementation_and_audit_are_sealed_and_uninvoked():
    implementation = json.loads((ART / "humor-mechanics-batch2-development-constructor-implementation-v5.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-constructor-v5-static-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(implementation)
    identity = core.pop("constructor_implementation_identity")
    assert seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5", core) == identity
    core = dict(audit)
    identity = core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_STATIC_AUDIT_V1", core) == identity
    module = MODULE.read_bytes()
    ast.parse(module.decode("utf-8"))
    assert hashlib.sha256(module).hexdigest() == implementation["module_sha256"]
    assert implementation["invocations"] == 0 and implementation["candidate_surface"] is None
    assert implementation["release_authority"] is False
    assert audit["constructor_invocations"] == audit["candidate_surfaces_created"] == 0
    assert audit["verdict"] == "PASS_IMPLEMENTATION_AND_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE"
