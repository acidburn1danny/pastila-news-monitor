"""Exact-tokenizer, zero-model differential and performance gate for projector V2."""
from __future__ import annotations
import hashlib, json, statistics, sys, time, types
from pathlib import Path

ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"

def percentile(values, fraction):
    return sorted(values)[min(len(values)-1, int((len(values)-1)*fraction))]

def main():
    sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
    if "pytest" not in sys.modules:
        stub=types.ModuleType("pytest"); stub.mark=types.SimpleNamespace(parametrize=lambda *a,**k:(lambda f:f))
        stub.raises=lambda *a,**k:None; sys.modules["pytest"]=stub
    from transformers import AutoTokenizer
    from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context,_valid_text
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1 as C
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v1 import StagePConstructionObligationV2TokenProjectorV1 as V1,StagePTokenProjectionFailureV1
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v2 import StagePConstructionObligationV2TokenProjectorV2 as V2
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    identity="sha256:"+hashlib.sha256(f"{MODEL}\n{len(tok)}".encode()).hexdigest()
    if identity != TOKENIZER_IDENTITY or len(tok)!=131072: raise SystemExit("TOKENIZER_IDENTITY_MISMATCH")
    decode=lambda ids:tok.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    pieces={i:decode([i]) for i in range(len(tok))}
    excluded=(set(tok.all_special_ids)-{tok.eos_token_id})|{i for i,p in pieces.items() if not p}
    context,_,_=_case_context(); raw=_valid_text(context)
    kwargs=dict(token_pieces=pieces,eos_token_id=tok.eos_token_id,tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,request_context_identity=context.binding_identity,excluded_token_ids=excluded)
    def make(kind):
        bound=dict(kwargs)
        if kind is V2: bound["request_authority_identity"]="authority:case01-zero-model-audit"
        return kind(controller=C(context=context,decoder_identity=DECODER_IDENTITY),**bound)
    positions=[0,1,raw.index('"overall_disposition":"')+len('"overall_disposition":"'),
        raw.index('"role_basis":"')+len('"role_basis":"'),raw.index('"candidate_span_ref":')+len('"candidate_span_ref":'),
        raw.index('},{"entry_id":"P2"')+1,len(raw)]
    comparisons=[]; divergences=0
    for pos in positions:
        ids=tok.encode(raw[:pos],add_special_tokens=False); a,b=make(V1),make(V2)
        def outcome(p):
            try:
                x=p.allowed_token_ids(ids,decode); return ("OK",x.token_ids,x.receipt.eos_allowed,x.receipt.terminal,x.receipt.reason_code)
            except StagePTokenProjectionFailureV1 as e:
                return ("FAIL",(),e.receipt.eos_allowed,e.receipt.terminal,e.receipt.reason_code)
        left=outcome(a); start=time.perf_counter_ns(); right=outcome(b); elapsed=time.perf_counter_ns()-start
        divergences += left != right
        comparisons.append({"position":pos,"equal":left==right,"allowed":len(right[1]),"optimized_ns":elapsed})
    ids=tok.encode(raw,add_special_tokens=False)
    if len(ids)<512: raise SystemExit("REALISTIC_SEQUENCE_TOO_SHORT")
    projector=make(V2); replay_oracle=make(V1); latencies=[]; wrapper=[]; telemetry=[]
    replay_divergences=0; oracle_seconds=0.0
    for count in range(512):
        prefix=ids[:count]
        oracle_started=time.perf_counter()
        expected=replay_oracle.allowed_token_ids(prefix,decode)
        oracle_seconds += time.perf_counter()-oracle_started
        outer=time.perf_counter_ns(); start=time.perf_counter_ns()
        observed=projector.allowed_token_ids(prefix,decode)
        projected=time.perf_counter_ns()-start
        replay_divergences += expected != observed
        publish_start=time.perf_counter_ns(); json.dumps({"count":count,"duration":projected},sort_keys=True,separators=(",",":"))
        published=time.perf_counter_ns()-publish_start
        latencies.append(projected); telemetry.append(published); wrapper.append(time.perf_counter_ns()-outer)
    divergences += replay_divergences
    result={"result":"PASS" if divergences==0 and statistics.median(latencies)<50_000_000 and percentile(latencies,.99)<100_000_000 else "FAIL",
      "activity":{"tokenizer_loads":1,"model_loads":0,"adapter_loads":0,"inference_calls":0,"wsl_generation_calls":0},
      "tokenizer_identity":identity,"vocabulary_size":len(tok),"differential_comparisons":comparisons,
      "divergences":divergences,"callbacks":512,"long_replay_comparisons":512,
      "long_replay_divergences":replay_divergences,"oracle_replay_seconds":oracle_seconds,
      "projection_ns":{"median":int(statistics.median(latencies)),"p95":percentile(latencies,.95),"p99":percentile(latencies,.99),"max":max(latencies)},
      "wrapper_ns":{"median":int(statistics.median(wrapper)),"p99":percentile(wrapper,.99)},
      "telemetry_publication_ns":{"median":int(statistics.median(telemetry)),"p99":percentile(telemetry,.99)},
      "callbacks_per_second":1e9/statistics.mean(latencies),"projected_3200_callback_seconds":statistics.mean(latencies)*3200/1e9,
      "trie_nodes":projector.trie_node_count,"statistics":projector.statistics.__dict__ if hasattr(projector.statistics,"__dict__") else {
        "cache_hits":projector.statistics.cache_hits,"cache_misses":projector.statistics.cache_misses,
        "visited_trie_nodes":projector.statistics.visited_trie_nodes,"admitted_terminal_tokens":projector.statistics.admitted_terminal_tokens}}
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    if result["result"]!="PASS": raise SystemExit(1)
if __name__=="__main__": main()
