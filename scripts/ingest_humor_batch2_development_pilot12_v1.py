"""Independently verify Pilot 12 proofs and atomically materialize ingestion."""

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
PREPARATION_COMMIT = "ee10e4b8714881b0eebe2f4bbcc29b7a8da83d73"
HELPER_COMMIT = "93fcc19dd20503c271872cbffd3961a2a90ea8ea"
PRE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-preingestion-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-signing-packet-v1.json"
REG_PATH = "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json"
PRIOR_LEDGER_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-ingestion-v1/access-ledger-segment.json"
SOURCE = ROOT / "owner-source-pilot12-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot12-v1.json"
DESTINATION = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-ingestion-v1"
HANDOFF = Path.home() / "Pastila-Owner-Handoff" / "Batch2-Development-Pilot12-v1"
SOURCE_SHA = "8b87cef6b320d45d7594bc48919bae63442f51f1f7937b599575d435df69ea27"
DECLARATION_SHA = "94f573e8aa1bb1789117ebef856da896447ddcfd944f195e17267e7bdf456ab3"
PACKET_ID = "5f9c0689ae8a92c9da648f5f6ea45fafc66fb2a340578f1996d03d4938782e6b"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed(commit: str, path: str) -> Any:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def verify_signature(public_pem: str, algorithm: str, message: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot12-verify-") as temp:
        folder = Path(temp)
        public, body, proof = folder / "public.pem", folder / "message.bin", folder / "signature.bin"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        body.write_bytes(message)
        proof.write_bytes(signature)
        if algorithm == "ED25519":
            command = ["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public),
                       "-in", str(body), "-sigfile", str(proof)]
        elif algorithm == "ECDSA_P256_SHA256":
            command = ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature", str(proof), str(body)]
        else:
            return False
        return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def spki_fingerprint(public_pem: str) -> str:
    with tempfile.TemporaryDirectory(prefix="pastila-b2-pilot12-spki-") as temp:
        public = Path(temp) / "public.pem"
        public.write_text(public_pem, encoding="ascii", newline="\n")
        der = subprocess.check_output(
            ["openssl", "pkey", "-pubin", "-in", str(public), "-outform", "DER"],
            stderr=subprocess.DEVNULL,
        )
        return sha(der)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def verify(responses: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != HELPER_COMMIT:
        raise SystemExit("HEAD differs from authorized Pilot 12 signing-helper commit")
    pre = committed(PREPARATION_COMMIT, PRE_PATH)
    packet = committed(PREPARATION_COMMIT, PACKET_PATH)
    registration = committed(HELPER_COMMIT, REG_PATH)
    prior = committed(HELPER_COMMIT, PRIOR_LEDGER_PATH)
    if prior["final_ledger_head"] != packet["packet_core"]["prior_ledger_head"]:
        raise SystemExit("stale prior ledger head")
    if packet["packet_identity"] != PACKET_ID:
        raise SystemExit("packet identity mismatch")
    if seal("B2_DEVELOPMENT_PILOT12_SIGNING_PACKET_V1", packet["packet_core"]) != PACKET_ID:
        raise SystemExit("packet seal mismatch")
    boundary_flags = (
        packet["proposition_sufficiency_evaluated"],
        packet["constructor_semantic_plan_release_or_invocation_performed"],
        packet["realization_candidate_emission_coordinate_conformance_or_semantic_edge_validation_performed"],
        packet["fragment_collision_evaluation_performed"], packet["source_ingested"], packet["archive_written"],
    )
    if any(boundary_flags) or packet["ledger_events_appended"] != 0:
        raise SystemExit("downstream authority boundary")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    if sha(source) != SOURCE_SHA or sha(declaration) != DECLARATION_SHA:
        raise SystemExit("owner input hash mismatch")
    if len(pre["factual_authority_envelope"]["propositions"]) != 8:
        raise SystemExit("proposition-binding count")
    expected = {(item["operation_ordinal"], item["role"]): item for item in packet["signature_requests"]}
    paths = sorted(responses.glob("*.pilot12-response.json"))
    if len(paths) != 8 or len(expected) != 8:
        raise SystemExit("exactly 8/8 responses required")
    if any(any(token in path.name.lower() for token in ("private", ".key", ".der", ".sig"))
           for path in responses.iterdir() if path.is_file()):
        raise SystemExit("secret-like material in public handoff")
    keys = {item["role"]: item for item in registration["registrations"]}
    fields = {"schema_name", "schema_version", "packet_identity", "operation_ordinal", "purpose", "signer_role",
              "principal_identity", "challenge_identity", "canonical_challenge_sha256", "registered_public_key_fingerprint",
              "algorithm", "signature", "private_key_included", "grants_operational_authority"}
    verified: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
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
        challenge_core = dict(challenge)
        challenge_identity = challenge_core.pop("challenge_identity")
        if seal("B2_PILOT12_SIGNING_CHALLENGE_V1", challenge_core) != challenge_identity:
            raise SystemExit(f"challenge seal: {key}")
        operation = packet["packet_core"]["operations"][request["operation_ordinal"]]
        binding = (
            response["packet_identity"] == PACKET_ID
            and response["purpose"] == request["purpose"] == challenge["purpose"]
            and response["principal_identity"] == challenge["principal_identity"] == registered["principal_identity"]
            and response["challenge_identity"] == challenge_identity
            and challenge["role"] == response["signer_role"]
            and challenge["domain"] == "PASTILA_BATCH2_DEVELOPMENT_PILOT12_PREINGESTION_V1"
            and challenge["object_identity"] == operation["object_identity"]
            and challenge["prior_ledger_head"] == prior["final_ledger_head"]
            and challenge["preingestion_identity"] == pre["preingestion_identity"]
            and challenge["source_sha256"] == SOURCE_SHA
            and challenge["declaration_sha256"] == DECLARATION_SHA
            and challenge["grants_operational_content_access"] is False
        )
        if not binding:
            raise SystemExit(f"challenge binding: {key}")
        message = canonical(challenge)
        if response["canonical_challenge_sha256"] != sha(message):
            raise SystemExit(f"canonical challenge hash: {key}")
        if response["algorithm"] != registered["algorithm"]:
            raise SystemExit(f"algorithm: {key}")
        if response["registered_public_key_fingerprint"] != registered["public_key_fingerprint"]:
            raise SystemExit(f"fingerprint: {key}")
        if spki_fingerprint(registered["public_key"]["value"]) != registered["public_key_fingerprint"]:
            raise SystemExit(f"independent SPKI fingerprint: {key}")
        if response["private_key_included"] is not False or response["grants_operational_authority"] is not False:
            raise SystemExit(f"private/authority marker: {key}")
        try:
            signature = base64.b64decode(response["signature"]["value"], validate=True)
        except (KeyError, ValueError) as error:
            raise SystemExit(f"signature encoding: {key}") from error
        if response["signature"].get("encoding") != "BASE64" or not verify_signature(
                registered["public_key"]["value"], registered["algorithm"], message, signature):
            raise SystemExit(f"invalid signature: {key}")
        verified.append({"operation_ordinal": key[0], "purpose": response["purpose"], "role": key[1],
                         "principal_identity": response["principal_identity"],
                         "public_key_fingerprint": response["registered_public_key_fingerprint"],
                         "challenge_identity": response["challenge_identity"], "nonce": challenge["nonce"],
                         "response_sha256": sha(raw), "signature_verification": "PASS"})
    if seen != set(expected) or len({item["nonce"] for item in verified}) != 8:
        raise SystemExit("missing duplicate replayed or reused proof")
    for operation in packet["packet_core"]["operations"]:
        actual = {item["role"] for item in verified if item["operation_ordinal"] == operation["ordinal"]}
        if actual != set(operation["required_signer_roles"]):
            raise SystemExit(f"countersignature set: {operation['ordinal']}")
    tracked = subprocess.check_output(["git", "grep", "-l", PACKET_ID, "HEAD", "--", "docs/artifacts"],
                                      cwd=ROOT, text=True).splitlines()
    allowed = {f"HEAD:{PACKET_PATH}", f"HEAD:{PRE_PATH}"}
    if any(item not in allowed for item in tracked):
        raise SystemExit("packet already consumed/replayed")
    return pre, packet, sorted(verified, key=lambda item: (item["operation_ordinal"], item["role"])), prior


def materialize(pre: dict[str, Any], packet: dict[str, Any], verified: list[dict[str, Any]], prior: dict[str, Any]) -> dict[str, Any]:
    if DESTINATION.exists():
        raise SystemExit("ingestion destination already exists; refusing replay")
    source, declaration = SOURCE.read_bytes(), DECLARATION.read_bytes()
    response_set = seal("B2_DEVELOPMENT_PILOT12_VERIFIED_RESPONSE_SET_V1", verified)
    previous, entries = prior["final_ledger_head"], []
    start = prior["entries"][-1]["entry_sequence"] + 1
    for sequence, operation in enumerate(packet["packet_core"]["operations"], start=start):
        entry = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
                 "entry_sequence": sequence, "previous_entry_hash": previous,
                 "event": "DEVELOPMENT_PILOT12_ATOMIC_INGESTION_OPERATION_ADMITTED", "packet_identity": PACKET_ID,
                 "operation_ordinal": operation["ordinal"], "purpose": operation["purpose"],
                 "object_identity": operation["object_identity"],
                 "signer_bindings": [item for item in verified if item["operation_ordinal"] == operation["ordinal"]],
                 "partition": "DEVELOPMENT", "creative_premise_family_id": "UNASSIGNED",
                 "operational_content_access": False}
        entry["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", entry)
        previous = entry["entry_hash"]
        entries.append(entry)
    completion = {"schema_name": "batch2-custodial-access-ledger-entry-v1", "schema_version": "1.0.0",
                  "entry_sequence": start + len(packet["packet_core"]["operations"]), "previous_entry_hash": previous,
                  "event": "DEVELOPMENT_PILOT12_ATOMIC_INGESTION_COMPLETED", "packet_identity": PACKET_ID,
                  "source_package_identity": pre["source_package_identity"],
                  "partition_identity": pre["prospective_partition_identity"], "response_set_identity": response_set,
                  "operational_content_access": False}
    completion["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", completion)
    entries.append(completion)
    ledger = {"schema_name": "batch2-development-pilot12-access-ledger-segment-v1", "schema_version": "1.0.0",
              "previous_ledger_head": prior["final_ledger_head"], "entries": entries,
              "final_ledger_head": completion["entry_hash"]}
    ledger["ledger_segment_identity"] = seal("B2_DEVELOPMENT_PILOT12_ACCESS_LEDGER_SEGMENT_V1", ledger)
    package = {"schema_name": "batch2-owned-authority-source-package-materialization-v1", "schema_version": "1.0.0",
               "source_package_identity": pre["source_package_identity"], "source_commitment": pre["source_commitment"],
               "immutable_archive_commitment": pre["immutable_archive_commitment"],
               "rights_instrument_identity": pre["rights_instrument_identity"],
               "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"],
               "source_sha256": SOURCE_SHA, "source_byte_length": len(source), "encoding": "UTF-8",
               "prospective_git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
               "family_identities": pre["family_identities"], "partition": "DEVELOPMENT",
               "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
               "access_ledger_identity": ledger["final_ledger_head"], "materialization_status": "INGESTED_IMMUTABLE"}
    archive = {"schema_name": "batch2-development-pilot12-immutable-archive-receipt-v1", "schema_version": "1.0.0",
               "immutable_archive_commitment": pre["immutable_archive_commitment"], "original_bytes_sha256": SOURCE_SHA,
               "readback_sha256": SOURCE_SHA, "byte_length": len(source),
               "git_blob_oid_sha1": pre["prospective_git_blob_oid_sha1"],
               "capture_time": json.loads(declaration)["source"]["capture_timestamp"],
               "writer_authority": "ATOMIC_CUSTODIAL_PACKET_8_OF_8",
               "rights_instrument_identity": pre["rights_instrument_identity"],
               "previous_ledger_head": prior["final_ledger_head"]}
    archive["archive_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT12_ARCHIVE_RECEIPT_V1", archive)
    evidence = {"schema_name": "batch2-development-pilot12-custodial-verification-v1", "schema_version": "1.0.0",
                "packet_identity": PACKET_ID, "verification_result": "PASS_8_OF_8", "verified_responses": verified,
                "response_set_identity": response_set, "countersignatures": "PASS", "separation_of_duties": "PASS",
                "replay_check": "PASS", "packet_consumed": True,
                "nonces_consumed": [item["nonce"] for item in verified]}
    evidence["verification_identity"] = seal("B2_DEVELOPMENT_PILOT12_CUSTODIAL_VERIFICATION_V1", evidence)
    authority_names = ("g01_admission", "proposition_sufficiency_evaluation", "assignment",
                       "constructor_source_compatibility_evaluation", "semantic_plan_evaluation", "constructor_release",
                       "constructor_invocation", "realization", "candidate_emission", "coordinate_bound_semantic_conformance",
                       "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c", "g03",
                       "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")
    receipt = {"schema_name": "batch2-development-pilot12-ingestion-receipt-v1", "schema_version": "1.0.0",
               "terminal_verdict": "ATOMIC_IMMUTABLE_INGESTION_PASS", "preparation_commit": PREPARATION_COMMIT,
               "signing_helper_commit": HELPER_COMMIT, "preingestion_identity": pre["preingestion_identity"],
               "packet_identity": PACKET_ID, "source_commitment": pre["source_commitment"],
               "rights_instrument_identity": pre["rights_instrument_identity"],
               "immutable_archive_commitment": pre["immutable_archive_commitment"],
               "source_package_identity": pre["source_package_identity"],
               "factual_authority_envelope_identity": pre["factual_authority_envelope_identity"],
               "partition_identity": pre["prospective_partition_identity"], "creative_premise_family_id": "UNASSIGNED",
               "proposition_bindings": "PASS_8_NOT_SELECTED", "proposition_sufficiency_evaluated": False,
               "verification_identity": evidence["verification_identity"],
               "archive_receipt_identity": archive["archive_receipt_identity"],
               "access_ledger_identity": ledger["final_ledger_head"],
               "ledger_segment_identity": ledger["ledger_segment_identity"],
               "authority_matrix": {name: False for name in authority_names}}
    receipt["ingestion_receipt_identity"] = seal("B2_DEVELOPMENT_PILOT12_INGESTION_RECEIPT_V1", receipt)
    temporary = Path(tempfile.mkdtemp(prefix=".pilot12-ingestion-", dir=DESTINATION.parent))
    try:
        (temporary / "source.utf8.txt").write_bytes(source)
        (temporary / "rights-instrument.json").write_bytes(declaration)
        values = (("factual-authority-envelope.json", pre["factual_authority_envelope"]),
                  ("source-package.json", package), ("archive-receipt.json", archive),
                  ("custodial-verification.json", evidence), ("access-ledger-segment.json", ledger),
                  ("ingestion-receipt.json", receipt))
        for name, value in values:
            write_json(temporary / name, value)
        if sha((temporary / "source.utf8.txt").read_bytes()) != SOURCE_SHA:
            raise SystemExit("atomic source readback mismatch")
        if sha((temporary / "rights-instrument.json").read_bytes()) != DECLARATION_SHA:
            raise SystemExit("atomic declaration readback mismatch")
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
