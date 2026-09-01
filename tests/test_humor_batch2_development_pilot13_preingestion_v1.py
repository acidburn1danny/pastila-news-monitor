import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def _json(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def _seal(namespace: str, value: object) -> str:
    payload = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def test_pilot13_unsigned_preparation_is_coordinate_bound_and_nonselecting() -> None:
    source_bytes = (ROOT / "owner-source-pilot13-v1.txt").read_bytes()
    source = source_bytes.decode("utf-8")
    prospective = _json("humor-mechanics-batch2-development-pilot13-preingestion-v1.json")
    packet = _json("humor-mechanics-batch2-development-pilot13-signing-packet-v1.json")
    propositions = prospective["factual_authority_envelope"]["propositions"]

    assert hashlib.sha256(source_bytes).hexdigest() == prospective["source_sha256"]
    assert len(propositions) == 8
    assert prospective["proposition_binding_status"] == "PASS_8_BOUND_NOT_SELECTED"
    assert prospective["selected_proposition"] == "UNASSIGNED"
    assert prospective["proposition_sufficiency_evaluated"] is False
    for proposition in propositions:
        for key in ("supporting_span", "subject", "predicate", "object"):
            witness = proposition[key]
            start, end = witness["character_coordinates"]
            bstart, bend = witness["utf8_byte_coordinates"]
            assert source[start:end].encode("utf-8") == source_bytes[bstart:bend]
            assert hashlib.sha256(source_bytes[bstart:bend]).hexdigest() == witness["sha256"]

    assert packet["status"] == "UNSIGNED"
    assert packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["packet_identity"] == _seal("B2_DEVELOPMENT_PILOT13_SIGNING_PACKET_V1", packet["packet_core"])
    assert prospective["preingestion_identity"] == _seal(
        "B2_DEVELOPMENT_PILOT13_PREINGESTION_V1",
        {key: value for key, value in prospective.items() if key != "preingestion_identity"},
    )


def test_pilot13_owner_inputs_remain_untracked() -> None:
    status = subprocess.check_output(
        ["git", "status", "--short", "--", "owner-source-pilot13-v1.txt", "owner-declaration-pilot13-v1.json"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert set(status) == {"?? owner-source-pilot13-v1.txt", "?? owner-declaration-pilot13-v1.json"}
