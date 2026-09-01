
"""Read-only verification of immutable Pilot 09 ingestion artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict[str, Any]:
    return json.loads((DIR / name).read_text(encoding="utf-8"))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    source = (DIR / "source.utf8.txt").read_bytes()
    rights = (DIR / "rights-instrument.json").read_bytes()
    envelope, package = load("factual-authority-envelope.json"), load("source-package.json")
    archive, evidence = load("archive-receipt.json"), load("custodial-verification.json")
    ledger, receipt = load("access-ledger-segment.json"), load("ingestion-receipt.json")
    require(hashlib.sha256(source).hexdigest() == "608f26b4588c347707ae5eccb08194d498fb3b3e9e7a6402be63ad2bc7c77c77", "source")
    require(hashlib.sha256(rights).hexdigest() == "8c68d5bf2a711fc518879fcddfba9ea44d7c232fb962fdecc816bf97d249b41b", "rights")
    require(receipt["ingestion_receipt_identity"] == seal("B2_DEVELOPMENT_PILOT09_INGESTION_RECEIPT_V1", {k: v for k, v in receipt.items() if k != "ingestion_receipt_identity"}), "receipt")
    require(archive["archive_receipt_identity"] == seal("B2_DEVELOPMENT_PILOT09_ARCHIVE_RECEIPT_V1", {k: v for k, v in archive.items() if k != "archive_receipt_identity"}), "archive")
    require(evidence["verification_identity"] == seal("B2_DEVELOPMENT_PILOT09_CUSTODIAL_VERIFICATION_V1", {k: v for k, v in evidence.items() if k != "verification_identity"}), "evidence")
    require(ledger["ledger_segment_identity"] == seal("B2_DEVELOPMENT_PILOT09_ACCESS_LEDGER_SEGMENT_V1", {k: v for k, v in ledger.items() if k != "ledger_segment_identity"}), "ledger")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "ledger continuity")
        require(entry["entry_hash"] == seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", {k: v for k, v in entry.items() if k != "entry_hash"}), "entry")
        previous = entry["entry_hash"]
    require(previous == ledger["final_ledger_head"] == receipt["access_ledger_identity"], "head")
    require(evidence["verification_result"] == "PASS_8_OF_8" and len(evidence["verified_responses"]) == 8, "signatures")
    require(len(set(evidence["nonces_consumed"])) == 8 and evidence["packet_consumed"] is True, "consumption")
    text = source.decode("utf-8")
    propositions = envelope["propositions"]
    require([p["proposition_id"] for p in propositions] == [f"P{i}" for i in range(1, 9)], "propositions")
    for proposition in propositions:
        for key in ("supporting_span", "subject", "predicate", "object"):
            part = proposition[key]; cs, ce = part["character_coordinates"]; bs, be = part["utf8_byte_coordinates"]
            require(text[cs:ce].encode() == source[bs:be], "coordinates")
            require(hashlib.sha256(source[bs:be]).hexdigest() == part.get("span_sha256", part.get("sha256")), "span hash")
    require(package["source_package_identity"] == receipt["source_package_identity"] == "e6b520958d949f673600366018572fb00da98125646ab75cdb4fc6e34d1da5f0", "package")
    require(receipt["terminal_verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS", "verdict")
    require(receipt["proposition_sufficiency_evaluated"] is False and receipt["constructor_v5_compatibility_evaluated"] is False and all(v is False for v in receipt["authority_matrix"].values()), "authority")
    blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(blob == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "blob")
    print(json.dumps({"verdict": receipt["terminal_verdict"], "signature_verification": evidence["verification_result"],
                      "eight_proposition_bindings": "PASS", "source_git_blob_oid_sha1": blob,
                      "ingestion_receipt_identity": receipt["ingestion_receipt_identity"],
                      "access_ledger_identity": receipt["access_ledger_identity"],
                      "proposition_sufficiency_evaluated": False, "constructor_v5_compatibility_evaluated": False, "downstream_authorities": False}, sort_keys=True))


if __name__ == "__main__":
    main()

