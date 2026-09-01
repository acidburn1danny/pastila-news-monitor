import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot12_validation_is_sealed_byte_exact_and_non_authorizing():
    artifact = json.loads((ART / "humor-mechanics-batch2-development-pilot12-strict-preingestion-validation-v1.json").read_text(encoding="utf-8"))
    core = dict(artifact); identity = core.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_STRICT_PREINGESTION_VALIDATION_V1", core)
    assert artifact["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert artifact["source_sha256"] == hashlib.sha256((ROOT / "owner-source-pilot12-v1.txt").read_bytes()).hexdigest()
    assert artifact["declaration_sha256"] == hashlib.sha256((ROOT / "owner-declaration-pilot12-v1.json").read_bytes()).hexdigest()
    assert artifact["checks"]["eight_independently_bindable_statement_candidates"] == "PASS_NOT_YET_BOUND"
    assert artifact["checks"]["pilot01_through_11_exact_source_and_line_independence"] == "PASS"
    assert artifact["deterministic_blockers"] == [] and artifact["repair_performed"] is False
    assert artifact["prospective_identities_derived"] is False
    assert all(value is False for value in artifact["authority_matrix"].values())
