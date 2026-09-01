import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot11_attempt_is_consumed_and_failed_closed_without_candidate():
    candidate = ART / "humor-mechanics-batch2-development-pilot11-candidate01-v1.txt"
    evidence = json.loads((ART / "humor-mechanics-batch2-development-pilot11-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    core = dict(evidence); identity = core.pop("evidence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTION_ATTEMPT01_V1", core)
    assert not candidate.exists()
    assert evidence["terminal_classification"] == "FAIL_CLOSED_PRE_EMISSION_SEMANTIC_CONFORMANCE_NO_CANDIDATE"
    assert evidence["failure_code"] == "ValueError: typed actor predicate or patient lacks an explicit surface witness"
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0,
                                   "constructor_invocations": 1, "provider_invocations": 1,
                                   "emitter_invocations": 1}
    assert evidence["capability"]["state"] == "CONSUMED_1_OF_1"
    assert evidence["candidate_identity"] is None
    assert evidence["candidate_surface_present"] is False
    assert evidence["pre_emission_semantic_conformance"]["verdict"] == "FAIL_CLOSED_NO_EMISSION"
    assert evidence["pre_emission_semantic_conformance"]["validation_preceded_candidate_persistence_and_emission"] is True
    assert evidence["retry_authority"] is False and evidence["repair_authority"] is False
    assert evidence["fragment_collision_evaluation"] == "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02"
    assert evidence["g02_eligibility"] is False
    assert all(value is False for value in evidence["authority_matrix"].values())
