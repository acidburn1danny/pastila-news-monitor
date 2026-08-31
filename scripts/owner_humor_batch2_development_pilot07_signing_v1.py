"""Owner-operated signer for the frozen Pilot 07 unsigned packet."""

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
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-signing-packet-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
PACKET_ID = "a859db33f8f87d00dffaf4fcb8f64fdd35bb48ec5fbbf66c545463478416b7e1"
PREINGESTION_ID = "c97b26476cf056c332085d0dc97b155a9e7f8021d532556311141a2ba6a531bb"
PRIOR_LEDGER_HEAD = "a92ba489bc32a5b62d3adf48c655703c107dde2ebc241b93cfc95ad39a91548f"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


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
    core = packet["packet_core"]
    if packet["packet_identity"] != PACKET_ID or seal("B2_DEVELOPMENT_PILOT07_SIGNING_PACKET_V1", core) != PACKET_ID:
        raise SystemExit("Pilot 07 packet identity mismatch")
    if core["preingestion_identity"] != PREINGESTION_ID or core["prior_ledger_head"] != PRIOR_LEDGER_HEAD:
        raise SystemExit("Pilot 07 lineage mismatch")
    if packet["status"] != "UNSIGNED" or packet["signatures_present"] != 0 or len(packet["signature_requests"]) != 8:
        raise SystemExit("Pilot 07 packet is not the frozen unsigned 8-request packet")
    if packet["proposition_sufficiency_evaluated"] is not False:
        raise SystemExit("proposition sufficiency boundary mismatch")
    nonces: set[str] = set()
    for item in packet["signature_requests"]:
        challenge = item["challenge"]
        challenge_core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        if challenge["challenge_identity"] != seal("B2_PILOT07_SIGNING_CHALLENGE_V1", challenge_core):
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
        output = response_dir / f"{item['operation_ordinal']:02d}-{stem}.pilot07-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot07-") as temporary:
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
            "schema_name": "batch2-development-pilot07-custodial-signature-response-v1", "schema_version": "1.0.0",
            "packet_identity": PACKET_ID, "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
            "signer_role": role, "principal_identity": item["challenge"]["principal_identity"],
            "challenge_identity": item["challenge"]["challenge_identity"],
            "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
            "registered_public_key_fingerprint": registrations[role]["public_key_fingerprint"], "algorithm": algorithm,
            "signature": {"encoding": "BASE64", "value": signature_b64}, "private_key_included": False,
            "grants_operational_authority": False,
        }
        output.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"operation_ordinal": item["operation_ordinal"], "role": role,
                          "public_response_path": str(output)}, sort_keys=True))


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
