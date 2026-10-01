#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,tempfile,sys
from pathlib import Path
def mod(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def audit(repo,active,rollback):
 repo,active,rollback=map(lambda x:Path(x).resolve(),(repo,active,rollback));b=mod(repo/"scripts/build_vnext_gui_active_attestation_repair_v1.py","b")
 with tempfile.TemporaryDirectory(dir="/root",prefix="gui-attestation-audit-") as td:
  out=Path(td)/"out";out.mkdir();r=b.build(repo,active,out)
  names=("vnext-gui-active-product-dependency-graph-v6.json","vnext-gui-canonical-rollback-manifest-v4.json","vnext-gui-activation-receipt-v1.json","vnext-gui-active-state-authority-v1.json","vnext-gui-active-product-lock-v8.json","vnext-gui-active-attestation-repair-result-v1.json")
  for n in names:
   if (repo/"docs/artifacts"/n).read_bytes()!=(out/n).read_bytes():raise RuntimeError("reproduction "+n)
  root=Path(td)/"root";(root/"manifest/activation").mkdir(parents=True);(root/"manifest/authorities").mkdir();(root/"manifest/rollback").mkdir()
  shutil.copy2(out/"vnext-gui-activation-receipt-v1.json",root/"manifest/activation/vnext-activation-receipt-v1.json");shutil.copy2(out/"vnext-gui-active-state-authority-v1.json",root/"manifest/authorities/vnext-active-product-lock-successor-v1.json");shutil.copy2(out/"vnext-gui-canonical-rollback-manifest-v4.json",root/"manifest/rollback/vnext-canonical-rollback-manifest-v1.json")
  lock=json.loads((out/"vnext-gui-active-product-lock-v8.json").read_text());sys.path.insert(0,str(active/"app/cli"));pf=mod(repo/"scripts/vnext_gui_active_preflight_v1.py","pf")
  if pf.verify_activation_authority(root,lock)!="V8_GUI_ACTIVE_ATTESTED":raise RuntimeError("schema8")
  rows={x["path"]:x for x in lock["application_files"]}
  if len(rows)!=33 or lock["status"]!="ACTIVE" or not lock["activation"]["authorized"]:raise RuntimeError("active semantics")
  old=b.sha(active/"product-lock.json");rb=b.sha(rollback/"product-lock.json");a=Path(td)/"active";n=Path(td)/"new";shutil.copy2(active/"product-lock.json",a);shutil.copy2(out/"vnext-gui-active-product-lock-v8.json",n);o=Path(td)/"old";a.rename(o);n.rename(a);o.rename(n);x=Path(td)/"successor";a.rename(x);n.rename(a);x.rename(n)
  if b.sha(a)!=old or b.sha(rollback/"product-lock.json")!=rb:raise RuntimeError("restore")
  return {**r,"audit_status":"PASS","schema8_preflight":"PASS","prospective_install_rollback_restore":"PASS","active_unchanged":True,"rollback_unchanged":True}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active",type=Path,required=True);p.add_argument("--rollback",type=Path,required=True);x=p.parse_args();print(json.dumps(audit(x.repo,x.active,x.rollback),sort_keys=True))
