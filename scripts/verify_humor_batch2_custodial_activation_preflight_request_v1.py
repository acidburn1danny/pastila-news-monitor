"""Verify the unsigned content-free activation-preflight request."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-activation-preflight-request-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    request = json.loads(PATH.read_text(encoding="utf-8"))
    unsealed = dict(request)
    identity = unsealed.pop("request_identity")
    require(identity == seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_REQUEST_V1", unsealed),
            "request seal")
    require(request["batch_identity"] ==
            seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_BATCH_V1", request["batch_core"]),
            "batch seal")
    require(len(request["batch_core"]["operations"]) == 6 and
            len(request["signature_requests"]) == 8, "operation/signature count")
    nonces, challenges = set(), set()
    for item in request["signature_requests"]:
        challenge = item["challenge"]
        unsealed_challenge = dict(challenge)
        challenge_identity = unsealed_challenge.pop("challenge_identity")
        require(challenge_identity ==
                seal("B2_ACTIVATION_PREFLIGHT_SIGNATURE_CHALLENGE_V1", unsealed_challenge),
                "challenge seal")
        require(challenge["batch_identity"] == request["batch_identity"] and
                challenge["prior_ledger_head"] == request["batch_core"]["prior_ledger_head"] and
                challenge["domain"] == "PASTILA_BATCH2_CUSTODIAL_ACTIVATION_PREFLIGHT_V1" and
                not challenge["grants_operational_authority"], "challenge binding")
        nonces.add(challenge["nonce"])
        challenges.add(challenge_identity)
    require(len(nonces) == len(challenges) == 8, "nonce/challenge collision")
    operations = request["batch_core"]["operations"]
    require(operations[1]["required_signer_roles"] ==
            ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"] and
            operations[4]["required_signer_roles"] ==
            ["PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN"], "countersignature dependency")
    require(all(not operation["structural_object"]["contains_source_content"] and
                not operation["structural_object"]["grants_operational_authority"]
                for operation in operations), "content/authority in placeholder")
    require(request["status"] == "AWAITING_OWNER_CONTROLLED_PREFLIGHT_SIGNATURES" and
            request["ledger_events_appended"] == 0 and
            request["activation_readiness"] == "NOT_YET_ESTABLISHED" and
            not request["operational_content_access"] and
            not any(request["authority_matrix"].values()), "premature readiness or authority")
    require(len(request["fail_closed_mutations"]) >= 14, "mutation suite incomplete")
    print(json.dumps({"verdict": "PASS_UNSIGNED_CONTENT_FREE_PREFLIGHT_REQUEST",
                      "request_identity": identity, "batch_identity": request["batch_identity"],
                      "operations": 6, "signature_requests": 8,
                      "ledger_events_appended": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
