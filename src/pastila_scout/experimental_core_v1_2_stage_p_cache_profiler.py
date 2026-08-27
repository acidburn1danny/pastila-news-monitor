"""Real-tokenizer, zero-inference Stage P cache equivalence/performance profiler."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path

MODEL=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ROOT=Path("/mnt/c/Projects/pastila-news-monitor")
CANDIDATE_SOURCE_SHA256="8cc6f68f1ff9751ab983306e9fb39efa0ae55c52cbe8a0471a2e5e98bfc54529"


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {name}")
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def _ledger(entries,length):
    records=[];span=("specific-"*((length//9)+1))[:length];commitment=("claim-"*((min(length,500)//6)+1))[:min(length,500)]
    for index in range(1,entries+1): records.append({"entry_id":f"P{index}","entry_type":"REAL_WORLD_COMMITMENT",
        "candidate_span":span,"authority_support":None,"commitment":commitment,"scope_basis":"ASSERTED",
        "event_alignment":"GOVERNED_EVENT","authority_modality":"POSSIBLE","candidate_modality":"CERTAIN_OR_ACTUAL",
        "authority_timing":"FUTURE","candidate_timing":"PRESENT","independence_group":f"G{index}"})
    return json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":records,
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":False}},ensure_ascii=False,separators=(",",":"))


def main(target):
    from transformers import AutoTokenizer
    candidate_path=ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py"
    if hashlib.sha256(candidate_path.read_bytes()).hexdigest()!=CANDIDATE_SOURCE_SHA256: raise RuntimeError("cache candidate identity drift")
    dfa=_load("sav2_cache_profiler_dfa",ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_constraint_v1.py")
    trie=_load("sav2_cache_profiler_trie",ROOT/"src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
    State=dfa.StagePConstraintStateV1;Baseline=trie.GateFTokenTrieProjectorOptimizedV1
    class Candidate(Baseline):
        def _cache_key(self,state):
            key=super()._cache_key(state)
            return replace(key,string_characters=1) if key.mode=="STRING" and key.string_characters>0 else key
    tracemalloc.start();setup=time.perf_counter();tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
    baseline=Baseline(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    candidate=Candidate(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    setup_seconds=time.perf_counter()-setup;profiles=[];divergences=0
    for entries in (1,4,8):
        for label,length in (("SHORT",24),("MAX_BOUNDED",400)):
            raw=_ledger(entries,length);ids=tokenizer.encode(raw,add_special_tokens=False);ends=sorted({round(i*len(ids)/8) for i in range(9)})
            baseline_seconds=candidate_seconds=0.0
            for end in ends:
                state=State().feed(tokenizer.decode(ids[:end],skip_special_tokens=True))
                tick=time.perf_counter();left=baseline.allowed_token_ids(state);baseline_seconds+=time.perf_counter()-tick
                tick=time.perf_counter();right=candidate.allowed_token_ids(state);candidate_seconds+=time.perf_counter()-tick
                if left!=right: divergences+=1
            profiles.append({"entries":entries,"free_string_class":label,"tokens":len(ids),"prefixes":len(ends),
                "baseline_projection_seconds":round(baseline_seconds,6),"candidate_projection_seconds":round(candidate_seconds,6),
                "speedup":round(baseline_seconds/candidate_seconds,6) if candidate_seconds else None})
    prefix='{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[{"entry_id":"P1","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":"'
    targeted=[]
    for length in (0,1,2,8,64,256,400):
        state=State().feed(prefix+"x"*length)
        tick=time.perf_counter();left=baseline.allowed_token_ids(state);base=time.perf_counter()-tick
        tick=time.perf_counter();right=candidate.allowed_token_ids(state);cand=time.perf_counter()-tick
        targeted.append({"string_characters":length,"baseline_seconds":round(base,6),"candidate_seconds":round(cand,6),"same":left==right})
        if left!=right: divergences+=1
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    value={"schema_name":"pastila-semantic-admission-v2-stage-p-cache-characterization","schema_version":"1.0.0",
        "candidate_source_sha256":CANDIDATE_SOURCE_SHA256,"model_imported":False,"model_load_started":False,
        "inference_started":False,"model_calls":0,"provider_calls":0,"tokenizer_vocabulary_size":len(tokenizer),
        "trie_node_count_baseline":baseline.trie_node_count,"trie_node_count_candidate":candidate.trie_node_count,
        "setup_seconds":round(setup_seconds,6),"profiles":profiles,"targeted_string_states":targeted,
        "allowed_set_divergences":divergences,"baseline_cache_size":baseline.cache_size,"candidate_cache_size":candidate.cache_size,
        "peak_traced_bytes":peak,"result":"PASS" if divergences==0 else "FAIL"}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n","utf-8")


if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: profiler TARGET")
    main(Path(sys.argv[1]))
