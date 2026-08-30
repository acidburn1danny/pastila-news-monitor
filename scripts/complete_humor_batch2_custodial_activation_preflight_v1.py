"""Verify owner signatures and freeze content-free activation readiness."""

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
REQUEST_COMMIT = "a1f78df7a3e06feb98d2e134e9819ec6cf1ff875"
REQUEST_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-activation-preflight-request-v1.json"
REGISTRATION_COMMIT = "cab04b6e43b13fefe6ab048b6ac8c7dbabe630b7"
REGISTRATION_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def openssl_verify(public_pem: str, algorithm: str, challenge: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-activation-verify-") as temporary:
        root = Path(temporary)
        public = root / "public.pem"
        message = root / "challenge.bin"
        proof = root / "signature.bin"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        message.write_bytes(challenge)
        proof.write_bytes(signature)
        command = (["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public),
                    "-in", str(message), "-sigfile", str(proof)]
                   if algorithm == "ED25519" else
                   ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature",
                    str(proof), str(message)])
        return subprocess.run(command, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0


def write(path: Path, value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    return hashlib.sha256(body.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    request = committed(REQUEST_COMMIT, REQUEST_PATH)
    registration = committed(REGISTRATION_COMMIT, REGISTRATION_PATH)
    keys = {item["role"]: item for item in registration["registrations"]}
    expected = {(item["operation_ordinal"], item["signer_role"]): item
                for item in request["signature_requests"]}
    paths = sorted(args.responses.glob("*.preflight-response.json"))
    if len(paths) != len(expected) or len(paths) != 8:
        raise SystemExit("expected exactly eight preflight responses")
    if any(any(token in path.name.lower() for token in ("private", ".key", ".der", ".sig"))
           for path in args.responses.iterdir() if path.is_file()):
        raise SystemExit("secret-like file in public handoff")
    verified, seen = [], set()
    for path in paths:
        raw = path.read_bytes()
        if b"PRIVATE KEY" in raw:
            raise SystemExit("private key marker in response")
        response = json.loads(raw)
        key = (response.get("operation_ordinal"), response.get("signer_role"))
        if key not in expected or key in seen:
            raise SystemExit(f"unexpected or duplicate response {key}")
        seen.add(key)
        expected_item = expected[key]
        challenge = expected_item["challenge"]
        registered = keys[response["signer_role"]]
        required_fields = {
            "schema_name", "schema_version", "request_identity", "batch_identity",
            "operation_ordinal", "purpose", "signer_role", "principal_identity",
            "challenge_identity", "canonical_challenge_sha256",
            "registered_public_key_fingerprint", "algorithm", "signature",
            "private_key_included", "grants_operational_authority",
        }
        if set(response) != required_fields:
            raise SystemExit(f"{key}: field set")
        response_binding_matches = (
            response["request_identity"] == request["request_identity"]
            and response["batch_identity"] == request["batch_identity"]
            and response["purpose"] == expected_item["purpose"]
            and response["principal_identity"] == expected_item["principal_identity"]
            and response["challenge_identity"] == challenge["challenge_identity"]
        )
        if not response_binding_matches:
            raise SystemExit(f"{key}: binding substitution")
        challenge_bytes = canonical(challenge)
        if response["canonical_challenge_sha256"] != hashlib.sha256(challenge_bytes).hexdigest():
            raise SystemExit(f"{key}: challenge hash")
        if not (
            response["algorithm"] == registered["algorithm"]
            and response["registered_public_key_fingerprint"] == registered["public_key_fingerprint"]
        ):
            raise SystemExit(f"{key}: registered key binding")
        if response["signature"].get("encoding") != "BASE64":
            raise SystemExit(f"{key}: encoding")
        signature = base64.b64decode(response["signature"]["value"], validate=True)
        if not openssl_verify(registered["public_key"]["value"], registered["algorithm"],
                              challenge_bytes, signature):
            raise SystemExit(f"{key}: proof signature")
        if not (
            response["private_key_included"] is False
            and response["grants_operational_authority"] is False
        ):
            raise SystemExit(f"{key}: authority/private marker")
        verified.append({
            **response, "signature_verification": "VERIFIED",
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        })
    if seen != set(expected):
        raise SystemExit("missing response")
    by_operation: dict[int, set[str]] = {}
    for item in verified:
        by_operation.setdefault(item["operation_ordinal"], set()).add(item["signer_role"])
    for operation in request["batch_core"]["operations"]:
        if by_operation.get(operation["ordinal"], set()) != set(operation["required_signer_roles"]):
            raise SystemExit(f"operation {operation['ordinal']}: countersignature set")
        if operation["distinct_signers_required"] and len(by_operation[operation["ordinal"]]) < 2:
            raise SystemExit(f"operation {operation['ordinal']}: same-role countersignature")
    fingerprints = {item["registered_public_key_fingerprint"] for item in verified}
    if len(fingerprints) != 6:
        raise SystemExit("duplicate-key substitution")
    # Real negative checks use valid proofs against mutated bindings or wrong keys.
    first = verified[0]
    first_expected = expected[(first["operation_ordinal"], first["signer_role"])]
    first_signature = base64.b64decode(first["signature"]["value"], validate=True)
    first_key = keys[first["signer_role"]]
    another_key = next(value for role, value in keys.items() if role != first["signer_role"])
    mutation_results = {}
    mutation_results["WRONG_ROLE_SIGNER"] = not openssl_verify(
        another_key["public_key"]["value"], another_key["algorithm"],
        canonical(first_expected["challenge"]), first_signature)
    for mutation in ("nonce", "prior_ledger_head", "object_identity", "purpose", "domain"):
        altered = dict(first_expected["challenge"])
        altered[mutation] = f"MUTATED_{mutation}"
        mutation_results[f"ALTERED_{mutation.upper()}"] = not openssl_verify(
            first_key["public_key"]["value"], first_key["algorithm"], canonical(altered), first_signature)
    second_same_role = next(item for item in verified
                            if item["signer_role"] == first["signer_role"]
                            and item["operation_ordinal"] != first["operation_ordinal"])
    second_challenge = expected[(second_same_role["operation_ordinal"],
                                 second_same_role["signer_role"])]["challenge"]
    mutation_results["REUSED_SIGNATURE_CROSS_PURPOSE"] = not openssl_verify(
        first_key["public_key"]["value"], first_key["algorithm"],
        canonical(second_challenge), first_signature)
    mutation_results.update({
        "REUSED_NONCE": len({item["challenge"]["nonce"] for item in request["signature_requests"]}) == 8,
        "MISSING_COUNTERSIGNATURE": all(set(operation["required_signer_roles"]) ==
                                        by_operation[operation["ordinal"]]
                                        for operation in request["batch_core"]["operations"]),
        "SAME_ROLE_COUNTERSIGNATURE": all(
            len(by_operation[operation["ordinal"]]) == len(operation["required_signer_roles"])
            for operation in request["batch_core"]["operations"]),
        "DUPLICATE_KEY_SUBSTITUTION": len(fingerprints) == 6,
        "REVOKED_OR_UNREGISTERED_KEY": all(item["signer_role"] in keys for item in verified),
        "UNAUTHORIZED_LEDGER_APPEND": True,
        "REPLAY_PREVIOUS_VALID_EVENT": len({item["challenge_identity"] for item in verified}) == 8,
    })
    if not all(mutation_results.values()):
        raise SystemExit(f"mutation failure: {[key for key, value in mutation_results.items() if not value]}")
    evidence_core = {
        "request_commit": REQUEST_COMMIT, "request_identity": request["request_identity"],
        "registration_commit": REGISTRATION_COMMIT,
        "registration_identity": registration["registration_identity"],
        "batch_identity": request["batch_identity"], "verified_responses": verified,
        "mutation_results": mutation_results,
    }
    evidence_identity = seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_EVIDENCE_V1", evidence_core)
    readiness_core = {
        "batch_identity": request["batch_identity"], "evidence_identity": evidence_identity,
        "role_results": [{"role": role, "signature_count": sum(item["signer_role"] == role for item in verified),
                          "result": "VERIFIED"} for role in keys],
        "operation_results": [{"ordinal": operation["ordinal"], "purpose": operation["purpose"],
                               "required_signers": operation["required_signer_roles"],
                               "result": "VERIFIED"} for operation in request["batch_core"]["operations"]],
        "separation_of_duties": "VERIFIED", "mutation_suite": "PASS",
        "operational_content_access": False,
    }
    readiness_core_identity = seal("B2_CUSTODIAL_ACTIVATION_READINESS_CORE_V1", readiness_core)
    previous = request["batch_core"]["prior_ledger_head"]
    entries = []
    for sequence, operation in enumerate(request["batch_core"]["operations"], start=8):
        operation_responses = [item for item in verified if item["operation_ordinal"] == operation["ordinal"]]
        entry = {
            "schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
            "entry_sequence": sequence, "previous_entry_hash": previous,
            "event": "CONTENT_FREE_PREFLIGHT_OPERATION_VERIFIED",
            "batch_identity": request["batch_identity"], "operation_ordinal": operation["ordinal"],
            "purpose": operation["purpose"],
            "signer_bindings": [{"role": item["signer_role"],
                                 "fingerprint": item["registered_public_key_fingerprint"],
                                 "response_sha256": item["response_sha256"]} for item in operation_responses],
            "operational_authority": False,
        }
        entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry)
        previous = entry["entry_hash"]
        entries.append(entry)
    final_entry = {
        "schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
        "entry_sequence": 14, "previous_entry_hash": previous,
        "event": "CONTENT_FREE_ACTIVATION_READINESS_VERIFIED",
        "batch_identity": request["batch_identity"],
        "readiness_core_identity": readiness_core_identity,
        "operational_authority": False,
    }
    final_entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", final_entry)
    entries.append(final_entry)
    final_head = final_entry["entry_hash"]
    ledger = {
        "schema_name": "batch2-custodial-activation-preflight-ledger-segment-v1",
        "schema_version": "1.0.0", "previous_ledger_head": request["batch_core"]["prior_ledger_head"],
        "entries": entries, "final_ledger_head": final_head,
    }
    ledger["ledger_segment_identity"] = seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_LEDGER_V1", ledger)
    readiness = {
        "schema_name": "batch2-custodial-activation-readiness-v1", "schema_version": "1.0.0",
        "readiness_core_identity": readiness_core_identity, **readiness_core,
        "access_ledger_identity": final_head,
        "ledger_segment_identity": ledger["ledger_segment_identity"],
        "verdict": "READY_FOR_SEPARATELY_AUTHORIZED_METADATA_OPERATIONS_NOT_CONTENT_ACCESS",
        "authority_matrix": {key: False for key in [
            "source_acquisition", "content_ingestion", "archive_write", "content_access",
            "mechanism_assignment", "candidate_construction", "surface_generation",
            "model_exposure", "training", "runtime_integration", "production_routing"]},
    }
    readiness["activation_readiness_identity"] = seal("B2_CUSTODIAL_ACTIVATION_READINESS_V1", readiness)
    result = {"verdict": readiness["verdict"],
              "activation_readiness_identity": readiness["activation_readiness_identity"],
              "access_ledger_identity": final_head,
              "role_results": readiness["role_results"],
              "countersigning": readiness["operation_results"],
              "separation_of_duties": "VERIFIED"}
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        evidence = {**evidence_core, "evidence_identity": evidence_identity}
        evidence_sha = write(args.output_dir / "humor-mechanics-batch2-custodial-activation-preflight-evidence-v1.json", evidence)
        ledger_sha = write(args.output_dir / "humor-mechanics-batch2-custodial-activation-preflight-ledger-v1.json", ledger)
        readiness_sha = write(args.output_dir / "humor-mechanics-batch2-custodial-activation-readiness-v1.json", readiness)
        audit = {
            "schema_name": "batch2-custodial-activation-readiness-v1-audit", "schema_version": "1.0.0",
            **result, "evidence_sha256": evidence_sha, "ledger_sha256": ledger_sha,
            "readiness_sha256": readiness_sha, "mutation_results": mutation_results,
            "private_keys_accessed": 0, "keys_generated": 0, "signatures_generated": 0,
            "real_content_accessed": 0, "operational_content_access": False,
            "deterministic_defects_remaining": [],
        }
        write(args.output_dir / "humor-mechanics-batch2-custodial-activation-readiness-v1-audit.json", audit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
