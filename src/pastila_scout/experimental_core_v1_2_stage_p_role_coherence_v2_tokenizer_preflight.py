"""Tokenizer-only compatibility for role-conditioned Stage P constraint V2."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
import types
from pathlib import Path


MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ROOT = Path("/mnt/c/Projects/pastila-news-monitor")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(name)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module


def _raw(role: str, supported: bool = False, invalid_real: bool = False) -> str:
    entry = {"entry_id":"P1","entry_type":role,"candidate_span":"hotelul","authority_support":"complex turistic" if supported else None,
             "commitment":"Descriere semantică story-locală.","scope_basis":"CREATIVE_CONTAINED","event_alignment":"CREATIVE_VEHICLE_ONLY",
             "authority_modality":"NOT_APPLICABLE","candidate_modality":"NOT_APPLICABLE","authority_timing":"NOT_APPLICABLE",
             "candidate_timing":"NOT_APPLICABLE","independence_group":"G1"}
    unresolved = role == "UNRESOLVED_SCOPE"
    if role == "REAL_WORLD_COMMITMENT":
        entry.update(scope_basis="PRESUPPOSED",event_alignment="NEW_UNSUPPORTED_EVENT",
                     authority_modality="POSSIBLE" if supported else "NOT_APPLICABLE",
                     candidate_modality="UNRESOLVED" if invalid_real else "CERTAIN_OR_ACTUAL",
                     authority_timing="FUTURE" if supported else "NOT_APPLICABLE",candidate_timing="PRESENT")
    elif unresolved:
        entry.update(scope_basis="UNRESOLVED",event_alignment="UNRESOLVED",candidate_modality="UNRESOLVED",candidate_timing="UNRESOLVED")
    value={"stage_id":"PROPOSITION_LEDGER","entries":[entry],"coverage_receipt":{
        "candidate_reviewed_as_whole":not unresolved,"embedded_propositions_checked":not unresolved,
        "creative_scope_checked":not unresolved,"unresolved_scope_present":unresolved},
        "coverage_decision":"INDETERMINATE" if unresolved else "COMPLETE"}
    return json.dumps(value,ensure_ascii=False,separators=(",", ":"))


def main() -> None:
    started=time.perf_counter(); from transformers import AutoTokenizer
    package_root=ROOT/"src/pastila_scout";semantic_root=package_root/"semantic_admission_v2"
    for name,path in (("pastila_scout",package_root),("pastila_scout.semantic_admission_v2",semantic_root)):
        package=types.ModuleType(name);package.__path__=[str(path)];sys.modules.setdefault(name,package)
    prefix="pastila_scout.semantic_admission_v2."
    _load(prefix+"stage_p_role_coherence_constraint_v1",semantic_root/"stage_p_role_coherence_constraint_v1.py")
    dfa=_load(prefix+"stage_p_role_coherence_constraint_v2",semantic_root/"stage_p_role_coherence_constraint_v2.py")
    _load(prefix+"gate_f_trie_projector_v1",semantic_root/"gate_f_trie_projector_v1.py")
    trie_module=_load(prefix+"stage_p_trie_projector_v1",semantic_root/"stage_p_trie_projector_v1.py")
    State=dfa.StagePRoleCoherenceConstraintStateV2;Trie=trie_module.StagePTokenTrieProjectorV1
    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
    trie=Trie(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,
              excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    streams=[]
    for label,raw in (("CONTAINED",_raw("CONTAINED_CREATIVE")),("REAL_NULL",_raw("REAL_WORLD_COMMITMENT")),
                      ("REAL_SUPPORTED",_raw("REAL_WORLD_COMMITMENT",True)),("UNRESOLVED",_raw("UNRESOLVED_SCOPE"))):
        ids=tokenizer.encode(raw,add_special_tokens=False);invalid=[]
        for index,token in enumerate(ids):
            state=State().feed(tokenizer.decode(ids[:index],skip_special_tokens=True))
            if token not in trie.allowed_token_ids(state): invalid.append(index);break
        decoded=tokenizer.decode(ids,skip_special_tokens=True);final=State().feed(decoded)
        streams.append({"label":label,"tokens":len(ids),"raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),
                        "decoded_exact":decoded==raw,"invalid_next_token_indices":invalid,"terminal":final.can_eos,
                        "eos_only":trie.allowed_token_ids(final)==(tokenizer.eos_token_id,)})
    bad=_raw("REAL_WORLD_COMMITMENT",invalid_real=True);bad_ids=tokenizer.encode(bad,add_special_tokens=False);first_blocked=None
    for index,token in enumerate(bad_ids):
        state=State().feed(tokenizer.decode(bad_ids[:index],skip_special_tokens=True))
        if token not in trie.allowed_token_ids(state): first_blocked=index;break
    passed=all(x["decoded_exact"] and not x["invalid_next_token_indices"] and x["terminal"] and x["eos_only"] for x in streams) and first_blocked is not None
    print(json.dumps({"schema_name":"pastila-semantic-admission-v2-stage-p-role-coherence-v2-real-tokenizer-preflight",
        "schema_version":"1.0.0","result":"PASS" if passed else "FAIL","vocabulary_size":len(tokenizer),
        "trie_nodes":trie.trie_node_count,"streams":streams,"observed_invalid_real_first_blocked_token_index":first_blocked,
        "elapsed_seconds":round(time.perf_counter()-started,6),"torch_imported":"torch" in sys.modules,"model_imported":False,
        "model_load_started":False,"inference_started":False,"model_calls":0,"provider_calls":0},ensure_ascii=False,separators=(",", ":")))


if __name__ == "__main__": main()
