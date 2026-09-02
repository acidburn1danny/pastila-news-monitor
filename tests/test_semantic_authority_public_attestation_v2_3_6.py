import copy,json
from pathlib import Path
import pytest
import pastila_scout.semantic_authority_public_attestation_v2_3_6 as m

POLICY=Path("docs/artifacts/semantic-contract-v2-3-6-public-attestation-governance.json")
def policy():return json.loads(POLICY.read_text(encoding="utf-8"))
def deployment(g):
 v={"schema":"SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_DEPLOYMENT_V2_3_6","governance_identity":g["governance_identity"],"repository_slug":"outside-owner/capture","repository_id":"123","owner_id":"456","workflow_path":g["workflow_policy"]["path"],"workflow_commit":"a"*40,"workflow_blob_sha256":"b"*64,"scheduled_utc":"2026-10-01T00:00:00Z","schedule_cron":"0 0 1 10 *","schedule_precommit_payload_sha256":"9"*64,"schedule_precommit_receipt_sha256":"0"*64,"schedule_precommit_verifier_sha256":"7"*64,"container_image_digest":"sha256:"+"c"*64,"dependency_lock_root":"d"*64,"acquisition_module_sha256":"e"*64,"metadata_proof_module_sha256":"f"*64,"provenance_module_sha256":"1"*64,"trusted_root_snapshot_sha256":"2"*64,"offline_verifier_sha256":"3"*64,"offline_launcher_sha256":"8"*64,"rekor_log_id":"4"*64,"rekor_origin":"rekor.sigstore.dev","deployment_commit":"a"*40}
 v["deployment_identity"]=m.identity(v,"deployment_identity");return v
def attestation(g,d,files,bundle=b"offline bundle"):
 manifest=[{"path":n,"length":len(x),"sha256":m.sha(x)} for n,x in sorted(files.items())]
 initiation={"deployment_identity":d["deployment_identity"],"repository_id":d["repository_id"],"workflow_commit":d["workflow_commit"],"workflow_path":d["workflow_path"],"scheduled_utc":d["scheduled_utc"],"schedule_precommit_payload_sha256":d["schedule_precommit_payload_sha256"],"event_name":"schedule","run_id":"10","run_attempt":1,"external_parameters":{}}
 return {"bundle_sha256":m.sha(bundle),"subject_sha256":m.sha(m.canonical(manifest)),"capture_manifest":manifest,"repository_slug":d["repository_slug"],"repository_id":d["repository_id"],"owner_id":d["owner_id"],"workflow_path":d["workflow_path"],"workflow_commit":d["workflow_commit"],"event_name":"schedule","run_id":"10","run_attempt":1,"runner_environment":"github-hosted","oidc_issuer":g["trust_policy"]["oidc_issuer"],"certificate_chain_verified":True,"fulcio_verified":True,"rekor_inclusion_verified":True,"rekor_checkpoint_verified":True,"rekor_log_id":d["rekor_log_id"],"rekor_origin":d["rekor_origin"],"rekor_uuid":"5"*64,"rekor_log_index":"12","rekor_integrated_time":"100","initiation_claim":initiation,"initiation_subject_sha256":m.sha(m.canonical(initiation)),"initiation_rekor_uuid":"7"*64,"initiation_rekor_log_index":"11","canonical_initiation_verified":True,"same_run_as_initiation":True,"predicate_type":g["provenance_policy"]["predicate_type"],"external_parameters":{},"trusted_root_snapshot_sha256":d["trusted_root_snapshot_sha256"],"offline_verifier_sha256":d["offline_verifier_sha256"],"deployment_identity":d["deployment_identity"]}

def test_governance_closed_and_acquisition_blocked():
 v=policy();m.validate_governance(v);assert not m.REAL_METADATA_ACQUISITION_READY and v["workflow_policy"]["inputs"]=={}
 assert v["workflow_policy"]["deployment_commit_is_inert"] is True
 assert v["workflow_policy"]["trigger"]=="SINGLE_PRECOMMITTED_GITHUB_SCHEDULE_EVENT"
 assert v["workflow_policy"]["schedule_precommit_rfc3161_required"] is True
