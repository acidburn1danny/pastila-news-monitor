import json
from pathlib import Path
import pytest
from scripts.build_editor_vnext_voice_bakeoff_authority_v1 import BOUNDARY, SOURCE_COMMIT, audit, identify
from scripts.preflight_editor_vnext_voice_bakeoff_authority_v1 import preflight

P=Path("docs/artifacts/editor-vnext-voice-bakeoff-execution-authority-v1.json")
def value(): return json.loads(P.read_text())
def test_authority_audit(): assert audit(Path("."))["grants"]==216
def test_frozen_binding():
    a=value(); assert a["boundary_identity"]==BOUNDARY and a["published_boundary_commit"]==SOURCE_COMMIT
def test_each_slot_once_and_no_retry():
    g=value()["grants"]; assert len(g)==len({x["slot_identity"] for x in g})==216; assert all(x["attempt_ceiling"]==1 and not x["retry"] for x in g)
def test_runtime_isolation_and_zero_execution():
    a=value(); assert a["runtime_isolation"]["answer_key_access"]=="FORBIDDEN"; assert a["execution"]=={"authorized":False,"generation":False,"inference":False,"model_load":False,"outputs_completed":0,"quantization_execution":False}
def test_tamper_changes_identity():
    a=value(); a["matrix"]["slots"]=217; assert identify(a,"authority_identity")["authority_identity"]!=a["authority_identity"]
def test_preflight_rejects_existing_output_root():
    with pytest.raises(ValueError,match="new and absent"): preflight(Path("."),Path("."))
