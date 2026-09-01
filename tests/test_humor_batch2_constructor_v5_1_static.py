"""Static/helper-only tests; the constructor entrypoint is never invoked."""

import json
import hashlib
import subprocess
from pathlib import Path

import pytest

from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    TypedPlanNode, derive_proposition_plan, extract_typed_operands, validate_typed_plan,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def git_json(commit, path):
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def fixture(commit, prefix, index):
    envelope = git_json(commit, prefix + "factual-authority-envelope.json")
    source = subprocess.check_output(["git", "show", f"{commit}:{prefix}source.utf8.txt"], cwd=ROOT)
    proposition = envelope["propositions"][index]
    bs, be = proposition["supporting_span"]["utf8_byte_coordinates"]
    return source[bs:be].decode(), proposition


@pytest.mark.parametrize("commit,prefix,index", [
    ("784eaacbc12c574e9a4d16e9f0059ae60a32b396", "docs/artifacts/humor-mechanics-batch2-development-pilot08-ingestion-v1/", 4),
    ("8991524fb136d29daa5f559ba8d9aef7386a2ac8", "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/", 4),
])
def test_source_shape_neutral_extraction_and_proposition_plan(commit, prefix, index):
    source, proposition = fixture(commit, prefix, index)
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    initial = {"FACT_OBJECT", operands.relation_id, "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"}
    validate_typed_plan(plan, frozenset(initial))
    assert len(plan) == 3 and all(operands.relation_id.rsplit("_", 1)[-1] in node.predicate_id for node in plan)


def test_unbound_derived_operand_fails_closed():
    source, proposition = fixture("8991524fb136d29daa5f559ba8d9aef7386a2ac8", "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/", 4)
    operands = extract_typed_operands(source, proposition)
    plan = list(derive_proposition_plan(operands))
    node = plan[1]
    plan[1] = TypedPlanNode(node.node_id, "UNBOUND_ACTOR", node.actor_role, node.predicate_id,
                            node.bound_patient_id, node.predecessor_node_ids, node.introduces_ids,
                            node.source_provenance, node.nonfactual_scope)
    with pytest.raises(ValueError, match="unbound actor"):
        validate_typed_plan(tuple(plan), frozenset({"FACT_OBJECT", "FACT_QUALIFICATION", operands.relation_id}))


def test_v5_1_frozen_contract_implementation_and_audit_are_non_authorizing():
    contract = json.loads((ART / "humor-mechanics-batch2-development-constructor-contract-v5-1.json").read_text(encoding="utf-8"))
    implementation = json.loads((ART / "humor-mechanics-batch2-development-constructor-implementation-v5-1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-constructor-v5-1-static-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(contract); identity = core.pop("constructor_contract_identity")
    assert identity == seal("B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_1", core)
    core = dict(implementation); identity = core.pop("constructor_implementation_identity")
    assert identity == seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_1", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_1_STATIC_AUDIT_V1", core)
    assert audit["pilot09_p5_source_compatibility"]["proposition_derived_plan_closure"] == "PASS"
    assert implementation["invocations"] == 0 and implementation["candidate_surface"] is None
    assert implementation["release_authority"] is False and implementation["construction_authority"] is False
    assert audit["constructor_invocations"] == audit["candidate_surfaces_created"] == 0
