import importlib.util,json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/"scripts/materialize_production_core_v10_terminal_failure_evidence.py"
DISPOSITION=ROOT/"docs/artifacts/production-core-v10-terminal-failure-disposition.json";ADDENDUM=ROOT/"docs/artifacts/production-core-v10-root-cause-addendum.json"
def module():
 spec=importlib.util.spec_from_file_location("v10_failure_evidence",SCRIPT);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def test_published_evidence_reproduces_and_validates():
 m=module();d,a=m.build();assert json.loads(DISPOSITION.read_bytes())==d;assert json.loads(ADDENDUM.read_bytes())==a
 Draft202012Validator(json.loads((ROOT/"docs/schemas/production-core-v10-terminal-failure-disposition.schema.json").read_bytes())).validate(d)
 Draft202012Validator(json.loads((ROOT/"docs/schemas/production-core-v10-root-cause-addendum.schema.json").read_bytes())).validate(a)
 assert d["attempt_consumed_permanently"] is True and d["root_cause_determined"] is False
 assert a["execution_boundary_cause"]=="WSL_EXECUTION_BOUNDARY_SIGBUS_DURING_MODEL_SNAPSHOT" and a["internal_sigbus_cause"]=="UNDETERMINED"
 assert a["retry_or_redraw"] is a["adjudication_performed"] is a["promotion_effect"] is False
 assert d["disposition_identity"]==m.identity({k:v for k,v in d.items() if k!="disposition_identity"})
 assert a["addendum_identity"]==m.identity({k:v for k,v in a.items() if k!="addendum_identity"})
def test_tampered_stderr_is_rejected(tmp_path):
 m=module();p=tmp_path/"stderr.log";p.write_bytes(m.STDERR.read_bytes()+b"x")
 with pytest.raises(ValueError,match="evidence drift"):m.build(stderr_path=p)
