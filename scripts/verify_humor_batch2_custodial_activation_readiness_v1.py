"""Independent verifier for frozen content-free activation readiness."""

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
REQUEST_COMMIT = "a1f78df7a3e06feb98d2e134e9819ec6cf1ff875"
REGISTRATION_COMMIT = "cab04b6e43b13fefe6ab048b6ac8c7dbabe630b7"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def load(name: str) -> tuple[dict[str, Any], str]:
    raw = (ART / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def verify_signature(public_pem: str, algorithm: str, challenge: bytes, signature: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-readiness-") as temporary:
        root = Path(temporary)
        public, message, proof = root / "public.pem", root / "message.bin", root / "proof.bin"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        message.write_bytes(challenge)
        proof.write_bytes(signature)
        command = (["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public),
                    "-in", str(message), "-sigfile", str(proof)]
                   if algorithm == "ED25519" else
                   ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature",
                    str(proof), str(message)])
        require(subprocess.run(command, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL).returncode == 0, "signature")


def main() -> None:
    evidence, evidence_sha = load("humor-mechanics-batch2-custodial-activation-preflight-evidence-v1.json")
    ledger, ledger_sha = load("humor-mechanics-batch2-custodial-activation-preflight-ledger-v1.json")
    readiness, readiness_sha = load("humor-mechanics-batch2-custodial-activation-readiness-v1.json")
    audit, _ = load("humor-mechanics-batch2-custodial-activation-readiness-v1-audit.json")
    request = committed(REQUEST_COMMIT,
                        "docs/artifacts/humor-mechanics-batch2-custodial-activation-preflight-request-v1.json")
    registration = committed(REGISTRATION_COMMIT,
                             "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    keys = {item["role"]: item for item in registration["registrations"]}
    challenges = {(item["operation_ordinal"], item["signer_role"]): item["challenge"]
                  for item in request["signature_requests"]}
    evidence_unsealed = dict(evidence)
    evidence_identity = evidence_unsealed.pop("evidence_identity")
    require(evidence_identity == seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_EVIDENCE_V1", evidence_unsealed),
            "evidence seal")
    require(len(evidence["verified_responses"]) == 8, "response count")
    seen = set()
    for response in evidence["verified_responses"]:
        key = (response["operation_ordinal"], response["signer_role"])
        require(key in challenges and key not in seen, "response set")
        seen.add(key)
        challenge = challenges[key]
        registered = keys[response["signer_role"]]
        require(response["challenge_identity"] == challenge["challenge_identity"] and
                response["principal_identity"] == registered["principal_identity"] and
                response["registered_public_key_fingerprint"] == registered["public_key_fingerprint"] and
                response["canonical_challenge_sha256"] == hashlib.sha256(canonical(challenge)).hexdigest() and
                response["signature_verification"] == "VERIFIED" and
                not response["grants_operational_authority"] and not response["private_key_included"],
                f"{key}: binding")
        verify_signature(registered["public_key"]["value"], registered["algorithm"], canonical(challenge),
                         base64.b64decode(response["signature"]["value"], validate=True))
    require(seen == set(challenges), "missing response")
    require(set(evidence["mutation_results"].values()) == {True} and
            len(evidence["mutation_results"]) >= 13, "mutation suite")
    ledger_unsealed = dict(ledger)
    ledger_identity = ledger_unsealed.pop("ledger_segment_identity")
    require(ledger_identity == seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_LEDGER_V1", ledger_unsealed),
            "ledger seal")
    previous = request["batch_core"]["prior_ledger_head"]
    for sequence, entry in enumerate(ledger["entries"], start=8):
        entry_unsealed = dict(entry)
        entry_hash = entry_unsealed.pop("entry_hash")
        require(entry["entry_sequence"] == sequence and entry["previous_entry_hash"] == previous and
                entry_hash == seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry_unsealed) and
                not entry["operational_authority"], f"ledger {sequence}")
        previous = entry_hash
    require(previous == ledger["final_ledger_head"] == readiness["access_ledger_identity"],
            "ledger final head")
    readiness_unsealed = dict(readiness)
    readiness_identity = readiness_unsealed.pop("activation_readiness_identity")
    require(readiness_identity == seal("B2_CUSTODIAL_ACTIVATION_READINESS_V1", readiness_unsealed),
            "readiness seal")
    require(readiness["ledger_segment_identity"] == ledger_identity and
            readiness["evidence_identity"] == evidence_identity and
            readiness["verdict"] ==
            "READY_FOR_SEPARATELY_AUTHORIZED_METADATA_OPERATIONS_NOT_CONTENT_ACCESS" and
            readiness["separation_of_duties"] == "VERIFIED" and
            not readiness["operational_content_access"] and not any(readiness["authority_matrix"].values()),
            "readiness state")
    require(audit["evidence_sha256"] == evidence_sha and audit["ledger_sha256"] == ledger_sha and
            audit["readiness_sha256"] == readiness_sha and
            audit["activation_readiness_identity"] == readiness_identity and
            audit["access_ledger_identity"] == previous and
            audit["private_keys_accessed"] == audit["keys_generated"] ==
            audit["signatures_generated"] == audit["real_content_accessed"] == 0 and
            not audit["operational_content_access"] and not audit["deterministic_defects_remaining"],
            "audit binding/state")
    print(json.dumps({
        "verdict": readiness["verdict"], "activation_readiness_identity": readiness_identity,
        "access_ledger_identity": previous, "signatures_verified": 8,
        "separation_of_duties": "VERIFIED", "operational_content_access": False,
        "all_action_authorities": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
