from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).parents[1]
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    runtime=json.loads((ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-runtime-boundary.json").read_text(encoding="utf-8"))
    arms=("T0_CONTROL_S0_CONTROL","T0_CONTROL_S1_HIGHER_PLASTICITY","T1_CONTRACT_WEIGHTED_S0_CONTROL","T1_CONTRACT_WEIGHTED_S1_HIGHER_PLASTICITY"); seeds=(161803,271828,314159)
    slots=[{"slot_id":f"{a}__seed_{s}","arm":a,"seed":s,"output_slug":f"{a.lower()}__seed_{s}","run_limit":1,"optimizer_steps":9,"fresh_zero_step_required":True} for a in arms for s in seeds]
    core={
      "schema":"editor-factual-setup-r2-causal-diagnostic-execution-authority","schema_version":1,"scope":"DEVELOPMENT_RESEARCH_FACTORIAL_2X2_ONLY",
      "source_commit":"9649ba9e290487d4fb5c365599904d1f2ee26f72","source_tree":"28642cd09a7c4bf0e2ad4e6a887d1a2f85e1795e",
      "runtime_boundary_identity":runtime["runtime_boundary_identity"],"worker_sha256":sha(ROOT/"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py"),
      "route_sha256":sha(ROOT/"scripts/run_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.sh"),"supervisor_sha256":sha(ROOT/"scripts/supervise_editor_core_factual_setup_r2_causal_diagnostic_v1.py"),
      "protocol_identity":runtime["protocol_identity"],"pack_identity":runtime["pack_identity"],"recipes_identity":runtime["recipes_identity"],"evaluation_identity":runtime["evaluation_identity"],
      "parent_adapter_identity":runtime["parent_adapter_identity"],"parent_checkpoint_identity":runtime["parent_checkpoint_identity"],"tokenizer_sha256":runtime["tokenizer_sha256"],"slots":slots,
      "owner_run_authorization_required":True,"publication_required":True,"real_runs_authorized_in_build_task":False,"holdout_access_authorized":False,"parent_selection_authority":False,
      "promotion_authorized":False,"release_authorized":False,"terminal_receipt_required":True,"retry_authorized":False}
    doc={**core,"authority_identity":hashlib.sha256(canonical(core)).hexdigest()}; out=ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-execution-authority.json"; out.write_text(json.dumps(doc,sort_keys=True,indent=2)+"\n",encoding="utf-8"); print(doc["authority_identity"])
if __name__=="__main__": main()
