import hashlib, importlib.util, json
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[1]
def load():
    p=ROOT/"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py"; s=importlib.util.spec_from_file_location("rt",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class Tok:
    def __call__(self,text,**_): return {"input_ids":list(range(len(text))),"offset_mapping":[(i,i+1) for i in range(len(text))]}

class ChatTok(Tok):
    def apply_chat_template(self,messages,tokenize,add_generation_prompt):
        text="".join(x["content"] for x in messages[:2])+"<assistant>"+("" if len(messages)==2 else messages[2]["content"])+("" if add_generation_prompt or len(messages)==2 else "<eos>")
        return list(range(len(text))) if tokenize else text

class BatchChatTok(ChatTok):
    def apply_chat_template(self,messages,tokenize,add_generation_prompt):
        value=super().apply_chat_template(messages,tokenize,add_generation_prompt)
        return {"input_ids":value,"attention_mask":[1]*len(value)} if tokenize else value

def test_inventory_and_axis_isolation():
    m=load(); assert len(m.ARMS)*len(m.SEEDS)==12
    assert {v[0] for v in m.ARMS.values()}=={"T0","T1"}; assert {v[1] for v in m.ARMS.values()}=={"5e-7","1e-6"}
    assert m.row_order(161803)==m.row_order(161803) and m.row_order(161803)!=m.row_order(271828)

def test_real_mapping_and_fail_closed(tmp_path):
    m=load(); assistant='{"case_id":"x","text":"Actorul păstrează calificarea."}'
    a=assistant.index("Actorul"); span={"field":"text","start":a,"end":a+7,"text":"Actorul"}
    got=m.real_token_map(Tok(),assistant,[span]); assert got["mapped_spans"][0]["token_start"]==a
    with pytest.raises(ValueError): m.real_token_map(Tok(),assistant,[{**span,"text":"greșit"}])
    with pytest.raises(RuntimeError): m.run_slot(*([Path("x")]*6),"T0_CONTROL_S0_CONTROL",161803)

def test_chat_mapping_uses_structural_assistant_boundary():
    m=load(); assistant='{"case_id":"x","text":"Actor calificat."}'; messages=[{"role":"system","content":"s"},{"role":"user","content":assistant},{"role":"assistant","content":assistant}]; a=assistant.index("Actor")
    got=m.real_chat_token_map(ChatTok(),messages,[{"field":"text","start":a,"end":a+5,"text":"Actor"}])
    expected=len("s"+assistant+"<assistant>"); assert got["assistant_token_start"]==expected; assert got["mapped_spans"][0]["token_start"]==expected+a
    assert m.real_chat_token_map(BatchChatTok(),messages,[{"field":"text","start":a,"end":a+5,"text":"Actor"}])==got

def test_fixture_receipts_and_no_partial(tmp_path):
    m=load(); out=tmp_path/"out"; out.mkdir(); assistant='{"case_id":"x","text":"Fapt calificat."}'; a=assistant.index("Fapt")
    terminal=m.fixture_run(Tok(),assistant,{"critical_spans":[{"field":"text","start":a,"end":a+4,"text":"Fapt"}]},out,"T1_CONTRACT_WEIGHTED_S0_CONTROL",161803)
    assert terminal["optimizer_steps"]==0 and {p.name for p in out.iterdir()}=={"mapping.json","teacher-forced.json","adapter-delta.json","semantic.json","terminal.json"}
    with pytest.raises(ValueError): m.fixture_run(Tok(),assistant,{"critical_spans":[]},out,"T1_CONTRACT_WEIGHTED_S0_CONTROL",161803)

def test_source_has_no_top_level_ml_import():
    text=(ROOT/"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py").read_text(encoding="utf-8")
    assert "    import torch" in text and "\nimport torch" not in text

def test_all_published_critical_spans_map_inside_assistant_text():
    m=load()
    corpus={r["example_id"]:r for r in map(json.loads,(ROOT/"docs/artifacts/editor-core-factual-setup-corrective-v1-training.jsonl").read_text(encoding="utf-8").splitlines())}
    challenger=list(map(json.loads,(ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl").read_text(encoding="utf-8").splitlines()))
    mapped=0
    for row in challenger:
        assistant=corpus[row["example_id"]]["messages"][2]["content"]
        assert hashlib.sha256(assistant.encode()).hexdigest()==row["assistant_target_sha256"]
        got=m.real_token_map(Tok(),assistant,row["critical_spans"]); mapped += len(got["mapped_spans"])
    assert len(challenger)==72 and mapped>0
