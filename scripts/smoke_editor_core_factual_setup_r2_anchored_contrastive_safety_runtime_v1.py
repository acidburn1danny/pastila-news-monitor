from __future__ import annotations
import json,shutil
from pathlib import Path
from editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1 import ARMS,SEEDS,fixture_slot
ROOT=Path(__file__).parents[1]
class Tokenizer:
    def __call__(self,text,**_): return {"input_ids":list(range(len(text))),"offset_mapping":[(i,i+1) for i in range(len(text))]}
def main():
    receipts=[]; root=ROOT/".anchored-contrastive-runtime-smoke"
    if root.exists(): shutil.rmtree(root)
    root.mkdir()
    try:
        for arm in ARMS:
            for seed in SEEDS:
                out=root/f"{arm}-{seed}"; out.mkdir(); receipts.append(fixture_slot(Tokenizer(),ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl",ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl",out,arm,seed))
    finally:
        shutil.rmtree(root)
    print(json.dumps({"status":"PASS_FIXTURE_ONLY","slots":len(receipts),"unique_receipts":len({x['receipt_identity'] for x in receipts}),"model_loaded":False,"optimizer_created":False,"training_performed":False},sort_keys=True))
if __name__=="__main__": main()
