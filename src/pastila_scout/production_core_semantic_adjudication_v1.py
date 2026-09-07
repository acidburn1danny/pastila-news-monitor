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
from pathlib import Path
from typing import Any

SCHEMA = "pastila-production-core-semantic-adjudication-receipt"
SCHEMA_VERSION = 1
VERDICTS = frozenset({"PASS", "FAIL", "INDETERMINATE"})
ROLE_IDS = ("ADJUDICATOR_A", "ADJUDICATOR_B")
CANDIDATE_ALIASES = frozenset({"CANDIDATE-A", "CANDIDATE-B"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,127}$")
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
