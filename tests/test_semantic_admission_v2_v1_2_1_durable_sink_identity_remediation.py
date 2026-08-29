from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 as composition,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    SUPERVISOR_CANDIDATE_IDENTITY,
    SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1,
    DurableEvidenceRootBindingV1,
    create_durable_filesystem_sink_v1,
    create_durable_filesystem_sink_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import (
    SUPERVISOR_CANDIDATE_IDENTITY as CANONICAL_V1_2_1_SUPERVISOR_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    PACKET_RELATIVE,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / PACKET_RELATIVE


def _binding(supervisor_identity: str) -> DurableEvidenceRootBindingV1:
    return DurableEvidenceRootBindingV1(
        "application-request-v1:test", "1" * 64, "2" * 64, supervisor_identity,
    )


def test_v1_2_1_sink_accepts_only_exact_current_supervisor(tmp_path: Path) -> None:
    assert SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1 == CANONICAL_V1_2_1_SUPERVISOR_IDENTITY
    sink = create_durable_filesystem_sink_v1_2_1(
        root=tmp_path / "v1-2-1", binding=_binding(CANONICAL_V1_2_1_SUPERVISOR_IDENTITY),
    )
    assert sink.binding.supervisor_candidate_identity == CANONICAL_V1_2_1_SUPERVISOR_IDENTITY
    with pytest.raises(ValueError, match="DURABLE_SUPERVISOR_IDENTITY_MISMATCH"):
        create_durable_filesystem_sink_v1_2_1(
            root=tmp_path / "legacy-rejected", binding=_binding(SUPERVISOR_CANDIDATE_IDENTITY),
        )


def test_legacy_sink_contract_remains_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DURABLE_SUPERVISOR_IDENTITY_MISMATCH"):
        create_durable_filesystem_sink_v1(
            root=tmp_path / "current-rejected",
            binding=_binding(CANONICAL_V1_2_1_SUPERVISOR_IDENTITY),
        )


def test_v1_2_1_composition_binds_versioned_sink_without_execution_surface() -> None:
    source = Path(composition.__file__).read_text("utf-8")
    assert "create_durable_filesystem_sink_v1_2_1" in source
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert all(not (isinstance(node.func, ast.Attribute) and node.func.attr == "execute")
               for node in calls)
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi",
    ))


def test_real_composition_crosses_sink_binding_and_persists_injected_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = json.loads((PACKET / "authority-receipt-candidate.json").read_bytes())
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = candidate["proposed_receipt_identity"]
    canonical = lambda value: (json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False) + "\n").encode()
    monkeypatch.setattr(
        composition, "build_linux_child_process_operations_v1_2_1",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("INJECTED_AFTER_SINK")))
    evidence = tmp_path / "linux-generation"
    with pytest.raises(RuntimeError, match="INJECTED_AFTER_SINK"):
        composition.run_linux_generation_composition_v1_2_1(
            raw_policy_receipt=(ROOT / "docs/artifacts/semantic-admission-v2-stage-p-"
                "construction-obligation-v2-generation-policy-validation-receipt-v1.json"
            ).read_bytes(),
            raw_authority_receipt=canonical(issued),
            raw_runner_request=(PACKET / "runner-request.json").read_bytes(),
            system_prompt="not consumed before injected failure",
            evidence_root=evidence, timeout_seconds=1200.0)
    persisted = evidence / "composition-pre-model-failure-v1-2.json"
    assert persisted.is_file()
    receipt = json.loads(persisted.read_bytes())
    assert receipt["failure_type"] == "RuntimeError"
    assert receipt["model_load_started"] is False
    assert receipt["generation_started"] is False
