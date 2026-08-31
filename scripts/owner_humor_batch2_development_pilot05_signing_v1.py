"""Owner-operated signer for the frozen Pilot 05 unsigned packet.

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
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot05-signing-packet-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
PACKET_ID = "a63721b2b2a442b195916919460ae7e455f2a25169efeb79f657afd91cf09bc3"
PREINGESTION_ID = "0d081b19b0fec01bf7cb5026f8c505dd2b9715fc18f8599e2c7dab6d67928037"
PRIOR_LEDGER_HEAD = "3a172491ec99d5f8c0ef2d4be075912b5518f6b42bb19641bd60ab9b20d26fd4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def outside_repo(path: Path) -> Path:
    value = path.expanduser().resolve()
    try:
        value.relative_to(ROOT.resolve())
    except ValueError:
        return value
    raise SystemExit(f"refusing repository-local secret/response path: {value}")


def verify_packet(packet: dict[str, Any]) -> None:
    if packet["packet_identity"] != PACKET_ID or seal("B2_DEVELOPMENT_PILOT05_SIGNING_PACKET_V1", packet["packet_core"]) != PACKET_ID:
        raise SystemExit("Pilot 05 packet identity mismatch")
    if packet["packet_core"]["preingestion_identity"] != PREINGESTION_ID or packet["packet_core"]["prior_ledger_head"] != PRIOR_LEDGER_HEAD:
        raise SystemExit("Pilot 05 lineage mismatch")
    if packet["status"] != "UNSIGNED" or packet["signatures_present"] != 0 or len(packet["signature_requests"]) != 8:
        raise SystemExit("Pilot 05 packet is not the frozen unsigned 8-request packet")
    nonces: set[str] = set()
    for item in packet["signature_requests"]:
        challenge = item["challenge"]
        core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        if challenge["challenge_identity"] != seal("B2_PILOT05_SIGNING_CHALLENGE_V1", core):
            raise SystemExit("challenge identity mismatch")
        if challenge["packet_identity"] != PACKET_ID or challenge["prior_ledger_head"] != PRIOR_LEDGER_HEAD:
            raise SystemExit("challenge packet/ledger mismatch")
        if challenge["role"] != item["role"] or challenge["purpose"] != item["purpose"]:
            raise SystemExit("challenge role/purpose mismatch")
        if challenge["nonce"] in nonces or challenge["grants_operational_content_access"] is not False:
            raise SystemExit("duplicate nonce or authority widening")
        nonces.add(challenge["nonce"])


def inspect(packet: dict[str, Any]) -> None:
    verify_packet(packet)
    print(json.dumps([{
        "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"], "signer_role": item["role"],
        "challenge_identity": item["challenge"]["challenge_identity"],
        "canonical_challenge_sha256": hashlib.sha256(canonical(item["challenge"])).hexdigest(),
        "nonce": item["challenge"]["nonce"], "prior_ledger_head": item["challenge"]["prior_ledger_head"],
    } for item in packet["signature_requests"]], indent=2, sort_keys=True))


def sign_all(packet: dict[str, Any], key_dir: Path, response_dir: Path) -> None:
    verify_packet(packet)
    key_dir, response_dir = outside_repo(key_dir), outside_repo(response_dir)
    response_dir.mkdir(parents=True, exist_ok=True)
    registrations = {item["role"]: item for item in json.loads(REGISTRATION.read_text(encoding="utf-8"))["registrations"]}
    for item in packet["signature_requests"]:
        role = item["role"]
        stem = role.lower().replace("_", "-")
        private_key = key_dir / f"{stem}.private.pem"
        if not private_key.is_file():
            raise SystemExit(f"missing owner-controlled private key for {role}")
        output = response_dir / f"{item['operation_ordinal']:02d}-{stem}.pilot05-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot05-") as temporary:
            message, signature = Path(temporary) / "challenge.bin", Path(temporary) / "signature.bin"
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
            "schema_name": "batch2-development-pilot05-custodial-signature-response-v1", "schema_version": "1.0.0",
            "packet_identity": packet["packet_identity"], "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
            "signer_role": role, "principal_identity": item["challenge"]["principal_identity"],
            "challenge_identity": item["challenge"]["challenge_identity"], "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
            "registered_public_key_fingerprint": registrations[role]["public_key_fingerprint"], "algorithm": algorithm,
            "signature": {"encoding": "BASE64", "value": signature_b64}, "private_key_included": False, "grants_operational_authority": False,
        }
        output.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"operation_ordinal": item["operation_ordinal"], "role": role, "public_response_path": str(output)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    signer = commands.add_parser("sign-all")
    signer.add_argument("--key-dir", type=Path, required=True)
    signer.add_argument("--response-dir", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    inspect(packet) if args.command == "inspect" else sign_all(packet, args.key_dir, args.response_dir)


if __name__ == "__main__":
    main()
