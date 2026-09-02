import base64,copy,hashlib,json
from pathlib import Path
import pytest
import pastila_scout.semantic_authority_metadata_proof_v2_3_3 as m

RUN='a'*64
def test_real_acquisition_remains_fail_closed_until_external_origin_and_integration_are_proved():
 assert m.REAL_METADATA_ACQUISITION_READY is False
 assert len(m.ACQUISITION_BLOCKERS)==4
def verified(purpose,url,payload=b'x',method='GET',headers=None,identity=None):return m.VerifiedCapture(purpose,RUN,method,url,headers or {},payload,identity or hashlib.sha256(payload+url.encode()).hexdigest())
def test_capture_attests_canonical_envelope_and_replay_domain(monkeypatch,tmp_path):
 calls=[];monkeypatch.setattr(m,'verify_rfc3161',lambda **kw:calls.append(kw))
 c=m.Capture('OPENALEX_RELEASE_NOTES',RUN,'GET',m.OPENALEX_NOTES,200,{'ETag':'x'},b'data',b'receipt','2026-09-03T00:00:00Z')
 result=m.verify_capture(c,expected_purpose=c.purpose,expected_url=c.url,run_identity=RUN,openssl=tmp_path/'o',ca_file=tmp_path/'c')
 envelope=json.loads(calls[0]['payload']);assert envelope['url']==c.url and envelope['headers']['etag']=='x' and envelope['payload_sha256']==m.sha(c.payload)
 for change in ({'run_identity':'b'*64},{'purpose':'OTHER'},{'url':'https://evil'},{'status':206}):
  bad=copy.copy(c);object.__setattr__(bad,next(iter(change)),next(iter(change.values())))
  with pytest.raises(ValueError):m.verify_capture(bad,expected_purpose=c.purpose,expected_url=c.url,run_identity=RUN,openssl=tmp_path/'o',ca_file=tmp_path/'c')
def test_crossref_is_derived_from_bytes_and_pagination():
 html=b'<article><time datetime="2026-03-17T12:00:00Z"></time><h2><a href="https://www.crossref.org/blog/2026-public-data-file-now-available/">2026 public data file now available</a></h2></article><a class="next" href="https://www.crossref.org/categories/metadata-retrieval/page/2/">Next</a>'
 page2=b'<article><time datetime="2025-03-18T12:00:00Z"></time><h2><a href="https://www.crossref.org/blog/2025-public-data-file-now-available/">2025 public data file now available</a></h2></article>'
 rows=m.parse_crossref_history([verified('CROSSREF_RELEASE_INDEX',m.CROSSREF_INDEX,html),verified('CROSSREF_RELEASE_INDEX',m.CROSSREF_INDEX+'page/2/',page2)])
 assert [x['release_id'] for x in rows]==['2025','2026']
 with pytest.raises(ValueError):m.parse_crossref_history([verified('CROSSREF_RELEASE_INDEX',m.CROSSREF_INDEX,html)])
def test_crossref_invented_projection_interface_no_longer_exists():assert not hasattr(m,'close_crossref_history')
def openalex(manifest_date='2026-06-26'):
 notes=verified('OPENALEX_RELEASE_NOTES',m.OPENALEX_NOTES,b'RELEASE 2026-06-25\ntext\nRELEASE 2026-05-22\n')
 body=json.dumps({'date':manifest_date,'entities':[{'entity_type':'works','files':[{'url':'s3://openalex/data/jsonl/works/p.gz','meta':{'content_length':3}}]}]}).encode()
 return notes,verified('OPENALEX_MANIFEST',m.OPENALEX_MANIFEST+'?versionId=v1',body)
def test_openalex_dates_and_objects_derived_from_bytes():
 result=m.parse_openalex_history(*openalex());assert result['release_date']=='2026-06-25' and result['objects'][0]['byte_length']==3
 with pytest.raises(ValueError):m.parse_openalex_history(*openalex('2026-06-27'))
def test_attested_head_manifest_closure_and_registry_allowlist():
 spec=[{'locator':'s3://openalex/data/jsonl/works/p.gz','byte_length':3}];checksum=base64.b64encode(bytes.fromhex('b'*64)).decode();head=verified('OPENALEX_ARCHIVE_OBJECT_HEAD','https://openalex.s3.amazonaws.com/data/jsonl/works/p.gz',b'',method='HEAD',headers={'x-amz-version-id':'v1','x-amz-checksum-sha256':checksum,'content-length':'3'})
 assert m.bind_attested_checksums(spec,[head],registry='OPENALEX',run_identity=RUN)['object_count']==1
 with pytest.raises(ValueError):m.bind_attested_checksums([{'locator':'s3://evil/p','byte_length':3}],[head],registry='OPENALEX',run_identity=RUN)
 with pytest.raises(ValueError):m.bind_attested_checksums(spec,[],registry='OPENALEX',run_identity=RUN)
 bad=copy.copy(head);object.__setattr__(bad,'headers',{**head.headers,'x-amz-checksum-sha256':'etag'})
 with pytest.raises(ValueError):m.bind_attested_checksums(spec,[bad],registry='OPENALEX',run_identity=RUN)
 with pytest.raises(ValueError):m.bind_attested_checksums(spec,[head,head],registry='OPENALEX',run_identity=RUN)
 bad_spec=[{'locator':spec[0]['locator'],'byte_length':True}]
 with pytest.raises(ValueError):m.bind_attested_checksums(bad_spec,[head],registry='OPENALEX',run_identity=RUN)
def test_qualification_is_fully_closed():
 p=json.loads(Path('docs/artifacts/semantic-contract-v2-3-3-metadata-proof-zero-source-qualification.json').read_text(encoding='utf-8'));m.validate_qualification(p)
 for key,value in [('verdict','REWRITTEN'),('implementation_sha256','0'*64),('dependencies',{}),('proofs',{})]:
  bad=copy.deepcopy(p);bad[key]=value;bad['qualification_identity']=m.qualification_identity(bad)
  with pytest.raises(ValueError):m.validate_qualification(bad)
