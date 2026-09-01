import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
CANDIDATE = ART / "humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
EVIDENCE = ART / "humor-mechanics-batch2-development-pilot13-construction-attempt01-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_attempt_is_sealed_single_use_and_preemission_conformant():
    candidate = CANDIDATE.read_bytes()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    core = dict(evidence)
    identity = core.pop("evidence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTION_ATTEMPT01_V1", core)
    assert identity == "a53ee85f94b7d30570ac77dac1f0345aaf642eea98383fe7b2bac89ca29fcd9e"
    assert evidence["candidate_identity"] == "00dfb416e99d9d489c05cbf317a8b9654d51a5ecb0994220032c0cd68efe2fb6"
    assert hashlib.sha256(candidate).hexdigest() == evidence["candidate_surface_sha256"] == "907392cd76554340b09ef27145256b45f3c1ae013f41f4e4503ea156dc546759"
    assert len(candidate) == evidence["candidate_surface_byte_length"] == 552
    assert evidence["terminal_classification"] == "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    assert evidence["release_hydration"] == "PASS_EXACT_REQUALIFIED_V5_3_3"
    assert evidence["class_a_closure"] == "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER"
    assert evidence["clause_only_provider"] == "PASS_EXACT_ONE_FIELD_CLAUSE"
    assert evidence["class_b_byte_derivation"] == "PASS_OBSERVED_EXCLUSIVELY_FROM_ACTUAL_UTF8_BYTES"
    conformance = evidence["pre_emission_v5_3_3_conformance"]
    assert conformance["verdict"] == "PASS_ACTUAL_SURFACE_SEMANTIC_CONFORMANCE"
    assert conformance["nodes"] == "3/3" and conformance["edges"] == "2/2"
    assert conformance["actor_predicate_patient_and_produced_observations"] == 11
    assert conformance["byte_exact_coordinate_roundtrip"] is True
    assert conformance["terminal_result_realization"] == 1
    assert evidence["POST_REQUALIFICATION_DETERMINISTIC_INFRASTRUCTURE_DEFECT"] == "NONE_DISCOVERED"
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0,
                                   "constructor_invocations": 1, "provider_invocations": 1, "emitter_invocations": 1}
    assert evidence["capability"]["state"] == "CONSUMED_1_OF_1"
    assert evidence["fragment_collision_evaluation"] == "NOT_PERFORMED"
    assert evidence["fragment_collision_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_FRAGMENT_COLLISION"
    assert evidence["g02_eligibility"] is False
    assert evidence["retry_authority"] is False and evidence["repair_authority"] is False
