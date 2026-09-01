import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot11-ingestion-v1"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot11_ingestion_is_exact_complete_and_non_authorizing() -> None:
    expected = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json", "source-package.json",
                "archive-receipt.json", "custodial-verification.json", "access-ledger-segment.json", "ingestion-receipt.json"}
    assert {path.name for path in DEST.iterdir()} == expected
    assert hashlib.sha256((DEST / "source.utf8.txt").read_bytes()).hexdigest() == "cdf1901941057914cb7b22ac1233771773e2f15bd1671bcc47e2d17d123e2bd9"
    assert hashlib.sha256((DEST / "rights-instrument.json").read_bytes()).hexdigest() == "6fdb4ca1cac39f6b4cf4ae9614163d0641695608568bebc4e582322190a3ed21"
    envelope = json.loads((DEST / "factual-authority-envelope.json").read_text(encoding="utf-8"))
    source = (DEST / "source.utf8.txt").read_text(encoding="utf-8")
    raw = source.encode()
    assert len(envelope["propositions"]) == 7
    for proposition in envelope["propositions"]:
        span = proposition["supporting_span"]
        cs, ce = span["character_coordinates"]; bs, be = span["utf8_byte_coordinates"]
        assert source[cs:ce].encode() == raw[bs:be]
        assert hashlib.sha256(raw[bs:be]).hexdigest() == span["span_sha256"]
    verification = json.loads((DEST / "custodial-verification.json").read_text(encoding="utf-8"))
    core = dict(verification); identity = core.pop("verification_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_CUSTODIAL_VERIFICATION_V1", core)
    assert verification["verification_result"] == "PASS_8_OF_8"
    assert len(verification["verified_responses"]) == 8
    ledger = json.loads((DEST / "access-ledger-segment.json").read_text(encoding="utf-8"))
    core = dict(ledger); identity = core.pop("ledger_segment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_ACCESS_LEDGER_SEGMENT_V1", core)
    assert len(ledger["entries"]) == 7 and ledger["entries"][-1]["entry_sequence"] == 91
    receipt = json.loads((DEST / "ingestion-receipt.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("ingestion_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_INGESTION_RECEIPT_V1", core)
    assert receipt["terminal_verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS"
    assert receipt["proposition_bindings"] == "PASS_7"
    assert all(value is False for value in receipt["authority_matrix"].values())
