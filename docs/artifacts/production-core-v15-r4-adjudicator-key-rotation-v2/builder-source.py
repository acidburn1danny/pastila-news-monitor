"""Verify two PoPs and issue the signed R4 adjudicator-key successor boundary."""
from __future__ import annotations
import base64,json,subprocess,tempfile
from pathlib import Path
import materialize_production_core_successor_execution_authority_v12 as signing
from pastila_scout.production_core_r4_adjudication_execution import canonical,digest,identity

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs/artifacts/production-core-v15-r4-adjudicator-key-rotation-v2'
CHALLENGES=ROOT/'docs/artifacts/production-core-v15-r4-adjudicator-key-rotation-v2-pop-challenges'
PUBLISHED='7dbdd79c16a40f8df32d02a4d9c129971b1caa06'
OLD_REGISTRY='26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639'
OLD_EXECUTION_BOUNDARY='77fcf784df5faedbda1f34de3e7def2da4ae6553d79de5bd0de839a5d6f8fe30'
OLD_CLIENT_BOUNDARY='6198072dd88e9bb66ba5d545924872e19fb3ae791bbe97676b50ab2a1812770e'
ARTIFACTS=('authority.json','binding.json','binding.sig','boundary.json','builder-source.py','pop-a.json','pop-a.sig','pop-b.json','pop-b.sig','registry.json')
KEYS={
 'ADJUDICATOR_A':{'adjudicator_id':'EVALUATOR-A-01','pem_sha256':'575f281fd695b0a4219b99dd8ebaee6a3e5c7af1e44c47731a54cbbf4797f07b','der_sha256':'92a52413e60c0efed05f11c80d69ef386c96d793d0e80e5cc2e89f6f327ace7c','pem_base64':'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0NCk1Db3dCUVlESzJWd0F5RUFycytha1pVZkh6Q0lIRCtVS1lNRUpMTTM5ZCtvWURCSjd6YzJzV3UwRitFPQ0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tDQo=','challenge_identity':'ce7aaebf755fb0d0865f91ee8e16d4909be677447108477b00df4b7b525422e2','challenge_sha256':'80fb2dd20d4748d125b3268741666d6676b510010d628e6a6b6abc7c57a78ae4','signature_sha256':'a8110a26dc66581693d11995d89ba8b6ce3ebc678c02f79a6204485ce5929acc','proof_identity':'13f36de97478f9ac1b196ff669ebb24c74ad3a2dc56a7d7e96994ef3bbacfd44'},
 'ADJUDICATOR_B':{'adjudicator_id':'EVALUATOR-B-01','pem_sha256':'27a3b1f397f5480767e6c7c26536a3358e05cbb621cb9b5b5c330c2a75683d91','der_sha256':'702619b8009684ff82229dc2498199a13f062675d54e196208f24bab8083f713','pem_base64':'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0NCk1Db3dCUVlESzJWd0F5RUFDdlgyb3hzOE0zSzR4VjNqNXNSc3hZUDVTOWdCdlN5cVRLejkwU1A5ell3PQ0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tDQo=','challenge_identity':'40c5729cb4d5b205589a1d5b7d90a40103fba69d66873d96756d3f31ca635cf4','challenge_sha256':'077e19e0a3cc14ecd04d4a26f8ebe16075449ba1749bb3bec216a0ac79eb2ebe','signature_sha256':'5dd005493af5d51ac77ef19f3b78725927d79f1a60418aa66a73914e465cae09','proof_identity':'f42eb5f7d046c263751c30341cd91fa9a39ba0ad54617d2e512d7140a731f77c'}}
SOURCES=('src/pastila_scout/production_core_r4_adjudicator_client_v2.py','scripts/adjudicate_production_core_v15_r4_v2.py','scripts/materialize_production_core_v15_r4_key_rotation_v2.py','scripts/audit_production_core_v15_r4_key_rotation_v2.py','tests/test_production_core_v15_r4_key_rotation_v2.py','docs/production-core-v15-r4-key-rotation-v2.md','docs/artifacts/production-core-v15-r4-adjudicator-key-rotation-v2-pop-challenges/ADJUDICATOR_A.challenge.json','docs/artifacts/production-core-v15-r4-adjudicator-key-rotation-v2-pop-challenges/ADJUDICATOR_B.challenge.json')

