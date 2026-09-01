import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
def can(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v): return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()
def test_zero_family_qualification_identity_and_authority_state():
    value=json.loads((ART/"humor-mechanics-batch2-constructor-v5-3-3-zero-family-executable-integration-qualification.json").read_text(encoding="utf-8")); core=dict(value); identity=core.pop("qualification_identity")
    assert identity==seal("B2_CONSTRUCTOR_V5_3_3_ZERO_FAMILY_EXECUTABLE_QUALIFICATION",core)
    assert value["ZERO_FAMILY_INTEGRATION_VERDICT"]=="PASS_ZERO_FAMILY_REAL_RELEASE_PATH_EXECUTABLE_QUALIFICATION"
    assert value["INFRASTRUCTURE_READINESS_VERDICT"]=="READY_FOR_NEXT_INDEPENDENT_FAMILY_AS_MECHANISM_TRIAL"
    assert (value["family_constructor_invocations"],value["family_provider_invocations"],value["family_emitter_invocations"])==(0,0,0)
    assert value["new_development_candidate_surfaces"]==0 and value["family_capabilities_consumed"]==0
    assert value["blind_material_accessed"] is False and value["release_authority"] is False
    assert value["worktree_remediation_remainder"]=="NONE_IN_SCOPE"
