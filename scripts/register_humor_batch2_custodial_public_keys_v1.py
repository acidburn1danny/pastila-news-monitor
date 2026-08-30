"""Verify six public enrollment responses and freeze public registrations."""

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
REQUEST_COMMIT = "be9bd9ca812468b46cc0c0924cb5db5392ae98d4"
REQUEST_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-key-enrollment-request-v1.json"
REQUEST_ID = "c5439550d6a6d86a9a88893cbeb2f88712d6fdcc5fc7b05b08b981ef275c0e04"
RUNBOOK_COMMIT = "bad0c7311999b6401659d292f3ef69e7af65e53c"
PREVIOUS_LEDGER_HEAD = "4d8cc1c7907523f44d611ea4fe8e38908b3e37e97f623d3511fd02b842634642"
ROLES = (
    "RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN", "FAMILY_CUSTODIAN",
    "PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN", "CONTAMINATION_AUDITOR",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_request() -> dict[str, Any]:
    raw = subprocess.check_output(["git", "show", f"{REQUEST_COMMIT}:{REQUEST_PATH}"], cwd=ROOT)
    data = json.loads(raw)
    if data["enrollment_request_identity"] != REQUEST_ID:
        raise SystemExit("committed enrollment request identity mismatch")
    return data


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def response_files(directory: Path) -> list[Path]:
    paths = sorted(directory.glob("*.response.json"))
    if len(paths) != 6:
        raise SystemExit(f"expected six response files, found {len(paths)}")
    forbidden = [path for path in directory.iterdir()
                 if path.is_file() and any(token in path.name.lower()
                                           for token in ("private", ".key", ".der", ".sig"))]
    if forbidden:
        raise SystemExit(f"forbidden secret-like file in handoff: {forbidden[0].name}")
    return paths


def verify_response(response_path: Path, request_item: dict[str, Any]) -> dict[str, Any]:
    raw = response_path.read_bytes()
    if b"PRIVATE KEY" in raw:
        raise SystemExit(f"{response_path.name}: private key marker")
    response = json.loads(raw)
    required = {
        "schema_name", "schema_version", "enrollment_request_identity", "role",
        "principal_identity", "challenge_identity", "canonical_challenge_sha256",
        "algorithm", "public_key", "public_key_fingerprint", "proof_signature",
        "owner_confirmation", "private_key_included",
    }
    if set(response) != required:
        raise SystemExit(f"{response_path.name}: response field set mismatch")
    role = request_item["role"]
    challenge = request_item["challenge"]
    if response["enrollment_request_identity"] != REQUEST_ID:
        raise SystemExit(f"{role}: enrollment request mismatch")
    if response["role"] != role or response["principal_identity"] != request_item["principal_identity"]:
        raise SystemExit(f"{role}: role/principal substitution")
    if response["challenge_identity"] != challenge["challenge_identity"]:
        raise SystemExit(f"{role}: challenge substitution")
    frozen_bindings_match = (
        challenge["domain"] == "PASTILA_BATCH2_OWNED_AUTHORITY_KEY_ENROLLMENT_V1"
        and challenge["purpose"] == "CUSTODIAL_PUBLIC_KEY_PROOF_OF_POSSESSION"
        and challenge["appointment_registry_identity"]
        == "e5b4ebb9fe29244a8d760337dcd66253264a42edd9b3540bb3fd5a44f91206d5"
        and challenge["previous_ledger_hash"]
        == "8afc9aa54bf66d385d8e89d84f18884e06e6838acc9c1e3cc4127d1450442ad1"
    )
    if not frozen_bindings_match:
        raise SystemExit(f"{role}: frozen challenge binding mismatch")
    challenge_bytes = canonical(challenge)
    challenge_sha = hashlib.sha256(challenge_bytes).hexdigest()
    if response["canonical_challenge_sha256"] != challenge_sha:
        raise SystemExit(f"{role}: canonical challenge hash mismatch")
    algorithm = response["algorithm"]
    if algorithm not in request_item["accepted_algorithms"]:
        raise SystemExit(f"{role}: algorithm not permitted")
    if response["public_key"].get("format") != "PEM_SPKI":
        raise SystemExit(f"{role}: public key format")
    if response["public_key_fingerprint"].get("method") != "SHA256_SPKI_DER":
        raise SystemExit(f"{role}: fingerprint method")
    if response["proof_signature"].get("encoding") != "BASE64":
        raise SystemExit(f"{role}: signature encoding")
    try:
        signature = base64.b64decode(response["proof_signature"]["value"], validate=True)
    except ValueError as error:
        raise SystemExit(f"{role}: invalid signature base64") from error
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pop-") as temporary:
        temp = Path(temporary)
        public_path = temp / "public.pem"
        der_path = temp / "public.der"
        challenge_path = temp / "challenge.bin"
        signature_path = temp / "signature.bin"
        public_path.write_text(response["public_key"]["value"], encoding="ascii", newline="\n")
        challenge_path.write_bytes(challenge_bytes)
        signature_path.write_bytes(signature)
        run(["openssl", "pkey", "-pubin", "-in", str(public_path), "-outform", "DER", "-out", str(der_path)])
        public_der = der_path.read_bytes()
        if algorithm == "ED25519":
            run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public_path),
                 "-in", str(challenge_path), "-sigfile", str(signature_path)])
        elif algorithm == "ECDSA_P256_SHA256":
            run(["openssl", "dgst", "-sha256", "-verify", str(public_path), "-signature",
                 str(signature_path), str(challenge_path)])
        else:
            raise SystemExit(f"{role}: unsupported allowed algorithm")
    fingerprint = hashlib.sha256(public_der).hexdigest()
    if response["public_key_fingerprint"]["value"] != fingerprint:
        raise SystemExit(f"{role}: fingerprint mismatch")
    confirmation = response["owner_confirmation"]
    if set(confirmation) != {"owner_identity", "confirmed", "role", "principal_identity",
                            "public_key_fingerprint", "statement"}:
        raise SystemExit(f"{role}: owner confirmation fields")
    confirmation_matches = (
        bool(confirmation["owner_identity"])
        and confirmation["confirmed"] is True
        and confirmation["role"] == role
        and confirmation["principal_identity"] == request_item["principal_identity"]
        and confirmation["public_key_fingerprint"] == fingerprint
        and confirmation["statement"]
        == "I bind this public key exclusively to this custodial role and retain the private key outside the repository."
    )
    if not confirmation_matches:
        raise SystemExit(f"{role}: owner confirmation mismatch")
    if response["private_key_included"] is not False:
        raise SystemExit(f"{role}: private_key_included not false")
    public_companion = response_path.with_name(response_path.name.replace(".response.json", ".public.pem"))
    if not public_companion.is_file() or public_companion.read_text(encoding="ascii") != response["public_key"]["value"]:
        raise SystemExit(f"{role}: companion public key disagreement")
    return {
        "role": role, "principal_identity": request_item["principal_identity"],
        "algorithm": algorithm, "public_key": response["public_key"],
        "public_key_fingerprint": fingerprint,
        "challenge_identity": challenge["challenge_identity"],
        "canonical_challenge_sha256": challenge_sha,
        "proof_signature": response["proof_signature"],
        "proof_of_possession": "VERIFIED",
        "owner_confirmation": confirmation,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "companion_public_pem_sha256": hashlib.sha256(public_companion.read_bytes()).hexdigest(),
        "operational_access": False,
    }


