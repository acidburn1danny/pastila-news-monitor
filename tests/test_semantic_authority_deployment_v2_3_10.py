import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_10 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import Capture
from pastila_scout.semantic_authority_deployment_v2_3_9 import CaptureExecution

def config():return m.FrozenRun("2026-10-01T00:00:00Z","0 0 1 10 *","a"*40,"b"*64,"c"*64)
def env():return {"GITHUB_EVENT_NAME":"schedule","GITHUB_RUN_ATTEMPT":"1","GITHUB_REPOSITORY":m.REPOSITORY_SLUG,"GITHUB_REPOSITORY_ID":m.REPOSITORY_ID,"GITHUB_SHA":"a"*40,"GITHUB_EVENT_SCHEDULE":"0 0 1 10 *"}
def test_one_shot_exact_and_no_retry_or_delay():
 m.one_shot_guard(config(),env(),datetime(2026,10,1,tzinfo=timezone.utc))
 for key,value in (("GITHUB_RUN_ATTEMPT","2"),("GITHUB_EVENT_NAME","workflow_dispatch"),("GITHUB_SHA","d"*40)):
  bad={**env(),key:value}
  with pytest.raises(ValueError):m.one_shot_guard(config(),bad,datetime(2026,10,1,tzinfo=timezone.utc))
 with pytest.raises(ValueError,match="delayed"):m.one_shot_guard(config(),env(),datetime(2026,10,1,0,1,tzinfo=timezone.utc))
def test_concrete_adapter_pins_ca_and_rejects_proxy(tmp_path,monkeypatch):
 ca=tmp_path/"ca";ca.write_bytes(b"ca");run={"ca_sha256":hashlib.sha256(b"ca").hexdigest()};a=m.AdaptiveProductionAdapter(run=run,ca_file=ca)
 monkeypatch.setenv("HTTPS_PROXY","x")
 with pytest.raises(ValueError):a("CROSSREF_RELEASE_INDEX","GET","https://www.crossref.org/categories/metadata-retrieval/")
def test_canonical_output_and_single_persistence(tmp_path):
 c=Capture("X","https://x",b"bytes","GET",200,(("x","y"),),"d"*64,"TLSv1.3"); initiation={"initiation_subject_sha256":"a"*64,"initiation_rekor_uuid":"b"*64,"initiation_rekor_log_index":"1","initiation_rekor_integrated_time":"2","verified":True};files,p=m.canonical_output(CaptureExecution((c,),()),{"x":1},initiation)
 assert set(files)=={"captures/000001.bin","capture-set.json","final-attestation-predicate.json"} and p["subject"][0]["digest"]["sha256"]
 assert p["_type"]=="https://in-toto.io/Statement/v1" and p["predicate"]["initiation"]==initiation
 manifest=json.loads(files["capture-set.json"]);assert manifest["captures"][0]["locator"]=="https://x" and manifest["captures"][0]["tls_version"]=="TLSv1.3"
 out=tmp_path/"out";m.persist_once(files,out)
 with pytest.raises(ValueError):m.persist_once(files,out)
 bad=tmp_path/"bad"
 with pytest.raises(ValueError):m.persist_once({"../escape":b"x"},bad)
 assert not bad.exists()
 with pytest.raises(ValueError,match="receipt"):m.canonical_output(CaptureExecution((c,),()),{"x":1},{"verified":True})
def test_dependency_pin_and_inert_cli(tmp_path):
 p=tmp_path/"tool";m.install_dependency_once(b"x",p,hashlib.sha256(b"x").hexdigest());m.verify_installed_dependency(p,hashlib.sha256(b"x").hexdigest())
 with pytest.raises(ValueError):m.install_dependency_once(b"x",p,hashlib.sha256(b"x").hexdigest())
 with pytest.raises(SystemExit):m.main([])
 assert m.main(["--qualification-check"])==0
def test_template_inert_and_qualification_closed():
 root=Path(__file__).resolve().parents[1];t=(root/"deployment/semantic-authority-metadata-capture-v2-3-10.yml.template").read_text()
 assert "@SCHEDULE_CRON@" in t and ".github/workflows" not in str(root/"deployment") and "workflow_dispatch" not in t
 q=json.loads((root/"docs/artifacts/semantic-contract-v2-3-10-deployment-zero-network-qualification.json").read_text()); identity=q.pop("qualification_identity")
 assert identity==hashlib.sha256(json.dumps(q,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
 assert q["module_sha256"]==hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
