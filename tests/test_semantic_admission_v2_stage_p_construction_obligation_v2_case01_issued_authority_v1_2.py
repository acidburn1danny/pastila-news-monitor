from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_2 import parse_generation_authority_v1_2

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2 import verify

ROOT = Path(__file__).resolve().parents[1]


def test_exact_v1_2_receipt_is_issued_with_one_unconsumed_attempt():
    result = verify(project_root=ROOT)
    assert result == {
        "packet_commit": "5237302820ccfc8d6fa13e344d9889318f756220",
        "packet_identity": "34cab9bfd4e0a339ba79fa1d6acba68ab8aec50856cbfc28fcd4866fb3a78202",
        "command_identity": "6ba16167bdacf2e88bf099fe782f5c8e21a0d47d696bb9ff710c38e7737166ea",
        "authority_receipt_identity": "e38035ec43e037c02d07597f6177763ee1e672cd462272c7da80fb50d1a86e06",
        "receipt_status": "ISSUED", "attempt_ceiling": 1,
        "consumed_attempts": 0, "remaining_attempts": 1,
        "execution_started": False,
    }


def test_issuance_verifier_has_no_execution_callsite():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2.py"
    tree = ast.parse(path.read_text("utf-8"))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    text = path.read_text("utf-8")
    assert all(term not in text for term in ("subprocess", "from_pretrained", ".generate(", "nvidia-smi"))


def test_consumed_v1_1_receipt_cannot_satisfy_v1_2_packet():
    old = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1/authority-receipt-issued.json"
    packet = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2"
    runner_raw = (packet / "runner-request.json").read_bytes()
    runner = json.loads(runner_raw)
    with pytest.raises(ValueError):
        parse_generation_authority_v1_2(
            raw_receipt=old.read_bytes(),
            expected_host_payload_sha256=runner["host_payload_sha256"],
            expected_runner_request_sha256=hashlib.sha256(runner_raw).hexdigest(),
            expected_provider_request_id=runner["provider_request_id"],
            expected_source_context_identity=runner["source_context_identity"],
        )
