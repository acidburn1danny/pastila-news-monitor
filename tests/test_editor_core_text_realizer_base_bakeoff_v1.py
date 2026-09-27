import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rebuild_fixture_and_audit():
    subprocess.run([sys.executable, "-B", "scripts/build_editor_core_text_realizer_base_bakeoff_v1.py"], cwd=ROOT, check=True)
    fixture = subprocess.run([sys.executable, "-B", "scripts/fixture_editor_core_text_realizer_base_bakeoff_v1.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    audit = subprocess.run([sys.executable, "-B", "scripts/audit_editor_core_text_realizer_base_bakeoff_v1.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert json.loads(fixture.stdout)["valid_acceptances"] == 144
    assert json.loads(audit.stdout)["checks"] == 12


def test_initial_round_is_text_only_and_unbound_models_block_real_execution():
    candidates = json.loads((ROOT / "docs/artifacts/editor-core-text-realizer-base-bakeoff-v1-candidates.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "docs/artifacts/editor-core-text-realizer-base-bakeoff-v1-protocol.json").read_text(encoding="utf-8"))
    assert all(arm["architecture_scope"] == "TEXT_ONLY" for arm in candidates["initial_arms"][1:])
    assert all(arm["model_revision"] == "MUST_PIN_BEFORE_DOWNLOAD" for arm in candidates["initial_arms"][1:])
    assert protocol["download_authorized"] is False
    assert protocol["inference_authorized"] is False
    assert protocol["base_weight_only_causal_claim_allowed"] is False
    assert candidates["quantization_policy"]["challengers"] == "SAME_BACKEND_BIT_WIDTH_AND_QUANTIZATION_RECIPE"
