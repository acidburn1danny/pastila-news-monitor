import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_attempt_is_single_consumed_conformant_and_collision_pending():
    candidate = (ART / "humor-mechanics-batch2-development-pilot10-candidate01-v1.txt").read_bytes()
    evidence = json.loads((ART / "humor-mechanics-batch2-development-pilot10-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    core = dict(evidence)
    identity = core.pop("evidence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTION_ATTEMPT01_V1", core)
    assert hashlib.sha256(candidate).hexdigest() == evidence["candidate_surface_sha256"]
    assert len(candidate) == evidence["candidate_surface_byte_length"]
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0,
                                   "constructor_invocations": 1, "provider_invocations": 1,
                                   "emitter_invocations": 1}
    assert evidence["capability"]["state"] == "CONSUMED_1_OF_1"
    conformance = evidence["pre_emission_conformance"]
    assert conformance["verdict"] == "PASS_PRE_EMISSION_REALIZATION_CONFORMANCE"
    assert (conformance["causal_nodes_realized"], conformance["causal_nodes_required"]) == (3, 3)
    assert (conformance["causal_edges_realized"], conformance["causal_edges_required"]) == (2, 2)
    assert conformance["typed_operand_continuity"] == "PASS"
    assert conformance["terminal_result_witnesses"] == 1
    assert conformance["validation_preceded_candidate_persistence_and_emission"] is True
    assert evidence["fragment_collision_evaluation"] == "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02"
    assert evidence["g02_eligibility"] is False
    assert all(value is False for value in evidence["authority_matrix"].values())
