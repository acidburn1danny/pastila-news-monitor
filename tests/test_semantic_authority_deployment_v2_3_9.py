import hashlib, json
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_deployment_v2_3_9 as m
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import Capture

def run():
    return {"deployment_identity":"a"*64,"repository_id":"1355263083","runtime_commit":m.RUNTIME_COMMIT,"workflow_commit":"b"*40,"run_id":"1","run_attempt":1,"event_name":"schedule","derivation_policy_identity":m.DERIVATION_POLICY_IDENTITY,"seed_plan_identity":m.SEED_PLAN_IDENTITY,"ca_sha256":"c"*64}

class Transport:
    production=True
    def __init__(self, fn): self.fn=fn; self.run_binding=m.sha(m.canonical(run())); self.ca_sha256=run()["ca_sha256"]
    def __call__(self,purpose,method,url): return self.fn(purpose,method,url)

def captured(purpose, method, url, payload=b"closed"):
    return Capture(purpose,url,payload,method,200,(("content-type","application/octet-stream"),),"d"*64,"TLSv1.3")

def test_runtime_and_workflow_commits_are_distinct_and_closed():
    assert m.initiation_claim(run())["runtime_commit"]==m.RUNTIME_COMMIT
    for field,value in (("runtime_commit","d"*40),("workflow_commit",m.RUNTIME_COMMIT),("derivation_policy_identity","0"*64),("seed_plan_identity","0"*64)):
        bad={**run(),field:value}
        with pytest.raises(ValueError):m.initiation_claim(bad)

def test_adaptive_derivation_is_byte_bound_and_order_invariant():
    cross=b'<a href="/blog/release-a/"></a><a href="https://api-snapshots-reqpays-crossref.s3.amazonaws.com/a.tar"></a>'
    versions=b'<ListVersionsResult><Version><VersionId>v2</VersionId></Version><Version><VersionId>v1</VersionId></Version><IsTruncated>false</IsTruncated></ListVersionsResult>'
    captures={"CROSSREF_RELEASE_INDEX":(Capture("CROSSREF_RELEASE_INDEX",m.SEEDS[0][2],cross),),"OPENALEX_MANIFEST_VERSION_INDEX":(Capture("OPENALEX_MANIFEST_VERSION_INDEX",m.SEEDS[3][2],versions),)}
    first=m.derive_requests(captures); second=m.derive_requests(dict(reversed(tuple(captures.items()))))
    assert first==second and all(row[3] in {m.sha(cross),m.sha(versions)} for row in first)
    assert {row[0] for row in first}=={"CROSSREF_RELEASE_RECORD","CROSSREF_ARCHIVE_OBJECT_HEAD","OPENALEX_MANIFEST"}

def test_manifest_object_derivation_rejects_malformed_or_foreign():
    good=json.dumps({"entries":[{"url":"works/a.gz"},{"url":"https://evil.invalid/x"}]}).encode()
    rows=m.derive_requests({"OPENALEX_MANIFEST":(Capture("OPENALEX_MANIFEST","https://openalex.s3.amazonaws.com/data/jsonl/manifest.json?versionId=v",good),)})
    assert len(rows)==1 and rows[0][2]=="https://openalex.s3.amazonaws.com/data/jsonl/works/a.gz"
    with pytest.raises(ValueError):m.derive_requests({"OPENALEX_MANIFEST":(Capture("OPENALEX_MANIFEST","x",b"{"),)})

def test_initiation_precedes_every_transport_and_failure_is_terminal(monkeypatch):
    calls=[]; verifier=object(); bundle_path=Path("bundle")
    monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw: (_ for _ in ()).throw(ValueError("crypto")))
    with pytest.raises(ValueError):m.execute_capture(run=run(),bundle=b"x",bundle_path=bundle_path,repository_slug=m.REPOSITORY_SLUG,verifier=verifier,capture_one=lambda *x:calls.append(x))
    assert calls==[]
    monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw:{"verified":True,"initiation_subject_sha256":m.sha(m.canonical(m.initiation_claim(run())))})
    def capture(p,method,url):
        calls.append((p,method,url))
        payload=b'<ListVersionsResult><IsTruncated>false</IsTruncated></ListVersionsResult>' if p=="OPENALEX_MANIFEST_VERSION_INDEX" else b"no links"
        return captured(p,method,url,payload)
    result=m.execute_capture(run=run(),bundle=b"x",bundle_path=bundle_path,repository_slug=m.REPOSITORY_SLUG,verifier=verifier,capture_one=Transport(capture))
    assert len(result.captures)==4 and result.derivations==() and calls==list(m.SEEDS)

