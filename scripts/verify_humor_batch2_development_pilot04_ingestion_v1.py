"""Verify immutable Development Pilot 04 materialization without writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1"
EXPECTED = {
    "source": "db4d440d42596e2db5ca402afa23bc8f65dcf7a7ba23a06d3ebef9e2eb1aa480",
    "declaration": "d7da118d32f2ca05fc5d1816a616e8bccdc58017f934539efc054733da9d5958",
    "source_package": "6fb31794566391bafa242fd8de1048ed3f3f234b9822b9d7f4a99307fbe1d72c",
    "archive": "07dc1bcf9f0af46e1b3003774ab39c7f612ba89daa58f3c402b1fc87cff1f7fd",
    "rights": "549fa8e91e20dd36365bb4a37c4871a2951180ca6059bdf1243ab2c73f33646d",
    "authority": "40c92efd6ee0ae4b99d422094d2d28073ad8602df0c1528a38bbf681aba3de8d",
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
    require(seal("B2_DEVELOPMENT_PILOT04_ARCHIVE_RECEIPT_V1", archive_core) == archive_id, "archive receipt")
    proof_core = dict(proof); proof_id = proof_core.pop("verification_identity")
    require(seal("B2_DEVELOPMENT_PILOT04_CUSTODIAL_VERIFICATION_V1", proof_core) == proof_id, "proof seal")
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
    require(seal("B2_DEVELOPMENT_PILOT04_ACCESS_LEDGER_SEGMENT_V1", ledger_core) == segment, "segment")
    receipt_core = dict(receipt); receipt_id = receipt_core.pop("ingestion_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT04_INGESTION_RECEIPT_V1", receipt_core) == receipt_id, "receipt")
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
