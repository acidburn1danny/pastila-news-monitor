"""Zero-execution verifier for the application-source-bound V1.2.1 receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "d0aa99529ec21e4c1bffcece4d25784db35ea9a1"
PACKET_RELATIVE = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-application-source-bound")
PACKET_IDENTITY = "d38b515c38e159765a09fa42a281cd438691ace9066cf7d811953d3e28c129e3"
PACKET_PLAN_IDENTITY = "1455976c7cc41f7475ee03a2c94404abd76195e341500904313333f8fd95e568"
COMMAND_IDENTITY = "6c30eaae256daeceb07806fa586d4e3d1116c91c99f984945e84fba29c0dac40"
RECEIPT_IDENTITY = "215cd224e82240ce2d7d439b3904063ab3d808a059ea70d53140ce73af65eb3f"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    actual = {path.name for path in packet_root.iterdir() if path.is_file()}
    required = {"application-provider-request.json", "authority-receipt-candidate.json",
                "authority-receipt-issued.json", "host-payload.json", "manifest.json",
                "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    if actual != required:
        raise RuntimeError("CASE01_V1_2_1_APPLICATION_SOURCE_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or manifest["attempts"] != {"completed": 0, "ceiling": 1}
            or any(manifest["execution"].values())
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY):
        raise RuntimeError("CASE01_V1_2_1_APPLICATION_SOURCE_IDENTITY_MISMATCH")
    expected_issued = dict(candidate["authority_body"])
    expected_issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    if raw_issued != _canonical(expected_issued):
        raise RuntimeError("CASE01_V1_2_1_APPLICATION_SOURCE_RECEIPT_BYTE_MISMATCH")
    return {"packet_commit": PACKET_COMMIT, "packet_identity": PACKET_IDENTITY,
            "packet_plan_identity": PACKET_PLAN_IDENTITY,
            "command_identity": COMMAND_IDENTITY,
            "authority_receipt_identity": RECEIPT_IDENTITY,
            "receipt_status": "ISSUED", "attempt_ceiling": 1,
            "consumed_attempts": 1, "remaining_attempts": 0,
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
