"""Owner-operated signer for the frozen Pilot 14 unsigned packet."""

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
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot14-signing-packet-v1.json"
PROSPECTIVE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot14-preingestion-v1.json"
INDEPENDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot14-family-independence-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
FREEZE_COMMIT = "5d9cffb5dc0b233789bba62e7635d7d7efa3cfad"
PACKET_IDENTITY = "7da09be0c2c5e4fc909986615dfa6bd0862d706e19665c719c744bbcd97a1858"
PREINGESTION_IDENTITY = "0409ca68b7abd4bc6784637a7e775a3c341046ac5a22b9147f3997cce50de4a4"
SOURCE_COMMITMENT = "5ac22f1c751961f9cc7f91ca97aafe57cfcc2889995530616a7c1cdc5cda77a2"
RIGHTS_IDENTITY = "c06955632d5578224dbcbba92b14872267aef4ba12d1dcb73afba2a5d8671a88"
SOURCE_PACKAGE_IDENTITY = "676ebacdbf0f8b660b87720798e99fa398c6bb7b46700a25e423c28b5ee9939f"
AUTHORITY_ENVELOPE_IDENTITY = "7b5eddc2a15d25eebfb84930abdc2db3c5236e1b4deb67e2b56555301c161075"
ARCHIVE_COMMITMENT = "7dfd0c4f28babc08704f8b40f67548568e8363d95d6ed220c2e3968350c5b4d4"
FAMILY_INDEPENDENCE_IDENTITY = "54b3c816b132d8c7158ad7838d069fecb352a5f9a6034e6e2e9e4383bebf9b81"
FAMILY_CLOSURE_IDENTITY = "313fea82d4e9bf87575460210d0d29dae96ffc2d93d5b5a75da1c2ce99bbc226"
PARTITION_IDENTITY = "ce65e5c102087d26ebc06d4dea6d954d104bec2b1a7e482a64814c483953fd8b"


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
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_COMMIT, "HEAD"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if ancestor.returncode != 0:
        raise SystemExit("Pilot 14 preparation commit is not an ancestor of HEAD")
    paths = [PACKET, PROSPECTIVE, INDEPENDENCE, REGISTRATION]
    relative = [path.relative_to(ROOT).as_posix() for path in paths]
    unchanged = subprocess.run(["git", "diff", "--quiet", FREEZE_COMMIT, "--", *relative], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if unchanged.returncode != 0:
        raise SystemExit("Pilot 14 frozen packet lineage differs from preparation commit")
    core = packet["packet_core"]
    if packet["packet_identity"] != PACKET_IDENTITY or seal("B2_DEVELOPMENT_PILOT14_SIGNING_PACKET_V1", core) != PACKET_IDENTITY:
        raise SystemExit("Pilot 14 packet identity/seal mismatch")
    if core["preingestion_identity"] != PREINGESTION_IDENTITY:
        raise SystemExit("Pilot 14 lineage mismatch")
    prospective = json.loads(PROSPECTIVE.read_text(encoding="utf-8"))
    independence = json.loads(INDEPENDENCE.read_text(encoding="utf-8"))
    expected = {
        "source_commitment": SOURCE_COMMITMENT,
        "rights_instrument_identity": RIGHTS_IDENTITY,
        "source_package_identity": SOURCE_PACKAGE_IDENTITY,
        "factual_authority_envelope_identity": AUTHORITY_ENVELOPE_IDENTITY,
        "immutable_archive_commitment": ARCHIVE_COMMITMENT,
        "prospective_partition_identity": PARTITION_IDENTITY,
    }
    for field, identity in expected.items():
        if prospective[field] != identity:
            raise SystemExit(f"Pilot 14 {field} mismatch")
    if prospective["family_identities"]["family_closure"] != FAMILY_CLOSURE_IDENTITY:
        raise SystemExit("Pilot 14 family-closure mismatch")
    if independence["family_independence_identity"] != FAMILY_INDEPENDENCE_IDENTITY:
        raise SystemExit("Pilot 14 family-independence mismatch")
    if prospective["proposition_binding_status"] != "PASS_8_BOUND_NOT_SELECTED":
        raise SystemExit("Pilot 14 proposition-binding status mismatch")
    if prospective["selected_proposition"] != "UNASSIGNED" or prospective["proposition_sufficiency_evaluated"] is not False:
        raise SystemExit("Pilot 14 proposition selection/sufficiency boundary mismatch")
    if len(prospective["factual_authority_envelope"]["propositions"]) != 8:
        raise SystemExit("Pilot 14 proposition-binding count mismatch")
    if packet["status"] != "UNSIGNED" or packet["signatures_present"] != 0 or len(packet["signature_requests"]) != 8:
        raise SystemExit("Pilot 14 packet is not the unsigned eight-request packet")
    if packet["source_ingested"] or packet["archive_written"] or packet["ledger_events_appended"] != 0:
        raise SystemExit("Pilot 14 response-consumption boundary mismatch")
    if packet["proposition_sufficiency_evaluated"] or packet["downstream_planning_or_construction_performed"]:
        raise SystemExit("Pilot 14 downstream boundary mismatch")
    nonces: set[str] = set()
    for item in packet["signature_requests"]:
        challenge = item["challenge"]
        challenge_core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        if challenge["challenge_identity"] != seal("B2_PILOT14_SIGNING_CHALLENGE_V1", challenge_core):
            raise SystemExit("challenge identity mismatch")
        if challenge["packet_identity"] != PACKET_IDENTITY or challenge["role"] != item["role"] or challenge["purpose"] != item["purpose"]:
            raise SystemExit("challenge packet/role/purpose mismatch")
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
        output = response_directory / f"{item['operation_ordinal']:02d}-{stem}.pilot14-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot14-") as temporary:
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
        response = {"schema_name": "batch2-development-pilot14-custodial-signature-response-v1", "schema_version": "1.0.0",
                    "packet_identity": PACKET_IDENTITY, "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"],
                    "signer_role": role, "principal_identity": item["challenge"]["principal_identity"],
                    "challenge_identity": item["challenge"]["challenge_identity"],
                    "canonical_challenge_sha256": hashlib.sha256(challenge_bytes).hexdigest(),
                    "registered_public_key_fingerprint": registrations[role]["public_key_fingerprint"],
                    "algorithm": algorithm, "signature": {"encoding": "BASE64", "value": signature_base64},
                    "private_key_included": False, "grants_operational_authority": False}
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
    if args.command == "inspect":
        verify_packet(packet)
        print(json.dumps({"packet_identity": PACKET_IDENTITY, "requests": len(packet["signature_requests"]), "verdict": "PASS_INSPECTION_ONLY"}, sort_keys=True))
    else:
        sign_all(packet, args.key_dir, args.response_dir)


if __name__ == "__main__":
    main()
