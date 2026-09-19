"""Successor R4 adjudicator client after two-person Ed25519 key rotation."""
from __future__ import annotations
import base64, json, os, subprocess, tempfile
from pathlib import Path
from typing import Callable, Mapping
from pastila_scout.production_core_r4_adjudication_execution import canonical,digest,identity
import pastila_scout.production_core_r4_adjudicator_client as v1

VERDICTS=("PASS","FAIL","INDETERMINATE")
SOURCE_REGISTRY="26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
ROLE_CONTRACT={
 "ADJUDICATOR_A":{"adjudicator_id":"EVALUATOR-A-01","key_sha256":"575f281fd695b0a4219b99dd8ebaee6a3e5c7af1e44c47731a54cbbf4797f07b","custody":v1.RUNTIME_ROOT/'custody/ADJUDICATOR_A',"receipts":Path('/root/pf9-v15-r4-adjudicator-a-receipts-v2')},
 "ADJUDICATOR_B":{"adjudicator_id":"EVALUATOR-B-01","key_sha256":"27a3b1f397f5480767e6c7c26536a3358e05cbb621cb9b5b5c330c2a75683d91","custody":v1.RUNTIME_ROOT/'custody/ADJUDICATOR_B',"receipts":Path('/root/pf9-v15-r4-adjudicator-b-receipts-v2')}}
PROJECT_PUBLIC_KEY=Path(__file__).resolve().parents[2]/'docs/artifacts/production-core-v8-1-signing-public.pem'
PROJECT_PUBLIC_KEY_SHA256='29616718e9d17a3c88f630af52fee0ef7a9dc7adc519412c4870f06b63ca1cca'

def load_canonical(path:Path)->dict:
 try:raw=path.read_bytes();value=json.loads(raw)
 except (OSError,ValueError,TypeError) as exc:raise ValueError('unavailable or invalid canonical input') from exc
 if path.is_symlink() or not path.is_file() or canonical(value)!=raw:raise ValueError('noncanonical or nonregular input')
 return value

def registry_registration(role:str,registry_path:Path)->tuple[str,str,bytes,str]:
 value=load_canonical(registry_path);core=dict(value);claimed=core.pop('registry_identity',None)
 if claimed!=identity(core) or value.get('supersedes_registry_identity')!=SOURCE_REGISTRY or set(value.get('roles',{}))!=set(ROLE_CONTRACT):raise ValueError('successor registry substitution')
 item=value['roles'][role];expected=ROLE_CONTRACT[role];public=base64.b64decode(item['public_key_pem_base64'],validate=True)
 if item['adjudicator_id']!=expected['adjudicator_id'] or item['public_key_sha256']!=expected['key_sha256'] or digest(public)!=expected['key_sha256']:raise ValueError('rotated registration substitution')
 return item['adjudicator_id'],item['public_key_sha256'],public,claimed

def validate_authority(artifact_root:Path,registry_identity:str,openssl:Path)->tuple[str,str]:
 if artifact_root.is_symlink() or not artifact_root.is_dir():raise ValueError('rotation artifact root invalid')
 authority_path=artifact_root/'authority.json';boundary_path=artifact_root/'boundary.json';registry_path=artifact_root/'registry.json';binding_path=artifact_root/'binding.json';signature_path=artifact_root/'binding.sig'
 authority=load_canonical(authority_path);acore=dict(authority);aid=acore.pop('rotation_authority_identity',None);boundary=load_canonical(boundary_path);bcore=dict(boundary);bid=bcore.pop('boundary_identity',None);binding=load_canonical(binding_path)
 if aid!=identity(acore) or bid!=identity(bcore) or boundary.get('rotation_authority_identity')!=aid or authority.get('successor_registry_identity')!=registry_identity or boundary.get('successor_registry_identity')!=registry_identity:raise ValueError('rotation authority/boundary substitution')
 if binding.get('registry_identity')!=registry_identity or binding.get('registry_sha256')!=digest(registry_path.read_bytes()) or binding.get('rotation_authority_identity')!=aid or binding.get('authority_sha256')!=digest(authority_path.read_bytes()) or binding.get('boundary_identity')!=bid or binding.get('boundary_sha256')!=digest(boundary_path.read_bytes()) or binding.get('public_key_pem_sha256')!=PROJECT_PUBLIC_KEY_SHA256:raise ValueError('signed rotation binding substitution')
 if digest(Path(__file__).read_bytes())!=boundary['source_sha256']['src/pastila_scout/production_core_r4_adjudicator_client_v2.py'] or digest(PROJECT_PUBLIC_KEY.read_bytes().replace(b'\r\n',b'\n'))!=PROJECT_PUBLIC_KEY_SHA256:raise ValueError('client source or project public key drift')
 run=subprocess.run([str(openssl),'pkeyutl','-verify','-pubin','-inkey',str(PROJECT_PUBLIC_KEY),'-rawin','-in',str(binding_path),'-sigfile',str(signature_path)],capture_output=True)
 if run.returncode:raise ValueError('rotation binding Ed25519 verification failed')
 return aid,bid