def test_adaptive_execution_reaches_fixed_point_without_retry(monkeypatch):
    calls=[];monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw:{"verified":True,"initiation_subject_sha256":m.sha(m.canonical(m.initiation_claim(run())))})
    def capture(purpose,method,url):
        calls.append((purpose,method,url))
        if purpose=="CROSSREF_RELEASE_INDEX" and url==m.SEEDS[0][2]: payload=b'<a href="/categories/metadata-retrieval/page/2/"></a>'
        elif purpose=="CROSSREF_RELEASE_INDEX": payload=b'<a href="/blog/release-z/"></a>'
        elif purpose=="OPENALEX_MANIFEST_VERSION_INDEX": payload=b'<ListVersionsResult><Version><VersionId>v1</VersionId></Version><IsTruncated>false</IsTruncated></ListVersionsResult>'
        elif purpose=="OPENALEX_MANIFEST": payload=b'{"entries":[{"url":"works/a.gz"}]}'
        else: payload=b"closed"
        return captured(purpose,method,url,payload)
    result=m.execute_capture(run=run(),bundle=b"x",bundle_path=Path("bundle"),repository_slug=m.REPOSITORY_SLUG,verifier=object(),capture_one=Transport(capture))
    assert len(calls)==len(set(calls))==8
    assert {x.purpose for x in result.captures}>={"CROSSREF_RELEASE_RECORD","OPENALEX_ARCHIVE_OBJECT_HEAD"}
    assert len(result.derivations)==4 and all(len(x)==4 and len(x[3])==64 for x in result.derivations)

def test_transport_cannot_substitute_response_identity(monkeypatch):
    monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw:{"verified":True,"initiation_subject_sha256":m.sha(m.canonical(m.initiation_claim(run())))})
    with pytest.raises(ValueError,match="response/request binding"):
        m.execute_capture(run=run(),bundle=b"x",bundle_path=Path("bundle"),repository_slug=m.REPOSITORY_SLUG,verifier=object(),capture_one=Transport(lambda p,method,url:captured(p,method,"https://evil.invalid/",b"x")))

def test_final_attestation_uses_exact_same_claim():
    r=run(); claim=m.initiation_claim(r)
    summary={"initiation_claim":claim,"initiation_subject_sha256":m.sha(m.canonical(claim)),"initiation_rekor_uuid":"d"*64,"initiation_rekor_log_index":"1","final_rekor_log_index":"2","runtime_commit":r["runtime_commit"],"workflow_commit":r["workflow_commit"],"derivation_policy_identity":r["derivation_policy_identity"],"seed_plan_identity":r["seed_plan_identity"]}
    m.validate_final_attestation(summary,r)
    bad=dict(summary);bad["seed_plan_identity"]="0"*64
    with pytest.raises(ValueError):m.validate_final_attestation(bad,r)

def test_linux_native_verifier_is_hash_pinned_and_closed(tmp_path,monkeypatch):
    cosign=tmp_path/"cosign";launcher=tmp_path/"launcher";root=tmp_path/"root"
    cosign.write_bytes(b"c");launcher.write_bytes(b"l");root.write_bytes(b"r")
    monkeypatch.setattr(m,"COSIGN_SHA256",hashlib.sha256(b"c").hexdigest());monkeypatch.setattr(m,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"r").hexdigest());monkeypatch.setattr(m,"LINUX_LAUNCHER_SHA256",hashlib.sha256(b"l").hexdigest())
    for key in m.PROXY_KEYS:monkeypatch.delenv(key,raising=False)
    seen={};monkeypatch.setattr(m.subprocess,"run",lambda cmd,**kw:(seen.update(cmd=cmd,kw=kw) or type("R",(),{"returncode":0})()))
    runtime=m.LinuxVerifier(cosign,launcher,root,m.COSIGN_SHA256,hashlib.sha256(b"l").hexdigest(),m.TRUSTED_ROOT_SHA256)
    assert m.run_linux_verifier(runtime,("version",)).returncode==0 and seen["cmd"][:2]==["/usr/bin/bash",str(launcher)]
    monkeypatch.setenv("HTTPS_PROXY","x")
    with pytest.raises(ValueError):m.run_linux_verifier(runtime,("version",))

