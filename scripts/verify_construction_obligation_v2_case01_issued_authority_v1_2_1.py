"""Zero-execution verifier for the issued, authority-plan-bound V1.2.1 receipt."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    EVIDENCE_RELATIVE, PACKET_RELATIVE, materialize_case01_issuance_packet_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    parse_generation_authority_v1_2_1,
)

PACKET_COMMIT = "2fbafa36b5937647498601095df1e5a2dc04b183"
PACKET_IDENTITY = "047158aba98385606383d3432bd4b3cef7a6bf90e8014460257400f505694004"
COMMAND_IDENTITY = "e120e6f264bebf90551fa625e038be0af821447d646af786e5ab455e8f0be41b"
PACKET_PLAN_IDENTITY = "8f3ffd7e3f1e2051819359c67e29fce8d176560fa9c6fe5e0d9dd9a90f53421d"
RECEIPT_IDENTITY = "d9d72feefa7015021ca79388dcee837c21103c87fef0733903b3d73f8e233da4"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    expected = materialize_case01_issuance_packet_v1_2_1(project_root=root)
    packet_root = root / PACKET_RELATIVE
    actual_names = {path.name for path in packet_root.iterdir() if path.is_file()}
    if actual_names != set(expected) | {ISSUED_NAME}:
        raise RuntimeError("CASE01_V1_2_1_ISSUED_AUTHORITY_FILE_SET_MISMATCH")
    for name, raw in expected.items():
        if (packet_root / name).read_bytes() != raw:
            raise RuntimeError(f"CASE01_V1_2_1_REVIEWED_PACKET_BYTE_DRIFT:{name}")
    manifest = json.loads(expected["manifest.json"])
    candidate = json.loads(expected["authority-receipt-candidate.json"])
    runner_raw = expected["runner-request.json"]
    runner = json.loads(runner_raw)
    if (manifest["packet_identity"] != PACKET_IDENTITY
            or manifest["command_identity"] != COMMAND_IDENTITY
            or manifest["packet_plan_identity"] != PACKET_PLAN_IDENTITY
            or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
            or candidate["receipt_status"] != "UNISSUED"
            or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY
            or candidate["authority_receipt_identity"] is not None):
        raise RuntimeError("CASE01_V1_2_1_REVIEWED_PACKET_IDENTITY_MISMATCH")
    raw_issued = (packet_root / ISSUED_NAME).read_bytes()
    issued = json.loads(raw_issued.decode("utf-8", errors="strict"))
    expected_issued = dict(candidate["authority_body"])
    expected_issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    if raw_issued != _canonical(expected_issued):
        raise RuntimeError("CASE01_V1_2_1_ISSUED_AUTHORITY_BYTE_MISMATCH")
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
        raise RuntimeError("CASE01_V1_2_1_ISSUED_AUTHORITY_SEAL_MISMATCH")
    evidence = root / EVIDENCE_RELATIVE
    if evidence.exists() or evidence.is_symlink():
        raise RuntimeError("CASE01_V1_2_1_ISSUED_AUTHORITY_ATTEMPT_ALREADY_CONSUMED")
    return {
        "packet_commit": PACKET_COMMIT, "packet_identity": PACKET_IDENTITY,
        "packet_plan_identity": PACKET_PLAN_IDENTITY,
        "command_identity": COMMAND_IDENTITY,
        "authority_receipt_identity": RECEIPT_IDENTITY,
        "receipt_status": "ISSUED", "attempt_ceiling": 1,
        "consumed_attempts": 0, "remaining_attempts": 1,
        "execution_started": False,
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
