import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SCRIPT = ROOT / "scripts/materialize_production_core_successor_qualification_generation_v9.py"


def module():
    spec = importlib.util.spec_from_file_location("generation_v9", SCRIPT)
    value = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(value)
    return value


def test_v9_schedule_is_byte_semantically_identical_without_redraw():
    old = json.loads((ART / "production-core-successor-comparative-qualification-generation-v5.json").read_bytes())
    new = json.loads((ART / "production-core-successor-comparative-qualification-generation-v9.json").read_bytes())
    assert new["schedule"] == old["schedule"]
    assert new["schedule_lineage"] == "PREDECESSOR_ORDER_PRESERVED_NO_REDRAW"
    assert new["retry_or_redraw_authorized"] is False
    assert len(new["schedule"]) == 2400


def test_v9_generation_and_qualification_seals_are_valid():
    value = module()
    for name, field in (("production-core-successor-comparative-qualification-generation-v9.json", "qualification_generation_identity"), ("production-core-successor-candidate-generation-qualification-v9.json", "qualification_identity")):
        document = json.loads((ART / name).read_bytes()); core = dict(document); claimed = core.pop(field)
        assert claimed == hashlib.sha256(value.canonical(core)).hexdigest()
        assert document["qualification_attempt_consumed"] is False
        assert document["candidate_execution_performed"] is False
