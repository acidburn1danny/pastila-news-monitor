"""Zero-execution verifier for the exact-operations-bound V1.2.1 receipt."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    EVIDENCE_RELATIVE, PACKET_RELATIVE, materialize_case01_issuance_packet_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import parse_generation_authority_v1_2_1

PACKET_COMMIT = "50c347195a146b23d0025c23f6046a37ff0e999e"
PACKET_IDENTITY = "329cbd127db807728f74928956b4868828de9f58373b9b45809d78763b890ff5"
PACKET_PLAN_IDENTITY = "b97ecdebdb4c539d9b0d41a2e5ece43f8daff41ef8934fcb97b013da1bf0cddf"
COMMAND_IDENTITY = "b7c70673f476eeec46297fbacf367c2697848e297d30c526f93c27746736cb00"
RECEIPT_IDENTITY = "b9176dbe4d2d1d98eb43d6e13e20e9955010c5e5a30ee89f609197dcb35b24a9"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    expected = materialize_case01_issuance_packet_v1_2_1(project_root=root)
    packet_root = root / PACKET_RELATIVE
    if {path.name for path in packet_root.iterdir() if path.is_file()} != set(expected) | {ISSUED_NAME}:
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_ISSUED_FILE_SET_MISMATCH")
    if any((packet_root / name).read_bytes() != raw for name, raw in expected.items()):
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_PACKET_DRIFT")
    manifest = json.loads(expected["manifest.json"])
    candidate = json.loads(expected["authority-receipt-candidate.json"])
    runner_raw = expected["runner-request.json"]
    runner = json.loads(runner_raw)
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
    parsed = parse_generation_authority_v1_2_1(
        raw_receipt=raw_issued,
        expected_host_payload_sha256=runner["host_payload_sha256"],
        expected_runner_request_sha256=hashlib.sha256(runner_raw).hexdigest(),
        expected_provider_request_id=runner["provider_request_id"],
        expected_source_context_identity=runner["source_context_identity"],
        expected_packet_plan_identity=PACKET_PLAN_IDENTITY,
        expected_command_plan_identity=COMMAND_IDENTITY,
    )
    if parsed.authority_receipt_identity != RECEIPT_IDENTITY:
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_RECEIPT_SEAL_MISMATCH")
    if (root / EVIDENCE_RELATIVE).exists() or (root / EVIDENCE_RELATIVE).is_symlink():
        raise RuntimeError("CASE01_V1_2_1_EXACT_OPERATIONS_ATTEMPT_ALREADY_CONSUMED")
    return {"packet_commit": PACKET_COMMIT, "packet_identity": PACKET_IDENTITY,
            "packet_plan_identity": PACKET_PLAN_IDENTITY, "command_identity": COMMAND_IDENTITY,
            "authority_receipt_identity": RECEIPT_IDENTITY, "receipt_status": "ISSUED",
            "attempt_ceiling": 1, "consumed_attempts": 0, "remaining_attempts": 1,
            "execution_started": False}


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
