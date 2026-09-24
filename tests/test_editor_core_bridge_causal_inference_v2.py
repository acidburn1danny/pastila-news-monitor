from __future__ import annotations

import json
import hashlib
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_editor_core_bridge_causal_responses_v2 import NO_REPEAT_NGRAM_SIZE, RESPONSE_KEYS, canonical, sha, validate_generated_response
from supervise_editor_core_bridge_causal_inference_v2 import Journal


def response(payload: dict) -> str:
    value = dict(zip(RESPONSE_KEYS, (
        "pastila-core-v2-structured-qualification-response", 2, payload["case_id"],
        payload["request_identity"], payload["output_type"], "ANSWER", "Text factual.",
        [{"claim_index": 1, "source_span_ids": [payload["authority_spans"][0]["span_id"]]}], None,
    ), strict=True))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def payload() -> dict:
    return {"case_id": "case-1", "request_identity": "sha256:" + "a" * 64,
            "output_type": "FACTUAL", "authority_spans": [{"span_id": "span:1"}]}


def test_valid_response_closes():
    assert NO_REPEAT_NGRAM_SIZE == 8
    assert validate_generated_response(response(payload()), payload(), True)["outcome"] == "ANSWER"


@pytest.mark.parametrize("text,eos", [
    ('{"schema":', False),
    ('{"schema":', True),
    (response(payload()), False),
    ('{"schema":1,"schema":2}', True),
])
def test_truncated_malformed_duplicate_or_non_eos_fails_closed(text: str, eos: bool):
    with pytest.raises(ValueError):
        validate_generated_response(text, payload(), eos)


def test_request_substitution_fails_closed():
    changed = json.loads(response(payload()))
    changed["case_id"] = "other"
    with pytest.raises(ValueError, match="binding"):
        validate_generated_response(json.dumps(changed, separators=(",", ":")), payload(), True)


def test_terminal_journal_is_single_assignment(tmp_path: Path):
    journal = Journal(tmp_path)
    journal.write("PROGRAM_START")
    journal.write("PROGRAM_END", status="PASS")
    with pytest.raises(RuntimeError, match="terminal"):
        journal.write("PROGRAM_END", status="BLOCKED")
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_bytes().splitlines()]
    assert [row["event"] for row in rows] == ["PROGRAM_START", "PROGRAM_END"]
    assert rows[-1]["status"] == "PASS"


def test_historical_outputs_are_rejected_by_successor_audit():
    from audit_editor_core_bridge_causal_responses_v2 import audit
    historical = Path("/root/pf9-editor-core-bridge-causal-inference-v1")
    if not historical.exists():
        pytest.skip("real historical outputs live only in the WSL evidence store")
    authority = json.loads((ROOT / "docs/artifacts/editor-core-editorial-bridge-causal-inference-authority-v1.json").read_bytes())
    identities = {row["candidate"]: row["adapter_sha256"] for row in authority["candidates"]}
    requests = ROOT / "docs/artifacts/editor-core-editorial-mechanics-bridge-v1-development-requests.jsonl"
    with pytest.raises(ValueError, match="EOS"):
        audit(historical, requests, identities)


def test_successor_authority_identity_and_source_closure():
    authority_path = ROOT / "docs/artifacts/editor-core-editorial-bridge-causal-inference-authority-v2.json"
    authority = json.loads(authority_path.read_bytes())
    core = {key: value for key, value in authority.items() if key != "authority_identity"}
    identity = hashlib.sha256(json.dumps(core, ensure_ascii=False, allow_nan=False,
                                         sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert authority["authority_identity"] == identity
    for name in ("worker", "route", "audit", "verifier", "supervisor", "design"):
        path = ROOT / authority[f"{name}_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == authority[f"{name}_sha256"]
    assert authority["terminal_eos_required_per_row"] is True
    assert authority["strict_json_required_per_row"] is True
    assert authority["historical_scoring_packages_eligibility"] == "REJECTED_REGENERATE_FROM_ZERO"
