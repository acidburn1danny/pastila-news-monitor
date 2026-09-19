import base64,copy,json
from pathlib import Path
import pytest
import materialize_production_core_v15_r4_key_rotation_v2 as issuer
import pastila_scout.production_core_r4_adjudicator_client_v2 as client
from pastila_scout.production_core_r4_adjudication_execution import canonical,digest,identity

SIG_A=base64.b64decode('UXKRBl0rnpq6UdmmvNwLgzw/IwP/xQpTph6/idG7TGCxcX+U0UqASvSKL45y5cQ0ZOl9E8Z6jSoz6byvd0BECw==')
SIG_B=base64.b64decode('RbEf/V7j6qb3ZTup+h3vBOiN3dfzoDxReY2JMB01XIcVVe+qekfYxUgtcDJN1eCaCEtGq62OAObiLgRbfwBKAA==')

def test_both_pop_and_independence():
 a=issuer.verify_pop('ADJUDICATOR_A',SIG_A);b=issuer.verify_pop('ADJUDICATOR_B',SIG_B)
 assert a['proof_identity']!=b['proof_identity'];assert issuer.KEYS['ADJUDICATOR_A']['pem_sha256']!=issuer.KEYS['ADJUDICATOR_B']['pem_sha256']
 with pytest.raises(ValueError):issuer.verify_pop('ADJUDICATOR_A',SIG_B)

def test_registry_supersession_and_authority_bridge():
 registry,responses,authority,boundary=issuer.build(SIG_A,SIG_B)
 assert registry['supersedes_registry_identity']==issuer.OLD_REGISTRY
 assert authority['successor_registry_identity']==registry['registry_identity']
 assert boundary['rotation_authority_identity']==authority['rotation_authority_identity']
 assert boundary['role_closure']==1986 and boundary['combined_receipt_closure']==3972
 assert not boundary['real_receipts_created'] and not boundary['adjudication_performed'] and boundary['semantic_verdict'] is None and not boundary['promotion']

def test_registry_rejects_old_or_cross_role_key(tmp_path):
 registry=issuer.registry_for({'ADJUDICATOR_A':issuer.response('ADJUDICATOR_A',SIG_A),'ADJUDICATOR_B':issuer.response('ADJUDICATOR_B',SIG_B)})
 path=tmp_path/'registry.json';path.write_bytes(canonical(registry))
 a=client.registry_registration('ADJUDICATOR_A',path);b=client.registry_registration('ADJUDICATOR_B',path);assert a[1]!=b[1]
 bad=copy.deepcopy(registry);bad['roles']['ADJUDICATOR_A']=bad['roles']['ADJUDICATOR_B'];core=dict(bad);core.pop('registry_identity');bad['registry_identity']=identity(core);path.write_bytes(canonical(bad))
 with pytest.raises(ValueError):client.registry_registration('ADJUDICATOR_A',path)

def test_receipt_v2_binds_rotation_registry_and_historical_packet_registry():
 packet={'packet_identity':'1'*64,'global_ordinal':1,'case_id':'case','candidate_alias':'CANDIDATE-A','raw_output_sha256':'2'*64}
 value=client.unsigned_receipt(authority_identity='3'*64,registry_identity='4'*64,packet=packet,role='ADJUDICATOR_A',adjudicator_id='EVALUATOR-A-01',key_sha256=issuer.KEYS['ADJUDICATOR_A']['pem_sha256'],verdict='PASS')
 assert value['schema_version']==2 and value['source_packet_registry_identity']==issuer.OLD_REGISTRY and value['adjudicator_registry_identity']=='4'*64 and value['key_rotation_authority_identity']=='3'*64
 for field in ('key_rotation_authority_identity','adjudicator_registry_identity','packet_identity','adjudicator_key_sha256'):
  bad=dict(value);bad[field]='0'*64;assert canonical(bad)!=canonical(value)

def test_old_receipt_and_invalid_verdict_fail_closed():
 packet={'packet_identity':'1'*64,'global_ordinal':1,'case_id':'case','candidate_alias':'CANDIDATE-A','raw_output_sha256':'2'*64}
 with pytest.raises(ValueError):client.unsigned_receipt(authority_identity='3'*64,registry_identity='4'*64,packet=packet,role='ADJUDICATOR_A',adjudicator_id='EVALUATOR-A-01',key_sha256='5'*64,verdict='YES')
 old={'schema':'pastila-production-core-v15-r4-semantic-receipt','schema_version':1}
 with pytest.raises(ValueError):client.verify_receipt(old,authority_identity='3'*64,registry_identity='4'*64,packet=packet,registration=('EVALUATOR-A-01','5'*64,b'public','4'*64),openssl=Path('/usr/bin/openssl'))

def test_tampering_and_wrong_pop_fail_closed():
 tampered=bytearray(SIG_A);tampered[0]^=1
 with pytest.raises(ValueError):issuer.verify_pop('ADJUDICATOR_A',bytes(tampered))
 registry,responses,authority,boundary=issuer.build(SIG_A,SIG_B);bad=dict(authority);bad['successor_registry_identity']='0'*64;core=dict(bad);core.pop('rotation_authority_identity');bad['rotation_authority_identity']=identity(core);assert bad['rotation_authority_identity']!=authority['rotation_authority_identity']

def test_successor_resume_progress_hides_verdicts(tmp_path):
 receipts={1:{'receipt_identity':'1'*64,'verdict':'FAIL'}}
 client.write_progress(role='ADJUDICATOR_A',boundary_identity='2'*64,output=tmp_path,receipts=receipts)
 raw=(tmp_path/'progress.json').read_bytes();value=json.loads(raw)
 assert value['completed']==1 and value['verdicts_disclosed'] is False and b'FAIL' not in raw

def test_successor_existing_receipt_rejects_cross_role(tmp_path):
 packet={'packet_identity':'1'*64,'global_ordinal':1,'case_id':'case','candidate_alias':'CANDIDATE-A','raw_output_sha256':'2'*64}
 (tmp_path/'0001.receipt.json').write_bytes(canonical({'global_ordinal':1,'adjudicator_role':'ADJUDICATOR_B'}))
 with pytest.raises(ValueError,match='cross-role'):
  client.existing_receipts(authority_identity='3'*64,registry_identity='4'*64,role='ADJUDICATOR_A',output=tmp_path,packets=[packet],registration=('EVALUATOR-A-01','5'*64,b'public','4'*64),openssl=Path('/usr/bin/openssl'))

def test_executable_route_requires_complete_signed_artifact_root(tmp_path):
 with pytest.raises(ValueError):client.validate_authority(tmp_path,'1'*64,Path('/usr/bin/openssl'))
