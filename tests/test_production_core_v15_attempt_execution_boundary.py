"""V15 attempt-route negative tests without candidate or real attempt output."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import execute_production_core_candidate_qualification_v14 as predecessor  # noqa: E402
import execute_production_core_candidate_qualification_v15 as executor  # noqa: E402
import materialize_production_core_v15_attempt_execution_boundary as issuer  # noqa: E402
import smoke_production_core_v15_attempt_execution_boundary as fixture  # noqa: E402
from pastila_scout import production_core_candidate_execution_authority_v15 as validator  # noqa: E402
from pastila_scout import production_core_wsl_driver_snapshot_v15 as drivers  # noqa: E402


def test_v15_projection_exact_shell_inputs_and_no_v14_shell() -> None:
    source = executor.projected_mechanics()
    assert source.count("            str(SNAPSHOT),\n") == 1
    assert source.count("            str(DRIVER_HELPER),\n") == 1
    assert source.count("            hashlib.sha256(read(DRIVER_HELPER)).hexdigest(),\n") == 1
    assert "scripts/execute_production_core_candidate_qualification_v14.py" not in source
    assert executor.LAUNCHER.name == "run_production_core_candidate_qualification_v15.sh"
    commands = [node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "command" for target in node.targets)
                and isinstance(node.value, ast.List)]
    assert len(commands) == 1
    command = commands[0].elts
    separator = next(index for index, node in enumerate(command)
                     if isinstance(node, ast.Constant) and node.value == "--")
    assert len(command[separator + 1:]) == 16
    assert validator.GENERATION_IDENTITY == "65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567"
    assert validator.QUALIFICATION_IDENTITY == "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13"


def test_wrong_argument_projection_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = predecessor.projected_mechanics()
    monkeypatch.setattr(predecessor, "projected_mechanics",
                        lambda: original.replace("            wsl(RUNNER),\n        ]",
                                                 "            wsl(RUNNER),\n            'wrong',\n        ]"))
    with pytest.raises(ValueError, match="16-argument"):
        executor.projected_mechanics()


def test_v14_shell_substitution_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executor, "LAUNCHER", ROOT / "scripts/run_production_core_candidate_qualification_v14.sh")
    with pytest.raises(ValueError, match="V14 launcher"):
        executor.build_namespace({"source_sha256": {}})


def test_v15_namespace_uses_only_new_boundary_identity() -> None:
    keys = (
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/execute_production_core_candidate_qualification_v15.py",
        "scripts/launch_production_core_candidate_qualification_v15.py",
        "scripts/preflight_production_core_candidate_qualification_v15.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v15.sh",
        "scripts/smoke_production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_candidate_execution_authority_v15.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
        "src/pastila_scout/production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
    )
    boundary = {"boundary_identity": "b" * 64,
                "source_sha256": {name: "a" * 64 for name in keys}}
    namespace = executor.build_namespace(boundary)
    assert namespace["PINNED_EXECUTION_MECHANISM"]["execution_authority_identity"] == "b" * 64
    assert namespace["LAUNCHER"].name == "run_production_core_candidate_qualification_v15.sh"
    assert namespace["HELPER"] == ROOT / "scripts/resolve_production_core_object_authority_v2.sh"
    assert namespace["DRIVER_HELPER"] == ROOT / "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"
    assert namespace["atomic"] is executor.atomic_no_replace
    assert namespace["lock_directory"] is executor.lock_directory


def test_wrong_execution_identity_rejected() -> None:
    with pytest.raises(validator.ExecutionAuthorityError):
        validator.build_attempt("0" * 64, {"execution_authority_identity": "1" * 64})


def test_modified_published_preflight_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.read_bytes
    target = ROOT / "scripts/preflight_production_core_candidate_qualification_v15.py"

    def changed(path: Path) -> bytes:
        if path == target:
            return b"modified-unpublished-preflight"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="published V15 attempt source drift"):
        issuer.source_closure()


def test_snapshot_manifest_and_output_are_bound() -> None:
    assert issuer.PREFLIGHT_COMMIT == "6415c3307dcfff4205c6d23af2db4102d933d160"
    assert issuer.V15_AUTHORITY == "6bcd6d782b8096c394f0dabd5f3bb4f25f32222edd712b2da587ae843e35d472"
    assert issuer.build.__code__.co_consts.count("NO_RESTART_OR_REEXECUTION_AFTER_ATTEMPT_JSON") == 1
    assert "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json" in issuer.SOURCE_FILES
    assert "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py" in issuer.SOURCE_FILES
    assert "scripts/smoke_production_core_v15_attempt_execution_boundary.py" in issuer.SOURCE_FILES


def test_modified_snapshot_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "drivers"
    root.mkdir()
    payload = root / "driver.bin"
    payload.write_bytes(b"pinned")
    rows = [["driver.bin", 6, hashlib.sha256(b"pinned").hexdigest()]]
    expected = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    monkeypatch.setattr(drivers, "EXPECTED_FILES", 1)
    monkeypatch.setattr(drivers, "EXPECTED_MANIFEST", expected)
    payload.chmod(0o444)
    root.chmod(0o555)
    try:
        assert drivers.manifest(root)["manifest_identity"] == expected
        payload.chmod(0o644)
        payload.write_bytes(b"changed")
        payload.chmod(0o444)
        with pytest.raises(ValueError, match="manifest mismatch"):
            drivers.manifest(root)
    finally:
        root.chmod(0o755)
        payload.chmod(0o644)


def test_fixture_concurrency_no_clobber_and_terminal_process() -> None:
    result = fixture.smoke()
    assert result["parallel_owner"] == "REJECTED"
    assert result["fixture_no_clobber"] == "PASS"
    assert result["terminal_process_failure"] == "PROPAGATED"
    assert result["sigkill_after_claim"] == "NO_RECONSUMPTION_NO_ORPHAN"
    assert result["real_attempt_json"] == "ABSENT"
