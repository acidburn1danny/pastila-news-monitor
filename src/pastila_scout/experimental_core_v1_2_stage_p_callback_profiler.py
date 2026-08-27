"""Tokenizer-only Stage P callback characterization; never imports or loads a model."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import tracemalloc
from pathlib import Path

MODEL=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ROOT=Path("/mnt/c/Projects/pastila-news-monitor")


def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {name}")
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def _ledger(entries:int,free_length:int)->str:
    records=[]
    span=("context-local-"*(free_length//14+1))[:free_length]
    commitment=("proposition-"*(min(free_length,500)//12+1))[:min(free_length,500)]
    for index in range(1,entries+1):
        records.append({"entry_id":f"P{index}","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":span,
            "authority_support":None,"commitment":commitment,"scope_basis":"ASSERTED","event_alignment":"GOVERNED_EVENT",
            "authority_modality":"POSSIBLE","candidate_modality":"CERTAIN_OR_ACTUAL","authority_timing":"FUTURE",
            "candidate_timing":"PRESENT","independence_group":f"G{index}"})
    return json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":records,
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":False}},ensure_ascii=False,separators=(",",":"))


def main(target:Path)->None:
    from transformers import AutoTokenizer
    dfa=_load("sav2_profiler_dfa",ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_constraint_v1.py")
    trie=_load("sav2_profiler_trie",ROOT/"src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
    StagePConstraintStateV1=dfa.StagePConstraintStateV1;GateFTokenTrieProjectorOptimizedV1=trie.GateFTokenTrieProjectorOptimizedV1
    class StagePIncrementalPrefixTrackerV1:
        def __init__(self):
            self.ids=();self.decoded="";self.state=StagePConstraintStateV1();self.rebuild_steps=0;self.incremental_steps=0
        def state_for(self,ids,decode):
            ids=tuple(ids);decoded=decode(ids)
            if len(ids)>=len(self.ids) and ids[:len(self.ids)]==self.ids and decoded.startswith(self.decoded):
                suffix=decoded[len(self.decoded):];state=self.state.feed(suffix);self.incremental_steps+=1
            else:
                suffix=decoded;state=StagePConstraintStateV1().feed(decoded);self.rebuild_steps+=1
            self.ids,self.decoded,self.state=ids,decoded,state
            return type("Result",(),{"state":state,"suffix_characters":len(suffix)})()
    lifecycle={"model_imported":False,"model_load_started":False,"inference_started":False,"model_calls":0,"provider_calls":0}
    tracemalloc.start();started=time.perf_counter();tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    token_pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
    projector=GateFTokenTrieProjectorOptimizedV1(token_pieces=token_pieces,eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    setup_seconds=time.perf_counter()-started;profiles=[];divergences=0
    for entries in (1,4,8):
        for label,length in (("SHORT",24),("MAX_BOUNDED",400)):
            raw=_ledger(entries,length);ids=tokenizer.encode(raw,add_special_tokens=False);tracker=StagePIncrementalPrefixTrackerV1()
            full_seconds=incremental_seconds=projection_seconds=0.0;replayed=incremental_chars=0;sampled=0
            ends=sorted({round(index*len(ids)/8) for index in range(9)})
            for end in ends:
                decoded=tokenizer.decode(ids[:end],skip_special_tokens=True)
                tick=time.perf_counter();full=StagePConstraintStateV1().feed(decoded);full_seconds+=time.perf_counter()-tick;replayed+=len(decoded)
                tick=time.perf_counter();inc=tracker.state_for(ids[:end],lambda sequence:tokenizer.decode(sequence,skip_special_tokens=True));incremental_seconds+=time.perf_counter()-tick;incremental_chars+=inc.suffix_characters
                tick=time.perf_counter();full_allowed=projector.allowed_token_ids(full);inc_allowed=projector.allowed_token_ids(inc.state);projection_seconds+=time.perf_counter()-tick
                if full!=inc.state or full_allowed!=inc_allowed: divergences+=1
                sampled+=1
            profiles.append({"entries":entries,"free_string_class":label,"utf8_bytes":len(raw.encode()),"tokens":len(ids),
                "prefix_sampling":"9_EVEN_DETERMINISTIC_CHECKPOINTS",
                "total_possible_prefixes":len(ids)+1,"prefixes_compared":sampled,"full_replay_seconds":round(full_seconds,6),"incremental_tracking_seconds":round(incremental_seconds,6),
                "token_projection_seconds":round(projection_seconds,6),"full_replayed_characters":replayed,
                "incremental_fed_characters":incremental_chars,"tracker_rebuilds":tracker.rebuild_steps,
                "tracker_incremental_steps":tracker.incremental_steps,"terminal_eos":StagePConstraintStateV1().feed(raw).can_eos})
    invalid=[]
    for label,raw in (("WRONG_ROOT",_ledger(1,24).replace('{"stage_id"','{"wrong"',1)),
                      ("INVALID_ENUM",_ledger(1,24).replace('"ASSERTED"','"INVALID"',1)),
                      ("TRAILING_BYTES",_ledger(1,24)+"x")):
        ids=tokenizer.encode(raw,add_special_tokens=False);tracker=StagePIncrementalPrefixTrackerV1();full_failure=incremental_failure=None
        for end in range(len(ids)+1):
            decoded=tokenizer.decode(ids[:end],skip_special_tokens=True)
            try: StagePConstraintStateV1().feed(decoded)
            except ValueError as exc: full_failure={"prefix":end,"code":str(exc)}
            try: tracker.state_for(ids[:end],lambda sequence:tokenizer.decode(sequence,skip_special_tokens=True))
            except ValueError as exc: incremental_failure={"prefix":end,"code":str(exc)}
            if full_failure or incremental_failure: break
        invalid.append({"class":label,"full_failure":full_failure,"incremental_failure":incremental_failure,
            "same_failure":full_failure==incremental_failure})
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    lifecycle.update(schema_name="pastila-semantic-admission-v2-stage-p-callback-characterization",schema_version="1.0.0",
        tokenizer_vocabulary_size=len(tokenizer),trie_node_count=projector.trie_node_count,setup_seconds=round(setup_seconds,6),
        profiles=profiles,invalid_profiles=invalid,allowed_set_divergences=divergences,peak_traced_bytes=peak,
        all_terminal=all(item["terminal_eos"] for item in profiles),all_invalid_failures_identical=all(item["same_failure"] for item in invalid),
        result="PASS" if divergences==0 and all(item["terminal_eos"] for item in profiles) and all(item["same_failure"] for item in invalid) else "FAIL")
    target.write_text(json.dumps(lifecycle,ensure_ascii=False,indent=2)+"\n","utf-8")


if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: profiler TARGET")
    main(Path(sys.argv[1]))
