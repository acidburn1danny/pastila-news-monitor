from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENTRY = (
    "pastila_scout.semantic_admission_v2."
    "stage_p_construction_obligation_v2_linux_generation_runner_v1_1"
)
SINK = SRC / "pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_durable_filesystem_sink_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-transport-failure-static-remediation-v1.json"


def _module_path(name: str) -> Path | None:
    candidate = SRC.joinpath(*name.split(".")).with_suffix(".py")
    if candidate.is_file():
        return candidate
    package = SRC.joinpath(*name.split("."), "__init__.py")
    return package if package.is_file() else None


def test_generation_import_closure_parses_under_frozen_python_3_12() -> None:
    pending = [ENTRY]
    visited: set[str] = set()
    paths: set[Path] = set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        path = _module_path(module)
        if path is None:
            continue
        paths.add(path)
        tree = ast.parse(
            path.read_text("utf-8"), filename=str(path), feature_version=(3, 12)
        )
        package = module if path.name == "__init__.py" else module.rpartition(".")[0]
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level:
                target = importlib.util.resolve_name(
                    "." * node.level + (node.module or ""), package
                )
            else:
                target = node.module or ""
            if target.startswith("pastila_scout"):
                pending.append(target)
    assert SINK in paths


def test_remediation_identity_and_non_authority_are_exact() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SINK.read_bytes()).hexdigest() == artifact["source_remediation"]["new_source_sha256"]
    assert artifact["source_remediation"]["corrected_command_identity"] is None
    assert artifact["future_authority"] == {
        "fresh_command_identity_required": True,
        "fresh_execution_packet_required": True,
        "fresh_owner_authority_required": True,
        "second_attempt_authorized": False,
        "stage_c_authorized": False,
    }
