import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_successor_candidate_manifest_v5.py"
ART = ROOT / "docs/artifacts"


def module():
    spec = importlib.util.spec_from_file_location("candidate_manifest_v5", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_v5_audit_receipt_and_manifest_are_sealed_zero_execution():
    value = module()
    receipt = value.audit_receipt()
    receipt_core = dict(receipt)
    assert receipt_core.pop("adapter_audit_identity") == value.identity(receipt_core)
    manifest = value.candidate_manifest(receipt)
    manifest_core = dict(manifest)
    assert manifest_core.pop("manifest_identity") == value.identity(manifest_core)
    assert manifest["qualification_authority_issued"] is False
    assert manifest["qualification_attempt_consumed"] is False
    assert manifest["candidate_execution_performed"] is False
    assert receipt["development_gate"]["status"] == "PASS"


def test_v5_materialization_is_reproducible(tmp_path):
    value = module()
    import sys

    prior = sys.argv
    try:
        sys.argv = [str(SCRIPT), "--output-dir", str(tmp_path)]
        assert value.main() == 0
    finally:
        sys.argv = prior
    for name in (
        "production-core-v1.1-successor-adapter-audit-receipt-v5.json",
        "production-core-successor-candidate-object-manifest-v5.json",
    ):
        assert (tmp_path / name).read_bytes() == (ART / name).read_bytes()


def test_v5_manifest_preserves_existing_v1_2_and_has_no_promotion():
    manifest = json.loads((ART / "production-core-successor-candidate-object-manifest-v5.json").read_bytes())
    assert manifest["adapter_manifest_sha256"]["pastila-editor-core-v1.2-json-successor"] == (
        "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719"
    )
    assert manifest["retry_or_redraw"] is False
    assert manifest["adjudication_performed"] is False
    assert manifest["promotion_effect"] is False
