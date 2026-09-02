import base64
import hashlib
import json
from pathlib import Path

import pytest

import pastila_scout.semantic_authority_acquisition_v2_3_4 as a
import pastila_scout.semantic_authority_metadata_proof_v2_3_3 as p

RUN="a"*64


def test_real_metadata_gate_remains_closed_for_unresolved_origin_and_registry_derivation():
    assert a.REAL_METADATA_ACQUISITION_READY is False
    assert len(a.REMAINING_BLOCKERS)==3


class Socket:
    def getpeercert(self, *, binary_form=False): return b"certificate" if binary_form else {}
    def version(self): return "TLSv1.3"


class Response:
    status=200
    def read(self): return b"publisher bytes"
    def getheaders(self): return [("Content-Type","text/plain")]


class Connection:
    def __init__(self,*args,**kwargs): self.sock=Socket(); self.request_args=None
    def request(self,*args,**kwargs): self.request_args=(args,kwargs)
    def getresponse(self): return Response()
    def close(self): pass


def test_direct_tls_capture_is_timestamped_and_verified(monkeypatch,tmp_path):
    ca=tmp_path/"ca";ca.write_bytes(b"ca");openssl=tmp_path/"openssl";openssl.write_bytes(b"openssl")
    monkeypatch.setattr(p,"CA_BUNDLE_SHA256",hashlib.sha256(b"ca").hexdigest())
    monkeypatch.setattr(a.ssl,"create_default_context",lambda **kwargs:object())
    monkeypatch.setattr(a.http.client,"HTTPSConnection",Connection)
    calls=[];monkeypatch.setattr(p,"verify_rfc3161",lambda **kw:calls.append(kw))
    got=a.acquire_attested_capture(url=p.OPENALEX_NOTES,purpose="OPENALEX_RELEASE_NOTES",run_identity=RUN,
      method="GET",ca_file=ca,openssl=openssl,timestamp=lambda payload:(b"receipt","2026-09-03T00:00:00Z"))
    assert got.payload==b"publisher bytes" and got.headers["x-pastila-tls-version"]=="TLSv1.3" and len(calls)==1
    with pytest.raises(ValueError):
      a.acquire_attested_capture(url="https://evil.invalid/x",purpose="OPENALEX_RELEASE_NOTES",run_identity=RUN,
        method="GET",ca_file=ca,openssl=openssl,timestamp=lambda payload:(b"r","2026-09-03T00:00:00Z"))
    with pytest.raises(ValueError):
      a.acquire_attested_capture(url="https://openalex.s3.amazonaws.com/unrelated",purpose="OPENALEX_RELEASE_NOTES",run_identity=RUN,
        method="GET",ca_file=ca,openssl=openssl,timestamp=lambda payload:(b"r","2026-09-03T00:00:00Z"))


def test_crossref_discovered_records_require_exact_independent_capture_closure():
    index=capture("CROSSREF_RELEASE_INDEX");url="https://www.crossref.org/blog/release/"
    parsed=[{"release_id":"2026","publication_date":"2026-03-17","official_url":url,"source_capture_identity":index.identity}]
    record=p.VerifiedCapture("CROSSREF_RELEASE_RECORD",RUN,"GET",url,{},b"record","d"*64)
    assert a.bind_crossref_release_records(parsed,[record])[0]["source_capture_identity"]=="d"*64
    with pytest.raises(ValueError):a.bind_crossref_release_records(parsed,[])


def capture(purpose="OPENALEX_MANIFEST"):
    if purpose=="OPENALEX_MANIFEST": url,method=p.OPENALEX_MANIFEST+"?versionId=v1","GET"
    elif purpose=="OPENALEX_ARCHIVE_OBJECT_HEAD": url,method="https://openalex.s3.amazonaws.com/data/jsonl/x","HEAD"
    else: url,method=p.OPENALEX_NOTES,"GET"
    identity="b"*64 if purpose=="OPENALEX_ARCHIVE_OBJECT_HEAD" else hashlib.sha256(purpose.encode()).hexdigest()
    return p.VerifiedCapture(purpose,RUN,method,url,{},b"" if method=="HEAD" else b"x",identity)


