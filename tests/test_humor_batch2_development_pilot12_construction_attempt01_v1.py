import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/"docs/artifacts"
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v): return hashlib.sha256(canonical({"namespace":n,"value":v})).hexdigest()

def test_pilot12_attempt_consumed_and_failed_closed_without_candidate():
    evidence=json.loads((ART/"humor-mechanics-batch2-development-pilot12-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    core=dict(evidence); identity=core.pop("evidence_identity")
    assert identity==seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTION_ATTEMPT01_V1",core)
    assert not (ART/"humor-mechanics-batch2-development-pilot12-candidate01-v1.txt").exists()
    assert evidence["terminal_classification"]=="FAIL_CLOSED_PRE_EMISSION_SEMANTIC_CONFORMANCE_NO_CANDIDATE"
    assert evidence["failure_code"]=="ValueError: realized semantic roles affordances or causal rule differ from validated plan"
    assert evidence["attempt"]=={"authorized":1,"consumed":1,"remaining":0,"constructor_invocations":1,"provider_invocations":1,"emitter_invocations":0}
    assert evidence["capability"]["state"]=="CONSUMED_1_OF_1"
    assert evidence["candidate_identity"] is None and evidence["candidate_surface_present"] is False
    assert evidence["pre_emission_v5_3_1_conformance"]["verdict"]=="FAIL_CLOSED_NO_EMISSION"
    assert evidence["fragment_collision_evaluation"]=="NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02"
    assert evidence["g02_eligibility"] is False
