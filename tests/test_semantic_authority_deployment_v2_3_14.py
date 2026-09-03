import copy, shutil, subprocess
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_14 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical

def fixture(tmp_path,monkeypatch):
 monkeypatch.setattr(m,"OPENSSL_EXECUTABLE_SHA256",m.sha(b"openssl"));monkeypatch.setattr(m,"COSIGN_SHA256",m.sha(b"cosign"));monkeypatch.setattr(m,"LINUX_LAUNCHER_SHA256",m.sha(b"deny-network-launcher.sh"))
 monkeypatch.setattr(m,"CA_BUNDLE_SHA256",m.sha(b"ca.pem"));monkeypatch.setattr(m,"RFC3161_ROOT_SHA256",m.sha(b"rfc3161-root.pem"));monkeypatch.setattr(m,"RFC3161_INTERMEDIATE_SHA256",m.sha(b"rfc3161-intermediate.pem"));monkeypatch.setattr(m,"TRUSTED_ROOT_SHA256",m.sha(b"trusted-root.json"))
 epoch=1788430198;scheduled,cron=m.derive_schedule(m.SCHEDULE_ANCHOR_EPOCH)
 v={"schema":m.SCHEMA,"repository_slug":m.REPOSITORY_SLUG,"repository_id":m.REPOSITORY_ID,"default_branch_ref":m.DEFAULT_BRANCH_REF,"core_runtime_commit":m.RUNTIME_COMMIT,"deployment_runtime_commit":m.DEPLOYMENT_RUNTIME_COMMIT,"workflow_freeze_commit":"a"*40,"workflow_freeze_epoch":epoch,"workflow_template_sha256":"1"*64,"schedule_selection_rule":m.SCHEDULE_SELECTION_RULE,"schedule_anchor_commit":m.SCHEDULE_ANCHOR_COMMIT,"schedule_anchor_epoch":m.SCHEDULE_ANCHOR_EPOCH,"scheduled_utc":scheduled,"schedule_cron":cron,"rfc3161_tsa_endpoint":m.RFC3161_TSA_ENDPOINT,"rfc3161_tsa_method":m.RFC3161_TSA_METHOD,"rfc3161_query_content_type":m.RFC3161_QUERY_CONTENT_TYPE,"rfc3161_reply_content_type":m.RFC3161_REPLY_CONTENT_TYPE,"rfc3161_tsa_redirects":m.RFC3161_TSA_REDIRECTS,"rfc3161_tsa_attempts":m.RFC3161_TSA_ATTEMPTS,"rfc3161_tsa_nonce":m.RFC3161_TSA_NONCE,"rfc3161_tsa_cert_req":m.RFC3161_TSA_CERT_REQ,"rfc3161_verifier_sha256":m.OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":m.RFC3161_ROOT_SHA256,"rfc3161_intermediate_sha256":m.RFC3161_INTERMEDIATE_SHA256,"ca_sha256":"3"*64,"cosign_sha256":m.COSIGN_SHA256,"launcher_sha256":m.LINUX_LAUNCHER_SHA256,"trusted_root_sha256":"4"*64,"derivation_policy_identity":m.DERIVATION_POLICY_IDENTITY,"seed_plan_identity":m.SEED_PLAN_IDENTITY}
 payload=m.schedule_payload(v);values={name:(payload if name=="schedule-precommit.json" else name.encode()) for name in m.OBJECTS};objects={}
 for name,data in values.items():
  path=tmp_path/"deployment"/"objects"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);objects[name]={"sha256":m.sha(data),"length":len(data),"path":f"deployment/objects/{name}"}
 v.update({"schedule_payload_sha256":m.sha(payload),"objects":objects});v.update({"rfc3161_root_sha256":objects["rfc3161-root.pem"]["sha256"],"rfc3161_intermediate_sha256":objects["rfc3161-intermediate.pem"]["sha256"],"rfc3161_request_sha256":objects["rfc3161-request.tsq"]["sha256"],"ca_sha256":objects["ca.pem"]["sha256"],"trusted_root_sha256":objects["trusted-root.json"]["sha256"]})
 payload=m.schedule_payload(v);(tmp_path/"deployment/objects/schedule-precommit.json").write_bytes(payload);objects["schedule-precommit.json"].update(sha256=m.sha(payload),length=len(payload));v["schedule_payload_sha256"]=m.sha(payload)
 body=dict(v);v["deployment_identity"]=m.sha(canonical(body));v["manifest_identity"]=m.sha(canonical(v));return v