def response(role,signature):
 key=KEYS[role];challenge=(CHALLENGES/f'{role}.challenge.json').read_bytes()
 if digest(challenge)!=key['challenge_sha256'] or digest(signature)!=key['signature_sha256'] or digest(challenge+signature)!=key['proof_identity']:raise ValueError('PoP byte identity mismatch')
 value=json.loads(challenge)
 if value['challenge_identity']!=key['challenge_identity'] or value['public_key_sha256']!=key['pem_sha256']:raise ValueError('PoP challenge substitution')
 return {'schema':'pastila-production-core-v15-r4-adjudicator-key-rotation-pop-response','schema_version':1,'adjudicator_role':role,'adjudicator_id':key['adjudicator_id'],'challenge_identity':key['challenge_identity'],'challenge_sha256':key['challenge_sha256'],'public_key_sha256':key['pem_sha256'],'signature_algorithm':'Ed25519','signature_mode':'RAW_MESSAGE','signature_base64':base64.b64encode(signature).decode(),'signature_sha256':key['signature_sha256'],'proof_identity':key['proof_identity']}

def verify_pop(role,signature,openssl=Path('/usr/bin/openssl')):
 value=response(role,signature);key=KEYS[role]
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);(root/'public.pem').write_bytes(base64.b64decode(key['pem_base64']));(root/'signature').write_bytes(signature)
  run=subprocess.run([str(openssl),'pkeyutl','-verify','-pubin','-inkey',str(root/'public.pem'),'-rawin','-in',str(CHALLENGES/f'{role}.challenge.json'),'-sigfile',str(root/'signature')],capture_output=True)
 if run.returncode:raise ValueError('PoP Ed25519 verification failed')
 return value

def registry_for(responses):
 roles={role:{'adjudicator_id':KEYS[role]['adjudicator_id'],'public_key_format':'PEM_SUBJECT_PUBLIC_KEY_INFO_ED25519_EXACT_BYTES_BASE64','public_key_sha256':KEYS[role]['pem_sha256'],'public_key_der_sha256':KEYS[role]['der_sha256'],'public_key_pem_base64':KEYS[role]['pem_base64'],'proof_identity':responses[role]['proof_identity']} for role in KEYS}
 core={'schema':'pastila-production-core-semantic-adjudicator-public-key-registry','schema_version':2,'status':'OWNER_REGISTERED_PUBLIC_IDENTITIES_ROTATED_WITH_PROOF_OF_POSSESSION','supersedes_registry_identity':OLD_REGISTRY,'roles':roles,'independence_assertion':'OWNER_DESIGNATED_DISTINCT_HUMAN_EVALUATORS_WITH_DISTINCT_PUBLIC_KEYS_AND_VALID_POP','private_key_material_present':False,'candidate_execution_authorized':False,'candidate_promotion_effect':False}
 return {**core,'registry_identity':identity(core)}

