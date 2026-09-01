"""Owner-operated signer for the frozen Pilot 12 unsigned packet."""

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
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-signing-packet-v1.json"
PROSPECTIVE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-preingestion-v1.json"
INDEPENDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-family-independence-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
FREEZE_COMMIT = "ee10e4b8714881b0eebe2f4bbcc29b7a8da83d73"
PACKET_IDENTITY = "5f9c0689ae8a92c9da648f5f6ea45fafc66fb2a340578f1996d03d4938782e6b"
PREINGESTION_IDENTITY = "3873ecef23559ab3ece679618d9f7290d0ee611c6e656bc3fb890432fe7a9ca6"
SOURCE_PACKAGE_IDENTITY = "24e76e7f17c28a093cddb9c8be355c1298030a17f4cec0cf126210c4a529e3b6"
AUTHORITY_ENVELOPE_IDENTITY = "f219f9188b7d35134f0271b40fe485c5525a4b094b72b8c7b51472385fa5a1f4"
FAMILY_INDEPENDENCE_IDENTITY = "de642c80a6c5ac0c2bad98ac1724ffe634ab0ceaef5476a7b5524b95db86606a"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def outside_repository(path: Path) -> Path:
    value = path.expanduser().resolve()
    try:
        value.relative_to(ROOT.resolve())
    except ValueError:
        return value
    raise SystemExit(f"refusing repository-local secret/response path: {value}")


def verify_packet(packet: dict[str, Any]) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", FREEZE_COMMIT, "HEAD"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if ancestor.returncode != 0:
        raise SystemExit("Pilot 12 preparation commit is not an ancestor of HEAD")
    paths = [PACKET, PROSPECTIVE, INDEPENDENCE, REGISTRATION]
    relative = [path.relative_to(ROOT).as_posix() for path in paths]
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", FREEZE_COMMIT, "--", *relative], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if unchanged.returncode != 0:
        raise SystemExit("Pilot 12 frozen packet lineage differs from preparation commit")
    core = packet["packet_core"]
    if packet["packet_identity"] != PACKET_IDENTITY:
        raise SystemExit("Pilot 12 packet identity mismatch")
    if seal("B2_DEVELOPMENT_PILOT12_SIGNING_PACKET_V1", core) != PACKET_IDENTITY:
        raise SystemExit("Pilot 12 packet seal mismatch")
    if core["preingestion_identity"] != PREINGESTION_IDENTITY:
        raise SystemExit("Pilot 12 lineage mismatch")
    prospective = json.loads(PROSPECTIVE.read_text(encoding="utf-8"))
    independence = json.loads(INDEPENDENCE.read_text(encoding="utf-8"))
    if prospective["source_package_identity"] != SOURCE_PACKAGE_IDENTITY:
        raise SystemExit("Pilot 12 source-package mismatch")
    if prospective["factual_authority_envelope_identity"] != AUTHORITY_ENVELOPE_IDENTITY:
        raise SystemExit("Pilot 12 authority-envelope mismatch")
    if independence["family_independence_identity"] != FAMILY_INDEPENDENCE_IDENTITY:
        raise SystemExit("Pilot 12 family-independence mismatch")
    if len(prospective["factual_authority_envelope"]["propositions"]) != 8:
        raise SystemExit("Pilot 12 proposition-binding count mismatch")
    if packet["status"] != "UNSIGNED" or packet["signatures_present"] != 0:
        raise SystemExit("Pilot 12 packet is not unsigned")
    if len(packet["signature_requests"]) != 8:
        raise SystemExit("Pilot 12 packet does not contain exactly eight requests")
    boundary_flags = (
        packet["proposition_sufficiency_evaluated"],
        packet["constructor_semantic_plan_release_or_invocation_performed"],
        packet["realization_candidate_emission_coordinate_conformance_or_semantic_edge_validation_performed"],
        packet["fragment_collision_evaluation_performed"],
        packet["source_ingested"],
        packet["archive_written"],
    )
    if any(boundary_flags) or packet["ledger_events_appended"] != 0:
        raise SystemExit("Pilot 12 downstream boundary mismatch")
    nonces: set[str] = set()
    for item in packet["signature_requests"]:
        challenge = item["challenge"]
        challenge_core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        if challenge["challenge_identity"] != seal("B2_PILOT12_SIGNING_CHALLENGE_V1", challenge_core):
            raise SystemExit("challenge identity mismatch")
        if challenge["packet_identity"] != PACKET_IDENTITY:
            raise SystemExit("challenge packet mismatch")
        if challenge["role"] != item["role"] or challenge["purpose"] != item["purpose"]:
            raise SystemExit("challenge role/purpose mismatch")
        if challenge["nonce"] in nonces or challenge["grants_operational_content_access"] is not False:
            raise SystemExit("nonce reuse or authority widening")
        nonces.add(challenge["nonce"])


def sign_all(packet: dict[str, Any], key_directory: Path, response_directory: Path) -> None:
    verify_packet(packet)
    key_directory = outside_repository(key_directory)
    response_directory = outside_repository(response_directory)
    response_directory.mkdir(parents=True, exist_ok=True)
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    registrations = {item["role"]: item for item in registration["registrations"]}
    for item in packet["signature_requests"]:
        role = item["role"]
        stem = role.lower().replace("_", "-")
        private_key = key_directory / f"{stem}.private.pem"
        if not private_key.is_file():
            raise SystemExit(f"missing owner-controlled private key for {role}")
        output = response_directory / f"{item['operation_ordinal']:02d}-{stem}.pilot12-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot12-") as temporary:
            message = Path(temporary) / "challenge.bin"
            signature = Path(temporary) / "signature.bin"
            message.write_bytes(challenge_bytes)
            if algorithm == "ED25519":
                command = ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", str(message), "-out", str(signature)]
            elif algorithm == "ECDSA_P256_SHA256":
                command = ["openssl", "dgst", "-sha256", "-sign", str(private_key), "-out", str(signature), str(message)]
            else:
                raise SystemExit(f"unsupported registered algorithm for {role}")
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            signature_base64 = base64.b64encode(signature.read_bytes()).decode("ascii")
        response = {
            "schema_name": "batch2-development-pilot12-custodial-signature-response-v1",
            "schema_version": "1.0.0", "packet_identity": PACKET_IDENTITY,
            "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
            "signer_role": role, "principal_identity": item["challenge"]["principal_identity"],
            "challenge_identity": item["challenge"]["challenge_identity"],
            "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
            "registered_public_key_fingerprint": registrations[role]["public_key_fingerprint"],
            "algorithm": algorithm, "signature": {"encoding": "BASE64", "value": signature_base64},
            "private_key_included": False, "grants_operational_authority": False,
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
    if args.command == "inspect":
        verify_packet(packet)
        print(json.dumps({"packet_identity": PACKET_IDENTITY, "requests": len(packet["signature_requests"]),
                          "verdict": "PASS_INSPECTION_ONLY"}, sort_keys=True))
    else:
        sign_all(packet, args.key_dir, args.response_dir)


if __name__ == "__main__":
    main()
