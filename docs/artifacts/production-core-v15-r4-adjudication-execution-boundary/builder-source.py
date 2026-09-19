"""Build and sign the R4 adjudication-execution contract without exporting packets."""

from __future__ import annotations
import hashlib, json, subprocess, tempfile
from pathlib import Path
import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_readonly_adjudication_boundary as source
from pastila_scout.production_core_r4_adjudication_execution import canonical, digest, identity, packet_for

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs/artifacts/production-core-v15-r4-adjudication-execution-boundary'
PUBLISHED='b0e34239e1f03b7b98d7e85feed57b0a6c910596'
SOURCE_BOUNDARY='6b2c55935999aaf6da077c0dddd9289f3eec059665d9e361c93cad40aa67568e'
R4_OUTPUT=Path('/root/pf9-v15-r4-preconsumption-output')
ARTIFACTS=('boundary.json','binding.json','binding.sig','builder-source.py')
SOURCES=(
 'src/pastila_scout/production_core_r4_adjudication_execution.py',
 'scripts/materialize_production_core_v15_r4_adjudication_execution_boundary.py',
 'scripts/audit_production_core_v15_r4_adjudication_execution_boundary.py',
 'tests/test_production_core_v15_r4_adjudication_execution_boundary.py',
 'docs/production-core-v15-r4-adjudication-execution-boundary.md')

def publication_state(head,remote):
 if head==PUBLISHED: return 'LOCAL_BUILD'
 if remote==PUBLISHED: return 'LOCAL_PREPUBLICATION'
 if remote==head: return 'PUBLISHED_EXACT_HEAD'
 raise ValueError('adjudication-execution publication ref drift')

def projection():
 generation=json.loads((ROOT/'docs/artifacts/production-core-successor-comparative-qualification-generation-v13.json').read_bytes())
 manifest=json.loads((ROOT/'docs/artifacts/production-core-candidate-request-manifest-v2.json').read_bytes())
 assertions=json.loads((ROOT/'docs/artifacts/production-core-qualification-assertions-v2.json').read_bytes())
 requests={r['case_id']:r for r in manifest['requests']}; asserted={a['case_id']:a for a in assertions['assertions']}
 completion=json.loads((R4_OUTPUT/'completion.json').read_bytes()); inventory={r['path']:r['sha256'] for r in completion['artifact_inventory']}
 packets=[]
 for row in generation['schedule']:
  directory=f"materialization-{row['materialization']}/repetition-{row['repetition']}/{row['candidate_alias']}"
  matches=[p for p in inventory if p.startswith(f"{directory}/{row['case_id']}.") and p.endswith('.receipt.json')]
  if len(matches)!=1: raise ValueError('R4 receipt projection mismatch')
  receipt=json.loads((R4_OUTPUT/matches[0]).read_bytes())
  if receipt['structural_status']=='FAIL_CLOSED_INVALID_OUTPUT': continue
  if receipt['structural_status']!='STRUCTURALLY_VALID_PENDING_ADJUDICATION': raise ValueError('unknown structural state')
  stem=matches[0].removeprefix(directory+'/').removesuffix('.receipt.json'); raw=(R4_OUTPUT/directory/'results'/f'{stem}.raw').read_bytes()
  compact={k:receipt[k] for k in ('global_ordinal','materialization','repetition','candidate_alias','case_id','request_identity','structural_status','raw_output_sha256')}
  compact['execution_receipt_identity']=receipt['receipt_identity']
  packet=packet_for(row=compact,raw=raw,request=requests[row['case_id']],assertion=asserted[row['case_id']]); path=f"packets/{row['global_ordinal']:04d}.blind.json"
  packets.append((path,packet))
 if len(packets)!=1986: raise ValueError('eligible packet count mismatch')
 inventory_rows=[{'path':p,'sha256':digest(canonical(v))} for p,v in packets]
 return {'packet_count':1986,'excluded_structural_failures':414,'packet_inventory_root':identity(inventory_rows),'packet_projection_root':identity([v for _,v in packets])}

