import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v):return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()
def test_pilot13_content_free_preparation_identities_and_authority():
    request=json.loads((ART/"humor-mechanics-batch2-development-pilot13-owner-input-request-v1.json").read_text(encoding="utf-8")); core=dict(request); identity=core.pop("owner_input_request_identity"); assert identity==seal("B2_DEVELOPMENT_PILOT13_OWNER_INPUT_REQUEST_V1",core)
    template=json.loads((ART/"humor-mechanics-batch2-development-pilot13-owner-declaration-template-v1.json").read_text(encoding="utf-8")); tcore=dict(template); tid=tcore.pop("template_identity"); assert tid==seal("B2_DEVELOPMENT_PILOT13_OWNER_DECLARATION_TEMPLATE_V1",tcore)
    audit=json.loads((ART/"humor-mechanics-batch2-development-pilot13-owner-input-preparation-audit-v1.json").read_text(encoding="utf-8")); acore=dict(audit); aid=acore.pop("audit_identity"); assert aid==seal("B2_DEVELOPMENT_PILOT13_OWNER_INPUT_PREPARATION_AUDIT_V1",acore)
    assert request["pilot_role"]=="LEGITIMATE_END_TO_END_MECHANISM_TRIAL" and request["status"]=="BLOCKED_AWAITING_OWNER_INPUT"
    assert request["qualification_identity"]=="9016f7a82cb04ba447c2c2ae4275861ef0bfbd16782c4be3584d85220f5b5c0a"
    assert all(value is False for value in request["authority_matrix"].values())
    assert audit["source_access_count"]==audit["source_files_created"]==audit["candidate_surfaces"]==audit["family_capabilities_consumed"]==0
    assert audit["constructor_provider_emitter_invocations"]=="0/0/0" and audit["blind_material_accessed"] is False
