"""Tokenizer-only preflight for the Bridge v3 structural decoder."""
from __future__ import annotations
import importlib.util,json,sys
from pathlib import Path

def constraint_types():
    path=Path(__file__).with_name('editor_core_bridge_json_constraint_v3.py')
    spec=importlib.util.spec_from_file_location('editor_core_bridge_json_constraint_v3_preflight',path)
    if spec is None or spec.loader is None: raise RuntimeError('constraint import')
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    return module.BridgeJSONStateV3,module.BridgeTokenTrieV3

def main(model:Path)->dict:
    from transformers import AutoTokenizer
    BridgeJSONStateV3,BridgeTokenTrieV3=constraint_types()
    tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,fix_mistral_regex=True)
    payload={"case_id":"fixture-1","request_identity":"sha256:"+"a"*64,"output_type":"FACTUAL",
             "authority_spans":[{"span_id":"span:1","text":"x"},{"span_id":"span:2","text":"y"}]}
    values=[{"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,
             "case_id":"fixture-1","request_identity":payload["request_identity"],"output_type":"FACTUAL",
             "outcome":"ANSWER","text":"Știrea spune «clar»: linia\nurmătoare.","claim_bindings":[{"claim_index":1,"source_span_ids":["span:1","span:2"]}],"abstention_code":None},
            {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,
             "case_id":"fixture-1","request_identity":payload["request_identity"],"output_type":"FACTUAL",
             "outcome":"ABSTAIN","text":None,"claim_bindings":[],"abstention_code":"INSUFFICIENT_AUTHORITY"}]
    pieces={item:tokenizer.decode([item],skip_special_tokens=True,clean_up_tokenization_spaces=False)
            for item in range(len(tokenizer))}
    projector=BridgeTokenTrieV3(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,
                                excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    counts=[]
    for value in values:
        text=json.dumps(value,ensure_ascii=False,separators=(',',':'))
        ids=tokenizer.encode(text,add_special_tokens=False); prefix=[]
        for token in ids:
            decoded=tokenizer.decode(prefix,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            state=BridgeJSONStateV3.start(payload).feed(decoded)
            if token not in projector.allowed_token_ids(state): raise ValueError("token projection")
            prefix.append(token)
        final=BridgeJSONStateV3.start(payload).feed(tokenizer.decode(prefix,skip_special_tokens=True,clean_up_tokenization_spaces=False))
        if projector.allowed_token_ids(final)!=(tokenizer.eos_token_id,): raise ValueError("terminal EOS")
        counts.append(len(ids))
    return {"status":"PASS","model_loaded":False,"inference":False,"streams":2,"token_counts":counts,
            "terminal_only_eos":True,"trie_nodes":len(projector.children)}

if __name__=='__main__': print(json.dumps(main(Path(sys.argv[1])),sort_keys=True))
