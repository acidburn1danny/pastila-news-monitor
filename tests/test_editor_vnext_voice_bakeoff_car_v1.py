import json
from pathlib import Path
from scripts.build_editor_vnext_voice_bakeoff_car_authority_v1 import audit,identify
P=Path("docs/artifacts")
def test_car_audit(): assert audit(Path("."))["rows"]==216
def test_dispatch_complete_balanced_unique():
 r=[json.loads(x) for x in (P/"editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl").read_text().splitlines()]; assert len(r)==len({x["slot_identity"] for x in r})==216; assert sorted(sum(x["candidate_id"]==c for x in r) for c in {x["candidate_id"] for x in r})==[72,72,72]
def test_dispatch_bound_to_revision_tokenizer():
 assert all(x["revision"] and len(x["tokenizer_sha256"])==64 for x in [json.loads(y) for y in (P/"editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl").read_text().splitlines()])
def test_answer_key_not_dependency():
 a=json.loads((P/"editor-vnext-voice-bakeoff-car-execution-authority-v1.json").read_text()); assert a["dispatch"]["review_answer_key_dependency"] is False and a["isolation"]["review_answer_key_access"]=="FORBIDDEN"
def test_tamper_identity():
 a=json.loads((P/"editor-vnext-voice-bakeoff-car-execution-authority-v1.json").read_text()); a["matrix"]["slots"]=215; assert identify(a,"successor_authority_identity")["successor_authority_identity"]!=a["successor_authority_identity"]
def test_worker_is_inference_only():
 s=Path("scripts/run_editor_vnext_voice_bakeoff_car_v1.py").read_text(); assert "model.generate" in s and "optimizer" not in s.lower().replace('"optimizer":false','') and "train(" not in s
def test_atomic_publication_is_durable():
 s=Path("scripts/run_editor_vnext_voice_bakeoff_car_v1.py").read_text(); assert "stream.flush()" in s and "os.fsync(stream.fileno())" in s and "tmp.replace(path)" in s
