import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"docs/artifacts"
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v):return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()
def test_pilot13_validation_is_identity_bound_and_non_authorizing():
    value=json.loads((ART/"humor-mechanics-batch2-development-pilot13-strict-preingestion-validation-v1.json").read_text(encoding="utf-8"));core=dict(value);identity=core.pop("validation_identity")
    assert identity==seal("B2_DEVELOPMENT_PILOT13_STRICT_PREINGESTION_VALIDATION_V1",core)
    assert value["validation_verdict"]=="PASS_STRICT_PREINGESTION_VALIDATION_ONLY" and value["bindable_factual_statement_candidates"]==8
    assert value["deterministic_blockers"]==[] and value["repair_performed"] is False
    assert value["proposition_binding_selection_or_sufficiency_performed"] is False and value["downstream_suitability_evaluated"] is False
    assert all(x is False for x in value["authority_matrix"].values())
    assert hashlib.sha256((ROOT/"owner-source-pilot13-v1.txt").read_bytes()).hexdigest()==value["source_sha256"]
    assert hashlib.sha256((ROOT/"owner-declaration-pilot13-v1.json").read_bytes()).hexdigest()==value["declaration_sha256"]
    status=subprocess.check_output(["git","status","--short","--","owner-source-pilot13-v1.txt","owner-declaration-pilot13-v1.json"],cwd=ROOT,text=True)
    assert "?? owner-source-pilot13-v1.txt" in status and "?? owner-declaration-pilot13-v1.json" in status