def archive():
    checksum=hashlib.sha256(b"object").hexdigest()
    leaf={"VERSIONED_IMMUTABLE_LOCATOR":"s3://openalex/data/jsonl/x?versionId=v1","BYTE_LENGTH":6,"SHA256":checksum,"HEAD_CAPTURE_IDENTITY":"b"*64}
    root=hashlib.sha256(b"\0"+p.canonical(leaf)).hexdigest()
    return {"object_count":1,"total_bytes":6,"merkle_root":root,"leaves":[leaf]}


def test_exact_v231_assembly_closes_registry_run_and_manifest(monkeypatch,tmp_path):
    openssl=tmp_path/"openssl";openssl.write_bytes(b"openssl");ca=tmp_path/"ca";ca.write_bytes(b"ca")
    monkeypatch.setattr(p,"verify_rfc3161",lambda **kw:None)
    manifest=capture();notes=capture("OPENALEX_RELEASE_NOTES");head=capture("OPENALEX_ARCHIVE_OBJECT_HEAD");release={"release_id":"2026-06-25","publication_date":"2026-06-25","official_url":p.OPENALEX_NOTES,"source_capture_identity":notes.identity}
    binding={release["release_id"]:{"registry":"OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT","release_id":release["release_id"],"release_record_identity":notes.identity,"manifest_capture_identity":manifest.identity,"archive":archive()}}
    rows,evidence=a.assemble_release_history(registry="OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT",parsed_releases=[release],commitments=binding,
      run_identity=RUN,captures=[notes,manifest,head],history_receipt=b"receipt",history_timestamp_utc="2026-09-03T00:00:00Z",openssl=openssl,ca_file=ca)
    assert set(rows[0])=={"registry","release_id","publication_date","official_release_record_identity","completeness_evidence_identity","archive_commitment_identity","immutable_locator_set_identity","archive_available"}
    selected=a.select_assembled_predecessor(rows=rows,evidence=evidence,history_receipt=b"receipt",registry="OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT",openssl=openssl,ca_file=ca)
    assert selected["release_id"]=="2026-06-25"
    bad=dict(binding);bad[release["release_id"]]={**binding[release["release_id"]],"registry":"CROSSREF_ANNUAL_PUBLIC_DATA_FILE"}
    with pytest.raises(ValueError):a.assemble_release_history(registry="OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT",parsed_releases=[release],commitments=bad,run_identity=RUN,captures=[notes,manifest,head],history_receipt=b"r",history_timestamp_utc="2026-09-03T00:00:00Z",openssl=openssl,ca_file=ca)
    corrupt={release["release_id"]:{**binding[release["release_id"]],"archive":{**archive(),"merkle_root":"0"*64}}}
    with pytest.raises(ValueError,match="Merkle"):a.assemble_release_history(registry="OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT",parsed_releases=[release],commitments=corrupt,run_identity=RUN,captures=[notes,manifest,head],history_receipt=b"r",history_timestamp_utc="2026-09-03T00:00:00Z",openssl=openssl,ca_file=ca)


def test_cross_registry_and_cross_run_replay_fail_closed(monkeypatch,tmp_path):
    openssl=tmp_path/"o";openssl.write_bytes(b"o");ca=tmp_path/"c";ca.write_bytes(b"c");monkeypatch.setattr(p,"verify_rfc3161",lambda **kw:None)
    cap=capture("CROSSREF_RELEASE_INDEX")
    release={"release_id":"2026","publication_date":"2026-03-17","official_url":"https://www.crossref.org/blog/x","source_capture_identity":cap.identity}
    binding={"2026":{"registry":"CROSSREF_ANNUAL_PUBLIC_DATA_FILE","release_id":"2026","release_record_identity":cap.identity,"manifest_capture_identity":cap.identity,"archive":archive()}}
    with pytest.raises(ValueError,match="cross-run or cross-registry"):
      a.assemble_release_history(registry="OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT",parsed_releases=[release],commitments=binding,run_identity=RUN,captures=[cap],history_receipt=b"r",history_timestamp_utc="2026-09-03T00:00:00Z",openssl=openssl,ca_file=ca)


def test_zero_metadata_qualification_is_identity_closed():
    value=json.loads(Path("docs/artifacts/semantic-contract-v2-3-4-acquisition-zero-metadata-qualification.json").read_text(encoding="utf-8"))
    a.validate_qualification(value)
    value["zero_activity"]["registry_metadata"]=1;value["qualification_identity"]=a.qualification_identity(value)
    with pytest.raises(ValueError):a.validate_qualification(value)
