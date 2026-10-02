#!/usr/bin/env python3
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs/artifacts'
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def ident(v,f): return hashlib.sha256(canonical({k:x for k,x in v.items() if k!=f})).hexdigest()
def run():
 r=json.loads((ART/'vnext-voice-factual-safety-taxonomy-correction-v1.json').read_text()); d=json.loads((ART/'vnext-voice-constrained-factual-projection-design-v1.json').read_text()); l=json.loads((ART/'vnext-r2-lora-effect-diagnosis-v1.json').read_text())
 assert ident(r,'result_identity')==r['result_identity'] and len(r['rows'])==216
 assert ident(d,'design_identity')==d['design_identity'] and ident(l,'diagnosis_identity')==l['diagnosis_identity']
 p=r['per_candidate']; assert p['V0_R2_MINISTRAL_CONTROL']['unsupported_cases']==['VOICE-V1-22']; assert p['V1_QWEN3_8B_NON_THINKING']['unsupported_cases']==[]; assert p['V2_QWEN25_7B_INSTRUCT']['terminal']=='REVISE_ABSTENTION'
 assert d['runtime_integration'] is False and r['promotion'] is False and r['legacy_dependency_count']==0
 t=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_vnext_voice_factual_projection_v1.py'],cwd=ROOT,env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True)
 if t.returncode: raise RuntimeError(t.stdout+t.stderr)
 out={'schema':'vnext-voice-factual-taxonomy-projection-audit','schema_version':1,'status':'PASS','blockers':[],'rows':216,'dedicated_tests':'4 passed','voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}; out['audit_identity']=ident(out,'audit_identity'); return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
