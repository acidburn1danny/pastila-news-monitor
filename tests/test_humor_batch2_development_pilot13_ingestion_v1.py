import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-ingestion-v1"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot13_ingestion_is_exact_complete_and_non_authorizing() -> None:
    expected = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json", "source-package.json",
                "archive-receipt.json", "custodial-verification.json", "access-ledger-segment.json", "ingestion-receipt.json"}
    assert {path.name for path in DEST.iterdir()} == expected
    source_bytes = (DEST / "source.utf8.txt").read_bytes()
    declaration_bytes = (DEST / "rights-instrument.json").read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == "9d79b45d06fba5b950f97e7d09f38450177b7ff7d5cbf962a9e4f7af452b6a76"
    assert hashlib.sha256(declaration_bytes).hexdigest() == "5e18c30cab71ee0ab1e3599e1abc433af3bcebea881d683ed8322387d0d570e3"
    envelope = json.loads((DEST / "factual-authority-envelope.json").read_text(encoding="utf-8"))
    source = source_bytes.decode()
    assert len(envelope["propositions"]) == 8 and envelope["proposition_selection"] == "NOT_PERFORMED"
    for proposition in envelope["propositions"]:
        for field in ("supporting_span", "subject", "predicate", "object"):
            witness = proposition[field]
            cs, ce = witness["character_coordinates"]
            bs, be = witness["utf8_byte_coordinates"]
            assert source[cs:ce].encode() == source_bytes[bs:be]
            assert hashlib.sha256(source_bytes[bs:be]).hexdigest() == witness["sha256"]
    verification = json.loads((DEST / "custodial-verification.json").read_text(encoding="utf-8"))
    core = dict(verification); identity = core.pop("verification_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_CUSTODIAL_VERIFICATION_V1", core)
    assert verification["verification_result"] == "PASS_8_OF_8" and len(verification["verified_responses"]) == 8
    ledger = json.loads((DEST / "access-ledger-segment.json").read_text(encoding="utf-8"))
    core = dict(ledger); identity = core.pop("ledger_segment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_ACCESS_LEDGER_SEGMENT_V1", core)
    assert len(ledger["entries"]) == 7 and ledger["entries"][-1]["entry_sequence"] == 105
    receipt = json.loads((DEST / "ingestion-receipt.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("ingestion_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_INGESTION_RECEIPT_V1", core)
    assert receipt["terminal_verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS"
    assert receipt["proposition_bindings"] == "PASS_8_NOT_SELECTED"
    assert all(value is False for value in receipt["authority_matrix"].values())
