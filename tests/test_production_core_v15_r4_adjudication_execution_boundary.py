import base64, copy, hashlib, subprocess
from pathlib import Path
import pytest
import materialize_production_core_v15_r4_adjudication_execution_boundary as issuer
import pastila_scout.production_core_r4_adjudication_execution as contract
from pastila_scout.production_core_r4_adjudication_execution import canonical,custody_manifest,digest,packet_for,unsigned_receipt,verify_receipt

def test_projection_is_exact_and_excludes_failures():
 p=issuer.projection(); assert p['packet_count']==1986; assert p['excluded_structural_failures']==414; assert len(p['packet_inventory_root'])==64
def test_build_is_no_effect_and_bound_to_published_boundary():
 a=issuer.build(); assert a['source_boundary_identity']==issuer.SOURCE_BOUNDARY; assert a['receipt_count_required']==3972; assert not a['real_packets_materialized']; assert not a['real_receipts_created']; assert a['semantic_verdict'] is None; assert not a['promotion']
def test_publication_gate_is_fail_closed():
 head='a'*40
 assert issuer.publication_state(issuer.PUBLISHED,issuer.PUBLISHED)=='LOCAL_BUILD'
 assert issuer.publication_state(head,issuer.PUBLISHED)=='LOCAL_PREPUBLICATION'
 assert issuer.publication_state(head,head)=='PUBLISHED_EXACT_HEAD'
 with pytest.raises(ValueError,match='publication ref drift'): issuer.publication_state(head,'b'*40)
def test_structural_failure_cannot_project():
 row={'structural_status':'FAIL_CLOSED_INVALID_OUTPUT'}
 with pytest.raises(ValueError,match='structural failure'): packet_for(row=row,raw=b'',request={},assertion={})
def test_custody_is_role_and_inventory_bound():
 inv=[{'path':f'packets/{i:04d}.blind.json','sha256':f'{i:064x}'} for i in range(1986)]
 a=custody_manifest('ADJUDICATOR_A','a'*64,inv); b=custody_manifest('ADJUDICATOR_B','a'*64,inv)
 assert a['custody_identity']!=b['custody_identity']; assert not a['candidate_mapping_present']
 with pytest.raises(ValueError): custody_manifest('ADJUDICATOR_A','a'*64,inv[:-1])
def test_receipt_message_binds_every_substitution():
 packet={'packet_identity':'1'*64,'global_ordinal':1,'case_id':'case','candidate_alias':'CANDIDATE-A','raw_output_sha256':'2'*64}
 base=unsigned_receipt(boundary_identity='3'*64,packet=packet,role='ADJUDICATOR_A',adjudicator_id='PERSON-A',key_sha256='4'*64,verdict='PASS')
 for field in ('packet_identity','global_ordinal','case_id','candidate_alias','raw_output_sha256','adjudicator_role','adjudicator_id','adjudicator_key_sha256','verdict'):
  bad=copy.deepcopy(base); bad[field]='x' if field!='global_ordinal' else 2; assert canonical(bad)!=canonical(base)
def test_packet_is_candidate_blinded():
 row={'structural_status':'STRUCTURALLY_VALID_PENDING_ADJUDICATION','global_ordinal':1,'materialization':'A','repetition':1,'candidate_alias':'CANDIDATE-A','case_id':'case','request_identity':'sha256:'+'1'*64,'execution_receipt_identity':'2'*64,'raw_output_sha256':digest(b'{}')}
 request={'case_id':'case','request_identity':row['request_identity']}; assertion={'case_id':'case'}; packet=packet_for(row=row,raw=b'{}',request=request,assertion=assertion); raw=canonical(packet)
 assert b'pastila-editor-core' not in raw and packet['candidate_mapping_present'] is False and packet['private_runtime_observation_present'] is False
def test_incomplete_and_nonindependent_closure_fail_closed(tmp_path):
 packet={'packet_identity':'1'*64}; registrations={'ADJUDICATOR_A':('A','2'*64,b'a'),'ADJUDICATOR_B':('B','3'*64,b'b')}
 with pytest.raises(ValueError,match='complete two-receipt'): contract.verify_complete_closure([],boundary_identity='4'*64,packets=[packet],registrations=registrations,openssl=tmp_path/'openssl')
 duplicate={'ADJUDICATOR_A':('A','2'*64,b'a'),'ADJUDICATOR_B':('A','2'*64,b'a')}
 with pytest.raises(ValueError,match='independent'): contract.verify_complete_closure([],boundary_identity='4'*64,packets=[],registrations=duplicate,openssl=tmp_path/'openssl')
def test_fixture_complete_closure_and_replay_rejection(monkeypatch,tmp_path):
 packets=[{'packet_identity':f'{i:064x}','global_ordinal':i,'case_id':f'case-{i}','candidate_alias':'CANDIDATE-A','raw_output_sha256':'1'*64} for i in range(1,1987)]
 registrations={'ADJUDICATOR_A':('A','2'*64,b'a'),'ADJUDICATOR_B':('B','3'*64,b'b')}
 receipts=[{'packet_identity':p['packet_identity'],'adjudicator_role':role,'verdict':'PASS'} for p in packets for role in contract.ROLES]
 monkeypatch.setattr(contract,'verify_receipt',lambda *args,**kwargs:'verified')
 assert contract.verify_complete_closure(receipts,boundary_identity='4'*64,packets=packets,registrations=registrations,openssl=tmp_path/'openssl')=='COMPLETE_TWO_PERSON_PASS'
 replay=list(receipts); replay[1]=dict(replay[0])
 with pytest.raises(ValueError,match='replay'): contract.verify_complete_closure(replay,boundary_identity='4'*64,packets=packets,registrations=registrations,openssl=tmp_path/'openssl')
def test_real_ed25519_and_wrong_key_rejection(tmp_path):
 openssl=Path('/usr/bin/openssl'); private=tmp_path/'private.pem'; public=tmp_path/'public.pem'; wrong_private=tmp_path/'wrong.pem'; wrong_public=tmp_path/'wrong.pub.pem'
 for priv,pub in ((private,public),(wrong_private,wrong_public)):
  subprocess.run([str(openssl),'genpkey','-algorithm','ED25519','-out',str(priv)],check=True); subprocess.run([str(openssl),'pkey','-in',str(priv),'-pubout','-out',str(pub)],check=True)
 packet={'packet_identity':'1'*64,'global_ordinal':1,'case_id':'case','candidate_alias':'CANDIDATE-A','raw_output_sha256':'2'*64}; key=public.read_bytes(); unsigned=unsigned_receipt(boundary_identity='3'*64,packet=packet,role='ADJUDICATOR_A',adjudicator_id='PERSON-A',key_sha256=digest(key),verdict='PASS'); msg=tmp_path/'msg'; sig=tmp_path/'sig'; msg.write_bytes(canonical(unsigned)); subprocess.run([str(openssl),'pkeyutl','-sign','-inkey',str(private),'-rawin','-in',str(msg),'-out',str(sig)],check=True); signature=sig.read_bytes(); receipt={**unsigned,'signature_base64':base64.b64encode(signature).decode(),'receipt_identity':digest(canonical(unsigned)+signature)}
 assert verify_receipt(receipt,boundary_identity='3'*64,packet=packet,registration=('PERSON-A',digest(key),key),openssl=openssl)==receipt['receipt_identity']
 with pytest.raises(ValueError): verify_receipt(receipt,boundary_identity='3'*64,packet=packet,registration=('PERSON-A',digest(wrong_public.read_bytes()),wrong_public.read_bytes()),openssl=openssl)
