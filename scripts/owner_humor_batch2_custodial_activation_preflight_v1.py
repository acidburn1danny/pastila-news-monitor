"""Owner-operated signer for the content-free activation-preflight batch.

The assistant must not execute sign-all. It is provided for the owner who
controls the already-enrolled private keys outside the repository.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUEST = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-activation-preflight-request-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def outside_repository(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise SystemExit(f"refusing repository-local secret/response path: {resolved}")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def inspect(request: dict[str, Any]) -> None:
    print(json.dumps([{
        "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
        "signer_role": item["signer_role"],
        "challenge_identity": item["challenge"]["challenge_identity"],
        "nonce": item["challenge"]["nonce"],
        "prior_ledger_head": item["challenge"]["prior_ledger_head"],
        "canonical_challenge_sha256": hashlib.sha256(canonical(item["challenge"])).hexdigest(),
    } for item in request["signature_requests"]], indent=2, sort_keys=True))


def sign_all(request: dict[str, Any], key_dir: Path, response_dir: Path) -> None:
    key_dir = outside_repository(key_dir)
    response_dir = outside_repository(response_dir)
    response_dir.mkdir(parents=True, exist_ok=True)
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    registered = {item["role"]: item for item in registration["registrations"]}
    for item in request["signature_requests"]:
        role = item["signer_role"]
        stem = role.lower().replace("_", "-")
        private_path = key_dir / f"{stem}.private.pem"
        if not private_path.is_file():
            raise SystemExit(f"missing owner-controlled private key for {role}")
        response_path = response_dir / f"{item['operation_ordinal']:02d}-{stem}.preflight-response.json"
        if response_path.exists():
            raise SystemExit(f"refusing overwrite: {response_path}")
        challenge_bytes = canonical(item["challenge"])
        with tempfile.TemporaryDirectory(prefix="pastila-b2-activation-") as temporary:
            temp = Path(temporary)
            challenge_path = temp / "challenge.bin"
            signature_path = temp / "signature.bin"
            challenge_path.write_bytes(challenge_bytes)
            algorithm = registered[role]["algorithm"]
            if algorithm == "ED25519":
                run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_path),
                     "-in", str(challenge_path), "-out", str(signature_path)])
            elif algorithm == "ECDSA_P256_SHA256":
                run(["openssl", "dgst", "-sha256", "-sign", str(private_path),
                     "-out", str(signature_path), str(challenge_path)])
            else:
                raise SystemExit(f"unsupported registered algorithm for {role}")
            signature = signature_path.read_bytes()
        response = {
            "schema_name": "batch2-custodial-activation-preflight-signature-response-v1",
            "schema_version": "1.0.0", "request_identity": request["request_identity"],
            "batch_identity": request["batch_identity"],
            "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
            "signer_role": role, "principal_identity": item["principal_identity"],
            "challenge_identity": item["challenge"]["challenge_identity"],
            "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
            "registered_public_key_fingerprint": registered[role]["public_key_fingerprint"],
            "algorithm": algorithm,
            "signature": {"encoding": "BASE64", "value": base64.b64encode(signature).decode("ascii")},
            "private_key_included": False, "grants_operational_authority": False,
        }
        response_path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8", newline="\n")
        print(json.dumps({"role": role, "operation_ordinal": item["operation_ordinal"],
                          "public_response_path": str(response_path)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sign = sub.add_parser("sign-all")
    sign.add_argument("--key-dir", type=Path, required=True)
    sign.add_argument("--response-dir", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if args.command == "inspect":
        inspect(request)
    else:
        sign_all(request, args.key_dir, args.response_dir)


if __name__ == "__main__":
    main()
