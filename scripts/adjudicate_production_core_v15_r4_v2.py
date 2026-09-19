"""Interactive successor R4 adjudication CLI after key rotation."""
import argparse,base64,json
from pathlib import Path
from pastila_scout.production_core_r4_adjudicator_client_v2 import ROLE_CONTRACT,run_session
def decide(packet):
 print(json.dumps({'global_ordinal':packet['global_ordinal'],'case_id':packet['case_id'],'candidate_alias':packet['candidate_alias'],'request':packet['request'],'assertion':packet['assertion'],'candidate_output':base64.b64decode(packet['raw_output_base64'],validate=True).decode('utf-8')},ensure_ascii=False,indent=2))
 while True:
  value=input('Verdict [PASS/FAIL/INDETERMINATE]: ').strip().upper()
  if value in ('PASS','FAIL','INDETERMINATE'):return value
def main():
 p=argparse.ArgumentParser();p.add_argument('--role',choices=tuple(ROLE_CONTRACT),required=True);p.add_argument('--custody-root',type=Path,required=True);p.add_argument('--receipt-root',type=Path,required=True);p.add_argument('--private-key',type=Path,required=True);p.add_argument('--artifact-root',type=Path,required=True);p.add_argument('--openssl',type=Path,required=True);o=p.parse_args();print(json.dumps(run_session(role=o.role,custody_root=o.custody_root,output_root=o.receipt_root,private_key=o.private_key,artifact_root=o.artifact_root,openssl=o.openssl,decide=decide),sort_keys=True))
if __name__=='__main__':main()
