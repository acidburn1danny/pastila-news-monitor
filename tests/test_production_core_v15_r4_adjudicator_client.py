import base64,copy,json,os
from pathlib import Path
import pytest
import pastila_scout.production_core_r4_adjudicator_client as client
from pastila_scout.production_core_r4_adjudication_execution import canonical,digest,identity

def packet(ordinal=1):
 core={'schema':'pastila-production-core-v15-r4-blind-adjudication-packet','schema_version':1,'source_boundary_identity':'6b2c55935999aaf6da077c0dddd9289f3eec059665d9e361c93cad40aa67568e','global_ordinal':ordinal,'materialization':'A','repetition':1,'candidate_alias':'CANDIDATE-A','case_id':f'case-{ordinal}','request_identity':'r','execution_receipt_identity':'e','raw_output_sha256':digest(b'out'),'raw_output_base64':base64.b64encode(b'out').decode(),'request':{},'assertion':{},'rubric_identity':'x','adjudicator_registry_identity':'26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639','candidate_mapping_present':False,'private_runtime_observation_present':False}
 return {**core,'packet_identity':identity(core)}

def test_role_contract_is_separate_and_has_no_private_paths():
 a,b=client.ROLE_CONTRACT.values();assert a['custody']!=b['custody'];assert a['receipts']!=b['receipts'];assert a['key_sha256']!=b['key_sha256'];assert all('private' not in key for value in client.ROLE_CONTRACT.values() for key in value)

def test_invalid_verdict_and_no_clobber(tmp_path,monkeypatch):
 with pytest.raises(ValueError,match='invalid verdict'):client.sign_receipt(role='ADJUDICATOR_A',packet=packet(),verdict='YES',private_key=tmp_path/'k',output_root=tmp_path,registration=('A','1'*64,b'x'),openssl=tmp_path/'openssl')
 target=tmp_path/'0001.receipt.json';target.write_bytes(b'kept')
 with pytest.raises(FileExistsError):client._write_no_clobber(target,b'new')
 assert target.read_bytes()==b'kept'

def test_output_cross_role_and_permissions_fail_closed(tmp_path,monkeypatch):
 monkeypatch.setitem(client.ROLE_CONTRACT['ADJUDICATOR_A'],'receipts',tmp_path/'A')
 with pytest.raises(ValueError,match='noncanonical'):client.validate_output_root('ADJUDICATOR_A',tmp_path/'B')
 (tmp_path/'A').mkdir(mode=0o755);os.chmod(tmp_path/'A',0o755)
 with pytest.raises(ValueError,match='permissions'):client.validate_output_root('ADJUDICATOR_A',tmp_path/'A')

def test_wrong_key_rejected_without_reading_private_bytes(tmp_path,monkeypatch):
 key=tmp_path/'key.pem';key.write_text('opaque');outside=tmp_path/'outside';outside.mkdir()
 monkeypatch.setattr(client.subprocess,'check_output',lambda *a,**k:b'wrong')
 monkeypatch.setattr(client,'_public_der',lambda *a:b'right')
 with pytest.raises(ValueError,match='does not match'):client.verify_private_key_path(key,('A','1'*64,b'pub'),tmp_path/'openssl',(outside,))

def test_existing_receipts_reject_cross_role_replay_and_modified_packet(tmp_path,monkeypatch):
 p=packet();bad=copy.deepcopy(p);bad['raw_output_sha256']='0'*64
 assert bad['packet_identity']!=identity({k:v for k,v in bad.items() if k!='packet_identity'})
 receipt={'global_ordinal':1,'adjudicator_role':'ADJUDICATOR_B'};(tmp_path/'0001.receipt.json').write_bytes(canonical(receipt))
 with pytest.raises(ValueError,match='cross-role'):client.existing_receipts(role='ADJUDICATOR_A',output_root=tmp_path,packets=[p],registration=('A','1'*64,b'p'),openssl=tmp_path/'openssl')

def test_progress_has_no_verdict_and_resume_uses_receipts(tmp_path):
 os.chmod(tmp_path,0o700);receipts={1:{'receipt_identity':'1'*64,'verdict':'FAIL'}};client.write_progress('ADJUDICATOR_A',tmp_path,receipts);value=json.loads((tmp_path/'progress.json').read_bytes());assert value['completed']==1;assert value['verdicts_disclosed'] is False;assert 'FAIL' not in (tmp_path/'progress.json').read_text()

def test_incomplete_closure_and_interruption_do_not_claim_complete(tmp_path,monkeypatch):
 monkeypatch.setattr(client,'PACKET_COUNT',2);monkeypatch.setattr(client,'registry_registration',lambda *a:('A','1'*64,b'p'));monkeypatch.setattr(client,'validate_custody',lambda *a:[packet(1),packet(2)]);monkeypatch.setattr(client,'validate_output_root',lambda *a:None);monkeypatch.setattr(client,'verify_private_key_path',lambda *a:None);monkeypatch.setattr(client,'existing_receipts',lambda **k:{});calls=[]
 def interrupted(**kwargs):calls.append(1);raise KeyboardInterrupt
 monkeypatch.setattr(client,'sign_receipt',interrupted)
 with pytest.raises(KeyboardInterrupt):client.run_session(role='ADJUDICATOR_A',custody_root=tmp_path,output_root=tmp_path,private_key=tmp_path/'k',registry_path=tmp_path/'r',openssl=tmp_path/'o',decide=lambda p:'PASS')
 assert len(calls)==1

def test_boundary_build_and_publication_fail_closed():
 import materialize_production_core_v15_r4_adjudicator_client_boundary as issuer
 value=issuer.build();assert value['packet_count']==1986;assert value['real_keys_accessed'] is False;assert value['real_receipts_created'] is False
 with pytest.raises(ValueError):issuer.publication_state('a'*40,'b'*40)