def test_linux_initiation_is_direct_crypto_not_callback(tmp_path,monkeypatch):
    import base64
    from types import SimpleNamespace
    r=run();claim=m.initiation_claim(r);digest=m.sha(m.canonical(claim));statement={"_type":"https://in-toto.io/Statement/v1","subject":[{"name":"pastila-capture-initiation.json","digest":{"sha256":digest}}],"predicateType":"https://pastila.invalid/semantic-authority/initiation/v2.3.9","predicate":claim}
    bundle=json.dumps({"dsseEnvelope":{"payload":base64.b64encode(json.dumps(statement).encode()).decode(),"payloadType":"application/vnd.in-toto+json","signatures":[{"sig":"fixture"}]},"verificationMaterial":{"tlogEntries":[{"logIndex":1,"integratedTime":2}]}}).encode();path=tmp_path/"bundle";path.write_bytes(bundle)
    monkeypatch.setattr(m,"run_linux_verifier",lambda runtime,args:type("R",(),{"returncode":0,"stdout":b"Verified OK","stderr":b""})())
    runtime=SimpleNamespace(trusted_root=tmp_path/"root")
    receipt=m.verify_linux_initiation(run=r,bundle=bundle,bundle_path=path,repository_slug=m.REPOSITORY_SLUG,runtime=runtime)
    assert receipt["verified"] is True and receipt["initiation_rekor_log_index"]=="1"
    with pytest.raises(ValueError):m.verify_linux_initiation(run=r,bundle=bundle+b" ",bundle_path=path,repository_slug=m.REPOSITORY_SLUG,runtime=runtime)

def test_rekor_entry_is_mandatory_even_after_cosign_success(tmp_path,monkeypatch):
    import base64
    from types import SimpleNamespace
    r=run();claim=m.initiation_claim(r);digest=m.sha(m.canonical(claim));statement={"_type":"https://in-toto.io/Statement/v1","subject":[{"name":"pastila-capture-initiation.json","digest":{"sha256":digest}}],"predicateType":"https://pastila.invalid/semantic-authority/initiation/v2.3.9","predicate":claim}
    bundle=json.dumps({"dsseEnvelope":{"payload":base64.b64encode(json.dumps(statement).encode()).decode(),"payloadType":"application/vnd.in-toto+json","signatures":[{"sig":"fixture"}]},"verificationMaterial":{"tlogEntries":[]}}).encode();path=tmp_path/"bundle";path.write_bytes(bundle)
    monkeypatch.setattr(m,"run_linux_verifier",lambda runtime,args:type("R",(),{"returncode":0,"stdout":b"Verified OK","stderr":b""})())
    with pytest.raises(ValueError,match="Rekor"):m.verify_linux_initiation(run=r,bundle=bundle,bundle_path=path,repository_slug=m.REPOSITORY_SLUG,runtime=SimpleNamespace(trusted_root=tmp_path/"root"))

