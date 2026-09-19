"""Build and sign the R4 human-adjudicator client boundary."""
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path
import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_adjudication_execution_boundary as source
from pastila_scout.production_core_r4_adjudication_execution import canonical, digest, identity
from pastila_scout.production_core_r4_adjudicator_client import ROLE_CONTRACT

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs/artifacts/production-core-v15-r4-adjudicator-client-boundary'
PUBLISHED='e3242946ac81ad0e988a703a6b62007e0c594db4'
SOURCE_BOUNDARY='77fcf784df5faedbda1f34de3e7def2da4ae6553d79de5bd0de839a5d6f8fe30'
ARTIFACTS=('boundary.json','binding.json','binding.sig','builder-source.py')
SOURCES=(
 'src/pastila_scout/production_core_r4_adjudicator_client.py',
 'scripts/adjudicate_production_core_v15_r4.py',
 'scripts/materialize_production_core_v15_r4_adjudicator_client_boundary.py',
 'scripts/audit_production_core_v15_r4_adjudicator_client_boundary.py',
 'tests/test_production_core_v15_r4_adjudicator_client.py',
 'docs/production-core-v15-r4-adjudicator-client.md')

def publication_state(head,remote):
 if head==PUBLISHED and remote==PUBLISHED:return 'SOURCE_PUBLISHED_LOCAL_BUILD'
 if remote==PUBLISHED:return 'LOCAL_PREPUBLICATION'
 if remote==head:return 'PUBLISHED_EXACT_HEAD'
 raise ValueError('adjudicator-client publication ref drift')

def build():
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(); remote=subprocess.check_output(['git','rev-parse','@{upstream}'],cwd=ROOT,text=True).strip()
 if subprocess.run(['git','merge-base','--is-ancestor',PUBLISHED,head],cwd=ROOT).returncode:raise ValueError('published source is not ancestor')
 state=publication_state(head,remote)
 source_value=json.loads((source.OUTPUT/'boundary.json').read_bytes())
 if source_value['boundary_identity']!=SOURCE_BOUNDARY:raise ValueError('source boundary substitution')
 sources={name:digest((ROOT/name).read_bytes()) for name in SOURCES}
 if state=='PUBLISHED_EXACT_HEAD':
  for name,expected in sources.items():
   if digest(subprocess.check_output(['git','show',f'{head}:{name}'],cwd=ROOT))!=expected:raise ValueError(f'published source drift: {name}')
 roles={role:{'adjudicator_id':value['adjudicator_id'],'registered_public_key_sha256':value['key_sha256'],'custody_root':str(value['custody']),'receipt_root':str(value['receipts'])} for role,value in ROLE_CONTRACT.items()}
 core={'schema':'pastila-production-core-v15-r4-adjudicator-client-boundary','schema_version':1,'status':'SIGNED_NO_KEYS_NO_RECEIPTS_NO_DECISIONS','published_source_commit':PUBLISHED,'source_boundary_identity':SOURCE_BOUNDARY,'packet_count':1986,'excluded_structural_failures':414,'packet_inventory_root':'bf5bc935db4cb0ccf48d4a880302de8e52a84cf8fe7ca27cb6038f70328c7baf','packet_projection_root':'871f4877a91f8143c497146a28a0d9ff22a38221491bd7c2cf15eb95de9a7e9d','roles':roles,'cli':'scripts/adjudicate_production_core_v15_r4.py','private_key_interface':'REQUIRED_EXTERNAL_PATH; NO_DEFAULT; NO_DISCOVERY; NO_GENERATION; OPENSSL_ONLY','verdicts':['PASS','FAIL','INDETERMINATE'],'signing':'ED25519_RAW_MESSAGE_CANONICAL_UNSIGNED_RECEIPT','receipt_identity':'SHA256(CANONICAL_UNSIGNED_RECEIPT || RAW_64_BYTE_SIGNATURE)','write_semantics':'ATOMIC_CREATE_NO_CLOBBER; VERIFIED_BEFORE_COMMIT','resume_semantics':'VERIFY_ALL_OWN_ROLE_RECEIPTS; RESUME_FIRST_MISSING; NO_OTHER_ROLE_ACCESS','role_closure':1986,'semantic_verdict':None,'promotion':False,'real_keys_accessed':False,'real_receipts_created':False,'source_sha256':sources,'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256}
 return {**core,'boundary_identity':identity(core)}

def binding_for(value,raw):return {'schema':'pastila-production-core-v15-r4-adjudicator-client-binding','schema_version':1,'algorithm':'Ed25519','boundary_identity':value['boundary_identity'],'boundary_sha256':digest(raw),'published_source_commit':PUBLISHED,'source_boundary_identity':SOURCE_BOUNDARY,'client_source_sha256':value['source_sha256']['src/pastila_scout/production_core_r4_adjudicator_client.py'],'cli_source_sha256':value['source_sha256']['scripts/adjudicate_production_core_v15_r4.py'],'source_sha256':value['source_sha256'],'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256,'semantic_verdict':None,'promotion':False}

def materialize(key):
 if OUTPUT.exists():raise ValueError('client boundary already exists')
 signing.verify_key(key); value=build(); raw=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'; binding=canonical(binding_for(value,raw))
 with tempfile.TemporaryDirectory(prefix='.r4-adjudicator-client-',dir=OUTPUT.parent) as folder:
  stage=Path(folder)/'payload';stage.mkdir();(stage/'boundary.json').write_bytes(raw);(stage/'binding.json').write_bytes(binding);(stage/'builder-source.py').write_bytes(Path(__file__).read_bytes())
  subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(key),'-rawin','-in',str(stage/'binding.json'),'-out',str(stage/'binding.sig')],check=True)
  subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(stage/'binding.json'),'-sigfile',str(stage/'binding.sig')],check=True,capture_output=True);stage.rename(OUTPUT)
 return {'boundary_identity':value['boundary_identity'],'binding_identity':digest(binding),'signature_identity':digest((OUTPUT/'binding.sig').read_bytes())}
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--private-key',type=Path,required=True);print(json.dumps(materialize(p.parse_args().private_key),sort_keys=True))
