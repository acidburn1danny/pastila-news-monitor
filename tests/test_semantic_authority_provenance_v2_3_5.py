import base64,copy,hashlib,json
from pathlib import Path
import pytest
import pastila_scout.semantic_authority_provenance_v2_3_5 as m
import pastila_scout.semantic_authority_metadata_proof_v2_3_3 as p

RUN="a"*64
def capture(purpose,url,payload):return p.VerifiedCapture(purpose,RUN,"GET",url,{},payload,hashlib.sha256(payload+url.encode()).hexdigest())

def test_notary_quorum_binds_exact_response_and_rejects_self_assertion(monkeypatch,tmp_path):
 c=capture("OPENALEX_RELEASE_NOTES",p.OPENALEX_NOTES,b"publisher");claim=m.sha(m.canonical(m.response_claim(c)));keys={};statements=[]
 monkeypatch.setattr(m,"_verify_ed25519",lambda *args:None)
 for name in ("n1","n2","n3"):
  keys[name]=(tmp_path/name,"0"*64)
  item={"schema":"PUBLISHER_RESPONSE_NOTARY_ATTESTATION_V2_3_5","notary_id":name,"claim_identity":claim,"observed_at_utc":"2026-09-03T00:00:00Z"}
  item["signature"]=base64.b64encode(b"signature").decode();statements.append(item)
 assert m.verify_notary_quorum(c,statements[:2],pinned_public_keys=keys,openssl_path=tmp_path/"openssl")["quorum"]==2
 with pytest.raises(ValueError):m.verify_notary_quorum(c,statements[:1],pinned_public_keys=keys,openssl_path=tmp_path/"openssl")
 bad=copy.deepcopy(statements[:2]);bad[0]["claim_identity"]="0"*64
 with pytest.raises(ValueError):m.verify_notary_quorum(c,bad,pinned_public_keys=keys,openssl_path=tmp_path/"openssl")

def xml(versions,truncated="false",next_key=None,next_version=None):
 ns="http://s3.amazonaws.com/doc/2006-03-01/";items="".join(f"<Version><Key>data/jsonl/manifest.json</Key><VersionId>{v}</VersionId><LastModified>{t}</LastModified></Version>" for v,t in versions)
 markers=(f"<NextKeyMarker>{next_key}</NextKeyMarker><NextVersionIdMarker>{next_version}</NextVersionIdMarker>" if next_key else "")
 return f'<ListVersionsResult xmlns="{ns}"><Name>openalex</Name><Prefix>data/jsonl/manifest.json</Prefix>{items}<IsTruncated>{truncated}</IsTruncated>{markers}</ListVersionsResult>'.encode()

def test_openalex_s3_version_history_is_marker_and_terminal_closed():
 first=capture("OPENALEX_MANIFEST_VERSION_INDEX",m.OPENALEX_VERSION_INDEX,xml([("v2","2026-08-01T00:00:00Z")],"true","data/jsonl/manifest.json","v2"))
 second_url=m._version_url("data/jsonl/manifest.json","v2");second=capture("OPENALEX_MANIFEST_VERSION_INDEX",second_url,xml([("v1","2026-06-26T00:00:00Z")]))
 assert [x["version_id"] for x in m.parse_openalex_manifest_version_history([first,second])]==["v1","v2"]
 with pytest.raises(ValueError):m.parse_openalex_manifest_version_history([first])
 forged=capture("OPENALEX_MANIFEST_VERSION_INDEX",second_url,xml([("v1","2026-06-26T00:00:00Z")],"true","x","y"))
 with pytest.raises(ValueError):m.parse_openalex_manifest_version_history([first,forged])

def test_crossref_archive_association_is_exact_unique_and_byte_derived():
 url=p.CROSSREF_ARCHIVE;body=b'<a href="https://api-snapshots-reqpays-crossref.s3.amazonaws.com/2026.tar">Crossref 2026 public data file</a>'
 archive=capture("CROSSREF_ARCHIVE_INDEX",url,body);rows=[{"release_id":"2026","source_capture_identity":"b"*64}]
 assert m.bind_crossref_archive_associations(rows,archive)["2026"]["archive_url"].endswith("2026.tar")
 duplicate=capture("CROSSREF_ARCHIVE_INDEX",url,body+body)
 with pytest.raises(ValueError):m.bind_crossref_archive_associations(rows,duplicate)

def test_real_acquisition_stays_closed_until_notary_appointments():
 assert m.REAL_METADATA_ACQUISITION_READY is False and len(m.REMAINING_BLOCKERS)==1

def test_zero_metadata_qualification_is_identity_closed():
 value=json.loads(Path("docs/artifacts/semantic-contract-v2-3-5-provenance-zero-metadata-qualification.json").read_text(encoding="utf-8"));m.validate_qualification(value)
 value["remaining_blockers"]=[];value["qualification_identity"]=m.qualification_identity(value)
 with pytest.raises(ValueError):m.validate_qualification(value)
