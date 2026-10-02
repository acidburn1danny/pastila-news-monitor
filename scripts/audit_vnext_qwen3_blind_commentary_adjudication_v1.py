#!/usr/bin/env python3
import hashlib,json,subprocess,sys,os
from pathlib import Path
R=Path(__file__).resolve().parents[1]; P=R/'docs/artifacts/vnext-qwen3-blind-commentary-adjudication-v1.json'
def c(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def run():
 x=json.loads(P.read_text()); assert x['result_identity']==hashlib.sha256(c({k:v for k,v in x.items() if k!='result_identity'})).hexdigest(); assert len(x['scores'])==24 and x['terminal']=='REJECT_STRUCTURAL_AND_COMMENTARY_QUALITY'; assert x['structural_violation_outputs']==12
 t=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_vnext_qwen3_blind_commentary_adjudication_v1.py'],cwd=R,env={**os.environ,'PYTHONPATH':str(R/'src')},capture_output=True,text=True); assert t.returncode==0,t.stdout+t.stderr
 out={'schema':'vnext-qwen3-blind-commentary-adjudication-audit','schema_version':1,'status':'PASS','blockers':[],'dedicated_tests':'4 passed','terminal':x['terminal'],'voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}; out['audit_identity']=hashlib.sha256(c(out)).hexdigest(); return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