def test_manifest_materialization_and_tamper(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);m.validate_manifest(v);assert set(m.materialize(v,tmp_path))==m.OBJECTS
 (tmp_path/"deployment/objects/cosign").write_bytes(b"tamper")
 with pytest.raises(ValueError,match="bytes"):m.materialize(v,tmp_path)

@pytest.mark.parametrize("key",["workflow_freeze_commit","schedule_selection_rule","schedule_anchor_commit","schedule_anchor_epoch","schedule_cron","rfc3161_tsa_endpoint","rfc3161_tsa_method","rfc3161_query_content_type","rfc3161_reply_content_type","rfc3161_tsa_redirects","rfc3161_tsa_attempts","rfc3161_tsa_nonce","rfc3161_tsa_cert_req","rfc3161_root_sha256","rfc3161_intermediate_sha256","rfc3161_verifier_sha256","schedule_payload_sha256","deployment_identity","manifest_identity"])
def test_identity_mutations_fail(tmp_path,monkeypatch,key):
 v=fixture(tmp_path,monkeypatch);v[key]="0"*(40 if key.endswith("commit") else 64)
 with pytest.raises((ValueError,TypeError)):m.validate_manifest(v)

def test_schedule_is_commit_time_derived_and_not_caller_selectable(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);scheduled,cron=m.derive_schedule(m.SCHEDULE_ANCHOR_EPOCH)
 assert (scheduled,cron)==(v["scheduled_utc"],v["schedule_cron"])
 assert scheduled=="2026-10-04T00:00:00Z" and cron=="0 0 4 10 *"
 bad=copy.deepcopy(v);bad["scheduled_utc"]="2026-10-05T00:00:00Z";bad["schedule_cron"]="0 0 5 10 *"
 with pytest.raises(ValueError,match="deterministic schedule selection"):m.validate_manifest(bad)
 with pytest.raises(TypeError):m.verify_git(tmp_path,v,"a"*40,schedule_anchor="b"*40,schedule_anchor_epoch=1)

def test_rfc3161_transport_profile_is_enforced_without_network(monkeypatch,tmp_path):
 calls=[]
 class Headers:
  def get_content_type(self):return m.RFC3161_REPLY_CONTENT_TYPE
 class Response:
  status=200;headers=Headers()
  def geturl(self):return m.RFC3161_TSA_ENDPOINT
  def read(self,n):calls.append(("read",n));return b"receipt"
  def __enter__(self):return self
  def __exit__(self,*args):return False
 class Opener:
  def open(self,request,timeout):calls.append((request,timeout));return Response()
 monkeypatch.setattr(m.urllib.request,"build_opener",lambda *handlers:(calls.append(handlers),Opener())[1])
 monkeypatch.setattr(m,"verify_rfc3161_query",lambda v,o:m._bound_rfc3161_query(v,o))
 query=tmp_path/"query.tsq";query.write_bytes(b"query")
 binding={"rfc3161_request_sha256":m.sha(b"query")}
 assert m.submit_rfc3161_query(binding, {"rfc3161-request.tsq":query})==b"receipt"
 handlers=calls[0];request,timeout=calls[1]
 assert any(isinstance(x,m.urllib.request.ProxyHandler) and x.proxies=={} for x in handlers)
 assert any(isinstance(x,m._RejectRedirect) for x in handlers)
 assert request.full_url==m.RFC3161_TSA_ENDPOINT and request.method=="POST" and request.data==b"query" and timeout==20
 assert request.get_header("Content-type")==m.RFC3161_QUERY_CONTENT_TYPE and request.get_header("Accept")==m.RFC3161_REPLY_CONTENT_TYPE
 query.write_bytes(b"")
 with pytest.raises(ValueError,match="query"):m.submit_rfc3161_query(binding, {"rfc3161-request.tsq":query})

