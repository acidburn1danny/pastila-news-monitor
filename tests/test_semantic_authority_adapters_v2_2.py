import hashlib,io,json,sys
from pathlib import Path
import pytest
from pastila_scout.semantic_authority_adapters_v2_2 import *

def test_openalex_real_shape_and_closure():
 raw=json.dumps({"date":"2027-01-02","record_count":3,"content_length":9,"files":[{"url":"s3://openalex/data/jsonl/works/updated_date=2027-01-01/part.gz","meta":{"content_length":9,"record_count":3}}]}).encode()
 released,items=parse_openalex_manifest(raw);assert str(released)=="2027-01-02" and items[0].byte_length==9
 bad=json.loads(raw);bad["record_count"]=4
 with pytest.raises(ValueError):parse_openalex_manifest(json.dumps(bad).encode())

def test_crossref_descriptor_is_authority_restricted():
 raw=json.dumps({"publisher":"Crossref","release_date":"2027-03-01","official_release_url":"https://www.crossref.org/blog/release/","official_release_record_sha256":"a"*64,"objects":[{"versioned_locator":"s3://bucket/key?versionId=x","byte_length":3}]}).encode()
 assert parse_crossref_release_descriptor(raw,verified_official_capture_sha256="a"*64)[1][0].byte_length==3
 bad=json.loads(raw);bad["publisher"]="Owner"
 with pytest.raises(ValueError):parse_crossref_release_descriptor(json.dumps(bad).encode(),verified_official_capture_sha256="a"*64)
 with pytest.raises(ValueError):parse_crossref_release_descriptor(raw,verified_official_capture_sha256="b"*64)

def test_hash_and_merkle_are_complete_deterministic():
 spec=ObjectSpec("s3://x/key?versionId=1",3);observed={spec.locator:hash_object(io.BytesIO(b"abc"),expected_length=3)}
 assert commitment([spec],observed)==commitment([spec],observed)
 with pytest.raises(ValueError):commitment([spec],{})
 with pytest.raises(ValueError):hash_object(io.BytesIO(b"ab"),expected_length=3)

def test_mutable_openalex_locators_require_complete_version_binding():
 spec=ObjectSpec("s3://openalex/data/jsonl/works/part.gz",3)
 with pytest.raises(ValueError):commitment([spec],{spec.locator:("a"*64,3)})
 bound=bind_s3_versions([spec],{spec.locator:"v1"})
 assert "versionId=v1" in bound[0].locator
 with pytest.raises(ValueError):bind_s3_versions([spec],{})
 with pytest.raises(ValueError):commitment([bound[0],bound[0]],{bound[0].locator:("a"*64,3)})
 bogus="s3://x/key?notversionId=x"
 with pytest.raises(ValueError):commitment([ObjectSpec(bogus,3)],{bogus:("a"*64,3)})

def test_pinned_verifier_and_quorum_fail_closed(tmp_path):
 executable=Path(sys.executable);pin=hashlib.sha256(executable.read_bytes()).hexdigest()
 assert verify_with_pinned_executable(executable=executable,expected_sha256=pin,args=["-c","print('PASS')"],expected_stdout=b"PASS").strip()==b"PASS"
 with pytest.raises(ValueError):verify_with_pinned_executable(executable=executable,expected_sha256="0"*64,args=[],expected_stdout=b"")
 endpoints=frozenset({"https://a","https://b"})
 assert verify_quorum_payloads({"https://a":b"x","https://b":b"x"},expected_endpoints=endpoints)==b"x"
 with pytest.raises(ValueError):verify_quorum_payloads({"https://a":b"x","https://b":b"y"},expected_endpoints=endpoints)
 with pytest.raises(ValueError):verify_quorum_payloads({"https://a":b"x","https://c":b"x"},expected_endpoints=endpoints)

def test_rfc3161_real_receipt_and_tamper():
 root=Path(__file__).resolve().parents[1];openssl=Path(r"C:\Program Files\FireDaemon OpenSSL 3.5\bin\openssl.exe")
 if not openssl.exists():pytest.skip("qualified OpenSSL unavailable")
 import certifi
 payload=(root/"docs/artifacts/semantic-authority-v2-2-governance-freeze-payload.txt").read_bytes();receipt=(root/"docs/artifacts/semantic-authority-v2-2-governance-freeze.tsr").read_bytes();pin=hashlib.sha256(openssl.read_bytes()).hexdigest()
 ca=Path(certifi.where());capin=hashlib.sha256(ca.read_bytes()).hexdigest();kwargs=dict(receipt=receipt,openssl=openssl,ca_file=ca,expected_executable_sha256=pin,expected_ca_sha256=capin,expected_timestamp_utc="2026-09-02T17:31:02Z")
 verify_rfc3161(payload=payload,**kwargs)
 with pytest.raises(ValueError):verify_rfc3161(payload=payload+b"x",**kwargs)
 with pytest.raises(ValueError):verify_rfc3161(payload=payload,**dict(kwargs,expected_ca_sha256="0"*64))
