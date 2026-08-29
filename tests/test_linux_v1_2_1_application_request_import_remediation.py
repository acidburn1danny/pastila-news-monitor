from __future__ import annotations

import inspect


def test_linux_v1_2_1_import_resolves_exact_canonical_application_request(
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

    from pastila_scout.application_request_authority_v1 import (
        ApplicationProviderRequestV1,
    )
    from pastila_scout.application_request_authority_v1.models import (
        ApplicationProviderRequestV1 as CanonicalApplicationProviderRequestV1,
        _reconstruct,
    )
    from pastila_scout.semantic_admission_v2 import (
        stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1,
    )

    copy_return = inspect.get_annotations(
        CanonicalApplicationProviderRequestV1.__copy__, eval_str=True,
    )["return"]
    reconstruct_return = inspect.get_annotations(_reconstruct, eval_str=True)["return"]
    assert copy_return is CanonicalApplicationProviderRequestV1
    assert reconstruct_return is CanonicalApplicationProviderRequestV1
    assert ApplicationProviderRequestV1 is CanonicalApplicationProviderRequestV1
    assert stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1.__name__.endswith(
        "v1_2_1"
    )
    assert calls == []


def test_application_request_import_remediation_has_no_execution_calls() -> None:
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "src/pastila_scout/application_request_authority_v1/models.py",
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