def unsigned_receipt(*,authority_identity:str,registry_identity:str,packet:Mapping[str,object],role:str,adjudicator_id:str,key_sha256:str,verdict:str)->dict:
 if role not in ROLE_CONTRACT or verdict not in VERDICTS:raise ValueError('receipt authority invalid')
 return {'schema':'pastila-production-core-v15-r4-semantic-receipt','schema_version':2,'key_rotation_authority_identity':authority_identity,'source_packet_registry_identity':SOURCE_REGISTRY,'adjudicator_registry_identity':registry_identity,'packet_identity':packet['packet_identity'],'global_ordinal':packet['global_ordinal'],'case_id':packet['case_id'],'candidate_alias':packet['candidate_alias'],'raw_output_sha256':packet['raw_output_sha256'],'adjudicator_role':role,'adjudicator_id':adjudicator_id,'adjudicator_key_sha256':key_sha256,'verdict':verdict}

def verify_receipt(receipt:Mapping[str,object],*,authority_identity:str,registry_identity:str,packet:Mapping[str,object],registration:tuple[str,str,bytes,str],openssl:Path)->str:
 item=dict(receipt);signature_text=item.pop('signature_base64',None);claimed=item.pop('receipt_identity',None)
 expected=unsigned_receipt(authority_identity=authority_identity,registry_identity=registry_identity,packet=packet,role=str(item.get('adjudicator_role')),adjudicator_id=registration[0],key_sha256=registration[1],verdict=str(item.get('verdict')))
 if item!=expected or not isinstance(signature_text,str):raise ValueError('successor receipt substitution')
 signature=base64.b64decode(signature_text,validate=True);message=canonical(expected)
 if len(signature)!=64 or claimed!=digest(message+signature):raise ValueError('successor receipt identity invalid')
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);(root/'message').write_bytes(message);(root/'signature').write_bytes(signature);(root/'public.pem').write_bytes(registration[2])
  run=subprocess.run([str(openssl),'pkeyutl','-verify','-pubin','-inkey',str(root/'public.pem'),'-rawin','-in',str(root/'message'),'-sigfile',str(root/'signature')],capture_output=True)
 if run.returncode:raise ValueError('successor receipt Ed25519 verification failed')
 return str(claimed)

def validate_output(role:str,root:Path)->None:
 if root.resolve()!=ROLE_CONTRACT[role]['receipts'].resolve():raise ValueError('cross-role output substitution')
 root.mkdir(mode=0o700,parents=False,exist_ok=True)
 if root.is_symlink() or root.stat().st_mode&0o077:raise ValueError('receipt output permissions invalid')

