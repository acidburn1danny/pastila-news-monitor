from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-strict-preingestion-validation-v1.json"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_pilot08_validation_passes_strictly_without_downstream_authority() -> None:
    value = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(value)
    identity = core.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_STRICT_PREINGESTION_VALIDATION_V1", core)
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["deterministic_blockers"] == []
    assert value["checks"]["hashes"] == "PASS"
    assert value["checks"]["exact_schema_shape"] == "PASS"
    assert value["checks"]["owner_rights_and_independent_grants"] == "PASS"
    assert value["checks"]["pilot01_through_07_exact_source_and_line_independence"] == "PASS"
    assert value["checks"]["source_exactly_one_terminal_lf"] == "PASS"
    assert value["checks"]["declaration_exactly_one_terminal_lf"] == "PASS"
    assert value["repair_performed"] is False
    assert value["proposition_sufficiency_evaluated"] is False
    assert value["prospective_identities_derived"] is False
    assert not any(value["authority_matrix"].values())
