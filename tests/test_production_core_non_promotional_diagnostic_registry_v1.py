import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ARTIFACT = (
    ROOT
    / "docs/artifacts/production-core-non-promotional-diagnostic-adjudicator-registry-v1.json"
)


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def test_replacement_registry_is_content_bound_and_non_promotional():
    value = json.loads(ARTIFACT.read_bytes())
    identity = value.pop("registry_identity")
    assert identity == hashlib.sha256(canonical(value)).hexdigest()
    assert value["purpose"] == "NON_PROMOTIONAL_DIAGNOSTIC"
    assert (
        value["supersedes_registry_identity"]
        == "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
    )
    assert value["historical_evidence_mutated"] is False
    assert value["hard_gate_compensation_permitted"] is False
    assert value["candidate_promotion_effect"] is False
    assert value["retry_or_redraw_permitted"] is False
    assert value["new_run_authorized"] is False


def test_b02_public_key_is_exact_ed25519_and_distinct_from_a():
    value = json.loads(ARTIFACT.read_bytes())
    a = value["roles"]["ADJUDICATOR_A"]
    b = value["roles"]["ADJUDICATOR_B"]
    a_raw = base64.b64decode(a["public_key_pem_base64"], validate=True)
    raw = base64.b64decode(b["public_key_pem_base64"], validate=True)
    assert b["adjudicator_id"] == "EVALUATOR-B-02"
    assert (
        hashlib.sha256(raw).hexdigest()
        == b["public_key_sha256"]
        == "3a93216b56f3ba932836a759e669437b03eabe3817ec5497e6beb7390cf4e8a9"
    )
    assert raw.split(b"\r\n")[-1] == b""
    der = base64.b64decode(raw.split(b"\r\n")[1], validate=True)
    assert len(der) == 44
    assert der.startswith(bytes.fromhex("302a300506032b6570032100"))
    assert a["adjudicator_id"] != b["adjudicator_id"]
    assert a["public_key_sha256"] != b["public_key_sha256"]
    assert hashlib.sha256(a_raw).hexdigest() == a["public_key_sha256"]
    assert a["public_key_format"] == b["public_key_format"]


def test_historical_registry_remains_unchanged():
    historical = (
        ROOT
        / "docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json"
    )
    expected = "9c0371fdbf5a455ac740f736b7733bab784422c177fd2a4534071e6f1a74327c"
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == expected
    value = json.loads(ARTIFACT.read_bytes())
    assert value["historical_registry_artifact_sha256"] == expected
