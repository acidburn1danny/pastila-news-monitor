"""Git-only verifier for the issued current Case 01 one-shot authority."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1 import (
    EVIDENCE_RELATIVE,
    PACKET_RELATIVE,
    materialize_case01_issuance_packet_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    parse_generation_authority_v1_1,
)

PACKET_COMMIT = "8cb2de3a5c55b69123616eb238ea9616edb42a87"
PACKET_IDENTITY = "f31c6862ed4b940bb8ea6c08fed7777cf36a30a1a017e242a2baf0df49979e7f"
COMMAND_IDENTITY = "73e8faf4dfed1477bc2f9aec58ba92a6c34109dc5b94c363a8f07d2345d608b1"
RECEIPT_IDENTITY = "b602bf5ffe937cf595b650fcd086ab578f4b173a08dd9557f3e1c61f874542d9"
ISSUED_NAME = "authority-receipt-issued.json"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    expected = materialize_case01_issuance_packet_v1(project_root=root)
    packet_root = root / PACKET_RELATIVE
    actual_names = {path.name for path in packet_root.iterdir() if path.is_file()}
    if actual_names != set(expected) | {ISSUED_NAME}:
        raise RuntimeError("CASE01_ISSUED_AUTHORITY_FILE_SET_MISMATCH")
    for name, raw in expected.items():
        if (packet_root / name).read_bytes() != raw:
            raise RuntimeError(f"CASE01_REVIEWED_PACKET_BYTE_DRIFT:{name}")
    manifest = json.loads(expected["manifest.json"])
    candidate = json.loads(expected["authority-receipt-candidate.json"])
    runner_raw = expected["runner-request.json"]
    runner = json.loads(runner_raw)
    if (
        manifest["packet_identity"] != PACKET_IDENTITY
        or manifest["command_identity"] != COMMAND_IDENTITY
        or manifest["authority_reference_if_issued"] != RECEIPT_IDENTITY
        or candidate["receipt_status"] != "UNISSUED"
        or candidate["proposed_receipt_identity"] != RECEIPT_IDENTITY
        or candidate["authority_receipt_identity"] is not None
    ):
        raise RuntimeError("CASE01_REVIEWED_PACKET_IDENTITY_MISMATCH")
    issued_path = packet_root / ISSUED_NAME
    raw_issued = issued_path.read_bytes()
    issued = json.loads(raw_issued.decode("utf-8", errors="strict"))
    expected_issued = dict(candidate["authority_body"])
    expected_issued["authority_receipt_identity"] = RECEIPT_IDENTITY
    if raw_issued != _canonical(expected_issued):
        raise RuntimeError("CASE01_ISSUED_AUTHORITY_BYTE_MISMATCH")
    parsed = parse_generation_authority_v1_1(
        raw_receipt=raw_issued,
        expected_host_payload_sha256=runner["host_payload_sha256"],
        expected_runner_request_sha256=hashlib.sha256(runner_raw).hexdigest(),
        expected_provider_request_id=runner["provider_request_id"],
        expected_source_context_identity=runner["source_context_identity"],
    )
    if parsed.authority_receipt_identity != RECEIPT_IDENTITY:
        raise RuntimeError("CASE01_ISSUED_AUTHORITY_SEAL_MISMATCH")
    if root.joinpath(EVIDENCE_RELATIVE).exists() or root.joinpath(EVIDENCE_RELATIVE).is_symlink():
        raise RuntimeError("CASE01_ISSUED_AUTHORITY_ATTEMPT_ALREADY_CONSUMED")
    return {
        "packet_commit": PACKET_COMMIT,
        "packet_identity": PACKET_IDENTITY,
        "command_identity": COMMAND_IDENTITY,
        "authority_receipt_identity": RECEIPT_IDENTITY,
        "receipt_status": "ISSUED",
        "attempt_ceiling": 1,
        "consumed_attempts": 0,
        "remaining_attempts": 1,
        "execution_started": False,
    }


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        raise SystemExit("usage: verifier PROJECT_ROOT")
    result = verify(project_root=Path(arguments[0]))
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
