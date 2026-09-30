#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
def ident(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def run(root,args):return subprocess.run([str(root/'platform/python-ml/bin/python'),*map(str,args)],text=True,capture_output=True,env={'PATH':'/usr/bin:/bin:/usr/lib/wsl/lib','PYTHONDONTWRITEBYTECODE':'1'})
def main(root):
 pre=root/'app/cli/preflight.py';acc=root/'app/cli/acceptance.py';lock=root/'product-lock.json';graph=root/'manifest/authorities/vnext-active-product-dependency-graph-v3.json';cfg=root/'config/sources.json';aud=root/'app/cli/audit.py'; checks=[]
 def mutate(name,path,fn,cmd=None):
  old=path.read_bytes()
  try:
   fn(path)
   r=run(root,cmd or [pre,'--root',root,'--skip-platform-hash','--skip-host'])
   if r.returncode==0:raise RuntimeError(name+' did not fail closed')
   checks.append(name)
  finally:path.write_bytes(old)
 mutate('LOCK_STATE',lock,lambda p:p.write_text(p.read_text().replace('"active_integration_state": "ACTIVATED"','"active_integration_state": "CANDIDATE_NOT_ACTIVATED"')))
 mutate('LOCK_IDENTITY',lock,lambda p:p.write_text(p.read_text().replace('63c547f5d5bb794a9a6d5b7aea3c71fd10dc418063494267ea3fbd03e8399646','0'*64)))
 mutate('GRAPH_IDENTITY',graph,lambda p:p.write_text(p.read_text().replace('dcac0c59b8ebacc492e8c053e00894b03dd654d569617b325e78073e67a8239f','1'*64)))
 def incompatible(p):
  d=json.loads(p.read_text());d['status']='INCOMPATIBLE';d['authority_identity']=ident({k:v for k,v in d.items() if k!='authority_identity'});p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 mutate('GRAPH_LOCK_BINDING',graph,incompatible)
 mutate('MANAGED_DRIFT',cfg,lambda p:p.write_bytes(p.read_bytes()+b' '))
 old=cfg.read_bytes();cfg.unlink()
 try:
  r=run(root,[pre,'--root',root,'--skip-platform-hash','--skip-host']);assert r.returncode!=0;checks.append('MISSING_MANAGED')
 finally:cfg.write_bytes(old)
 extra=root/'config/unauthorized.tmp';extra.write_text('x')
 try:
  r=run(root,[pre,'--root',root,'--skip-platform-hash','--skip-host']);assert r.returncode!=0;checks.append('EXTRA_MANAGED')
 finally:extra.unlink()
 mutate('AUDITOR_INCOMPATIBLE',aud,lambda p:p.write_bytes(p.read_bytes()+b'\n# drift\n'))
 with tempfile.TemporaryDirectory(prefix='vnext-bypass-',dir='/root') as td:
  old=lock.read_bytes()
  try:
   d=json.loads(old);d['status']='BROKEN';lock.write_text(json.dumps(d));r=run(root,[acc,'--root',root,'--workspace',td]);assert r.returncode!=0;checks.append('E2E_NO_BYPASS')
  finally:lock.write_bytes(old)
 return {'status':'PASS','checks':checks,'passed':len(checks),'total':9}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();print(json.dumps(main(a.root),sort_keys=True))