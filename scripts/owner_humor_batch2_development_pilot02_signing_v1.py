"""Owner-operated signer for the frozen Pilot 02 unsigned packet.

The assistant may run ``inspect`` but must never run ``sign-all``.
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
REQUEST = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot02-signing-packet-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def outside_repo(path: Path) -> Path:
    value = path.expanduser().resolve()
    try:
        value.relative_to(ROOT.resolve())
    except ValueError:
        return value
    raise SystemExit(f"refusing repository-local secret/response path: {value}")


def inspect(packet: dict[str, Any]) -> None:
    print(json.dumps([{
        "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"], "signer_role": item["role"],
        "challenge_identity": item["challenge"]["challenge_identity"],
        "canonical_challenge_sha256": hashlib.sha256(canonical(item["challenge"])).hexdigest(),
        "nonce": item["challenge"]["nonce"], "prior_ledger_head": item["challenge"]["prior_ledger_head"],
    } for item in packet["signature_requests"]], indent=2, sort_keys=True))


def sign_all(packet: dict[str, Any], key_dir: Path, response_dir: Path) -> None:
    key_dir, response_dir = outside_repo(key_dir), outside_repo(response_dir)
    response_dir.mkdir(parents=True, exist_ok=True)
    registrations = {x["role"]: x for x in json.loads(REGISTRATION.read_text(encoding="utf-8"))["registrations"]}
    for item in packet["signature_requests"]:
        role = item["role"]
        stem = role.lower().replace("_", "-")
        private_key = key_dir / f"{stem}.private.pem"
        if not private_key.is_file():
            raise SystemExit(f"missing owner-controlled private key for {role}")
        output = response_dir / f"{item['operation_ordinal']:02d}-{stem}.pilot02-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot02-") as tmp:
            message, signature = Path(tmp) / "challenge.bin", Path(tmp) / "signature.bin"
            message.write_bytes(challenge_bytes)
            if algorithm == "ED25519":
                command = ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", str(message), "-out", str(signature)]
            elif algorithm == "ECDSA_P256_SHA256":
                command = ["openssl", "dgst", "-sha256", "-sign", str(private_key), "-out", str(signature), str(message)]
            else:
                raise SystemExit(f"unsupported registered algorithm for {role}")
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            signature_b64 = base64.b64encode(signature.read_bytes()).decode("ascii")
        response = {
            "schema_name": "batch2-development-pilot02-custodial-signature-response-v1", "schema_version": "1.0.0",
            "packet_identity": packet["packet_identity"], "operation_ordinal": item["operation_ordinal"],
            "purpose": item["purpose"], "signer_role": role, "principal_identity": item["challenge"]["principal_identity"],
            "challenge_identity": item["challenge"]["challenge_identity"],
            "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
            "registered_public_key_fingerprint": registrations[role]["public_key_fingerprint"], "algorithm": algorithm,
            "signature": {"encoding": "BASE64", "value": signature_b64}, "private_key_included": False,
            "grants_operational_authority": False,
        }
        output.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"operation_ordinal": item["operation_ordinal"], "role": role, "public_response_path": str(output)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    signer = sub.add_parser("sign-all")
    signer.add_argument("--key-dir", type=Path, required=True)
    signer.add_argument("--response-dir", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(REQUEST.read_text(encoding="utf-8"))
    inspect(packet) if args.command == "inspect" else sign_all(packet, args.key_dir, args.response_dir)


if __name__ == "__main__":
    main()
