"""Verify Pilot 10 custodial proofs and atomically materialize ingestion."""

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
FREEZE_COMMIT = "902a06567e60e76d0a31a5d6bd706fec53277f95"
HELPER_COMMIT = "346a4e5caf140db1be2909a72ad1687b552622c4"
PRE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-preingestion-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-signing-packet-v1.json"
REG_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
PRIOR_LEDGER_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/access-ledger-segment.json"
SOURCE = ROOT / "owner-source-pilot10-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot10-v1.json"
DESTINATION = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-ingestion-v1"
SOURCE_SHA = "454a0c568c12a46224407f6c3b378f8197e3f4653cca6d897d1c03b8d94821d7"
DECLARATION_SHA = "4bc43e0b03964d50685fe2e5193fafcbfee2c14cd35ebe777fdba64c15540435"
PACKET_ID = "19a74d1147f3b1173e1ca07d8a2a852407920fdbe28e1ab75b5bf7580bab6fb5"
HANDOFF = Path.home() / "Pastila-Owner-Handoff" / "Batch2-Development-Pilot10-v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed(commit: str, path: str) -> Any:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def verify_signature(public_pem: str, algorithm: str, message: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot10-verify-") as temp:
        folder = Path(temp)
        public, body, proof = folder / "public.pem", folder / "message.bin", folder / "signature.bin"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        body.write_bytes(message); proof.write_bytes(signature)
        command = (["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public), "-in", str(body), "-sigfile", str(proof)]
                   if algorithm == "ED25519" else
                   ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature", str(proof), str(body)])
        return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def spki_fingerprint(public_pem: str) -> str:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot10-spki-") as temp:
        public = Path(temp) / "public.pem"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        der = subprocess.check_output(["openssl", "pkey", "-pubin", "-in", str(public), "-outform", "DER"], stderr=subprocess.DEVNULL)
        return sha(der)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def verify(responses: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != HELPER_COMMIT:
        raise SystemExit("HEAD differs from authorized Pilot 10 helper commit")
    pre, packet = committed(FREEZE_COMMIT, PRE_PATH), committed(FREEZE_COMMIT, PACKET_PATH)
    registration, prior = committed(HELPER_COMMIT, REG_PATH), committed(HELPER_COMMIT, PRIOR_LEDGER_PATH)
    if prior["final_ledger_head"] != packet["packet_core"]["prior_ledger_head"]:
        raise SystemExit("stale prior ledger head")
    if packet["packet_identity"] != PACKET_ID or seal("B2_DEVELOPMENT_PILOT10_SIGNING_PACKET_V1", packet["packet_core"]) != PACKET_ID:
        raise SystemExit("packet identity/seal")
    if any((packet["proposition_sufficiency_evaluated"], packet["constructor_source_compatibility_or_release_performed"],
            packet["realization_candidate_emission_or_preemission_conformance_performed"], packet["fragment_collision_evaluation_performed"])):
        raise SystemExit("downstream authority boundary")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    if sha(source) != SOURCE_SHA or sha(declaration) != DECLARATION_SHA:
        raise SystemExit("owner input hash mismatch")
    if len(pre["factual_authority_envelope"]["propositions"]) != 7:
        raise SystemExit("proposition-binding count")
    expected = {(item["operation_ordinal"], item["role"]): item for item in packet["signature_requests"]}
    paths = sorted(responses.glob("*.pilot10-response.json"))
    if len(paths) != 8 or len(expected) != 8:
        raise SystemExit("exactly 8/8 responses required")
    if any(any(token in path.name.lower() for token in ("private", ".key", ".der", ".sig")) for path in responses.iterdir() if path.is_file()):
        raise SystemExit("secret-like material in public handoff")
    keys = {item["role"]: item for item in registration["registrations"]}
    fields = {"schema_name", "schema_version", "packet_identity", "operation_ordinal", "purpose", "signer_role",
              "principal_identity", "challenge_identity", "canonical_challenge_sha256", "registered_public_key_fingerprint",
              "algorithm", "signature", "private_key_included", "grants_operational_authority"}
    verified, seen = [], set()
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
        challenge_core = dict(challenge); challenge_identity = challenge_core.pop("challenge_identity")
        if seal("B2_PILOT10_SIGNING_CHALLENGE_V1", challenge_core) != challenge_identity:
            raise SystemExit(f"challenge seal: {key}")
        operation = packet["packet_core"]["operations"][request["operation_ordinal"]]
        if not (response["packet_identity"] == PACKET_ID and response["purpose"] == request["purpose"] == challenge["purpose"]
                and response["principal_identity"] == challenge["principal_identity"] == registered["principal_identity"]
                and response["challenge_identity"] == challenge_identity and challenge["role"] == response["signer_role"]
                and challenge["domain"] == "PASTILA_BATCH2_DEVELOPMENT_PILOT10_PREINGESTION_V1"
                and challenge["object_identity"] == operation["object_identity"]
                and challenge["prior_ledger_head"] == prior["final_ledger_head"]
                and challenge["preingestion_identity"] == pre["preingestion_identity"]
                and challenge["source_sha256"] == SOURCE_SHA and challenge["declaration_sha256"] == DECLARATION_SHA
                and challenge["grants_operational_content_access"] is False):
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
        signature = base64.b64decode(response["signature"]["value"], validate=True)
        if response["signature"].get("encoding") != "BASE64" or not verify_signature(registered["public_key"]["value"], registered["algorithm"], message, signature):
            raise SystemExit(f"invalid signature: {key}")
        verified.append({"operation_ordinal": key[0], "purpose": response["purpose"], "role": key[1],
            "principal_identity": response["principal_identity"], "public_key_fingerprint": response["registered_public_key_fingerprint"],
            "challenge_identity": response["challenge_identity"], "nonce": challenge["nonce"],
            "response_sha256": sha(raw), "signature_verification": "PASS"})
    if seen != set(expected) or len({item["nonce"] for item in verified}) != 8 or len({item["challenge_identity"] for item in verified}) != 8:
        raise SystemExit("missing, duplicate, replayed, or reused proof")
    for operation in packet["packet_core"]["operations"]:
        actual = {item["role"] for item in verified if item["operation_ordinal"] == operation["ordinal"]}
        if actual != set(operation["required_signer_roles"]):
            raise SystemExit(f"countersignature set: {operation['ordinal']}")
    tracked = subprocess.check_output(["git", "grep", "-l", PACKET_ID, "HEAD", "--", "docs/artifacts"], cwd=ROOT, text=True).splitlines()
    if any(item not in {f"HEAD:{PACKET_PATH}", f"HEAD:{PRE_PATH}"} for item in tracked):
        raise SystemExit("packet already consumed/replayed")
    return pre, packet, sorted(verified, key=lambda item: (item["operation_ordinal"], item["role"])), prior


def materialize(pre: dict[str, Any], packet: dict[str, Any], verified: list[dict[str, Any]], prior: dict[str, Any]) -> dict[str, Any]:
    if DESTINATION.exists():
        raise SystemExit("ingestion destination already exists; refusing replay")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    response_set = seal("B2_DEVELOPMENT_PILOT10_VERIFIED_RESPONSE_SET_V1", verified)
    previous, entries = prior["final_ledger_head"], []
    for sequence, operation in enumerate(packet["packet_core"]["operations"], start=78):
        entry = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
            "entry_sequence": sequence, "previous_entry_hash": previous,
            "event": "DEVELOPMENT_PILOT10_ATOMIC_INGESTION_OPERATION_ADMITTED", "packet_identity": PACKET_ID,
            "operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "object_identity": operation["object_identity"],
            "signer_bindings": [item for item in verified if item["operation_ordinal"] == operation["ordinal"]],
            "partition": "DEVELOPMENT", "creative_premise_family_id": "UNASSIGNED", "operational_content_access": False}
        entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry)
        previous = entry["entry_hash"]; entries.append(entry)
    completion = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
        "entry_sequence": 84, "previous_entry_hash": previous, "event": "DEVELOPMENT_PILOT10_ATOMIC_INGESTION_COMPLETED",
        "packet_identity": PACKET_ID, "source_package_identity": pre["source_package_identity"],
        "partition_identity": pre["prospective_partition_identity"], "response_set_identity": response_set,
        "operational_content_access": False}
    completion["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", completion); entries.append(completion)
    ledger = {"schema_name": "batch2-development-pilot10-access-ledger-segment-v1", "schema_version": "1.0.0",
        "previous_ledger_head": prior["final_ledger_head"], "entries": entries, "final_ledger_head": completion["entry_hash"]}
    ledger["ledger_segment_identity"] = seal("B2_DEVELOPMENT_PILOT10_ACCESS_LEDGER_SEGMENT_V1", ledger)
    package = {"schema_name": "batch2-owned-authority-source-package-materialization-v1", "schema_version": "1.0.0",
        "source_package_identity": pre["source_package_identity"], "source_commitment": pre["source_commitment"],
        "immutable_archive_commitment": pre["immutable_archive_commitment"], "rights_instrument_identity": pre["rights_instrument_identity"],
        "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"], "source_sha256": SOURCE_SHA,
        "source_byte_length": len(source), "encoding": "UTF-8", "prospective_git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
        "family_identities": pre["family_identities"], "partition": "DEVELOPMENT",
        "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
        "access_ledger_identity": ledger["final_ledger_head"], "materialization_status": "INGESTED_IMMUTABLE"}
    archive = {"schema_name": "batch2-development-pilot10-immutable-archive-receipt-v1", "schema_version": "1.0.0",
        "immutable_archive_commitment": pre["immutable_archive_commitment"], "original_bytes_sha256": SOURCE_SHA,
        "readback_sha256": SOURCE_SHA, "byte_length": len(source), "git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
        "capture_time": json.loads(declaration)["source"]["capture_timestamp"], "writer_authority": "ATOMIC_CUSTODIAL_PACKET_8_OF_8",
        "rights_instrument_identity": pre["rights_instrument_identity"], "previous_ledger_head": prior["final_ledger_head"]}
    archive["archive_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT10_ARCHIVE_RECEIPT_V1", archive)
    evidence = {"schema_name": "batch2-development-pilot10-custodial-verification-v1", "schema_version": "1.0.0",
        "packet_identity": PACKET_ID, "verification_result": "PASS_8_OF_8", "verified_responses": verified,
        "response_set_identity": response_set, "countersignatures": "PASS", "separation_of_duties": "PASS",
        "replay_check": "PASS", "packet_consumed": True, "nonces_consumed": [item["nonce"] for item in verified]}
    evidence["verification_identity"] = seal("B2_DEVELOPMENT_PILOT10_CUSTODIAL_VERIFICATION_V1", evidence)
    receipt = {"schema_name": "batch2-development-pilot10-ingestion-receipt-v1", "schema_version": "1.0.0",
        "terminal_verdict": "ATOMIC_IMMUTABLE_INGESTION_PASS", "freeze_commit": FREEZE_COMMIT,
        "preingestion_identity": pre["preingestion_identity"], "packet_identity": PACKET_ID,
        "source_commitment": pre["source_commitment"], "rights_instrument_identity": pre["rights_instrument_identity"],
        "immutable_archive_commitment": pre["immutable_archive_commitment"], "source_package_identity": pre["source_package_identity"],
        "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"],
        "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
        "proposition_bindings": "PASS_7", "proposition_sufficiency_evaluated": False,
        "constructor_v5_2_compatibility_evaluated": False, "verification_identity": evidence["verification_identity"],
        "archive_receipt_identity": archive["archive_receipt_identity"], "access_ledger_identity": ledger["final_ledger_head"],
        "ledger_segment_identity": ledger["ledger_segment_identity"],
        "authority_matrix": {key: False for key in ("g01_admission", "proposition_sufficiency_evaluation", "assignment",
            "constructor_source_compatibility_evaluation", "constructor_release", "constructor_invocation", "realization",
            "candidate_emission", "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c",
            "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    receipt["ingestion_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT10_INGESTION_RECEIPT_V1", receipt)
    temporary = Path(tempfile.mkdtemp(prefix=".pilot10-ingestion-", dir=DESTINATION.parent))
    try:
        (temporary / "source.utf8.txt").write_bytes(source)
        (temporary / "rights-instrument.json").write_bytes(declaration)
        for name, value in (("factual-authority-envelope.json", pre["factual_authority_envelope"]),
                            ("source-package.json", package), ("archive-receipt.json", archive),
                            ("custodial-verification.json", evidence), ("access-ledger-segment.json", ledger),
                            ("ingestion-receipt.json", receipt)):
            write_json(temporary / name, value)
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
        print(json.dumps({"verdict": "PASS_8_OF_8_NO_INGESTION", "packet_identity": PACKET_ID,
                          "verified": len(verified), "ingested": False}, sort_keys=True))
        return
    print(json.dumps(materialize(pre, packet, verified, prior), sort_keys=True))


if __name__ == "__main__":
    main()
