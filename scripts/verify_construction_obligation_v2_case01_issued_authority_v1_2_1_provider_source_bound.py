"""Zero-execution verifier for the provider-source-bound V1.2.1 receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "db20be3f54ab1d248e7bf92a9c063351ccb8d595"
FREEZE_COMMIT = "d908b9b8"
PACKET_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-provider-source-bound")
PACKET_IDENTITY = "4b5a4cde519be6f94292fd1873e6bbb7b74d737e92d965580ec61423dbf017eb"
PACKET_PLAN_IDENTITY = "163164b545bd05ff914a9daa3bf77f91881dea7adc80b7b0f355dbec467875d0"
COMMAND_IDENTITY = "56b187d186bd7ea3b7096afa965c955e5812720f9a3138a7d8a2217cc8b91ce7"
RECEIPT_IDENTITY = "9e79a1bec349d417d1a8cbbc79137385c92c994a57a2ed0ce5d528a2d73f9362"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    actual_names = {path.name for path in packet_root.iterdir() if path.is_file()}
    required = {"application-provider-request.json", "authority-receipt-candidate.json", "authority-receipt-issued.json", "host-payload.json", "manifest.json", "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    if actual_names != required:
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY
            or candidate["receipt_status"] != "UNISSUED"
            or candidate["authority_receipt_identity"] is not None):
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_IDENTITY_MISMATCH")
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    expected_issued = dict(candidate["authority_body"])
    expected_issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    if raw_issued != _canonical(expected_issued):
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_RECEIPT_BYTE_MISMATCH")
    return {
        "packet_commit": PACKET_COMMIT, "freeze_commit": FREEZE_COMMIT,
        "packet_identity": PACKET_IDENTITY,
        "packet_plan_identity": PACKET_PLAN_IDENTITY,
        "command_identity": COMMAND_IDENTITY,
        "authority_receipt_identity": RECEIPT_IDENTITY,
        "receipt_status": "ISSUED", "attempt_ceiling": 1,
        "consumed_attempts": 1, "remaining_attempts": 0,
        "execution_started": True,
    }


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
