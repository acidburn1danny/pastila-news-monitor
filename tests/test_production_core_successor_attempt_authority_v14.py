"""The V14 runner accepts only the successor qualification identities."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v14.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("runner_v14_under_test", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_successor_pair_accepted() -> None:
    runner = load_runner()
    runner.verify_successor_identities(
        "65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567",
        "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13",
    )


@pytest.mark.parametrize("generation,qualification", [
    ("a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7",
     "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13"),
    ("65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567",
     "607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45"),
    ("0" * 64, "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13"),
    ("65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567", "0" * 64),
])
def test_historical_or_substituted_identity_rejected(generation: str, qualification: str) -> None:
    with pytest.raises(SystemExit):
        load_runner().verify_successor_identities(generation, qualification)


def test_shell_transports_both_authorities() -> None:
    shell = (ROOT / "scripts/run_production_core_candidate_qualification_v14.sh").read_text()
    assert 'QUALIFICATION_GENERATION_IDENTITY="$GENERATION_ID"' in shell
    assert 'QUALIFICATION_IDENTITY="$QUALIFICATION_ID"' in shell
    assert 'if [[ $# -ne 13 ]]' in shell
    assert "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7" not in RUNNER.read_text()


def test_executor_projection_passes_qualification_to_shell() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import execute_production_core_candidate_qualification_v14 as executor
        source = executor.projected_mechanics()
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    assert '            GENERATION_IDENTITY,\n            QUALIFICATION_IDENTITY,\n' in source
    assert '"scripts/execute_production_core_candidate_qualification_v14.py"' in source
