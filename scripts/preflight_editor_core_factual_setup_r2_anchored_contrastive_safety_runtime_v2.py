"""CAR v2 exact-tokenizer zero-step with complete 72-row mapping closure."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1 import ARMS,SEEDS,EXPECTED_TOKENIZER,identity,matched_order,sha,validate_inputs
from editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2 import validate_training_mapping

def main():
 p=argparse.ArgumentParser()
 for n in ("model","corpus","annotations","pairs","retention","output"): p.add_argument(f"--{n}",type=Path,required=True)
 a=p.parse_args()
 if sha(a.model/"tokenizer.json")!=EXPECTED_TOKENIZER: raise ValueError("exact tokenizer mismatch")
 if a.output.is_symlink() or not a.output.is_dir() or any(a.output.iterdir()): raise ValueError("output root must be distinct and empty")
 from transformers import AutoTokenizer
 tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True,fix_mistral_regex=True)
 pack=validate_inputs(tok,a.pairs,a.retention); mapping=validate_training_mapping(tok,a.corpus,a.annotations,a.pairs,a.retention)
 core={"schema":"editor-r2-anchored-contrastive-runtime-zero-step","schema_version":2,"status":"PASS_ZERO_STEP","tokenizer_sha256":EXPECTED_TOKENIZER,**pack,**mapping,"arms":sorted(ARMS),"seeds":list(SEEDS),"slots":12,"orders":{str(s):identity(matched_order(s)) for s in SEEDS},"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False,"parent_selection_authority":False}
 receipt={**core,"preflight_identity":identity(core)}; staging=a.output/".staging"; staging.mkdir(); path=staging/"zero-step.json"; path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8"); os.replace(path,a.output/"zero-step.json"); staging.rmdir(); print(json.dumps(receipt,sort_keys=True,separators=(",",":")))
if __name__=="__main__": main()
