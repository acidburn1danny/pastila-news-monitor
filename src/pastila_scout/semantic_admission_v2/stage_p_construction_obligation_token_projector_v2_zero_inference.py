"""Real-tokenizer equivalence/performance audit for split-trie V2."""
from __future__ import annotations
import json,sys,time,types
from pathlib import Path
ROOT=Path("/mnt/c/Projects/pastila-news-monitor")
MODEL=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
def main():
 sys.path.insert(0,str(ROOT/"tests"))
 if "pytest" not in sys.modules:
  p=types.ModuleType("pytest");p.mark=types.SimpleNamespace(parametrize=lambda *a,**k:(lambda f:f));p.raises=lambda *a,**k:None;sys.modules["pytest"]=p
 from transformers import AutoTokenizer
 from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context,_valid_text
 from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1 as C
 from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_token_projector_v1 import StagePConstructionObligationTokenProjectorV1 as V1
 from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_token_projector_v2 import StagePConstructionObligationTokenProjectorV2 as V2
 t=AutoTokenizer.from_pretrained(MODEL,local_files_only=True);decode=lambda ids:t.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
 pieces={i:decode([i]) for i in range(len(t))};excluded=(set(t.all_special_ids)-{t.eos_token_id})|{i for i,x in pieces.items() if not x}
 context,_,_=_case_context();raw=_valid_text(context);marker='"role_basis":"';start=raw.index(marker)+len(marker)
 prefixes={"INITIAL":"","LITERAL":raw[:1],"STRING_EMPTY":raw[:start],"STRING_1":raw[:start]+"x","STRING_64":raw[:start]+"x"*64,"STRING_ESCAPE":raw[:start]+"x\\","TERMINAL":raw}
 kwargs=dict(token_pieces=pieces,eos_token_id=t.eos_token_id,tokenizer_identity="sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c",decoder_identity="ministral-tokenizer-decode-skip-special-cleanup-false-v1",excluded_token_ids=excluded)
 a=V1(controller=C(context=context,decoder_identity=kwargs["decoder_identity"]),**kwargs);b=V2(controller=C(context=context,decoder_identity=kwargs["decoder_identity"]),**kwargs)
 rows=[];exact=True
 for name,prefix in prefixes.items():
  ids=t.encode(prefix,add_special_tokens=False)
  s=time.perf_counter();left=a.allowed_token_ids(ids,decode);bt=time.perf_counter()-s
  s=time.perf_counter();right=b.allowed_token_ids(ids,decode);ct=time.perf_counter()-s
  s=time.perf_counter();b.allowed_token_ids(ids,decode);warm=time.perf_counter()-s
  exact=exact and left==right;rows.append({"state":name,"equal":left==right,"allowed":len(right),"v1_seconds":round(bt,6),"v2_seconds":round(ct,6),"v2_warm_seconds":round(warm,6)})
 out={"result":"PASS" if exact else "FAIL","rows":rows,"ordinary_token_count":b.ordinary_token_count,"boundary_trie_node_count":b.boundary_trie_node_count,"full_trie_node_count":b.trie_node_count,"activity":{"tokenizer_loads":1,"model_loads":0,"inference_calls":0,"probe_executions":0}}
 print(json.dumps(out,sort_keys=True,separators=(",",":")))
 if not exact:raise SystemExit(1)
if __name__=="__main__":main()
