import hashlib, json
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_12 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical

def manifest():
    v={"schema":m.SCHEMA,"repository_slug":m.REPOSITORY_SLUG,"repository_id":m.REPOSITORY_ID,"core_runtime_commit":m.RUNTIME_COMMIT,"deployment_runtime_commit":"a"*40,"workflow_commit":"b"*40,"scheduled_utc":"2026-10-01T00:00:00Z","schedule_cron":"0 0 1 10 *","ca_sha256":m.CA_BUNDLE_SHA256,"cosign_sha256":"2"*64,"launcher_sha256":"3"*64,"trusted_root_sha256":"4"*64,"derivation_policy_identity":"5"*64,"seed_plan_identity":"6"*64,"schedule_precommit_receipt_sha256":"7"*64,"schedule_precommit_verifier_sha256":m.OPENSSL_SHA256,"schedule_precommit_tsa_root_sha256":m.CA_BUNDLE_SHA256,"rfc3161_qualification_identity":m.V2_3_3_QUALIFICATION_IDENTITY}
    v["schedule_precommit_payload_sha256"]=m.sha(m.schedule_payload(v));v["deployment_identity"]=m.sha(canonical(v));v["manifest_identity"]=m.sha(canonical(v));return v

def test_manifest_closes_three_phase_identity_chain():
    m.validate_manifest(manifest())
    bad={**manifest(),"schedule_precommit_payload_sha256":"0"*64};bad["deployment_identity"]=m.sha(canonical({k:v for k,v in bad.items() if k not in {"deployment_identity","manifest_identity"}}));bad["manifest_identity"]=m.sha(canonical({k:v for k,v in bad.items() if k!="manifest_identity"}))
    with pytest.raises(ValueError):m.validate_manifest(bad)
    for key in ("schedule_precommit_receipt_sha256","schedule_precommit_verifier_sha256","schedule_precommit_tsa_root_sha256"):
        bad=manifest();bad.pop(key)
        with pytest.raises(ValueError):m.validate_manifest(bad)

def test_rfc3161_verifier_is_executed_and_fail_closed(monkeypatch,tmp_path):
    v=manifest();receipt=tmp_path/"receipt";receipt.write_bytes(b"receipt");tool=tmp_path/"tool";tool.write_bytes(b"tool");root=tmp_path/"root";root.write_bytes(b"root")
    v["schedule_precommit_receipt_sha256"]=m.sha(b"receipt");v["schedule_precommit_payload_sha256"]=m.sha(m.schedule_payload(v));v["deployment_identity"]=m.sha(canonical({k:x for k,x in v.items() if k not in {"deployment_identity","manifest_identity"}}));v["manifest_identity"]=m.sha(canonical({k:x for k,x in v.items() if k!="manifest_identity"}));payload=tmp_path/"payload";payload.write_bytes(m.schedule_payload(v))
    launcher=tmp_path/"launcher";launcher.write_bytes(b"launcher");v["launcher_sha256"]=m.sha(b"launcher");v["deployment_identity"]=m.sha(canonical({k:x for k,x in v.items() if k not in {"deployment_identity","manifest_identity"}}));v["manifest_identity"]=m.sha(canonical({k:x for k,x in v.items() if k!="manifest_identity"}))
    replies=iter([type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Wed Sep 30 23:59:00 2026 GMT\n","stderr":b""})()])
    regular=m._regular;monkeypatch.setattr(m,"_regular",lambda path,expected,label:b"root" if label=="TSA root" else regular(path,expected,label))
    monkeypatch.setattr(m,"verify_installed_dependency",lambda *a:None);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(replies))
    m.verify_schedule_precommit(v,payload=payload,receipt=receipt,verifier=tool,tsa_root=root,launcher=launcher)
    monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:type("R",(),{"returncode":1,"stdout":b"","stderr":b""})())
    with pytest.raises(ValueError,match="RFC3161"):m.verify_schedule_precommit(v,payload=payload,receipt=receipt,verifier=tool,tsa_root=root,launcher=launcher)
    late=iter([type("R",(),{"returncode":0,"stdout":b"Verification: OK\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Thu Oct 1 00:00:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(late))
    with pytest.raises(ValueError,match="precommit order"):m.verify_schedule_precommit(v,payload=payload,receipt=receipt,verifier=tool,tsa_root=root,launcher=launcher)
    warning=iter([type("R",(),{"returncode":0,"stdout":b"Verification: OK\nwarning\n","stderr":b""})(),type("R",(),{"returncode":0,"stdout":b"Hash Algorithm: sha256\nTime stamp: Wed Sep 30 23:59:00 2026 GMT\n","stderr":b""})()]);monkeypatch.setattr(m.subprocess,"run",lambda *a,**k:next(warning))
    with pytest.raises(ValueError,match="RFC3161 verification"):m.verify_schedule_precommit(v,payload=payload,receipt=receipt,verifier=tool,tsa_root=root,launcher=launcher)

def test_template_is_inert_and_complete():
    text=(Path(__file__).resolve().parents[1]/"deployment/semantic-authority-metadata-capture-v2-3-12.yml.template").read_text()
    assert "workflow_dispatch" not in text and "@SCHEDULE_RECEIPT@" in text and "@RFC3161_VERIFIER@" in text and "semantic_authority_deployment_v2_3_12" in text
