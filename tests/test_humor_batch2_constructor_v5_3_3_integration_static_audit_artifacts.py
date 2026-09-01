import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
def can(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v): return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()

def test_v533_audit_is_identity_bound_zero_invocation_and_single_source():
    value=json.loads((ART/"humor-mechanics-batch2-constructor-v5-3-3-integration-static-audit.json").read_text(encoding="utf-8"))
    core=dict(value); identity=core.pop("static_audit_identity")
    assert identity==seal("B2_CONSTRUCTOR_V5_3_3_INTEGRATION_STATIC_AUDIT",core)
    assert value["P10_P11_P12_SHARED_BOUNDARY_VERDICT"]=="SHARED_EPISTEMIC_CLASS_DUPLICATION_AND_POST_HOC_RECONCILIATION_DEFECT_CONFIRMED_AND_REMOVED"
    assert value["FIVE_FIELD_PROVIDER_SINGLE_SOURCE_OF_TRUTH_VERDICT"]=="FAIL_DUPLICATED_GENERATIVE_REPRESENTATION_REMEDIATED_TO_CLAUSE_ONLY_PROVIDER"
    assert value["counts"]=={"A":39,"B":17,"C":1}
    assert not any(value["cross_product"].values())
    assert value["legacy_reachability"].startswith("PASS_UNREACHABLE")
    assert value["known_blockers_before_next_family"]==[]
    assert (value["constructor_invocations"],value["provider_invocations"],value["emitter_invocations"],value["candidate_surfaces"])==(0,0,0,0)
    assert value["release_authority"] is False
