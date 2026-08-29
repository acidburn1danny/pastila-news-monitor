"""Zero-execution verifier for the provider-source-bound V1.2.1 receipt."""
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

PACKET_COMMIT = "db20be3f54ab1d248e7bf92a9c063351ccb8d595"
PACKET_IDENTITY = "4b5a4cde519be6f94292fd1873e6bbb7b74d737e92d965580ec61423dbf017eb"
PACKET_PLAN_IDENTITY = "163164b545bd05ff914a9daa3bf77f91881dea7adc80b7b0f355dbec467875d0"
COMMAND_IDENTITY = "56b187d186bd7ea3b7096afa965c955e5812720f9a3138a7d8a2217cc8b91ce7"
RECEIPT_IDENTITY = "9e79a1bec349d417d1a8cbbc79137385c92c994a57a2ed0ce5d528a2d73f9362"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    expected = materialize_case01_issuance_packet_v1_2_1(project_root=root)
    packet_root = root / PACKET_RELATIVE
    actual_names = {path.name for path in packet_root.iterdir() if path.is_file()}
    if actual_names != set(expected) | {ISSUED_NAME}:
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_ISSUED_FILE_SET_MISMATCH")
    for name, raw in expected.items():
        if (packet_root / name).read_bytes() != raw:
            raise RuntimeError(f"CASE01_V1_2_1_PROVIDER_SOURCE_PACKET_DRIFT:{name}")
    manifest = json.loads(expected["manifest.json"])
    candidate = json.loads(expected["authority-receipt-candidate.json"])
    runner_raw = expected["runner-request.json"]
    runner = json.loads(runner_raw)
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
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_RECEIPT_SEAL_MISMATCH")
    evidence = root / EVIDENCE_RELATIVE
    if evidence.exists() or evidence.is_symlink():
        raise RuntimeError("CASE01_V1_2_1_PROVIDER_SOURCE_ATTEMPT_ALREADY_CONSUMED")
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
