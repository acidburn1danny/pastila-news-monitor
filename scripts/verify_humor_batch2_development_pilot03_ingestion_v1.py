"""Verify immutable Development Pilot 03 materialization without writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1"
EXPECTED = {
    "source": "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30",
    "declaration": "5915ee71841ed1a40ae375e0e7c6a4b611c525d0b8690464e61d66e078b14d8d",
    "source_package": "08fe16a0a8b003a661cac1238eec0f752be1ae5c11e417125e1d7031291abeb6",
    "archive": "a114c0858b66bee530afe758e1ba174356913f2eecac5f90780ff63902816955",
    "rights": "1165555c4f91781f5c22db56316899c9f89dfcc46c817f24d59dc997790cc4d6",
    "authority": "3808b24094412383f4a152233c7f18d098ea4cfa6a90c2a41ee1093c8ac02ac3",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    expected_files = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json",
                      "source-package.json", "archive-receipt.json", "custodial-verification.json",
                      "access-ledger-segment.json", "ingestion-receipt.json"}
    require({x.name for x in FOLDER.iterdir()} == expected_files, "exact file set")
    source = (FOLDER / "source.utf8.txt").read_bytes()
    rights = (FOLDER / "rights-instrument.json").read_bytes()
    require(hashlib.sha256(source).hexdigest() == EXPECTED["source"], "source hash")
    require(hashlib.sha256(rights).hexdigest() == EXPECTED["declaration"], "rights bytes hash")
    load = lambda name: json.loads((FOLDER / name).read_text(encoding="utf-8"))
    package, envelope, archive = load("source-package.json"), load("factual-authority-envelope.json"), load("archive-receipt.json")
    proof, ledger, receipt = load("custodial-verification.json"), load("access-ledger-segment.json"), load("ingestion-receipt.json")
    require(package["source_package_identity"] == EXPECTED["source_package"], "source package")
    require(package["immutable_archive_commitment"] == EXPECTED["archive"], "archive commitment")
    require(package["rights_instrument_identity"] == EXPECTED["rights"], "rights identity")
    require(package["factual_authority_envelope_identity"] == EXPECTED["authority"], "authority identity")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition")
    archive_core = dict(archive); archive_id = archive_core.pop("archive_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT03_ARCHIVE_RECEIPT_V1", archive_core) == archive_id, "archive receipt")
    proof_core = dict(proof); proof_id = proof_core.pop("verification_identity")
    require(seal("B2_DEVELOPMENT_PILOT03_CUSTODIAL_VERIFICATION_V1", proof_core) == proof_id, "proof seal")
    require(proof["verification_result"] == "PASS_8_OF_8" and len(proof["verified_responses"]) == 8, "8/8")
    require(proof["packet_consumed"] is True and len(set(proof["nonces_consumed"])) == 8, "consumption")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "ledger continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "ledger entry")
        previous = identity
    require(previous == ledger["final_ledger_head"] == package["access_ledger_identity"], "ledger head")
    ledger_core = dict(ledger); segment = ledger_core.pop("ledger_segment_identity")
    require(seal("B2_DEVELOPMENT_PILOT03_ACCESS_LEDGER_SEGMENT_V1", ledger_core) == segment, "segment")
    receipt_core = dict(receipt); receipt_id = receipt_core.pop("ingestion_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT03_INGESTION_RECEIPT_V1", receipt_core) == receipt_id, "receipt")
    text = source.decode("utf-8")
    require(len(envelope["propositions"]) == 7, "seven propositions")
    for proposition in envelope["propositions"]:
        for component in ("subject", "predicate", "object"):
            item = proposition[component]
            cs, ce = item["character_coordinates"]
            bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode("utf-8")
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item["sha256"], f"span {proposition['proposition_id']} {component}")
    require(all(value is False for value in receipt["authority_matrix"].values()), "downstream authority")
    blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(blob == package["prospective_git_blob_oid_sha1"], "blob")
    print(json.dumps({"verdict": receipt["terminal_verdict"], "signature_verification": "PASS_8_OF_8",
                      "ingestion_receipt_identity": receipt_id, "verification_identity": proof_id,
                      "access_ledger_identity": ledger["final_ledger_head"], "ledger_segment_identity": segment,
                      "archive_receipt_identity": archive_id, "source_git_blob_oid_sha1": blob,
                      "seven_proposition_bindings": "PASS", "downstream_authorities": False}, sort_keys=True))


if __name__ == "__main__":
    main()