def test_same_bytes_at_distinct_locators_are_not_collapsed(monkeypatch):
    monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw:{"verified":True,"initiation_subject_sha256":m.sha(m.canonical(m.initiation_claim(run())))})
    def derive(captures):
        item=next(iter(captures.values()))[0];source=m.sha(item.payload)
        if item.purpose!="CROSSREF_RELEASE_INDEX":return ()
        if item.locator==m.SEEDS[0][2]:return (("CROSSREF_RELEASE_INDEX","GET","https://www.crossref.org/categories/metadata-retrieval/page/2/",source),)
        return (("CROSSREF_RELEASE_RECORD","GET","https://www.crossref.org/blog/release-from-page-2/",source),)
    monkeypatch.setattr(m,"derive_requests",derive)
    def capture(purpose,method,url):
        return captured(purpose,method,url,b"identical")
    result=m.execute_capture(run=run(),bundle=b"x",bundle_path=Path("bundle"),repository_slug=m.REPOSITORY_SLUG,verifier=object(),capture_one=Transport(capture))
    assert any(x.purpose=="CROSSREF_RELEASE_RECORD" for x in result.captures)

def test_production_transport_and_tls_are_mandatory(monkeypatch):
    monkeypatch.setattr(m,"verify_linux_initiation",lambda **kw:{"verified":True,"initiation_subject_sha256":m.sha(m.canonical(m.initiation_claim(run())))})
    with pytest.raises(ValueError,match="production capture"):
        m.execute_capture(run=run(),bundle=b"x",bundle_path=Path("bundle"),repository_slug=m.REPOSITORY_SLUG,verifier=object(),capture_one=lambda p,method,url:captured(p,method,url))
    with pytest.raises(ValueError,match="response/request binding"):
        m.execute_capture(run=run(),bundle=b"x",bundle_path=Path("bundle"),repository_slug=m.REPOSITORY_SLUG,verifier=object(),capture_one=Transport(lambda p,method,url:Capture(p,url,b"x",method)))

def test_repository_identity_is_not_caller_selectable(tmp_path):
    r=run(); bad={**r,"repository_id":"999"}
    with pytest.raises(ValueError,match="run closure"):m.initiation_claim(bad)

def test_openalex_truncation_is_closed_and_continued():
    payload=b'<ListVersionsResult><Version><VersionId>v1</VersionId></Version><IsTruncated>true</IsTruncated><NextKeyMarker>data-key</NextKeyMarker><NextVersionIdMarker>v1</NextVersionIdMarker></ListVersionsResult>'
    item=Capture("OPENALEX_MANIFEST_VERSION_INDEX",m.SEEDS[3][2],payload)
    rows=m.derive_requests({"OPENALEX_MANIFEST_VERSION_INDEX":(item,)})
    assert any(row[0]=="OPENALEX_MANIFEST_VERSION_INDEX" and "key-marker=data-key" in row[2] for row in rows)
    broken=payload.replace(b"<NextKeyMarker>data-key</NextKeyMarker>",b"")
    with pytest.raises(ValueError,match="continuation"):m.derive_requests({"OPENALEX_MANIFEST_VERSION_INDEX":(Capture("OPENALEX_MANIFEST_VERSION_INDEX",m.SEEDS[3][2],broken),)})

def test_derived_locator_boundary_rejects_userinfo_ports_and_dot_segments():
    for url in ("https://evil@www.crossref.org/blog/x/","https://www.crossref.org:444/blog/x/","https://openalex.s3.amazonaws.com/data/jsonl/../secret"):
        assert not m._allowed_request("CROSSREF_RELEASE_RECORD" if "crossref" in url else "OPENALEX_ARCHIVE_OBJECT_HEAD","GET" if "crossref" in url else "HEAD",url)

def test_entry_point_remains_inert():
    with pytest.raises(SystemExit,match="not authorized"):m.main()

def test_zero_network_qualification_identity_chain():
    root=Path(__file__).resolve().parents[1];path=root/"docs/artifacts/semantic-contract-v2-3-9-deployment-path-zero-network-qualification.json"
    value=json.loads(path.read_text(encoding="utf-8"));identity=value.pop("qualification_identity")
    assert identity==m.sha(m.canonical(value));assert value["implementation_sha256"]==m.sha(Path(m.__file__).read_bytes());assert value["test_sha256"]==m.sha(Path(__file__).read_bytes())
    assert value["zero_activity"]=={"workflow_deployed":0,"rfc3161_schedule_requests":0,"registry_metadata":0,"snapshot_content":0,"frame_execution":0,"source_selection":0,"authority_bases":0,"pilot15":0,"blind_access":0}
