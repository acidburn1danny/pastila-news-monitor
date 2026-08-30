"""Verify the content-free custodial key-enrollment request."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name: str) -> tuple[dict, str]:
    raw = (ART / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict, field: str) -> str:
    body = dict(value)
    body.pop(field)
    return hashlib.sha256(canonical({"namespace": namespace, "value": body})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    packet, packet_sha = load("humor-mechanics-batch2-custodial-key-enrollment-request-v1.json")
    ledger, ledger_sha = load("humor-mechanics-batch2-custodial-access-ledger-entry-0001-key-enrollment-v1.json")
    audit, _ = load("humor-mechanics-batch2-custodial-key-enrollment-request-v1-audit.json")
    require(packet["enrollment_request_identity"] ==
            seal("B2_CUSTODIAL_KEY_ENROLLMENT_REQUEST_V1", packet, "enrollment_request_identity"),
            "packet seal invalid")
    require(ledger["entry_hash"] == seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", ledger, "entry_hash"),
            "ledger seal invalid")
    require(len(packet["requests"]) == 6, "role challenge count")
    require(len({item["principal_identity"] for item in packet["requests"]}) == 6, "principal reuse")
    require(len({item["challenge"]["challenge_identity"] for item in packet["requests"]}) == 6,
            "challenge collision")
    for item in packet["requests"]:
        require(item["owner_supplied_public_key"] is None and item["public_key_fingerprint"] is None and
                item["proof_signature"] is None and item["proof_status"] == "AWAITING_OWNER_INPUT" and
                item["registration_status"] == "NOT_REGISTERED", "key or proof fabricated")
        challenge = item["challenge"]
        require(challenge["challenge_identity"] ==
                seal("B2_CUSTODIAL_KEY_CHALLENGE_V1", challenge, "challenge_identity"),
                "challenge seal invalid")
        require(challenge["role"] == item["role"] and
                challenge["principal_identity"] == item["principal_identity"], "challenge substitution")
    require(packet["status"] == audit["verdict"] ==
            "BLOCKED_AWAITING_OWNER_PUBLIC_KEYS_AND_PROOFS", "blocked state lost")
    require(not any(packet["current_authority"].values()) and
            packet["current_authority"] == audit["authority_matrix"], "authority widened")
    require(ledger["object_identity"] == packet["enrollment_request_identity"] and
            ledger["object_sha256"] == packet_sha and ledger["keys_registered"] == 0 and
            ledger["proofs_verified"] == 0 and not ledger["operational_authority"], "ledger overclaim")
    require(audit["ledger_entry_sha256"] == ledger_sha and
            audit["enrollment_request_sha256"] == packet_sha, "audit binding mismatch")
    require(set(audit["checks"].values()) == {"PASS"} and
            audit["blocker"] == "NO_OWNER_SUPPLIED_PUBLIC_KEYS_OR_PROOF_SIGNATURES_AVAILABLE",
            "audit blocker mismatch")
    print(json.dumps({"verdict": audit["verdict"],
                      "enrollment_request_identity": packet["enrollment_request_identity"],
                      "roles_awaiting_keys": 6, "keys_registered": 0,
                      "all_action_authorities": False}, sort_keys=True))


if __name__ == "__main__":
    main()
