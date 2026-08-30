"""Independently verify frozen custodial public keys, PoP, and ledger."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
REQUEST_COMMIT = "be9bd9ca812468b46cc0c0924cb5db5392ae98d4"
REQUEST_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-key-enrollment-request-v1.json"
PREVIOUS_HEAD = "4d8cc1c7907523f44d611ea4fe8e38908b3e37e97f623d3511fd02b842634642"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> tuple[dict[str, Any], str]:
    raw = (ART / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def verify_pop(registration: dict[str, Any], challenge: dict[str, Any]) -> None:
    challenge_bytes = canonical(challenge)
    require(hashlib.sha256(challenge_bytes).hexdigest() == registration["canonical_challenge_sha256"],
            f"{registration['role']}: challenge hash")
    signature = base64.b64decode(registration["proof_signature"]["value"], validate=True)
    with tempfile.TemporaryDirectory(prefix="pastila-b2-registration-") as temporary:
        root = Path(temporary)
        public = root / "public.pem"
        der = root / "public.der"
        challenge_file = root / "challenge.bin"
        signature_file = root / "signature.bin"
        public.write_text(registration["public_key"]["value"], encoding="ascii", newline="\n")
        challenge_file.write_bytes(challenge_bytes)
        signature_file.write_bytes(signature)
        run(["openssl", "pkey", "-pubin", "-in", str(public), "-outform", "DER", "-out", str(der)])
        require(hashlib.sha256(der.read_bytes()).hexdigest() == registration["public_key_fingerprint"],
                f"{registration['role']}: fingerprint")
        if registration["algorithm"] == "ED25519":
            run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public),
                 "-in", str(challenge_file), "-sigfile", str(signature_file)])
        elif registration["algorithm"] == "ECDSA_P256_SHA256":
            run(["openssl", "dgst", "-sha256", "-verify", str(public), "-signature",
                 str(signature_file), str(challenge_file)])
        else:
            raise SystemExit(f"{registration['role']}: algorithm")


def main() -> None:
    registration, registration_sha = load("humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    ledger, ledger_sha = load("humor-mechanics-batch2-custodial-public-key-registration-ledger-v1.json")
    audit, _ = load("humor-mechanics-batch2-custodial-public-key-registration-v1-audit.json")
    request = json.loads(subprocess.check_output(
        ["git", "show", f"{REQUEST_COMMIT}:{REQUEST_PATH}"], cwd=ROOT))
    request_by_role = {item["role"]: item for item in request["requests"]}
    core = {
        "enrollment_request_commit": registration["enrollment_request_commit"],
        "enrollment_request_identity": registration["enrollment_request_identity"],
        "runbook_commit": registration["runbook_commit"],
        "previous_ledger_head": registration["previous_ledger_head"],
        "registrations": registration["registrations"],
    }
    require(registration["registration_core_identity"] ==
            seal("B2_CUSTODIAL_PUBLIC_KEY_REGISTRATION_CORE_V1", core), "registration core seal")
    unsealed = dict(registration)
    identity = unsealed.pop("registration_identity")
    require(identity == seal("B2_CUSTODIAL_PUBLIC_KEY_REGISTRATION_V1", unsealed),
            "registration artifact seal")
    require(registration["enrollment_request_identity"] ==
            request["enrollment_request_identity"], "request identity")
    fingerprints, public_keys = set(), set()
    for item in registration["registrations"]:
        request_item = request_by_role[item["role"]]
        require(item["principal_identity"] == request_item["principal_identity"] and
                item["challenge_identity"] == request_item["challenge"]["challenge_identity"],
                f"{item['role']}: request binding")
        verify_pop(item, request_item["challenge"])
        require(item["proof_of_possession"] == "VERIFIED" and
                item["owner_confirmation"]["confirmed"] is True and
                item["owner_confirmation"]["public_key_fingerprint"] == item["public_key_fingerprint"] and
                not item["operational_access"], f"{item['role']}: registration state")
        fingerprints.add(item["public_key_fingerprint"])
        public_keys.add(item["public_key"]["value"])
    require(len(fingerprints) == len(public_keys) == 6, "duplicate role key")
    ledger_unsealed = dict(ledger)
    ledger_identity = ledger_unsealed.pop("ledger_segment_identity")
    require(ledger_identity == seal("B2_CUSTODIAL_REGISTRATION_LEDGER_SEGMENT_V1", ledger_unsealed),
            "ledger segment seal")
    previous = PREVIOUS_HEAD
    require(ledger["previous_ledger_head"] == previous and len(ledger["entries"]) == 6,
            "ledger segment start/count")
    for expected_sequence, entry in enumerate(ledger["entries"], start=2):
        entry_unsealed = dict(entry)
        entry_hash = entry_unsealed.pop("entry_hash")
        require(entry["entry_sequence"] == expected_sequence and
                entry["previous_entry_hash"] == previous and
                entry_hash == seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry_unsealed) and
                entry["proof_of_possession"] == "VERIFIED" and not entry["operational_access"],
                f"ledger sequence {expected_sequence}")
        previous = entry_hash
    require(previous == ledger["final_ledger_head"] ==
            registration["access_ledger_identity"], "final ledger head")
    require(registration["ledger_segment_identity"] == ledger_identity, "registration ledger binding")
    require(audit["registration_identity"] == registration["registration_identity"] and
            audit["registration_sha256"] == registration_sha and
            audit["ledger_sha256"] == ledger_sha and
            audit["access_ledger_identity"] == previous, "audit binding")
    require(audit["verdict"] == "PASS_SIX_PUBLIC_KEYS_REGISTERED_POP_VERIFIED_NONOPERATIONAL" and
            audit["duplicate_keys"] == audit["private_keys_accessed"] == audit["keys_generated"] ==
            audit["signatures_generated"] == 0 and not audit["operational_access"] and
            not audit["deterministic_defects_remaining"], "audit state")
    require(not any(registration["authority_matrix"].values()), "authority widened")
    print(json.dumps({
        "verdict": audit["verdict"], "registration_identity": registration["registration_identity"],
        "access_ledger_identity": previous,
        "bindings": [{"role": item["role"], "fingerprint": item["public_key_fingerprint"],
                      "proof_of_possession": "VERIFIED"} for item in registration["registrations"]],
        "operational_access": False, "all_action_authorities": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
