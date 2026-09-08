"""Candidate-neutral, offline semantic-adjudication receipts for Core V2."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pastila_scout.production_core_technical_output_envelope_v1 import (
    canonical_response_bytes,
)

SCHEMA = "pastila-production-core-semantic-adjudication-receipt"
SCHEMA_VERSION = 1
VERDICTS = frozenset({"PASS", "FAIL", "INDETERMINATE"})
ROLE_IDS = ("ADJUDICATOR_A", "ADJUDICATOR_B")
CANDIDATE_ALIASES = frozenset({"CANDIDATE-A", "CANDIDATE-B"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,127}$")
FROZEN_GENERATION_IDENTITY = "cfa6c00b96430246755c7cdce4c59b52d67946b91c1635077890c317b9afcadf"
FROZEN_CORPUS_IDENTITY = "5933f6ddb450a00566cb42a7dabd908975687360e5d9f16766d55b1dff7899b6"
FROZEN_RUBRIC_IDENTITY = "3bff615d5412abbde10a3ab85d45b82a0e019be196ea21914303d1e6b284353b"
FROZEN_REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
SIGNED_FIELDS = (
    "schema",
    "schema_version",
    "qualification_generation_sha256",
    "corpus_sha256",
    "case_id",
    "candidate_alias",
    "candidate_output_sha256",
    "assertion_id",
    "rubric_sha256",
    "adjudicator_registry_identity",
    "adjudicator_id",
    "adjudicator_role",
    "adjudicator_key_sha256",
    "verdict",
)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_unsigned(value: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(value)
    if tuple(item) != SIGNED_FIELDS:
        raise ValueError("receipt fields/order invalid")
    if (
        item["schema"] != SCHEMA
        or type(item["schema_version"]) is not int
        or item["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("receipt schema invalid")
    for field in (
        "qualification_generation_sha256",
        "corpus_sha256",
        "candidate_output_sha256",
        "rubric_sha256",
        "adjudicator_registry_identity",
        "adjudicator_key_sha256",
    ):
        if not isinstance(item[field], str) or not HEX64.fullmatch(item[field]):
            raise ValueError(f"{field} invalid")
    for field in ("case_id", "candidate_alias", "assertion_id", "adjudicator_id"):
        if not isinstance(item[field], str) or not ID.fullmatch(item[field]):
            raise ValueError(f"{field} invalid")
    if item["candidate_alias"] not in CANDIDATE_ALIASES:
        raise ValueError("candidate alias is not opaque")
    if item["adjudicator_role"] not in ROLE_IDS or item["verdict"] not in VERDICTS:
        raise ValueError("receipt enum invalid")
    return item


REGISTRY_FIELDS = (
    "schema",
    "schema_version",
    "status",
    "registration_basis_kit_commit",
    "registration_basis_kit_tree",
    "roles",
    "independence_assertion",
    "private_key_material_present",
    "candidate_execution_authorized",
    "candidate_promotion_effect",
    "registry_identity",
)
REGISTRY_ROLE_FIELDS = (
    "adjudicator_id",
    "public_key_format",
    "public_key_sha256",
    "public_key_pem_base64",
)
ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
AUTHORIZED_REGISTRY_ARTIFACT_SHA256 = (
    "9c0371fdbf5a455ac740f736b7733bab784422c177fd2a4534071e6f1a74327c"
)
AUTHORIZED_REGISTRY_IDENTITY = (
    "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
)
AUTHORIZED_REGISTRY_KIT_COMMIT = "776e673a640b1619edbeaf9b4aa2471bcc62d77d"
AUTHORIZED_REGISTRY_KIT_TREE = "44f25a7ea1a4598a75cd83bfa6560bf369a58162"


@dataclass(frozen=True)
class LoadedAdjudicatorRegistry:
    identity: str
    registrations: Mapping[str, tuple[str, str]]
    public_key_bytes: Mapping[str, bytes]


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate registry JSON key: {key}")
        result[key] = value
    return result


def load_adjudicator_registry(registry_bytes: bytes) -> LoadedAdjudicatorRegistry:
    """Validate one exact registry byte snapshot and materialize its public keys."""
    if type(registry_bytes) is not bytes:
        raise ValueError("registry snapshot must be immutable bytes")
    if sha256(registry_bytes) != AUTHORIZED_REGISTRY_ARTIFACT_SHA256:
        raise ValueError("registry artifact identity mismatch")
    try:
        value = json.loads(
            registry_bytes.decode("utf-8"), object_pairs_hook=_strict_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("registry encoding invalid") from exc
    if not isinstance(value, dict) or tuple(value) != REGISTRY_FIELDS:
        raise ValueError("registry fields/order invalid")
    if (
        value["schema"]
        != "pastila-production-core-semantic-adjudicator-public-key-registry"
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["status"] != "OWNER_REGISTERED_PUBLIC_IDENTITIES"
        or value["registration_basis_kit_commit"] != AUTHORIZED_REGISTRY_KIT_COMMIT
        or value["registration_basis_kit_tree"] != AUTHORIZED_REGISTRY_KIT_TREE
        or value["independence_assertion"]
        != "OWNER_DESIGNATED_DISTINCT_HUMAN_EVALUATORS_WITH_DISTINCT_PUBLIC_KEYS"
        or value["private_key_material_present"] is not False
        or value["candidate_execution_authorized"] is not False
        or value["candidate_promotion_effect"] is not False
    ):
        raise ValueError("registry authority invalid")
    roles = value["roles"]
    if not isinstance(roles, dict) or tuple(roles) != ROLE_IDS:
        raise ValueError("registry roles invalid")
    body = dict(value)
    claimed_identity = body.pop("registry_identity")
    if claimed_identity != AUTHORIZED_REGISTRY_IDENTITY or claimed_identity != sha256(
        canonical(body)
    ):
        raise ValueError("registry identity invalid")
    registrations: dict[str, tuple[str, str]] = {}
    keys: dict[str, bytes] = {}
    for role in ROLE_IDS:
        record = roles[role]
        if not isinstance(record, dict) or tuple(record) != REGISTRY_ROLE_FIELDS:
            raise ValueError("registry role fields/order invalid")
        adjudicator_id = record["adjudicator_id"]
        key_sha256 = record["public_key_sha256"]
        encoded = record["public_key_pem_base64"]
        if (
            not isinstance(adjudicator_id, str)
            or not ID.fullmatch(adjudicator_id)
            or record["public_key_format"]
            != "PEM_SUBJECT_PUBLIC_KEY_INFO_ED25519_EXACT_BYTES_BASE64"
            or not isinstance(key_sha256, str)
            or not HEX64.fullmatch(key_sha256)
            or not isinstance(encoded, str)
        ):
            raise ValueError("registry role authority invalid")
        try:
            key_bytes = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError("registry key encoding invalid") from exc
        if (
            base64.b64encode(key_bytes).decode("ascii") != encoded
            or sha256(key_bytes) != key_sha256
        ):
            raise ValueError("registry key identity invalid")
        lines = key_bytes.split(b"\r\n")
        if (
            len(lines) != 4
            or lines[0] != b"-----BEGIN PUBLIC KEY-----"
            or lines[2] != b"-----END PUBLIC KEY-----"
            or lines[3] != b""
        ):
            raise ValueError("registry key PEM invalid")
        try:
            der = base64.b64decode(lines[1], validate=True)
        except Exception as exc:
            raise ValueError("registry key DER encoding invalid") from exc
        if (
            base64.b64encode(der) != lines[1]
            or len(der) != 44
            or not der.startswith(ED25519_SPKI_PREFIX)
        ):
            raise ValueError("registry key is not exact Ed25519 SPKI")
        registrations[role] = (adjudicator_id, key_sha256)
        keys[role] = key_bytes
    if (
        len({x[0] for x in registrations.values()}) != 2
        or len({x[1] for x in registrations.values()}) != 2
    ):
        raise ValueError("registry adjudicators are not independent")
    return LoadedAdjudicatorRegistry(claimed_identity, registrations, keys)


def signed_message(value: Mapping[str, Any]) -> bytes:
    return canonical(_validate_unsigned(value))


def _run(
    command: list[str], *, timeout: int = 30, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command, capture_output=True, check=False, timeout=timeout, env=env
    )


def _run_pinned_openssl(
    openssl: Path,
    expected_runtime_sha256: Mapping[str, str],
    arguments: Sequence[str],
) -> subprocess.CompletedProcess[bytes]:
    required = ("openssl.exe", "libcrypto-3-x64.dll", "libssl-3-x64.dll")
    if (
        tuple(expected_runtime_sha256) != required
        or openssl.name.lower() != "openssl.exe"
    ):
        raise ValueError("OpenSSL runtime manifest invalid")
    source_root = openssl.parent
    snapshots: dict[str, bytes] = {}
    for name in required:
        path = source_root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("OpenSSL runtime object invalid")
        data = path.read_bytes()
        if sha256(data) != expected_runtime_sha256[name]:
            raise ValueError("OpenSSL runtime identity mismatch")
        snapshots[name] = data
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name, data in snapshots.items():
            (root / name).write_bytes(data)
        config = root / "openssl-empty.cnf"
        modules = root / "empty-modules"
        config.write_bytes(b"")
        modules.mkdir()
        environment = {
            "OPENSSL_CONF": str(config),
            "OPENSSL_MODULES": str(modules),
            "PATH": str(root),
            "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
        }
        return _run([str(root / "openssl.exe"), *arguments], env=environment)


def sign_receipt(
    value: Mapping[str, Any],
    *,
    private_key: Path,
    openssl: Path,
    expected_openssl_runtime_sha256: Mapping[str, str],
) -> dict[str, Any]:
    message = signed_message(value)
    if private_key.is_symlink() or not private_key.is_file():
        raise ValueError("private key invalid")
    private_key_bytes = private_key.read_bytes()
    if not private_key_bytes:
        raise ValueError("private key invalid")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        msg = root / "message"
        sig = root / "signature"
        key_snapshot = root / "private-key-snapshot.pem"
        msg.write_bytes(message)
        key_snapshot.write_bytes(private_key_bytes)
        run = _run_pinned_openssl(
            openssl,
            expected_openssl_runtime_sha256,
            [
                "pkeyutl",
                "-sign",
                "-inkey",
                str(key_snapshot),
                "-rawin",
                "-in",
                str(msg),
                "-out",
                str(sig),
            ],
        )
        if run.returncode or run.stdout or run.stderr:
            raise ValueError("receipt signing failed")
        signature = sig.read_bytes()
    result = dict(value)
    result["signature_base64"] = base64.b64encode(signature).decode("ascii")
    result["receipt_identity"] = sha256(message + signature)
    return result


def verify_receipt(
    receipt: Mapping[str, Any],
    *,
    public_key: Path,
    openssl: Path,
    expected_openssl_runtime_sha256: Mapping[str, str],
) -> str:
    item = dict(receipt)
    if tuple(item) != SIGNED_FIELDS + ("signature_base64", "receipt_identity"):
        raise ValueError("signed receipt fields/order invalid")
    signature_text = item.pop("signature_base64")
    claimed_identity = item.pop("receipt_identity")
    message = signed_message(item)
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except Exception as exc:
        raise ValueError("signature encoding invalid") from exc
    if (
        not signature
        or base64.b64encode(signature).decode("ascii") != signature_text
        or claimed_identity != sha256(message + signature)
    ):
        raise ValueError("receipt identity invalid")
    if public_key.is_symlink() or not public_key.is_file():
        raise ValueError("public key invalid")
    key_bytes = public_key.read_bytes()
    if sha256(key_bytes) != item["adjudicator_key_sha256"]:
        raise ValueError("adjudicator key identity mismatch")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        msg = root / "message"
        sig = root / "signature"
        key_snapshot = root / "public-key-snapshot.pem"
        msg.write_bytes(message)
        sig.write_bytes(signature)
        key_snapshot.write_bytes(key_bytes)
        run = _run_pinned_openssl(
            openssl,
            expected_openssl_runtime_sha256,
            [
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(key_snapshot),
                "-rawin",
                "-in",
                str(msg),
                "-sigfile",
                str(sig),
            ],
        )
    if (
        run.returncode
        or run.stdout != b"Signature Verified Successfully\n"
        or run.stderr
    ):
        raise ValueError("receipt signature invalid")
    return claimed_identity


def adjudicate_pair(
    receipts: Sequence[Mapping[str, Any]],
    *,
    public_keys: Mapping[str, Path],
    registered_adjudicators: Mapping[str, tuple[str, str]],
    expected_authority: Mapping[str, Any],
    openssl: Path,
    expected_openssl_runtime_sha256: Mapping[str, str],
) -> str:
    authority_fields = (
        "qualification_generation_sha256",
        "corpus_sha256",
        "case_id",
        "candidate_alias",
        "candidate_output_sha256",
        "assertion_id",
        "rubric_sha256",
        "adjudicator_registry_identity",
    )
    if (
        len(receipts) != 2
        or set(public_keys) != set(ROLE_IDS)
        or set(registered_adjudicators) != set(ROLE_IDS)
        or tuple(expected_authority) != authority_fields
    ):
        raise ValueError("two-adjudicator closure absent")
    if (
        len({value[0] for value in registered_adjudicators.values()}) != 2
        or len({value[1] for value in registered_adjudicators.values()}) != 2
    ):
        raise ValueError("registered adjudicators are not independent")
    verified: list[dict[str, Any]] = []
    for raw in receipts:
        item = dict(raw)
        role = item.get("adjudicator_role")
        if role not in public_keys:
            raise ValueError("adjudicator role unknown")
        registered_id, registered_key = registered_adjudicators[role]
        if (
            item.get("adjudicator_id") != registered_id
            or item.get("adjudicator_key_sha256") != registered_key
        ):
            raise ValueError("owner-registered adjudicator mismatch")
        if any(
            item.get(field) != expected_authority[field] for field in authority_fields
        ):
            raise ValueError("expected qualification authority mismatch")
        verify_receipt(
            item,
            public_key=public_keys[role],
            openssl=openssl,
            expected_openssl_runtime_sha256=expected_openssl_runtime_sha256,
        )
        verified.append(item)
    if {x["adjudicator_role"] for x in verified} != set(ROLE_IDS):
        raise ValueError("adjudicator roles duplicated")
    if len({x["adjudicator_key_sha256"] for x in verified}) != 2:
        raise ValueError("adjudicator keys not independent")
    bound = tuple(
        k
        for k in SIGNED_FIELDS
        if k
        not in {
            "adjudicator_id",
            "adjudicator_role",
            "adjudicator_key_sha256",
            "verdict",
        }
    )
    if any(verified[0][k] != verified[1][k] for k in bound):
        raise ValueError("adjudicators evaluated different authority")
    verdicts = [x["verdict"] for x in verified]
    return "PASS" if verdicts == ["PASS", "PASS"] else "FAIL_CLOSED"


def adjudicate_pair_from_registry(
    receipts: Sequence[Mapping[str, Any]],
    *,
    registry_bytes: bytes,
    blind_packet_bytes: bytes,
    blind_packet_path: str,
    export_inventory_bytes: bytes,
    custody_manifest_bytes: bytes,
    authorized_custody_identity: str,
    openssl: Path,
    expected_openssl_runtime_sha256: Mapping[str, str],
) -> str:
    """Adjudicate a structurally valid, identity-closed blind packet snapshot."""
    registry = load_adjudicator_registry(registry_bytes)
    try:
        inventory = json.loads(export_inventory_bytes, object_pairs_hook=_strict_pairs)
        custody = json.loads(custody_manifest_bytes, object_pairs_hook=_strict_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("custody authority is not canonical JSON") from exc
    if (
        not isinstance(inventory, list)
        or canonical(inventory) != export_inventory_bytes
        or not isinstance(custody, dict)
        or canonical(custody) != custody_manifest_bytes
        or not HEX64.fullmatch(authorized_custody_identity)
    ):
        raise ValueError("custody authority malformed")
    custody_fields = (
        "schema", "schema_version", "adjudicator_role",
        "qualification_generation_identity", "packet_count", "packets_root",
        "candidate_mapping_present", "private_observations_present",
        "custody_identity",
    )
    if tuple(custody) != custody_fields:
        raise ValueError("custody fields/order invalid")
    normalized_inventory: list[dict[str, str]] = []
    for row in inventory:
        if not isinstance(row, dict) or tuple(row) != ("path", "sha256"):
            raise ValueError("custody inventory row schema invalid")
        path = row.get("path")
        digest = row.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ValueError("custody inventory row value invalid")
        pure = PurePosixPath(path)
        if (
            not path.endswith(".blind.json")
            or not path.isascii()
            or "\\" in path
            or pure.is_absolute()
            or str(pure) != path
            or any(part in {"", ".", ".."} for part in pure.parts)
        ):
            raise ValueError("custody inventory path invalid")
        normalized_inventory.append({"path": path, "sha256": digest})
    if (
        len(normalized_inventory) != 2400
        or len({row["path"] for row in normalized_inventory}) != 2400
        or normalized_inventory != sorted(
            normalized_inventory, key=lambda row: row["path"].encode("ascii")
        )
    ):
        raise ValueError("custody inventory cardinality/order invalid")
    custody_core = dict(custody)
    custody_identity = custody_core.pop("custody_identity", None)
    if custody_identity != authorized_custody_identity or custody_identity != sha256(canonical(custody_core)):
        raise ValueError("custody identity is not owner-authorized")
    if (
        custody.get("schema") != "pastila-production-core-blind-export-custody-manifest"
        or type(custody.get("schema_version")) is not int
        or custody.get("schema_version") != 1
        or custody.get("adjudicator_role") not in ROLE_IDS
        or custody.get("qualification_generation_identity") != FROZEN_GENERATION_IDENTITY
        or type(custody.get("packet_count")) is not int
        or custody.get("packet_count") != len(inventory)
        or custody.get("packets_root") != sha256(export_inventory_bytes)
        or custody.get("candidate_mapping_present") is not False
        or custody.get("private_observations_present") is not False
    ):
        raise ValueError("custody closure mismatch")
    expected_member = {"path": blind_packet_path, "sha256": sha256(blind_packet_bytes)}
    if inventory.count(expected_member) != 1:
        raise ValueError("blind packet absent from authorized custody")
    try:
        packet = json.loads(blind_packet_bytes, object_pairs_hook=_strict_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("blind packet is not one JSON object") from exc
    if not isinstance(packet, dict) or canonical(packet) != blind_packet_bytes:
        raise ValueError("blind packet is not canonical")
    packet_core = dict(packet)
    packet_identity = packet_core.pop("packet_identity", None)
    if packet_identity != sha256(canonical(packet_core)):
        raise ValueError("blind packet identity mismatch")
    validation = packet.get("candidate_output_validation")
    if validation != {"status": "PASS", "failure_code": None, "failure_detail": None}:
        raise ValueError("structural FAIL is terminal")
    try:
        raw_output = base64.b64decode(packet["candidate_output_base64"], validate=True)
        case_id = packet["case"]["case_id"]
        request_identity = packet["case"]["request_identity"]
        output_type = packet["case"]["output_type"]
        assertion_id = packet["assertion"]["assertion_id"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("blind packet authority malformed") from exc
    if sha256(raw_output) != packet.get("candidate_output_sha256"):
        raise ValueError("blind packet raw-output identity mismatch")
    candidate_output = packet.get("candidate_output")
    if not isinstance(candidate_output, dict):
        raise TypeError("structural PASS output is not an object")
    try:
        independently_canonical = canonical_response_bytes(candidate_output)
    except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("structural PASS does not satisfy the response contract") from exc
    if independently_canonical != raw_output:
        raise ValueError("structural PASS raw/canonical output mismatch")
    if (
        candidate_output.get("case_id") != case_id
        or candidate_output.get("request_identity") != request_identity
        or candidate_output.get("output_type") != output_type
    ):
        raise ValueError("structural PASS case binding mismatch")
    if (
        packet.get("schema") != "pastila-production-core-blind-adjudication-packet"
        or type(packet.get("schema_version")) is not int
        or packet.get("schema_version") != 1
        or packet.get("qualification_generation_sha256") != FROZEN_GENERATION_IDENTITY
        or packet.get("corpus_sha256") != FROZEN_CORPUS_IDENTITY
        or packet.get("rubric_sha256") != FROZEN_RUBRIC_IDENTITY
        or packet.get("adjudicator_registry_identity") != FROZEN_REGISTRY_IDENTITY
    ):
        raise ValueError("blind packet frozen authority mismatch")
    expected_authority = {
        "qualification_generation_sha256": packet.get("qualification_generation_sha256"),
        "corpus_sha256": packet.get("corpus_sha256"),
        "case_id": case_id,
        "candidate_alias": packet.get("candidate_alias"),
        "candidate_output_sha256": packet.get("candidate_output_sha256"),
        "assertion_id": assertion_id,
        "rubric_sha256": packet.get("rubric_sha256"),
        "adjudicator_registry_identity": packet.get("adjudicator_registry_identity"),
    }
    if expected_authority.get("adjudicator_registry_identity") != registry.identity:
        raise ValueError("expected registry authority mismatch")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        public_keys: dict[str, Path] = {}
        for role in ROLE_IDS:
            path = root / f"{role}.public.pem"
            path.write_bytes(registry.public_key_bytes[role])
            public_keys[role] = path
        return adjudicate_pair(
            receipts,
            public_keys=public_keys,
            registered_adjudicators=registry.registrations,
            expected_authority=expected_authority,
            openssl=openssl,
            expected_openssl_runtime_sha256=expected_openssl_runtime_sha256,
        )
