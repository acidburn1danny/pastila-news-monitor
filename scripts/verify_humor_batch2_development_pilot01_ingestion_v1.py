"""Verify the immutable Development Pilot 01 materialization (no writes)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1"
EXPECTED = {"source": "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2",
            "declaration": "26712ba98a4022dc72d1a41b6c178665fbd7cb27aeb76da1aa08ff02b960aa81",
            "source_package": "8377969bb9974e1e884243072fb178c977bb7074e03083f03a9329e64589f9ec",
            "archive": "33fe934281f3eb21c19dc6bad23edfb5c809d32026dfdfddd77ed15d8417e031",
            "rights": "11b24f3d67d17e04ff8ff24a38f1e24722de5433d76830a5b8c0e85ec0d45bab",
            "authority": "7d0f1decc3e4908a03beedf4cec408cce096e07381b5e36f56c5e9dcb4975c65"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value: raise SystemExit(message)


def main() -> None:
    expected_files = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json",
                      "source-package.json", "archive-receipt.json", "custodial-verification.json",
                      "access-ledger-segment.json", "ingestion-receipt.json"}
    require({x.name for x in FOLDER.iterdir()} == expected_files, "exact file set")
    source, rights = (FOLDER / "source.utf8.txt").read_bytes(), (FOLDER / "rights-instrument.json").read_bytes()
    require(hashlib.sha256(source).hexdigest() == EXPECTED["source"], "source hash")
    require(hashlib.sha256(rights).hexdigest() == EXPECTED["declaration"], "rights bytes hash")
    package = json.loads((FOLDER / "source-package.json").read_text(encoding="utf-8"))
    envelope = json.loads((FOLDER / "factual-authority-envelope.json").read_text(encoding="utf-8"))
    archive = json.loads((FOLDER / "archive-receipt.json").read_text(encoding="utf-8"))
    proof = json.loads((FOLDER / "custodial-verification.json").read_text(encoding="utf-8"))
    ledger = json.loads((FOLDER / "access-ledger-segment.json").read_text(encoding="utf-8"))
    receipt = json.loads((FOLDER / "ingestion-receipt.json").read_text(encoding="utf-8"))
    require(package["source_package_identity"] == EXPECTED["source_package"] and package["immutable_archive_commitment"] == EXPECTED["archive"], "package identity")
    require(package["rights_instrument_identity"] == EXPECTED["rights"] and package["factual_authority_envelope_identity"] == EXPECTED["authority"], "rights/authority identity")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition/creative premise")
    require(archive["immutable_archive_commitment"] == EXPECTED["archive"] and archive["readback_sha256"] == EXPECTED["source"], "archive readback")
    archive_core = dict(archive); archive_id = archive_core.pop("archive_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_ARCHIVE_RECEIPT_V1", archive_core) == archive_id, "archive receipt seal")
    proof_core = dict(proof); proof_id = proof_core.pop("verification_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_CUSTODIAL_VERIFICATION_V1", proof_core) == proof_id, "proof seal")
    require(proof["verification_result"] == "PASS_8_OF_8" and len(proof["verified_responses"]) == 8, "8/8 proof")
    require(len(set(proof["nonces_consumed"])) == 8 and proof["packet_consumed"] is True, "nonce/packet consumption")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "ledger continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "ledger entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == package["access_ledger_identity"], "ledger head")
    ledger_core = dict(ledger); segment = ledger_core.pop("ledger_segment_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_ACCESS_LEDGER_SEGMENT_V1", ledger_core) == segment, "ledger segment seal")
    receipt_core = dict(receipt); receipt_id = receipt_core.pop("ingestion_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_INGESTION_RECEIPT_V1", receipt_core) == receipt_id, "ingestion receipt seal")
    text = source.decode("utf-8")
    require(len(envelope["propositions"]) == 6, "six propositions")
    for proposition in envelope["propositions"]:
        for component in ("subject", "predicate", "object"):
            item = proposition[component]; cs, ce = item["character_coordinates"]; bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode("utf-8")
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item["sha256"], f"span {proposition['proposition_id']} {component}")
    require(all(value is False for value in receipt["authority_matrix"].values()), "downstream authority")
    blob_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(blob_oid == package["prospective_git_blob_oid_sha1"], "git blob projection")
    result = {"verdict": receipt["terminal_verdict"], "signature_verification": "PASS_8_OF_8",
              "ingestion_receipt_identity": receipt_id, "access_ledger_identity": ledger["final_ledger_head"],
              "ledger_segment_identity": segment, "source_git_blob_oid_sha1": blob_oid,
              "six_proposition_bindings": "PASS", "downstream_authorities": False}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
