"""Zero-execution verifier for the durable-source-bound V1.2.1 receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "7e6b6cc928efa7e57fdd9d59429810c7c2679a0c"
PACKET_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-durable-source-bound")
PACKET_IDENTITY = "211146a527ad73c67f414ce3da582049eb1a5053884abfd1726abae29bb7ec25"
PACKET_PLAN_IDENTITY = "2c9ae745c46a83e898ef992bdeae594a895b5e1fd3264d4b1fadad80cda61961"
COMMAND_IDENTITY = "84d1d039d6b83c9e23441a8b8c3323b6ec9299b9789e5123762451ec85bba474"
RECEIPT_IDENTITY = "2ca3f66aa1f5ac86444151b376e36d884f3324a9986c228f01b9894f1b41ab99"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    required = {"application-provider-request.json", "authority-receipt-candidate.json",
                "authority-receipt-issued.json", "host-payload.json", "manifest.json",
                "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    if {path.name for path in packet_root.iterdir() if path.is_file()} != required:
        raise RuntimeError("CASE01_V1_2_1_DURABLE_SOURCE_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or manifest["attempts"] != {"completed": 0, "ceiling": 1}
            or any(manifest["execution"].values())
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY):
        raise RuntimeError("CASE01_V1_2_1_DURABLE_SOURCE_IDENTITY_MISMATCH")
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    if raw_issued != _canonical(issued):
        raise RuntimeError("CASE01_V1_2_1_DURABLE_SOURCE_RECEIPT_BYTE_MISMATCH")
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
