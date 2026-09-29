#!/usr/bin/env python3
import argparse,hashlib,json,os,tempfile
from pathlib import Path
from preflight_vnext_active_integration_candidate_v1 import file_hash,identity,verify
ACTIVE='2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6'
def rollback(old,new):
 with tempfile.TemporaryDirectory(prefix='vnext-proof-') as d:
  r=Path(d);c=r/'current';s=r/'staged';b=r/'backup';c.mkdir();s.mkdir();(c/'lock').write_bytes(old);(s/'lock').write_bytes(new)
  oh=file_hash(c/'lock');nh=file_hash(s/'lock');os.replace(c,b);os.replace(s,c)
  assert file_hash(c/'lock')==nh;os.replace(c,s);os.replace(b,c);assert file_hash(c/'lock')==oh
  return {'status':'PASS','old_lock_sha256':oh,'candidate_lock_sha256':nh,'rollback_byte_exact':True}
def audit(repo,candidate,active):
 p=verify(candidate,full_platform_hash=True);new=(candidate/'manifest/product-lock.json').read_bytes()
 assert new==(repo/'docs/artifacts/vnext-active-integration-product-lock-candidate-v1.json').read_bytes()
 old=(active/'product-lock.json').read_bytes();assert hashlib.sha256(old).hexdigest()==ACTIVE
 r={'status':'PASS','candidate_product_lock_identity':p['product_lock_identity'],'active_product_lock_sha256':ACTIVE,'dependency_closure':'PASS','rollback':rollback(old,new),'active_product_root_mutated':False,'product_lock_replaced':False,'legacy_dependency_count':0}
 r['audit_identity']=identity(r);return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--active-root',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.repo.resolve(),a.candidate.resolve(),a.active_root.resolve()),sort_keys=True))
