"""Tokenizer-only construction/equivalence preflight for Stage P runner V3."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

MODEL=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ROOT=Path("/mnt/c/Projects/pastila-news-monitor")
RUNNER=ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py"


def _ledger(span):
    record={"entry_id":"P1","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":span,
        "authority_support":None,"commitment":span,"scope_basis":"ASSERTED","event_alignment":"GOVERNED_EVENT",
        "authority_modality":"POSSIBLE","candidate_modality":"CERTAIN_OR_ACTUAL","authority_timing":"FUTURE",
        "candidate_timing":"PRESENT","independence_group":"G1"}
    return json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[record],
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":False}},ensure_ascii=False,separators=(",",":"))


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {name}")
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def main(target):
    from transformers import AutoTokenizer
    package_root=ROOT/"src/pastila_scout";semantic_root=package_root/"semantic_admission_v2"
    for name,path in (("pastila_scout",package_root),("pastila_scout.semantic_admission_v2",semantic_root)):
        package=types.ModuleType(name);package.__path__=[str(path)];sys.modules.setdefault(name,package)
    prefix="pastila_scout.semantic_admission_v2."
    dfa=_load(prefix+"stage_p_constraint_v1",semantic_root/"stage_p_constraint_v1.py")
    baseline_module=_load(prefix+"gate_f_trie_projector_v1",semantic_root/"gate_f_trie_projector_v1.py")
    _load(prefix+"stage_p_incremental_tracker_v1",semantic_root/"stage_p_incremental_tracker_v1.py")
    candidate_module=_load(prefix+"stage_p_trie_projector_v1",semantic_root/"stage_p_trie_projector_v1.py")
    controller_module=_load(prefix+"stage_p_callback_controller_v1",semantic_root/"stage_p_callback_controller_v1.py")
    GateFTokenTrieProjectorOptimizedV1=baseline_module.GateFTokenTrieProjectorOptimizedV1
    StagePCallbackControllerV1=controller_module.StagePCallbackControllerV1
    StagePConstraintStateV1=dfa.StagePConstraintStateV1
    StagePTokenTrieProjectorV1=candidate_module.StagePTokenTrieProjectorV1

    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
    excluded=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id}
    baseline=GateFTokenTrieProjectorOptimizedV1(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,excluded_token_ids=excluded)
    candidate=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,excluded_token_ids=excluded)
    controller=StagePCallbackControllerV1(projector=candidate);divergences=0;prefixes=0
    tracker_paths=set()
    for raw in (_ledger("specific"),_ledger("x"*400)):
        ids=tokenizer.encode(raw,add_special_tokens=False)
        ends=sorted({round(index*len(ids)/8) for index in range(9)})
        for end in ends:
            receipt=controller.allowed(ids[:end],lambda values:tokenizer.decode(values,skip_special_tokens=True))
            full=StagePConstraintStateV1().feed(tokenizer.decode(ids[:end],skip_special_tokens=True))
            if receipt.allowed_token_ids!=baseline.allowed_token_ids(full): divergences+=1
            tracker_paths.add(receipt.tracking_path);prefixes+=1
        controller=StagePCallbackControllerV1(projector=candidate)
    value={"schema_name":"pastila-semantic-admission-v2-stage-p-runner-v3-zero-inference-preflight",
        "schema_version":"1.0.0","runner_sha256":hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        "tokenizer_vocabulary_size":len(tokenizer),"candidate_trie_nodes":candidate.trie_node_count,
        "prefixes_compared":prefixes,"checkpoint_policy":"nine evenly spaced deterministic prefixes per stream",
        "allowed_set_divergences":divergences,"tracker_paths":sorted(tracker_paths),
        "model_imported":False,"model_load_started":False,"inference_started":False,"model_calls":0,"provider_calls":0,
        "result":"PASS" if divergences==0 else "FAIL"}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n","utf-8")


if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: preflight TARGET")
    main(Path(sys.argv[1]))
