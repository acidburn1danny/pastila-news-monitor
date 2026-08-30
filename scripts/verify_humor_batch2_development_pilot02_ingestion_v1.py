"""Verify the immutable Development Pilot 02 materialization (no writes)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1"
EXPECTED = {"source": "be9853603f82bc1fd11b2d0e06a692b3db4b83d1a7e20733c203c5aea1a04ea8",
            "declaration": "1791250d9e17c718b48f93c8354afe120fedce0821e0021b4423d88f89416929",
            "source_package": "241171211ce96e247dcfaeaa513fb4a38f187008dd0e71697b3c85e4e4140668",
            "archive": "584f483b830492ff8ac8353238d9c5d3b9747683aab8133de026a42d24831780",
            "rights": "5d3e704a4d40715cbfad67a59188a873335b9f45116d09f6c4c0fa7d974e2ac3",
            "authority": "f3a66b5ccaa831acc171daa509700b16dbe2ebc9cfac30c8e68296e67c4bed9e"}


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
    require(seal("B2_DEVELOPMENT_PILOT02_ARCHIVE_RECEIPT_V1", archive_core) == archive_id, "archive receipt seal")
    proof_core = dict(proof); proof_id = proof_core.pop("verification_identity")
    require(seal("B2_DEVELOPMENT_PILOT02_CUSTODIAL_VERIFICATION_V1", proof_core) == proof_id, "proof seal")
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
    require(seal("B2_DEVELOPMENT_PILOT02_ACCESS_LEDGER_SEGMENT_V1", ledger_core) == segment, "ledger segment seal")
    receipt_core = dict(receipt); receipt_id = receipt_core.pop("ingestion_receipt_identity")
    require(seal("B2_DEVELOPMENT_PILOT02_INGESTION_RECEIPT_V1", receipt_core) == receipt_id, "ingestion receipt seal")
    text = source.decode("utf-8")
    require(len(envelope["propositions"]) == 7, "seven propositions")
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
              "seven_proposition_bindings": "PASS", "downstream_authorities": False}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
