from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from editor_core_bridge_json_constraint_v3 import BridgeJSONStateV3, BridgeTokenTrieV3
from generate_editor_core_bridge_causal_responses_v3 import persist_failure, validate_generated_response
from supervise_editor_core_bridge_causal_inference_v3 import Journal

PAYLOAD={"case_id":"case-1","request_identity":"sha256:"+"a"*64,"output_type":"FACTUAL",
         "authority_spans":[{"span_id":"span:1","text":"x"},{"span_id":"span:2","text":"y"}]}

def answer()->str:
    return json.dumps({"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,
        "case_id":PAYLOAD["case_id"],"request_identity":PAYLOAD["request_identity"],"output_type":"FACTUAL",
        "outcome":"ANSWER","text":"Text factual.","claim_bindings":[{"claim_index":1,"source_span_ids":["span:1"]}],
        "abstention_code":None},ensure_ascii=False,separators=(',',':'))

def abstain()->str:
    return json.dumps({"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,
        "case_id":PAYLOAD["case_id"],"request_identity":PAYLOAD["request_identity"],"output_type":"FACTUAL",
        "outcome":"ABSTAIN","text":None,"claim_bindings":[],"abstention_code":"INSUFFICIENT_AUTHORITY"},
        separators=(',',':'))

@pytest.mark.parametrize('text',[answer(),abstain()])
def test_structural_dfa_accepts_only_complete_json(text:str):
    state=BridgeJSONStateV3.start(PAYLOAD).feed(text)
    assert state.can_eos
    assert validate_generated_response(text,PAYLOAD,True)
    with pytest.raises(ValueError,match='TRAILING'):
        state.feed('x')

@pytest.mark.parametrize('text',[answer()[:-1],answer().replace('"case_id"','"wrong"',1),
                                  answer().replace('span:1','unknown',1),'```'+answer()])
def test_structural_dfa_rejects_truncation_order_unknown_span_and_fence(text:str):
    try: state=BridgeJSONStateV3.start(PAYLOAD).feed(text)
    except ValueError: return
    assert not state.can_eos

def test_trie_allows_eos_only_at_terminal():
    chars=sorted(set(answer()))
    trie=BridgeTokenTrieV3(token_pieces={i:char for i,char in enumerate(chars)},eos_token_id=999)
    assert 999 not in trie.allowed_token_ids(BridgeJSONStateV3.start(PAYLOAD))
    assert trie.allowed_token_ids(BridgeJSONStateV3.start(PAYLOAD).feed(answer()))==(999,)

def test_failure_evidence_has_case_without_invalid_payload(tmp_path:Path):
    row={"example_id":"case-1"}
    failure=persist_failure(tmp_path,candidate='r2',row=row,payload=PAYLOAD,index=4,exc=ValueError('secret invalid payload'))
    assert failure['case_id']=='case-1' and failure['index']==4
    assert failure['invalid_payload_persisted'] is False and failure['receipt_persisted'] is False
    raw=(tmp_path/'failure.json').read_text('utf-8')
    assert 'secret invalid payload' not in raw
    assert {p.name for p in tmp_path.iterdir()}=={'failure.json'}
    with pytest.raises(ValueError,match='not empty'):
        persist_failure(tmp_path,candidate='r2',row=row,payload=PAYLOAD,index=4,exc=ValueError())

def test_post_validator_rejects_duplicate_key_and_request_substitution():
    duplicate=answer().replace('{"schema":','{"schema":"x","schema":',1)
    with pytest.raises(ValueError): validate_generated_response(duplicate,PAYLOAD,True)
    changed=answer().replace('"case_id":"case-1"','"case_id":"other"')
    with pytest.raises(ValueError,match='binding'): validate_generated_response(changed,PAYLOAD,True)
    with pytest.raises(ValueError,match='EOS'): validate_generated_response(answer(),PAYLOAD,False)

def test_supervisor_terminal_is_unique_and_audit_precedes_packets(tmp_path:Path):
    journal=Journal(tmp_path); journal.write('PROGRAM_START'); journal.write('PROGRAM_END',status='BLOCKED')
    with pytest.raises(RuntimeError,match='terminal'): journal.write('PROGRAM_END',status='PASS')
    source=(ROOT/'scripts/supervise_editor_core_bridge_causal_inference_v3.py').read_text('utf-8')
    assert source.index('inference = audit(')<source.index('prepared = prepare(')

def test_candidate_neutral_constraint():
    assert BridgeJSONStateV3.start(PAYLOAD)==BridgeJSONStateV3.start(dict(PAYLOAD))

def test_no_generic_repetition_constraint_in_worker():
    source=(ROOT/'scripts/generate_editor_core_bridge_causal_responses_v3.py').read_text('utf-8')
    assert 'no_repeat_ngram_size' not in source
    assert 'prefix_allowed_tokens_fn=allowed' in source

def test_v3_audit_rejects_historical_v1_and_failed_v2():
    from audit_editor_core_bridge_causal_responses_v3 import audit
    authority=json.loads((ROOT/'docs/artifacts/editor-core-editorial-bridge-causal-inference-authority-v2.json').read_bytes())
    identities={row['candidate']:row['adapter_sha256'] for row in authority['candidates']}
    requests=ROOT/'docs/artifacts/editor-core-editorial-mechanics-bridge-v1-development-requests.jsonl'
    for root in (Path('/root/pf9-editor-core-bridge-causal-inference-v1'),Path('/root/pf9-editor-core-bridge-causal-inference-v2')):
        if root.exists():
            with pytest.raises(ValueError): audit(root,requests,identities)

def test_v3_authority_identity_and_source_closure():
    path=ROOT/'docs/artifacts/editor-core-editorial-bridge-causal-inference-authority-v3.json'
    value=json.loads(path.read_bytes()); core={k:v for k,v in value.items() if k!='authority_identity'}
    identity=hashlib.sha256(json.dumps(core,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert value['authority_identity']==identity and value['no_repeat_ngram_size'] is None
    for name in ('worker','route','audit','verifier','supervisor','constraint','preflight','design'):
        assert hashlib.sha256((ROOT/value[name+'_path']).read_bytes()).hexdigest()==value[name+'_sha256']
