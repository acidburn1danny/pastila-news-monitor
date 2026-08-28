def test_identity_contract_is_import_isolated_and_exact():
    from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_v1_2_identity_contract as identity
    assert identity.COMPOSITION_IDENTITY.startswith("d846d21e")
    assert identity.RUNNER_IDENTITY.startswith("47fd00ab")
    assert identity.WSL_BINDING_IDENTITY.startswith("f7ca486f")
    assert identity.HOST_EXECUTOR_IDENTITY.startswith("fc793d41")


def test_authority_gate_import_does_not_import_effectful_layers():
    import subprocess, sys
    code = (
        "import sys; "
        "import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_2; "
        "print(any(k.endswith('linux_generation_composition_v1_2') or k.endswith('generation_wsl_host_executor_v1_2') for k in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
