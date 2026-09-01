"""Owner-operated signer for the frozen Pilot 10 unsigned packet."""

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
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-signing-packet-v1.json"
PROSPECTIVE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-preingestion-v1.json"
INDEPENDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-family-independence-v1.json"
REGISTRATION = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
FREEZE_COMMIT = "902a06567e60e76d0a31a5d6bd706fec53277f95"
PACKET_IDENTITY = "19a74d1147f3b1173e1ca07d8a2a852407920fdbe28e1ab75b5bf7580bab6fb5"
PREINGESTION_IDENTITY = "82054e36f0755764cd114fea811960ee9cfbc79f10e1c40dc369a25022e5954f"
SOURCE_PACKAGE_IDENTITY = "cd1c968bb7d90416b5255ad14094410491e756ce58bc78512cca2e5297a044c1"
AUTHORITY_ENVELOPE_IDENTITY = "fbae8cb29dcf203bae478b010fe19036239623551f22949b3cb56ac34ba18d21"
FAMILY_INDEPENDENCE_IDENTITY = "b06507f5239ab9215a21f120a01c65463b3fee48f5cf78ff70f9a83e440e398c"
PRIOR_LEDGER_HEAD = "0dc087dde79a0b008d333c4e84a0572b32cb9bd25704b9a55a00cb4d5849069a"


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
        raise SystemExit("Pilot 10 preparation commit is not an ancestor of HEAD")
    frozen_paths = [PACKET, PROSPECTIVE, INDEPENDENCE, REGISTRATION]
    relative_paths = [path.relative_to(ROOT).as_posix() for path in frozen_paths]
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", FREEZE_COMMIT, "--", *relative_paths], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if unchanged.returncode != 0:
        raise SystemExit("Pilot 10 frozen packet lineage differs from the preparation commit")
    core = packet["packet_core"]
    if packet["packet_identity"] != PACKET_IDENTITY or seal("B2_DEVELOPMENT_PILOT10_SIGNING_PACKET_V1", core) != PACKET_IDENTITY:
        raise SystemExit("Pilot 10 packet identity mismatch")
    if core["preingestion_identity"] != PREINGESTION_IDENTITY or core["prior_ledger_head"] != PRIOR_LEDGER_HEAD:
        raise SystemExit("Pilot 10 lineage mismatch")
    prospective = json.loads(PROSPECTIVE.read_text(encoding="utf-8"))
    independence = json.loads(INDEPENDENCE.read_text(encoding="utf-8"))
    if prospective["source_package_identity"] != SOURCE_PACKAGE_IDENTITY:
        raise SystemExit("Pilot 10 source-package mismatch")
    if prospective["factual_authority_envelope_identity"] != AUTHORITY_ENVELOPE_IDENTITY:
        raise SystemExit("Pilot 10 authority-envelope mismatch")
    if independence["family_independence_identity"] != FAMILY_INDEPENDENCE_IDENTITY:
        raise SystemExit("Pilot 10 family-independence mismatch")
    if len(prospective["factual_authority_envelope"]["propositions"]) != 7:
        raise SystemExit("Pilot 10 proposition-binding count mismatch")
    if packet["status"] != "UNSIGNED" or packet["signatures_present"] != 0 or len(packet["signature_requests"]) != 8:
        raise SystemExit("Pilot 10 packet is not exactly unsigned 8/8")
    if any((packet["proposition_sufficiency_evaluated"],
            packet["constructor_source_compatibility_or_release_performed"],
            packet["realization_candidate_emission_or_preemission_conformance_performed"],
            packet["fragment_collision_evaluation_performed"])):
        raise SystemExit("Pilot 10 downstream boundary mismatch")
    nonces: set[str] = set()
    for item in packet["signature_requests"]:
        challenge = item["challenge"]
        challenge_core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        if challenge["challenge_identity"] != seal("B2_PILOT10_SIGNING_CHALLENGE_V1", challenge_core):
            raise SystemExit("challenge identity mismatch")
        if challenge["packet_identity"] != PACKET_IDENTITY or challenge["prior_ledger_head"] != PRIOR_LEDGER_HEAD:
            raise SystemExit("challenge packet/ledger mismatch")
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
    registrations = {item["role"]: item for item in json.loads(REGISTRATION.read_text(encoding="utf-8"))["registrations"]}
    for item in packet["signature_requests"]:
        role = item["role"]
        stem = role.lower().replace("_", "-")
        private_key = key_directory / f"{stem}.private.pem"
        if not private_key.is_file():
            raise SystemExit(f"missing owner-controlled private key for {role}")
        output = response_directory / f"{item['operation_ordinal']:02d}-{stem}.pilot10-response.json"
        if output.exists():
            raise SystemExit(f"refusing overwrite: {output}")
        challenge_bytes = canonical(item["challenge"])
        algorithm = registrations[role]["algorithm"]
        with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot10-") as temporary:
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
            "schema_name": "batch2-development-pilot10-custodial-signature-response-v1",
            "schema_version": "1.0.0", "packet_identity": PACKET_IDENTITY,
            "operation_ordinal": item["operation_ordinal"], "purpose": item["purpose"], "signer_role": role,
            "principal_identity": item["challenge"]["principal_identity"],
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
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    signer = sub.add_parser("sign-all")
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
