import copy, shutil, subprocess
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_14 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical

def fixture(tmp_path,monkeypatch):
 monkeypatch.setattr(m,"OPENSSL_EXECUTABLE_SHA256",m.sha(b"openssl"));monkeypatch.setattr(m,"COSIGN_SHA256",m.sha(b"cosign"));monkeypatch.setattr(m,"LINUX_LAUNCHER_SHA256",m.sha(b"deny-network-launcher.sh"))
 monkeypatch.setattr(m,"CA_BUNDLE_SHA256",m.sha(b"ca.pem"));monkeypatch.setattr(m,"TRUSTED_ROOT_SHA256",m.sha(b"trusted-root.json"))
 v={"schema":m.SCHEMA,"repository_slug":m.REPOSITORY_SLUG,"repository_id":m.REPOSITORY_ID,"default_branch_ref":m.DEFAULT_BRANCH_REF,"core_runtime_commit":m.RUNTIME_COMMIT,"deployment_runtime_commit":m.DEPLOYMENT_RUNTIME_COMMIT,"workflow_freeze_commit":"a"*40,"workflow_freeze_epoch":1,"workflow_template_sha256":"1"*64,"scheduled_utc":"2026-10-01T00:00:00Z","schedule_cron":"0 0 1 10 *","rfc3161_verifier_sha256":m.OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":"2"*64,"ca_sha256":"3"*64,"cosign_sha256":m.COSIGN_SHA256,"launcher_sha256":m.LINUX_LAUNCHER_SHA256,"trusted_root_sha256":"4"*64,"derivation_policy_identity":m.DERIVATION_POLICY_IDENTITY,"seed_plan_identity":m.SEED_PLAN_IDENTITY}
 payload=m.schedule_payload(v);values={name:(payload if name=="schedule-precommit.json" else (b"ca.pem" if name=="rfc3161-root.pem" else name.encode())) for name in m.OBJECTS};objects={}
 for name,data in values.items():
  path=tmp_path/"deployment"/"objects"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);objects[name]={"sha256":m.sha(data),"length":len(data),"path":f"deployment/objects/{name}"}
 v.update({"schedule_payload_sha256":m.sha(payload),"objects":objects});v.update({"rfc3161_root_sha256":objects["rfc3161-root.pem"]["sha256"],"ca_sha256":objects["ca.pem"]["sha256"],"trusted_root_sha256":objects["trusted-root.json"]["sha256"]})
 payload=m.schedule_payload(v);(tmp_path/"deployment/objects/schedule-precommit.json").write_bytes(payload);objects["schedule-precommit.json"].update(sha256=m.sha(payload),length=len(payload));v["schedule_payload_sha256"]=m.sha(payload)
 body=dict(v);v["deployment_identity"]=m.sha(canonical(body));v["manifest_identity"]=m.sha(canonical(v));return v

def test_manifest_materialization_and_tamper(tmp_path,monkeypatch):
 v=fixture(tmp_path,monkeypatch);m.validate_manifest(v);assert set(m.materialize(v,tmp_path))==m.OBJECTS
 (tmp_path/"deployment/objects/cosign").write_bytes(b"tamper")
 with pytest.raises(ValueError,match="bytes"):m.materialize(v,tmp_path)

@pytest.mark.parametrize("key",["workflow_freeze_commit","schedule_cron","rfc3161_verifier_sha256","schedule_payload_sha256","deployment_identity","manifest_identity"])
def test_identity_mutations_fail(tmp_path,monkeypatch,key):
 v=fixture(tmp_path,monkeypatch);v[key]="0"*(40 if key.endswith("commit") else 64)
 with pytest.raises((ValueError,TypeError)):m.validate_manifest(v)

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
 replies=iter([type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Wed Sep 30 23:59:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(replies));m.verify_timestamp(v,o,freeze_epoch=1)
 late=iter([type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Thu Oct 1 00:00:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(late))
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
 v=fixture(tmp_path,monkeypatch);v["workflow_freeze_commit"]=freeze;v["workflow_freeze_epoch"]=int(call("show","-s","--format=%ct",freeze));v["workflow_template_sha256"]=m.sha(template);payload=m.schedule_payload(v);schedule=tmp_path/"deployment/objects/schedule-precommit.json";schedule.write_bytes(payload);v["schedule_payload_sha256"]=m.sha(payload);v["objects"]["schedule-precommit.json"].update(sha256=m.sha(payload),length=len(payload));body={k:x for k,x in v.items() if k not in {"deployment_identity","manifest_identity"}};v["deployment_identity"]=m.sha(canonical(body));complete={**v};complete.pop("manifest_identity",None);v["manifest_identity"]=m.sha(canonical(complete))
 active=tmp_path/m.WORKFLOW_PATH;active.parent.mkdir(parents=True);active.write_bytes(m.render_workflow(template,v));call("add",m.WORKFLOW_PATH);call("commit","-m","deploy");head=call("rev-parse","HEAD")
 m.verify_worktree(tmp_path,v)
 assert m.verify_git(tmp_path,v,head,git_executable=git,isolated=False,deployment_ancestor=freeze)>0
 with pytest.raises(ValueError,match="executing HEAD mismatch"):m.verify_git(tmp_path,v,freeze,git_executable=git,isolated=False,deployment_ancestor=freeze)
 skew=copy.deepcopy(v);skew["workflow_freeze_epoch"]+=1
 with pytest.raises(ValueError,match="workflow freeze time"):m.verify_git(tmp_path,skew,head,git_executable=git,isolated=False,deployment_ancestor=freeze)
 active.write_bytes(b"tampered");call("add",m.WORKFLOW_PATH);call("commit","-m","tamper")
 with pytest.raises(ValueError,match="workflow worktree evidence"):m.verify_worktree(tmp_path,v)
 with pytest.raises(ValueError,match="workflow evidence"):m.verify_git(tmp_path,v,call("rev-parse","HEAD"),git_executable=git,isolated=False,deployment_ancestor=freeze)

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
 assert value["readiness_authority"]=="PARTIALLY_PROVEN" and len(value["external_evidence_pending"])==4
