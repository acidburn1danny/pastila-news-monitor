from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]
ARMS=("P0_POSITIVE_ONLY_K0_NO_KL","P1_CONTRASTIVE_K0_NO_KL","P0_POSITIVE_ONLY_K1_R2_KL","P1_CONTRASTIVE_K1_R2_KL"); SEEDS=(161803,271828,314159)
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 b=json.loads((ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-runtime-boundary.json").read_text())
 slots=[{"slot_id":f"{a}__seed_{s}","arm":a,"seed":s,"output_slug":f"{a.lower()}__seed_{s}","run_limit":1,"optimizer_steps":9,"fresh_exact_tokenizer_zero_step_required":True} for a in ARMS for s in SEEDS]
 core={"schema":"editor-r2-anchored-contrastive-safety-execution-authority","schema_version":1,"scope":"DEVELOPMENT_RESEARCH_4X3_ONLY","runtime_source_commit":"0c257c6d6434900673be6b6ee49ca7e7e2476bd4","runtime_boundary_identity":b["runtime_boundary_identity"],"protocol_identity":b["protocol_identity"],"pack_identity":b["pack_identity"],"recipe_identity":b["recipe_identity"],"evaluator_identity":b["evaluator_identity"],"parent":"R2_STEP_9","parent_adapter_identity":b["parent_adapter_identity"],"parent_checkpoint_identity":b["parent_checkpoint_identity"],"tokenizer_sha256":b["tokenizer_sha256"],"worker_sha256":sha(ROOT/"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py"),"supervisor_sha256":sha(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py"),"verifier_sha256":sha(ROOT/"scripts/verify_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v1.py"),"slots":slots,"distinct_empty_output_root_per_slot":True,"retry_authorized":False,"stop_on_first_failure":True,"owner_run_authorization_required":True,"real_runs_authorized_in_build_task":False,"historical_holdouts_allowed":False,"parent_selection_authority":False,"promotion_authorized":False,"release_authorized":False,"weighted_sft_t1s0_line":"CLOSED_REFERENCE_ONLY"}
 doc={**core,"authority_identity":hashlib.sha256(canonical(core)).hexdigest()}; out=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-execution-authority.json"; out.write_text(json.dumps(doc,sort_keys=True,indent=2)+"\n"); print(doc["authority_identity"])
if __name__=="__main__": main()
