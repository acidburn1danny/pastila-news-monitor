import json
from pathlib import Path

import pytest

from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import Capture, HOSTS, PURPOSES, canonical, orchestrate, sha256, validate_pins

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / "deployment" / "dependency-pins-v2-3-7.json").read_text(encoding="utf-8"))
RUN = {"deployment_identity":"d"*64,"repository_id":"1355263083","workflow_commit":"6aac983e6db4136296e9062cdf46c9c95fe21d01","run_id":"1","run_attempt":1,"event_name":"schedule","request_plan_identity":"e"*64,"ca_sha256":"f"*64}


def receipt(run=RUN):
    return {"verified":True,"deployment_identity":run["deployment_identity"],"repository_id":run["repository_id"],"workflow_commit":run["workflow_commit"],"run_id":run["run_id"],"run_attempt":1,"request_plan_identity":run["request_plan_identity"],"ca_sha256":run["ca_sha256"],"rekor_uuid":"a"*64,"rekor_log_index":"1","bundle_sha256":"b"*64}


def item(purpose, *, payload=b"fixture", status=200, host=None, method=None):
    return Capture(purpose, f"https://{host or HOSTS[purpose]}/frozen", payload, method or ("HEAD" if purpose.endswith("OBJECT_HEAD") else "GET"), status)


def test_exact_once_order_and_actual_byte_closure():
    calls=[]
    result=orchestrate(run=RUN,pins=PINS,verify_initiation=lambda r:(calls.append("init") or receipt(r)),capture=lambda p:(calls.append(p) or (item(p,payload=p.encode()),)))
    assert calls == ["init", *PURPOSES]
    assert tuple(x["purpose"] for x in result.manifest["captures"]) == PURPOSES
    assert len(result.capture_files) == 8
    for row in result.manifest["captures"]:
        assert row["length"] == len(result.capture_files[row["path"]])
        assert row["sha256"] == sha256(result.capture_files[row["path"]])


def test_initiation_failure_or_noop_prevents_transport():
    for verifier in (lambda _: (_ for _ in ()).throw(ValueError("bad")), lambda _: None, lambda _: {**receipt(),"verified":False}):
        called=[]
        with pytest.raises(ValueError): orchestrate(run=RUN,pins=PINS,verify_initiation=verifier,capture=lambda p:called.append(p))
        assert called == []


def test_production_adapter_run_binding_cannot_be_substituted():
    class Adapter:
        run_binding="0"*64
        def __call__(self,purpose): raise AssertionError("transport reached")
    with pytest.raises(ValueError,match="adapter/run binding"):
        orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=Adapter())


def test_production_head_evidence_allows_empty_body_but_not_missing_tls():
    class Adapter:
        production=True
        run_binding=sha256(canonical(RUN))
        plan_identity=RUN["request_plan_identity"]
        ca_sha256=RUN["ca_sha256"]
        def __call__(self,purpose):
            method="HEAD" if purpose.endswith("OBJECT_HEAD") else "GET"
            payload=b"" if method=="HEAD" else b"x"
            return (Capture(purpose,f"https://{HOSTS[purpose]}/object",payload,method,200,(("content-length","1"),),"a"*64,"TLSv1.3"),)
    result=orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=Adapter())
    assert sum(row["method"]=="HEAD" and row["length"]==0 for row in result.manifest["captures"])==2
    class MissingTls(Adapter):
        def __call__(self,purpose):
            value=super().__call__(purpose)[0]
            return (Capture(value.purpose,value.locator,value.payload,value.method,value.status),)
    with pytest.raises(ValueError,match="TLS evidence"): orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=MissingTls())

def test_production_plan_or_ca_cannot_be_self_consistent_but_unsigned():
    class Adapter:
        production=True
        run_binding=sha256(canonical(RUN))
        plan_identity="0"*64
        ca_sha256=RUN["ca_sha256"]
        def __call__(self,purpose): raise AssertionError("transport reached")
    with pytest.raises(ValueError,match="plan/CA initiation binding"):
        orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=Adapter())