def test_rfc3161_query_substitution_after_semantic_validation_uses_bound_bytes(monkeypatch,tmp_path):
 query=tmp_path/"query.tsq";query.write_bytes(b"bound-query")
 v={"rfc3161_request_sha256":m.sha(b"bound-query")};o={"rfc3161-request.tsq":query}
 sent=[]
 class Headers:
  def get_content_type(self):return m.RFC3161_REPLY_CONTENT_TYPE
 class Response:
  status=200;headers=Headers()
  def geturl(self):return m.RFC3161_TSA_ENDPOINT
  def read(self,n):return b"receipt"
  def __enter__(self):return self
  def __exit__(self,*args):return False
 class Opener:
  def open(self,request,timeout):sent.append(request.data);return Response()
 def substitute(*args):query.write_bytes(b"substituted-query");return b"bound-query"
 monkeypatch.setattr(m,"verify_rfc3161_query",substitute)
 monkeypatch.setattr(m.urllib.request,"build_opener",lambda *handlers:Opener())
 assert m.submit_rfc3161_query(v,o)==b"receipt" and sent==[b"bound-query"]

def query_text(v):
 digest=m.sha(m.schedule_payload(v));pairs=" ".join(digest[i:i+2] for i in range(0,len(digest),2))
 return f"Hash Algorithm: sha256\nMessage data:\n  0000 - {pairs[:47]}\n  0010 - {pairs[48:95]}\nPolicy OID: unspecified\nNonce: 0x01\nCertificate required: yes\nExtensions:\n".encode()

def test_rfc3161_query_requires_payload_imprint_nonce_and_certreq(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);o=m.materialize(v,tmp_path);monkeypatch.setattr(m,"verify_executable",lambda p:None);monkeypatch.setattr(m,"verify_installed_dependency",lambda *a:None)
 good=query_text(v)
 monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:type("R",(),{"returncode":0,"stdout":good,"stderr":b""})())
 m.verify_rfc3161_query(v,o)
 for bad in (good.replace(b"sha256",b"sha384"),good.replace(b"Nonce: 0x01\n",b""),good.replace(b"required: yes",b"required: no"),good.replace(b"0000 - ",b"0000 - ff ",1)):
  monkeypatch.setattr(m.subprocess,"run",lambda *a,_bad=bad,**k:type("R",(),{"returncode":0,"stdout":_bad,"stderr":b""})())
  with pytest.raises(ValueError):m.verify_rfc3161_query(v,o)

def test_alias_extra_separator_and_symlink_fail(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);bad=copy.deepcopy(v);bad["objects"]["cosign"]["path"]="deployment/objects/../cosign"
 with pytest.raises(ValueError):m.validate_manifest(bad)
 bad=copy.deepcopy(v);bad["objects"]["cosign"]["path"]="deployment\\objects\\cosign"
 with pytest.raises(ValueError):m.validate_manifest(bad)
 bad=copy.deepcopy(v);bad["objects"]["extra"]={"sha256":"0"*64,"length":1,"path":"deployment/objects/extra"}
 with pytest.raises(ValueError):m.validate_manifest(bad)
 link=tmp_path/"deployment/objects/cosign";original=m.Path.is_symlink
 monkeypatch.setattr(m.Path,"is_symlink",lambda self:self==link or original(self))
 with pytest.raises(ValueError,match="object containment"):m.materialize(v,tmp_path)
 monkeypatch.setattr(m.Path,"is_symlink",original)

