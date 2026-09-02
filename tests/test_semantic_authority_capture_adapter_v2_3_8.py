import base64, hashlib, json
from pathlib import Path
import pytest
from pastila_scout import semantic_authority_capture_adapter_v2_3_8 as subject

RUN={"deployment_identity":"d"*64,"repository_id":"1355263083","workflow_commit":"9df3768bf1d9033e0b8e9b7674c56765565fcd25","run_id":"7","run_attempt":1,"event_name":"schedule","request_plan_identity":"e"*64,"ca_sha256":"f"*64}

def bundle():
    claim=subject._initiation_claim(RUN); digest=subject.sha256(subject.canonical(claim))
    statement={"_type":"https://in-toto.io/Statement/v1","subject":[{"name":"pastila-capture-initiation.json","digest":{"sha256":digest}}],"predicateType":subject.INITIATION_PREDICATE,"predicate":claim}
    return json.dumps({"dsseEnvelope":{"payload":base64.b64encode(json.dumps(statement).encode()).decode(),"payloadType":"application/vnd.in-toto+json","signatures":[{"sig":"fixture"}]},"verificationMaterial":{"tlogEntries":[{"logIndex":9,"integratedTime":10,"canonicalizedBody":"fixture"}]}}).encode()

def runtime(tmp_path,raw):
    bundle_path=tmp_path/"bundle"; bundle_path.write_bytes(raw)
    root_path=tmp_path/"trusted-root"; root_path.write_bytes(b"root")
    return subject.CosignRuntime(tmp_path/"wsl", "Ubuntu-24.04", tmp_path/"launcher", "/mnt/c/launcher", "a"*64, "/mnt/c/cosign", bundle_path, subject._expected_wsl_path(bundle_path), root_path, subject._expected_wsl_path(root_path))

def test_crypto_verification_precedes_structural_acceptance(tmp_path,monkeypatch):
    seen=[]; monkeypatch.setattr(subject.cosign,"verify_blob_attestation",lambda **kw:seen.append(kw)); monkeypatch.setattr(subject.cosign,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"root").hexdigest())
    raw=bundle(); receipt=subject.verify_initiation_bundle(bundle=raw,run=RUN,repository_slug="acidburn1danny/pastila-news-monitor",runtime=runtime(tmp_path,raw))
    assert len(seen)==1 and seen[0]["digest"]==subject.sha256(subject.canonical(subject._initiation_claim(RUN)))
    assert seen[0]["certificate_identity"]=="https://github.com/acidburn1danny/pastila-news-monitor/.github/workflows/semantic-authority-metadata-capture-v2-3-6.yml@refs/heads/public/v2.3.7-capture"
    assert receipt["verified"] is True and receipt["run_id"]=="7"

@pytest.mark.parametrize("change", ["predicate","subject","tlog","crypto"])
def test_initiation_tampering_fails_closed(tmp_path,monkeypatch,change):
    raw=json.loads(bundle())
    if change in {"predicate","subject"}:
        statement=json.loads(base64.b64decode(raw["dsseEnvelope"]["payload"]))
        if change=="predicate": statement["predicate"]["run_id"]="8"
        else: statement["subject"]=[]
        raw["dsseEnvelope"]["payload"]=base64.b64encode(json.dumps(statement).encode()).decode()
    elif change=="tlog": raw["verificationMaterial"]["tlogEntries"].append(raw["verificationMaterial"]["tlogEntries"][0])
    def verify(**kw):
        if change=="crypto": raise ValueError("signature")
    monkeypatch.setattr(subject.cosign,"verify_blob_attestation",verify)
    monkeypatch.setattr(subject.cosign,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"root").hexdigest())
    encoded=json.dumps(raw).encode()
    with pytest.raises(ValueError): subject.verify_initiation_bundle(bundle=encoded,run=RUN,repository_slug="acidburn1danny/pastila-news-monitor",runtime=runtime(tmp_path,encoded))

def test_cosign_bundle_and_decoded_bytes_cannot_diverge(tmp_path,monkeypatch):
    raw=bundle(); rt=runtime(tmp_path,raw); monkeypatch.setattr(subject.cosign,"verify_blob_attestation",lambda **kw:None); monkeypatch.setattr(subject.cosign,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"root").hexdigest())
    with pytest.raises(ValueError,match="byte split"): subject.verify_initiation_bundle(bundle=raw+b" ",run=RUN,repository_slug="acidburn1danny/pastila-news-monitor",runtime=rt)

def test_host_and_wsl_bundle_paths_cannot_diverge(tmp_path,monkeypatch):
    raw=bundle(); rt=runtime(tmp_path,raw); monkeypatch.setattr(subject.cosign,"verify_blob_attestation",lambda **kw:None); monkeypatch.setattr(subject.cosign,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"root").hexdigest())
    altered=subject.CosignRuntime(rt.wsl,rt.distribution,rt.launcher_host,rt.launcher_linux,rt.launcher_sha256,rt.cosign_linux,rt.bundle_host,"/mnt/c/other",rt.trusted_root_host,rt.trusted_root_linux)
    with pytest.raises(ValueError,match="path split"): subject.verify_initiation_bundle(bundle=raw,run=RUN,repository_slug="acidburn1danny/pastila-news-monitor",runtime=altered)

