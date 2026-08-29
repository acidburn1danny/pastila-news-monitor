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
ROOT = Path(__file__).resolve().parents[1]


def test_generation_telemetry_packet_plan_is_fresh_unissued_and_deterministic() -> None:
    generated = materialize_case01_issuance_packet_v1_2_1(project_root=ROOT)
    assert all((ROOT / PACKET_RELATIVE / name).read_bytes() == raw
               for name, raw in generated.items())
    actual = {path.name for path in (ROOT / PACKET_RELATIVE).iterdir()}
    assert actual == {"application-provider-request.json", "authority-receipt-candidate.json",
                      "host-payload.json", "manifest.json",
                      "rendered-prompt.json", "runner-request.json", "static-executor-binding.json"}
    manifest = json.loads((ROOT / PACKET_RELATIVE / "manifest.json").read_bytes())
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
    packet_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-packet-bound"
    assert json.loads((packet_bound / "manifest.json").read_bytes())["packet_identity"] == "38a3bf93c01b35b935089ddb7db576cc1f2438a7fea386f5e7678b1e01734720"
    assert json.loads((packet_bound / "authority-receipt-candidate.json").read_bytes())["proposed_receipt_identity"] == "5eae2ad3c40b27ab5440c37d89cbf69a93cc028848fadc31f0326b5ff91fc69d"
    authority_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-authority-plan-bound"
    assert json.loads((authority_bound / "manifest.json").read_bytes())["packet_identity"] == "047158aba98385606383d3432bd4b3cef7a6bf90e8014460257400f505694004"
    assert json.loads((authority_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "d9d72feefa7015021ca79388dcee837c21103c87fef0733903b3d73f8e233da4"
    provider_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-provider-source-bound"
    assert json.loads((provider_bound / "manifest.json").read_bytes())["packet_identity"] == "4b5a4cde519be6f94292fd1873e6bbb7b74d737e92d965580ec61423dbf017eb"
    assert json.loads((provider_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "9e79a1bec349d417d1a8cbbc79137385c92c994a57a2ed0ce5d528a2d73f9362"
    application_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-application-source-bound"
    assert json.loads((application_bound / "manifest.json").read_bytes())["packet_identity"] == "d38b515c38e159765a09fa42a281cd438691ace9066cf7d811953d3e28c129e3"
    assert json.loads((application_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "215cd224e82240ce2d7d439b3904063ab3d808a059ea70d53140ce73af65eb3f"
    durable_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-durable-source-bound"
    assert json.loads((durable_bound / "manifest.json").read_bytes())["packet_identity"] == "211146a527ad73c67f414ce3da582049eb1a5053884abfd1726abae29bb7ec25"
    assert json.loads((durable_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "2ca3f66aa1f5ac86444151b376e36d884f3324a9986c228f01b9894f1b41ab99"
    runtime_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-runtime-source-bound"
    assert json.loads((runtime_bound / "manifest.json").read_bytes())["packet_identity"] == "8ecc76557f5d020655abf9ed2c8cd51b355d6131d3299d27704625b91710d510"
    assert json.loads((runtime_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "9ef49ce6b0b3992928a6904427497522b51eac03a7e5aa79297298b4b348c397"
    exact_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-exact-operations-bound"
    assert json.loads((exact_bound / "manifest.json").read_bytes())["packet_identity"] == "329cbd127db807728f74928956b4868828de9f58373b9b45809d78763b890ff5"
    assert json.loads((exact_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "b9176dbe4d2d1d98eb43d6e13e20e9955010c5e5a30ee89f609197dcb35b24a9"
    durable_label_bound = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-durable-label-bound"
    assert json.loads((durable_label_bound / "manifest.json").read_bytes())["packet_identity"] == "181a50a073ff1517700cff6c7a012ae9f259d53bcf6f2eeba870eda71f5aa257"
    assert json.loads((durable_label_bound / "authority-receipt-issued.json").read_bytes())["authority_receipt_identity"] == "50ae8b93807b9749d0007887a33556344cc7e3382b2d5cf7ce8283fb9191e19e"
