import importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/materialize_production_core_v10_unified_execution_design.py"

def module():
    spec=importlib.util.spec_from_file_location("v10_design",SCRIPT); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def test_design_reproduces_and_preserves_zero_execution():
    m=module(); published=json.loads(m.OUTPUT.read_bytes()); assert m.build()==published
    schema=json.loads((ROOT/"docs/schemas/production-core-v10-unified-execution-contract-design.schema.json").read_bytes())
    Draft202012Validator(schema).validate(published)
    assert published["root_cause"]=="NON_REPRESENTATIVE_DEVELOPMENT_GATE_PROMPT_AND_DISTRIBUTION_MISMATCH"
    assert published["v9_evidence"]["deterministic_v1_1_overflow_cases"]=={"pcq-eos-007":6,"pcq-eos-009":6,"pcq-eos-013":6,"pcq-eos-014":6}
    assert published["training_authorized"] is False and published["training_performed"] is False
    assert published["qualification_execution_authorized"] is False
    assert published["qualification_attempt_consumed"] is False
    assert published["promotion_effect"] is False