@pytest.mark.parametrize("section,key,replacement",[("repository_policy","repository_secrets_prohibited",False),("workflow_policy","manual_dispatch",True),("workflow_policy","first_step_transparency_commitment_before_network",False),("execution_policy","container_digest_bound",False),("trust_policy","rekor_inclusion_body_set_and_checkpoint_verified",False),("provenance_policy","subject_digest_recomputed_from_bytes",False),("anti_gaming","later_matching_attestation_substitution",True)])
def test_governance_widening_fails(section,key,replacement):
 v=policy();v[section][key]=replacement;v["governance_identity"]=m.identity(v,"governance_identity")
 with pytest.raises(ValueError):m.validate_governance(v)
def test_deployment_manifest_strictly_identity_closed():
 g=policy();v=deployment(g);m.validate_deployment(v,g)
 for field,replacement in (("repository_id","0"),("workflow_commit","b"*40),("container_image_digest","c"*64),("rekor_origin","evil.invalid")):
  bad=copy.deepcopy(v);bad[field]=replacement;bad["deployment_identity"]=m.identity(bad,"deployment_identity")
  with pytest.raises(ValueError):m.validate_deployment(bad,g)
def test_bundle_subject_and_exact_artifact_set_recomputed():
 g=policy();d=deployment(g);files={"capture/crossref.json":b"one","capture/openalex.json":b"two"};bundle=b"offline bundle";s=attestation(g,d,files,bundle)
 m.validate_verified_attestation(s,bundle=bundle,capture_files=files,governance=g,deployment=d)
 with pytest.raises(ValueError,match="bundle"):m.validate_verified_attestation(s,bundle=b"substitute",capture_files=files,governance=g,deployment=d)
 with pytest.raises(ValueError,match="manifest"):m.validate_verified_attestation(s,bundle=bundle,capture_files={"capture/crossref.json":b"one"},governance=g,deployment=d)
@pytest.mark.parametrize("field,replacement",[("run_attempt",2),("same_run_as_initiation",False),("rekor_checkpoint_verified",False),("repository_id","999"),("workflow_commit","9"*40),("external_parameters",{"release":"owner-selected"})])
def test_identity_replay_and_redraw_variants_fail(field,replacement):
 g=policy();d=deployment(g);files={"capture/a":b"x"};s=attestation(g,d,files);s[field]=replacement
 with pytest.raises(ValueError):m.validate_verified_attestation(s,bundle=b"offline bundle",capture_files=files,governance=g,deployment=d)
def test_final_entry_must_follow_initiation():
 g=policy();d=deployment(g);files={"capture/a":b"x"};s=attestation(g,d,files);s["rekor_log_index"]="11"
 with pytest.raises(ValueError,match="does not follow"):m.validate_verified_attestation(s,bundle=b"offline bundle",capture_files=files,governance=g,deployment=d)
def test_initiation_claim_is_recomputed_not_asserted():
 g=policy();d=deployment(g);files={"capture/a":b"x"};s=attestation(g,d,files);s["initiation_claim"]["run_id"]="9"
 with pytest.raises(ValueError,match="initiation claim"):m.validate_verified_attestation(s,bundle=b"offline bundle",capture_files=files,governance=g,deployment=d)
def test_legacy_pseudo_verifier_is_unreachable_after_v237(tmp_path):
 g=policy();verifier=tmp_path/"verifier.exe";verifier.write_bytes(b"tool");launcher=tmp_path/"launcher.exe";launcher.write_bytes(b"isolate");trusted=b"root";d=deployment(g);d["offline_verifier_sha256"]=m.sha(b"tool");d["offline_launcher_sha256"]=m.sha(b"isolate");d["trusted_root_snapshot_sha256"]=m.sha(trusted);d["deployment_identity"]=m.identity(d,"deployment_identity")
 files={"capture/a":b"x"}
 with pytest.raises(RuntimeError,match="V2.3.7 real Cosign"):
  m.verify_attestation_bundle(bundle=b"offline bundle",trusted_root=trusted,capture_files=files,governance=g,deployment=d,verifier=verifier,launcher=launcher)
def test_qualification_identity_closed():
 v=json.loads(Path("docs/artifacts/semantic-contract-v2-3-6-public-attestation-zero-network-qualification.json").read_text(encoding="utf-8"));m.validate_qualification(v)
 bad=copy.deepcopy(v);bad["audit_findings"]=bad["audit_findings"][:-1];bad["qualification_identity"]=m.qualification_identity(bad)
 with pytest.raises(ValueError):m.validate_qualification(bad)