def test_render_and_template_are_inert_and_executable(tmp_path,monkeypatch):
 template=(Path(__file__).parents[1]/m.TEMPLATE_PATH).read_bytes();v=fixture(tmp_path,monkeypatch);v["workflow_template_sha256"]=m.sha(template)
 rendered=m.render_workflow(template,v);text=rendered.decode();assert not m.re.search(r"@[A-Z0-9_]+@",text)
 assert "workflow_dispatch" not in text and "semantic_authority_deployment_v2_3_14" in text
 assert m.WORKFLOW_PATH.endswith("semantic-authority-metadata-capture-v2-3-9.yml") and m.DEPLOYMENT_RUNTIME_COMMIT=="26f66c54c02e18c05927b91d010290c2f712ca06"
 assert text.index("--prepare-initiation")<text.index("actions/attest@")<text.index("--execute")
 assert text.index("--execute")<text.index("Create final public capture attestation")<text.index("upload-artifact@")
 assert "sha256sum -c -" in text and "@UPLOAD_ACTION_COMMIT@" not in text
 assert text.count("python -I -S -c") == 2 and "python -m pastila_scout" not in text

def test_timestamp_is_cryptographic_and_precedes_schedule(monkeypatch,tmp_path):
 v=fixture(tmp_path,monkeypatch);o=m.materialize(v,tmp_path);monkeypatch.setattr(m,"verify_executable",lambda p:None);monkeypatch.setattr(m,"verify_installed_dependency",lambda *a:None)
 calls=[];replies=iter([type("R",(),{"returncode":0,"stdout":query_text(v),"stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Wed Sep 30 23:59:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda args,**k:(calls.append((args,k)),next(replies))[1]);m.verify_timestamp(v,o,freeze_epoch=1)
 assert "-queryfile" in calls[1][0] and "/dev/stdin" in calls[1][0] and "-data" not in calls[1][0]
 assert calls[0][1]["input"]==calls[1][1]["input"]==(tmp_path/"deployment/objects/rfc3161-request.tsq").read_bytes()
 late=iter([type("R",(),{"returncode":0,"stdout":query_text(v),"stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Sun Oct 4 00:00:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(late))
 with pytest.raises(ValueError,match="phase order"):m.verify_timestamp(v,o,freeze_epoch=1)

def test_initiation_is_one_shot_guarded_and_has_exact_subject_bytes(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);monkeypatch.setattr(m,"one_shot_guard",lambda *a:None);monkeypatch.setattr(m,"initiation_claim",lambda run:{"closed":True})
 monkeypatch.setenv("GITHUB_RUN_ID","7");dest=tmp_path/"initiation";m.prepare_initiation(v,"b"*40,dest)
 expected=canonical({"closed":True});assert (dest/"pastila-capture-initiation.json").read_bytes()==expected
 assert (dest/"predicate.json").read_bytes()==expected and not expected.endswith(b"\n")

def test_nonselectable_roots_and_default_branch(monkeypatch,tmp_path):
 v=fixture(tmp_path,monkeypatch)
 for key in ("rfc3161_root_sha256","ca_sha256","trusted_root_sha256"):
  bad=copy.deepcopy(v);bad[key]="0"*64
  with pytest.raises(ValueError):m.validate_manifest(bad)
 monkeypatch.setenv("GITHUB_SHA","b"*40);monkeypatch.setenv("GITHUB_EVENT_NAME","schedule");monkeypatch.setenv("GITHUB_REF",m.DEFAULT_BRANCH_REF);assert m.runtime_head()=="b"*40
 monkeypatch.setenv("GITHUB_REF","refs/heads/owner-choice")
 with pytest.raises(ValueError,match="default-branch"):m.runtime_head()

def test_real_git_ancestry_blob_and_rendering(tmp_path,monkeypatch):
 git=shutil.which("git");assert git
 def call(*args):return subprocess.check_output([git,"-C",str(tmp_path),*args]).decode().strip()
 subprocess.check_call([git,"init",str(tmp_path)]);call("config","user.email","zero@example.invalid");call("config","user.name","zero")
 template=(Path(__file__).parents[1]/m.TEMPLATE_PATH).read_bytes();path=tmp_path/m.TEMPLATE_PATH;path.parent.mkdir(parents=True);path.write_bytes(template);call("add",m.TEMPLATE_PATH);call("commit","-m","freeze");freeze=call("rev-parse","HEAD")
 monkeypatch.setattr(m,"SCHEDULE_ANCHOR_COMMIT",freeze);monkeypatch.setattr(m,"SCHEDULE_ANCHOR_EPOCH",int(call("show","-s","--format=%ct",freeze)))
 v=fixture(tmp_path,monkeypatch);v["workflow_freeze_commit"]=freeze;v["workflow_freeze_epoch"]=int(call("show","-s","--format=%ct",freeze));v["scheduled_utc"],v["schedule_cron"]=m.derive_schedule(m.SCHEDULE_ANCHOR_EPOCH);v["workflow_template_sha256"]=m.sha(template);payload=m.schedule_payload(v);schedule=tmp_path/"deployment/objects/schedule-precommit.json";schedule.write_bytes(payload);v["schedule_payload_sha256"]=m.sha(payload);v["objects"]["schedule-precommit.json"].update(sha256=m.sha(payload),length=len(payload));body={k:x for k,x in v.items() if k not in {"deployment_identity","manifest_identity"}};v["deployment_identity"]=m.sha(canonical(body));complete={**v};complete.pop("manifest_identity",None);v["manifest_identity"]=m.sha(canonical(complete))
 active=tmp_path/m.WORKFLOW_PATH;active.parent.mkdir(parents=True);active.write_bytes(m.render_workflow(template,v));call("add",m.WORKFLOW_PATH);call("commit","-m","deploy");head=call("rev-parse","HEAD")
 m.verify_worktree(tmp_path,v)
 git_args={"git_executable":git,"isolated":False,"deployment_ancestor":freeze}
 assert m.verify_git(tmp_path,v,head,**git_args)>0
 with pytest.raises(ValueError,match="executing HEAD mismatch"):m.verify_git(tmp_path,v,freeze,**git_args)
 skew=copy.deepcopy(v);skew["workflow_freeze_epoch"]+=1
 with pytest.raises(ValueError,match="workflow freeze time"):m.verify_git(tmp_path,skew,head,**git_args)
 active.write_bytes(b"tampered");call("add",m.WORKFLOW_PATH);call("commit","-m","tamper")
 with pytest.raises(ValueError,match="workflow worktree evidence"):m.verify_worktree(tmp_path,v)
 with pytest.raises(ValueError,match="workflow evidence"):m.verify_git(tmp_path,v,call("rev-parse","HEAD"),**git_args)

def test_production_main_enforces_git_and_rejects_bundle_alias(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);manifest=tmp_path/"manifest.json";manifest.write_text(m.json.dumps(v),encoding="utf-8")
 monkeypatch.chdir(tmp_path);monkeypatch.setattr(m,"runtime_head",lambda:"b"*40)
 called=[]
 monkeypatch.setattr(m,"verify_git",lambda root,value,head:called.append((root,value,head)))
 monkeypatch.setattr(m,"verify_worktree",lambda *a:None);monkeypatch.setattr(m,"materialize",lambda *a:{})
 monkeypatch.setattr(m,"verify_timestamp",lambda *a,**k:None)
 destination=tmp_path/"initiation";monkeypatch.setattr(m,"prepare_initiation",lambda *a:None)
 assert m.main(["--manifest",str(manifest),"--prepare-initiation",str(destination)])==0
 assert called and called[0][2]=="b"*40
 outside=tmp_path.parent/"outside-bundle.json";outside.write_bytes(b"{}")
 with pytest.raises(ValueError,match="input containment"):m.regular_input(outside,tmp_path)
 inside=tmp_path/"bundle.json";inside.write_bytes(b"{}")
 alias=tmp_path/"bundle-alias.json";alias.write_bytes(b"{}")
 original=m.Path.is_symlink;monkeypatch.setattr(m.Path,"is_symlink",lambda self:self==alias or original(self))
 with pytest.raises(ValueError,match="input containment"):m.regular_input(alias,tmp_path)
 monkeypatch.setattr(m.Path,"is_symlink",original)
 assert m.regular_input(inside,tmp_path)==inside.resolve()
 parent=tmp_path/"nested";parent.mkdir();nested=parent/"bundle.json";nested.write_bytes(b"{}")
 monkeypatch.setattr(m.Path,"is_symlink",lambda self:self==parent or original(self))
 with pytest.raises(ValueError,match="input containment"):m.regular_input(nested,tmp_path)

def test_production_main_fails_before_materialization_when_git_evidence_fails(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);manifest=tmp_path/"manifest.json";manifest.write_text(m.json.dumps(v),encoding="utf-8")
 monkeypatch.chdir(tmp_path);monkeypatch.setattr(m,"runtime_head",lambda:"b"*40)
 monkeypatch.setattr(m,"verify_git",lambda *a,**k:(_ for _ in ()).throw(ValueError("git evidence")))
 reached=[];monkeypatch.setattr(m,"materialize",lambda *a:reached.append(True))
 with pytest.raises(ValueError,match="git evidence"):m.main(["--manifest",str(manifest),"--prepare-initiation",str(tmp_path/"i")])
 assert reached==[]

def test_milestone9_audit_qualification_identity_chain():
 root=Path(__file__).parents[1];record_path=root/"docs/artifacts/semantic-contract-v2-3-14-three-phase-deployment-zero-network-qualification.json"
 value=m.json.loads(record_path.read_text("utf-8"));identity=value.pop("qualification_identity")
 assert identity==m.sha(canonical(value))
 assert value["implementation_sha256"]==m.sha((root/"src/pastila_scout/semantic_authority_deployment_v2_3_14.py").read_bytes())
 assert value["test_sha256"]==m.sha(Path(__file__).read_bytes())
 assert value["workflow_template_sha256"]==m.sha((root/m.TEMPLATE_PATH).read_bytes())
 assert value["readiness_authority"]=="PARTIALLY_PROVEN" and len(value["external_evidence_pending"])==3
 assert "DURABLE_PUBLICATION_RECEIPT" not in value["external_evidence_pending"]

def test_durable_publication_receipt_identity_and_target_binding():
 root=Path(__file__).parents[1];path=root/"docs/artifacts/semantic-contract-v2-3-14-durable-publication-receipt.json"
 value=m.json.loads(path.read_text("utf-8"));identity=value.pop("receipt_identity")
 assert identity==m.sha(canonical(value))
 target="9487348116128059fbc8319e4f581a1365c9f9ce"
 assert value["commit_sha"]==target and value["published_ref"]==m.DEFAULT_BRANCH_REF
 assert value["tree_sha"]=="dc8429bc3f422b3b90d58fd0dfeee716e324d56b"
 assert value["parent_sha"]=="5a45f1901773d9ca0d3fc93859125bb433686e2f"
 assert set(value["evidence"])=={"git_ls_remote_sha","github_commit_api_sha","github_branch_api_sha"}
 assert set(value["evidence"].values())=={target}
 assert value["publication_review_verdict"]=="PASS_PUBLIC_COMMIT_AND_BRANCH_IDENTITY_CONFIRMED"
 assert value["observed_utc_authority"]=="LOCAL_CLOCK_NOT_RFC3161"
