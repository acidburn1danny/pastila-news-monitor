"""Executable, candidate-blinded adjudication contracts for completed R4 evidence."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

SOURCE_BOUNDARY = "6b2c55935999aaf6da077c0dddd9289f3eec059665d9e361c93cad40aa67568e"
REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
RUBRIC_IDENTITY = "659339bac91cfbdf993c7b57555dfd9191e609816db76e60bc41f13d0dfba1a6"
ROLES = ("ADJUDICATOR_A", "ADJUDICATOR_B")
VERDICTS = ("PASS", "FAIL", "INDETERMINATE")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identity(value: object) -> str:
    return digest(canonical(value))


def packet_for(*, row: Mapping[str, object], raw: bytes, request: Mapping[str, object],
               assertion: Mapping[str, object]) -> dict[str, object]:
    if row.get("structural_status") != "STRUCTURALLY_VALID_PENDING_ADJUDICATION":
        raise ValueError("structural failure cannot become an adjudication packet")
    core = {
        "schema": "pastila-production-core-v15-r4-blind-adjudication-packet",
        "schema_version": 1,
        "source_boundary_identity": SOURCE_BOUNDARY,
        "global_ordinal": row["global_ordinal"],
        "materialization": row["materialization"],
        "repetition": row["repetition"],
        "candidate_alias": row["candidate_alias"],
        "case_id": row["case_id"],
        "request_identity": row["request_identity"],
        "execution_receipt_identity": row["execution_receipt_identity"],
        "raw_output_sha256": row["raw_output_sha256"],
        "raw_output_base64": base64.b64encode(raw).decode("ascii"),
        "request": dict(request),
        "assertion": dict(assertion),
        "rubric_identity": RUBRIC_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
        "candidate_mapping_present": False,
        "private_runtime_observation_present": False,
    }
    if (digest(raw) != row["raw_output_sha256"]
            or request.get("case_id") != row["case_id"]
            or request.get("request_identity") != row["request_identity"]
            or assertion.get("case_id") != row["case_id"]
            or core["candidate_alias"] not in ("CANDIDATE-A", "CANDIDATE-B")):
        raise ValueError("packet source projection mismatch")
    return {**core, "packet_identity": identity(core)}


def custody_manifest(role: str, boundary_identity: str, inventory: list[dict[str, str]]) -> dict[str, object]:
    if role not in ROLES or len(inventory) != 1986:
        raise ValueError("custody authority mismatch")
    core = {
        "schema": "pastila-production-core-v15-r4-adjudication-custody",
        "schema_version": 1,
        "adjudication_execution_boundary_identity": boundary_identity,
        "adjudicator_role": role,
        "packet_count": 1986,
        "packet_inventory_root": identity(inventory),
        "candidate_mapping_present": False,
        "private_runtime_observations_present": False,
    }
    return {**core, "custody_identity": identity(core)}


def unsigned_receipt(*, boundary_identity: str, packet: Mapping[str, object], role: str,
                     adjudicator_id: str, key_sha256: str, verdict: str) -> dict[str, object]:
    if role not in ROLES or verdict not in VERDICTS:
        raise ValueError("receipt authority invalid")
    return {
        "schema": "pastila-production-core-v15-r4-semantic-receipt",
        "schema_version": 1,
        "adjudication_execution_boundary_identity": boundary_identity,
        "packet_identity": packet["packet_identity"],
        "global_ordinal": packet["global_ordinal"],
        "case_id": packet["case_id"],
        "candidate_alias": packet["candidate_alias"],
        "raw_output_sha256": packet["raw_output_sha256"],
        "adjudicator_role": role,
        "adjudicator_id": adjudicator_id,
        "adjudicator_key_sha256": key_sha256,
        "verdict": verdict,
    }


def verify_receipt(receipt: Mapping[str, object], *, boundary_identity: str,
                   packet: Mapping[str, object], registration: tuple[str, str, bytes],
                   openssl: Path) -> str:
    item = dict(receipt)
    signature_text = item.pop("signature_base64", None)
    claimed = item.pop("receipt_identity", None)
    expected = unsigned_receipt(
        boundary_identity=boundary_identity, packet=packet,
        role=str(item.get("adjudicator_role")), adjudicator_id=registration[0],
        key_sha256=registration[1], verdict=str(item.get("verdict")),
    )
    if item != expected or not isinstance(signature_text, str):
        raise ValueError("receipt signed-message substitution")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except Exception as exc:
        raise ValueError("receipt signature encoding invalid") from exc
    message = canonical(expected)
    if len(signature) != 64 or claimed != digest(message + signature):
        raise ValueError("receipt identity invalid")
    if digest(registration[2]) != registration[1]:
        raise ValueError("registered public key drift")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder); msg = root / "message"; sig = root / "signature"; key = root / "public.pem"
        msg.write_bytes(message); sig.write_bytes(signature); key.write_bytes(registration[2])
        run = subprocess.run([str(openssl), "pkeyutl", "-verify", "-pubin", "-inkey", str(key),
                              "-rawin", "-in", str(msg), "-sigfile", str(sig)], capture_output=True)
    if run.returncode:
        raise ValueError("receipt Ed25519 verification failed")
    return str(claimed)


def verify_complete_closure(receipts: Sequence[Mapping[str, object]], *, boundary_identity: str,
                            packets: Sequence[Mapping[str, object]],
                            registrations: Mapping[str, tuple[str, str, bytes]], openssl: Path) -> str:
    if set(registrations) != set(ROLES) or len({v[0] for v in registrations.values()}) != 2 or len({v[1] for v in registrations.values()}) != 2:
        raise ValueError("independent owner registrations absent")
    if len(packets) != 1986 or len(receipts) != 3972:
        raise ValueError("complete two-receipt closure absent")
    by_key: dict[tuple[str, str], Mapping[str, object]] = {}
    packet_by_identity = {str(p["packet_identity"]): p for p in packets}
    if len(packet_by_identity) != 1986:
        raise ValueError("packet identity uniqueness absent")
    for receipt in receipts:
        role, packet_id = str(receipt.get("adjudicator_role")), str(receipt.get("packet_identity"))
        if role not in ROLES or packet_id not in packet_by_identity or (packet_id, role) in by_key:
            raise ValueError("receipt replay, role, or packet substitution")
        verify_receipt(receipt, boundary_identity=boundary_identity, packet=packet_by_identity[packet_id],
                       registration=registrations[role], openssl=openssl)
        by_key[(packet_id, role)] = receipt
    if len(by_key) != 3972:
        raise ValueError("receipt closure cardinality mismatch")
    return "COMPLETE_TWO_PERSON_PASS" if all(r["verdict"] == "PASS" for r in receipts) else "COMPLETE_FAIL_CLOSED"
