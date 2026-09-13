import importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/materialize_production_core_v9_terminal_disposition.py"

def module():
    spec=importlib.util.spec_from_file_location("v9_disposition",SCRIPT); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def test_published_disposition_reproduces_and_is_non_promotional():
    m=module(); observed=m.build(); published=json.loads(m.OUTPUT.read_bytes())
    assert observed==published
    schema=json.loads((ROOT/"docs/schemas/production-core-v9-terminal-disposition.schema.json").read_bytes())
    Draft202012Validator(schema).validate(published)
    assert published["status"]=="TERMINAL_STRUCTURAL_REJECTION_BOTH_CANDIDATES"
    assert published["evidence"]["structural_status_counts"]=={"FAIL_CLOSED_INVALID_OUTPUT":2400}
    assert published["semantic_adjudication_performed"] is False
    assert published["promotion_effect"] is False

def test_wrong_attempt_is_rejected(tmp_path):
    m=module(); attempt=json.loads((m.EXECUTION/"attempt.json").read_bytes()); attempt["attempt_identity"]="0"*64
    (tmp_path/"attempt.json").write_bytes(m.canonical(attempt)); (tmp_path/"completion.json").write_bytes((m.EXECUTION/"completion.json").read_bytes())
    try: m.build(tmp_path)
    except ValueError: pass
    else: raise AssertionError("wrong attempt accepted")
