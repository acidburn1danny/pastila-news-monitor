import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SCRIPT=ROOT/"scripts/materialize_production_core_v10_token_audit_receipt.py"; ART=ROOT/"docs/artifacts"

def module():
 spec=importlib.util.spec_from_file_location("v10_token_receipt",SCRIPT);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def test_receipt_reproduces_and_records_no_execution():
 m=module();published=json.loads(m.OUTPUT.read_bytes());assert m.build(m.EVIDENCE)==published
 assert published["status"]=="PASS_ZERO_BLOCKERS_TOKENIZER_ONLY_ZERO_MODEL_LOAD"
 assert published["model_loaded"] is False and published["inference_performed"] is False
 assert published["training_authorized"] is False and published["training_performed"] is False
 assert published["qualification_attempt_consumed"] is False and published["promotion_effect"] is False
 assert len(published["token_materialization_evidence_identity"])==64
