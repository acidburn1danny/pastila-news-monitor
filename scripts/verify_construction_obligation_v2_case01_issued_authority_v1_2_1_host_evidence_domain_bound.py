"""Zero-execution verifier for the host-evidence-domain-bound V1.2.1 issuance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "b4ef5dc51200578dd7394de8168abac91ec16c97"
PACKET_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "case01-successor-issuance-packet-v1-2-1-host-evidence-domain-bound")
EVIDENCE_RELATIVE = Path(
    ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-"
    "v1-2-1-host-evidence-domain-bound-evidence")
PACKET_IDENTITY = "bbad9ac2588e08c8cdd0583d4e6b977a7225535f137c3ee23a8fb8f9f675d49f"
PACKET_PLAN_IDENTITY = "f5fa43d8ee483a3eaf43d1474ff45a216787b94056fd52c167cd3b302372c327"
COMMAND_IDENTITY = "dd618c52d7e9165688f27ece19f49ea09a0990ab67c1435785d3dd3ff009ff7c"
RECEIPT_IDENTITY = "e8bf4ca020ff1a91b90e1025d8768a22fa18dd02c138ed035b574475e3d94ddd"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    required = {
        "application-provider-request.json", "authority-receipt-candidate.json",
        "authority-receipt-issued.json", "host-payload.json", "manifest.json",
        "rendered-prompt.json", "runner-request.json", "static-executor-binding.json",
    }
    if {path.name for path in packet_root.iterdir() if path.is_file()} != required:
        raise RuntimeError("CASE01_V1_2_1_HOST_EVIDENCE_ISSUED_FILE_SET_MISMATCH")
    manifest = json.loads((packet_root / "manifest.json").read_bytes())
    candidate = json.loads((packet_root / "authority-receipt-candidate.json").read_bytes())
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or manifest["attempts"] != {"completed": 0, "ceiling": 1}
            or any(manifest["execution"].values())
            or candidate["receipt_status"] != "UNISSUED"
            or candidate["authority_receipt_identity"] is not None
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY):
        raise RuntimeError("CASE01_V1_2_1_HOST_EVIDENCE_ISSUANCE_IDENTITY_MISMATCH")
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    if (packet_root / "authority-receipt-issued.json").read_bytes() != _canonical(issued):
        raise RuntimeError("CASE01_V1_2_1_HOST_EVIDENCE_ISSUED_RECEIPT_BYTE_MISMATCH")
    if (root / EVIDENCE_RELATIVE).exists() or (root / EVIDENCE_RELATIVE).is_symlink():
        raise RuntimeError("CASE01_V1_2_1_HOST_EVIDENCE_ROOT_NOT_ABSENT")
    return {
        "packet_commit": PACKET_COMMIT, "packet_identity": PACKET_IDENTITY,
        "packet_plan_identity": PACKET_PLAN_IDENTITY,
        "command_identity": COMMAND_IDENTITY,
        "authority_receipt_identity": RECEIPT_IDENTITY,
        "receipt_status": "ISSUED", "attempt_ceiling": 1,
        "consumed_attempts": 0, "remaining_attempts": 1,
        "execution_started": False, "evidence_root_absent": True,
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
