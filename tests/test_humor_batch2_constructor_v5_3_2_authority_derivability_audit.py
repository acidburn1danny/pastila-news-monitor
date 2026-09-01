import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
def can(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v): return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()

def test_inventory_is_complete_unique_and_has_exactly_three_classes():
    value=json.loads((ART/"humor-mechanics-batch2-constructor-v5-3-2-full-authority-derivability-audit.json").read_text(encoding="utf-8"))
    core=dict(value); identity=core.pop("audit_identity")
    assert identity==seal("B2_CONSTRUCTOR_V5_3_2_FULL_AUTHORITY_DERIVABILITY_AUDIT",core)
    fields=[x["field"] for x in value["field_inventory"]]
    assert len(fields)==len(set(fields)) and len(fields)>=60
    assert {x["authority_class"] for x in value["field_inventory"]}=={"AUTHORITY_DERIVED_METADATA","SURFACE_OBSERVED_EVIDENCE","GENUINELY_GENERATIVE_CHOICES"}
    assert value["known_same_family_plumbing_failure_remaining_before_pilot13"] is False
    assert value["zero_construction"] and value["zero_release"] and value["provider_invocations"]==0
