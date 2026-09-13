import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_production_core_candidate_qualification_v9.py"
MATERIALIZER = ROOT / "scripts/materialize_production_core_successor_execution_authority_v9.py"
AUTHORITY = ROOT / "docs/artifacts/production-core-candidate-execution-authority-v9.json"
BINDING = ROOT / "docs/artifacts/production-core-candidate-execution-authority-v9.binding.json"


def test_v9_launcher_is_detached_signed_and_fail_closed():
    source = LAUNCHER.read_text("utf-8")
    assert "production-core-candidate-execution-authority-v9.json" in source
    assert "production-core-candidate-execution-authority-v8-1.json" not in source
    assert "SIGNING_PUBLIC_KEY_SHA256" in source
    assert "detached authority signature invalid" in source
    assert "signed authority binding mismatch" in source
    assert "FROZEN_SUCCESSOR_V9_DUAL_STRUCTURAL_REMEDIATION_ZERO_ATTEMPTS" in source
    assert "candidate_execution_authorized\") is not False" in source
    assert "attempt_consumption_authorized\") is not False" in source


def test_v9_runtime_source_closure_uses_v9_launcher_only():
    source = (ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v3.py").read_text("utf-8")
    assert '"scripts/launch_production_core_candidate_qualification_v9.py"' in source
    assert '"scripts/launch_production_core_candidate_qualification_v4.py"' not in source


def test_v9_authority_and_binding_are_content_addressed_zero_attempt():
    spec = importlib.util.spec_from_file_location("authority_v9", MATERIALIZER)
    value = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(value)
    authority = json.loads(AUTHORITY.read_bytes())
    assert value.build() == authority
    core = dict(authority); claimed = core.pop("execution_authority_identity")
    assert hashlib.sha256(value.canonical(core)).hexdigest() == claimed
    binding = json.loads(BINDING.read_bytes())
    assert binding["authority_identity"] == claimed
    assert binding["authority_sha256"] == hashlib.sha256(AUTHORITY.read_bytes()).hexdigest()
    assert authority["candidate_execution_authorized"] is False
    assert authority["attempt_consumption_authorized"] is False
