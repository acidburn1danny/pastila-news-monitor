"""Public-transparency publisher-response provenance governance (V2.3.6)."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any,Mapping

DOMAIN="PASTILA_SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_V2_3_6"
V235_IDENTITY="552edb1f10a18f027e641b336580d27f4c4d5c653c69fe08fa1d0161b4008e81"
HEX64=re.compile(r"^[0-9a-f]{64}$");HEX40=re.compile(r"^[0-9a-f]{40}$");UINT=re.compile(r"^[1-9][0-9]*$")
ENDPOINT_PURPOSES=("CROSSREF_RELEASE_INDEX","CROSSREF_RELEASE_RECORD","CROSSREF_ARCHIVE_INDEX","CROSSREF_ARCHIVE_OBJECT_HEAD","OPENALEX_RELEASE_NOTES","OPENALEX_MANIFEST_VERSION_INDEX","OPENALEX_MANIFEST","OPENALEX_ARCHIVE_OBJECT_HEAD")
REAL_METADATA_ACQUISITION_READY=False
REMAINING_BLOCKERS=("PUBLIC_REPOSITORY_WORKFLOW_DEPLOYMENT_MANIFEST_AND_PINNED_OFFLINE_VERIFIER_NOT_YET_FROZEN",)

def canonical(value:Any)->bytes:return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def identity(value:Mapping[str,Any],field:str)->str:
 body=dict(value);body.pop(field,None);return sha(canonical(body))
def _exact(actual,expected,label):
 if actual!=expected:raise ValueError(label)

def validate_governance(v:Mapping[str,Any])->None:
 required={"schema","supersedes","repository_policy","workflow_policy","execution_policy","trust_policy","provenance_policy","anti_gaming","deployment_state","real_metadata_acquisition_ready","remaining_blockers","governance_identity"}
 if set(v)!=required or v["schema"]!="SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_GOVERNANCE_V2_3_6":raise ValueError("governance schema")
 if v["supersedes"]!=V235_IDENTITY:raise ValueError("governance lineage")
 _exact(v["repository_policy"],{"visibility":"PUBLIC","numeric_repository_id_bound":True,"numeric_owner_id_bound":True,"repository_slug_bound":True,"actions_permissions_frozen":True,"environments_prohibited":True,"repository_variables_prohibited":True,"repository_secrets_prohibited":True,"fork_pull_requests_prohibited":True},"repository policy")
 _exact(v["workflow_policy"],{"path":".github/workflows/semantic-authority-metadata-capture-v2-3-6.yml","source_commit_bound":True,"workflow_blob_sha256_bound":True,"trigger":"SINGLE_PRECOMMITTED_GITHUB_SCHEDULE_EVENT","deployment_commit_is_inert":True,"schedule_utc_and_cron_bound":True,"schedule_precommit_rfc3161_required":True,"deployment_after_schedule_precommit_required":True,"missed_delayed_cancelled_or_failed_schedule_is_terminal":True,"manual_dispatch":False,"push_dispatch":False,"workflow_call":False,"inputs":{},"permissions":{"contents":"read","id-token":"write","attestations":"write"},"clean_checkout_exact_sha":True,"persist_credentials":False,"first_step_transparency_commitment_before_network":True,"capture_only_after_commitment_inclusion_verified":True,"failed_or_cancelled_committed_run_is_terminal":True,"rerun_or_distinct_run_substitution":False},"workflow policy")
 _exact(v["execution_policy"],{"runner":"GITHUB_HOSTED","container_digest_bound":True,"dependency_lock_root_bound":True,"network":"DIRECT_HTTPS_FROZEN_ENDPOINTS_ONLY","proxy_environment_rejected":True,"source_endpoints":list(ENDPOINT_PURPOSES),"endpoint_order_frozen":True,"response_bytes_not_exposed_before_final_attestation":True},"execution policy")
 _exact(v["trust_policy"],{"oidc_issuer":"https://token.actions.githubusercontent.com","certificate_authority":"SIGSTORE_FULCIO_PUBLIC_GOOD_INSTANCE","transparency_log":"SIGSTORE_REKOR_PUBLIC_GOOD_INSTANCE","trusted_root_snapshot_sha256_bound":True,"offline_verifier_sha256_bound":True,"offline_bundle_bytes_sha256_bound":True,"certificate_chain_and_validity_verified":True,"rekor_inclusion_body_set_and_checkpoint_verified":True,"rekor_log_id_and_origin_bound":True,"integrated_time_bound":True},"trust policy")
 _exact(v["provenance_policy"],{"statement":"DSSE_IN_TOTO_V1","predicate_type":"PASTILA_PUBLISHER_CAPTURE_V2_3_6","subject":"CANONICAL_CAPTURE_SET_ROOT","subject_digest_recomputed_from_bytes":True,"capture_manifest_exact_file_set_lengths_and_sha256":True,"repository_workflow_ref_sha_event_run_id_and_run_attempt_bound":True,"numeric_repository_and_owner_ids_bound":True,"runner_environment":"github-hosted","external_parameters":{},"capture_run_identity_derived_from_transparency_commitment":True,"initiation_and_final_attestation_same_run_required":True,"final_attestation_references_initiation_rekor_uuid_and_log_index":True},"provenance policy")
 _exact(v["anti_gaming"],{"owner_supplied_content":False,"owner_supplied_endpoint":False,"owner_supplied_release":False,"owner_supplied_environment_or_secret":False,"redraw_or_resample":False,"cancel_retry_or_rerun_after_commitment":False,"later_matching_attestation_substitution":False,"unattested_artifact_accepted":False,"private_repository_accepted":False,"mutable_workflow_ref_accepted":False,"verifier_summary_without_bundle_accepted":False,"artifact_set_with_missing_or_extra_members_accepted":False,"availability_withholding_can_change_accepted_outcome":False},"anti-gaming")
 _exact(v["deployment_state"],{"status":"NOT_DEPLOYED","deployment_manifest_identity":None},"deployment state")
 if v["real_metadata_acquisition_ready"] is not False or v["remaining_blockers"]!=list(REMAINING_BLOCKERS):raise ValueError("readiness closure")
 if v["governance_identity"]!=identity(v,"governance_identity"):raise ValueError("governance identity")

def validate_deployment(v:Mapping[str,Any],g:Mapping[str,Any])->None:
 validate_governance(g)
 required={"schema","governance_identity","repository_slug","repository_id","owner_id","workflow_path","workflow_commit","workflow_blob_sha256","scheduled_utc","schedule_cron","schedule_precommit_payload_sha256","schedule_precommit_receipt_sha256","schedule_precommit_verifier_sha256","container_image_digest","dependency_lock_root","acquisition_module_sha256","metadata_proof_module_sha256","provenance_module_sha256","trusted_root_snapshot_sha256","offline_verifier_sha256","offline_launcher_sha256","rekor_log_id","rekor_origin","deployment_commit","deployment_identity"}
 if set(v)!=required or v["schema"]!="SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_DEPLOYMENT_V2_3_6":raise ValueError("deployment schema")
 if v["governance_identity"]!=g["governance_identity"]:raise ValueError("deployment governance skew")
 if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+",str(v["repository_slug"])):raise ValueError("repository slug")
 if not UINT.fullmatch(str(v["repository_id"])) or not UINT.fullmatch(str(v["owner_id"])):raise ValueError("numeric repository identity")
 if v["workflow_path"]!=g["workflow_policy"]["path"]:raise ValueError("workflow path")
 if not HEX40.fullmatch(str(v["workflow_commit"])) or v["deployment_commit"]!=v["workflow_commit"]:raise ValueError("workflow/deployment commit")
 if not re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:00Z",str(v["scheduled_utc"])) or not re.fullmatch(r"\d\d? \d\d? \d\d? \d\d? \*",str(v["schedule_cron"])):raise ValueError("schedule precommit")
 for field in ("workflow_blob_sha256","schedule_precommit_payload_sha256","schedule_precommit_receipt_sha256","schedule_precommit_verifier_sha256","dependency_lock_root","acquisition_module_sha256","metadata_proof_module_sha256","provenance_module_sha256","trusted_root_snapshot_sha256","offline_verifier_sha256","offline_launcher_sha256","rekor_log_id"):
  if not HEX64.fullmatch(str(v[field])):raise ValueError("deployment hash: "+field)
 if not re.fullmatch(r"sha256:[0-9a-f]{64}",str(v["container_image_digest"])):raise ValueError("container digest")
 if v["rekor_origin"]!="rekor.sigstore.dev":raise ValueError("Rekor origin")
 if v["deployment_identity"]!=identity(v,"deployment_identity"):raise ValueError("deployment identity")

def validate_verified_attestation(s:Mapping[str,Any],*,bundle:bytes,capture_files:Mapping[str,bytes],governance:Mapping[str,Any],deployment:Mapping[str,Any])->None:
 """Validate pinned-verifier output and independently bind bundle and capture bytes."""
 validate_deployment(deployment,governance)
 required={"bundle_sha256","subject_sha256","capture_manifest","repository_slug","repository_id","owner_id","workflow_path","workflow_commit","event_name","run_id","run_attempt","runner_environment","oidc_issuer","certificate_chain_verified","fulcio_verified","rekor_inclusion_verified","rekor_checkpoint_verified","rekor_log_id","rekor_origin","rekor_uuid","rekor_log_index","rekor_integrated_time","initiation_claim","initiation_subject_sha256","initiation_rekor_uuid","initiation_rekor_log_index","canonical_initiation_verified","same_run_as_initiation","predicate_type","external_parameters","trusted_root_snapshot_sha256","offline_verifier_sha256","deployment_identity"}
 if set(s)!=required:raise ValueError("attestation summary schema")
 if not bundle or s["bundle_sha256"]!=sha(bundle):raise ValueError("offline bundle bytes unbound")
 manifest=s["capture_manifest"]
 if not isinstance(manifest,list) or not manifest or len(manifest)!=len(capture_files):raise ValueError("capture manifest closure")
 if sorted(capture_files)!=sorted(str(x.get("path")) for x in manifest if isinstance(x,dict)):raise ValueError("capture file membership")
 for item in manifest:
  if set(item)!={"path","length","sha256"} or item["path"] not in capture_files:raise ValueError("capture manifest item")
  payload=capture_files[item["path"]]
  if item["length"]!=len(payload) or item["sha256"]!=sha(payload):raise ValueError("capture byte commitment")
 root=sha(canonical(sorted(manifest,key=lambda x:x["path"])))
 if s["subject_sha256"]!=root:raise ValueError("attestation subject digest")
 expected={"repository_slug":deployment["repository_slug"],"repository_id":deployment["repository_id"],"owner_id":deployment["owner_id"],"workflow_path":deployment["workflow_path"],"workflow_commit":deployment["workflow_commit"],"event_name":"schedule","run_attempt":1,"runner_environment":"github-hosted","oidc_issuer":governance["trust_policy"]["oidc_issuer"],"certificate_chain_verified":True,"fulcio_verified":True,"rekor_inclusion_verified":True,"rekor_checkpoint_verified":True,"rekor_log_id":deployment["rekor_log_id"],"rekor_origin":deployment["rekor_origin"],"canonical_initiation_verified":True,"same_run_as_initiation":True,"predicate_type":governance["provenance_policy"]["predicate_type"],"external_parameters":{},"trusted_root_snapshot_sha256":deployment["trusted_root_snapshot_sha256"],"offline_verifier_sha256":deployment["offline_verifier_sha256"],"deployment_identity":deployment["deployment_identity"]}
 if any(s.get(k)!=v for k,v in expected.items()):raise ValueError("attestation identity or trust mismatch")
 for field in ("run_id","rekor_log_index","initiation_rekor_log_index","rekor_integrated_time"):
  if not UINT.fullmatch(str(s[field])):raise ValueError("run/log numeric identity")
 for field in ("rekor_uuid","initiation_rekor_uuid","initiation_subject_sha256"):
  if not HEX64.fullmatch(str(s[field])):raise ValueError("transparency initiation identity")
 if int(s["rekor_log_index"])<=int(s["initiation_rekor_log_index"]):raise ValueError("final attestation does not follow initiation")
 initiation={"deployment_identity":deployment["deployment_identity"],"repository_id":deployment["repository_id"],"workflow_commit":deployment["workflow_commit"],"workflow_path":deployment["workflow_path"],"scheduled_utc":deployment["scheduled_utc"],"schedule_precommit_payload_sha256":deployment["schedule_precommit_payload_sha256"],"event_name":"schedule","run_id":s["run_id"],"run_attempt":1,"external_parameters":{}}
 if s["initiation_claim"]!=initiation or s["initiation_subject_sha256"]!=sha(canonical(initiation)):raise ValueError("initiation claim binding")

def verify_attestation_bundle(*,bundle:bytes,trusted_root:bytes,capture_files:Mapping[str,bytes],governance:Mapping[str,Any],deployment:Mapping[str,Any],verifier:Path,launcher:Path)->Mapping[str,Any]:
 """The design-only V2.3.6 pseudo CLI is forbidden after V2.3.7."""
 raise RuntimeError("V2.3.7 real Cosign contained verifier required")

def qualification_identity(v:Mapping[str,Any])->str:return identity(v,"qualification_identity")
def validate_qualification(v:Mapping[str,Any])->None:
 required={"schema","verdict","implementation_sha256","test_sha256","governance_identity","audit_findings","invariants","zero_activity","remaining_blockers","qualification_identity"}
 if set(v)!=required or v["schema"]!="SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_V2_3_6_ZERO_NETWORK_QUALIFICATION" or v["verdict"]!="PASS_REMEDIATED_PUBLIC_ATTESTATION_DESIGN_ZERO_NETWORK_DEPLOYMENT_PENDING":raise ValueError("qualification schema/verdict")
 root=Path(__file__).resolve().parents[2];test=root/"tests"/"test_semantic_authority_public_attestation_v2_3_6.py";gp=root/"docs"/"artifacts"/"semantic-contract-v2-3-6-public-attestation-governance.json"
 policy=json.loads(gp.read_text(encoding="utf-8"));validate_governance(policy)
 if v["implementation_sha256"]!=sha(Path(__file__).read_bytes()) or v["test_sha256"]!=sha(test.read_bytes()) or v["governance_identity"]!=policy["governance_identity"]:raise ValueError("qualification identity chain")
 findings=["DISTINCT_FIRST_ATTEMPT_RUN_SUBSTITUTION","CANCEL_BEFORE_ATTESTATION_REDRAW","NULL_DEPLOYMENT_PINS_NOT_REPRESENTABLE","VERIFIER_SUMMARY_NOT_BOUND_TO_BUNDLE_BYTES","CAPTURE_ARTIFACT_SET_NOT_CLOSED","SUBJECT_DIGEST_NOT_RECOMPUTED","REPOSITORY_VARIABLE_SECRET_ENVIRONMENT_INJECTION","DEPENDENCY_AND_CONTAINER_IDENTITY_GAP","OIDC_CERTIFICATE_REPOSITORY_WORKFLOW_RUN_CLAIMS_INCOMPLETE","REKOR_CHECKPOINT_LOG_ORIGIN_AND_INITIATION_ORDER_UNBOUND","CALLER_ASSERTED_CRYPTOGRAPHIC_VERIFICATION","INITIATION_DIGEST_WITHOUT_CLAIM_BINDING","OFFLINE_FLAG_WITHOUT_TRANSPORT_ISOLATION","DEPLOYMENT_COMMIT_AUTOMATICALLY_TRIGGERED_FORBIDDEN_ACQUISITION","OWNER_TIMED_EXECUTION_MARKER_CAN_SELECT_OBSERVATION_TIME","LEGACY_PSEUDO_VERIFIER_ENTRY_POINT_REMAINED_REACHABLE"]
 invariants={"SEPARATE_IMMUTABLE_DEPLOYMENT_MANIFEST":"PASS","TRANSPARENCY_FIRST_RUN_COMMITMENT":"PASS","CANCEL_FAILURE_OR_RERUN_AFTER_COMMITMENT_TERMINAL":"PASS","BUNDLE_AND_CAPTURE_BYTES_RECOMPUTED":"PASS","PINNED_OFFLINE_VERIFIER_EXECUTED":"SUPERSEDED_BY_V2_3_7_REAL_COSIGN","LEGACY_PSEUDO_VERIFIER_UNREACHABLE":"PASS","OIDC_FULCIO_REKOR_IDENTITY_CLOSURE":"PASS","REPOSITORY_INPUT_AND_DEPENDENCY_CLOSURE":"PASS","REAL_ACQUISITION":"FAIL_CLOSED_PENDING_DEPLOYMENT"}
 zero={"registry_metadata":0,"snapshot_content":0,"frame_execution":0,"source_selection":0,"authority_bases":0,"pilot15":0,"blind_access":0}
 if v["audit_findings"]!=findings or v["invariants"]!=invariants or v["zero_activity"]!=zero or v["remaining_blockers"]!=list(REMAINING_BLOCKERS) or v["qualification_identity"]!=qualification_identity(v):raise ValueError("qualification closure")