def build(sig_a,sig_b):
 responses={'ADJUDICATOR_A':verify_pop('ADJUDICATOR_A',sig_a),'ADJUDICATOR_B':verify_pop('ADJUDICATOR_B',sig_b)};registry=registry_for(responses);sources={name:digest((ROOT/name).read_bytes()) for name in SOURCES}
 acore={'schema':'pastila-production-core-v15-r4-adjudicator-key-rotation-authority','schema_version':2,'status':'SIGNED_SUCCESSOR_NO_RECEIPTS_NO_ADJUDICATION','published_predecessor_commit':PUBLISHED,'supersedes_registry_identity':OLD_REGISTRY,'successor_registry_identity':registry['registry_identity'],'source_adjudication_execution_boundary_identity':OLD_EXECUTION_BOUNDARY,'source_adjudicator_client_boundary_identity':OLD_CLIENT_BOUNDARY,'pop_proof_identities':{r:responses[r]['proof_identity'] for r in responses},'packet_count':1986,'excluded_structural_failures':414,'packet_inventory_root':'bf5bc935db4cb0ccf48d4a880302de8e52a84cf8fe7ca27cb6038f70328c7baf','packet_projection_root':'871f4877a91f8143c497146a28a0d9ff22a38221491bd7c2cf15eb95de9a7e9d','bridge_rule':'IMMUTABLE_V1_PACKET_AND_CUSTODY_EVIDENCE; V2_RECEIPTS_MUST_BIND_THIS_AUTHORITY_AND_V2_REGISTRY','receipts_existing':0,'adjudication_performed':False,'semantic_verdict':None,'promotion':False}
 authority={**acore,'rotation_authority_identity':identity(acore)}
 bcore={'schema':'pastila-production-core-v15-r4-adjudication-successor-boundary','schema_version':2,'status':'SIGNED_NO_RECEIPTS_NO_DECISIONS','rotation_authority_identity':authority['rotation_authority_identity'],'successor_registry_identity':registry['registry_identity'],'supersedes_client_boundary_identity':OLD_CLIENT_BOUNDARY,'source_adjudication_execution_boundary_identity':OLD_EXECUTION_BOUNDARY,'receipt_schema':'pastila-production-core-v15-r4-semantic-receipt/v2','receipt_signed_bindings':['key_rotation_authority_identity','source_packet_registry_identity','adjudicator_registry_identity','packet_identity','global_ordinal','case_id','candidate_alias','raw_output_sha256','adjudicator_role','adjudicator_id','adjudicator_key_sha256','verdict'],'cli':'scripts/adjudicate_production_core_v15_r4_v2.py','roles':{r:{'adjudicator_id':KEYS[r]['adjudicator_id'],'public_key_sha256':KEYS[r]['pem_sha256'],'custody_root':f'/root/pf9-v15-r4-human-adjudication/custody/{r}','receipt_root':f"/root/pf9-v15-r4-adjudicator-{'a' if r.endswith('A') else 'b'}-receipts-v2"} for r in KEYS},'role_closure':1986,'combined_receipt_closure':3972,'source_sha256':sources,'real_receipts_created':False,'adjudication_performed':False,'semantic_verdict':None,'promotion':False,'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256}
 boundary={**bcore,'boundary_identity':identity(bcore)}
 return registry,responses,authority,boundary

def binding_for(registry,authority,boundary,raws):return {'schema':'pastila-production-core-v15-r4-key-rotation-successor-binding','schema_version':2,'algorithm':'Ed25519','registry_identity':registry['registry_identity'],'registry_sha256':digest(raws['registry']),'rotation_authority_identity':authority['rotation_authority_identity'],'authority_sha256':digest(raws['authority']),'boundary_identity':boundary['boundary_identity'],'boundary_sha256':digest(raws['boundary']),'supersedes_registry_identity':OLD_REGISTRY,'published_predecessor_commit':PUBLISHED,'source_sha256':boundary['source_sha256'],'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256,'adjudication_performed':False,'promotion':False}

def materialize(key,sig_a_path,sig_b_path):
 if OUTPUT.exists():raise ValueError('rotation output exists')
 signing.verify_key(key);sig_a=sig_a_path.read_bytes();sig_b=sig_b_path.read_bytes();registry,responses,authority,boundary=build(sig_a,sig_b);raws={n:canonical(v) for n,v in [('registry',registry),('authority',authority),('boundary',boundary)]};binding=canonical(binding_for(registry,authority,boundary,raws))
 with tempfile.TemporaryDirectory(prefix='.r4-key-rotation-',dir=OUTPUT.parent) as folder:
  stage=Path(folder)/'payload';stage.mkdir();(stage/'registry.json').write_bytes(raws['registry']);(stage/'authority.json').write_bytes(raws['authority']);(stage/'boundary.json').write_bytes(raws['boundary']);(stage/'binding.json').write_bytes(binding);(stage/'pop-a.json').write_bytes(canonical(responses['ADJUDICATOR_A']));(stage/'pop-b.json').write_bytes(canonical(responses['ADJUDICATOR_B']));(stage/'pop-a.sig').write_bytes(sig_a);(stage/'pop-b.sig').write_bytes(sig_b);(stage/'builder-source.py').write_bytes(Path(__file__).read_bytes());subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(key),'-rawin','-in',str(stage/'binding.json'),'-out',str(stage/'binding.sig')],check=True);subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(stage/'binding.json'),'-sigfile',str(stage/'binding.sig')],check=True,capture_output=True);stage.rename(OUTPUT)
 return {'registry_identity':registry['registry_identity'],'rotation_authority_identity':authority['rotation_authority_identity'],'boundary_identity':boundary['boundary_identity'],'binding_identity':digest(binding),'signature_identity':digest((OUTPUT/'binding.sig').read_bytes())}
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--private-key',type=Path,required=True);p.add_argument('--pop-a-signature',type=Path,required=True);p.add_argument('--pop-b-signature',type=Path,required=True);o=p.parse_args();print(json.dumps(materialize(o.private_key,o.pop_a_signature,o.pop_b_signature),sort_keys=True))