def write(path: Path, value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    return hashlib.sha256(body.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    request = git_request()
    by_role = {}
    for path in response_files(args.responses):
        response = json.loads(path.read_text(encoding="utf-8"))
        role = response.get("role")
        if role not in ROLES or role in by_role:
            raise SystemExit(f"unexpected or duplicate role: {role}")
        by_role[role] = (path, response)
    if set(by_role) != set(ROLES):
        raise SystemExit("role set mismatch")
    request_by_role = {item["role"]: item for item in request["requests"]}
    registrations = [verify_response(by_role[role][0], request_by_role[role]) for role in ROLES]
    fingerprints = [item["public_key_fingerprint"] for item in registrations]
    public_values = [item["public_key"]["value"] for item in registrations]
    if len(set(fingerprints)) != 6 or len(set(public_values)) != 6:
        raise SystemExit("duplicate/reused public key across roles")
    core = {
        "enrollment_request_commit": REQUEST_COMMIT, "enrollment_request_identity": REQUEST_ID,
        "runbook_commit": RUNBOOK_COMMIT, "previous_ledger_head": PREVIOUS_LEDGER_HEAD,
        "registrations": registrations,
    }
    core_identity = seal("B2_CUSTODIAL_PUBLIC_KEY_REGISTRATION_CORE_V1", core)
    entries, previous = [], PREVIOUS_LEDGER_HEAD
    for sequence, registration in enumerate(registrations, start=2):
        entry = {
            "schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
            "entry_sequence": sequence, "previous_entry_hash": previous,
            "event": "PUBLIC_KEY_REGISTERED_POP_VERIFIED",
            "registration_core_identity": core_identity, "role": registration["role"],
            "principal_identity": registration["principal_identity"],
            "public_key_fingerprint": registration["public_key_fingerprint"],
            "challenge_identity": registration["challenge_identity"],
            "proof_of_possession": "VERIFIED", "operational_access": False,
        }
        entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry)
        previous = entry["entry_hash"]
        entries.append(entry)
    ledger = {
        "schema_name": "batch2-custodial-public-key-registration-ledger-segment-v1",
        "schema_version": "1.0.0", "previous_ledger_head": PREVIOUS_LEDGER_HEAD,
        "entries": entries, "final_ledger_head": previous,
    }
    ledger["ledger_segment_identity"] = seal("B2_CUSTODIAL_REGISTRATION_LEDGER_SEGMENT_V1", ledger)
    artifact = {
        "schema_name": "batch2-custodial-public-key-registration-v1", "schema_version": "1.0.0",
        "registration_core_identity": core_identity, **core,
        "ledger_segment_identity": ledger["ledger_segment_identity"],
        "access_ledger_identity": previous,
        "registration_status": "REGISTERED_POP_VERIFIED_NONOPERATIONAL",
        "operational_access": False,
        "authority_matrix": {key: False for key in [
            "source_acquisition", "content_ingestion", "archive_write", "content_access",
            "mechanism_assignment", "candidate_construction", "surface_generation",
            "model_exposure", "training", "runtime_integration", "production_routing"]},
    }
    artifact["registration_identity"] = seal("B2_CUSTODIAL_PUBLIC_KEY_REGISTRATION_V1", artifact)
    result = {
        "verdict": "PASS_SIX_PUBLIC_KEYS_REGISTERED_POP_VERIFIED_NONOPERATIONAL",
        "registration_identity": artifact["registration_identity"],
        "access_ledger_identity": previous,
        "bindings": [{"role": item["role"], "fingerprint": item["public_key_fingerprint"],
                      "proof_of_possession": item["proof_of_possession"]} for item in registrations],
    }
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        registration_sha = write(args.output_dir / "humor-mechanics-batch2-custodial-public-key-registration-v1.json", artifact)
        ledger_sha = write(args.output_dir / "humor-mechanics-batch2-custodial-public-key-registration-ledger-v1.json", ledger)
        audit = {
            "schema_name": "batch2-custodial-public-key-registration-v1-audit", "schema_version": "1.0.0",
            **result, "registration_sha256": registration_sha, "ledger_sha256": ledger_sha,
            "duplicate_keys": 0, "private_keys_accessed": 0, "keys_generated": 0,
            "signatures_generated": 0, "operational_access": False,
            "deterministic_defects_remaining": [],
        }
        write(args.output_dir / "humor-mechanics-batch2-custodial-public-key-registration-v1-audit.json", audit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
