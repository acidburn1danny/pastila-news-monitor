from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    CASE_ID,
    PACKET_RELATIVE,
    SOURCE_CONTEXT_IDENTITY,
    materialize_case01_issuance_packet_v1_2_1,
)
from scripts.verify_construction_obligation_v2_case01_issuance_packet_v1_2_1 import verify

ROOT = Path(__file__).resolve().parents[1]


def test_packet_is_byte_exact_current_case01_and_unissued() -> None:
    rebuilt = materialize_case01_issuance_packet_v1_2_1(project_root=ROOT)
    actual = {path.name for path in (ROOT / PACKET_RELATIVE).iterdir()}
    assert actual == set(rebuilt)
    assert all((ROOT / PACKET_RELATIVE / name).read_bytes() == raw
               for name, raw in rebuilt.items())
    manifest = verify(project_root=ROOT)
    assert manifest["case_id"] == CASE_ID == "HMCV1-SASC-01"
    assert manifest["source_context_identity"] == SOURCE_CONTEXT_IDENTITY
    assert manifest["historical_request_reused"] is False
    assert manifest["receipt_status"] == "UNISSUED"
    assert manifest["attempts"] == {"completed": 0, "ceiling": 1}
    assert all(value is False for value in manifest["execution"].values())


def test_single_command_and_fail_closed_limits_are_exact() -> None:
    manifest = json.loads((ROOT / PACKET_RELATIVE / "manifest.json").read_bytes())
    command = manifest["command"]
    assert command.count("-m") == 1
    assert any(item.endswith("linux_generation_runner_v1_2_1") for item in command)
    assert manifest["limits"] == {
        "attempt_ceiling": 1, "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200, "minimum_free_vram_mib": 14000,
        "retry": 0, "fallback": 0, "repair": 0, "selection": 0,
        "stage_c": False,
    }


def test_materializer_and_verifier_have_no_execution_callsite() -> None:
    paths = (
        ROOT / "src/pastila_scout/semantic_admission_v2/"
        "stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1.py",
        ROOT / "scripts/verify_construction_obligation_v2_case01_issuance_packet_v1_2_1.py",
    )
    for path in paths:
        tree = ast.parse(path.read_text("utf-8"))
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert "execute" not in attributes
        text = path.read_text("utf-8")
        assert all(term not in text for term in (
            "subprocess", "from_pretrained", ".generate(", "nvidia-smi"))


def test_v1_2_packet_and_issued_receipt_remain_byte_exact_and_distinct():
    import hashlib
    old = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2"
    assert hashlib.sha256((old / "manifest.json").read_bytes()).hexdigest() == "3e12bda6cb4ff4eec92ea4af8f61891418273afb346648372d49311daa0074b6"
    assert hashlib.sha256((old / "authority-receipt-issued.json").read_bytes()).hexdigest() == "51edb799c9194283f39deda9cbf7650ae9e2b1f8ded2fde3b3c6f362c650e4d8"
    current = json.loads((ROOT / PACKET_RELATIVE / "manifest.json").read_bytes())
    assert current["packet_identity"] != "34cab9bfd4e0a339ba79fa1d6acba68ab8aec50856cbfc28fcd4866fb3a78202"
    assert current["authority_reference_if_issued"] != "e38035ec43e037c02d07597f6177763ee1e672cd462272c7da80fb50d1a86e06"
    superseded = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1"
    assert json.loads((superseded / "manifest.json").read_bytes())["packet_identity"] == "1e5af20116b8500488dd6a5fcb7ea8de05ada1f3d6c72103b4c80e5300fd86a9"
    assert json.loads((superseded / "authority-receipt-candidate.json").read_bytes())["proposed_receipt_identity"] == "b092c6a7c5d8aeca4dcbe1300e67ee3ea10b311939105608e661f54a5cf86754"
    isolated = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-identity-isolated"
    assert json.loads((isolated / "manifest.json").read_bytes())["packet_identity"] == "34513d594d5e55dfd94c930de791c621da58b1db78d2b978518e2c4f4877772b"
    assert json.loads((isolated / "authority-receipt-candidate.json").read_bytes())["proposed_receipt_identity"] == "053336878603d8cbd8fea9cd0c3eee6cb307a002be632f22670932a55d3503a6"
