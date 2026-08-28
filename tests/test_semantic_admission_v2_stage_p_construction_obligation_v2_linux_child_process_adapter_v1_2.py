from pathlib import Path

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2 as adapter

ROOT = Path(__file__).resolve().parents[1] / "src/pastila_scout/semantic_admission_v2"


def test_v1_2_child_binding_uses_only_v1_2_authority_and_generation_layers():
    source = (ROOT / "stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2.py").read_text("utf-8")
    assert "parse_generation_authority_v1_2" in source
    assert "supervise_injected_generation_v1_2" in source
    assert "prepare_linux_runtime_operations_v1_1" in source
    assert "adapt_runtime_operations_v1_2" in source
    assert "parse_generation_authority_v1_1" not in source
    assert "supervise_injected_generation_v1_1" not in source


def test_import_and_construction_boundary_remain_separate():
    assert adapter.build_linux_child_process_operations_v1_2.__name__.endswith("v1_2")
    assert adapter.LINUX_CHILD_PROCESS_ADAPTER_IDENTITY.startswith("3fb67ad0")
