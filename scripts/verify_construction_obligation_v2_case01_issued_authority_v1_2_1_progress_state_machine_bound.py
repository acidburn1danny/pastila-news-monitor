"""Zero-execution verifier for the progress-state-machine-bound V1.2.1 issuance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKET_COMMIT = "d5e87d449ad21b57c785c883024ff0853849f87e"
PACKET_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "case01-successor-issuance-packet-v1-2-1-progress-state-machine-bound")
EVIDENCE_RELATIVE = Path(
    ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-"
    "v1-2-1-progress-state-machine-bound-evidence")
PACKET_IDENTITY = "1dd87623730bf091e4e5e824918bd0e1f27a5899a6cde3f1c80f2f40b742528d"
PACKET_PLAN_IDENTITY = "f37cea4d2652f4a1d335aca414e405e0b73eb0602884b81aa906b6653b2f2d56"
COMMAND_IDENTITY = "02c9544b6cb9e6d1c2b203a2c951f9c2cd4bf69bd1b6888159e975e721486b49"
RECEIPT_IDENTITY = "9fce4877a60aadcfb1364a814ddb377476245faa59ce8a475180931fca013573"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    packet_root = root / PACKET_RELATIVE
    required = {
        "application-provider-request.json", "authority-receipt-candidate.json",
        "authority-receipt-issued.json", "host-payload.json", "manifest.json",
        "rendered-prompt.json", "runner-request.json", "static-executor-binding.json",
    }
    if {path.name for path in packet_root.iterdir() if path.is_file()} != required:
        raise RuntimeError("CASE01_V1_2_1_PROGRESS_STATE_ISSUED_FILE_SET_MISMATCH")
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
        raise RuntimeError("CASE01_V1_2_1_PROGRESS_STATE_ISSUANCE_IDENTITY_MISMATCH")
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    if (packet_root / "authority-receipt-issued.json").read_bytes() != _canonical(issued):
        raise RuntimeError("CASE01_V1_2_1_PROGRESS_STATE_ISSUED_RECEIPT_BYTE_MISMATCH")
    if (root / EVIDENCE_RELATIVE).exists() or (root / EVIDENCE_RELATIVE).is_symlink():
        raise RuntimeError("CASE01_V1_2_1_PROGRESS_STATE_EVIDENCE_ROOT_NOT_ABSENT")
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