def build():
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(); remote=subprocess.check_output(['git','rev-parse','@{upstream}'],cwd=ROOT,text=True).strip()
 if subprocess.run(['git','merge-base','--is-ancestor',PUBLISHED,head],cwd=ROOT).returncode: raise ValueError('published source boundary is not an ancestor')
 descendants=subprocess.check_output(['git','rev-list','--reverse','--parents',f'{PUBLISHED}..{head}'],cwd=ROOT,text=True).splitlines()
 if head!=PUBLISHED and (not descendants or any(len(r.split())!=2 for r in descendants) or descendants[0].split()[1]!=PUBLISHED or descendants[-1].split()[0]!=head): raise ValueError('adjudication-execution history is not linear')
 state=publication_state(head,remote)
 source_boundary=json.loads((source.OUTPUT/'boundary.json').read_bytes())
 if source_boundary['boundary_identity']!=SOURCE_BOUNDARY: raise ValueError('source boundary substitution')
 sources={p:digest((ROOT/p).read_bytes()) for p in SOURCES}; projected=projection()
 if state=='PUBLISHED_EXACT_HEAD':
  for name,expected in sources.items():
   if digest(subprocess.check_output(['git','show',f'{head}:{name}'],cwd=ROOT))!=expected: raise ValueError(f'published source drift: {name}')
 registry=json.loads((ROOT/'docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json').read_bytes())
 core={'schema':'pastila-production-core-v15-r4-adjudication-execution-boundary','schema_version':1,'status':'SIGNED_NO_PACKETS_NO_RECEIPTS_NO_VERDICT',
 'published_source_commit':PUBLISHED,'publication_gate':'LINEAR_SUCCESSOR; REMOTE_IS_BASE_PREPUBLICATION_OR_EXACT_HEAD_POSTPUBLICATION','source_boundary_identity':SOURCE_BOUNDARY,'projection':projected,
 'packet_schema':'pastila-production-core-v15-r4-blind-adjudication-packet/v1','custody_schema':'pastila-production-core-v15-r4-adjudication-custody/v1',
 'receipt_schema':'pastila-production-core-v15-r4-semantic-receipt/v1','receipt_count_required':3972,'receipts_per_packet':2,
 'roles':list(registry['roles']),'registry_identity':registry['registry_identity'],'registry_sha256':digest((ROOT/'docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json').read_bytes()),
 'closure_rule':'EXACTLY_ONE_VALID_ED25519_RECEIPT_PER_PACKET_PER_DISTINCT_REGISTERED_ROLE; ALL_1986_PAIRS_REQUIRED; OTHERWISE_FAIL_CLOSED',
 'real_packets_materialized':False,'real_receipts_created':False,'adjudication_performed':False,'semantic_verdict':None,'promotion':False,
 'source_sha256':sources,'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256}
 return {**core,'boundary_identity':identity(core)}

def binding_for(a,raw): return {'schema':'pastila-production-core-v15-r4-adjudication-execution-binding','schema_version':1,'algorithm':'Ed25519','boundary_identity':a['boundary_identity'],'boundary_sha256':digest(raw),'published_source_commit':PUBLISHED,'source_boundary_identity':SOURCE_BOUNDARY,'packet_inventory_root':a['projection']['packet_inventory_root'],'source_sha256':a['source_sha256'],'public_key_pem_sha256':signing.PUBLIC_PEM_SHA256,'adjudication_performed':False,'promotion':False}
def materialize(key):
 if OUTPUT.exists(): raise ValueError('boundary already exists')
 signing.verify_key(key); a=build(); raw=json.dumps(a,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'; bound=canonical(binding_for(a,raw))
 with tempfile.TemporaryDirectory(prefix='.r4-adj-exec-',dir=OUTPUT.parent) as t:
  s=Path(t)/'payload'; s.mkdir(); (s/'boundary.json').write_bytes(raw); (s/'binding.json').write_bytes(bound); (s/'builder-source.py').write_bytes(Path(__file__).read_bytes())
  subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(key),'-rawin','-in',str(s/'binding.json'),'-out',str(s/'binding.sig')],check=True)
  subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(s/'binding.json'),'-sigfile',str(s/'binding.sig')],check=True,capture_output=True); s.rename(OUTPUT)
 return {'boundary_identity':a['boundary_identity'],'binding_identity':digest(bound),'signature_identity':digest((OUTPUT/'binding.sig').read_bytes())}
if __name__=='__main__':
 import argparse; p=argparse.ArgumentParser(); p.add_argument('--private-key',type=Path,required=True); print(json.dumps(materialize(p.parse_args().private_key),sort_keys=True))
