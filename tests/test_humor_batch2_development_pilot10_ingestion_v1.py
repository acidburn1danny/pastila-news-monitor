"""Test Pilot 10 ingestion invariants without consuming the public responses."""

import importlib.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_humor_batch2_development_pilot10_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pilot10_ingestion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_packet_and_ingestion_boundary():
    module = load_module()
    pre = module.committed(module.FREEZE_COMMIT, module.PRE_PATH)
    packet = module.committed(module.FREEZE_COMMIT, module.PACKET_PATH)
    assert packet["packet_identity"] == module.PACKET_ID
    assert len(packet["signature_requests"]) == 8
    assert len(pre["factual_authority_envelope"]["propositions"]) == 7
    assert pre["source_package_identity"] == "cd1c968bb7d90416b5255ad14094410491e756ce58bc78512cca2e5297a044c1"
    assert all(value is False for value in pre["authority_matrix"].values())


def test_materialized_receipt_remains_non_authorizing_if_present():
    module = load_module()
    receipt_path = module.DESTINATION / "ingestion-receipt.json"
    if not receipt_path.exists():
        return
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["terminal_verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS"
    assert receipt["proposition_bindings"] == "PASS_7"
    assert all(value is False for value in receipt["authority_matrix"].values())


def test_materialized_objects_rederive_and_preserve_all_seven_spans():
    module = load_module()
    destination = module.DESTINATION
    assert destination.is_dir()
    assert {path.name for path in destination.iterdir()} == {
        "source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json", "source-package.json",
        "archive-receipt.json", "custodial-verification.json", "access-ledger-segment.json", "ingestion-receipt.json",
    }
    source = (destination / "source.utf8.txt").read_bytes()
    assert hashlib.sha256(source).hexdigest() == module.SOURCE_SHA
    assert hashlib.sha256((destination / "rights-instrument.json").read_bytes()).hexdigest() == module.DECLARATION_SHA
    envelope = json.loads((destination / "factual-authority-envelope.json").read_text(encoding="utf-8"))
    source_text = source.decode("utf-8")
    for proposition in envelope["propositions"]:
        span = proposition["supporting_span"]
        cs, ce = span["character_coordinates"]; bs, be = span["utf8_byte_coordinates"]
        assert source_text[cs:ce].encode() == source[bs:be]
        assert hashlib.sha256(source[bs:be]).hexdigest() == span["span_sha256"]
    identities = [
        ("archive-receipt.json", "archive_receipt_identity", "B2_DEVELOPMENT_PILOT10_ARCHIVE_RECEIPT_V1"),
        ("custodial-verification.json", "verification_identity", "B2_DEVELOPMENT_PILOT10_CUSTODIAL_VERIFICATION_V1"),
        ("access-ledger-segment.json", "ledger_segment_identity", "B2_DEVELOPMENT_PILOT10_ACCESS_LEDGER_SEGMENT_V1"),
        ("ingestion-receipt.json", "ingestion_receipt_identity", "B2_DEVELOPMENT_PILOT10_INGESTION_RECEIPT_V1"),
    ]
    for filename, field, namespace in identities:
        value = json.loads((destination / filename).read_text(encoding="utf-8"))
        identity = value.pop(field)
        assert identity == module.seal(namespace, value)
    ledger = json.loads((destination / "access-ledger-segment.json").read_text(encoding="utf-8"))
    assert ledger["previous_ledger_head"] == "0dc087dde79a0b008d333c4e84a0572b32cb9bd25704b9a55a00cb4d5849069a"
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_hash"] == previous
        core = dict(entry); identity = core.pop("entry_hash")
        assert identity == module.seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core)
        previous = identity
    assert previous == ledger["final_ledger_head"]
