"""Zero-execution verifier for the exact-operations-bound V1.2.1 receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "50c347195a146b23d0025c23f6046a37ff0e999e"
PACKET_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-exact-operations-bound")
PACKET_IDENTITY = "329cbd127db807728f74928956b4868828de9f58373b9b45809d78763b890ff5"
PACKET_PLAN_IDENTITY = "b97ecdebdb4c539d9b0d41a2e5ece43f8daff41ef8934fcb97b013da1bf0cddf"
COMMAND_IDENTITY = "b7c70673f476eeec46297fbacf367c2697848e297d30c526f93c27746736cb00"
RECEIPT_IDENTITY = "b9176dbe4d2d1d98eb43d6e13e20e9955010c5e5a30ee89f609197dcb35b24a9"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    required = {"application-provider-request.json", "authority-receipt-candidate.json",
                "authority-receipt-issued.json", "host-payload.json", "manifest.json",
                "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    if {path.name for path in packet_root.iterdir() if path.is_file()} != required:
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or manifest["attempts"] != {"completed": 0, "ceiling": 1}
            or any(manifest["execution"].values())
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY):
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_IDENTITY_MISMATCH")
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    if raw_issued != _canonical(issued):
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_RECEIPT_BYTE_MISMATCH")
    return {"packet_commit": PACKET_COMMIT, "packet_identity": PACKET_IDENTITY,
            "packet_plan_identity": PACKET_PLAN_IDENTITY, "command_identity": COMMAND_IDENTITY,
            "authority_receipt_identity": RECEIPT_IDENTITY, "receipt_status": "ISSUED",
            "attempt_ceiling": 1, "consumed_attempts": 1, "remaining_attempts": 0,
            "execution_started": True}


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        raise SystemExit("usage: verifier PROJECT_ROOT")
    print(json.dumps(verify(project_root=Path(arguments[0])), ensure_ascii=True,
                     sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
