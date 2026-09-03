import copy
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_14 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical

def fixture(tmp_path,monkeypatch):
 monkeypatch.setattr(m,"OPENSSL_EXECUTABLE_SHA256",m.sha(b"openssl"));monkeypatch.setattr(m,"COSIGN_SHA256",m.sha(b"cosign"));monkeypatch.setattr(m,"LINUX_LAUNCHER_SHA256",m.sha(b"deny-network-launcher.sh"))
 v={"schema":m.SCHEMA,"repository_slug":m.REPOSITORY_SLUG,"repository_id":m.REPOSITORY_ID,"core_runtime_commit":m.RUNTIME_COMMIT,"deployment_runtime_commit":m.DEPLOYMENT_RUNTIME_COMMIT,"workflow_freeze_commit":"a"*40,"workflow_template_sha256":"1"*64,"scheduled_utc":"2026-10-01T00:00:00Z","schedule_cron":"0 0 1 10 *","rfc3161_verifier_sha256":m.OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":"2"*64,"ca_sha256":"3"*64,"cosign_sha256":m.COSIGN_SHA256,"launcher_sha256":m.LINUX_LAUNCHER_SHA256,"trusted_root_sha256":"4"*64,"derivation_policy_identity":m.DERIVATION_POLICY_IDENTITY,"seed_plan_identity":m.SEED_PLAN_IDENTITY}
 payload=m.schedule_payload(v);values={name:(payload if name=="schedule-precommit.json" else name.encode()) for name in m.OBJECTS};objects={}
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

def test_render_and_template_are_inert_and_executable(tmp_path,monkeypatch):
 template=(Path(__file__).parents[1]/m.TEMPLATE_PATH).read_bytes();v=fixture(tmp_path,monkeypatch);v["workflow_template_sha256"]=m.sha(template)
 rendered=m.render_workflow(template,v);text=rendered.decode();assert not m.re.search(r"@[A-Z0-9_]+@",text)
 assert "workflow_dispatch" not in text and "semantic_authority_deployment_v2_3_14" in text
 assert m.WORKFLOW_PATH.endswith("semantic-authority-metadata-capture-v2-3-9.yml") and m.DEPLOYMENT_RUNTIME_COMMIT=="26f66c54c02e18c05927b91d010290c2f712ca06"
 assert text.index("--prepare-initiation")<text.index("actions/attest@")<text.index("--execute")

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
