"""Zero-execution verifier for the runtime-source-bound V1.2.1 receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "35078f9cf63421eada5cc88a5d3a468f83b5f796"
PACKET_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-runtime-source-bound")
PACKET_IDENTITY = "8ecc76557f5d020655abf9ed2c8cd51b355d6131d3299d27704625b91710d510"
PACKET_PLAN_IDENTITY = "bc1b793b88de9c63a1d43200c86c44402a705f4c2f21aa61a494fc6ac82e4f39"
COMMAND_IDENTITY = "a7cba567ba6a1235b48c5ec67ec4e2f7541840d990356c563f81318c12560c78"
RECEIPT_IDENTITY = "9ef49ce6b0b3992928a6904427497522b51eac03a7e5aa79297298b4b348c397"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    required = {"application-provider-request.json", "authority-receipt-candidate.json",
                "authority-receipt-issued.json", "host-payload.json", "manifest.json",
                "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    if {path.name for path in packet_root.iterdir() if path.is_file()} != required:
        raise RuntimeError("CASE01_V1_2_1_RUNTIME_SOURCE_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or manifest["attempts"] != {"completed": 0, "ceiling": 1}
            or any(manifest["execution"].values())
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY):
        raise RuntimeError("CASE01_V1_2_1_RUNTIME_SOURCE_IDENTITY_MISMATCH")
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    if raw_issued != _canonical(issued):
        raise RuntimeError("CASE01_V1_2_1_RUNTIME_SOURCE_RECEIPT_BYTE_MISMATCH")
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
