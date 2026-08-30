"""Owner-operated custodial key enrollment helper.

The assistant may run only inspect. prepare-role generates and uses a private
key and is intentionally reserved for the owner. Private keys and response
files must be stored outside the repository.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUEST = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-key-enrollment-request-v1.json"
REQUEST_ID = "c5439550d6a6d86a9a88893cbeb2f88712d6fdcc5fc7b05b08b981ef275c0e04"
ROLES = (
    "RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN", "FAMILY_CUSTODIAN",
    "PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN", "CONTAMINATION_AUDITOR",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_request(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["enrollment_request_identity"] != REQUEST_ID:
        raise SystemExit("enrollment request identity mismatch")
    if tuple(item["role"] for item in data["requests"]) != ROLES:
        raise SystemExit("role order/set mismatch")
    return data


def role_request(data: dict[str, Any], role: str) -> dict[str, Any]:
    return next(item for item in data["requests"] if item["role"] == role)


def outside_repository(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise SystemExit(f"refusing repository-local secret/response path: {resolved}")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def fingerprint(public_der: bytes) -> str:
    return hashlib.sha256(public_der).hexdigest()


def inspect(data: dict[str, Any]) -> None:
    safe = []
    for item in data["requests"]:
        challenge = item["challenge"]
        safe.append({
            "role": item["role"], "principal_identity": item["principal_identity"],
            "challenge_identity": challenge["challenge_identity"],
            "domain": challenge["domain"], "purpose": challenge["purpose"],
            "appointment_registry_identity": challenge["appointment_registry_identity"],
            "previous_ledger_hash": challenge["previous_ledger_hash"],
            "json_pointer": f"/requests/{len(safe)}/challenge",
            "canonical_challenge_sha256": hashlib.sha256(canonical(challenge)).hexdigest(),
        })
    print(json.dumps(safe, indent=2, sort_keys=True))


def prepare_role(data: dict[str, Any], role: str, algorithm: str, key_dir: Path,
                 response_dir: Path, owner_identity: str) -> None:
    key_dir = outside_repository(key_dir)
    response_dir = outside_repository(response_dir)
    key_dir.mkdir(parents=True, exist_ok=True)
    response_dir.mkdir(parents=True, exist_ok=True)
    item = role_request(data, role)
    stem = role.lower().replace("_", "-")
    private_path = key_dir / f"{stem}.private.pem"
    public_path = response_dir / f"{stem}.public.pem"
    response_path = response_dir / f"{stem}.response.json"
    for path in (private_path, public_path, response_path):
        if path.exists():
            raise SystemExit(f"refusing overwrite: {path}")
    challenge_bytes = canonical(item["challenge"])
    with tempfile.TemporaryDirectory(prefix="pastila-b2-enroll-") as temporary:
        temp = Path(temporary)
        challenge_path = temp / "challenge.bin"
        signature_path = temp / "signature.bin"
        der_path = temp / "public.der"
        challenge_path.write_bytes(challenge_bytes)
        if algorithm == "ED25519":
            run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_path)])
            run(["openssl", "pkey", "-in", str(private_path), "-pubout", "-out", str(public_path)])
            run(["openssl", "pkey", "-pubin", "-in", str(public_path), "-outform", "DER", "-out", str(der_path)])
            run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_path),
                 "-in", str(challenge_path), "-out", str(signature_path)])
            run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public_path),
                 "-in", str(challenge_path), "-sigfile", str(signature_path)])
        elif algorithm == "ECDSA_P256_SHA256":
            run(["openssl", "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256",
                 "-out", str(private_path)])
            run(["openssl", "pkey", "-in", str(private_path), "-pubout", "-out", str(public_path)])
            run(["openssl", "pkey", "-pubin", "-in", str(public_path), "-outform", "DER", "-out", str(der_path)])
            run(["openssl", "dgst", "-sha256", "-sign", str(private_path), "-out", str(signature_path),
                 str(challenge_path)])
            run(["openssl", "dgst", "-sha256", "-verify", str(public_path), "-signature",
                 str(signature_path), str(challenge_path)])
        else:
            raise SystemExit("unsupported algorithm")
        os.chmod(private_path, 0o600)
        public_der = der_path.read_bytes()
        signature = signature_path.read_bytes()
    response = {
        "schema_name": "batch2-custodial-key-enrollment-response-v1",
        "schema_version": "1.0.0", "enrollment_request_identity": REQUEST_ID,
        "role": role, "principal_identity": item["principal_identity"],
        "challenge_identity": item["challenge"]["challenge_identity"],
        "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
        "algorithm": algorithm,
        "public_key": {"format": "PEM_SPKI", "value": public_path.read_text(encoding="ascii")},
        "public_key_fingerprint": {"method": "SHA256_SPKI_DER", "value": fingerprint(public_der)},
        "proof_signature": {"encoding": "BASE64", "value": base64.b64encode(signature).decode("ascii")},
        "owner_confirmation": {
            "owner_identity": owner_identity, "confirmed": True, "role": role,
            "principal_identity": item["principal_identity"],
            "public_key_fingerprint": fingerprint(public_der),
            "statement": "I bind this public key exclusively to this custodial role and retain the private key outside the repository.",
        },
        "private_key_included": False,
    }
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8", newline="\n")
    print(json.dumps({"role": role, "public_response_path": str(response_path),
                      "fingerprint": fingerprint(public_der)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    prepare = sub.add_parser("prepare-role")
    prepare.add_argument("--role", choices=ROLES, required=True)
    prepare.add_argument("--algorithm", choices=("ED25519", "ECDSA_P256_SHA256"), default="ED25519")
    prepare.add_argument("--key-dir", type=Path, required=True)
    prepare.add_argument("--response-dir", type=Path, required=True)
    prepare.add_argument("--owner-identity", required=True)
    args = parser.parse_args()
    data = load_request(args.request)
    if args.command == "inspect":
        inspect(data)
    else:
        prepare_role(data, args.role, args.algorithm, args.key_dir, args.response_dir,
                     args.owner_identity)


if __name__ == "__main__":
    main()
