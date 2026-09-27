import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


RUNTIME = module("hybrid_runtime", "scripts/editor_core_source_bound_hybrid_runtime_v1.py")
FIXTURE = module("hybrid_fixture_runtime", "scripts/fixture_editor_core_source_bound_hybrid_feasibility_v1.py")


def test_boundary_rebuild_and_source_hashes():
    subprocess.run([sys.executable, "-B", "scripts/build_editor_core_source_bound_hybrid_runtime_boundary_v1.py"], check=True)
    boundary = json.loads(Path("docs/artifacts/editor-core-source-bound-hybrid-runtime-boundary-v1.json").read_text(encoding="utf-8"))
    assert boundary["source_commit"] == "50c103a5cf7238588789ed3600693ff4ac2ba053"
    assert boundary["pack_identity"] == "bbad139fde613c1c912cd53992b4c2be047d73180f6a6ae732dc6348461d28f9"
    assert boundary["protocol_identity"] == "5a5ef79af85a3b58b3c0e2f46be3f9e3dd573d75dae361c6d6df88588f7c1aea"
    assert boundary["files"] == {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in boundary["files"]}


def test_b0_b1_b2_are_separate_fixture_routes():
    ledger = FIXTURE.load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")[0]
    outputs = {arm: RUNTIME.fixture_arm(arm, ledger) for arm in RUNTIME.ARMS}
    assert outputs["B0_R2_ONE_PASS"]["mode"] == "REQUEST_ONLY_NO_INFERENCE"
    assert outputs["B1_EXTRACTIVE_BASELINE"]["mode"] == "DETERMINISTIC_EXTRACTIVE"
    assert outputs["B2_HYBRID"]["mode"] == "FIXTURE_REALIZER_THEN_VERIFY"
    assert not any(output["model_loaded"] for output in outputs.values())


def test_boundary_has_no_real_authority_and_preserves_oracle_limit():
    boundary = json.loads(Path("docs/artifacts/editor-core-source-bound-hybrid-runtime-boundary-v1.json").read_text(encoding="utf-8"))
    assert boundary["slots"] == 9
    assert boundary["oracle_fixture_upper_bound"] is True
    assert boundary["autonomous_ledger_construction_claimed"] is False
    for key in (
        "model_load_authorized", "inference_authorized", "optimizer_creation_authorized",
        "training_authorized", "execution_authority", "successor_candidate_authorized",
        "parent_selection_authority", "promotion_authorized", "release_authorized",
        "voice_or_chief_editor_objective",
    ):
        assert boundary[key] is False


def test_route_only_permits_zero_step():
    route = Path("scripts/run_editor_core_source_bound_hybrid_runtime_v1.sh").read_text(encoding="utf-8")
    assert "--zero-step-only" in route and "exit 64" in route


def test_fixture_smoke_and_adversarial_audit():
    smoke = subprocess.run([sys.executable, "-B", "scripts/smoke_editor_core_source_bound_hybrid_runtime_v1.py"], check=True, capture_output=True, text=True)
    audit = subprocess.run([sys.executable, "-B", "scripts/audit_editor_core_source_bound_hybrid_runtime_v1.py"], check=True, capture_output=True, text=True)
    assert json.loads(smoke.stdout)["status"] == "PASS_FIXTURE_RUNTIME_SMOKE"
    assert json.loads(audit.stdout)["status"] == "PASS_ADVERSARIAL"
