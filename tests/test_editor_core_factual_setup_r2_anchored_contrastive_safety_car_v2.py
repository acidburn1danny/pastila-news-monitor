from __future__ import annotations
import importlib.util,json,shutil,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
def load():
 sys.path.insert(0,str(ROOT/"scripts"))
 p=ROOT/"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2.py"; spec=importlib.util.spec_from_file_location("anchored_v2",p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
class Tok:
 def apply_chat_template(self,messages,tokenize=False,add_generation_prompt=False):
  text="".join(x["content"] for x in messages)
  if add_generation_prompt: text += ""
  return {"input_ids":list(range(len(text)))} if tokenize else text
 def __call__(self,text,**_): return {"input_ids":list(range(len(text))),"offset_mapping":[(i,i+1) for i in range(len(text))]}
def paths():
 a=ROOT/"docs/artifacts"
 return (a/"editor-core-factual-setup-corrective-v1-training.jsonl",a/"editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl",a/"editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl",a/"editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl")
def test_partition_specific_span_contract():
 m=load(); result=m.validate_training_mapping(Tok(),*paths()); assert result=={"training_rows":72,"corrective_rows":48,"replay_rows":24,"corrective_nonempty_token_mappings":48,"replay_empty_span_rows":24}
def test_empty_corrective_and_nonempty_replay_fail_closed():
 m=load(); corpus,annotations,pairs,replay=paths(); root=ROOT/".car-v2-mutation-test"; shutil.rmtree(root,ignore_errors=True); root.mkdir()
 try:
  rows=[json.loads(x) for x in annotations.read_text(encoding="utf-8").splitlines()]; corrective=next(x for x in rows if x["split"]=="CORRECTIVE_TARGETED"); corrective["critical_spans"]=[]; bad=root/"bad.jsonl"; bad.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
  with pytest.raises(ValueError,match="corrective critical spans required"): m.validate_training_mapping(Tok(),corpus,bad,pairs,replay)
  rows=[json.loads(x) for x in annotations.read_text(encoding="utf-8").splitlines()]; rr=next(x for x in rows if x["split"]=="REPLAY_PROTECTION"); rr["critical_spans"]=[{"field":"text","start":0,"end":1,"text":"x"}]; bad.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
  with pytest.raises(ValueError,match="replay critical spans forbidden"): m.validate_training_mapping(Tok(),corpus,bad,pairs,replay)
 finally: shutil.rmtree(root)
def test_failure_receipt_is_atomic_and_ineligible():
 m=load(); root=ROOT/".car-v2-failure-test"; shutil.rmtree(root,ignore_errors=True); root.mkdir()
 try:
  exc=m.SlotFailure("PRE_MODEL_TRAINING_MAPPING","case-1","bad"); m._atomic_failure(root,"ARM__seed_1",exc); files=list(root.iterdir()); assert [x.name for x in files]==["failure.json"]
  d=json.loads(files[0].read_text()); assert d["example_id"]=="case-1" and d["phase"]=="PRE_MODEL_TRAINING_MAPPING" and not d["eligible_evidence"]
 finally: shutil.rmtree(root)
def test_supervisor_verifies_before_plan_and_persists_failure():
 text=(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v2.py").read_text(); assert text.index("auth=verify") < text.index("slots=plan")
 assert "program-failure.json" in text and "corrective_nonempty_token_mappings" in text and "replay_empty_span_rows" in text
