from __future__ import annotations

import ast
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

ROOT = Path(__file__).resolve().parents[1]


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
