"""Fail-closed R4 human-adjudicator client contract."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Mapping

from pastila_scout.production_core_r4_adjudication_execution import (
    VERDICTS,
    canonical,
    digest,
    identity,
    unsigned_receipt,
    verify_receipt,
)

BOUNDARY_IDENTITY = "77fcf784df5faedbda1f34de3e7def2da4ae6553d79de5bd0de839a5d6f8fe30"
PACKET_COUNT = 1986
INVENTORY_ROOT = "bf5bc935db4cb0ccf48d4a880302de8e52a84cf8fe7ca27cb6038f70328c7baf"
PROJECTION_ROOT = "871f4877a91f8143c497146a28a0d9ff22a38221491bd7c2cf15eb95de9a7e9d"
RUNTIME_ROOT = Path("/root/pf9-v15-r4-human-adjudication")
ROLE_CONTRACT = {
    "ADJUDICATOR_A": {
        "adjudicator_id": "EVALUATOR-A-01",
        "key_sha256": "e30913d2a150ff6c3c5d621550c94e9559175921ca9dae49bfbe2bbabc911497",
        "custody": RUNTIME_ROOT / "custody/ADJUDICATOR_A",
        "receipts": Path("/root/pf9-v15-r4-adjudicator-a-receipts"),
    },
    "ADJUDICATOR_B": {
        "adjudicator_id": "EVALUATOR-B-01",
        "key_sha256": "0fcc6461e3e6a0c53693ac834ae7e7264dc379a37b721eb40ace99d12c96c793",
        "custody": RUNTIME_ROOT / "custody/ADJUDICATOR_B",
        "receipts": Path("/root/pf9-v15-r4-adjudicator-b-receipts"),
    },
}


def load_canonical(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"non-regular input: {path}")
    raw = path.read_bytes()
    value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError(f"noncanonical JSON: {path}")
    return value


def registry_registration(role: str, registry_path: Path) -> tuple[str, str, bytes]:
    registry = json.loads(registry_path.read_bytes())
    if (registry.get("registry_identity")
            != "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"):
        raise ValueError("registry substitution")
    if role not in ROLE_CONTRACT or set(registry["roles"]) != set(ROLE_CONTRACT):
        raise ValueError("role substitution")
    item = registry["roles"][role]
    expected = ROLE_CONTRACT[role]
    public = base64.b64decode(item["public_key_pem_base64"], validate=True)
    if (item["adjudicator_id"] != expected["adjudicator_id"]
            or item["public_key_sha256"] != expected["key_sha256"]
            or digest(public) != expected["key_sha256"]):
        raise ValueError("registered person/key substitution")
    return item["adjudicator_id"], item["public_key_sha256"], public


def _public_der(pem: bytes, openssl: Path) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        key = Path(folder) / "public.pem"
        key.write_bytes(pem)
        return subprocess.check_output(
            [str(openssl), "pkey", "-pubin", "-in", str(key), "-outform", "DER"],
            stderr=subprocess.DEVNULL,
        )


def verify_private_key_path(private_key: Path, registration: tuple[str, str, bytes],
                            openssl: Path, forbidden_roots: tuple[Path, ...]) -> None:
    if private_key.is_symlink() or not private_key.is_file():
        raise ValueError("private key must be an external regular file")
    resolved = private_key.resolve()
    for root in forbidden_roots:
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        raise ValueError("private key is inside a public/runtime output root")
    derived = subprocess.check_output(
        [str(openssl), "pkey", "-in", str(resolved), "-pubout", "-outform", "DER"],
        stderr=subprocess.DEVNULL,
    )
    if derived != _public_der(registration[2], openssl):
        raise ValueError("private key does not match owner registration")


def validate_custody(role: str, custody_root: Path) -> list[dict]:
    contract = ROLE_CONTRACT.get(role)
    if contract is None or custody_root.resolve() != Path(contract["custody"]).resolve():
        raise ValueError("cross-role or noncanonical custody root")
    manifest = load_canonical(custody_root / "custody.json")
    expected_custody = {
        "ADJUDICATOR_A": "01d969ffcd740a09d7445e2d68f96d92d6e3985653490965ff64878d73e92dd3",
        "ADJUDICATOR_B": "f938765643701e5c25d584dbd8a6af3c103875a6a3454c2542c1aa7005448804",
    }[role]
    if (manifest.get("custody_identity") != expected_custody
            or manifest.get("adjudicator_role") != role
            or manifest.get("adjudication_execution_boundary_identity") != BOUNDARY_IDENTITY
            or manifest.get("packet_count") != PACKET_COUNT
            or manifest.get("packet_inventory_root") != INVENTORY_ROOT
            or manifest.get("candidate_mapping_present") is not False
            or manifest.get("private_runtime_observations_present") is not False):
        raise ValueError("custody manifest mismatch")
    core = dict(manifest); claimed = core.pop("custody_identity")
    if identity(core) != claimed:
        raise ValueError("custody identity mismatch")
    paths = sorted((custody_root / "packets").glob("*.blind.json"))
    if len(paths) != PACKET_COUNT or any(path.is_symlink() for path in paths):
        raise ValueError("packet cardinality or symlink mismatch")
    packets: list[dict] = []
    inventory = []
    for path in paths:
        packet = load_canonical(path)
        core = dict(packet); packet_identity = core.pop("packet_identity", None)
        if (packet_identity != identity(core)
                or packet.get("source_boundary_identity")
                != "6b2c55935999aaf6da077c0dddd9289f3eec059665d9e361c93cad40aa67568e"
                or packet.get("candidate_alias") not in ("CANDIDATE-A", "CANDIDATE-B")
                or packet.get("candidate_mapping_present") is not False
                or packet.get("private_runtime_observation_present") is not False):
            raise ValueError("packet identity or blinding mismatch")
        raw = base64.b64decode(packet["raw_output_base64"], validate=True)
        if digest(raw) != packet["raw_output_sha256"]:
            raise ValueError("packet raw-output mismatch")
        relative = f"packets/{path.name}"
        inventory.append({"path": relative, "sha256": digest(path.read_bytes())})
        packets.append(packet)
    if identity(inventory) != INVENTORY_ROOT or identity(packets) != PROJECTION_ROOT:
        raise ValueError("packet inventory/projection root mismatch")
    return packets


def validate_output_root(role: str, output_root: Path) -> None:
    contract = ROLE_CONTRACT.get(role)
    if contract is None or output_root.resolve() != Path(contract["receipts"]).resolve():
        raise ValueError("cross-role or noncanonical receipt root")
    if output_root.exists() and (output_root.is_symlink() or not output_root.is_dir()):
        raise ValueError("receipt root is not a regular directory")
    output_root.mkdir(mode=0o700, parents=False, exist_ok=True)
    if output_root.stat().st_mode & 0o077:
        raise ValueError("receipt root permissions are not private")


def _write_no_clobber(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def sign_receipt(*, role: str, packet: Mapping[str, object], verdict: str,
                 private_key: Path, output_root: Path,
                 registration: tuple[str, str, bytes], openssl: Path) -> dict:
    if verdict not in VERDICTS:
        raise ValueError("invalid verdict")
    unsigned = unsigned_receipt(
        boundary_identity=BOUNDARY_IDENTITY, packet=packet, role=role,
        adjudicator_id=registration[0], key_sha256=registration[1], verdict=verdict,
    )
    message = canonical(unsigned)
    with tempfile.TemporaryDirectory(dir=output_root, prefix=".signing-") as folder:
        message_path = Path(folder) / "message"
        signature_path = Path(folder) / "signature"
        message_path.write_bytes(message)
        subprocess.run(
            [str(openssl), "pkeyutl", "-sign", "-inkey", str(private_key),
             "-rawin", "-in", str(message_path), "-out", str(signature_path)],
            check=True, capture_output=True,
        )
        signature = signature_path.read_bytes()
    if len(signature) != 64:
        raise ValueError("Ed25519 signature length invalid")
    receipt = {
        **unsigned,
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "receipt_identity": digest(message + signature),
    }
    verify_receipt(receipt, boundary_identity=BOUNDARY_IDENTITY, packet=packet,
                   registration=registration, openssl=openssl)
    target = output_root / f"{int(packet['global_ordinal']):04d}.receipt.json"
    _write_no_clobber(target, canonical(receipt))
    return receipt


def existing_receipts(*, role: str, output_root: Path, packets: list[dict],
                      registration: tuple[str, str, bytes], openssl: Path) -> dict[int, dict]:
    packet_by_ordinal = {int(packet["global_ordinal"]): packet for packet in packets}
    found: dict[int, dict] = {}
    for path in sorted(output_root.glob("*.receipt.json")):
        receipt = load_canonical(path)
        ordinal = int(receipt.get("global_ordinal", -1))
        if ordinal not in packet_by_ordinal or ordinal in found or path.name != f"{ordinal:04d}.receipt.json":
            raise ValueError("duplicate, replayed, or cross-row receipt")
        if receipt.get("adjudicator_role") != role:
            raise ValueError("cross-role receipt")
        verify_receipt(receipt, boundary_identity=BOUNDARY_IDENTITY,
                       packet=packet_by_ordinal[ordinal], registration=registration,
                       openssl=openssl)
        found[ordinal] = receipt
    return found


def write_progress(role: str, output_root: Path, receipts: Mapping[int, dict]) -> None:
    core = {
        "schema": "pastila-production-core-v15-r4-adjudicator-progress",
        "schema_version": 1,
        "boundary_identity": BOUNDARY_IDENTITY,
        "adjudicator_role": role,
        "completed": len(receipts),
        "required": PACKET_COUNT,
        "receipt_identities": [receipts[key]["receipt_identity"] for key in sorted(receipts)],
        "verdicts_disclosed": False,
    }
    value = {**core, "progress_identity": identity(core)}
    temporary = output_root / ".progress.json.tmp"
    temporary.write_bytes(canonical(value)); os.chmod(temporary, 0o400)
    os.replace(temporary, output_root / "progress.json")


def run_session(*, role: str, custody_root: Path, output_root: Path, private_key: Path,
                registry_path: Path, openssl: Path,
                decide: Callable[[Mapping[str, object]], str]) -> dict:
    registration = registry_registration(role, registry_path)
    packets = validate_custody(role, custody_root)
    validate_output_root(role, output_root)
    verify_private_key_path(private_key, registration, openssl,
                            (custody_root, output_root, registry_path.parent))
    receipts = existing_receipts(role=role, output_root=output_root, packets=packets,
                                 registration=registration, openssl=openssl)
    for packet in packets:
        ordinal = int(packet["global_ordinal"])
        if ordinal in receipts:
            continue
        verdict = decide(packet)
        receipts[ordinal] = sign_receipt(
            role=role, packet=packet, verdict=verdict, private_key=private_key,
            output_root=output_root, registration=registration, openssl=openssl,
        )
        write_progress(role, output_root, receipts)
    if len(receipts) != PACKET_COUNT:
        raise ValueError("incomplete per-role receipt closure")
    return {"role": role, "receipts": len(receipts), "closure": "COMPLETE_ROLE_CLOSURE"}
