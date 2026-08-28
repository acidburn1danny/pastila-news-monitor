from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1 import (
    CASE_ID,
    PACKET_RELATIVE,
    SOURCE_CONTEXT_IDENTITY,
    materialize_case01_issuance_packet_v1,
)
from scripts.verify_construction_obligation_v2_case01_issuance_packet_v1 import verify

ROOT = Path(__file__).resolve().parents[1]


def test_packet_is_byte_exact_current_case01_and_unissued() -> None:
    rebuilt = materialize_case01_issuance_packet_v1(project_root=ROOT)
    actual = {path.name for path in (ROOT / PACKET_RELATIVE).iterdir()}
    assert actual == set(rebuilt) | {"authority-receipt-issued.json"}
    assert all((ROOT / PACKET_RELATIVE / name).read_bytes() == raw
               for name, raw in rebuilt.items())
    manifest = verify(project_root=ROOT)
    assert manifest["case_id"] == CASE_ID == "HMCV1-SASC-01"
    assert manifest["source_context_identity"] == SOURCE_CONTEXT_IDENTITY
    assert manifest["historical_request_reused"] is False
    assert manifest["receipt_status"] == "UNISSUED"
    assert all(value is False for value in manifest["execution"].values())


def test_single_command_and_fail_closed_limits_are_exact() -> None:
    manifest = json.loads((ROOT / PACKET_RELATIVE / "manifest.json").read_bytes())
    command = manifest["command"]
    assert command.count("-m") == 1
    assert any(item.endswith("linux_generation_runner_v1_1") for item in command)
    assert manifest["limits"] == {
        "attempt_ceiling": 1, "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200, "minimum_free_vram_mib": 14000,
        "retry": 0, "fallback": 0, "repair": 0, "selection": 0,
        "stage_c": False,
    }


def test_materializer_and_verifier_have_no_execution_callsite() -> None:
    paths = (
        ROOT / "src/pastila_scout/semantic_admission_v2/"
        "stage_p_construction_obligation_v2_case01_issuance_packet_v1.py",
        ROOT / "scripts/verify_construction_obligation_v2_case01_issuance_packet_v1.py",
    )
    for path in paths:
        tree = ast.parse(path.read_text("utf-8"))
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert "execute" not in attributes
        text = path.read_text("utf-8")
        assert all(term not in text for term in (
            "subprocess", "from_pretrained", ".generate(", "nvidia-smi"))
