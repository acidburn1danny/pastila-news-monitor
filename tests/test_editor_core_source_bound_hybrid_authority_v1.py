import importlib.util, json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def test_build_verify_and_audit():
    subprocess.run([sys.executable, "-B", str(SCRIPTS / "build_editor_core_source_bound_hybrid_authority_v1.py")], check=True)
    verifier = load("verify_editor_core_source_bound_hybrid_authority_v1")
    assert len(verifier.verify()["slots"]) == 9
    result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "audit_editor_core_source_bound_hybrid_authority_v1.py")],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["blockers"] == 0

def test_slot_fixture_and_invalid_slot():
    worker = load("editor_core_source_bound_hybrid_slot_v1")
    assert worker.fixture("B2_HYBRID", 161803)["status"] == "PASS_FIXTURE_SLOT"
    with pytest.raises(ValueError, match="unauthorized slot"): worker.fixture("B9", 161803)

def test_supervisor_refuses_before_root_creation():
    root = ROOT / "NEVER_CREATED_HYBRID_AUTHORITY_TEST"
    assert not root.exists()
    result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "supervise_editor_core_source_bound_hybrid_v1.py"),
                             "--output-root", str(root)], capture_output=True, text=True)
    assert result.returncode != 0 and "separate owner authorization required" in result.stderr
    assert not root.exists()

def test_b2_verifier_and_fallback_are_in_worker_source():
    source = (SCRIPTS / "editor_core_source_bound_hybrid_slot_v1.py").read_text(encoding="utf-8")
    assert "execute_with_fallback(ledger, proposal)" in source
    assert 'result["route"]' in source and '"verified": True' in source

def test_atomic_and_no_partial_evidence_are_supervised():
    source = (SCRIPTS / "supervise_editor_core_source_bound_hybrid_v1.py").read_text(encoding="utf-8")
    assert 'work = args.output_root / ".inflight"' in source
    assert "if work.exists(): shutil.rmtree(work)" in source
    assert ').replace(args.output_root / f"{arm.lower()}__seed_{seed}")' in source
    assert source.index('shutil.rmtree(work)\n    atomic_json(args.output_root / "terminal.json"') > source.index("for arm in ARMS:")
    assert '"partial_eligible_evidence": False' in source