def sign_receipt(*,authority_identity:str,registry_identity:str,role:str,packet:Mapping[str,object],verdict:str,private_key:Path,output:Path,registration:tuple[str,str,bytes,str],openssl:Path)->dict:
 unsigned=unsigned_receipt(authority_identity=authority_identity,registry_identity=registry_identity,packet=packet,role=role,adjudicator_id=registration[0],key_sha256=registration[1],verdict=verdict);message=canonical(unsigned)
 with tempfile.TemporaryDirectory(dir=output,prefix='.signing-') as folder:
  root=Path(folder);(root/'message').write_bytes(message);subprocess.run([str(openssl),'pkeyutl','-sign','-inkey',str(private_key),'-rawin','-in',str(root/'message'),'-out',str(root/'signature')],check=True,capture_output=True);signature=(root/'signature').read_bytes()
 receipt={**unsigned,'signature_base64':base64.b64encode(signature).decode(),'receipt_identity':digest(message+signature)}
 verify_receipt(receipt,authority_identity=authority_identity,registry_identity=registry_identity,packet=packet,registration=registration,openssl=openssl)
 target=output/f"{int(packet['global_ordinal']):04d}.receipt.json";descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
 with os.fdopen(descriptor,'wb') as stream:stream.write(canonical(receipt));stream.flush();os.fsync(stream.fileno())
 return receipt

def existing_receipts(*,authority_identity:str,registry_identity:str,role:str,output:Path,packets:list[dict],registration:tuple[str,str,bytes,str],openssl:Path)->dict[int,dict]:
 packet_by_ordinal={int(packet['global_ordinal']):packet for packet in packets};found={}
 for path in sorted(output.glob('*.receipt.json')):
  receipt=load_canonical(path);ordinal=int(receipt.get('global_ordinal',-1))
  if ordinal not in packet_by_ordinal or ordinal in found or path.name!=f'{ordinal:04d}.receipt.json' or receipt.get('adjudicator_role')!=role:raise ValueError('replayed, cross-row, or cross-role successor receipt')
  verify_receipt(receipt,authority_identity=authority_identity,registry_identity=registry_identity,packet=packet_by_ordinal[ordinal],registration=registration,openssl=openssl);found[ordinal]=receipt
 return found

def write_progress(*,role:str,boundary_identity:str,output:Path,receipts:Mapping[int,dict])->None:
 core={'schema':'pastila-production-core-v15-r4-adjudicator-progress','schema_version':2,'boundary_identity':boundary_identity,'adjudicator_role':role,'completed':len(receipts),'required':v1.PACKET_COUNT,'receipt_identities':[receipts[key]['receipt_identity'] for key in sorted(receipts)],'verdicts_disclosed':False};value={**core,'progress_identity':identity(core)};temporary=output/'.progress.json.tmp';temporary.write_bytes(canonical(value));os.chmod(temporary,0o400);os.replace(temporary,output/'progress.json')

def run_session(*,role:str,custody_root:Path,output_root:Path,private_key:Path,artifact_root:Path,openssl:Path,decide:Callable[[Mapping[str,object]],str])->dict:
 registry_path=artifact_root/'registry.json';registration=registry_registration(role,registry_path);aid,bid=validate_authority(artifact_root,registration[3],openssl);packets=v1.validate_custody(role,custody_root);validate_output(role,output_root);v1.verify_private_key_path(private_key,(registration[0],registration[1],registration[2]),openssl,(custody_root,output_root,artifact_root))
 receipts=existing_receipts(authority_identity=aid,registry_identity=registration[3],role=role,output=output_root,packets=packets,registration=registration,openssl=openssl)
 for packet in packets:
  ordinal=int(packet['global_ordinal'])
  if ordinal in receipts:continue
  receipts[ordinal]=sign_receipt(authority_identity=aid,registry_identity=registration[3],role=role,packet=packet,verdict=decide(packet),private_key=private_key,output=output_root,registration=registration,openssl=openssl);write_progress(role=role,boundary_identity=bid,output=output_root,receipts=receipts)
 if len(receipts)!=v1.PACKET_COUNT:raise ValueError('incomplete successor role closure')
 return {'role':role,'receipts':len(receipts),'boundary_identity':bid,'closure':'COMPLETE_ROLE_CLOSURE'}