def plan():
    return {
      "CROSSREF_RELEASE_INDEX":(("GET","https://www.crossref.org/categories/metadata-retrieval/"),),
      "CROSSREF_RELEASE_RECORD":(("GET","https://www.crossref.org/blog/release-2026/"),),
      "CROSSREF_ARCHIVE_INDEX":(("GET","https://www.crossref.org/services/metadata-retrieval/public-data-file/"),),
      "CROSSREF_ARCHIVE_OBJECT_HEAD":(("HEAD","https://api-snapshots-reqpays-crossref.s3.amazonaws.com/file.tar"),),
      "OPENALEX_RELEASE_NOTES":(("GET","https://openalex.s3.amazonaws.com/RELEASE_NOTES.txt"),),
      "OPENALEX_MANIFEST_VERSION_INDEX":(("GET","https://openalex.s3.amazonaws.com/?prefix=data%2Fjsonl%2Fmanifest.json&versions="),),
      "OPENALEX_MANIFEST":(("GET","https://openalex.s3.amazonaws.com/data/jsonl/manifest.json?versionId=x"),),
      "OPENALEX_ARCHIVE_OBJECT_HEAD":(("HEAD","https://openalex.s3.amazonaws.com/data/jsonl/a.gz"),),
    }

def test_plan_is_exact_purpose_url_method_and_ca_closed(tmp_path,monkeypatch):
    ca=tmp_path/"ca"; ca.write_bytes(b"ca"); pin=hashlib.sha256(b"ca").hexdigest()
    requests=plan(); run={**RUN,"request_plan_identity":subject.request_plan_identity(requests),"ca_sha256":pin}; adapter=subject.ProductionCaptureAdapter(requests=requests,run=run,ca_file=ca)
    assert tuple(adapter._requests)==subject.PURPOSES
    bad=plan(); bad["OPENALEX_MANIFEST"]=(("GET","https://evil.invalid/x"),)
    with pytest.raises(ValueError): subject.ProductionCaptureAdapter(requests=bad,run=run,ca_file=ca)
    with pytest.raises(ValueError): subject.ProductionCaptureAdapter(requests=requests,run={**run,"ca_sha256":"0"*64},ca_file=ca)
    monkeypatch.setenv("HTTPS_PROXY","x")
    with pytest.raises(ValueError): adapter("OPENALEX_MANIFEST")

def test_zero_network_fake_tls_exercises_production_path(tmp_path,monkeypatch):
    ca=tmp_path/"ca"; ca.write_bytes(b"ca"); pin=hashlib.sha256(b"ca").hexdigest()
    class Sock:
        def getpeercert(self,binary_form=False): return b"cert"
        def version(self): return "TLSv1.3"
    class Response:
        status=200
        def read(self,n): return b"bytes"
        def getheader(self,k): return None
        def getheaders(self): return [("content-type","text/plain")]
    class Connection:
        def __init__(self,*a,**k): self.sock=Sock()
        def request(self,*a,**k): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(subject.ssl,"create_default_context",lambda **kw:object())
    monkeypatch.setattr(subject.http.client,"HTTPSConnection",Connection)
    for key in subject.PROXY_KEYS: monkeypatch.delenv(key,raising=False)
    requests=plan(); run={**RUN,"request_plan_identity":subject.request_plan_identity(requests),"ca_sha256":pin}; adapter=subject.ProductionCaptureAdapter(requests=requests,run=run,ca_file=ca)
    assert adapter("OPENALEX_MANIFEST")[0].payload==b"bytes"

def test_signed_initiation_binds_plan_and_ca(tmp_path,monkeypatch):
    raw=bundle(); rt=runtime(tmp_path,raw); monkeypatch.setattr(subject.cosign,"verify_blob_attestation",lambda **kw:None); monkeypatch.setattr(subject.cosign,"TRUSTED_ROOT_SHA256",hashlib.sha256(b"root").hexdigest())
    for field in ("request_plan_identity","ca_sha256"):
        altered={**RUN,field:"0"*64}
        with pytest.raises(ValueError,match="statement closure"):
            subject.verify_initiation_bundle(bundle=raw,run=altered,repository_slug="acidburn1danny/pastila-news-monitor",runtime=rt)

def test_no_network_or_workflow_activation_occurred():
    assert not (Path(__file__).resolve().parents[1]/".github/workflows").exists()

def test_qualification_identity_chain():
    root=Path(__file__).resolve().parents[1]
    path=root/"docs/artifacts/semantic-contract-v2-3-8-production-capture-zero-network-qualification.json"
    value=json.loads(path.read_text(encoding="utf-8")); identity=value.pop("qualification_identity")
    assert identity==subject.sha256(subject.canonical(value))
    assert value["implementation_sha256"]==subject.sha256(Path(subject.__file__).read_bytes())
    assert value["test_sha256"]==subject.sha256(Path(__file__).read_bytes())
    assert value["orchestrator_sha256"]==subject.sha256((root/"src/pastila_scout/semantic_authority_capture_orchestrator_v2_3_7.py").read_bytes())
    assert value["zero_activity"]["registry_metadata"]==0 and value["invariants"]["workflow"]=="INERT_NOT_DEPLOYED"
