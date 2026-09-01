import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-ingestion-v1"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot12_ingestion_is_exact_complete_and_non_authorizing() -> None:
    expected = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json", "source-package.json",
                "archive-receipt.json", "custodial-verification.json", "access-ledger-segment.json", "ingestion-receipt.json"}
    assert {path.name for path in DEST.iterdir()} == expected
    assert hashlib.sha256((DEST / "source.utf8.txt").read_bytes()).hexdigest() == "8b87cef6b320d45d7594bc48919bae63442f51f1f7937b599575d435df69ea27"
    assert hashlib.sha256((DEST / "rights-instrument.json").read_bytes()).hexdigest() == "94f573e8aa1bb1789117ebef856da896447ddcfd944f195e17267e7bdf456ab3"
    envelope = json.loads((DEST / "factual-authority-envelope.json").read_text(encoding="utf-8"))
    source = (DEST / "source.utf8.txt").read_text(encoding="utf-8")
    raw = source.encode()
    assert len(envelope["propositions"]) == 8
    for proposition in envelope["propositions"]:
        span = proposition["supporting_span"]
        cs, ce = span["character_coordinates"]
        bs, be = span["utf8_byte_coordinates"]
        assert source[cs:ce].encode() == raw[bs:be]
        assert hashlib.sha256(raw[bs:be]).hexdigest() == span["span_sha256"]
    verification = json.loads((DEST / "custodial-verification.json").read_text(encoding="utf-8"))
    core = dict(verification); identity = core.pop("verification_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_CUSTODIAL_VERIFICATION_V1", core)
    assert verification["verification_result"] == "PASS_8_OF_8"
    assert len(verification["verified_responses"]) == 8
    ledger = json.loads((DEST / "access-ledger-segment.json").read_text(encoding="utf-8"))
    core = dict(ledger); identity = core.pop("ledger_segment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_ACCESS_LEDGER_SEGMENT_V1", core)
    assert len(ledger["entries"]) == 7 and ledger["entries"][-1]["entry_sequence"] == 98
    receipt = json.loads((DEST / "ingestion-receipt.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("ingestion_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_INGESTION_RECEIPT_V1", core)
    assert receipt["terminal_verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS"
    assert receipt["proposition_bindings"] == "PASS_8_NOT_SELECTED"
    assert all(value is False for value in receipt["authority_matrix"].values())
