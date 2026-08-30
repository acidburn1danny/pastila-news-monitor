"""Verify all Pilot 03 custodial proofs and atomically materialize ingestion."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE_COMMIT = "1822e55e057fc7b1b0b7399df6475f6d27559804"
PRE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-preingestion-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-signing-packet-v1.json"
REG_COMMIT = "cab04b6e43b13fefe6ab048b6ac8c7dbabe630b7"
REG_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
PRIOR_LEDGER_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/access-ledger-segment.json"
SOURCE = ROOT / "owner-source-pilot03-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot03-v1.json"
DESTINATION = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1"
SOURCE_SHA = "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30"
DECLARATION_SHA = "5915ee71841ed1a40ae375e0e7c6a4b611c525d0b8690464e61d66e078b14d8d"
PACKET_ID = "5ce4ddc234cdbfc63088c2e4d5059e84b9fc519f6231f7be3cb9ac711e877ba3"
HANDOFF = Path.home() / "Pastila-Owner-Handoff" / "Batch2-Development-Pilot03-v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed(commit: str, path: str) -> Any:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def verify_signature(public_pem: str, algorithm: str, message: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot03-verify-") as temp:
        folder = Path(temp)
        public, body, proof = folder / "public.pem", folder / "message.bin", folder / "signature.bin"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        body.write_bytes(message)
        proof.write_bytes(signature)
        command = (
            ["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public), "-in", str(body), "-sigfile", str(proof)]
            if algorithm == "ED25519"
            else ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature", str(proof), str(body)]
        )
        return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def spki_fingerprint(public_pem: str) -> str:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot03-spki-") as temp:
        public = Path(temp) / "public.pem"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        der = subprocess.check_output(
            ["openssl", "pkey", "-pubin", "-in", str(public), "-outform", "DER"],
            stderr=subprocess.DEVNULL,
        )
        return sha(der)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def verify(responses: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != FREEZE_COMMIT:
        raise SystemExit("HEAD differs from frozen pre-ingestion commit")
    pre, packet = committed(FREEZE_COMMIT, PRE_PATH), committed(FREEZE_COMMIT, PACKET_PATH)
    registration = committed(REG_COMMIT, REG_PATH)
    prior_ledger = committed(FREEZE_COMMIT, PRIOR_LEDGER_PATH)
    if prior_ledger["final_ledger_head"] != packet["packet_core"]["prior_ledger_head"]:
        raise SystemExit("stale prior ledger head")
    if packet["packet_identity"] != PACKET_ID:
        raise SystemExit("packet identity")
    if packet["packet_identity"] != seal("B2_DEVELOPMENT_PILOT03_SIGNING_PACKET_V1", packet["packet_core"]):
        raise SystemExit("packet seal")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    if sha(source) != SOURCE_SHA or sha(declaration) != DECLARATION_SHA:
        raise SystemExit("owner input hash mismatch")
    if source.startswith(b"\xef\xbb\xbf") or b"\r" in source or not source.endswith(b"\n") or source.endswith(b"\n\n"):
        raise SystemExit("source encoding/line ending mismatch")
    expected = {(x["operation_ordinal"], x["role"]): x for x in packet["signature_requests"]}
    paths = sorted(responses.glob("*.pilot03-response.json"))
    if len(paths) != 8 or len(expected) != 8:
        raise SystemExit("exactly 8/8 responses required")
    if any(any(token in p.name.lower() for token in ("private", ".key", ".der", ".sig")) for p in responses.iterdir() if p.is_file()):
        raise SystemExit("secret-like material in public handoff")
    keys = {x["role"]: x for x in registration["registrations"]}
    verified: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    fields = {"schema_name", "schema_version", "packet_identity", "operation_ordinal", "purpose",
              "signer_role", "principal_identity", "challenge_identity", "canonical_challenge_sha256",
              "registered_public_key_fingerprint", "algorithm", "signature", "private_key_included",
              "grants_operational_authority"}
    for path in paths:
        raw = path.read_bytes()
        if b"PRIVATE KEY" in raw:
            raise SystemExit("private key marker in response")
        response = json.loads(raw)
        key = (response.get("operation_ordinal"), response.get("signer_role"))
        if set(response) != fields or key not in expected or key in seen:
            raise SystemExit(f"response fields/duplicate/unexpected: {key}")
        seen.add(key)
        request, registered = expected[key], keys[response["signer_role"]]
        challenge = request["challenge"]
        core = dict(challenge)
        identity = core.pop("challenge_identity")
        if seal("B2_PILOT03_SIGNING_CHALLENGE_V1", core) != identity:
            raise SystemExit(f"challenge seal: {key}")
        operation = packet["packet_core"]["operations"][request["operation_ordinal"]]
        if not (
            response["packet_identity"] == packet["packet_identity"]
            and response["purpose"] == request["purpose"] == challenge["purpose"]
            and response["principal_identity"] == challenge["principal_identity"] == registered["principal_identity"]
            and response["challenge_identity"] == challenge["challenge_identity"]
            and challenge["role"] == response["signer_role"]
            and challenge["domain"] == "PASTILA_BATCH2_DEVELOPMENT_PILOT03_PREINGESTION_V1"
            and challenge["object_identity"] == operation["object_identity"]
            and challenge["prior_ledger_head"] == prior_ledger["final_ledger_head"]
            and challenge["preingestion_identity"] == pre["preingestion_identity"]
            and challenge["source_sha256"] == SOURCE_SHA
            and challenge["declaration_sha256"] == DECLARATION_SHA
            and challenge["grants_operational_content_access"] is False
        ):
            raise SystemExit(f"challenge binding: {key}")
        message = canonical(challenge)
        if response["canonical_challenge_sha256"] != sha(message):
            raise SystemExit(f"canonical challenge hash: {key}")
        if response["algorithm"] != registered["algorithm"] or response["algorithm"] not in {"ED25519", "ECDSA_P256_SHA256"}:
            raise SystemExit(f"algorithm: {key}")
        if response["registered_public_key_fingerprint"] != registered["public_key_fingerprint"]:
            raise SystemExit(f"fingerprint: {key}")
        if spki_fingerprint(registered["public_key"]["value"]) != registered["public_key_fingerprint"]:
            raise SystemExit(f"independent SPKI fingerprint: {key}")
        if response["private_key_included"] is not False or response["grants_operational_authority"] is not False:
            raise SystemExit(f"private/authority marker: {key}")
        if response["signature"].get("encoding") != "BASE64":
            raise SystemExit(f"signature encoding: {key}")
        signature = base64.b64decode(response["signature"]["value"], validate=True)
        if not verify_signature(registered["public_key"]["value"], registered["algorithm"], message, signature):
            raise SystemExit(f"invalid signature: {key}")
        verified.append({"operation_ordinal": key[0], "purpose": response["purpose"], "role": key[1],
                         "principal_identity": response["principal_identity"],
                         "public_key_fingerprint": response["registered_public_key_fingerprint"],
                         "challenge_identity": response["challenge_identity"], "nonce": challenge["nonce"],
                         "response_sha256": sha(raw), "signature_verification": "PASS"})
    if seen != set(expected) or len({x["nonce"] for x in verified}) != 8 or len({x["challenge_identity"] for x in verified}) != 8:
        raise SystemExit("missing, duplicate, replayed, or reused proof")
    by_op: dict[int, set[str]] = {}
    for item in verified:
        by_op.setdefault(item["operation_ordinal"], set()).add(item["role"])
    for operation in packet["packet_core"]["operations"]:
        if by_op.get(operation["ordinal"]) != set(operation["required_signer_roles"]):
            raise SystemExit(f"countersignature set: {operation['ordinal']}")
        if operation["distinct_signers_required"] and len(by_op[operation["ordinal"]]) != len(operation["required_signer_roles"]):
            raise SystemExit(f"separation of duties: {operation['ordinal']}")
    if len({keys[x["role"]]["public_key_fingerprint"] for x in verified}) != 5:
        raise SystemExit("role-key separation mismatch")
    tracked = subprocess.check_output(["git", "grep", "-l", packet["packet_identity"], "HEAD", "--", "docs/artifacts"], cwd=ROOT, text=True).splitlines()
    allowed = {f"HEAD:{PACKET_PATH}", f"HEAD:{PRE_PATH}"}
    if any(x not in allowed for x in tracked):
        raise SystemExit("packet already consumed/replayed")
    return pre, packet, sorted(verified, key=lambda x: (x["operation_ordinal"], x["role"])), prior_ledger


def materialize(pre: dict[str, Any], packet: dict[str, Any], verified: list[dict[str, Any]], prior_ledger: dict[str, Any]) -> dict[str, Any]:
    if DESTINATION.exists():
        raise SystemExit("ingestion destination already exists; refusing replay")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    response_set_identity = seal("B2_DEVELOPMENT_PILOT03_VERIFIED_RESPONSE_SET_V1", verified)
    previous = prior_ledger["final_ledger_head"]
    entries = []
    for sequence, operation in enumerate(packet["packet_core"]["operations"], start=29):
        signers = [x for x in verified if x["operation_ordinal"] == operation["ordinal"]]
        entry = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
                 "entry_sequence": sequence, "previous_entry_hash": previous,
                 "event": "DEVELOPMENT_PILOT03_ATOMIC_INGESTION_OPERATION_ADMITTED",
                 "packet_identity": packet["packet_identity"], "operation_ordinal": operation["ordinal"],
                 "purpose": operation["purpose"], "object_identity": operation["object_identity"],
                 "signer_bindings": signers, "partition": "DEVELOPMENT",
                 "creative_premise_family_id": "UNASSIGNED", "operational_content_access": False}
        entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry)
        previous = entry["entry_hash"]
        entries.append(entry)
    completion = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
                  "entry_sequence": 35, "previous_entry_hash": previous,
                  "event": "DEVELOPMENT_PILOT03_ATOMIC_INGESTION_COMPLETED",
                  "packet_identity": packet["packet_identity"], "source_package_identity": pre["source_package_identity"],
                  "partition_identity": pre["prospective_partition_identity"], "response_set_identity": response_set_identity,
                  "operational_content_access": False}
    completion["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", completion)
    entries.append(completion)
    ledger = {"schema_name": "batch2-development-pilot03-access-ledger-segment-v1", "schema_version": "1.0.0",
              "previous_ledger_head": prior_ledger["final_ledger_head"], "entries": entries,
              "final_ledger_head": completion["entry_hash"]}
    ledger["ledger_segment_identity"] = seal("B2_DEVELOPMENT_PILOT03_ACCESS_LEDGER_SEGMENT_V1", ledger)
    source_package = {"schema_name": "batch2-owned-authority-source-package-materialization-v1", "schema_version": "1.0.0",
                      "source_package_identity": pre["source_package_identity"], "source_commitment": pre["source_commitment"],
                      "immutable_archive_commitment": pre["immutable_archive_commitment"],
                      "rights_instrument_identity": pre["rights_instrument_identity"],
                      "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"],
                      "source_sha256": SOURCE_SHA, "source_byte_length": len(source), "encoding": "UTF-8",
                      "prospective_git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
                      "family_identities": pre["family_identities"], "partition": "DEVELOPMENT",
                      "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
                      "access_ledger_identity": ledger["final_ledger_head"], "materialization_status": "INGESTED_IMMUTABLE"}
    archive_receipt = {"schema_name": "batch2-development-pilot03-immutable-archive-receipt-v1", "schema_version": "1.0.0",
                       "immutable_archive_commitment": pre["immutable_archive_commitment"],
                       "original_bytes_sha256": SOURCE_SHA, "readback_sha256": SOURCE_SHA,
                       "byte_length": len(source), "git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
                       "capture_time": json.loads(declaration)["source"]["capture_timestamp"],
                       "writer_authority": "ATOMIC_CUSTODIAL_PACKET_8_OF_8", "rights_instrument_identity": pre["rights_instrument_identity"],
                       "previous_ledger_head": prior_ledger["final_ledger_head"]}
    archive_receipt["archive_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT03_ARCHIVE_RECEIPT_V1", archive_receipt)
    evidence = {"schema_name": "batch2-development-pilot03-custodial-verification-v1", "schema_version": "1.0.0",
                "packet_identity": packet["packet_identity"], "verification_result": "PASS_8_OF_8",
                "verified_responses": verified, "response_set_identity": response_set_identity,
                "countersignatures": "PASS", "separation_of_duties": "PASS", "replay_check": "PASS",
                "packet_consumed": True, "nonces_consumed": [x["nonce"] for x in verified]}
    evidence["verification_identity"] = seal("B2_DEVELOPMENT_PILOT03_CUSTODIAL_VERIFICATION_V1", evidence)
    receipt = {"schema_name": "batch2-development-pilot03-ingestion-receipt-v1", "schema_version": "1.0.0",
               "terminal_verdict": "ATOMIC_IMMUTABLE_INGESTION_PASS", "freeze_commit": FREEZE_COMMIT,
               "preingestion_identity": pre["preingestion_identity"], "packet_identity": packet["packet_identity"],
               "source_commitment": pre["source_commitment"], "rights_instrument_identity": pre["rights_instrument_identity"],
               "immutable_archive_commitment": pre["immutable_archive_commitment"], "source_package_identity": pre["source_package_identity"],
               "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"],
               "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
               "verification_identity": evidence["verification_identity"], "archive_receipt_identity": archive_receipt["archive_receipt_identity"],
               "access_ledger_identity": ledger["final_ledger_head"], "ledger_segment_identity": ledger["ledger_segment_identity"],
               "authority_matrix": {"mechanism_assignment": False, "operational_obligation_assignment": False,
                                    "creative_premise_assignment": False, "humor_construction": False,
                                    "candidate_generation": False, "model_exposure": False, "training": False,
                                    "runtime_integration": False, "production_routing": False}}
    receipt["ingestion_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT03_INGESTION_RECEIPT_V1", receipt)
    temporary = Path(tempfile.mkdtemp(prefix=".pilot03-ingestion-", dir=DESTINATION.parent))
    try:
        (temporary / "source.utf8.txt").write_bytes(source)
        (temporary / "rights-instrument.json").write_bytes(declaration)
        write_json(temporary / "factual-authority-envelope.json", pre["factual_authority_envelope"])
        write_json(temporary / "source-package.json", source_package)
        write_json(temporary / "archive-receipt.json", archive_receipt)
        write_json(temporary / "custodial-verification.json", evidence)
        write_json(temporary / "access-ledger-segment.json", ledger)
        write_json(temporary / "ingestion-receipt.json", receipt)
        if sha((temporary / "source.utf8.txt").read_bytes()) != SOURCE_SHA or sha((temporary / "rights-instrument.json").read_bytes()) != DECLARATION_SHA:
            raise SystemExit("atomic staging readback mismatch")
        os.replace(temporary, DESTINATION)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, default=HANDOFF)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    pre, packet, verified, prior = verify(args.responses)
    if args.verify_only:
        print(json.dumps({"verdict": "PASS_8_OF_8_NO_INGESTION", "packet_identity": packet["packet_identity"],
                          "verified": len(verified), "ingested": False}, sort_keys=True))
        return
    receipt = materialize(pre, packet, verified, prior)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
