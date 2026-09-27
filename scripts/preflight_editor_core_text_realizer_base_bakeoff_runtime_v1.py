"""No-model-load preflight for the real base-model bake-off."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

AUTH="52346e1d315ab7a6245a3c81a24ce8518355b5bd586636cea6a36253d3c3536f"
PROGRAM="3529f416d9aa9e2a96d6a254609ea51decbd6cf20906e2302afa61ece5bb685c"
R2="c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def flat(root:Path)->str:
 rows=[]
 for p in sorted(root.iterdir(),key=lambda x:x.name.encode()):
  if p.is_symlink() or not p.is_file(): raise ValueError("adapter shape")
  rows.append(p.name.encode()+b"\0"+p.stat().st_size.to_bytes(8,"big")+bytes.fromhex(sha(p.read_bytes())))
 return sha(b"".join(rows))
def main():
 p=argparse.ArgumentParser();p.add_argument("--store",type=Path,required=True);p.add_argument("--r2-adapter",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists() and (a.output.is_symlink() or any(a.output.iterdir())):raise ValueError("nonempty zero-step")
 pr=json.loads((a.store/"program-receipt.json").read_text())
 if pr["authority_identity"]!=AUTH or pr["receipt_identity"]!=PROGRAM or pr["status"]!="PASS_ACQUIRED_2":raise ValueError("acquisition receipt")
 if flat(a.r2_adapter)!=R2:raise ValueError("R2 identity")
 a.output.mkdir(parents=True,exist_ok=True)
 core={"status":"PASS_ZERO_STEP","authority_identity":AUTH,"acquisition_receipt_identity":PROGRAM,"r2_adapter_identity":R2,"candidates":3,"model_loaded":False,"inference_performed":False}
 core["receipt_identity"]=sha(json.dumps(core,sort_keys=True,separators=(",",":")).encode())
 (a.output/"zero-step.json").write_text(json.dumps(core,sort_keys=True,indent=2)+"\n")
 print(json.dumps(core,sort_keys=True))
if __name__=="__main__":main()
