import hashlib,json
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_11 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical
def manifest():
 v={"schema":m.SCHEMA,"repository_slug":m.REPOSITORY_SLUG,"repository_id":m.REPOSITORY_ID,"core_runtime_commit":m.RUNTIME_COMMIT,"deployment_runtime_commit":"a"*40,"workflow_commit":"b"*40,"scheduled_utc":"2026-10-01T00:00:00Z","schedule_cron":"0 0 1 10 *","ca_sha256":"d"*64,"cosign_sha256":"e"*64,"launcher_sha256":"f"*64,"trusted_root_sha256":"1"*64,"derivation_policy_identity":"2"*64,"seed_plan_identity":"3"*64};v["deployment_identity"]=hashlib.sha256(canonical(v)).hexdigest();v["manifest_identity"]=hashlib.sha256(canonical(v)).hexdigest();return v
def test_manifest_identity_runtime_workflow_and_schedule_closed():
 m.validate_manifest(manifest())
 for key,value in (("deployment_runtime_commit","b"*40),("core_runtime_commit","9"*40),("schedule_cron","1 0 1 10 *"),("repository_id","9")):
  bad={**manifest(),key:value}
  with pytest.raises(ValueError):m.validate_manifest(bad)
def test_cli_is_real_and_requires_complete_paths(monkeypatch,tmp_path):
 p=tmp_path/"manifest.json";p.write_text(json.dumps(manifest()),encoding="utf-8");seen={};monkeypatch.setattr(m,"checkout_commit",lambda root:"a"*40);monkeypatch.setattr(m,"execute",lambda value,**kw:seen.update(value=value,kw=kw) or {})
 assert m.main(["--manifest",str(p),"--bundle","b","--cosign","c","--launcher","l","--trusted-root","r","--ca","a","--output","o"])==0 and seen["value"]["schema"]==m.SCHEMA
 assert seen["kw"]["checkout_sha"]=="a"*40
def test_checkout_evidence_and_deployment_identity_are_not_self_asserted(monkeypatch,tmp_path):
 monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:type("R",(),{"returncode":0,"stdout":b"a"*40+b"\n"})())
 assert m.checkout_commit(tmp_path)=="a"*40
 bad=manifest();bad["deployment_identity"]="0"*64;bad["manifest_identity"]=hashlib.sha256(canonical({k:v for k,v in bad.items() if k!="manifest_identity"})).hexdigest()
 with pytest.raises(ValueError,match="deployment identity"):m.validate_manifest(bad)
def test_template_has_frozen_runtime_without_workflow_self_reference():
 root=Path(__file__).resolve().parents[1];text=(root/"deployment/semantic-authority-metadata-capture-v2-3-11.yml.template").read_text()
 assert "ref: '@DEPLOYMENT_RUNTIME_COMMIT@'" in text and "ref: '@WORKFLOW_COMMIT@'" not in text and "--manifest" in text and "workflow_dispatch" not in text
 assert "PYTHONPATH: ${{ github.workspace }}/src" in text
def test_qualification_identity_chain():
 root=Path(__file__).resolve().parents[1];q=json.loads((root/"docs/artifacts/semantic-contract-v2-3-11-runtime-cli-zero-network-qualification.json").read_text());identity=q.pop("qualification_identity")
 assert identity==hashlib.sha256(json.dumps(q,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
 assert q["module_sha256"]==hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
