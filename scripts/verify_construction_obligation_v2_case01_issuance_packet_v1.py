"""Git-only verifier for the unissued current Case 01 issuance packet."""
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


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True)
    expected = materialize_case01_issuance_packet_v1(project_root=root)
    packet_root = root / PACKET_RELATIVE
    actual_names = {path.name for path in packet_root.iterdir() if path.is_file()}
    allowed_names = set(expected) | {"authority-receipt-issued.json"}
    if actual_names not in (set(expected), allowed_names):
        raise RuntimeError("CASE01_ISSUANCE_PACKET_FILE_SET_MISMATCH")
    for name, raw in expected.items():
        if (packet_root / name).read_bytes() != raw:
            raise RuntimeError(f"CASE01_ISSUANCE_PACKET_BYTE_DRIFT:{name}")
    candidate = json.loads(expected["authority-receipt-candidate.json"])
    manifest = json.loads(expected["manifest.json"])
    if (candidate["receipt_status"] != "UNISSUED"
            or candidate["authority_receipt_identity"] is not None
            or manifest["receipt_status"] != "UNISSUED"
            or any(manifest["execution"].values())):
        raise RuntimeError("CASE01_ISSUANCE_PACKET_AUTHORITY_STATUS_INVALID")
    if (root / EVIDENCE_RELATIVE).exists() or (root / EVIDENCE_RELATIVE).is_symlink():
        raise RuntimeError("CASE01_ISSUANCE_PACKET_EVIDENCE_ROOT_NOT_EXCLUSIVE")
    body = candidate["authority_body"]
    issued_shape = dict(body)
    issued_shape["authority_receipt_identity"] = candidate["proposed_receipt_identity"]
    raw_issued_shape = _canonical(issued_shape)
    runner = json.loads(expected["runner-request.json"])
    parsed = parse_generation_authority_v1_1(
        raw_receipt=raw_issued_shape,
        expected_host_payload_sha256=runner["host_payload_sha256"],
        expected_runner_request_sha256=hashlib.sha256(
            expected["runner-request.json"]).hexdigest(),
        expected_provider_request_id=runner["provider_request_id"],
        expected_source_context_identity=runner["source_context_identity"])
    if parsed.authority_receipt_identity != candidate["proposed_receipt_identity"]:
        raise RuntimeError("CASE01_ISSUANCE_PACKET_PROPOSED_RECEIPT_INVALID")
    return manifest


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        raise SystemExit("usage: verifier PROJECT_ROOT")
    manifest = verify(project_root=Path(arguments[0]))
    print(json.dumps({"result": "PASS", "packet_identity": manifest["packet_identity"],
                      "receipt_status": manifest["receipt_status"]},
                     ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