@pytest.mark.parametrize("field,value", [("repository_id","9"),("workflow_commit","x"),("run_id","0"),("run_attempt",2),("event_name","workflow_dispatch")])
def test_run_identity_mutations_fail_closed(field,value):
    run={**RUN,field:value}
    with pytest.raises(ValueError): orchestrate(run=run,pins=PINS,verify_initiation=lambda r:receipt(r),capture=lambda p:(item(p),))


@pytest.mark.parametrize("mutation", ["extra", "action", "container", "dependency"])
def test_pin_mutations_fail_closed(mutation):
    value=json.loads(json.dumps(PINS))
    if mutation == "extra": value["extra"] = True
    elif mutation == "action": value["actions"]["actions/checkout"] = "0"*40
    elif mutation == "container": value["container"] = "python:latest"
    else: value["runtime_dependencies"] = ["unpinned"]
    with pytest.raises(ValueError): validate_pins(value)


@pytest.mark.parametrize("transport", [
    lambda p:(item("CROSSREF_RELEASE_INDEX"),), lambda p:(item(p,payload=b""),), lambda p:(item(p,status=302),),
    lambda p:(item(p,host="evil.invalid"),), lambda p:(item(p,method="POST"),),
    lambda p:(Capture(p,f"https://{HOSTS[p]}/../escape",b"x","HEAD" if p.endswith("OBJECT_HEAD") else "GET"),),
    lambda p:(), lambda p:(item(p),item(p)),
])
def test_capture_boundary_mutations_fail_closed(transport):
    with pytest.raises(ValueError): orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=transport)


def test_real_network_and_process_escape_not_used_by_qualification(monkeypatch):
    import socket, subprocess, urllib.request
    deny=lambda *a,**k:(_ for _ in ()).throw(AssertionError("external execution"))
    monkeypatch.setattr(socket,"socket",deny); monkeypatch.setattr(subprocess,"run",deny); monkeypatch.setattr(subprocess,"Popen",deny); monkeypatch.setattr(urllib.request,"urlopen",deny)
    assert len(orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=lambda p:(item(p),)).capture_files)==8


def test_dynamic_pages_are_retained_without_owner_redraw():
    def grouped(purpose):
        if purpose=="CROSSREF_RELEASE_INDEX":
            return (item(purpose,payload=b"page1"), Capture(purpose,f"https://{HOSTS[purpose]}/page/2/",b"page2"))
        return (item(purpose),)
    result=orchestrate(run=RUN,pins=PINS,verify_initiation=lambda _:receipt(),capture=grouped)
    assert len(result.capture_files)==9
    assert [x["purpose"] for x in result.manifest["captures"]][:2]==["CROSSREF_RELEASE_INDEX"]*2


def test_cli_is_inert():
    from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import main
    with pytest.raises(SystemExit, match="not activated"): main()


def test_template_and_qualification_identity_chain():
    template=(ROOT/"deployment/semantic-authority-metadata-capture-v2-3-6.yml.template").read_text(encoding="utf-8")
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in template
    assert "python@sha256:edf6433343f65f94707985869aeaafe8beadaeaee11c4bc02068fca52dce28dd" in template
    assert "actions/checkout@v" not in template and not (ROOT/".github/workflows").exists()
    q=json.loads((ROOT/"docs/artifacts/semantic-contract-v2-3-7-capture-orchestration-zero-network-qualification.json").read_text(encoding="utf-8")); qid=q.pop("qualification_identity")
    assert qid==sha256(canonical(q)) and q["dependency_pins_identity"]==PINS["pins_identity"]
    assert q["implementation_sha256"]==sha256((ROOT/"src/pastila_scout/semantic_authority_capture_orchestrator_v2_3_7.py").read_bytes())
    assert q["test_sha256"]==sha256(Path(__file__).read_bytes())
    assert q["workflow_template_sha256"]==sha256((ROOT/"deployment/semantic-authority-metadata-capture-v2-3-6.yml.template").read_bytes())
