from __future__ import annotations

import inspect


def test_linux_v1_2_1_import_resolves_exact_canonical_provider_request(
    monkeypatch,
) -> None:
    import os
    import subprocess

    calls: list[str] = []

    def forbidden(*args, **kwargs):
        calls.append("process")
        raise AssertionError("import attempted a process side effect")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2
    from pastila_scout.provider_execution_v2.models import (
        ProviderExecutionRequestV2 as CanonicalProviderExecutionRequestV2,
    )
    from pastila_scout.semantic_admission_v2 import (
        stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1,
    )

    annotation = inspect.get_annotations(
        CanonicalProviderExecutionRequestV2.validate_provider_authority,
        eval_str=True,
    )["return"]
    assert annotation is CanonicalProviderExecutionRequestV2
    assert ProviderExecutionRequestV2 is CanonicalProviderExecutionRequestV2
    assert stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1.__name__.endswith(
        "v1_2_1"
    )
    assert calls == []


def test_import_remediation_contains_no_execution_or_model_calls() -> None:
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "src/pastila_scout/provider_execution_v2/models.py",
        root / "src/pastila_scout/semantic_admission_v2/"
        "stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1.py",
    )
    for path in paths:
        source = path.read_text("utf-8")
        tree = ast.parse(source)
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert "execute" not in attributes
        assert all(term not in source for term in (
            "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi",
        ))
