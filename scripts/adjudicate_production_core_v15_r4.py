"""Interactive CLI for one isolated R4 human adjudicator session."""
from __future__ import annotations
import argparse, base64, json
from pathlib import Path
from pastila_scout.production_core_r4_adjudicator_client import ROLE_CONTRACT, run_session

def decision(packet):
 print(json.dumps({"global_ordinal":packet["global_ordinal"],"case_id":packet["case_id"],"candidate_alias":packet["candidate_alias"],"request":packet["request"],"assertion":packet["assertion"],"candidate_output":base64.b64decode(packet["raw_output_base64"],validate=True).decode("utf-8",errors="strict")},ensure_ascii=False,indent=2))
 while True:
  value=input("Verdict [PASS/FAIL/INDETERMINATE]: ").strip().upper()
  if value in ("PASS","FAIL","INDETERMINATE"): return value
  print("Invalid verdict.")

def main():
 p=argparse.ArgumentParser(); p.add_argument("--role",choices=tuple(ROLE_CONTRACT),required=True); p.add_argument("--custody-root",type=Path,required=True); p.add_argument("--receipt-root",type=Path,required=True); p.add_argument("--private-key",type=Path,required=True); p.add_argument("--registry",type=Path,required=True); p.add_argument("--openssl",type=Path,required=True)
 o=p.parse_args(); print(json.dumps(run_session(role=o.role,custody_root=o.custody_root,output_root=o.receipt_root,private_key=o.private_key,registry_path=o.registry,openssl=o.openssl,decide=decision),sort_keys=True))
if __name__=="__main__": main()
