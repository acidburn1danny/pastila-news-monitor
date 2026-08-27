from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "pastila_scout"

# Frozen/evaluation launchers are intentionally grandfathered.  Their exact
# bytes and evidence must be rebound individually before migration.
LEGACY_DIRECT_LAUNCHERS = {
    "semantic_admission_v2/constrained_core_executor_v1.py",
    "semantic_admission_v2/stage_p_construction_obligation_durable_executor_v1.py",
    "semantic_admission_v2/stage_p_construction_obligation_projector_durable_executor_v2.py",
    "semantic_admission_v2/stage_p_construction_obligation_projector_durable_executor_v3.py",
    "semantic_admission_v2/stage_p_construction_role_durable_executor_v1.py",
    "semantic_admission_v2/stage_p_creative_target_durable_executor_v1.py",
    "semantic_admission_v2/stage_p_durable_executor_v2.py",
    "semantic_admission_v2/stage_p_durable_executor_v3.py",
    "semantic_admission_v2/stage_p_durable_executor_v4.py",
    "semantic_admission_v2/stage_p_role_coherence_durable_executor_v1.py",
    "semantic_admission_v2/stage_p_role_coherence_durable_executor_v2.py",
    "semantic_admission_v2/stage_p_scope_graph_durable_executor_v1.py",
    "semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_1.py",
    "semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_2.py",
    "semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_3.py",
    "semantic_admission_v2/staged_gate_f_provider_v1.py",
}


def test_no_new_direct_wsl_launchers_bypass_canonical_boundary():
    observed = set()
    for path in SOURCE_ROOT.rglob("*.py"):
        if "wsl.exe" in path.read_text("utf-8"):
            relative = path.relative_to(SOURCE_ROOT).as_posix()
            if relative != "wsl_execution_v1/boundary.py":
                observed.add(relative)
    assert observed <= LEGACY_DIRECT_LAUNCHERS


def test_active_core_consumers_use_shared_boundary_not_direct_subprocess():
    for name in ("experimental_core_v1_1.py", "experimental_core_v1_2.py"):
        source = (SOURCE_ROOT / name).read_text("utf-8")
        assert "pastila_scout.wsl_execution_v1" in source
        assert "subprocess.run" not in source
        assert '"wsl.exe"' not in source


def test_packager_explicitly_collects_boundary_for_dynamic_consumers():
    spec = (ROOT / "packaging" / "pyinstaller" / "PastilaScout.spec").read_text("utf-8")
    assert '"pastila_scout.wsl_execution_v1"' in spec
    assert '"pastila_scout.wsl_execution_v1.boundary"' in spec
